"""
Scrape Queue Service

Manages the role-based scrape queue for external scrapers.

Key Features:
- FIFO queue with priority support
- Session tracking for observability
- Job import handling with deduplication
- Event triggering for job matching
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import select, case, func, and_, or_
import inngest

from app import db
from app.models.global_role import GlobalRole
from app.models.scrape_session import ScrapeSession
from app.models.scraper_api_key import ScraperApiKey
from app.models.job_posting import JobPosting
from app.models.role_job_mapping import RoleJobMapping
from app.models.scraper_platform import ScraperPlatform
from app.models.session_platform_status import SessionPlatformStatus
from app.services.job_import_service import JobImportService
from app.inngest import inngest_client
from config.settings import settings

logger = logging.getLogger(__name__)


class ScrapeQueueService:
    """
    Service for managing the role-based scrape queue.
    
    Key Design: Role-based, not candidate-based
    - One role scraped → benefits ALL candidates linked to that role
    - Avoids duplicate scrapes when 100 candidates want "Python Developer"
    
    Queue Priority (highest to lowest):
    1. urgent: High-value roles, manual escalation
    2. high: Roles with many candidates waiting
    3. normal: Regular queue processing
    4. low: Background refresh (stale roles)
    
    Within same priority: higher candidate_count first
    """
    
    # Session timeout in seconds (1 hour)
    SESSION_TIMEOUT_SECONDS = 3600
    
    @staticmethod
    def get_queue_stats() -> Dict[str, Any]:
        """
        Get queue statistics for dashboard.
        
        Returns:
            Dict with queue counts by status and priority
        """
        # Count by status
        status_counts = db.session.execute(
            select(
                GlobalRole.queue_status,
                func.count(GlobalRole.id)
            ).group_by(GlobalRole.queue_status)
        ).fetchall()
        
        # Count by priority (for approved roles in the scrape queue)
        priority_counts = db.session.execute(
            select(
                GlobalRole.priority,
                func.count(GlobalRole.id)
            ).where(
                GlobalRole.queue_status == 'approved'
            ).group_by(GlobalRole.priority)
        ).fetchall()
        
        # Total candidates waiting (approved roles only)
        total_candidates = db.session.execute(
            select(func.sum(GlobalRole.candidate_count)).where(
                GlobalRole.queue_status == 'approved'
            )
        ).scalar() or 0
        
        # Queue depth = approved roles
        queue_depth = sum(row[1] for row in status_counts if row[0] == 'approved')
        
        return {
            "by_status": {row[0]: row[1] for row in status_counts},
            "by_priority": {row[0]: row[1] for row in priority_counts},
            "total_pending_candidates": total_candidates,
            "queue_depth": queue_depth
        }
    
    @staticmethod
    def get_next_role(scraper_key: ScraperApiKey) -> Optional[Dict[str, Any]]:
        """
        Get next role from queue and start session.
        
        Called by: GET /api/scraper/queue/next-role
        
        Args:
            scraper_key: Authenticated scraper API key
        
        Returns:
            Dict with session_id and role details, or None if queue empty
        """
        # Find approved roles ready for scraping, prioritized by priority + candidate_count
        # 'approved' = auto-approved, ready for scraping
        role = GlobalRole.query.filter(
            GlobalRole.queue_status == "approved"
        ).order_by(
            case(
                (GlobalRole.priority == "urgent", 4),
                (GlobalRole.priority == "high", 3),
                (GlobalRole.priority == "normal", 2),
                (GlobalRole.priority == "low", 1),
            ).desc(),
            GlobalRole.candidate_count.desc()  # Higher demand = higher priority
        ).first()
        
        if not role:
            logger.info("Scrape queue is empty")
            return None
        
        # Mark role as processing
        role.queue_status = "processing"
        role.updated_at = datetime.utcnow()
        
        # Create session for tracking
        session = ScrapeSession(
            session_id=uuid.uuid4(),
            scraper_key_id=scraper_key.id,
            scraper_name=scraper_key.name,
            global_role_id=role.id,
            role_name=role.name,
            started_at=datetime.utcnow(),
            status="in_progress"
        )
        db.session.add(session)
        
        # Record API key usage
        scraper_key.record_usage()
        
        db.session.commit()
        
        logger.info(
            f"Assigned role '{role.name}' (id={role.id}) to scraper '{scraper_key.name}' "
            f"(session={session.session_id})"
        )
        
        return {
            "session_id": str(session.session_id),
            "role": {
                "id": role.id,
                "name": role.name,
                "aliases": role.aliases or [],
                "category": role.category,
                "candidate_count": role.candidate_count
            }
        }
    
    @staticmethod
    def get_next_role_with_platforms(scraper_key: ScraperApiKey) -> Optional[Dict[str, Any]]:
        """
        Get next role from queue with platform checklist.
        Creates session and platform status entries for each active platform.
        
        Called by: GET /api/scraper/queue/next-role
        
        Args:
            scraper_key: Authenticated scraper API key
        
        Returns:
            Dict with session_id, role details, and platforms list, or None if queue empty
        
        Raises:
            ValueError: If scraper already has an active session
        """
        # Check if this API key already has an active session
        active_session = ScrapeSession.query.filter(
            ScrapeSession.scraper_key_id == scraper_key.id,
            ScrapeSession.status == "in_progress"
        ).first()
        
        if active_session:
            logger.warning(
                f"Scraper '{scraper_key.name}' (key_id={scraper_key.id}) already has an active session: "
                f"{active_session.session_id} for role '{active_session.role_name}'"
            )
            raise ValueError(
                f"Scraper already has an active session ({active_session.session_id}) "
                f"for role '{active_session.role_name}'. "
                f"Complete or terminate the current session before requesting a new role."
            )
        
        # Find approved roles ready for scraping, prioritized by priority + candidate_count
        role = GlobalRole.query.filter(
            GlobalRole.queue_status == "approved"
        ).order_by(
            case(
                (GlobalRole.priority == "urgent", 4),
                (GlobalRole.priority == "high", 3),
                (GlobalRole.priority == "normal", 2),
                (GlobalRole.priority == "low", 1),
            ).desc(),
            GlobalRole.candidate_count.desc()
        ).first()
        
        if not role:
            logger.info("Scrape queue is empty - no approved roles")
            return None
        
        # Get active platforms
        active_platforms = ScraperPlatform.get_active_platforms()
        
        if not active_platforms:
            logger.warning("No active platforms configured")
            return None
        
        # Mark role as processing
        role.queue_status = "processing"
        role.updated_at = datetime.utcnow()
        
        # Create session for tracking
        session = ScrapeSession(
            session_id=uuid.uuid4(),
            scraper_key_id=scraper_key.id,
            scraper_name=scraper_key.name,
            global_role_id=role.id,
            role_name=role.name,
            started_at=datetime.utcnow(),
            status="in_progress",
            platforms_total=len(active_platforms),
            platforms_completed=0,
            platforms_failed=0
        )
        db.session.add(session)
        db.session.flush()  # Get session_id
        
        # Create platform status entries for each active platform
        platform_list = []
        for platform in active_platforms:
            platform_status = SessionPlatformStatus(
                session_id=session.session_id,
                platform_id=platform.id,
                platform_name=platform.name,
                status="pending"
            )
            db.session.add(platform_status)
            
            platform_list.append({
                "id": platform.id,
                "name": platform.name,
                "display_name": platform.display_name
            })
        
        # Record API key usage
        scraper_key.record_usage()
        
        db.session.commit()
        
        logger.info(
            f"Assigned role '{role.name}' (id={role.id}) to scraper '{scraper_key.name}' "
            f"(session={session.session_id}) with {len(platform_list)} platforms"
        )
        
        return {
            "session_id": str(session.session_id),
            "role": {
                "id": role.id,
                "name": role.name,
                "aliases": role.aliases or [],
                "category": role.category,
                "candidate_count": role.candidate_count
            },
            "platforms": platform_list
        }
    
    @staticmethod
    def complete_session(
        session_id: str,
        jobs_data: List[Dict],
        scraper_key: ScraperApiKey
    ) -> Dict[str, Any]:
        """
        Complete session and import jobs.
        
        Called by: POST /api/scraper/queue/jobs
        
        Args:
            session_id: Session ID from get_next_role
            jobs_data: List of job objects to import
            scraper_key: Authenticated scraper API key
        
        Returns:
            Import results with statistics
        """
        # Find session
        session = ScrapeSession.query.filter_by(
            session_id=uuid.UUID(session_id),
            scraper_key_id=scraper_key.id
        ).first()
        
        if not session:
            raise ValueError("Session not found or unauthorized")
        
        if session.status != "in_progress":
            raise ValueError(f"Session already {session.status}")
        
        logger.info(
            f"Completing session {session_id} with {len(jobs_data)} jobs "
            f"for role '{session.role_name}'"
        )
        
        # Import jobs
        import_result = ScrapeQueueService._import_jobs(
            jobs_data=jobs_data,
            scraper_key=scraper_key,
            session=session
        )
        
        # Update session
        session.complete(
            jobs_found=len(jobs_data),
            jobs_imported=import_result["imported"],
            jobs_skipped=import_result["skipped"]
        )
        
        # Update role status
        role = db.session.get(GlobalRole, session.global_role_id)
        if role:
            role.queue_status = "completed"
            role.last_scraped_at = datetime.utcnow()
            role.total_jobs_scraped += import_result["imported"]
        
        # Record API key usage with job count
        scraper_key.record_usage(jobs_imported=import_result["imported"])
        
        db.session.commit()
        
        # Trigger job matching event if jobs were imported
        if import_result["job_ids"]:
            try:
                inngest_client.send_sync(
                    inngest.Event(
                        name="jobs/imported",
                        data={
                            "job_ids": import_result["job_ids"],
                            "global_role_id": session.global_role_id,
                            "role_name": session.role_name,
                            "session_id": str(session.session_id),
                            "source": "scraper"
                        }
                    )
                )
                logger.info(f"Triggered jobs/imported event for {len(import_result['job_ids'])} jobs")
            except Exception as e:
                logger.error(f"Failed to trigger jobs/imported event: {e}")
        
        result = {
            "session_id": str(session.session_id),
            "role_name": session.role_name,
            "jobs_found": session.jobs_found,
            "jobs_imported": session.jobs_imported,
            "jobs_skipped": session.jobs_skipped,
            "duration_seconds": session.duration_seconds,
            "matching_triggered": len(import_result["job_ids"]) > 0
        }
        
        logger.info(f"Session completed: {result}")
        
        return result
    
    @staticmethod
    def _import_jobs(
        jobs_data: List[Dict],
        scraper_key: ScraperApiKey,
        session: ScrapeSession
    ) -> Dict[str, Any]:
        """
        Import jobs from scraper data.
        
        Args:
            jobs_data: List of job objects
            scraper_key: Scraper API key
            session: Scrape session
        
        Returns:
            Dict with imported count, skipped count, and job IDs
        """
        job_import_service = JobImportService()
        
        imported_count = 0
        skipped_count = 0
        job_ids = []
        
        for job_data in jobs_data:
            try:
                # Check for duplicate
                existing = JobPosting.query.filter_by(
                    platform=job_data.get("platform", "scraper"),
                    external_job_id=job_data.get("job_id") or job_data.get("external_job_id")
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Parse job data
                parsed = job_import_service.parse_job_data(job_data)
                
                # Create job posting
                job = JobPosting(
                    external_job_id=parsed.get("external_job_id") or job_data.get("job_id"),
                    platform=parsed.get("platform", "scraper"),
                    title=parsed["title"],
                    company=parsed.get("company", "Unknown"),
                    location=parsed.get("location"),
                    description=parsed.get("description", ""),
                    requirements=parsed.get("requirements"),
                    salary_range=parsed.get("salary_range"),
                    salary_min=parsed.get("salary_min"),
                    salary_max=parsed.get("salary_max"),
                    experience_required=parsed.get("experience_required"),
                    experience_min=parsed.get("experience_min"),
                    experience_max=parsed.get("experience_max"),
                    skills=parsed.get("skills", []),
                    keywords=parsed.get("keywords", []),
                    job_type=parsed.get("job_type"),
                    is_remote=parsed.get("is_remote", False),
                    job_url=parsed.get("job_url", ""),
                    apply_url=parsed.get("apply_url"),
                    posted_date=parsed.get("posted_date"),
                    # Scraper tracking
                    scraped_by_key_id=scraper_key.id,
                    scrape_session_id=session.session_id,
                    normalized_role_id=session.global_role_id,
                    import_batch_id=str(session.session_id)
                )
                
                db.session.add(job)
                db.session.flush()  # Get the ID
                
                # Create role-job mapping
                role_mapping = RoleJobMapping(
                    global_role_id=session.global_role_id,
                    job_posting_id=job.id
                )
                db.session.add(role_mapping)
                
                job_ids.append(job.id)
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Failed to import job: {e}")
                skipped_count += 1
        
        return {
            "imported": imported_count,
            "skipped": skipped_count,
            "job_ids": job_ids
        }
    
    @staticmethod
    def fail_session(
        session_id: str,
        error_message: str,
        scraper_key: ScraperApiKey
    ) -> Dict[str, Any]:
        """
        Mark session as failed.
        
        Validates actual platform statuses before marking session as failed.
        If all platforms are actually completed, marks session as completed instead.
        
        Args:
            session_id: Session ID
            error_message: Error description from scraper
            scraper_key: Scraper API key
        
        Returns:
            Updated session info
        """
        session = ScrapeSession.query.filter_by(
            session_id=uuid.UUID(session_id),
            scraper_key_id=scraper_key.id
        ).first()
        
        if not session:
            raise ValueError("Session not found or unauthorized")
        
        # Check actual platform statuses from database
        platform_statuses = SessionPlatformStatus.query.filter_by(
            session_id=session.session_id
        ).all()
        
        actually_failed = [ps for ps in platform_statuses if ps.status == 'failed']
        actually_completed = [ps for ps in platform_statuses if ps.status == 'completed']
        
        # If no platforms actually failed, don't mark session as failed
        if len(actually_failed) == 0 and len(actually_completed) > 0:
            logger.warning(
                f"Scraper reported failure for session {session_id} but all platforms completed. "
                f"Marking as completed instead. Scraper message: {error_message}"
            )
            # Mark as completed instead
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            session.session_notes = f"Scraper incorrectly reported failure: {error_message}"
            
            # Calculate stats from platform statuses
            session.jobs_found = sum(ps.jobs_found or 0 for ps in platform_statuses)
            session.jobs_imported = sum(ps.jobs_imported or 0 for ps in platform_statuses)
            session.jobs_skipped = sum(ps.jobs_skipped or 0 for ps in platform_statuses)
            session.platforms_completed = len(actually_completed)
            session.platforms_failed = 0
            
            # Reset role to approved for next rotation
            role = db.session.get(GlobalRole, session.global_role_id)
            if role:
                role.queue_status = "approved"
            
            db.session.commit()
            
            return {
                "session_id": str(session.session_id),
                "status": "completed",
                "message": "All platforms completed successfully - scraper failure report was incorrect",
                "jobs_imported": session.jobs_imported,
                "jobs_skipped": session.jobs_skipped
            }
        
        # There are actual failures, mark session as failed
        session.fail(error_message)
        
        # Reset role to approved so it can be retried
        role = db.session.get(GlobalRole, session.global_role_id)
        if role:
            role.queue_status = "approved"
        
        db.session.commit()
        
        logger.warning(f"Session {session_id} failed: {error_message}")
        
        return {
            "session_id": str(session.session_id),
            "status": "failed",
            "error_message": error_message,
            "failed_platforms": [ps.platform_name for ps in actually_failed]
        }
    
    @staticmethod
    def terminate_session(session_id: str) -> Dict[str, Any]:
        """
        Terminate a session and return the role back to the queue.
        
        Used by PM_ADMIN to manually stop a stuck session and allow the role
        to be picked up again by another scraper.
        
        Args:
            session_id: Session ID (UUID string)
        
        Returns:
            Dict with session and role status
        
        Raises:
            ValueError: If session not found
        """
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise ValueError(f"Invalid session ID format: {session_id}")
        
        session = ScrapeSession.query.filter_by(session_id=session_uuid).first()
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Only allow terminating in_progress sessions
        if session.status not in ['in_progress', 'completing']:
            raise ValueError(
                f"Cannot terminate session with status '{session.status}'. "
                f"Only 'in_progress' or 'completing' sessions can be terminated."
            )
        
        # Mark session as terminated (using 'failed' status with specific message)
        session.status = 'terminated'
        session.error_message = 'Manually terminated by PM_ADMIN'
        session.completed_at = datetime.utcnow()
        if session.started_at:
            session.duration_seconds = int((session.completed_at - session.started_at).total_seconds())
        
        # Reset the role back to approved status so it goes back in the queue
        role_name = session.role_name
        role_id = session.global_role_id
        
        if session.global_role_id:
            role = db.session.get(GlobalRole, session.global_role_id)
            if role:
                role.queue_status = 'approved'
                role.updated_at = datetime.utcnow()
                role_name = role.name
                logger.info(f"Role '{role.name}' (id={role.id}) returned to queue")
        
        db.session.commit()
        
        logger.info(f"Session {session_id} terminated manually. Role '{role_name}' returned to queue.")
        
        return {
            "session_id": str(session.session_id),
            "status": "terminated",
            "role_id": role_id,
            "role_name": role_name,
            "role_returned_to_queue": True,
            "message": f"Session terminated. Role '{role_name}' has been returned to the queue."
        }
    
    @staticmethod
    def cleanup_stale_sessions() -> Dict[str, int]:
        """
        Clean up stale sessions that have been in_progress too long.
        
        Called by scheduled task.
        
        Returns:
            Dict with counts of timed out sessions
        """
        timeout_threshold = datetime.utcnow() - timedelta(seconds=ScrapeQueueService.SESSION_TIMEOUT_SECONDS)
        
        # Find stale sessions
        stale_sessions = ScrapeSession.query.filter(
            and_(
                ScrapeSession.status == "in_progress",
                ScrapeSession.started_at < timeout_threshold
            )
        ).all()
        
        timed_out = 0
        
        for session in stale_sessions:
            session.timeout()
            
            # Reset role to approved
            role = db.session.get(GlobalRole, session.global_role_id)
            if role and role.queue_status == "processing":
                role.queue_status = "approved"
            
            timed_out += 1
            logger.warning(f"Session {session.session_id} timed out")
        
        db.session.commit()
        
        return {"timed_out": timed_out}
    
    @staticmethod
    def reset_completed_roles(force: bool = False, hours_threshold: int = 24) -> Dict[str, int]:
        """
        Reset completed roles back to pending for fresh scraping.
        
        Called by daily scheduled task or manual cleanup endpoint.
        
        Args:
            force: If True, reset ALL completed roles regardless of time/candidate count
            hours_threshold: Number of hours after which roles are considered stale (default 24)
        
        Returns:
            Dict with count of reset roles
        """
        if force:
            # Force reset all completed roles back to pending
            reset_count = GlobalRole.query.filter(
                GlobalRole.queue_status == "completed"
            ).update({"queue_status": "pending"})
            
            db.session.commit()
            logger.info(f"Force reset {reset_count} completed roles back to pending")
            return {"reset_count": reset_count, "mode": "force"}
        
        stale_threshold = datetime.utcnow() - timedelta(hours=hours_threshold)
        
        # Find completed roles with stale data OR no last_scraped_at time
        # Roles are reset if:
        # 1. They have candidates and haven't been scraped in X hours, OR
        # 2. They have no last_scraped_at timestamp (never scraped or no record)
        reset_count = GlobalRole.query.filter(
            and_(
                GlobalRole.queue_status == "completed",
                or_(
                    # Roles with candidates that are stale
                    and_(
                        GlobalRole.candidate_count > 0,
                        or_(
                            GlobalRole.last_scraped_at < stale_threshold,
                            GlobalRole.last_scraped_at.is_(None)
                        )
                    ),
                    # Roles with no candidates but marked as completed (shouldn't stay completed)
                    GlobalRole.candidate_count == 0
                )
            )
        ).update({"queue_status": "pending"})
        
        db.session.commit()
        
        logger.info(f"Reset {reset_count} completed roles back to pending (threshold: {hours_threshold}h)")
        
        return {"reset_count": reset_count, "mode": "threshold", "hours": hours_threshold}
    
    @staticmethod
    def get_active_sessions() -> List[Dict[str, Any]]:
        """
        Get all active (in_progress) sessions for monitoring.
        
        Returns:
            List of active session info
        """
        sessions = ScrapeSession.query.filter_by(
            status="in_progress"
        ).order_by(ScrapeSession.started_at.desc()).all()
        
        return [
            {
                "session_id": str(s.session_id),
                "scraper_name": s.scraper_name,
                "role_name": s.role_name,
                "started_at": s.started_at.isoformat(),
                "elapsed_seconds": int((datetime.utcnow() - s.started_at).total_seconds())
            }
            for s in sessions
        ]
    
    @staticmethod
    def get_recent_sessions(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent sessions for activity log.
        
        Args:
            limit: Max sessions to return
        
        Returns:
            List of session info
        """
        sessions = ScrapeSession.query.order_by(
            ScrapeSession.started_at.desc()
        ).limit(limit).all()
        
        return [s.to_dict() for s in sessions]
    
    @staticmethod
    def update_role_priority(role_id: int, priority: str) -> GlobalRole:
        """
        Update role priority.
        
        Args:
            role_id: Global role ID
            priority: New priority (urgent, high, normal, low)
        
        Returns:
            Updated role
        """
        if priority not in ["urgent", "high", "normal", "low"]:
            raise ValueError(f"Invalid priority: {priority}")
        
        role = db.session.get(GlobalRole, role_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")
        
        role.priority = priority
        db.session.commit()
        
        logger.info(f"Updated role '{role.name}' priority to {priority}")
        
        return role
    
    @staticmethod
    def force_queue_role(role_id: int) -> GlobalRole:
        """
        Force a role back into the queue (regardless of current status).
        
        Args:
            role_id: Global role ID
        
        Returns:
            Updated role
        """
        role = db.session.get(GlobalRole, role_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")
        
        role.queue_status = "approved"
        role.priority = "high"  # Bump priority when manually queued
        db.session.commit()
        
        logger.info(f"Forced role '{role.name}' back into queue with high priority")
        
        return role
