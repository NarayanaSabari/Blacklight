"""
Job Import Inngest Workflows

Handles asynchronous job importing from external scrapers with multi-platform support.

Workflows:
1. jobs/scraper.platform-import - Import jobs for a single platform
2. jobs/scraper.complete - Finalize session and trigger matching

Benefits:
- Non-blocking API response
- Per-platform import tracking
- Retryable with exponential backoff
- Better error handling and observability
- Can handle large job batches without timeout
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import UUID
import inngest
from sqlalchemy import or_

from app import db
from app.models.scrape_session import ScrapeSession
from app.models.scraper_api_key import ScraperApiKey
from app.models.global_role import GlobalRole
from app.models.job_posting import JobPosting
from app.models.role_job_mapping import RoleJobMapping
from app.models.session_platform_status import SessionPlatformStatus
from app.models.scraper_platform import ScraperPlatform
from app.inngest import inngest_client

logger = logging.getLogger(__name__)


# ============================================================================
# WORKFLOW 1: Platform Import (per-platform job import)
# ============================================================================

@inngest_client.create_function(
    fn_id="job-import-platform",
    trigger=inngest.TriggerEvent(event="jobs/scraper.platform-import"),
    name="Import Jobs for Platform",
    retries=3
)
async def import_platform_jobs_fn(ctx: inngest.Context) -> dict:
    """
    Import jobs for a single platform within a session.
    
    Event data:
    {
        "session_id": "uuid",
        "scraper_key_id": 123,
        "platform_name": "linkedin",
        "platform_status_id": 456,
        "jobs": [...],
        "jobs_count": 47
    }
    """
    event_data = ctx.event.data
    session_id = event_data["session_id"]
    scraper_key_id = event_data["scraper_key_id"]
    platform_name = event_data["platform_name"]
    platform_status_id = event_data["platform_status_id"]
    jobs_data = event_data["jobs"]
    
    logger.info(
        f"[JOB-IMPORT] Starting import for platform '{platform_name}' "
        f"in session {session_id} with {len(jobs_data)} jobs"
    )
    
    # Step 1: Validate session and platform status
    session_data = await ctx.step.run(
        "validate-session",
        lambda: validate_session_for_platform(session_id, scraper_key_id, platform_status_id)
    )
    
    if not session_data:
        logger.error(f"[JOB-IMPORT] ❌ Session {session_id} or platform status not found")
        return {"status": "error", "message": "Invalid session or platform"}
    
    # Step 2: Import jobs for this platform
    import_result = await ctx.step.run(
        "import-jobs",
        lambda: import_jobs_batch_for_platform(jobs_data, session_data, platform_name)
    )
    
    # Step 3: Update platform status to completed
    await ctx.step.run(
        "complete-platform",
        lambda: complete_platform_status(
            platform_status_id,
            session_id,
            scraper_key_id,
            len(jobs_data),
            import_result["imported"],
            import_result["skipped"]
        )
    )
    
    logger.info(
        f"[JOB-IMPORT] ✅ Platform '{platform_name}' completed: "
        f"{import_result['imported']} imported, {import_result['skipped']} skipped"
    )
    
    return {
        "status": "success",
        "platform": platform_name,
        "jobs_imported": import_result["imported"],
        "jobs_skipped": import_result["skipped"],
        "job_ids": import_result["job_ids"]
    }


# ============================================================================
# WORKFLOW 2: Session Complete (finalize and trigger matching)
# ============================================================================

@inngest_client.create_function(
    fn_id="job-import-complete",
    trigger=inngest.TriggerEvent(event="jobs/scraper.complete"),
    name="Complete Scrape Session",
    retries=3
)
async def complete_scrape_session_fn(ctx: inngest.Context) -> dict:
    """
    Finalize a scrape session and trigger job matching.
    
    Event data:
    {
        "session_id": "uuid",
        "scraper_key_id": 123
    }
    """
    event_data = ctx.event.data
    session_id = event_data["session_id"]
    scraper_key_id = event_data["scraper_key_id"]
    
    logger.info(f"[JOB-IMPORT] Completing session {session_id}")
    
    # Step 1: Aggregate platform results
    session_stats = await ctx.step.run(
        "aggregate-stats",
        lambda: aggregate_session_stats(session_id)
    )
    
    # Step 2: Update session to completed
    await ctx.step.run(
        "finalize-session",
        lambda: finalize_session(session_id, scraper_key_id, session_stats)
    )
    
    # Step 3: Update role status (GlobalRole)
    await ctx.step.run(
        "update-role-status",
        lambda: update_role_status(session_stats["global_role_id"], session_stats["total_imported"])
    )
    
    # Step 4: Update RoleLocationQueue status (for location-based scraping)
    await ctx.step.run(
        "update-role-location-queue",
        lambda: update_role_location_queue_status(session_id, session_stats["total_imported"])
    )
    
    # Step 5: Trigger job matching if jobs were imported
    if session_stats["total_imported"] > 0:
        await ctx.step.run(
            "trigger-job-matching",
            lambda: trigger_job_matching(
                job_ids=session_stats["job_ids"],
                global_role_id=session_stats["global_role_id"],
                role_name=session_stats["role_name"],
                session_id=session_id
            )
        )
    
    logger.info(
        f"[JOB-IMPORT] ✅ Session {session_id} completed: "
        f"{session_stats['total_imported']} jobs imported from "
        f"{session_stats['successful_platforms']}/{session_stats['total_platforms']} platforms"
    )
    
    return {
        "status": "success",
        "session_id": session_id,
        "total_imported": session_stats["total_imported"],
        "platforms_successful": session_stats["successful_platforms"],
        "platforms_failed": session_stats["failed_platforms"]
    }


# ============================================================================
# HELPER FUNCTIONS - Session Validation
# ============================================================================

def validate_session_for_platform(
    session_id: str,
    scraper_key_id: int,
    platform_status_id: int
) -> Optional[Dict[str, Any]]:
    """Validate session and platform status exist and are in correct state."""
    session = ScrapeSession.query.filter_by(
        session_id=UUID(session_id),
        scraper_key_id=scraper_key_id
    ).first()
    
    if not session:
        logger.error(f"Session {session_id} not found")
        return None
    
    if session.status not in ("in_progress", "pending"):
        logger.error(f"Session {session_id} has invalid status: {session.status}")
        return None
    
    # Validate platform status exists
    platform_status = db.session.get(SessionPlatformStatus, platform_status_id)
    if not platform_status:
        logger.error(f"Platform status {platform_status_id} not found")
        return None
    
    # Return serializable dict (not ORM object)
    return {
        "session_id": str(session.session_id),
        "scraper_key_id": session.scraper_key_id,
        "global_role_id": session.global_role_id,
        "role_name": session.role_name,
        "platform_status_id": platform_status_id
    }


# ============================================================================
# HELPER FUNCTIONS - Job Import
# ============================================================================

def import_jobs_batch_for_platform(
    jobs_data: List[Dict],
    session_data: Dict[str, Any],
    platform_name: str
) -> Dict[str, Any]:
    """
    Import batch of jobs for a specific platform with deduplication.
    
    Your job schema fields:
    - platform: "linkedin" | "indeed" | "monster" | "dice" | "glassdoor" | "techfetch"
    - jobId: string (external ID)
    - title: string
    - company: string
    - location: string
    - salary: string
    - postedDate: "YYYY-MM-DD" | "N/A"
    - jobUrl: URL | "N/A"
    - applyUrl: URL | "N/A"
    - description: string
    - snippet: string
    - experience: string
    - skills: string[]
    - jobType: string
    - isRemote: boolean
    - metadata: { extractedAt, platformSpecific }
    
    Returns:
        Dict with imported count, skipped count, and job IDs
    """
    from app.services.job_import_service import JobImportService
    
    job_import_service = JobImportService()
    scraper_key = db.session.get(ScraperApiKey, session_data["scraper_key_id"])
    
    imported_count = 0
    skipped_count = 0
    job_ids = []
    
    logger.info(
        f"[JOB-IMPORT] Processing {len(jobs_data)} jobs from {platform_name} "
        f"for role '{session_data['role_name']}'"
    )
    
    # Track skip reasons for debugging
    skip_reasons = {
        "missing_required": 0,
        "duplicate_platform_id": 0,
        "duplicate_title_company_location": 0,
        "duplicate_title_company_description": 0,
        "error": 0
    }
    
    # Helper to truncate strings to fit database varchar limits
    def truncate_str(value, max_len):
        if value and isinstance(value, str) and len(value) > max_len:
            return value[:max_len]
        return value
    
    for idx, job_data in enumerate(jobs_data):
        try:
            # Map your schema field names to our internal names
            external_id = job_data.get("jobId") or job_data.get("job_id") or job_data.get("external_job_id") or job_data.get("external_id")
            platform = job_data.get("platform", platform_name)
            
            # Truncate external_id if too long (VARCHAR(255) limit)
            # Use hash suffix for very long IDs to maintain uniqueness
            if external_id and len(str(external_id)) > 255:
                import hashlib
                ext_id_str = str(external_id)
                # Use first 200 chars + hash of full ID to maintain uniqueness
                id_hash = hashlib.md5(ext_id_str.encode()).hexdigest()[:32]
                external_id = f"{ext_id_str[:200]}...{id_hash}"
                logger.debug(f"[JOB-IMPORT] Truncated long external_id to {len(external_id)} chars")
            
            # Validate required fields
            title = job_data.get("title")
            company = job_data.get("company")
            location = job_data.get("location", "")
            description = job_data.get("description", "")
            
            if not title or not company:
                logger.warning(f"[JOB-IMPORT] Skipping job {idx+1}: Missing title or company")
                skipped_count += 1
                skip_reasons["missing_required"] += 1
                continue
            
            # =================================================================
            # DEDUPLICATION STRATEGY (in order of priority):
            # 1. Same platform + external_job_id = exact duplicate
            # 2. Same title + company + location = likely same job
            # 3. Same title + company + similar description = same job different platform
            # =================================================================
            
            # Check 1: Exact duplicate by platform + external_job_id
            if external_id:
                existing = JobPosting.query.filter_by(
                    platform=platform,
                    external_job_id=str(external_id)
                ).first()
                
                if existing:
                    logger.info(f"[JOB-IMPORT] Skipping duplicate (platform+id): platform={platform}, id={external_id}")
                    skipped_count += 1
                    skip_reasons["duplicate_platform_id"] += 1
                    continue
            
            # Check 2: Duplicate by title + company + location (case-insensitive)
            # This catches the same job posted on different platforms
            # Build query filters dynamically to handle empty location correctly
            content_filters = [
                db.func.lower(JobPosting.title) == title.lower().strip(),
                db.func.lower(JobPosting.company) == company.lower().strip(),
            ]
            
            # Only add location filter if we have a location to compare
            if location and location.strip():
                content_filters.append(
                    db.func.lower(JobPosting.location) == location.lower().strip()
                )
            else:
                # If no location provided, only match jobs that also have no location
                content_filters.append(
                    or_(
                        JobPosting.location.is_(None),
                        JobPosting.location == "",
                        db.func.trim(JobPosting.location) == ""
                    )
                )
            
            existing_by_content = JobPosting.query.filter(*content_filters).first()
            
            if existing_by_content:
                logger.info(
                    f"[JOB-IMPORT] Skipping duplicate (title+company+location): "
                    f"'{title}' at '{company}' in '{location}' (existing job id={existing_by_content.id})"
                )
                skipped_count += 1
                skip_reasons["duplicate_title_company_location"] += 1
                continue
            
            # Check 3: Similar job by title + company + description prefix
            # Only skip if description start is identical (same job posting text)
            # This catches exact reposts but allows different jobs at same company
            if description and len(description) >= 100:
                desc_prefix = description[:100].lower().strip()
                existing_similar = JobPosting.query.filter(
                    db.func.lower(JobPosting.title) == title.lower().strip(),
                    db.func.lower(JobPosting.company) == company.lower().strip(),
                    db.func.left(db.func.lower(JobPosting.description), 100) == desc_prefix
                ).first()
                
                if existing_similar:
                    logger.info(
                        f"[JOB-IMPORT] Skipping duplicate (title+company+description): "
                        f"'{title}' at '{company}' (existing job id={existing_similar.id})"
                    )
                    skipped_count += 1
                    skip_reasons["duplicate_title_company_description"] += 1
                    continue
            
            # Parse salary
            salary_str = job_data.get("salary", "")
            salary_min, salary_max, currency = job_import_service.parse_salary(salary_str)
            
            # Parse experience
            experience_str = job_data.get("experience", "")
            exp_min, exp_max = job_import_service.parse_experience(experience_str, description)
            
            # Parse and normalize skills
            raw_skills = job_data.get("skills", [])
            normalized_skills = job_import_service.normalize_skills(raw_skills)
            
            # Parse posted date
            posted_date_str = job_data.get("postedDate", job_data.get("posted_date", ""))
            posted_date = job_import_service.parse_posted_date(posted_date_str)
            
            # Detect remote
            is_remote = job_import_service.detect_remote(
                job_data.get("location", ""),
                description,
                job_data.get("isRemote", job_data.get("is_remote"))
            )
            
            # Handle "N/A" values for URLs
            job_url = job_data.get("jobUrl", job_data.get("job_url", ""))
            if job_url == "N/A":
                job_url = ""
            
            apply_url = job_data.get("applyUrl", job_data.get("apply_url"))
            if apply_url == "N/A":
                apply_url = None
            
            # Get job_type and truncate to fit database limits
            job_type_raw = job_data.get("jobType", job_data.get("job_type"))
            
            # Create job posting with truncated fields to fit varchar limits
            job = JobPosting(
                external_job_id=str(external_id) if external_id else f"scraper-{session_data['session_id']}-{platform_name}-{idx}",
                platform=truncate_str(platform, 50),
                title=truncate_str(title, 500),
                company=truncate_str(company, 255),
                location=truncate_str(job_data.get("location"), 255),
                description=description,
                snippet=job_data.get("snippet"),
                requirements=job_data.get("requirements"),
                salary_range=truncate_str(salary_str if salary_str and salary_str.upper() != "N/A" else None, 255),
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=truncate_str(currency, 10),
                experience_required=truncate_str(experience_str if experience_str and experience_str.upper() != "N/A" else None, 100),
                experience_min=exp_min,
                experience_max=exp_max,
                skills=normalized_skills,
                keywords=job_import_service.generate_keywords(title, description, normalized_skills),
                job_type=truncate_str(job_type_raw, 255),
                is_remote=is_remote,
                job_url=job_url,
                apply_url=apply_url,
                posted_date=posted_date,
                raw_metadata=job_data.get("metadata", {}),
                # Scraper tracking
                scraped_by_key_id=scraper_key.id if scraper_key else None,
                scrape_session_id=UUID(session_data["session_id"]),
                normalized_role_id=session_data["global_role_id"],
                import_batch_id=session_data["session_id"]
            )
            
            db.session.add(job)
            db.session.flush()  # Get the ID
            
            # Create role-job mapping
            role_mapping = RoleJobMapping(
                global_role_id=session_data["global_role_id"],
                job_posting_id=job.id
            )
            db.session.add(role_mapping)
            
            job_ids.append(job.id)
            imported_count += 1
            
            # Log progress every 10 jobs
            if (idx + 1) % 10 == 0:
                logger.info(f"[JOB-IMPORT] Progress: {idx+1}/{len(jobs_data)} processed")
            
        except Exception as e:
            logger.error(f"[JOB-IMPORT] Failed to import job {idx+1}: {e}")
            skipped_count += 1
            skip_reasons["error"] += 1
    
    db.session.commit()
    
    # Log detailed skip reasons summary
    logger.info(
        f"[JOB-IMPORT] {platform_name} batch complete: {imported_count} imported, "
        f"{skipped_count} skipped"
    )
    if skipped_count > 0:
        logger.info(
            f"[JOB-IMPORT] Skip breakdown for {platform_name}: "
            f"platform_id_dup={skip_reasons['duplicate_platform_id']}, "
            f"title_company_location_dup={skip_reasons['duplicate_title_company_location']}, "
            f"title_company_desc_dup={skip_reasons['duplicate_title_company_description']}, "
            f"missing_required={skip_reasons['missing_required']}, "
            f"errors={skip_reasons['error']}"
        )
    
    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "job_ids": job_ids,
        "skip_reasons": skip_reasons
    }


# ============================================================================
# HELPER FUNCTIONS - Platform Status
# ============================================================================

def complete_platform_status(
    platform_status_id: int,
    session_id: str,
    scraper_key_id: int,
    jobs_found: int,
    jobs_imported: int,
    jobs_skipped: int
) -> None:
    """Update platform status to completed."""
    platform_status = db.session.get(SessionPlatformStatus, platform_status_id)
    
    if platform_status:
        platform_status.status = "completed"
        platform_status.jobs_found = jobs_found
        platform_status.jobs_imported = jobs_imported
        platform_status.jobs_skipped = jobs_skipped
        platform_status.completed_at = datetime.utcnow()
        
        # Update session progress counters
        session = ScrapeSession.query.filter_by(
            session_id=UUID(session_id),
            scraper_key_id=scraper_key_id
        ).first()
        
        if session:
            session.platforms_completed = (session.platforms_completed or 0) + 1
            session.jobs_found = (session.jobs_found or 0) + jobs_found
            session.jobs_imported = (session.jobs_imported or 0) + jobs_imported
            session.jobs_skipped = (session.jobs_skipped or 0) + jobs_skipped
        
        db.session.commit()
        
        logger.info(
            f"[JOB-IMPORT] Platform status {platform_status_id} completed: "
            f"{jobs_imported} imported, {jobs_skipped} skipped"
        )


def mark_platform_failed(
    platform_status_id: int,
    session_id: str,
    scraper_key_id: int,
    error_message: str
) -> None:
    """Mark platform as failed with error message."""
    platform_status = db.session.get(SessionPlatformStatus, platform_status_id)
    
    if platform_status:
        platform_status.status = "failed"
        platform_status.error_message = error_message
        platform_status.completed_at = datetime.utcnow()
        
        # Update session failed counter
        session = ScrapeSession.query.filter_by(
            session_id=UUID(session_id),
            scraper_key_id=scraper_key_id
        ).first()
        
        if session:
            session.platforms_failed = (session.platforms_failed or 0) + 1
        
        db.session.commit()
        
        logger.warning(
            f"[JOB-IMPORT] Platform status {platform_status_id} failed: {error_message}"
        )


# ============================================================================
# HELPER FUNCTIONS - Session Aggregation
# ============================================================================

def aggregate_session_stats(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Aggregate statistics from all platform statuses for a session.
    
    Returns dict with:
    - total_imported: total jobs imported across all platforms
    - total_skipped: total jobs skipped
    - successful_platforms: count of platforms that completed
    - failed_platforms: count of platforms that failed
    - total_platforms: total platforms in session
    - job_ids: list of all imported job IDs
    - global_role_id: the role ID for this session
    - role_name: the role name
    """
    session = ScrapeSession.query.filter_by(session_id=UUID(session_id)).first()
    
    if not session:
        logger.error(f"Session {session_id} not found for aggregation")
        return None
    
    # Get all platform statuses for this session
    platform_statuses = SessionPlatformStatus.query.filter_by(
        session_id=session.session_id
    ).all()
    
    total_imported = 0
    total_skipped = 0
    successful_platforms = 0
    failed_platforms = 0
    
    for ps in platform_statuses:
        if ps.status == "completed":
            successful_platforms += 1
            total_imported += ps.jobs_imported or 0
            total_skipped += ps.jobs_skipped or 0
        elif ps.status == "failed":
            failed_platforms += 1
        # Note: "skipped" status means platform was skipped by scraper
    
    # Get job IDs for matching
    jobs = JobPosting.query.filter_by(
        scrape_session_id=session.session_id
    ).with_entities(JobPosting.id).all()
    job_ids = [j.id for j in jobs]
    
    return {
        "total_imported": total_imported,
        "total_skipped": total_skipped,
        "successful_platforms": successful_platforms,
        "failed_platforms": failed_platforms,
        "total_platforms": len(platform_statuses),
        "job_ids": job_ids,
        "global_role_id": session.global_role_id,
        "role_name": session.role_name
    }


