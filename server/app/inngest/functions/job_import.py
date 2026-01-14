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
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.scrape_session import ScrapeSession
from app.models.scraper_api_key import ScraperApiKey
from app.models.global_role import GlobalRole
from app.models.job_posting import JobPosting
from app.models.role_job_mapping import RoleJobMapping
from app.models.session_platform_status import SessionPlatformStatus
from app.models.scraper_platform import ScraperPlatform
from app.inngest import inngest_client
from app.services.resume_tailor.keyword_extractor import KeywordExtractorService

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
    
    Supports batched imports - when a platform has many jobs, they are split
    into multiple events. Each batch is processed independently and the platform
    status is only marked complete when all batches finish.
    
    Event data:
    {
        "session_id": "uuid",
        "scraper_key_id": 123,
        "platform_name": "linkedin",
        "platform_status_id": 456,
        "jobs": [...],
        "jobs_count": 47,
        "batch_index": 0,           # Optional: which batch this is (0-indexed)
        "total_batches": 1,         # Optional: total number of batches
        "total_jobs_in_platform": 47  # Optional: total jobs across all batches
    }
    """
    event_data = ctx.event.data
    session_id = event_data["session_id"]
    scraper_key_id = event_data["scraper_key_id"]
    platform_name = event_data["platform_name"]
    platform_status_id = event_data["platform_status_id"]
    jobs_data = event_data["jobs"]
    
    # Batch metadata (defaults for backwards compatibility)
    batch_index = event_data.get("batch_index", 0)
    total_batches = event_data.get("total_batches", 1)
    total_jobs_in_platform = event_data.get("total_jobs_in_platform", len(jobs_data))
    
    logger.info(
        f"[JOB-IMPORT] Starting import for platform '{platform_name}' "
        f"in session {session_id} - batch {batch_index + 1}/{total_batches} "
        f"with {len(jobs_data)} jobs"
    )
    
    # Step 1: Validate session and platform status
    session_data = await ctx.step.run(
        "validate-session",
        lambda: validate_session_for_platform(session_id, scraper_key_id, platform_status_id)
    )
    
    if not session_data:
        logger.error(f"[JOB-IMPORT] ❌ Session {session_id} or platform status not found")
        return {"status": "error", "message": "Invalid session or platform"}
    
    # Step 2: Import jobs for this platform batch
    import_result = await ctx.step.run(
        f"import-jobs-batch-{batch_index}",
        lambda: import_jobs_batch_for_platform(jobs_data, session_data, platform_name)
    )
    
    # NOTE: Keyword extraction removed - scoring now uses Skills (45%), Semantic (35%), Experience (20%)
    
    # Step 3: Update platform status (increment batch counter, mark complete if all batches done)
    completion_result = await ctx.step.run(
        f"update-platform-batch-{batch_index}",
        lambda: update_platform_batch_status(
            platform_status_id,
            session_id,
            scraper_key_id,
            len(jobs_data),
            import_result["imported"],
            import_result["skipped"],
            batch_index,
            total_batches
        )
    )
    
    if completion_result.get("platform_completed"):
        logger.info(
            f"[JOB-IMPORT] ✅ Platform '{platform_name}' fully completed "
            f"(all {total_batches} batches done): "
            f"total {completion_result['total_imported']} imported, "
            f"{completion_result['total_skipped']} skipped"
        )
    else:
        logger.info(
            f"[JOB-IMPORT] ✓ Platform '{platform_name}' batch {batch_index + 1}/{total_batches} done: "
            f"{import_result['imported']} imported, {import_result['skipped']} skipped"
        )
    
    return {
        "status": "success",
        "platform": platform_name,
        "batch_index": batch_index,
        "total_batches": total_batches,
        "batch_imported": import_result["imported"],
        "batch_skipped": import_result["skipped"],
        "job_ids": import_result["job_ids"],
        "platform_completed": completion_result.get("platform_completed", False)
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
    
    # NOTE: This function is now triggered by the last batch to complete (not by HTTP endpoint)
    # So all batches should already be done - no need to wait
    
    # Step 1: Aggregate platform results (fresh read from DB)
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
    
    # Allow in_progress, pending, or pending_completion status
    # pending_completion is set when /queue/complete is called but batches are still processing
    if session.status not in ("in_progress", "pending", "pending_completion"):
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
    from app.models.session_job_log import SessionJobLog
    
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
        "duplicate_in_batch": 0,
        "error": 0
    }
    
    # Track jobs added within this batch to prevent intra-batch duplicates
    # Key: (platform, external_job_id), Value: True
    batch_external_ids: Dict[tuple, bool] = {}
    # Key: (title_lower, company_lower, location_lower), Value: True
    batch_title_company_location: Dict[tuple, bool] = {}
    
    # Helper to truncate strings to fit database varchar limits
    def truncate_str(value, max_len):
        if value and isinstance(value, str) and len(value) > max_len:
            return value[:max_len]
        return value
    
    for idx, job_data in enumerate(jobs_data):
        # Use a savepoint for each job so failures don't rollback previous jobs
        # This is critical - without this, one bad job rolls back ALL jobs in the batch
        savepoint = db.session.begin_nested()
        
        # Create job log entry for tracking
        job_log = SessionJobLog.log_job(
            session_id=UUID(session_data["session_id"]),
            platform_name=platform_name,
            job_index=idx,
            raw_job_data=job_data,
            platform_status_id=session_data.get("platform_status_id")
        )
        
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
                job_log.mark_skipped(
                    reason="missing_required",
                    detail=f"Missing required field: {'title' if not title else 'company'}"
                )
                savepoint.commit()  # Commit the skip log entry
                skipped_count += 1
                skip_reasons["missing_required"] += 1
                continue
            
            # =================================================================
            # DEDUPLICATION STRATEGY (in order of priority):
            # 1. Same platform + external_job_id = exact duplicate
            # 2. Same title + company + location = likely same job
            # 3. Same title + company + similar description = same job different platform
            # =================================================================
            
            # Check 0: Intra-batch duplicate by platform + external_job_id
            # This catches duplicates within the same batch (before they're committed)
            if external_id:
                batch_key = (platform.lower(), str(external_id).lower())
                if batch_key in batch_external_ids:
                    logger.info(f"[JOB-IMPORT] Skipping intra-batch duplicate (platform+id): platform={platform}, id={external_id}")
                    job_log.mark_skipped(
                        reason="duplicate_in_batch",
                        detail=f"Duplicate within same batch: platform '{platform}' and external_job_id '{external_id}'"
                    )
                    savepoint.commit()  # Commit the skip log entry
                    skipped_count += 1
                    skip_reasons["duplicate_in_batch"] += 1
                    continue
            
            # Check 1: Exact duplicate by platform + external_job_id (in database)
            if external_id:
                existing = JobPosting.query.filter_by(
                    platform=platform,
                    external_job_id=str(external_id)
                ).first()
                
                if existing:
                    logger.info(f"[JOB-IMPORT] Skipping duplicate (platform+id): platform={platform}, id={external_id}")
                    job_log.mark_skipped(
                        reason="duplicate_platform_id",
                        detail=f"Exact duplicate: same platform '{platform}' and external_job_id '{external_id}'",
                        duplicate_job_id=existing.id
                    )
                    savepoint.commit()  # Commit the skip log entry
                    skipped_count += 1
                    skip_reasons["duplicate_platform_id"] += 1
                    continue
            
            # Check 2a: Intra-batch duplicate by title + company + location
            # This catches duplicates within the same batch (before they're committed)
            batch_content_key = (
                title.lower().strip(),
                company.lower().strip(),
                (location.lower().strip() if location else "")
            )
            if batch_content_key in batch_title_company_location:
                logger.info(
                    f"[JOB-IMPORT] Skipping intra-batch duplicate (title+company+location): "
                    f"'{title}' at '{company}' in '{location}'"
                )
                job_log.mark_skipped(
                    reason="duplicate_in_batch",
                    detail=f"Duplicate within same batch: '{title}' at '{company}' in '{location}'"
                )
                savepoint.commit()  # Commit the skip log entry
                skipped_count += 1
                skip_reasons["duplicate_in_batch"] += 1
                continue
            
            # Check 2b: Duplicate by title + company + location (case-insensitive, in database)
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
                job_log.mark_skipped(
                    reason="duplicate_title_company_location",
                    detail=f"Duplicate by title+company+location: '{title}' at '{company}' in '{location}'",
                    duplicate_job_id=existing_by_content.id
                )
                savepoint.commit()  # Commit the skip log entry
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
                    job_log.mark_skipped(
                        reason="duplicate_title_company_description",
                        detail=f"Duplicate by title+company+description: '{title}' at '{company}' - same description prefix",
                        duplicate_job_id=existing_similar.id
                    )
                    savepoint.commit()  # Commit the skip log entry
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
            # Check jobUrl, job_url, and source_url (scraper sends source_url)
            job_url = job_data.get("jobUrl", job_data.get("job_url", job_data.get("source_url", "")))
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
                # NOTE: extracted_keywords is populated by extract_keywords step after import
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
            
            # Track this job in batch dictionaries for intra-batch dedup
            if external_id:
                batch_external_ids[(platform.lower(), str(external_id).lower())] = True
            batch_title_company_location[batch_content_key] = True
            
            # Create role-job mapping
            role_mapping = RoleJobMapping(
                global_role_id=session_data["global_role_id"],
                job_posting_id=job.id
            )
            db.session.add(role_mapping)
            
            # Mark job log as imported
            job_log.mark_imported(job.id)
            
            job_ids.append(job.id)
            imported_count += 1
            
            # Commit the savepoint (releases the savepoint, keeps changes)
            savepoint.commit()
            
            # Log progress every 10 jobs
            if (idx + 1) % 10 == 0:
                logger.info(f"[JOB-IMPORT] Progress: {idx+1}/{len(jobs_data)} processed")
            
        except IntegrityError as e:
            # Handle race condition: parallel batches inserting the same job
            # This happens when multiple Inngest batches try to insert jobs with
            # the same external_job_id simultaneously - the check-then-insert fails
            error_msg = str(e)
            is_unique_violation = "unique" in error_msg.lower() or "duplicate" in error_msg.lower()
            
            # Rollback the savepoint
            try:
                savepoint.rollback()
            except Exception:
                db.session.rollback()
            
            if is_unique_violation:
                # Treat as a duplicate skip, not an error
                logger.info(
                    f"[JOB-IMPORT] Race condition duplicate detected for job {idx+1}: "
                    f"'{job_data.get('title', 'Unknown')}' - already inserted by parallel batch"
                )
                
                # Log as skipped due to race condition duplicate
                try:
                    skip_savepoint = db.session.begin_nested()
                    skip_job_log = SessionJobLog.log_job(
                        session_id=UUID(session_data["session_id"]),
                        platform_name=platform_name,
                        job_index=idx,
                        raw_job_data=job_data,
                        platform_status_id=session_data.get("platform_status_id")
                    )
                    skip_job_log.mark_skipped(
                        reason="duplicate_race_condition",
                        detail=f"Duplicate detected via database constraint (parallel batch race): {job_data.get('title', 'Unknown')}"
                    )
                    skip_savepoint.commit()
                except Exception as log_error:
                    logger.warning(f"[JOB-IMPORT] Failed to log skip for job {idx+1}: {log_error}")
                    try:
                        skip_savepoint.rollback()
                    except Exception:
                        pass
                
                skipped_count += 1
                skip_reasons["duplicate_race_condition"] = skip_reasons.get("duplicate_race_condition", 0) + 1
            else:
                # Other IntegrityError - log as error
                logger.error(f"[JOB-IMPORT] IntegrityError for job {idx+1}: {error_msg}")
                try:
                    error_savepoint = db.session.begin_nested()
                    error_job_log = SessionJobLog.log_job(
                        session_id=UUID(session_data["session_id"]),
                        platform_name=platform_name,
                        job_index=idx,
                        raw_job_data=job_data,
                        platform_status_id=session_data.get("platform_status_id")
                    )
                    error_job_log.mark_error(error_msg)
                    error_savepoint.commit()
                except Exception as log_error:
                    logger.warning(f"[JOB-IMPORT] Failed to log error for job {idx+1}: {log_error}")
                    try:
                        error_savepoint.rollback()
                    except Exception:
                        pass
                
                skipped_count += 1
                skip_reasons["error"] += 1
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[JOB-IMPORT] Failed to import job {idx+1}: {error_msg}")
            
            # Rollback only the current savepoint, not the entire transaction
            # This preserves all previously successful jobs
            try:
                savepoint.rollback()
            except Exception:
                # Savepoint might already be invalid, try full rollback as fallback
                db.session.rollback()
            
            # Create error log entry in a new savepoint
            try:
                error_savepoint = db.session.begin_nested()
                error_job_log = SessionJobLog.log_job(
                    session_id=UUID(session_data["session_id"]),
                    platform_name=platform_name,
                    job_index=idx,
                    raw_job_data=job_data,
                    platform_status_id=session_data.get("platform_status_id")
                )
                error_job_log.mark_error(error_msg)
                error_savepoint.commit()
            except Exception as log_error:
                logger.warning(f"[JOB-IMPORT] Failed to log error for job {idx+1}: {log_error}")
                try:
                    error_savepoint.rollback()
                except Exception:
                    pass
            
            skipped_count += 1
            skip_reasons["error"] += 1
    
    # Commit any remaining successful jobs
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"[JOB-IMPORT] Failed to commit batch: {e}")
        db.session.rollback()
    
    # Log detailed skip reasons summary
    logger.info(
        f"[JOB-IMPORT] {platform_name} batch complete: {imported_count} imported, "
        f"{skipped_count} skipped"
    )
    if skipped_count > 0:
        logger.info(
            f"[JOB-IMPORT] Skip breakdown for {platform_name}: "
            f"in_batch_dup={skip_reasons['duplicate_in_batch']}, "
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
# HELPER FUNCTIONS - Keyword Extraction
# ============================================================================

def extract_keywords_for_jobs(job_ids: List[int]) -> Dict[str, Any]:
    """
    Extract keywords from job descriptions for unified scoring.
    
    Uses KeywordExtractorService to extract:
    - technical_keywords
    - action_verbs  
    - industry_terms
    - soft_skills
    
    These are stored in JobPosting.extracted_keywords JSONB field.
    
    Args:
        job_ids: List of job posting IDs to process
        
    Returns:
        Dict with extracted count and failed count
    """
    extracted_count = 0
    failed_count = 0
    
    try:
        keyword_extractor = KeywordExtractorService()
    except Exception as e:
        logger.error(f"[JOB-IMPORT] Failed to initialize KeywordExtractorService: {e}")
        return {"extracted": 0, "failed": len(job_ids), "error": str(e)}
    
    for job_id in job_ids:
        try:
            job = db.session.get(JobPosting, job_id)
            if not job:
                logger.warning(f"[JOB-IMPORT] Job {job_id} not found for keyword extraction")
                failed_count += 1
                continue
            
            # Skip if keywords already extracted
            if job.extracted_keywords:
                extracted_count += 1
                continue
            
            # Extract keywords using AI
            job_keywords = keyword_extractor.extract_keywords_only(
                job.description or ""
            )
            
            # Store as JSONB in the extracted_keywords field
            job.extracted_keywords = {
                "technical_keywords": job_keywords.technical_keywords,
                "action_verbs": job_keywords.action_verbs,
                "industry_terms": job_keywords.industry_terms,
                "soft_skills": job_keywords.soft_skills
            }
            
            extracted_count += 1
            
            # Commit every 5 jobs to avoid long transactions
            if extracted_count % 5 == 0:
                db.session.commit()
                
        except Exception as e:
            logger.error(f"[JOB-IMPORT] Failed to extract keywords for job {job_id}: {e}")
            failed_count += 1
    
    # Final commit
    db.session.commit()
    
    logger.info(
        f"[JOB-IMPORT] Keyword extraction complete: "
        f"{extracted_count} extracted, {failed_count} failed"
    )
    
    return {
        "extracted": extracted_count,
        "failed": failed_count
    }


# ============================================================================
# HELPER FUNCTIONS - Platform Status
# ============================================================================

def update_platform_batch_status(
    platform_status_id: int,
    session_id: str,
    scraper_key_id: int,
    jobs_found: int,
    jobs_imported: int,
    jobs_skipped: int,
    batch_index: int,
    total_batches: int
) -> Dict[str, Any]:
    """
    Update platform status for a completed batch.
    
    Increments the completed_batches counter and accumulates job counts.
    Only marks the platform as 'completed' when all batches are done.
    
    Returns:
        Dict with platform_completed flag and totals
    """
    platform_status = db.session.get(SessionPlatformStatus, platform_status_id)
    
    if not platform_status:
        logger.error(f"[JOB-IMPORT] Platform status {platform_status_id} not found")
        return {"platform_completed": False, "error": "Platform status not found"}
    
    # Accumulate job counts from this batch
    platform_status.jobs_found = (platform_status.jobs_found or 0) + jobs_found
    platform_status.jobs_imported = (platform_status.jobs_imported or 0) + jobs_imported
    platform_status.jobs_skipped = (platform_status.jobs_skipped or 0) + jobs_skipped
    
    # Increment completed batch counter
    platform_status.completed_batches = (platform_status.completed_batches or 0) + 1
    
    # Ensure total_batches is set (in case of legacy events without batch info)
    if not platform_status.total_batches or platform_status.total_batches < total_batches:
        platform_status.total_batches = total_batches
    
    # Check if all batches are complete
    all_batches_complete = platform_status.completed_batches >= platform_status.total_batches
    
    should_trigger_session_complete = False
    
    if all_batches_complete:
        # Mark platform as completed
        platform_status.status = "completed"
        platform_status.completed_at = datetime.utcnow()
        
        # Update session progress counters (only once when fully complete)
        session = ScrapeSession.query.filter_by(
            session_id=UUID(session_id),
            scraper_key_id=scraper_key_id
        ).first()
        
        if session:
            session.platforms_completed = (session.platforms_completed or 0) + 1
            session.jobs_found = (session.jobs_found or 0) + platform_status.jobs_found
            session.jobs_imported = (session.jobs_imported or 0) + platform_status.jobs_imported
            session.jobs_skipped = (session.jobs_skipped or 0) + platform_status.jobs_skipped
            
            # Check if session is pending_completion and ALL platforms are now done
            # This triggers session completion from the last batch to finish
            if session.status == 'pending_completion':
                # Get all platform statuses for this session
                all_platform_statuses = SessionPlatformStatus.query.filter_by(
                    session_id=session.session_id
                ).all()
                
                all_platforms_done = all(
                    ps.status in ('completed', 'failed', 'skipped') or
                    (ps.completed_batches or 0) >= (ps.total_batches or 1)
                    for ps in all_platform_statuses
                )
                
                if all_platforms_done:
                    should_trigger_session_complete = True
                    logger.info(
                        f"[JOB-IMPORT] All platforms done for session {session_id}. "
                        f"Triggering session completion."
                    )
        
        logger.info(
            f"[JOB-IMPORT] Platform {platform_status_id} fully completed "
            f"({platform_status.completed_batches}/{platform_status.total_batches} batches): "
            f"{platform_status.jobs_imported} imported, {platform_status.jobs_skipped} skipped"
        )
    else:
        logger.info(
            f"[JOB-IMPORT] Platform {platform_status_id} batch {batch_index + 1} complete "
            f"({platform_status.completed_batches}/{platform_status.total_batches} batches done)"
        )
    
    db.session.commit()
    
    # Trigger session completion AFTER commit (so the state is persisted)
    if should_trigger_session_complete:
        try:
            inngest_client.send_sync(
                inngest.Event(
                    name="jobs/scraper.complete",
                    data={
                        "session_id": session_id,
                        "scraper_key_id": scraper_key_id
                    }
                )
            )
            logger.info(f"[JOB-IMPORT] Session complete event sent for {session_id}")
        except Exception as e:
            logger.error(f"[JOB-IMPORT] Failed to send session complete event: {e}")
    
    return {
        "platform_completed": all_batches_complete,
        "completed_batches": platform_status.completed_batches,
        "total_batches": platform_status.total_batches,
        "total_imported": platform_status.jobs_imported,
        "total_skipped": platform_status.jobs_skipped,
        "session_complete_triggered": should_trigger_session_complete
    }


def complete_platform_status(
    platform_status_id: int,
    session_id: str,
    scraper_key_id: int,
    jobs_found: int,
    jobs_imported: int,
    jobs_skipped: int
) -> None:
    """
    Update platform status to completed.
    
    DEPRECATED: Use update_platform_batch_status for batch-aware updates.
    This function is kept for backwards compatibility with non-batched events.
    """
    # Delegate to batch-aware function with single batch
    update_platform_batch_status(
        platform_status_id,
        session_id,
        scraper_key_id,
        jobs_found,
        jobs_imported,
        jobs_skipped,
        batch_index=0,
        total_batches=1
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

def wait_for_platform_batches_complete(session_id: str, max_wait_seconds: int = 120) -> Dict[str, Any]:
    """
    Wait for all platform batches to complete before aggregating stats.
    
    This is necessary because:
    1. POST /queue/jobs sends batch events to Inngest
    2. POST /queue/complete is called immediately after
    3. Batches might still be processing when complete_session runs
    
    We poll the database every 2 seconds to check if all platforms
    have completed_batches >= total_batches.
    
    Args:
        session_id: Session UUID string
        max_wait_seconds: Maximum time to wait (default 120s)
    
    Returns:
        Dict with all_complete flag and status details
    """
    import time
    
    poll_interval = 2  # seconds
    elapsed = 0
    
    while elapsed < max_wait_seconds:
        # Expire cached data to get fresh reads
        db.session.expire_all()
        
        session = ScrapeSession.query.filter_by(session_id=UUID(session_id)).first()
        if not session:
            logger.error(f"[JOB-IMPORT] Session {session_id} not found during wait")
            return {"all_complete": False, "error": "Session not found"}
        
        platform_statuses = SessionPlatformStatus.query.filter_by(
            session_id=session.session_id
        ).all()
        
        if not platform_statuses:
            logger.warning(f"[JOB-IMPORT] No platform statuses found for session {session_id}")
            return {"all_complete": True, "platforms": 0}
        
        all_done = True
        pending_platforms = []
        
        for ps in platform_statuses:
            # A platform is done if:
            # 1. status is 'completed' or 'failed', OR
            # 2. completed_batches >= total_batches
            is_terminal_status = ps.status in ('completed', 'failed', 'skipped')
            batches_done = (ps.completed_batches or 0) >= (ps.total_batches or 1)
            
            if not is_terminal_status and not batches_done:
                all_done = False
                pending_platforms.append({
                    "platform": ps.platform_name,
                    "status": ps.status,
                    "completed_batches": ps.completed_batches or 0,
                    "total_batches": ps.total_batches or 1
                })
        
        if all_done:
            logger.info(
                f"[JOB-IMPORT] All {len(platform_statuses)} platforms completed "
                f"for session {session_id} after {elapsed}s"
            )
            return {
                "all_complete": True,
                "platforms": len(platform_statuses),
                "wait_time_seconds": elapsed
            }
        
        logger.debug(
            f"[JOB-IMPORT] Waiting for batches: {len(pending_platforms)} platforms pending. "
            f"Elapsed: {elapsed}s. Pending: {pending_platforms}"
        )
        
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    # Timeout reached
    logger.warning(
        f"[JOB-IMPORT] Timeout waiting for batches after {max_wait_seconds}s. "
        f"Session: {session_id}"
    )
    return {
        "all_complete": False,
        "timeout": True,
        "wait_time_seconds": elapsed
    }


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
    # CRITICAL: Expire all cached objects to ensure we read fresh data from DB
    # This is necessary because platform batches are processed async and may have
    # updated the database after our session was loaded
    db.session.expire_all()
    
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
    total_found = 0
    successful_platforms = 0
    failed_platforms = 0
    
    # FIX: Count jobs from ALL platforms, not just "completed" ones
    # A platform is considered successful if it has completed all batches OR has status "completed"
    for ps in platform_statuses:
        is_done = (
            ps.status in ("completed", "failed", "skipped") or
            (ps.completed_batches or 0) >= (ps.total_batches or 1)
        )
        
        if ps.status == "failed":
            failed_platforms += 1
        elif is_done:
            # Count as successful if done (regardless of exact status)
            successful_platforms += 1
        
        # Always accumulate job counts from the platform status
        # These are tracked in update_platform_batch_status as batches complete
        total_imported += ps.jobs_imported or 0
        total_skipped += ps.jobs_skipped or 0
        total_found += ps.jobs_found or 0
    
    # Get job IDs for matching - this is the source of truth for imported jobs
    jobs = JobPosting.query.filter_by(
        scrape_session_id=session.session_id
    ).with_entities(JobPosting.id).all()
    job_ids = [j.id for j in jobs]
    
    # Use actual job count from DB as the most reliable source
    # This handles any edge cases where platform counters might be off
    actual_imported_count = len(job_ids)
    
    # Log if there's a mismatch for debugging
    if actual_imported_count != total_imported:
        logger.warning(
            f"[JOB-IMPORT] Session {session_id} count mismatch: "
            f"platform_status says {total_imported} imported, "
            f"but found {actual_imported_count} actual JobPosting records. "
            f"Using actual count."
        )
        total_imported = actual_imported_count
    
    logger.info(
        f"[JOB-IMPORT] Aggregated stats for session {session_id}: "
        f"{total_imported} imported, {total_skipped} skipped, "
        f"{successful_platforms}/{len(platform_statuses)} platforms successful"
    )
    
    return {
        "total_imported": total_imported,
        "total_skipped": total_skipped,
        "total_found": total_found,
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
    session.jobs_found = session_stats.get("total_found") or (session_stats["total_imported"] + session_stats["total_skipped"])
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
