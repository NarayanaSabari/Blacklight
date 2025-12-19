# Inngest Workflows

## Overview

This document describes the background job workflows for email integration using Inngest. These jobs handle periodic email syncing, parsing, and job creation.

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INNGEST WORKFLOWS                                      │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │           CRON: sync-all-email-integrations (every 15 min)              │    │
│  │                                                                          │    │
│  │  Triggers individual sync jobs for each active integration              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│                                       │ triggers                                 │
│                                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │           EVENT: email/sync-user-inbox                                   │    │
│  │                                                                          │    │
│  │  Per-user sync: fetch emails → parse → create jobs                      │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│                                       │ for each email                           │
│                                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │           EVENT: email/parse-job-email                                   │    │
│  │                                                                          │    │
│  │  AI parsing with retry logic                                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Implementation

```python
# app/inngest/functions/email_sync.py
"""
Inngest workflows for email integration and job extraction.
"""
import inngest
from datetime import datetime, timedelta
from app.inngest import inngest_client
from app import db


# ============================================================================
# CRON JOB: Trigger sync for all active integrations
# ============================================================================

@inngest_client.create_function(
    fn_id="sync-all-email-integrations",
    trigger=inngest.TriggerCron(cron="*/15 * * * *"),  # Every 15 minutes
    name="Sync All Email Integrations",
    retries=1
)
async def sync_all_email_integrations_workflow(ctx):
    """
    Cron job that triggers individual sync for each active email integration.
    Runs every 15 minutes.
    """
    from app.models import UserEmailIntegration
    from app import create_app
    
    app = create_app()
    with app.app_context():
        # Step 1: Get all active integrations
        integrations = await ctx.step.run(
            "fetch-active-integrations",
            fetch_active_integrations_step
        )
        
        if not integrations:
            return {"message": "No active integrations to sync", "count": 0}
        
        # Step 2: Trigger individual sync for each integration
        triggered_count = 0
        for integration in integrations:
            try:
                inngest_client.send_sync(
                    inngest.Event(
                        name="email/sync-user-inbox",
                        data={
                            "integration_id": integration["id"],
                            "user_id": integration["user_id"],
                            "tenant_id": integration["tenant_id"],
                            "provider": integration["provider"],
                            "manual_trigger": False
                        }
                    )
                )
                triggered_count += 1
            except Exception as e:
                print(f"Failed to trigger sync for integration {integration['id']}: {e}")
        
        return {
            "message": f"Triggered sync for {triggered_count} integrations",
            "total_active": len(integrations),
            "triggered": triggered_count
        }


def fetch_active_integrations_step():
    """Fetch all active email integrations that need syncing."""
    from app.models import UserEmailIntegration
    from sqlalchemy import select
    
    # Get integrations that:
    # 1. Are active
    # 2. Haven't been synced in the last sync_frequency_minutes
    stmt = (
        select(UserEmailIntegration)
        .where(UserEmailIntegration.is_active == True)
    )
    
    result = db.session.execute(stmt)
    integrations = result.scalars().all()
    
    # Filter by sync frequency
    now = datetime.utcnow()
    ready_to_sync = []
    
    for integration in integrations:
        if integration.last_synced_at is None:
            ready_to_sync.append(integration)
        else:
            next_sync = integration.last_synced_at + timedelta(
                minutes=integration.sync_frequency_minutes or 15
            )
            if now >= next_sync:
                ready_to_sync.append(integration)
    
    return [
        {
            "id": i.id,
            "user_id": i.user_id,
            "tenant_id": i.tenant_id,
            "provider": i.provider
        }
        for i in ready_to_sync
    ]


# ============================================================================
# EVENT: Sync individual user's inbox
# ============================================================================

@inngest_client.create_function(
    fn_id="sync-user-email-inbox",
    trigger=inngest.TriggerEvent(event="email/sync-user-inbox"),
    name="Sync User Email Inbox",
    retries=3,
    rate_limit=inngest.RateLimit(limit=10, period=timedelta(minutes=1))  # Max 10 syncs/minute
)
async def sync_user_inbox_workflow(ctx):
    """
    Sync a single user's email inbox:
    1. Get search keywords from tenant's candidates
    2. Fetch matching emails
    3. Parse each email with AI
    4. Create jobs from valid emails
    """
    from app import create_app
    
    event = ctx.event
    integration_id = event.data.get("integration_id")
    user_id = event.data.get("user_id")
    tenant_id = event.data.get("tenant_id")
    manual_trigger = event.data.get("manual_trigger", False)
    
    app = create_app()
    with app.app_context():
        # Step 1: Get integration and validate
        integration = await ctx.step.run(
            "get-integration",
            get_integration_step,
            integration_id, user_id
        )
        
        if not integration:
            return {"error": "Integration not found or inactive"}
        
        # Step 2: Get search keywords for tenant
        keywords = await ctx.step.run(
            "get-search-keywords",
            get_search_keywords_step,
            tenant_id
        )
        
        if not keywords:
            # Update sync status and return
            await ctx.step.run(
                "update-sync-status-no-keywords",
                update_sync_status_step,
                integration_id, "success", "No candidate preferred roles found"
            )
            return {"message": "No keywords to search", "emails_processed": 0}
        
        # Step 3: Fetch matching emails
        emails = await ctx.step.run(
            "fetch-matching-emails",
            fetch_emails_step,
            integration_id, keywords
        )
        
        if not emails:
            await ctx.step.run(
                "update-sync-status-no-emails",
                update_sync_status_step,
                integration_id, "success", None
            )
            return {"message": "No matching emails found", "emails_processed": 0}
        
        # Step 4: Process each email
        jobs_created = 0
        emails_processed = 0
        errors = []
        
        for email_data in emails:
            try:
                result = await ctx.step.run(
                    f"process-email-{email_data['message_id'][:20]}",
                    process_single_email_step,
                    integration_id, tenant_id, user_id, email_data
                )
                
                emails_processed += 1
                if result.get("job_created"):
                    jobs_created += 1
                    
            except Exception as e:
                errors.append({
                    "email_id": email_data.get("message_id"),
                    "error": str(e)
                })
        
        # Step 5: Update integration stats
        await ctx.step.run(
            "update-integration-stats",
            update_integration_stats_step,
            integration_id, emails_processed, jobs_created
        )
        
        return {
            "message": "Sync completed",
            "keywords_searched": len(keywords),
            "emails_found": len(emails),
            "emails_processed": emails_processed,
            "jobs_created": jobs_created,
            "errors": errors if errors else None
        }


def get_integration_step(integration_id, user_id):
    """Get and validate email integration."""
    from app.models import UserEmailIntegration
    
    integration = db.session.get(UserEmailIntegration, integration_id)
    
    if not integration:
        return None
    
    if integration.user_id != user_id:
        return None
    
    if not integration.is_active:
        return None
    
    return {
        "id": integration.id,
        "provider": integration.provider,
        "user_id": integration.user_id,
        "tenant_id": integration.tenant_id
    }


def get_search_keywords_step(tenant_id):
    """Get search keywords from tenant candidates' preferred roles."""
    from app.services.email_sync_service import EmailSyncService
    
    service = EmailSyncService()
    keywords = service.get_search_keywords_for_tenant(tenant_id)
    
    return keywords


def fetch_emails_step(integration_id, keywords):
    """Fetch matching emails from provider."""
    from app.models import UserEmailIntegration
    from app.services.email_sync_service import EmailSyncService
    
    integration = db.session.get(UserEmailIntegration, integration_id)
    if not integration:
        return []
    
    service = EmailSyncService()
    emails = service.fetch_matching_emails(integration, keywords)
    
    # Convert to serializable format
    return [
        {
            "message_id": e.message_id,
            "thread_id": e.thread_id,
            "subject": e.subject,
            "sender": e.sender,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "body_text": e.body_text,
            "body_html": e.body_html
        }
        for e in emails
    ]


def process_single_email_step(integration_id, tenant_id, user_id, email_data):
    """Process a single email: parse with AI and create job if valid."""
    from app.services.email_job_parser import EmailJobParserService, EmailMessage
    from app.services.email_sync_service import EmailSyncService
    from app.models import JobPosting
    from datetime import datetime
    
    # Reconstruct EmailMessage
    email = EmailMessage(
        message_id=email_data["message_id"],
        thread_id=email_data.get("thread_id"),
        subject=email_data["subject"],
        sender=email_data["sender"],
        received_at=datetime.fromisoformat(email_data["received_at"]) if email_data.get("received_at") else datetime.utcnow(),
        body_text=email_data["body_text"],
        body_html=email_data.get("body_html")
    )
    
    parser = EmailJobParserService()
    sync_service = EmailSyncService()
    
    # Parse email with AI
    parsed = parser.parse_email(email)
    
    if not parsed:
        sync_service.mark_email_processed(
            integration_id, tenant_id, email,
            result="failed",
            skip_reason="AI parsing failed"
        )
        return {"job_created": False, "reason": "parsing_failed"}
    
    # Check if it's a valid job
    if not parser.is_valid_job_email(parsed):
        reason = "not_job" if not parsed.is_job_requirement else f"low_confidence_{parsed.confidence_score}"
        sync_service.mark_email_processed(
            integration_id, tenant_id, email,
            result="skipped",
            skip_reason=reason
        )
        return {"job_created": False, "reason": reason}
    
    # Create job
    job = parser.create_job_from_parsed(parsed, email, tenant_id, user_id)
    db.session.add(job)
    db.session.commit()
    
    # Mark email as processed
    sync_service.mark_email_processed(
        integration_id, tenant_id, email,
        result="job_created",
        job_id=job.id
    )
    
    return {"job_created": True, "job_id": job.id}


def update_sync_status_step(integration_id, status, error_message):
    """Update integration sync status."""
    from app.models import UserEmailIntegration
    
    integration = db.session.get(UserEmailIntegration, integration_id)
    if integration:
        integration.last_synced_at = datetime.utcnow()
        integration.last_sync_status = status
        integration.last_sync_error = error_message
        db.session.commit()


def update_integration_stats_step(integration_id, emails_processed, jobs_created):
    """Update integration statistics after sync."""
    from app.models import UserEmailIntegration
    from sqlalchemy import text
    
    integration = db.session.get(UserEmailIntegration, integration_id)
    if integration:
        integration.last_synced_at = datetime.utcnow()
        integration.last_sync_status = "success"
        integration.last_sync_error = None
        integration.emails_processed_count = (integration.emails_processed_count or 0) + emails_processed
        integration.jobs_created_count = (integration.jobs_created_count or 0) + jobs_created
        db.session.commit()


# ============================================================================
# EVENT: Handle OAuth token refresh errors
# ============================================================================

@inngest_client.create_function(
    fn_id="handle-email-integration-error",
    trigger=inngest.TriggerEvent(event="email/integration-error"),
    name="Handle Email Integration Error",
    retries=1
)
async def handle_integration_error_workflow(ctx):
    """
    Handle errors during email integration (e.g., token refresh failures).
    Notifies user and potentially disables integration.
    """
    from app import create_app
    from app.models import UserEmailIntegration, PortalUser
    from app.services.email_service import EmailService
    
    event = ctx.event
    integration_id = event.data.get("integration_id")
    error_type = event.data.get("error_type")
    error_message = event.data.get("error_message")
    
    app = create_app()
    with app.app_context():
        integration = db.session.get(UserEmailIntegration, integration_id)
        if not integration:
            return {"error": "Integration not found"}
        
        user = db.session.get(PortalUser, integration.user_id)
        
        # Update integration status
        if error_type == "token_expired":
            integration.is_active = False
            integration.last_sync_status = "failed"
            integration.last_sync_error = "Token expired - please reconnect"
            db.session.commit()
            
            # Notify user
            if user:
                email_service = EmailService()
                email_service.send_email(
                    to_email=user.email,
                    subject="Action Required: Reconnect Your Email Integration",
                    body=f"""
                    Your {integration.provider.title()} email integration has been disconnected 
                    due to an expired token.
                    
                    Please log in to Blacklight and reconnect your email account in 
                    Settings → Integrations.
                    """
                )
        
        return {
            "integration_id": integration_id,
            "action_taken": "disabled" if error_type == "token_expired" else "logged",
            "user_notified": user is not None
        }


# ============================================================================
# Register all functions
# ============================================================================

EMAIL_SYNC_FUNCTIONS = [
    sync_all_email_integrations_workflow,
    sync_user_inbox_workflow,
    handle_integration_error_workflow,
]
```

