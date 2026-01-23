"""Email Sync Service.

Handles fetching emails from connected accounts, filtering for job-related emails,
and coordinating with the parser service.

SCALABILITY IMPROVEMENTS (Phases 1-7):
- Phase 2: Gmail Batch API for reduced API calls
- Phase 3: Redis caching for tenant roles
- Phase 5: Incremental sync using Gmail History API
- Phase 7: Circuit breakers for fault tolerance

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


class EmailSyncService:
    """Service for syncing and filtering job-related emails.
    
    Uses ROLE-BASED filtering only:
    - Matches emails where subject contains exact role names from tenant
    - No generic pattern/keyword matching (reduces AI processing cost)
    
    Scalability features:
    - Redis caching for tenant roles (Phase 3)
    - Gmail Batch API for reduced API calls (Phase 2)
    - Incremental sync using Gmail History API (Phase 5)
    - Circuit breakers for external API fault tolerance (Phase 7)
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
        self.initial_lookback_days = settings.email_sync_initial_lookback_days  # 2 days for first scan
        self.max_emails_per_page = settings.email_sync_max_emails_per_page  # Gmail pagination size
    
    def update_sync_timestamp(
        self, 
        integration_id: int, 
        new_history_id: Optional[str] = None
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
    
    def sync_integration(self, integration: UserEmailIntegration) -> dict:
        """
        Sync emails for a single integration.
        
        NOTE: This method does NOT update last_synced_at. Call update_sync_timestamp()
        after the Inngest workflow completes successfully.
        
        Args:
            integration: UserEmailIntegration object
            
        Returns:
            Dictionary with sync results
        """
        if not integration.is_active:
            logger.info(f"Skipping inactive integration {integration.id}")
            return {"skipped": True, "reason": "inactive"}
        
        try:
            # Get preferred roles for filtering FIRST - skip if none configured
            # Phase 3: Uses Redis cache for performance
            preferred_roles = self._get_tenant_roles_cached(integration.tenant_id)
            
            if not preferred_roles:
                logger.info(f"Skipping integration {integration.id}: no roles configured in tenant")
                return {
                    "skipped": True, 
                    "reason": "no_roles_configured",
                    "message": "No candidate preferred roles or global roles found in tenant"
                }
            
            logger.info(f"Integration {integration.id}: Found {len(preferred_roles)} roles to match: {preferred_roles[:5]}...")
            
            # Get valid access token
            access_token = email_integration_service.get_valid_access_token(integration)
            
            # Fetch emails based on provider (with circuit breaker protection)
            # Phase 2: Gmail uses batch API, Phase 5: Gmail uses incremental sync
            if integration.provider == "gmail":
                emails, new_history_id = self._fetch_gmail_emails_with_history(access_token, integration)
            else:
                emails = self._fetch_outlook_emails_safe(access_token, integration)
                new_history_id = None
            
            # Filter and process emails
            results = {
                "fetched": len(emails),
                "matched": 0,
                "skipped_count": 0,  # Renamed from "skipped" to avoid confusion with boolean
                "already_processed": 0,
                "errors": 0,
                "emails_to_process": [],
                "roles_searched": preferred_roles,
            }
            
            for email in emails:
                email_id = email.get("id") or email.get("message_id")
                
                # Check if already processed
                if self._is_email_processed(integration.id, email_id):
                    results["already_processed"] += 1
                    continue
                
                # Check if matches job criteria (ROLE-BASED only)
                subject = email.get("subject", "")
                sender = email.get("sender", "")
                matches, match_reason = self._matches_job_criteria(subject, sender, preferred_roles)
                
                if not matches:
                    # Log skipped emails for debugging
                    logger.debug(f"Skipped email: subject='{subject[:60]}...', reason={match_reason}")
                    
                    # Record as skipped
                    self._record_skipped_email(
                        integration=integration,
                        email_id=email_id,
                        subject=subject,
                        sender=email.get("sender", ""),
                        reason=match_reason or "no_match",
                    )
                    results["skipped_count"] += 1
                    continue
                
                logger.info(f"Matched email: subject='{subject[:60]}...', reason={match_reason}")
                
                # Add to processing queue
                received_at = email.get("received_at")
                if isinstance(received_at, datetime):
                    received_at = received_at.isoformat()
                
                results["emails_to_process"].append({
                    "email_id": email_id,
                    "thread_id": email.get("thread_id"),
                    "subject": subject,
                    "sender": email.get("sender", ""),
                    "body": email.get("body", ""),
                    "received_at": received_at,
                    "match_reason": match_reason,
                })
                results["matched"] += 1
            
            # NOTE: Don't update last_synced_at here!
            # It should be updated AFTER the Inngest workflow completes successfully.
            # This ensures idempotency - if the Inngest step retries, we get the same emails.
            
            # Store the new history ID in results for later update
            if new_history_id and integration.provider == "gmail":
                results["new_history_id"] = new_history_id
            
            # Clear any previous errors (but don't commit yet)
            integration.consecutive_failures = 0
            integration.last_error = None
            db.session.commit()
            
            logger.info(
                f"Synced integration {integration.id}: "
                f"fetched={results['fetched']}, matched={results['matched']}, "
                f"skipped={results['skipped_count']}, already_processed={results['already_processed']}"
            )
            
            return results
        
        # Phase 7: Circuit breaker error handling
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker open for integration {integration.id}: {e}")
            return {"error": str(e), "circuit_breaker_open": True}
            
        except Exception as e:
            logger.error(f"Sync failed for integration {integration.id}: {e}")
            integration.last_error = str(e)
            integration.consecutive_failures = (integration.consecutive_failures or 0) + 1
            
            if integration.consecutive_failures >= 3:
                integration.is_active = False
                logger.warning(f"Deactivated integration {integration.id} due to repeated failures")
            
            db.session.commit()
            return {"error": str(e)}
    
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
                    # Redis returns string, need to deserialize JSON
                    return json.loads(cached) if isinstance(cached, str) else cached
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Cache miss - compute roles
        roles = self._get_tenant_roles(tenant_id)
        
        # Store in cache - serialize list to JSON
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
        service = gmail_oauth_service.build_gmail_service(access_token)
        
        # Get current profile to obtain latest history ID
        try:
            profile = service.users().getProfile(userId="me").execute()
            latest_history_id = profile.get("historyId")
        except Exception as e:
            logger.warning(f"Failed to get Gmail profile: {e}")
            latest_history_id = None
        
        # Try incremental sync if we have a history ID
        if integration.gmail_history_id and latest_history_id:
            try:
                emails = self._fetch_gmail_emails_incremental(
                    service, integration.gmail_history_id
                )
                logger.info(f"Incremental sync: fetched {len(emails)} new emails")
                return emails, latest_history_id
            except Exception as e:
                # History ID expired or invalid, fall back to full sync
                logger.info(f"Incremental sync failed, falling back to full: {e}")
        
        # Full sync with batch API
        emails = self._fetch_gmail_emails_batch(access_token, integration)
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
        # Fetch history changes
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
        
        # Fetch full message details using batch API
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
        - No count limit - fetches all matching emails using pagination
        
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
            # First scan: Look back 2 days
            after_date = datetime.now(timezone.utc) - timedelta(days=self.initial_lookback_days)
            logger.info(f"Initial sync for integration {integration.id}: fetching emails from past {self.initial_lookback_days} days")
        else:
            # Subsequent syncs: Fetch since last sync time (with 15 min buffer for safety)
            after_date = integration.last_synced_at - timedelta(minutes=15)
            logger.info(f"Incremental sync for integration {integration.id}: fetching emails since {after_date.isoformat()}")
        
        # Build Gmail query with date filter
        # Gmail uses epoch seconds for precise time filtering
        after_timestamp = int(after_date.timestamp())
        query = f"after:{after_timestamp}"
        
        logger.info(f"Gmail query: '{query}' (after_date={after_date.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        
        # Fetch ALL messages using pagination (no maxResults limit on total)
        # Note: By default, Gmail API searches all mail (not just inbox)
        all_message_ids = []
        page_token = None
        
        while True:
            # Fetch a page of message IDs
            # Include all labels to search everywhere (inbox, promotions, updates, etc.)
            request_params = {
                "userId": "me",
                "q": query,
                "maxResults": self.max_emails_per_page,  # Page size, not total limit
                "includeSpamTrash": False,  # Exclude spam/trash
            }
            if page_token:
                request_params["pageToken"] = page_token
            
            results = service.users().messages().list(**request_params).execute()
            
            messages = results.get("messages", [])
            all_message_ids.extend([msg["id"] for msg in messages])
            
            logger.info(f"Gmail returned {len(messages)} messages in this page, total so far: {len(all_message_ids)}")
            
            # Check for more pages
            page_token = results.get("nextPageToken")
            if not page_token:
                break
            
            logger.info(f"More pages available, continuing...")
        
        logger.info(f"Found {len(all_message_ids)} total emails since {after_date.strftime('%Y-%m-%d %H:%M')}")
        
        if not all_message_ids:
            return []
        
        # Fetch all messages in batch
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
        Phase 7: Protected by circuit breaker for fault tolerance.
        Phase 8: Chunked batches to avoid Google's 1000 request limit.
        
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
        
        logger.info(f"Fetching {total_messages} messages in {total_chunks} batch(es) of up to {GMAIL_BATCH_SIZE}")
        
        # Process message_ids in chunks to avoid Google's 1000 request limit
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
            
            # Create batch request for this chunk
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
            
            # Execute this chunk's batch request
            batch.execute()
            
            all_emails.extend(chunk_emails)
            all_errors.extend(chunk_errors)
            
            logger.info(
                f"Batch {chunk_num}/{total_chunks}: fetched {len(chunk_emails)} emails "
                f"from {len(chunk)} IDs ({len(chunk_errors)} errors)"
            )
        
        if all_errors:
            logger.warning(f"Batch fetch had {len(all_errors)} total errors: {all_errors[:5]}")
        
        logger.info(f"Batch fetched {len(all_emails)} emails from {total_messages} IDs total")
        return all_emails
    
    def _parse_gmail_message(self, message: dict) -> Optional[dict]:
        """Parse Gmail message into email dictionary."""
        try:
            headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
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
    
    def _fetch_gmail_emails(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> list[dict]:
        """
        DEPRECATED: Legacy N+1 fetch method. Use _fetch_gmail_emails_batch instead.
        Kept for backwards compatibility.
        
        Args:
            access_token: Valid Gmail access token
            integration: UserEmailIntegration object
            
        Returns:
            List of email dictionaries
        """
        return self._fetch_gmail_emails_batch(access_token, integration)
    
    def _extract_gmail_body(self, payload: dict) -> str:
        """Extract body text from Gmail message payload."""
        body = ""
        
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        break
                elif mime_type == "text/html":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        # Strip HTML tags
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
    
    @outlook_circuit_breaker
    def _fetch_outlook_emails_safe(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> list[dict]:
        """
        Fetch emails from Outlook with circuit breaker protection.
        
        Phase 7: Wraps Outlook fetch with circuit breaker for fault tolerance.
        
        Args:
            access_token: Valid Outlook access token
            integration: UserEmailIntegration object
            
        Returns:
            List of email dictionaries
        """
        return self._fetch_outlook_emails(access_token, integration)
    
    def _fetch_outlook_emails(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> list[dict]:
        """
        Fetch emails from Outlook using delta query for incremental sync (Phase 9A).
        
        Phase 9A: Delta Query Strategy
        - Uses Microsoft Graph delta query to track changes since last sync
        - Avoids full mailbox scans by fetching only new/changed messages
        - Stores deltaLink in integration.outlook_delta_link for next sync
        
        Fallback Strategy:
        - First sync (no delta_link): Use delta query initial sync
        - Delta link expired: Fall back to time-based filter for past 2 days
        
        Args:
            access_token: Valid Outlook access token
            integration: UserEmailIntegration object
            
        Returns:
            List of email dictionaries
        """
        all_emails = []
        new_delta_link: Optional[str] = None
        
        has_delta_link = bool(integration.outlook_delta_link)
        
        if has_delta_link:
            logger.info(f"Incremental Outlook delta sync for integration {integration.id}")
        else:
            logger.info(f"Initial Outlook delta sync for integration {integration.id}")
        
        try:
            next_link: Optional[str] = None
            is_first_request = True
            
            while True:
                if is_first_request:
                    messages, next_link, new_delta_link = outlook_oauth_service.get_messages_delta(
                        access_token=access_token,
                        folder="inbox",
                        delta_link=integration.outlook_delta_link,
                    )
                    is_first_request = False
                else:
                    messages, next_link, new_delta_link = outlook_oauth_service.get_messages_delta(
                        access_token=access_token,
                        folder="inbox",
                        delta_link=next_link,
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
                            sender = f"{sender_info.get('name', '')} <{sender_info.get('address', '')}>"
                        
                        all_emails.append({
                            "id": msg["id"],
                            "thread_id": msg.get("conversationId"),
                            "subject": msg.get("subject", ""),
                            "sender": sender,
                            "body": body.strip()[:10000],
                            "received_at": datetime.fromisoformat(msg["receivedDateTime"].replace("Z", "+00:00")) if msg.get("receivedDateTime") else None,
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to process Outlook message: {e}")
                        continue
                
                logger.debug(f"Fetched {len(all_emails)} Outlook emails so far, continuing...")
                
                if not next_link:
                    break
            
            if new_delta_link:
                integration.outlook_delta_link = new_delta_link
                integration.last_batch_processed_at = datetime.now(timezone.utc)
                db.session.commit()
                logger.info(f"Stored new Outlook delta link for integration {integration.id}")
            
        except Exception as e:
            logger.warning(f"Delta query failed for integration {integration.id}: {e}. Falling back to time-based sync.")
            
            integration.outlook_delta_link = None
            db.session.commit()
            
            after_date = datetime.now(timezone.utc) - timedelta(days=self.initial_lookback_days)
            filter_query = f"receivedDateTime ge {after_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            
            all_emails = []
            next_link = None
            is_first_request = True
            
            while True:
                if is_first_request:
                    messages, next_link = outlook_oauth_service.get_messages(
                        access_token=access_token,
                        top=self.max_emails_per_page,
                        filter_query=filter_query,
                    )
                    is_first_request = False
                else:
                    messages, next_link = outlook_oauth_service.get_messages_from_url(
                        access_token=access_token,
                        url=next_link,  # type: ignore
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
                            sender = f"{sender_info.get('name', '')} <{sender_info.get('address', '')}>"
                        
                        all_emails.append({
                            "id": msg["id"],
                            "thread_id": msg.get("conversationId"),
                            "subject": msg.get("subject", ""),
                            "sender": sender,
                            "body": body.strip()[:10000],
                            "received_at": datetime.fromisoformat(msg["receivedDateTime"].replace("Z", "+00:00")) if msg.get("receivedDateTime") else None,
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to process Outlook message: {e}")
                        continue
                
                if not next_link:
                    break
        
        logger.info(f"Found {len(all_emails)} total Outlook emails")
        return all_emails
    
    def _get_tenant_roles(self, tenant_id: int) -> list[str]:
        """
        Get all roles to search for in this tenant.
        
        Sources:
        1. Candidate.preferred_roles from all candidates in tenant
        2. GlobalRole.name for roles linked to candidates in tenant
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of normalized role names (lowercase, unique)
        """
        roles = set()
        
        # Source 1: Candidate preferred_roles (ARRAY column)
        stmt = select(func.unnest(Candidate.preferred_roles)).where(
            Candidate.tenant_id == tenant_id,
            Candidate.preferred_roles.isnot(None),
        ).distinct()
        
        candidate_roles = list(db.session.scalars(stmt).all())
        for role in candidate_roles:
            if role:
                roles.add(role.strip().lower())
        
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
        for role in global_roles:
            if role:
                roles.add(role.strip().lower())
        
        # Also add GlobalRole aliases
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
        for alias in aliases:
            if alias:
                roles.add(alias.strip().lower())
        
        return list(roles)
    
    def _matches_job_criteria(
        self,
        subject: str,
        sender: str,
        preferred_roles: list[str],
    ) -> tuple[bool, Optional[str]]:
        """
        Check if email subject matches job criteria using ONLY role-based filtering.
        
        This method implements strict role-based matching:
        - Only emails with subject containing exact role names (case-insensitive) are matched
        - No generic patterns or keywords - prevents fetching unrelated emails
        - Blocked senders and subjects are still filtered out
        
        Args:
            subject: Email subject line
            sender: Email sender address
            preferred_roles: List of preferred roles to match (from tenant candidates + GlobalRoles)
            
        Returns:
            Tuple of (matches, reason)
        """
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        
        # First, check if sender is blocked (marketing, newsletters, etc.)
        for blocked in self.BLOCKED_SENDERS:
            if blocked in sender_lower:
                return False, f"blocked_sender:{blocked}"
        
        # Check if subject matches blocked patterns (automated emails)
        for pattern in self.BLOCKED_SUBJECT_PATTERNS:
            if re.search(pattern, subject_lower, re.IGNORECASE):
                return False, f"blocked_subject:{pattern}"
        
        # ONLY match if subject contains one of the preferred roles (exact match)
        # No generic patterns or keywords - this ensures we only fetch relevant jobs
        for role in preferred_roles:
            if role and role in subject_lower:
                return True, f"role_match:{role}"
        
        # If no role matches, reject the email
        return False, "no_role_match"
    
    def _is_email_processed(self, integration_id: int, email_id: str) -> bool:
        """Check if email has already been processed."""
        stmt = select(ProcessedEmail).where(
            ProcessedEmail.integration_id == integration_id,
            ProcessedEmail.email_message_id == email_id,
        )
        return db.session.scalar(stmt) is not None
    
    def _record_skipped_email(
        self,
        integration: UserEmailIntegration,
        email_id: str,
        subject: str,
        sender: str,
        reason: str,
    ) -> None:
        """Record a skipped email to prevent reprocessing."""
        processed = ProcessedEmail(
            integration_id=integration.id,
            tenant_id=integration.tenant_id,
            email_message_id=email_id,
            email_subject=subject[:500] if subject else None,
            email_sender=sender[:255] if sender else None,
            processing_result="skipped",
            skip_reason=reason,
        )
        db.session.add(processed)
        # Don't commit here - let caller handle transaction


# Singleton instance
email_sync_service = EmailSyncService()
