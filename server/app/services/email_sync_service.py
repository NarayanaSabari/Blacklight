"""Email Sync Service.

Handles fetching emails from connected accounts, filtering for job-related emails,
and coordinating with the parser service.
"""

import base64
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from sqlalchemy import select

from app import db
from app.models.candidate import Candidate
from app.models.processed_email import ProcessedEmail
from app.models.user_email_integration import UserEmailIntegration
from app.services.email_integration_service import email_integration_service
from app.services.oauth.gmail_oauth import gmail_oauth_service
from app.services.oauth.outlook_oauth import outlook_oauth_service
from config.settings import settings

logger = logging.getLogger(__name__)


class EmailSyncService:
    """Service for syncing and filtering job-related emails."""
    
    # Common job-related keywords in email subjects
    JOB_KEYWORDS = [
        "job",
        "position",
        "opening",
        "opportunity",
        "requirement",
        "hiring",
        "developer",
        "engineer",
        "analyst",
        "consultant",
        "manager",
        "lead",
        "architect",
        "admin",
        "specialist",
        "coordinator",
    ]
    
    # Patterns that indicate job emails
    JOB_PATTERNS = [
        r"urgent\s+requirement",
        r"hot\s+requirement",
        r"immediate\s+need",
        r"looking\s+for",
        r"need\s+a?\s*\w+\s*(developer|engineer|analyst)",
        r"\b(c2c|w2|corp.to.corp|1099)\b",
        r"rate:\s*\$?\d+",
        r"duration:\s*\d+",
        r"location:\s*\w+",
    ]
    
    def __init__(self):
        """Initialize email sync service."""
        self.lookback_days = settings.email_sync_lookback_days
        self.max_emails = settings.email_sync_max_emails
    
    def sync_integration(self, integration: UserEmailIntegration) -> dict:
        """
        Sync emails for a single integration.
        
        Args:
            integration: UserEmailIntegration object
            
        Returns:
            Dictionary with sync results
        """
        if not integration.is_active:
            logger.info(f"Skipping inactive integration {integration.id}")
            return {"skipped": True, "reason": "inactive"}
        
        try:
            # Get valid access token
            access_token = email_integration_service.get_valid_access_token(integration)
            
            # Fetch emails based on provider
            if integration.provider == "gmail":
                emails = self._fetch_gmail_emails(access_token, integration)
            else:
                emails = self._fetch_outlook_emails(access_token, integration)
            
            # Get preferred roles for filtering
            preferred_roles = self._get_preferred_roles_for_tenant(integration.tenant_id)
            
            # Filter and process emails
            results = {
                "fetched": len(emails),
                "matched": 0,
                "skipped": 0,
                "already_processed": 0,
                "errors": 0,
                "emails_to_process": [],
            }
            
            for email in emails:
                email_id = email.get("id") or email.get("message_id")
                
                # Check if already processed
                if self._is_email_processed(integration.id, email_id):
                    results["already_processed"] += 1
                    continue
                
                # Check if matches job criteria
                subject = email.get("subject", "")
                matches, match_reason = self._matches_job_criteria(subject, preferred_roles)
                
                if not matches:
                    # Record as skipped
                    self._record_skipped_email(
                        integration=integration,
                        email_id=email_id,
                        subject=subject,
                        sender=email.get("sender", ""),
                        reason=match_reason or "no_match",
                    )
                    results["skipped"] += 1
                    continue
                
                # Add to processing queue
                results["emails_to_process"].append({
                    "email_id": email_id,
                    "thread_id": email.get("thread_id"),
                    "subject": subject,
                    "sender": email.get("sender", ""),
                    "body": email.get("body", ""),
                    "received_at": email.get("received_at"),
                    "match_reason": match_reason,
                })
                results["matched"] += 1
            
            # Update integration sync time
            integration.last_synced_at = datetime.now(timezone.utc)
            integration.consecutive_failures = 0
            integration.last_error = None
            db.session.commit()
            
            logger.info(
                f"Synced integration {integration.id}: "
                f"fetched={results['fetched']}, matched={results['matched']}, "
                f"skipped={results['skipped']}, already_processed={results['already_processed']}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Sync failed for integration {integration.id}: {e}")
            integration.last_error = str(e)
            integration.consecutive_failures = (integration.consecutive_failures or 0) + 1
            
            if integration.consecutive_failures >= 3:
                integration.is_active = False
                logger.warning(f"Deactivated integration {integration.id} due to repeated failures")
            
            db.session.commit()
            return {"error": str(e)}
    
    def _fetch_gmail_emails(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> list[dict]:
        """
        Fetch emails from Gmail.
        
        Args:
            access_token: Valid Gmail access token
            integration: UserEmailIntegration object
            
        Returns:
            List of email dictionaries
        """
        service = gmail_oauth_service.build_gmail_service(access_token)
        
        # Calculate date filter
        after_date = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        query = f"after:{after_date.strftime('%Y/%m/%d')}"
        
        # Search for messages
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=self.max_emails,
        ).execute()
        
        messages = results.get("messages", [])
        emails = []
        
        for msg_info in messages:
            try:
                # Get full message
                message = service.users().messages().get(
                    userId="me",
                    id=msg_info["id"],
                    format="full",
                ).execute()
                
                # Extract headers
                headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
                
                # Extract body
                body = self._extract_gmail_body(message.get("payload", {}))
                
                emails.append({
                    "id": message["id"],
                    "thread_id": message.get("threadId"),
                    "subject": headers.get("subject", ""),
                    "sender": headers.get("from", ""),
                    "body": body,
                    "received_at": self._parse_gmail_date(headers.get("date", "")),
                })
                
            except Exception as e:
                logger.warning(f"Failed to fetch Gmail message {msg_info['id']}: {e}")
                continue
        
        return emails
    
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
    
    def _fetch_outlook_emails(
        self,
        access_token: str,
        integration: UserEmailIntegration,
    ) -> list[dict]:
        """
        Fetch emails from Outlook.
        
        Args:
            access_token: Valid Outlook access token
            integration: UserEmailIntegration object
            
        Returns:
            List of email dictionaries
        """
        # Calculate date filter
        after_date = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        filter_query = f"receivedDateTime ge {after_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        
        # Fetch messages
        messages = outlook_oauth_service.get_messages(
            access_token=access_token,
            top=self.max_emails,
            filter_query=filter_query,
        )
        
        emails = []
        for msg in messages:
            try:
                # Extract body
                body = ""
                if msg.get("body"):
                    body = msg["body"].get("content", "")
                    if msg["body"].get("contentType") == "html":
                        body = re.sub(r"<[^>]+>", " ", body)
                        body = re.sub(r"\s+", " ", body)
                
                # Extract sender
                sender = ""
                if msg.get("from", {}).get("emailAddress"):
                    sender_info = msg["from"]["emailAddress"]
                    sender = f"{sender_info.get('name', '')} <{sender_info.get('address', '')}>"
                
                emails.append({
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
        
        return emails
    
    def _get_preferred_roles_for_tenant(self, tenant_id: int) -> list[str]:
        """
        Get preferred roles from approved candidates in tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of normalized role names
        """
        stmt = select(Candidate.preferred_role).where(
            Candidate.tenant_id == tenant_id,
            Candidate.status == "approved",
            Candidate.preferred_role.isnot(None),
        ).distinct()
        
        roles = list(db.session.scalars(stmt).all())
        
        # Normalize roles
        normalized = []
        for role in roles:
            if role:
                # Split compound roles
                for part in re.split(r"[,/|]", role):
                    normalized.append(part.strip().lower())
        
        return list(set(normalized))
    
    def _matches_job_criteria(
        self,
        subject: str,
        preferred_roles: list[str],
    ) -> tuple[bool, Optional[str]]:
        """
        Check if email subject matches job criteria.
        
        Args:
            subject: Email subject line
            preferred_roles: List of preferred roles to match
            
        Returns:
            Tuple of (matches, reason)
        """
        subject_lower = subject.lower()
        
        # Check for preferred roles match (highest priority)
        for role in preferred_roles:
            if role and role in subject_lower:
                return True, f"role_match:{role}"
        
        # Check for job patterns
        for pattern in self.JOB_PATTERNS:
            if re.search(pattern, subject_lower, re.IGNORECASE):
                return True, f"pattern_match:{pattern}"
        
        # Check for job keywords
        for keyword in self.JOB_KEYWORDS:
            if keyword in subject_lower:
                return True, f"keyword_match:{keyword}"
        
        return False, "no_match"
    
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
