"""
Scheduled Tasks (Cron Jobs)
Automated background jobs that run on schedule
"""
import logging
from datetime import datetime, timedelta

import inngest

from app.inngest import inngest_client

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="check-expiring-invitations",
    trigger=inngest.TriggerCron(cron="0 9 * * *"),
    name="Check Expiring Invitations"
)
async def check_expiring_invitations_workflow(ctx: inngest.Context) -> dict:
    """
    Send reminder emails for invitations expiring in 24 hours
    Runs daily at 9 AM
    """
    logger.info("[INNGEST] Running expiring invitations check")
    
    # Step 1: Fetch expiring invitations
    expiring_invitations = await ctx.step.run(
        "fetch-expiring",
        fetch_expiring_invitations_step,
        hours=24
    )
    
    logger.info(f"[INNGEST] Found {len(expiring_invitations)} expiring invitations")
    
    # Step 2: Send reminder emails
    for invitation in expiring_invitations:
        await ctx.step.run(
            f"send-reminder-{invitation['id']}",
            send_reminder_email_step,
            invitation
        )
    
    return {
        "invitations_checked": len(expiring_invitations),
        "reminders_sent": len(expiring_invitations)
    }


@inngest_client.create_function(
    fn_id="generate-daily-stats",
    trigger=inngest.TriggerCron(cron="0 8 * * *"),
    name="Generate Daily Statistics"
)
async def generate_daily_stats_workflow(ctx: inngest.Context) -> dict:
    """
    Generate daily recruiting statistics
    Runs daily at 8 AM
    """
    logger.info("[INNGEST] Generating daily statistics")
    
    # Step 1: Calculate metrics for all tenants
    all_stats = await ctx.step.run(
        "calculate-all-stats",
        calculate_daily_stats_step
    )
    
    # Step 2: Store in cache/database
    await ctx.step.run(
        "store-stats",
        store_stats_step,
        all_stats
    )
    
    logger.info(f"[INNGEST] Generated stats for {len(all_stats)} tenants")
    
    return {"tenants_processed": len(all_stats)}


# Step Functions

def fetch_expiring_invitations_step(hours: int = 24) -> list:
    """Fetch invitations expiring within specified hours"""
    from app import db
    from app.models.candidate_invitation import CandidateInvitation
    from sqlalchemy import select
    
    threshold = datetime.utcnow() + timedelta(hours=hours)
    now = datetime.utcnow()
    
    query = select(CandidateInvitation).where(
        CandidateInvitation.status == 'invited',
        CandidateInvitation.expires_at <= threshold,
        CandidateInvitation.expires_at > now
    )
    
    invitations = db.session.execute(query).scalars().all()
    
    return [
        {
            "id": inv.id,
            "email": inv.email,
            "first_name": inv.first_name,
            "last_name": inv.last_name,
            "token": inv.token,
            "tenant_id": inv.tenant_id,
            "expires_at": inv.expires_at.isoformat()
        }
        for inv in invitations
    ]


def send_reminder_email_step(invitation: dict) -> bool:
    """Send reminder email for expiring invitation"""
    from app.inngest import inngest_client
    import inngest
    
    # Send email event (will be processed by email workflow)
    inngest_client.send_sync(
        inngest.Event(
            name="email/reminder",
            data={
                "invitation_id": invitation["id"],
                "tenant_id": invitation["tenant_id"],
                "email": invitation["email"],
                "candidate_name": f"{invitation.get('first_name', '')} {invitation.get('last_name', '')}".strip(),
                "hours_remaining": 24
            }
        )
    )
    
    logger.info(f"[INNGEST] Sent reminder email event for invitation {invitation['id']}")
    return True