## Function Registration

Add to `app/inngest/functions/__init__.py`:

```python
# Add import
from app.inngest.functions.email_sync import EMAIL_SYNC_FUNCTIONS

# Add to INNGEST_FUNCTIONS list
INNGEST_FUNCTIONS = [
    # ... existing functions ...
    *EMAIL_SYNC_FUNCTIONS,
]
```

## Workflow Events

### Event: `email/sync-user-inbox`

Triggered by cron job or manual sync button.

```python
inngest_client.send_sync(
    inngest.Event(
        name="email/sync-user-inbox",
        data={
            "integration_id": 123,
            "user_id": 456,
            "tenant_id": 789,
            "provider": "gmail",
            "manual_trigger": True
        }
    )
)
```

### Event: `email/integration-error`

Triggered when sync fails due to token issues.

```python
inngest_client.send_sync(
    inngest.Event(
        name="email/integration-error",
        data={
            "integration_id": 123,
            "error_type": "token_expired",
            "error_message": "Refresh token invalid"
        }
    )
)
```

## Monitoring

### Inngest Dashboard

View job runs at: `http://localhost:8288` (Inngest Dev Server)

### Logs

```python
# Example log output
[2025-12-17 10:00:00] sync-all-email-integrations: Started
[2025-12-17 10:00:01] sync-all-email-integrations: Found 5 active integrations
[2025-12-17 10:00:01] sync-user-email-inbox (integration_id=123): Started
[2025-12-17 10:00:02] sync-user-email-inbox: Keywords: ['python developer', 'react dev']
[2025-12-17 10:00:05] sync-user-email-inbox: Found 12 matching emails
[2025-12-17 10:00:30] sync-user-email-inbox: Processed 12 emails, created 3 jobs
```

## Error Handling & Retries

| Error Type | Retry | Action |
|------------|-------|--------|
| API Rate Limit | Yes (3x) | Exponential backoff |
| Token Expired | No | Disable integration, notify user |
| Parsing Error | Yes (1x) | Log and skip email |
| Network Error | Yes (3x) | Retry with backoff |

## Performance Considerations

1. **Batch Processing**: Each sync processes up to 50 emails
2. **Rate Limiting**: Max 10 syncs per minute across all users
3. **Staggered Execution**: Cron triggers individual events, not bulk processing
4. **Step Functions**: Long-running tasks broken into steps for reliability
