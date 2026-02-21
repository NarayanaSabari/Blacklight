"""Email Sync Service.

Handles fetching emails from connected accounts, filtering for job-related emails,
and coordinating with the parser service.

SCALABILITY IMPROVEMENTS (Phases 1-8 + Large Scale Redesign):
- Phase 2: Gmail Batch API for reduced API calls
- Phase 3: Redis caching for tenant roles
- Phase 5: Incremental sync using Gmail History API
- Phase 7: Distributed circuit breakers (Redis-backed)
- Large Scale: Batch dedup, Redis email storage, no skipped-email recording

FILTERING STRATEGY:
- Only match emails where subject contains EXACT role names from:
  1. Candidate.preferred_roles in the tenant
  2. GlobalRoles linked to candidates in the tenant (via CandidateGlobalRole)
- Skip if no roles configured in tenant
- No generic pattern/keyword matching (reduces noise)
"""

import base64
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from sqlalchemy import select, func

from app import db
from app.models.candidate import Candidate
from app.models.candidate_global_role import CandidateGlobalRole
from app.models.global_role import GlobalRole
from app.models.processed_email import ProcessedEmail
from app.models.user_email_integration import UserEmailIntegration
from app.services.email_integration_service import email_integration_service
from app.services.oauth.gmail_oauth import gmail_oauth_service
from app.services.oauth.outlook_oauth import outlook_oauth_service
from app.utils.circuit_breaker import gmail_circuit_breaker, outlook_circuit_breaker, CircuitBreakerError
from config.settings import settings

logger = logging.getLogger(__name__)

# Redis cache TTL for tenant roles (1 hour)
TENANT_ROLES_CACHE_TTL = 3600

# Gmail Batch API limit is 1000 requests per batch
# Using 100 for safety margin, better error isolation, and lower memory pressure
GMAIL_BATCH_SIZE = 100

# Redis key prefix for email data storage
REDIS_EMAIL_DATA_PREFIX = "email_sync:emails:"