def calculate_daily_stats_step() -> dict:
    """Calculate daily statistics for all tenants"""
    from app import db
    from app.models.tenant import Tenant
    from app.models.candidate import Candidate
    from app.models.candidate_invitation import CandidateInvitation
    from sqlalchemy import select, func
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    today = datetime.utcnow()
    
    # Get all active tenants
    tenants = db.session.execute(select(Tenant).where(Tenant.is_active == True)).scalars().all()
    
    all_stats = {}
    
    for tenant in tenants:
        # Count new candidates
        new_candidates = db.session.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant.id,
                Candidate.created_at >= yesterday,
                Candidate.created_at < today
            )
        ) or 0
        
        # Count new invitations
        new_invitations = db.session.scalar(
            select(func.count()).select_from(CandidateInvitation).where(
                CandidateInvitation.tenant_id == tenant.id,
                CandidateInvitation.created_at >= yesterday,
                CandidateInvitation.created_at < today
            )
        ) or 0
        
        # Count submissions
        submissions = db.session.scalar(
            select(func.count()).select_from(CandidateInvitation).where(
                CandidateInvitation.tenant_id == tenant.id,
                CandidateInvitation.status == 'pending_review',
                CandidateInvitation.submitted_at >= yesterday,
                CandidateInvitation.submitted_at < today
            )
        ) or 0
        
        all_stats[tenant.id] = {
            "tenant_name": tenant.company_name,
            "date": yesterday.strftime("%Y-%m-%d"),
            "new_candidates": new_candidates,
            "new_invitations": new_invitations,
            "new_submissions": submissions
        }
    
    return all_stats


def store_stats_step(stats: dict) -> None:
    """Store statistics in Redis cache"""
    from app import get_redis
    import json
    
    redis_client = get_redis()
    if not redis_client:
        logger.warning("[INNGEST] Redis not available, skipping stats storage")
        return
    
    # Store in Redis with 30-day expiry
    for tenant_id, tenant_stats in stats.items():
        key = f"stats:daily:{tenant_id}:{tenant_stats['date']}"
        redis_client.setex(
            key,
            30 * 24 * 60 * 60,  # 30 days
            json.dumps(tenant_stats)
        )
    
    logger.info(f"[INNGEST] Stored daily stats for {len(stats)} tenants in Redis")


# ============================================================================
# SCRAPE QUEUE SCHEDULED TASKS
# ============================================================================

@inngest_client.create_function(
    fn_id="cleanup-stale-scrape-sessions",
    trigger=inngest.TriggerCron(cron="*/15 * * * *"),  # Every 15 minutes
    name="Cleanup Stale Scrape Sessions"
)
async def cleanup_stale_sessions_workflow(ctx: inngest.Context) -> dict:
    """
    Cleanup scrape sessions stuck in 'processing' state and reset stuck queue entries.
    Runs every 15 minutes.
    
    Sessions older than 1 hour in processing state are:
    1. Marked as 'timeout'
    2. Role is reset to 'approved' for retry
    3. RoleLocationQueue entry is reset to 'approved' for retry
    
    Also resets any RoleLocationQueue entries stuck in 'processing' or 'completed'.
    """
    logger.info("[INNGEST] Running stale scrape session cleanup")
    
    # Step 1: Cleanup stale sessions and reset stuck queue entries
    cleanup_result = await ctx.step.run(
        "cleanup-stale-sessions",
        cleanup_stale_sessions_step
    )
    
    logger.info(
        f"[INNGEST] Cleanup complete: {cleanup_result.get('sessions_timed_out', 0)} sessions timed out, "
        f"{cleanup_result.get('role_location_stuck_reset', 0)} stuck queue entries reset"
    )
    
    return {
        "cleanup_result": cleanup_result,
        "timestamp": datetime.utcnow().isoformat()
    }


@inngest_client.create_function(
    fn_id="reset-completed-roles",
    trigger=inngest.TriggerCron(cron="0 0 * * *"),  # Midnight daily
    name="Reset Completed Roles for New Scraping"
)
async def reset_completed_roles_workflow(ctx: inngest.Context) -> dict:
    """
    Reset completed roles back to pending for daily fresh scraping.
    Runs daily at midnight.
    
    This ensures:
    1. Jobs are refreshed daily with new postings
    2. Roles with active candidates are prioritized
    """
    logger.info("[INNGEST] Running completed roles reset")
    
    # Step 1: Reset completed roles
    reset_count = await ctx.step.run(
        "reset-completed-roles",
        reset_completed_roles_step
    )
    
    logger.info(f"[INNGEST] Reset {reset_count} roles back to pending")
    
    return {
        "roles_reset": reset_count,
        "timestamp": datetime.utcnow().isoformat()
    }


@inngest_client.create_function(
    fn_id="update-role-candidate-counts",
    trigger=inngest.TriggerCron(cron="0 */6 * * *"),  # Every 6 hours
    name="Update Role Candidate Counts"
)
async def update_role_candidate_counts_workflow(ctx: inngest.Context) -> dict:
    """
    Recalculate candidate counts for all global roles.
    Runs every 6 hours.
    
    This ensures accurate priority-based queue ordering.
    """
    logger.info("[INNGEST] Updating role candidate counts")
    
    # Step 1: Update counts
    updated_count = await ctx.step.run(
        "update-candidate-counts",
        update_candidate_counts_step
    )
    
    logger.info(f"[INNGEST] Updated candidate counts for {updated_count} roles")
    
    return {
        "roles_updated": updated_count,
        "timestamp": datetime.utcnow().isoformat()
    }