# ============================================================================
# HELPER FUNCTIONS - Session Finalization
# ============================================================================

def finalize_session(
    session_id: str,
    scraper_key_id: int,
    session_stats: Dict[str, Any]
) -> None:
    """Finalize session with aggregated stats."""
    session = ScrapeSession.query.filter_by(
        session_id=UUID(session_id),
        scraper_key_id=scraper_key_id
    ).first()
    
    if not session:
        logger.error(f"Session {session_id} not found for finalization")
        return
    
    # Update session with final stats
    session.status = "completed"
    session.completed_at = datetime.utcnow()
    session.jobs_found = session_stats["total_imported"] + session_stats["total_skipped"]
    session.jobs_imported = session_stats["total_imported"]
    session.jobs_skipped = session_stats["total_skipped"]
    session.platforms_completed = session_stats["successful_platforms"]
    session.platforms_failed = session_stats["failed_platforms"]
    
    # Add notes if any platforms failed
    if session_stats["failed_platforms"] > 0:
        session.session_notes = (
            f"Completed with {session_stats['failed_platforms']} platform failure(s). "
            f"Successfully imported from {session_stats['successful_platforms']} platforms."
        )
    
    # Update scraper key usage
    scraper_key = db.session.get(ScraperApiKey, scraper_key_id)
    if scraper_key:
        scraper_key.record_usage(jobs_imported=session_stats["total_imported"])
    
    db.session.commit()
    
    logger.info(
        f"[JOB-IMPORT] Session {session_id} finalized: "
        f"{session_stats['total_imported']} jobs from "
        f"{session_stats['successful_platforms']}/{session_stats['total_platforms']} platforms"
    )


