"""
Job Import Inngest Workflow

Handles asynchronous job importing from external scrapers.

Triggered by: jobs/scraper.import event
Steps:
1. Validate session and scraper key
2. Import jobs with deduplication
3. Update session and role status
4. Trigger job matching workflow

Benefits:
- Non-blocking API response
- Retryable with exponential backoff
- Better error handling and observability
- Can handle large job batches without timeout
"""
import logging
from datetime import datetime
from typing import Dict, List, Any
from uuid import UUID
import inngest

from app import db
from app.models.scrape_session import ScrapeSession
from app.models.scraper_api_key import ScraperApiKey
from app.models.global_role import GlobalRole
from app.models.job_posting import JobPosting
from app.models.role_job_mapping import RoleJobMapping
from app.inngest import inngest_client

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="job-import-scraper",
    trigger=inngest.TriggerEvent(event="jobs/scraper.import"),
    name="Import Scraped Jobs",
    retries=3
)
async def import_scraped_jobs_fn(ctx: inngest.Context, step):
    """
    Import jobs from scraper submission.
    
    Event data:
    {
        "session_id": "uuid",
        "scraper_key_id": 123,
        "jobs": [...],  # List of job objects
        "jobs_count": 47
    }
    
    Steps:
    1. Validate session
    2. Import jobs with deduplication
    3. Update session completion
    4. Update role status
    5. Trigger job matching
    """
    event_data = ctx.event.data
    session_id = event_data["session_id"]
    scraper_key_id = event_data["scraper_key_id"]
    jobs_data = event_data["jobs"]
    
    logger.info(
        f"[JOB-IMPORT] Starting import for session {session_id} "
        f"with {len(jobs_data)} jobs"
    )
    
    # Step 1: Validate session
    session_data = await step.run(
        "validate-session",
        lambda: validate_session(session_id, scraper_key_id)
    )
    
    if not session_data:
        logger.error(f"[JOB-IMPORT] ❌ Session {session_id} not found or invalid")
        return {"status": "error", "message": "Invalid session"}
    
    # Step 2: Import jobs
    import_result = await step.run(
        "import-jobs",
        lambda: import_jobs_batch(jobs_data, session_data)
    )
    
    # Step 3: Update session
    await step.run(
        "complete-session",
        lambda: complete_session(
            session_id,
            scraper_key_id,
            len(jobs_data),
            import_result["imported"],
            import_result["skipped"]
        )
    )
    
    # Step 4: Update role status
    await step.run(
        "update-role-status",
        lambda: update_role_status(session_data["global_role_id"], import_result["imported"])
    )
    
    # Step 5: Trigger job matching if jobs imported
    if import_result["job_ids"]:
        await step.run(
            "trigger-job-matching",
            lambda: trigger_job_matching(
                job_ids=import_result["job_ids"],
                global_role_id=session_data["global_role_id"],
                role_name=session_data["role_name"],
                session_id=session_id
            )
        )
    
    logger.info(
        f"[JOB-IMPORT] ✅ Completed: {import_result['imported']} imported, "
        f"{import_result['skipped']} skipped"
    )
    
    return {
        "status": "success",
        "session_id": session_id,
        "jobs_imported": import_result["imported"],
        "jobs_skipped": import_result["skipped"],
        "job_ids": import_result["job_ids"]
    }


def validate_session(session_id: str, scraper_key_id: int) -> Dict[str, Any]:
    """Validate session exists and is in correct state."""
    session = ScrapeSession.query.filter_by(
        session_id=UUID(session_id),
        scraper_key_id=scraper_key_id
    ).first()
    
    if not session:
        logger.error(f"Session {session_id} not found")
        return None
    
    if session.status != "in_progress":
        logger.error(f"Session {session_id} has invalid status: {session.status}")
        return None
    
    # Return serializable dict (not ORM object)
    return {
        "session_id": str(session.session_id),
        "scraper_key_id": session.scraper_key_id,
        "global_role_id": session.global_role_id,
        "role_name": session.role_name
    }


