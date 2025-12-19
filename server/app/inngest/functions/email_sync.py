"""
Email Sync Inngest Workflows

Background jobs for syncing emails from connected accounts
and parsing job postings from matching emails.
"""

import logging
from datetime import datetime, timezone

import inngest

from app.inngest import inngest_client
from config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Scheduled Sync - All Integrations
# ============================================================================

@inngest_client.create_function(
    fn_id="sync-all-email-integrations",
    trigger=inngest.TriggerCron(cron="*/15 * * * *"),  # Every 15 minutes
    name="Sync All Email Integrations",
    retries=1,
)
async def sync_all_integrations_workflow(ctx, step):
    """
    Scheduled job to sync all active email integrations.
    Runs every 15 minutes (configurable).
    """
    logger.info("[INNGEST] Starting sync-all-email-integrations")
    
    if not settings.email_sync_enabled:
        logger.info("[INNGEST] Email sync is disabled, skipping")
        return {"status": "disabled", "message": "Email sync is disabled"}
    
    # Step 1: Get all active integrations
    def get_active_integrations():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.services.email_integration_service import email_integration_service
            integrations = email_integration_service.get_active_integrations()
            return [
                {
                    "id": i.id,
                    "user_id": i.user_id,
                    "tenant_id": i.tenant_id,
                    "provider": i.provider,
                }
                for i in integrations
            ]
    
    active_integrations = await step.run(
        "get-active-integrations",
        get_active_integrations,
    )
    
    logger.info(f"[INNGEST] Found {len(active_integrations)} active integrations to sync")
    
    # Step 2: Trigger individual sync events for each integration
    # This allows parallel processing and better error isolation
    for integration in active_integrations:
        inngest_client.send_sync(
            inngest.Event(
                name="email/sync-user-inbox",
                data={
                    "integration_id": integration["id"],
                    "user_id": integration["user_id"],
                    "tenant_id": integration["tenant_id"],
                    "scheduled": True,
                },
            )
        )
    
    return {
        "status": "triggered",
        "integrations_count": len(active_integrations),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Single Integration Sync
# ============================================================================

@inngest_client.create_function(
    fn_id="sync-user-inbox",
    trigger=inngest.TriggerEvent(event="email/sync-user-inbox"),
    name="Sync User Email Inbox",
    retries=3,
    throttle=inngest.Throttle(
        limit=10,  # Max 10 syncs per minute per integration
        period=60000,  # 1 minute in milliseconds
        key="event.data.integration_id",
    ),
)
async def sync_user_inbox_workflow(ctx, step):
    """
    Sync emails for a single user's integration.
    
    Event data:
        integration_id: int
        user_id: int
        tenant_id: int
        manual_trigger: bool (optional)
    """
    event_data = ctx.event.data
    integration_id = event_data.get("integration_id")
    manual_trigger = event_data.get("manual_trigger", False)
    
    logger.info(f"[INNGEST] Syncing inbox for integration {integration_id} (manual={manual_trigger})")
    
    # Step 1: Fetch and filter emails
    def sync_emails():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            from app.models.user_email_integration import UserEmailIntegration
            from app.services.email_sync_service import email_sync_service
            
            integration = db.session.get(UserEmailIntegration, integration_id)
            if not integration:
                return {"error": "Integration not found"}
            
            if not integration.is_active:
                return {"skipped": True, "reason": "inactive"}
            
            return email_sync_service.sync_integration(integration)
    
    sync_result = await step.run("sync-emails", sync_emails)
    
    if sync_result.get("error"):
        logger.error(f"[INNGEST] Sync failed: {sync_result['error']}")
        return sync_result
    
    if sync_result.get("skipped"):
        logger.info(f"[INNGEST] Sync skipped: {sync_result['reason']}")
        return sync_result
    
    # Step 2: Parse matched emails into jobs
    emails_to_process = sync_result.get("emails_to_process", [])
    
    if not emails_to_process:
        logger.info("[INNGEST] No emails to process")
        return {
            "status": "completed",
            "fetched": sync_result.get("fetched", 0),
            "matched": 0,
            "jobs_created": 0,
        }
    
    logger.info(f"[INNGEST] Processing {len(emails_to_process)} matched emails")
    
    # Step 3: Parse each email into a job
    jobs_created = 0
    
    for email_data in emails_to_process:
        def parse_email(data=email_data):
            from app import create_app
            app = create_app()
            with app.app_context():
                from app import db
                from app.models.user_email_integration import UserEmailIntegration
                from app.services.email_job_parser_service import email_job_parser_service
                
                integration = db.session.get(UserEmailIntegration, integration_id)
                if not integration:
                    return {"error": "Integration not found"}
                
                job = email_job_parser_service.parse_email_to_job(integration, data)
                
                if job:
                    db.session.commit()
                    return {"job_id": job.id, "title": job.title}
                
                return {"skipped": True}
        
        email_id = email_data.get("email_id", "unknown")
        result = await step.run(f"parse-email-{email_id[:20]}", parse_email)
        
        if result.get("job_id"):
            jobs_created += 1
            logger.info(f"[INNGEST] Created job {result['job_id']}: {result['title']}")
    
    return {
        "status": "completed",
        "fetched": sync_result.get("fetched", 0),
        "matched": sync_result.get("matched", 0),
        "already_processed": sync_result.get("already_processed", 0),
        "jobs_created": jobs_created,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Manual Sync Trigger
# ============================================================================

@inngest_client.create_function(
    fn_id="manual-email-sync",
    trigger=inngest.TriggerEvent(event="email/manual-sync"),
    name="Manual Email Sync",
    retries=2,
)
async def manual_sync_workflow(ctx, step):
    """
    Manually triggered sync for a specific user.
    
    Event data:
        user_id: int
        tenant_id: int
        provider: str (optional - 'gmail' or 'outlook', syncs all if not specified)
    """
    event_data = ctx.event.data
    user_id = event_data.get("user_id")
    tenant_id = event_data.get("tenant_id")
    provider = event_data.get("provider")
    
    logger.info(f"[INNGEST] Manual sync triggered for user {user_id}, provider={provider}")
    
    # Get integrations for user
    def get_user_integrations():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.services.email_integration_service import email_integration_service
            integrations = email_integration_service.get_integrations_for_user(user_id, tenant_id)
            
            result = []
            for i in integrations:
                if provider and i.provider != provider:
                    continue
                if i.is_active:
                    result.append({
                        "id": i.id,
                        "provider": i.provider,
                    })
            return result
    
    integrations = await step.run("get-user-integrations", get_user_integrations)
    
    # Trigger sync for each integration
    for integration in integrations:
        inngest_client.send_sync(
            inngest.Event(
                name="email/sync-user-inbox",
                data={
                    "integration_id": integration["id"],
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "manual_trigger": True,
                },
            )
        )
    
    return {
        "status": "triggered",
        "integrations_synced": len(integrations),
    }
