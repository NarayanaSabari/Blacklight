"""
Email Sync Inngest Workflows

Background jobs for syncing emails from connected accounts
and parsing job postings from matching emails.

SCALABILITY IMPROVEMENTS:
- Phase 1: Batch event sending for triggering syncs
- Phase 4: Increased throttle limits for higher throughput
- Phase 6: ProcessedEmail cleanup cron job
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List

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
async def sync_all_integrations_workflow(ctx: inngest.Context) -> dict:
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
    
    active_integrations = await ctx.step.run(
        "get-active-integrations",
        get_active_integrations,
    )
    
    logger.info(f"[INNGEST] Found {len(active_integrations)} active integrations to sync")
    
    # Phase 1: Batch event sending for better performance
    # Instead of sending events one-by-one, batch them together
    def send_batch_events(integrations: list) -> int:
        """Send sync events in batch for efficiency."""
        events = [
            inngest.Event(
                name="email/sync-user-inbox",
                data={
                    "integration_id": integration["id"],
                    "user_id": integration["user_id"],
                    "tenant_id": integration["tenant_id"],
                    "scheduled": True,
                },
            )
            for integration in integrations
        ]
        
        if events:
            # Batch send all events at once
            inngest_client.send_sync(events)
        
        return len(events)
    
    events_sent = await ctx.step.run(
        "send-batch-sync-events",
        lambda: send_batch_events(active_integrations),
    )
    
    logger.info(f"[INNGEST] Batch sent {events_sent} sync events")
    
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
        limit=50,  # Phase 4: Increased from 10 to 50 syncs per minute per integration
        period=60000,  # 1 minute in milliseconds
        key="event.data.integration_id",
    ),
)
async def sync_user_inbox_workflow(ctx: inngest.Context) -> dict:
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
            
            result = email_sync_service.sync_integration(integration)
            
            # Store full email data in a separate key to avoid bloating step output
            # Inngest dashboard has limits on displayed data size
            emails_to_process = result.pop("emails_to_process", [])
            
            # Return summary for dashboard visibility + compact email refs
            return {
                **result,
                "email_count": len(emails_to_process),
                "email_subjects": [e.get("subject", "")[:80] for e in emails_to_process],
                "_emails_data": emails_to_process,  # Full data for processing
            }
    
    sync_result = await ctx.step.run("sync-emails", sync_emails)
    
    if sync_result.get("error"):
        logger.error(f"[INNGEST] Sync failed: {sync_result['error']}")
        return sync_result
    
    # Check if integration was skipped (inactive, no roles, etc.)
    # Note: sync_result may contain "skipped" as a count of skipped emails (int),
    # so we check for the boolean True explicitly, not just truthiness
    if sync_result.get("skipped") is True:
        logger.info(f"[INNGEST] Sync skipped: {sync_result.get('reason', 'unknown')}")
        return sync_result
    
    # Step 2: Parse matched emails into jobs
    # Use _emails_data which contains the full email bodies
    emails_to_process = sync_result.get("_emails_data", [])
    
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
    created_job_ids = []  # Collect job IDs for matching
    
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
                    return {
                        "job_id": job.id, 
                        "title": job.title,
                        "tenant_id": integration.tenant_id,
                    }
                
                return {"skipped": True}
        
        email_id = email_data.get("email_id", "unknown")
        result = await ctx.step.run(f"parse-email-{email_id[:20]}", parse_email)
        
        if result.get("job_id"):
            jobs_created += 1
            created_job_ids.append(result["job_id"])
            logger.info(f"[INNGEST] Created job {result['job_id']}: {result['title']}")
    
    # Step 4: Trigger job matching for email-sourced jobs
    if created_job_ids:
        def trigger_email_job_matching(job_ids=created_job_ids, tenant_id=event_data.get("tenant_id")):
            # Trigger event to generate embeddings and match to candidates
            inngest_client.send_sync(
                inngest.Event(
                    name="email-jobs/match-to-candidates",
                    data={
                        "job_ids": job_ids,
                        "tenant_id": tenant_id,
                        "source": "email",
                    }
                )
            )
            return {"triggered": True, "job_count": len(job_ids)}
        
        await ctx.step.run("trigger-email-job-matching", trigger_email_job_matching)
    
    # Step 5: Update last_synced_at AFTER all emails processed successfully
    # This ensures idempotency - if Inngest retries, we re-process the same emails
    def update_sync_timestamp():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.services.email_sync_service import email_sync_service
            
            new_history_id = sync_result.get("new_history_id")
            email_sync_service.update_sync_timestamp(integration_id, new_history_id)
            return {"updated": True}
    
    await ctx.step.run("update-sync-timestamp", update_sync_timestamp)
    
    return {
        "status": "completed",
        "fetched": sync_result.get("fetched", 0),
        "matched": sync_result.get("matched", 0),
        "already_processed": sync_result.get("already_processed", 0),
        "jobs_created": jobs_created,
        "job_ids": created_job_ids,
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
async def manual_sync_workflow(ctx: inngest.Context) -> dict:
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
    
    integrations = await ctx.step.run("get-user-integrations", get_user_integrations)
    
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


# ============================================================================
# Email Job Matching - Generate embeddings and match to candidates
# ============================================================================

@inngest_client.create_function(
    fn_id="match-email-jobs-to-candidates",
    trigger=inngest.TriggerEvent(event="email-jobs/match-to-candidates"),
    name="Match Email Jobs to Candidates",
    retries=3,
)
async def match_email_jobs_to_candidates_workflow(ctx: inngest.Context) -> dict:
    """
    Generate embeddings for email-sourced jobs and match them to candidates.
    
    This is similar to the scraped job matching but works differently:
    - Email jobs don't have a global_role_id
    - Instead, we match based on the job title/role to candidates in the same tenant
    - We find candidates whose preferred_roles or global_roles contain similar roles
    
    Event data:
        job_ids: list[int] - IDs of newly created email-sourced jobs
        tenant_id: int - Tenant that owns the jobs
        source: str - Always "email"
    """
    event_data = ctx.event.data
    job_ids = event_data.get("job_ids", [])
    tenant_id = event_data.get("tenant_id")
    
    if not job_ids:
        logger.info("[INNGEST] No email jobs to process for matching")
        return {"status": "completed", "matches_created": 0}
    
    logger.info(f"[INNGEST] Processing {len(job_ids)} email jobs for matching in tenant {tenant_id}")
    
    # Step 1: Generate embeddings for jobs
    def generate_job_embeddings():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            from app.models.job_posting import JobPosting
            from app.services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            embeddings_generated = 0
            job_infos = []
            
            for job_id in job_ids:
                job = db.session.get(JobPosting, job_id)
                if not job:
                    continue
                
                # Generate embedding if missing
                if job.embedding is None:
                    try:
                        embedding = embedding_service.generate_job_embedding(job)
                        if embedding:
                            job.embedding = embedding
                            embeddings_generated += 1
                    except Exception as e:
                        logger.error(f"[INNGEST] Failed to generate embedding for job {job_id}: {e}")
                        continue
                
                job_infos.append({
                    "id": job.id,
                    "title": job.title,
                    "source_tenant_id": job.source_tenant_id,
                })
            
            db.session.commit()
            return {
                "embeddings_generated": embeddings_generated,
                "jobs_processed": len(job_infos),
                "job_infos": job_infos,
            }
    
    embedding_result = await ctx.step.run("generate-email-job-embeddings", generate_job_embeddings)
    
    logger.info(
        f"[INNGEST] Generated {embedding_result['embeddings_generated']} embeddings "
        f"for {embedding_result['jobs_processed']} email jobs"
    )
    
    # Step 2: Find candidates in tenant and generate matches
    def generate_candidate_matches():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            from app.models.job_posting import JobPosting
            from app.models.candidate import Candidate
            from app.models.candidate_job_match import CandidateJobMatch
            from app.services.job_matching_service import JobMatchingService
            from sqlalchemy import select
            
            # Get all approved candidates in tenant with embeddings
            stmt = select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status.in_(['approved', 'ready_for_assignment']),
                Candidate.embedding.isnot(None),
            )
            candidates = list(db.session.scalars(stmt).all())
            
            if not candidates:
                logger.info(f"[INNGEST] No matching candidates found in tenant {tenant_id}")
                return {"candidates_found": 0, "matches_created": 0}
            
            # Initialize matching service
            # Use UnifiedScorerService for consistent scoring
            from app.services.unified_scorer_service import UnifiedScorerService
            unified_scorer = UnifiedScorerService()
            matches_created = 0
            
            # For each job, calculate match scores against all candidates
            for job_id in job_ids:
                job = db.session.get(JobPosting, job_id)
                if not job or job.embedding is None:
                    continue
                
                for candidate in candidates:
                    try:
                        # Check if match already exists
                        existing = CandidateJobMatch.query.filter_by(
                            candidate_id=candidate.id,
                            job_posting_id=job.id,
                        ).first()
                        
                        if existing:
                            continue
                        
                        # Calculate and store match using unified scorer
                        match = unified_scorer.calculate_and_store_match(candidate, job)
                        
                        if match and match.match_score >= 50:
                            matches_created += 1
                    
                    except Exception as e:
                        logger.error(
                            f"[INNGEST] Error creating match for candidate {candidate.id} "
                            f"and job {job.id}: {e}"
                        )
                        continue
            
            db.session.commit()
            return {
                "candidates_found": len(candidates),
                "matches_created": matches_created,
            }
    
    match_result = await ctx.step.run("generate-candidate-matches", generate_candidate_matches)
    
    logger.info(
        f"[INNGEST] Created {match_result['matches_created']} matches "
        f"from {match_result['candidates_found']} candidates"
    )
    
    return {
        "status": "completed",
        "jobs_processed": embedding_result["jobs_processed"],
        "embeddings_generated": embedding_result["embeddings_generated"],
        "candidates_found": match_result["candidates_found"],
        "matches_created": match_result["matches_created"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Phase 6: ProcessedEmail Cleanup - Data Retention
# ============================================================================

@inngest_client.create_function(
    fn_id="cleanup-old-processed-emails",
    trigger=inngest.TriggerCron(cron="0 3 * * *"),  # Daily at 3 AM
    name="Cleanup Old Processed Emails",
    retries=2,
)
async def cleanup_old_processed_emails_workflow(ctx: inngest.Context) -> dict:
    """
    Phase 6: Clean up old ProcessedEmail records to control table growth.
    
    Runs daily at 3 AM. Deletes records older than 90 days to prevent
    unbounded table growth while maintaining reasonable audit history.
    
    At scale (1000 users × 50 emails/day × 365 days = 18M+ rows/year),
    this cleanup prevents database bloat and maintains query performance.
    """
    logger.info("[INNGEST] Starting processed emails cleanup")
    
    RETENTION_DAYS = 90  # Keep 90 days of history
    
    def cleanup_old_records():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            from app.models.processed_email import ProcessedEmail
            from sqlalchemy import delete
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
            
            # Count records to be deleted first (for reporting)
            count_to_delete = ProcessedEmail.query.filter(
                ProcessedEmail.created_at < cutoff_date
            ).count()
            
            if count_to_delete == 0:
                return {"deleted": 0, "message": "No old records to delete"}
            
            # Delete in batches to avoid long locks
            batch_size = 10000
            total_deleted = 0
            
            while True:
                # Delete a batch
                stmt = delete(ProcessedEmail).where(
                    ProcessedEmail.created_at < cutoff_date
                ).execution_options(synchronize_session=False)
                
                # Use LIMIT-like approach for batch deletion
                subquery = ProcessedEmail.query.filter(
                    ProcessedEmail.created_at < cutoff_date
                ).limit(batch_size).with_entities(ProcessedEmail.id).subquery()
                
                result = db.session.execute(
                    delete(ProcessedEmail).where(ProcessedEmail.id.in_(
                        db.session.query(subquery.c.id)
                    ))
                )
                
                deleted_count = result.rowcount
                total_deleted += deleted_count
                db.session.commit()
                
                logger.info(f"[INNGEST] Deleted batch of {deleted_count} processed emails")
                
                if deleted_count < batch_size:
                    break  # No more records to delete
            
            return {
                "deleted": total_deleted,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": RETENTION_DAYS,
            }
    
    result = await ctx.step.run("cleanup-processed-emails", cleanup_old_records)
    
    logger.info(f"[INNGEST] Cleanup completed: deleted {result.get('deleted', 0)} old records")
    
    return {
        "status": "completed",
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Circuit Breaker Status Check (for monitoring)
# ============================================================================

@inngest_client.create_function(
    fn_id="check-circuit-breaker-status",
    trigger=inngest.TriggerEvent(event="email/check-circuit-status"),
    name="Check Circuit Breaker Status",
    retries=1,
)
async def check_circuit_breaker_status_workflow(ctx: inngest.Context) -> dict:
    """
    Phase 7: Check and report circuit breaker status for monitoring.
    
    Useful for dashboards and alerting on external service health.
    """
    from app.utils.circuit_breaker import (
        gmail_circuit_breaker,
        outlook_circuit_breaker,
        gemini_circuit_breaker,
    )
    
    return {
        "status": "completed",
        "circuit_breakers": {
            "gmail": gmail_circuit_breaker.get_status(),
            "outlook": outlook_circuit_breaker.get_status(),
            "gemini": gemini_circuit_breaker.get_status(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