def import_jobs_batch(
    jobs_data: List[Dict],
    session_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Import batch of jobs with deduplication.
    
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
    
    logger.info(f"[JOB-IMPORT] Processing {len(jobs_data)} jobs for role '{session_data['role_name']}'")
    
    for idx, job_data in enumerate(jobs_data):
        try:
            # Map your schema field names to our internal names
            external_id = job_data.get("jobId") or job_data.get("job_id") or job_data.get("external_job_id")
            platform = job_data.get("platform", "scraper")
            
            # Validate required fields
            title = job_data.get("title")
            company = job_data.get("company")
            
            if not title or not company:
                logger.warning(f"[JOB-IMPORT] Skipping job {idx+1}: Missing title or company")
                skipped_count += 1
                continue
            
            # Check for duplicate by platform + external_job_id
            if external_id:
                existing = JobPosting.query.filter_by(
                    platform=platform,
                    external_job_id=str(external_id)
                ).first()
                
                if existing:
                    logger.debug(f"[JOB-IMPORT] Skipping duplicate: {external_id}")
                    skipped_count += 1
                    continue
            
            # Parse salary
            salary_str = job_data.get("salary", "")
            salary_min, salary_max, currency = job_import_service.parse_salary(salary_str)
            
            # Parse experience
            experience_str = job_data.get("experience", "")
            description = job_data.get("description", "")
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
            
            # Create job posting
            job = JobPosting(
                external_job_id=str(external_id) if external_id else f"scraper-{session_data['session_id']}-{idx}",
                platform=platform,
                title=title,
                company=company,
                location=job_data.get("location"),
                description=description,
                snippet=job_data.get("snippet"),
                requirements=job_data.get("requirements"),
                salary_range=salary_str if salary_str and salary_str.upper() != "N/A" else None,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                experience_required=experience_str if experience_str and experience_str.upper() != "N/A" else None,
                experience_min=exp_min,
                experience_max=exp_max,
                skills=normalized_skills,
                keywords=job_import_service.generate_keywords(title, description, normalized_skills),
                job_type=job_data.get("jobType", job_data.get("job_type")),
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
    
    db.session.commit()
    
    logger.info(
        f"[JOB-IMPORT] Batch complete: {imported_count} imported, "
        f"{skipped_count} skipped"
    )
    
    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "job_ids": job_ids
    }


def complete_session(
    session_id: str,
    scraper_key_id: int,
    jobs_found: int,
    jobs_imported: int,
    jobs_skipped: int
) -> None:
    """Update session to completed status."""
    session = ScrapeSession.query.filter_by(
        session_id=UUID(session_id),
        scraper_key_id=scraper_key_id
    ).first()
    
    if session:
        session.complete(
            jobs_found=jobs_found,
            jobs_imported=jobs_imported,
            jobs_skipped=jobs_skipped
        )
        
        # Update scraper key usage
        scraper_key = db.session.get(ScraperApiKey, scraper_key_id)
        if scraper_key:
            scraper_key.record_usage(jobs_imported=jobs_imported)
        
        db.session.commit()
        
        logger.info(
            f"[JOB-IMPORT] Session {session_id} completed: "
            f"{jobs_imported} imported, {jobs_skipped} skipped"
        )


def update_role_status(global_role_id: int, jobs_imported: int) -> None:
    """Update role status to completed and update job count."""
    role = db.session.get(GlobalRole, global_role_id)
    
    if role:
        role.queue_status = "completed"
        role.last_scraped_at = datetime.utcnow()
        role.total_jobs_scraped = (role.total_jobs_scraped or 0) + jobs_imported
        db.session.commit()
        
        logger.info(
            f"[JOB-IMPORT] Updated role '{role.name}' status to completed, "
            f"total jobs: {role.total_jobs_scraped}"
        )


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