# Step Functions for Scrape Queue Tasks

def cleanup_stale_sessions_step() -> dict:
    """Cleanup stale scrape sessions and reset stuck RoleLocationQueue entries"""
    from app.services.scrape_queue_service import ScrapeQueueService
    
    # Cleanup stale sessions (also resets associated RoleLocationQueue entries)
    session_result = ScrapeQueueService.cleanup_stale_sessions()
    
    # Also reset any stuck RoleLocationQueue entries (processing without active session, or completed)
    queue_result = ScrapeQueueService.reset_stuck_role_location_queue()
    
    return {
        "sessions_timed_out": session_result.get("timed_out", 0),
        "role_location_from_sessions": session_result.get("role_location_reset", 0),
        "role_location_stuck_reset": queue_result.get("total_reset", 0)
    }


def reset_completed_roles_step() -> dict:
    """Reset completed roles back to pending"""
    from app.services.scrape_queue_service import ScrapeQueueService
    result = ScrapeQueueService.reset_completed_roles()
    return result.get("reset_count", 0)


def update_candidate_counts_step() -> int:
    """Update candidate counts for all roles"""
    from app import db
    from app.models.global_role import GlobalRole
    from app.models.candidate_global_role import CandidateGlobalRole
    from sqlalchemy import select, func
    
    # Get count per role
    counts_query = (
        select(
            CandidateGlobalRole.global_role_id,
            func.count(CandidateGlobalRole.candidate_id).label('count')
        )
        .group_by(CandidateGlobalRole.global_role_id)
    )
    
    counts = {row[0]: row[1] for row in db.session.execute(counts_query).all()}
    
    # Update all roles
    roles = db.session.execute(select(GlobalRole)).scalars().all()
    
    for role in roles:
        new_count = counts.get(role.id, 0)
        if role.candidate_count != new_count:
            role.candidate_count = new_count
    
    db.session.commit()
    
    logger.info(f"[INNGEST] Updated candidate counts for {len(roles)} roles")
    return len(roles)


# ============================================================================
# SCRAPER CREDENTIALS SCHEDULED TASKS
# ============================================================================

@inngest_client.create_function(
    fn_id="cleanup-stale-scraper-credentials",
    trigger=inngest.TriggerCron(cron="*/10 * * * *"),  # Every 10 minutes
    name="Cleanup Stale Scraper Credentials"
)
async def cleanup_stale_credentials_workflow(ctx) -> dict:
    """
    Cleanup scraper credentials stuck in 'in_use' state.
    Runs every 10 minutes.
    
    Credentials assigned for more than 60 minutes are released
    to prevent being stuck if a scraper crashes.
    """
    logger.info("[INNGEST] Running stale scraper credentials cleanup")
    
    # Step 1: Cleanup stale assignments
    stale_count = await ctx.step.run(
        "cleanup-stale-credentials",
        cleanup_stale_credentials_step
    )
    
    logger.info(f"[INNGEST] Released {stale_count} stale credentials")
    
    return {
        "credentials_released": stale_count,
        "timestamp": datetime.utcnow().isoformat()
    }


@inngest_client.create_function(
    fn_id="clear-expired-credential-cooldowns",
    trigger=inngest.TriggerCron(cron="*/5 * * * *"),  # Every 5 minutes
    name="Clear Expired Credential Cooldowns"
)
async def clear_credential_cooldowns_workflow(ctx) -> dict:
    """
    Clear cooldown status for credentials whose cooldown has expired.
    Runs every 5 minutes.
    
    Credentials in 'cooldown' status with expired cooldown_until
    are moved back to 'available'.
    """
    logger.info("[INNGEST] Running credential cooldown expiry check")
    
    # Step 1: Clear expired cooldowns
    cleared_count = await ctx.step.run(
        "clear-expired-cooldowns",
        clear_expired_cooldowns_step
    )
    
    logger.info(f"[INNGEST] Cleared cooldown for {cleared_count} credentials")
    
    return {
        "cooldowns_cleared": cleared_count,
        "timestamp": datetime.utcnow().isoformat()
    }