def update_role_status(global_role_id: int, jobs_imported: int) -> None:
    """
    Update role stats and keep it in the approved queue for continuous rotation.
    
    This ensures the scraping queue rotates continuously - once a role is scraped,
    it stays approved and ready for the next scrape cycle.
    """
    role = db.session.get(GlobalRole, global_role_id)
    
    if role:
        # Keep the role in approved status for next rotation
        role.queue_status = "approved"
        role.last_scraped_at = datetime.utcnow()
        role.total_jobs_scraped = (role.total_jobs_scraped or 0) + jobs_imported
        db.session.commit()
        
        logger.info(
            f"[JOB-IMPORT] Role '{role.name}' scraped successfully. "
            f"Stays approved for next cycle. Total jobs: {role.total_jobs_scraped}"
        )


def update_role_location_queue_status(session_id: str, jobs_imported: int) -> None:
    """
    Update RoleLocationQueue entry stats and reset to approved for continuous rotation.
    
    This ensures the location-based scraping queue rotates continuously - once a 
    role+location is scraped, it stays approved and ready for the next scrape cycle.
    """
    from app.models.role_location_queue import RoleLocationQueue
    
    session = ScrapeSession.query.filter_by(session_id=UUID(session_id)).first()
    
    if not session:
        logger.warning(f"[JOB-IMPORT] Session {session_id} not found for queue update")
        return
    
    # Get the role_location_queue_id from the session (direct column, not metadata)
    role_location_queue_id = session.role_location_queue_id
    
    if not role_location_queue_id:
        logger.debug(
            f"[JOB-IMPORT] Session {session_id} has no role_location_queue_id - "
            f"this is a role-based (not location-based) scrape"
        )
        return
    
    queue_entry = db.session.get(RoleLocationQueue, role_location_queue_id)
    
    if queue_entry:
        # Reset to approved for next rotation (continuous scraping)
        queue_entry.queue_status = "approved"
        queue_entry.last_scraped_at = datetime.utcnow()
        queue_entry.total_jobs_scraped = (queue_entry.total_jobs_scraped or 0) + jobs_imported
        queue_entry.last_scrape_session_id = str(session.session_id)
        db.session.commit()
        
        logger.info(
            f"[JOB-IMPORT] RoleLocationQueue entry {role_location_queue_id} updated: "
            f"'{queue_entry.location}' stays approved for next cycle. "
            f"Total jobs: {queue_entry.total_jobs_scraped}"
        )
    else:
        logger.warning(
            f"[JOB-IMPORT] RoleLocationQueue entry {role_location_queue_id} not found"
        )


# ============================================================================
# HELPER FUNCTIONS - Job Matching Trigger
# ============================================================================

def trigger_job_matching(
    job_ids: List[int],
    global_role_id: int,
    role_name: str,
    session_id: str
) -> None:
    """Trigger job matching workflow for imported jobs."""
    try:
        inngest_client.send_sync(
            inngest.Event(
                name="jobs/imported",
                data={
                    "job_ids": job_ids,
                    "global_role_id": global_role_id,
                    "role_name": role_name,
                    "session_id": session_id,
                    "source": "scraper"
                }
            )
        )
        
        logger.info(
            f"[JOB-IMPORT] ✅ Triggered jobs/imported event for {len(job_ids)} jobs"
        )
        
    except Exception as e:
        logger.error(f"[JOB-IMPORT] ❌ Failed to trigger jobs/imported event: {e}")
