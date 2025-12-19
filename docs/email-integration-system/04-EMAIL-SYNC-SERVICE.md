# Email Sync Service

## Overview

The Email Sync Service is responsible for fetching emails from connected Gmail/Outlook accounts and filtering them based on tenant candidates' preferred roles. This is "Layer 1" of the email processing pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EMAIL SYNC SERVICE                                     │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    1. GET SEARCH KEYWORDS                                  │  │
│  │                                                                            │  │
│  │  Tenant Candidates → preferred_roles → AIRoleNormalizationService         │  │
│  │                                                                            │  │
│  │  Example:                                                                  │  │
│  │  ["Senior Python Developer", "Tech Lead"] →                               │  │
│  │  ["python developer", "python dev", "tech lead", "technical lead"]        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    2. FETCH EMAILS BY SUBJECT                              │  │
│  │                                                                            │  │
│  │  Gmail API:  q="subject:python developer OR subject:tech lead"            │  │
│  │  Graph API:  $search="subject:python developer OR subject:tech lead"      │  │
│  │                                                                            │  │
│  │  Filters:                                                                  │  │
│  │  - Only from last N days (configurable, default 7)                        │  │
│  │  - Skip already processed emails (check ProcessedEmail table)             │  │
│  │  - Limit batch size (default 50 emails per sync)                          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    3. RETURN EMAIL OBJECTS                                 │  │
│  │                                                                            │  │
│  │  For each email:                                                           │  │
│  │  {                                                                         │  │
│  │    "message_id": "RFC2822 Message-ID",                                    │  │
│  │    "thread_id": "Gmail/Outlook thread ID",                                │  │
│  │    "subject": "Python Developer - Remote - $150k",                        │  │
│  │    "sender": "vendor@company.com",                                        │  │
│  │    "received_at": "2025-12-16T10:00:00Z",                                 │  │
│  │    "body_text": "Full email body in plain text",                          │  │
│  │    "body_html": "Full email body in HTML (optional)"                      │  │
│  │  }                                                                         │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Email Sync Service Implementation