# Step Functions for Scraper Credentials Tasks

def cleanup_stale_credentials_step() -> int:
    """Release credentials stuck in 'in_use' state for too long"""
    from app.services.scraper_credential_service import ScraperCredentialService
    return ScraperCredentialService.cleanup_stale_assignments(timeout_minutes=60)


def clear_expired_cooldowns_step() -> int:
    """Clear expired cooldown status from credentials"""
    from app.services.scraper_credential_service import ScraperCredentialService
    return ScraperCredentialService.clear_expired_cooldowns()


# ============================================================================
# JOB ROLE NORMALIZATION BACKFILL
# ============================================================================

@inngest_client.create_function(
    fn_id="backfill-orphaned-job-roles",
    trigger=inngest.TriggerCron(cron="0 */3 * * *"),  # Every 3 hours
    name="Backfill Orphaned Job Roles",
    retries=2
)
async def backfill_orphaned_job_roles_workflow(ctx) -> dict:
    """
    Find job postings with no normalized_role_id (orphaned during email import
    when role normalization failed) and retry normalization.

    Runs every 3 hours. Processes up to 50 jobs per run to avoid overloading
    the Gemini API.
    """
    logger.info("[INNGEST] Running orphaned job role backfill")

    # Step 1: Find orphaned jobs
    orphaned_jobs = await ctx.step.run(
        "find-orphaned-jobs",
        find_orphaned_jobs_step
    )

    if not orphaned_jobs:
        logger.info("[INNGEST] No orphaned jobs found")
        return {"orphaned_found": 0, "normalized": 0, "failed": 0}

    logger.info(f"[INNGEST] Found {len(orphaned_jobs)} orphaned jobs to normalize")

    # Step 2: Normalize each job (one step per job for retryability)
    normalized = 0
    failed = 0

    for job_info in orphaned_jobs:
        try:
            result = await ctx.step.run(
                f"normalize-job-{job_info['id']}",
                normalize_orphaned_job_step,
                job_info
            )
            if result.get("success"):
                normalized += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(
                f"[INNGEST] Failed to normalize job {job_info['id']}: {e}"
            )
            failed += 1

    logger.info(
        f"[INNGEST] Backfill complete: {normalized} normalized, {failed} failed "
        f"out of {len(orphaned_jobs)} orphaned jobs"
    )

    return {
        "orphaned_found": len(orphaned_jobs),
        "normalized": normalized,
        "failed": failed
    }


def find_orphaned_jobs_step() -> list:
    """Find job postings without a normalized_role_id (max 50)."""
    from app import db
    from app.models.job_posting import JobPosting
    from sqlalchemy import select

    stmt = (
        select(JobPosting.id, JobPosting.title)
        .where(
            JobPosting.normalized_role_id.is_(None),
            JobPosting.title.isnot(None),
            JobPosting.title != ""
        )
        .order_by(JobPosting.created_at.desc())
        .limit(50)
    )

    rows = db.session.execute(stmt).all()

    return [{"id": row[0], "title": row[1]} for row in rows]


def normalize_orphaned_job_step(job_info: dict) -> dict:
    """Normalize a single orphaned job's title and create its RoleJobMapping."""
    from app import db
    from app.services.ai_role_normalization_service import AIRoleNormalizationService

    job_id = job_info["id"]
    job_title = job_info["title"]

    logger.info(f"[INNGEST] Backfill normalizing job {job_id}: '{job_title}'")

    try:
        service = AIRoleNormalizationService()
        global_role, similarity, method = service.normalize_job_title(
            job_title=job_title,
            job_posting_id=job_id
        )

        if global_role:
            db.session.commit()
            logger.info(
                f"[INNGEST] Job {job_id} linked to role '{global_role.name}' "
                f"(similarity: {similarity:.2%}, method: {method})"
            )
            return {
                "success": True,
                "job_id": job_id,
                "role_name": global_role.name,
                "similarity": similarity,
                "method": method
            }
        else:
            logger.warning(f"[INNGEST] Normalization returned None for job {job_id}")
            return {"success": False, "job_id": job_id, "reason": "normalization_returned_none"}

    except Exception as e:
        db.session.rollback()
        logger.error(f"[INNGEST] Error normalizing job {job_id}: {e}", exc_info=True)
        return {"success": False, "job_id": job_id, "reason": str(e)}