class EmailSyncService:
    """Service for syncing and filtering job-related emails.

    Uses ROLE-BASED filtering only:
    - Matches emails where subject contains exact role names from tenant
    - No generic pattern/keyword matching (reduces AI processing cost)

    Scalability features:
    - Redis caching for tenant roles (Phase 3)
    - Gmail Batch API for reduced API calls (Phase 2)
    - Incremental sync using Gmail History API (Phase 5)
    - Distributed circuit breakers (Redis-backed) (Phase 7)
    - Batch dedup via IN() query (Large Scale)
    - Redis email data storage (Large Scale)
    - No ProcessedEmail rows for skipped emails (Large Scale)
    """

    # Email senders to skip (marketing, newsletters, automated)
    BLOCKED_SENDERS = [
        "linkedin.com",
        "e.linkedin.com",
        "messages-noreply@linkedin.com",
        "jobs-noreply@linkedin.com",
        "noreply@",
        "no-reply@",
        "mailer-daemon@",
        "newsletter@",
        "notifications@",
        "marketing@",
        "promo@",
        "substack.com",
        "medium.com",
        "mailchimp.com",
        "sendgrid.net",
        "amazonses.com",
    ]

    # Subject patterns to skip (automated emails, not actual job requirements)
    BLOCKED_SUBJECT_PATTERNS = [
        r"^new jobs similar to",
        r"jobs? you may be interested in",
        r"job alert",
        r"job recommendations?",
        r"people you may know",
        r"people also viewed",
        r"your weekly",
        r"your daily",
        r"digest",
        r"newsletter",
        r"unsubscribe",
        r"confirm your",
        r"verify your",
        r"reset password",
        r"security alert",
    ]

    def __init__(self):
        """Initialize email sync service."""
        self.initial_lookback_days = settings.email_sync_initial_lookback_days
        self.max_emails_per_page = settings.email_sync_max_emails_per_page

    # ========================================================================
    # Paginated Integration Queries (Large Scale)
    # ========================================================================

    def get_active_integrations_page(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        """
        Get a page of active integrations with total count.

        Returns serializable dicts (not ORM objects) so Inngest step output
        stays small and JSON-safe.

        Args:
            offset: Pagination offset
            limit: Page size

        Returns:
            Tuple of (integrations list of dicts, total count)
        """
        total_stmt = select(func.count(UserEmailIntegration.id)).where(
            UserEmailIntegration.is_active == True,
        )
        total = db.session.scalar(total_stmt) or 0

        stmt = (
            select(UserEmailIntegration)
            .where(UserEmailIntegration.is_active == True)
            .order_by(UserEmailIntegration.id)
            .offset(offset)
            .limit(limit)
        )
        integrations = list(db.session.scalars(stmt).all())

        return [
            {
                "id": i.id,
                "user_id": i.user_id,
                "tenant_id": i.tenant_id,
                "provider": i.provider,
            }
            for i in integrations
        ], total

    # ========================================================================
    # Sync Timestamp Update
    # ========================================================================

    def update_sync_timestamp(
        self,
        integration_id: int,
        new_history_id: Optional[str] = None,
    ) -> bool:
        """
        Update the last_synced_at timestamp after successful workflow completion.

        This should be called AFTER all emails have been processed successfully,
        not during the sync step. This ensures idempotency for Inngest retries.

        Args:
            integration_id: Integration ID to update
            new_history_id: Optional Gmail history ID for incremental sync

        Returns:
            True if updated successfully
        """
        integration = db.session.get(UserEmailIntegration, integration_id)
        if not integration:
            logger.warning(f"Integration {integration_id} not found for timestamp update")
            return False

        integration.last_synced_at = datetime.now(timezone.utc)

        if new_history_id and integration.provider == "gmail":
            integration.gmail_history_id = new_history_id

        db.session.commit()
        logger.info(f"Updated last_synced_at for integration {integration_id}")
        return True

    # ========================================================================
    # Fetch & Filter (called from Inngest step)
    # ========================================================================

    def fetch_and_filter_emails(self, integration_id: int) -> dict:
        """
        Fetch emails for an integration, filter them, and store matched emails
        in Redis. Returns a lightweight summary (no email bodies in output).

        This replaces the old sync_integration() monolith. The email bodies
        are stored in Redis with a TTL, and only a Redis key is returned
        so that Inngest step output stays under 4MB.

        Args:
            integration_id: Integration ID

        Returns:
            Dict with sync summary + redis_key for matched emails
        """
        integration = db.session.get(UserEmailIntegration, integration_id)
        if not integration:
            return {"error": "Integration not found"}

        if not integration.is_active:
            logger.info(f"Skipping inactive integration {integration.id}")
            return {"skipped": True, "reason": "inactive"}

        try:
            # Get preferred roles for filtering FIRST — skip if none configured
            preferred_roles = self._get_tenant_roles_cached(integration.tenant_id)

            if not preferred_roles:
                logger.info(
                    f"Skipping integration {integration.id}: no roles configured in tenant"
                )
                return {
                    "skipped": True,
                    "reason": "no_roles_configured",
                    "message": "No candidate preferred roles or global roles found in tenant",
                }

            logger.info(
                f"Integration {integration.id}: Found {len(preferred_roles)} roles "
                f"to match: {preferred_roles[:5]}..."
            )

            # Get valid access token
            access_token = email_integration_service.get_valid_access_token(integration)

            # Fetch emails based on provider
            if integration.provider == "gmail":
                emails, new_history_id = self._fetch_gmail_emails_with_history(
                    access_token, integration
                )
            else:
                emails = self._fetch_outlook_emails(access_token, integration)
                new_history_id = None

            # Batch dedup: get all already-processed email IDs in one query
            email_ids = [
                e.get("id") or e.get("message_id") for e in emails
            ]
            email_ids = [eid for eid in email_ids if eid]
            already_processed_ids = self._batch_check_processed(
                integration.id, email_ids
            )

            # Filter and collect matched emails
            matched_emails = []
            skipped_count = 0
            already_processed_count = len(already_processed_ids)

            for email in emails:
                email_id = email.get("id") or email.get("message_id")
                if not email_id:
                    continue

                # Skip if already processed (batch-checked)
                if email_id in already_processed_ids:
                    continue

                # Check if matches job criteria (ROLE-BASED only)
                subject = email.get("subject", "")
                sender = email.get("sender", "")
                matches, match_reason = self._matches_job_criteria(
                    subject, sender, preferred_roles
                )

                if not matches:
                    skipped_count += 1
                    # Large Scale: Do NOT record skipped emails to ProcessedEmail.
                    # We rely on time-based sync cursors for dedup, not row-per-email.
                    continue

                logger.info(
                    f"Matched email: subject='{subject[:60]}...', reason={match_reason}"
                )

                # Serialize received_at for JSON
                received_at = email.get("received_at")
                if isinstance(received_at, datetime):
                    received_at = received_at.isoformat()

                matched_emails.append({
                    "email_id": email_id,
                    "thread_id": email.get("thread_id"),
                    "subject": subject,
                    "sender": email.get("sender", ""),
                    "body": email.get("body", ""),
                    "received_at": received_at,
                    "match_reason": match_reason,
                })

            # Store matched emails in Redis (not in step output)
            redis_key = None
            if matched_emails:
                redis_key = self._store_emails_in_redis(
                    integration.id, matched_emails
                )

            # Clear previous errors
            integration.consecutive_failures = 0
            integration.last_error = None
            db.session.commit()

            result = {
                "fetched": len(emails),
                "matched": len(matched_emails),
                "skipped_count": skipped_count,
                "already_processed": already_processed_count,
                "roles_searched_count": len(preferred_roles),
                "redis_key": redis_key,
                "integration_id": integration.id,
                "tenant_id": integration.tenant_id,
            }

            # Store history ID for later update
            if new_history_id and integration.provider == "gmail":
                result["new_history_id"] = new_history_id

            logger.info(
                f"Synced integration {integration.id}: "
                f"fetched={result['fetched']}, matched={result['matched']}, "
                f"skipped={result['skipped_count']}, "
                f"already_processed={result['already_processed']}"
            )

            return result

        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker open for integration {integration.id}: {e}")
            return {"error": str(e), "circuit_breaker_open": True}

        except Exception as e:
            logger.error(f"Sync failed for integration {integration.id}: {e}")
            integration.last_error = str(e)
            integration.consecutive_failures = (
                integration.consecutive_failures or 0
            ) + 1

            if integration.consecutive_failures >= 3:
                integration.is_active = False
                logger.warning(
                    f"Deactivated integration {integration.id} due to repeated failures"
                )

            db.session.commit()
            return {"error": str(e)}

    # ========================================================================
    # Batch Dedup (Large Scale — replaces N+1 _is_email_processed)
    # ========================================================================

    def _batch_check_processed(
        self,
        integration_id: int,
        email_ids: list[str],
    ) -> set[str]:
        """
        Check which email IDs have already been processed using a single
        batch IN() query instead of N individual queries.

        Args:
            integration_id: Integration ID
            email_ids: List of email message IDs to check

        Returns:
            Set of already-processed email IDs
        """
        if not email_ids:
            return set()

        # Process in chunks of 500 to avoid hitting query parameter limits
        processed_ids: set[str] = set()
        chunk_size = 500

        for i in range(0, len(email_ids), chunk_size):
            chunk = email_ids[i:i + chunk_size]
            stmt = select(ProcessedEmail.email_message_id).where(
                ProcessedEmail.integration_id == integration_id,
                ProcessedEmail.email_message_id.in_(chunk),
            )
            chunk_results = set(db.session.scalars(stmt).all())
            processed_ids.update(chunk_results)

        logger.debug(
            f"Batch dedup: {len(processed_ids)}/{len(email_ids)} already processed "
            f"for integration {integration_id}"
        )
        return processed_ids

    # ========================================================================
    # Redis Email Storage (Large Scale)
    # ========================================================================

    def _store_emails_in_redis(
        self,
        integration_id: int,
        emails: list[dict],
    ) -> Optional[str]:
        """
        Store matched email data in Redis with TTL instead of passing
        through Inngest step output.

        The emails are stored as a JSON list under a unique key.
        The key is returned so subsequent steps can retrieve the data.

        Args:
            integration_id: Integration ID (for key namespacing)
            emails: List of matched email dicts (with bodies)

        Returns:
            Redis key string, or None if Redis unavailable
        """
        from app import redis_client

        if not redis_client:
            logger.warning(
                "Redis unavailable — email data will be passed through step output"
            )
            return None

        try:
            redis_key = (
                f"{REDIS_EMAIL_DATA_PREFIX}{integration_id}:"
                f"{uuid.uuid4().hex[:12]}"
            )
            redis_client.set(
                redis_key,
                json.dumps(emails),
                ex=settings.email_sync_redis_ttl,
            )
            logger.info(
                f"Stored {len(emails)} emails in Redis: {redis_key} "
                f"(TTL={settings.email_sync_redis_ttl}s)"
            )
            return redis_key

        except Exception as e:
            logger.error(f"Failed to store emails in Redis: {e}")
            return None

    def get_emails_from_redis(self, redis_key: str) -> Optional[list[dict]]:
        """
        Retrieve email data from Redis.

        Args:
            redis_key: Redis key returned by _store_emails_in_redis

        Returns:
            List of email dicts, or None if key expired/missing
        """
        from app import redis_client

        if not redis_client or not redis_key:
            return None

        try:
            data = redis_client.get(redis_key)
            if data:
                emails = json.loads(data)
                logger.debug(
                    f"Retrieved {len(emails)} emails from Redis: {redis_key}"
                )
                return emails
            else:
                logger.warning(f"Redis key expired or missing: {redis_key}")
                return None

        except Exception as e:
            logger.error(f"Failed to retrieve emails from Redis: {e}")
            return None

    def delete_emails_from_redis(self, redis_key: str) -> bool:
        """
        Clean up email data from Redis after processing.

        Args:
            redis_key: Redis key to delete

        Returns:
            True if deleted successfully
        """
        from app import redis_client

        if not redis_client or not redis_key:
            return False

        try:
            redis_client.delete(redis_key)
            logger.debug(f"Deleted email data from Redis: {redis_key}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete from Redis: {e}")
            return False

    # ========================================================================
    # Tenant Roles (cached)
    # ========================================================================

    def _get_tenant_roles_cached(self, tenant_id: int) -> list[str]:
        """
        Get tenant roles with Redis caching.

        Phase 3: Caches tenant roles for 1 hour to reduce DB queries.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of role names
        """
        from app import redis_client

        cache_key = f"tenant_roles:{tenant_id}"

        # Try to get from cache
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for tenant roles: {tenant_id}")
                    return json.loads(cached) if isinstance(cached, str) else cached
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # Cache miss — compute roles
        roles = self._get_tenant_roles(tenant_id)

        # Store in cache
        if redis_client and roles:
            try:
                redis_client.set(cache_key, json.dumps(roles), ex=TENANT_ROLES_CACHE_TTL)
                logger.debug(f"Cached {len(roles)} roles for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

        return roles

    @staticmethod
    def invalidate_tenant_roles_cache(tenant_id: int) -> bool:
        """
        Invalidate tenant roles cache when candidates/roles change.

        Should be called when:
        - Candidate preferred_roles are updated
        - CandidateGlobalRole associations change
        - GlobalRole is updated

        Args:
            tenant_id: Tenant ID

        Returns:
            True if cache was invalidated
        """
        from app import redis_client

        if not redis_client:
            return False

        try:
            cache_key = f"tenant_roles:{tenant_id}"
            redis_client.delete(cache_key)
            logger.info(f"Invalidated roles cache for tenant {tenant_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to invalidate roles cache: {e}")
            return False

    # ========================================================================
    # Gmail Fetch (with History API + Batch API)
    # ========================================================================

    def _fetch_gmail_emails_with_history(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> tuple[list[dict], Optional[str]]:
        """
        Fetch Gmail emails using incremental History API when possible.

        Phase 5: Uses Gmail History API for incremental sync, falling back
        to full sync when history ID is not available or expired.

        Args:
            access_token: Valid Gmail access token
            integration: UserEmailIntegration object

        Returns:
            Tuple of (emails list, new history_id for next sync)
        """
        logger.info(f"Fetching Gmail emails for integration_id={integration.id}")

        service = gmail_oauth_service.build_gmail_service(access_token)

        try:
            profile = service.users().getProfile(userId="me").execute()
            latest_history_id = profile.get("historyId")
            logger.debug(
                f"Gmail profile fetched: email={profile.get('emailAddress')}, "
                f"historyId={latest_history_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to get Gmail profile: {e}")
            latest_history_id = None

        if integration.gmail_history_id and latest_history_id:
            try:
                logger.info(
                    f"Attempting incremental sync from "
                    f"historyId={integration.gmail_history_id}"
                )
                emails = self._fetch_gmail_emails_incremental(
                    service, integration.gmail_history_id
                )
                logger.info(
                    f"Incremental sync successful: fetched {len(emails)} new emails"
                )
                return emails, latest_history_id
            except Exception as e:
                logger.info(
                    f"Incremental sync failed (will fallback to full): {e}"
                )
        else:
            logger.info("No history ID available, performing full sync")

        emails = self._fetch_gmail_emails_batch(access_token, integration)
        logger.info(f"Full sync complete: fetched {len(emails)} emails")
        return emails, latest_history_id

    @gmail_circuit_breaker
    def _fetch_gmail_emails_incremental(
        self,
        service,
        start_history_id: str,
    ) -> list[dict]:
        """
        Fetch only new emails since last sync using History API.

        Phase 5: Incremental sync reduces API calls and data transfer.

        Args:
            service: Gmail API service
            start_history_id: History ID from last sync

        Returns:
            List of new email dictionaries
        """
        response = service.users().history().list(
            userId="me",
            startHistoryId=start_history_id,
            historyTypes=["messageAdded"],
            maxResults=100,
        ).execute()

        # Extract message IDs from history
        message_ids = set()
        for history in response.get("history", []):
            for msg_added in history.get("messagesAdded", []):
                message_ids.add(msg_added["message"]["id"])

        if not message_ids:
            return []

        return self._fetch_gmail_messages_batch(service, list(message_ids))

    @gmail_circuit_breaker
    def _fetch_gmail_emails_batch(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> list[dict]:
        """
        Fetch emails from Gmail using Batch API for efficiency.

        Time-based fetching strategy:
        - First scan (no last_synced_at): Fetch ALL emails from past 2 days
        - Subsequent syncs: Fetch ALL emails since last_synced_at
        - No count limit — fetches all matching emails using pagination

        Args:
            access_token: Valid Gmail access token
            integration: UserEmailIntegration object

        Returns:
            List of email dictionaries
        """
        service = gmail_oauth_service.build_gmail_service(access_token)

        # Determine time boundary based on sync state
        is_initial_sync = integration.last_synced_at is None

        if is_initial_sync:
            after_date = datetime.now(timezone.utc) - timedelta(
                days=self.initial_lookback_days
            )
            logger.info(
                f"Initial sync for integration {integration.id}: fetching emails "
                f"from past {self.initial_lookback_days} days"
            )
        else:
            # Subsequent syncs: fetch since last sync (with 15 min buffer)
            after_date = integration.last_synced_at - timedelta(minutes=15)
            logger.info(
                f"Incremental sync for integration {integration.id}: "
                f"fetching emails since {after_date.isoformat()}"
            )

        # Build Gmail query with date filter
        after_timestamp = int(after_date.timestamp())
        query = f"after:{after_timestamp}"

        logger.info(
            f"Gmail query: '{query}' "
            f"(after_date={after_date.strftime('%Y-%m-%d %H:%M:%S UTC')})"
        )

        # Fetch ALL messages using pagination
        all_message_ids = []
        page_token = None

        while True:
            request_params = {
                "userId": "me",
                "q": query,
                "maxResults": self.max_emails_per_page,
                "includeSpamTrash": False,
            }
            if page_token:
                request_params["pageToken"] = page_token

            results = service.users().messages().list(**request_params).execute()

            messages = results.get("messages", [])
            all_message_ids.extend([msg["id"] for msg in messages])

            logger.info(
                f"Gmail returned {len(messages)} messages in this page, "
                f"total so far: {len(all_message_ids)}"
            )

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        logger.info(
            f"Found {len(all_message_ids)} total emails since "
            f"{after_date.strftime('%Y-%m-%d %H:%M')}"
        )

        if not all_message_ids:
            return []

        return self._fetch_gmail_messages_batch(service, all_message_ids)

    @gmail_circuit_breaker
    def _fetch_gmail_messages_batch(
        self,
        service,
        message_ids: list[str],
    ) -> list[dict]:
        """
        Fetch multiple Gmail messages using batch API with chunking.

        Phase 2: Batch requests reduce N API calls to ceil(N/GMAIL_BATCH_SIZE).
        Phase 7: Protected by distributed circuit breaker.

        Args:
            service: Gmail API service
            message_ids: List of message IDs to fetch

        Returns:
            List of parsed email dictionaries
        """
        from googleapiclient.http import BatchHttpRequest

        all_emails = []
        all_errors = []
        total_messages = len(message_ids)
        total_chunks = (total_messages + GMAIL_BATCH_SIZE - 1) // GMAIL_BATCH_SIZE

        logger.info(
            f"Fetching {total_messages} messages in {total_chunks} batch(es) "
            f"of up to {GMAIL_BATCH_SIZE}"
        )

        for chunk_index in range(0, total_messages, GMAIL_BATCH_SIZE):
            chunk = message_ids[chunk_index:chunk_index + GMAIL_BATCH_SIZE]
            chunk_num = (chunk_index // GMAIL_BATCH_SIZE) + 1
            chunk_emails = []
            chunk_errors = []

            def make_callback(emails_list, errors_list):
                """Create a callback closure for this chunk."""
                def handle_message(request_id, response, exception):
                    if exception:
                        errors_list.append({"id": request_id, "error": str(exception)})
                        return
                    try:
                        email = self._parse_gmail_message(response)
                        if email:
                            emails_list.append(email)
                    except Exception as e:
                        errors_list.append({"id": request_id, "error": str(e)})
                return handle_message

            batch = service.new_batch_http_request(
                callback=make_callback(chunk_emails, chunk_errors)
            )

            for msg_id in chunk:
                batch.add(
                    service.users().messages().get(
                        userId="me",
                        id=msg_id,
                        format="full",
                    ),
                    request_id=msg_id,
                )

            batch.execute()

            all_emails.extend(chunk_emails)
            all_errors.extend(chunk_errors)

            logger.info(
                f"Batch {chunk_num}/{total_chunks}: fetched {len(chunk_emails)} emails "
                f"from {len(chunk)} IDs ({len(chunk_errors)} errors)"
            )

        if all_errors:
            logger.warning(
                f"Batch fetch had {len(all_errors)} total errors: {all_errors[:5]}"
            )

        logger.info(
            f"Batch fetched {len(all_emails)} emails from {total_messages} IDs total"
        )
        return all_emails

    def _parse_gmail_message(self, message: dict) -> Optional[dict]:
        """Parse Gmail message into email dictionary."""
        try:
            headers = {
                h["name"].lower(): h["value"]
                for h in message.get("payload", {}).get("headers", [])
            }
            body = self._extract_gmail_body(message.get("payload", {}))

            return {
                "id": message["id"],
                "thread_id": message.get("threadId"),
                "subject": headers.get("subject", ""),
                "sender": headers.get("from", ""),
                "body": body,
                "received_at": self._parse_gmail_date(headers.get("date", "")),
            }
        except Exception as e:
            logger.warning(f"Failed to parse Gmail message {message.get('id')}: {e}")
            return None

    def _extract_gmail_body(self, payload: dict) -> str:
        """Extract body text from Gmail message payload."""
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8", errors="ignore")
                        break
                elif mime_type == "text/html":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8", errors="ignore")
                        body = re.sub(r"<[^>]+>", " ", body)
                        body = re.sub(r"\s+", " ", body)
                elif mime_type.startswith("multipart/"):
                    body = self._extract_gmail_body(part)
                    if body:
                        break

        return body.strip()[:10000]  # Limit body size

    def _parse_gmail_date(self, date_str: str) -> Optional[datetime]:
        """Parse Gmail date header."""
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return None

    # ========================================================================
    # Outlook Fetch
    # ========================================================================

    @outlook_circuit_breaker
    def _fetch_outlook_emails(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> list[dict]:
        """
        Fetch Outlook emails using delta query for incremental sync.

        Args:
            access_token: Valid Outlook access token
            integration: UserEmailIntegration object

        Returns:
            List of email dictionaries
        """
        logger.info(f"Fetching Outlook emails for integration_id={integration.id}")

        all_emails = []

        if integration.outlook_delta_link:
            logger.info("Attempting delta sync with saved delta link")
            try:
                messages, new_delta_link = outlook_oauth_service.get_messages_delta(
                    access_token=access_token,
                    delta_link=integration.outlook_delta_link,
                )

                logger.info(f"Delta sync successful: fetched {len(messages)} messages")

                for msg in messages:
                    try:
                        body = ""
                        if msg.get("body"):
                            body = msg["body"].get("content", "")
                            if msg["body"].get("contentType") == "html":
                                body = re.sub(r"<[^>]+>", " ", body)
                                body = re.sub(r"\s+", " ", body)

                        sender = ""
                        if msg.get("from", {}).get("emailAddress"):
                            sender_info = msg["from"]["emailAddress"]
                            sender = (
                                f"{sender_info.get('name', '')} "
                                f"<{sender_info.get('address', '')}>"
                            )

                        all_emails.append({
                            "id": msg["id"],
                            "thread_id": msg.get("conversationId"),
                            "subject": msg.get("subject", ""),
                            "sender": sender,
                            "body": body.strip()[:10000],
                            "received_at": (
                                datetime.fromisoformat(
                                    msg["receivedDateTime"].replace("Z", "+00:00")
                                )
                                if msg.get("receivedDateTime")
                                else None
                            ),
                        })

                    except Exception as e:
                        logger.warning(f"Failed to process Outlook message: {e}")
                        continue

                integration.outlook_delta_link = new_delta_link
                db.session.commit()

                logger.info(
                    f"Outlook delta sync complete: {len(all_emails)} emails processed"
                )
                return all_emails

            except Exception as e:
                logger.warning(
                    f"Delta query failed (will fallback to time-based): {e}"
                )
                integration.outlook_delta_link = None
                db.session.commit()

        # Fallback to time-based sync
        logger.info(
            f"Performing time-based sync (lookback: {self.initial_lookback_days} days)"
        )
        after_date = datetime.now(timezone.utc) - timedelta(
            days=self.initial_lookback_days
        )
        filter_query = (
            f"receivedDateTime ge {after_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )

        all_emails = []
        next_link = None
        is_first_request = True
        page_count = 0

        while True:
            page_count += 1
            logger.debug(f"Fetching Outlook page {page_count}")

            if is_first_request:
                messages, next_link = outlook_oauth_service.get_messages(
                    access_token=access_token,
                    top=self.max_emails_per_page,
                    filter_query=filter_query,
                )
                is_first_request = False
            else:
                if not next_link:
                    break
                messages, next_link = outlook_oauth_service.get_messages_from_url(
                    access_token=access_token,
                    url=next_link,
                )

            if not messages:
                break

            for msg in messages:
                try:
                    body = ""
                    if msg.get("body"):
                        body = msg["body"].get("content", "")
                        if msg["body"].get("contentType") == "html":
                            body = re.sub(r"<[^>]+>", " ", body)
                            body = re.sub(r"\s+", " ", body)

                    sender = ""
                    if msg.get("from", {}).get("emailAddress"):
                        sender_info = msg["from"]["emailAddress"]
                        sender = (
                            f"{sender_info.get('name', '')} "
                            f"<{sender_info.get('address', '')}>"
                        )

                    all_emails.append({
                        "id": msg["id"],
                        "thread_id": msg.get("conversationId"),
                        "subject": msg.get("subject", ""),
                        "sender": sender,
                        "body": body.strip()[:10000],
                        "received_at": (
                            datetime.fromisoformat(
                                msg["receivedDateTime"].replace("Z", "+00:00")
                            )
                            if msg.get("receivedDateTime")
                            else None
                        ),
                    })

                except Exception as e:
                    logger.warning(f"Failed to process Outlook message: {e}")
                    continue

            if not next_link:
                break

        logger.info(
            f"Outlook time-based sync complete: {len(all_emails)} total emails, "
            f"{page_count} pages"
        )
        return all_emails

    # ========================================================================
    # Role Normalization & Matching
    # ========================================================================

    def _normalize_role(self, role: str) -> str:
        """
        Normalize a role string by extracting the base role name.

        Examples:
        - "senior python developer - backend" -> "python developer"
        - "devops engineer with terraform" -> "devops engineer"
        - "sr. devops engineer" -> "devops engineer"

        Args:
            role: Original role string

        Returns:
            Normalized base role name
        """
        role_lower = role.lower().strip()

        # Remove common prefixes (seniority indicators)
        prefixes_to_remove = [
            r'^sr\.?\s+',
            r'^senior\s+',
            r'^junior\s+',
            r'^lead\s+',
            r'^entry-level\s+',
            r'^associate\s+',
            r'^lead/senior\s+',
        ]

        for prefix_pattern in prefixes_to_remove:
            role_lower = re.sub(prefix_pattern, '', role_lower)

        # Remove everything after common separators
        separators = [
            r'\s+with\s+',
            r'\s+w/d\s+',
            r'\s+–\s+',
            r'\s+-\s+',
            r'\s+\(',
            r'\s+/',
        ]

        for separator in separators:
            parts = re.split(separator, role_lower, maxsplit=1)
            if len(parts) > 1:
                role_lower = parts[0].strip()
                break

        # Remove trailing punctuation
        role_lower = re.sub(r'[.,;:\-–]+$', '', role_lower).strip()

        return role_lower

    def _get_tenant_roles(self, tenant_id: int) -> list[str]:
        """
        Get all roles to search for in this tenant with normalization.

        Sources:
        1. Candidate.preferred_roles from all candidates in tenant
        2. GlobalRole.name for roles linked to candidates in tenant
        3. GlobalRole.aliases for additional role variations

        Args:
            tenant_id: Tenant ID

        Returns:
            List of normalized role names (lowercase, unique)
        """
        roles = set()

        logger.debug(f"Fetching roles for tenant_id={tenant_id}")

        # Source 1: Candidate preferred_roles (ARRAY column)
        stmt = select(func.unnest(Candidate.preferred_roles)).where(
            Candidate.tenant_id == tenant_id,
            Candidate.preferred_roles.isnot(None),
        ).distinct()

        candidate_roles = list(db.session.scalars(stmt).all())
        logger.debug(f"Found {len(candidate_roles)} candidate preferred_roles")

        for role in candidate_roles:
            if role:
                normalized = self._normalize_role(role)
                if normalized:
                    roles.add(normalized)

        # Source 2: GlobalRoles linked to candidates in this tenant
        stmt = select(GlobalRole.name).join(
            CandidateGlobalRole,
            CandidateGlobalRole.global_role_id == GlobalRole.id
        ).join(
            Candidate,
            Candidate.id == CandidateGlobalRole.candidate_id
        ).where(
            Candidate.tenant_id == tenant_id,
        ).distinct()

        global_roles = list(db.session.scalars(stmt).all())
        logger.debug(f"Found {len(global_roles)} global roles")

        for role in global_roles:
            if role:
                normalized = self._normalize_role(role)
                if normalized:
                    roles.add(normalized)

        # Source 3: GlobalRole aliases
        stmt = select(func.unnest(GlobalRole.aliases)).join(
            CandidateGlobalRole,
            CandidateGlobalRole.global_role_id == GlobalRole.id
        ).join(
            Candidate,
            Candidate.id == CandidateGlobalRole.candidate_id
        ).where(
            Candidate.tenant_id == tenant_id,
            GlobalRole.aliases.isnot(None),
        ).distinct()

        aliases = list(db.session.scalars(stmt).all())
        logger.debug(f"Found {len(aliases)} global role aliases")

        for alias in aliases:
            if alias:
                normalized = self._normalize_role(alias)
                if normalized:
                    roles.add(normalized)

        final_roles = sorted(list(roles))
        logger.info(
            f"Tenant {tenant_id}: Extracted {len(final_roles)} unique normalized roles"
        )

        return final_roles

    def _tokenized_role_match(self, subject: str, role: str) -> bool:
        """
        Check if a role matches the subject using tokenized matching.

        Algorithm:
        1. Tokenize role into significant words (skip common stopwords)
        2. Check if ALL role tokens appear in subject
        3. Must maintain rough order (prevents false positives)

        Args:
            subject: Email subject line (lowercase)
            role: Normalized role name (lowercase)

        Returns:
            True if role matches subject
        """
        stopwords = {
            'a', 'an', 'and', 'the', 'for', 'with', 'in',
            'on', 'at', 'to', 'of', 'is', 'are',
        }

        role_tokens = [
            token for token in role.split()
            if token not in stopwords and len(token) > 1
        ]

        if not role_tokens:
            return False

        subject_lower = subject.lower()

        last_found_pos = -1
        for token in role_tokens:
            pos = subject_lower.find(token, last_found_pos + 1)
            if pos == -1:
                return False
            last_found_pos = pos

        return True

    def _matches_job_criteria(
        self,
        subject: str,
        sender: str,
        preferred_roles: list[str],
    ) -> tuple[bool, Optional[str]]:
        """
        Check if email subject matches job criteria using tokenized role matching.

        Args:
            subject: Email subject line
            sender: Email sender address
            preferred_roles: List of normalized roles to match

        Returns:
            Tuple of (matches: bool, reason: str)
        """
        subject_lower = subject.lower()
        sender_lower = sender.lower()

        for blocked in self.BLOCKED_SENDERS:
            if blocked in sender_lower:
                return False, f"blocked_sender:{blocked}"

        for pattern in self.BLOCKED_SUBJECT_PATTERNS:
            if re.search(pattern, subject_lower, re.IGNORECASE):
                return False, f"blocked_subject:{pattern}"

        for role in preferred_roles:
            if self._tokenized_role_match(subject_lower, role):
                return True, f"role_match:{role}"

        return False, "no_role_match"

    # ========================================================================
    # Legacy Methods (kept for backward compatibility)
    # ========================================================================

    def _is_email_processed(self, integration_id: int, email_id: str) -> bool:
        """
        Check if email has already been processed.
        DEPRECATED: Use _batch_check_processed() for batch efficiency.
        """
        stmt = select(ProcessedEmail).where(
            ProcessedEmail.integration_id == integration_id,
            ProcessedEmail.email_message_id == email_id,
        )
        return db.session.scalar(stmt) is not None

    def sync_integration(self, integration: UserEmailIntegration) -> dict:
        """
        DEPRECATED: Use fetch_and_filter_emails() instead.
        Kept for backward compatibility with manual sync triggers.
        """
        return self.fetch_and_filter_emails(integration.id)


# Singleton instance
email_sync_service = EmailSyncService()