```python
# app/services/email_sync_service.py
from typing import List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from app.models import Candidate, UserEmailIntegration, ProcessedEmail, GlobalRole
from app.services.ai_role_normalization import AIRoleNormalizationService
from app import db
from sqlalchemy import select, distinct

@dataclass
class EmailMessage:
    """Represents a fetched email."""
    message_id: str
    thread_id: Optional[str]
    subject: str
    sender: str
    received_at: datetime
    body_text: str
    body_html: Optional[str] = None


class EmailSyncService:
    """
    Service for fetching and filtering emails from connected accounts.
    Implements Layer 1: Subject line matching.
    """
    
    def __init__(self):
        self.role_normalization_service = AIRoleNormalizationService()
        self.max_emails_per_sync = 50
        self.default_lookback_days = 7
    
    def get_search_keywords_for_tenant(self, tenant_id: int) -> List[str]:
        """
        Get search keywords based on tenant's candidates' preferred roles.
        Normalizes roles and extracts searchable keywords.
        
        Returns:
            List of lowercase keyword strings for email subject search
        """
        # Get all unique preferred roles from tenant's candidates
        stmt = (
            select(distinct(db.func.unnest(Candidate.preferred_roles)))
            .where(Candidate.tenant_id == tenant_id)
            .where(Candidate.preferred_roles.isnot(None))
        )
        result = db.session.execute(stmt)
        preferred_roles = [row[0] for row in result if row[0]]
        
        if not preferred_roles:
            return []
        
        # Also get GlobalRole names that candidates are linked to
        stmt = (
            select(GlobalRole.name, GlobalRole.aliases)
            .join(CandidateGlobalRole, CandidateGlobalRole.global_role_id == GlobalRole.id)
            .join(Candidate, Candidate.id == CandidateGlobalRole.candidate_id)
            .where(Candidate.tenant_id == tenant_id)
            .distinct()
        )
        result = db.session.execute(stmt)
        global_roles = list(result)
        
        keywords = set()
        
        # Add preferred roles (normalized to lowercase)
        for role in preferred_roles:
            # Extract core keywords from role
            keywords.add(role.lower())
            # Also add common variations
            core = self._extract_core_role(role)
            if core:
                keywords.add(core.lower())
        
        # Add global role names and aliases
        for name, aliases in global_roles:
            keywords.add(name.lower())
            if aliases:
                for alias in aliases:
                    keywords.add(alias.lower())
        
        return list(keywords)
    
    def _extract_core_role(self, role: str) -> Optional[str]:
        """
        Extract core searchable term from a role.
        "Senior Python Developer" → "python developer"
        "Lead Software Engineer" → "software engineer"
        """
        # Remove common prefixes
        prefixes = ['senior', 'junior', 'lead', 'principal', 'staff', 'entry', 'mid', 'sr.', 'jr.']
        words = role.lower().split()
        core_words = [w for w in words if w not in prefixes]
        
        if core_words:
            return ' '.join(core_words)
        return None
    
    def fetch_matching_emails(
        self,
        integration: UserEmailIntegration,
        keywords: List[str],
        lookback_days: Optional[int] = None
    ) -> List[EmailMessage]:
        """
        Fetch emails matching keywords from the connected email account.
        
        Args:
            integration: The user's email integration record
            keywords: List of keywords to search in subject lines
            lookback_days: How far back to search (default: 7 days)
        
        Returns:
            List of EmailMessage objects (not yet processed)
        """
        if not keywords:
            return []
        
        lookback = lookback_days or integration.sync_lookback_days or self.default_lookback_days
        since_date = datetime.utcnow() - timedelta(days=lookback)
        
        # Get already processed email IDs to skip
        processed_ids = self._get_processed_email_ids(integration.id)
        
        # Fetch based on provider
        if integration.provider == 'gmail':
            emails = self._fetch_gmail_emails(integration, keywords, since_date)
        else:
            emails = self._fetch_outlook_emails(integration, keywords, since_date)
        
        # Filter out already processed emails
        new_emails = [e for e in emails if e.message_id not in processed_ids]
        
        # Limit batch size
        return new_emails[:self.max_emails_per_sync]
    
    def _get_processed_email_ids(self, integration_id: int) -> set:
        """Get set of already processed email message IDs."""
        stmt = (
            select(ProcessedEmail.email_message_id)
            .where(ProcessedEmail.integration_id == integration_id)
        )
        result = db.session.execute(stmt)
        return {row[0] for row in result}
    
    def _fetch_gmail_emails(
        self,
        integration: UserEmailIntegration,
        keywords: List[str],
        since_date: datetime
    ) -> List[EmailMessage]:
        """Fetch emails from Gmail API."""
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from app.services.email_integration_service import EmailIntegrationService
        
        # Get valid access token (refreshing if needed)
        email_integration_service = EmailIntegrationService()
        access_token = email_integration_service.get_valid_access_token(integration)
        
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        
        # Build search query
        # Gmail search: subject:(python developer) OR subject:(tech lead)
        subject_queries = [f'subject:({kw})' for kw in keywords[:10]]  # Limit keywords
        search_query = ' OR '.join(subject_queries)
        
        # Add date filter
        date_str = since_date.strftime('%Y/%m/%d')
        search_query = f'({search_query}) after:{date_str}'
        
        # Fetch message list
        try:
            response = service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=100  # Fetch more, filter later
            ).execute()
        except Exception as e:
            print(f"Gmail API error: {e}")
            return []
        
        messages = response.get('messages', [])
        emails = []
        
        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId='me',
                    id=msg_ref['id'],
                    format='full'
                ).execute()
                
                email = self._parse_gmail_message(msg)
                if email:
                    emails.append(email)
            except Exception as e:
                print(f"Error fetching Gmail message {msg_ref['id']}: {e}")
                continue
        
        return emails
    
    def _parse_gmail_message(self, msg: dict) -> Optional[EmailMessage]:
        """Parse Gmail API message into EmailMessage."""
        import base64
        from email.utils import parsedate_to_datetime
        
        headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
        
        message_id = headers.get('message-id', msg['id'])
        subject = headers.get('subject', '')
        sender = headers.get('from', '')
        date_str = headers.get('date', '')
        
        # Parse date
        try:
            received_at = parsedate_to_datetime(date_str)
        except:
            received_at = datetime.utcnow()
        
        # Extract body
        body_text = ''
        body_html = None
        
        payload = msg.get('payload', {})
        
        def extract_body(part):
            nonlocal body_text, body_html
            
            mime_type = part.get('mimeType', '')
            body = part.get('body', {})
            data = body.get('data', '')
            
            if data:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                if 'text/plain' in mime_type:
                    body_text = decoded
                elif 'text/html' in mime_type:
                    body_html = decoded
            
            # Recurse into parts
            for sub_part in part.get('parts', []):
                extract_body(sub_part)
        
        extract_body(payload)
        
        # If no plain text, extract from HTML
        if not body_text and body_html:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(body_html, 'html.parser')
            body_text = soup.get_text(separator='\n', strip=True)
        
        return EmailMessage(
            message_id=message_id,
            thread_id=msg.get('threadId'),
            subject=subject,
            sender=sender,
            received_at=received_at,
            body_text=body_text,
            body_html=body_html
        )
    
    def _fetch_outlook_emails(
        self,
        integration: UserEmailIntegration,
        keywords: List[str],
        since_date: datetime
    ) -> List[EmailMessage]:
        """Fetch emails from Microsoft Graph API."""
        import requests
        from app.services.email_integration_service import EmailIntegrationService
        
        # Get valid access token
        email_integration_service = EmailIntegrationService()
        access_token = email_integration_service.get_valid_access_token(integration)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Build search query for Microsoft Graph
        # $search requires specific format
        search_terms = ' OR '.join([f'subject:{kw}' for kw in keywords[:10]])
        
        # Filter by date
        date_filter = since_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        url = 'https://graph.microsoft.com/v1.0/me/messages'
        params = {
            '$filter': f"receivedDateTime ge {date_filter}",
            '$search': f'"{search_terms}"',
            '$top': 100,
            '$select': 'id,internetMessageId,subject,from,receivedDateTime,body,bodyPreview'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Graph API error: {e}")
            return []
        
        emails = []
        for msg in data.get('value', []):
            email = self._parse_outlook_message(msg)
            if email:
                emails.append(email)
        
        return emails
    
    def _parse_outlook_message(self, msg: dict) -> Optional[EmailMessage]:
        """Parse Microsoft Graph message into EmailMessage."""
        from dateutil.parser import parse as parse_date
        
        message_id = msg.get('internetMessageId', msg['id'])
        subject = msg.get('subject', '')
        
        from_obj = msg.get('from', {}).get('emailAddress', {})
        sender = f"{from_obj.get('name', '')} <{from_obj.get('address', '')}>"
        
        try:
            received_at = parse_date(msg.get('receivedDateTime', ''))
        except:
            received_at = datetime.utcnow()
        
        body = msg.get('body', {})
        body_content = body.get('content', '')
        content_type = body.get('contentType', 'text')
        
        if content_type.lower() == 'html':
            body_html = body_content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(body_html, 'html.parser')
            body_text = soup.get_text(separator='\n', strip=True)
        else:
            body_text = body_content
            body_html = None
        
        return EmailMessage(
            message_id=message_id,
            thread_id=msg.get('conversationId'),
            subject=subject,
            sender=sender,
            received_at=received_at,
            body_text=body_text,
            body_html=body_html
        )
    
    def mark_email_processed(
        self,
        integration_id: int,
        tenant_id: int,
        email: EmailMessage,
        result: str,
        job_id: Optional[int] = None,
        skip_reason: Optional[str] = None
    ):
        """
        Mark an email as processed to avoid reprocessing.
        
        Args:
            integration_id: ID of the email integration
            tenant_id: Tenant ID
            email: The processed email
            result: 'job_created', 'skipped', 'failed', 'irrelevant'
            job_id: ID of created job (if applicable)
            skip_reason: Why email was skipped (if applicable)
        """
        processed = ProcessedEmail(
            integration_id=integration_id,
            tenant_id=tenant_id,
            email_message_id=email.message_id,
            email_thread_id=email.thread_id,
            email_subject=email.subject[:500] if email.subject else '',
            email_sender=email.sender[:255] if email.sender else '',
            processing_result=result,
            job_id=job_id,
            skip_reason=skip_reason
        )
        db.session.add(processed)
        db.session.commit()
```

## Keyword Extraction Examples

| Candidate Preferred Roles | Extracted Keywords |
|--------------------------|-------------------|
| `["Senior Python Developer"]` | `["senior python developer", "python developer"]` |
| `["Tech Lead", "Engineering Manager"]` | `["tech lead", "engineering manager"]` |
| `["Full Stack Engineer", "React Developer"]` | `["full stack engineer", "react developer", "stack engineer"]` |
| `["Data Scientist", "ML Engineer"]` | `["data scientist", "ml engineer", "machine learning engineer"]` |

## Gmail Search Query Examples

```
# For keywords: ["python developer", "tech lead"]
(subject:(python developer) OR subject:(tech lead)) after:2025/12/09

# For keywords: ["react", "frontend", "javascript"]
(subject:(react) OR subject:(frontend) OR subject:(javascript)) after:2025/12/09
```

## Microsoft Graph Search Examples

```
# OData filter with search
$filter=receivedDateTime ge 2025-12-09T00:00:00Z
$search="subject:python developer OR subject:tech lead"
```

## Rate Limiting Considerations

### Gmail API
- 250 quota units per user per second
- `messages.list`: 5 units
- `messages.get`: 5 units
- With 50 emails: ~255 units (within limits)

### Microsoft Graph
- 10,000 requests per 10 minutes per app
- With 50 users syncing 50 emails each: 2,500 requests (well within limits)

## Error Handling

```python
class EmailSyncError(Exception):
    """Base exception for email sync errors."""
    pass

class TokenExpiredError(EmailSyncError):
    """OAuth token expired and refresh failed."""
    pass

class RateLimitError(EmailSyncError):
    """API rate limit exceeded."""
    pass

class ProviderError(EmailSyncError):
    """Error from email provider API."""
    pass
```

## Dependencies

```txt
# requirements.txt additions
google-api-python-client>=2.95.0
beautifulsoup4>=4.12.0
python-dateutil>=2.8.2
```
