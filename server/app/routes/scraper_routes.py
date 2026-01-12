"""
Scraper API Routes

External API endpoints for job scrapers to:
1. Fetch next role from queue (GET /api/scraper/queue/next-role) - includes platform list
2. Fetch next role+location from queue (GET /api/scraper/queue/next-role-location) - location-specific scraping
3. Post jobs for a platform (POST /api/scraper/queue/jobs) - per-platform submission
4. Complete session (POST /api/scraper/queue/complete) - finalize and trigger matching
5. Report platform failure (POST /api/scraper/queue/fail) - report failure for a platform

Authentication: X-Scraper-API-Key header
"""
import logging
import math
from functools import wraps
from typing import List, Any
from uuid import UUID
from flask import Blueprint, request, jsonify, g
import inngest

from app import db
from app.models.scraper_api_key import ScraperApiKey
from app.models.scrape_session import ScrapeSession
from app.models.session_platform_status import SessionPlatformStatus
from app.models.scraper_platform import ScraperPlatform
from app.services.scrape_queue_service import ScrapeQueueService
from app.inngest import inngest_client

logger = logging.getLogger(__name__)

scraper_bp = Blueprint('scraper', __name__, url_prefix='/api/scraper')


def require_scraper_auth(f):
    """
    Middleware to validate scraper API key.
    
    Expects X-Scraper-API-Key header.
    Sets g.scraper_key on success.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Scraper-API-Key')
        
        if not api_key:
            return jsonify({
                "error": "Unauthorized",
                "message": "Missing X-Scraper-API-Key header"
            }), 401
        
        # Validate key
        scraper_key = ScraperApiKey.validate_key(api_key)
        
        if not scraper_key:
            return jsonify({
                "error": "Unauthorized",
                "message": "Invalid or revoked API key"
            }), 401
        
        # Set in context
        g.scraper_key = scraper_key
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# QUEUE ENDPOINTS (for external scrapers)
# ============================================================================

@scraper_bp.route('/queue/next-role', methods=['GET'])
@require_scraper_auth
def get_next_role():
    """
    Get next role from the scrape queue with platform checklist.
    
    Note: A scraper can only have ONE active session at a time.
    Complete or terminate the current session before requesting a new role.
    
    Response (200 OK):
    {
        "session_id": "uuid",
        "role": {
            "id": 1,
            "name": "Python Developer",
            "aliases": ["Python Dev", "Python Engineer"],
            "category": "Engineering",
            "candidate_count": 50
        },
        "platforms": [
            { "id": 1, "name": "linkedin", "display_name": "LinkedIn" },
            { "id": 2, "name": "monster", "display_name": "Monster" },
            ...
        ]
    }
    
    Returns 204 No Content if queue is empty.
    Returns 409 Conflict if scraper already has an active session.
    """
    try:
        result = ScrapeQueueService.get_next_role_with_platforms(g.scraper_key)
        
        if not result:
            return '', 204  # No content - queue empty
        
        return jsonify(result), 200
    
    except ValueError as e:
        # Scraper already has an active session
        logger.warning(f"Scraper blocked from getting new role: {e}")
        return jsonify({
            "error": "Conflict",
            "message": str(e),
            "code": "ACTIVE_SESSION_EXISTS"
        }), 409
        
    except Exception as e:
        logger.error(f"Error getting next role: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/next-role-location', methods=['GET'])
@require_scraper_auth
def get_next_role_location():
    """
    Get next role+location combination from the scrape queue with platform checklist.
    
    This is the location-aware version of /queue/next-role.
    Returns role+location combinations for location-specific job scraping.
    
    Note: A scraper can only have ONE active session at a time.
    Complete or terminate the current session before requesting a new role+location.
    
    Response (200 OK):
    {
        "session_id": "uuid",
        "role": {
            "id": 1,
            "name": "Python Developer",
            "aliases": ["Python Dev", "Python Engineer"],
            "category": "Engineering",
            "candidate_count": 50
        },
        "location": "New York, NY",
        "role_location_queue_id": 42,
        "platforms": [
            { "id": 1, "name": "linkedin", "display_name": "LinkedIn" },
            { "id": 2, "name": "monster", "display_name": "Monster" },
            ...
        ]
    }
    
    Returns 204 No Content if queue is empty.
    Returns 409 Conflict if scraper already has an active session.
    """
    try:
        result = ScrapeQueueService.get_next_role_location_with_platforms(g.scraper_key)
        
        if not result:
            return '', 204  # No content - queue empty
        
        return jsonify(result), 200
    
    except ValueError as e:
        # Scraper already has an active session
        logger.warning(f"Scraper blocked from getting new role+location: {e}")
        return jsonify({
            "error": "Conflict",
            "message": str(e),
            "code": "ACTIVE_SESSION_EXISTS"
        }), 409
        
    except Exception as e:
        logger.error(f"Error getting next role+location: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/current-session', methods=['GET'])
@require_scraper_auth
def get_current_session():
    """
    Get the current active session for this scraper (if any).
    
    Useful for:
    - Checking if there's an active session before requesting a new role
    - Resuming work after a scraper restart
    - Debugging session issues
    
    Response (200 OK) - Has active session:
    {
        "has_active_session": true,
        "session": {
            "session_id": "uuid",
            "role_name": "Python Developer",
            "role_id": 42,
            "status": "in_progress",
            "started_at": "2025-12-14T10:00:00Z",
            "platforms_total": 6,
            "platforms_completed": 2,
            "platforms_failed": 0
        }
    }
    
    Response (200 OK) - No active session:
    {
        "has_active_session": false,
        "session": null
    }
    """
    try:
        from app.models.scrape_session import ScrapeSession
        
        active_session = ScrapeSession.query.filter(
            ScrapeSession.scraper_key_id == g.scraper_key.id,
            ScrapeSession.status == "in_progress"
        ).first()
        
        if not active_session:
            return jsonify({
                "has_active_session": False,
                "session": None
            }), 200
        
        return jsonify({
            "has_active_session": True,
            "session": {
                "session_id": str(active_session.session_id),
                "role_name": active_session.role_name,
                "role_id": active_session.global_role_id,
                "location": active_session.location,
                "role_location_queue_id": active_session.role_location_queue_id,
                "status": active_session.status,
                "started_at": active_session.started_at.isoformat() if active_session.started_at else None,
                "platforms_total": active_session.platforms_total or 0,
                "platforms_completed": active_session.platforms_completed or 0,
                "platforms_failed": active_session.platforms_failed or 0,
                "jobs_found": active_session.jobs_found or 0,
                "jobs_imported": active_session.jobs_imported or 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting current session: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/jobs', methods=['POST'])
@require_scraper_auth
def post_jobs():
    """
    Post jobs for a specific platform in a scrape session.
    Can be called multiple times per session (once per platform).
    
    Request body (Success):
    {
        "session_id": "uuid",
        "platform": "linkedin",
        "jobs": [...]
    }
    
    Request body (Failure):
    {
        "session_id": "uuid",
        "platform": "indeed",
        "status": "failed",
        "error_message": "Connection timeout",
        "jobs": []
    }
    
    Response (202 Accepted):
    {
        "status": "accepted",
        "session_id": "uuid",
        "platform": "linkedin",
        "platform_status": "completed",
        "jobs_count": 47,
        "progress": {
            "total_platforms": 6,
            "completed": 1,
            "pending": 5,
            "failed": 0
        }
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body required"
        }), 400
    
    session_id = data.get('session_id')
    platform_name = data.get('platform')
    jobs = data.get('jobs', [])
    is_failed = data.get('status') == 'failed'
    error_message = data.get('error_message', 'Unknown error')
    
    if not session_id:
        return jsonify({
            "error": "Bad Request",
            "message": "session_id required"
        }), 400
    
    if not platform_name:
        return jsonify({
            "error": "Bad Request",
            "message": "platform required"
        }), 400
    
    # Validate session exists and belongs to this scraper key
    session = ScrapeSession.query.filter_by(
        session_id=UUID(session_id),
        scraper_key_id=g.scraper_key.id
    ).first()
    
    if not session:
        return jsonify({
            "error": "Not Found",
            "message": "Session not found or unauthorized"
        }), 404
    
    if session.status not in ['in_progress']:
        return jsonify({
            "error": "Bad Request",
            "message": f"Session already {session.status}"
        }), 400
    
    # Get platform status entry
    platform_status = SessionPlatformStatus.query.filter_by(
        session_id=session.session_id,
        platform_name=platform_name
    ).first()
    
    if not platform_status:
        return jsonify({
            "error": "Bad Request",
            "message": f"Platform '{platform_name}' not found in session"
        }), 400
    
    if platform_status.status not in ['pending', 'in_progress']:
        return jsonify({
            "error": "Bad Request",
            "message": f"Platform '{platform_name}' already {platform_status.status}"
        }), 400
    
    try:
        if is_failed:
            # Mark platform as failed
            platform_status.mark_failed(error_message)
            session.platforms_completed += 1
            session.platforms_failed += 1
            db.session.commit()
            
            logger.info(
                f"Platform {platform_name} failed for session {session_id}: {error_message}"
            )
            
            result = {
                "status": "accepted",
                "session_id": session_id,
                "platform": platform_name,
                "platform_status": "failed",
                "error_message": error_message,
                "jobs_count": 0,
                "progress": _get_session_progress(session)
            }
        else:
            # Batch jobs to avoid Inngest payload size limits (256KB max)
            # Each job can be ~5-10KB, so we use batches of 20 jobs (~100-200KB safe margin)
            BATCH_SIZE = 20
            total_jobs = len(jobs)
            total_batches = max(1, math.ceil(total_jobs / BATCH_SIZE))
            
            # Send batched events
            for batch_index in range(total_batches):
                start_idx = batch_index * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, total_jobs)
                batch_jobs = jobs[start_idx:end_idx]
                
                inngest_client.send_sync(
                    inngest.Event(
                        name="jobs/scraper.platform-import",
                        data={
                            "session_id": session_id,
                            "scraper_key_id": g.scraper_key.id,
                            "platform_name": platform_name,
                            "platform_status_id": platform_status.id,
                            "jobs": batch_jobs,
                            "jobs_count": len(batch_jobs),
                            # Batch metadata for tracking
                            "batch_index": batch_index,
                            "total_batches": total_batches,
                            "total_jobs_in_platform": total_jobs
                        }
                    )
                )
            
            # Mark platform as in_progress (will be completed by workflow)
            platform_status.mark_in_progress()
            # Store total batches for tracking completion
            platform_status.total_batches = total_batches
            platform_status.completed_batches = 0
            db.session.commit()
            
            logger.info(
                f"Triggered job import for platform {platform_name} "
                f"with {total_jobs} jobs in {total_batches} batch(es) (session: {session_id})"
            )
            
            result = {
                "status": "accepted",
                "session_id": session_id,
                "platform": platform_name,
                "platform_status": "processing",
                "jobs_count": total_jobs,
                "batches": total_batches,
                "progress": _get_session_progress(session)
            }
        
        return jsonify(result), 202
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error processing jobs for platform {platform_name}: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/complete', methods=['POST'])
@require_scraper_auth
def complete_session_endpoint():
    """
    Complete a scrape session after all platforms have submitted.
    Triggers job matching workflow for all imported jobs.
    
    Request body:
    {
        "session_id": "uuid"
    }
    
    Response (200 OK):
    {
        "status": "completed",
        "session_id": "uuid",
        "role_name": "Python Developer",
        "summary": {
            "total_platforms": 6,
            "successful_platforms": 5,
            "failed_platforms": 1,
            "failed_platform_details": [
                { "platform": "indeed", "error": "Connection timeout" }
            ]
        },
        "jobs": {
            "total_found": 165,
            "total_imported": 158,
            "total_skipped": 7
        },
        "duration_seconds": 450,
        "matching_triggered": true
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body required"
        }), 400
    
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({
            "error": "Bad Request",
            "message": "session_id required"
        }), 400
    
    # Validate session
    session = ScrapeSession.query.filter_by(
        session_id=UUID(session_id),
        scraper_key_id=g.scraper_key.id
    ).first()
    
    if not session:
        return jsonify({
            "error": "Not Found",
            "message": "Session not found or unauthorized"
        }), 404
    
    if session.status == 'completed':
        return jsonify({
            "error": "Bad Request",
            "message": "Session already completed"
        }), 400
    
    try:
        # Trigger session completion workflow
        inngest_client.send_sync(
            inngest.Event(
                name="jobs/scraper.complete",
                data={
                    "session_id": session_id,
                    "scraper_key_id": g.scraper_key.id
                }
            )
        )
        
        # Get current stats for response
        platform_statuses = session.platform_statuses
        
        failed_platforms = [
            {"platform": ps.platform_name, "error": ps.error_message}
            for ps in platform_statuses if ps.status == 'failed'
        ]
        
        total_found = sum(ps.jobs_found for ps in platform_statuses)
        total_imported = sum(ps.jobs_imported for ps in platform_statuses)
        total_skipped = sum(ps.jobs_skipped for ps in platform_statuses)
        
        result = {
            "status": "completing",
            "message": "Session completion triggered",
            "session_id": session_id,
            "role_name": session.role_name,
            "location": session.location,
            "role_location_queue_id": session.role_location_queue_id,
            "summary": {
                "total_platforms": session.platforms_total,
                "successful_platforms": session.platforms_completed - session.platforms_failed,
                "failed_platforms": session.platforms_failed,
                "failed_platform_details": failed_platforms
            },
            "jobs": {
                "total_found": total_found,
                "total_imported": total_imported,
                "total_skipped": total_skipped
            },
            "matching_triggered": total_imported > 0
        }
        
        logger.info(f"Session completion triggered: {session_id}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error completing session: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/fail', methods=['POST'])
@require_scraper_auth
def fail_session():
    """
    Report a failed scrape session.
    
    Request body:
    {
        "session_id": "uuid",
        "error_message": "Connection timeout to job board"
    }
    
    Response:
    {
        "session_id": "uuid",
        "status": "failed",
        "error_message": "..."
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body required"
        }), 400
    
    session_id = data.get('session_id')
    error_message = data.get('error_message', 'Unknown error')
    
    if not session_id:
        return jsonify({
            "error": "Bad Request",
            "message": "session_id required"
        }), 400
    
    try:
        result = ScrapeQueueService.fail_session(
            session_id=session_id,
            error_message=error_message,
            scraper_key=g.scraper_key
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error failing session: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/stats', methods=['GET'])
@require_scraper_auth
def get_queue_stats():
    """
    Get queue statistics.
    
    Response:
    {
        "by_status": {"pending": 50, "processing": 3, "completed": 200},
        "by_priority": {"urgent": 5, "high": 15, "normal": 30},
        "total_pending_candidates": 1234,
        "queue_depth": 50
    }
    """
    try:
        stats = ScrapeQueueService.get_queue_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/location-stats', methods=['GET'])
@require_scraper_auth
def get_role_location_queue_stats():
    """
    Get role+location queue statistics.
    
    Response:
    {
        "by_status": {"pending": 50, "approved": 20, "processing": 3, "completed": 200},
        "by_priority": {"urgent": 5, "high": 15, "normal": 30, "low": 10},
        "total_location_entries": 60,
        "unique_roles": 15,
        "unique_locations": 8,
        "queue_depth": 20
    }
    """
    try:
        stats = ScrapeQueueService.get_role_location_queue_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting role+location queue stats: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint (no auth required).
    
    Response:
    {
        "status": "healthy",
        "service": "scraper-api"
    }
    """
    return jsonify({
        "status": "healthy",
        "service": "scraper-api"
    }), 200


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_session_progress(session: ScrapeSession) -> dict:
    """Get progress stats for a session."""
    platform_statuses = SessionPlatformStatus.query.filter_by(
        session_id=session.session_id
    ).all()
    
    total = len(platform_statuses)
    completed = sum(1 for ps in platform_statuses if ps.status == 'completed')
    failed = sum(1 for ps in platform_statuses if ps.status == 'failed')
    in_progress = sum(1 for ps in platform_statuses if ps.status == 'in_progress')
    pending = sum(1 for ps in platform_statuses if ps.status == 'pending')
    
    return {
        "total_platforms": total,
        "completed": completed,
        "in_progress": in_progress,
        "pending": pending,
        "failed": failed
    }


# ============================================================================
# PLATFORM MANAGEMENT ENDPOINTS (for PM_ADMIN dashboard)
# ============================================================================

from app.middleware.pm_admin import require_pm_admin
from app.services.platform_service import PlatformService


@scraper_bp.route('/platforms', methods=['GET'])
@require_pm_admin
def list_platforms():
    """
    List all scraper platforms.
    
    Response:
    {
        "platforms": [
            {
                "id": 1,
                "name": "linkedin",
                "display_name": "LinkedIn Jobs",
                "base_url": "https://linkedin.com/jobs",
                "is_active": true,
                "priority": 1,
                "description": null,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        ],
        "total": 6
    }
    """
    try:
        platforms = PlatformService.get_all_platforms(include_inactive=True)
        return jsonify({
            "platforms": platforms,
            "total": len(platforms)
        }), 200
    except Exception as e:
        logger.error(f"Error listing platforms: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/platforms/active', methods=['GET'])
@require_pm_admin
def list_active_platforms():
    """
    List only active scraper platforms.
    
    Response:
    {
        "platforms": [...],
        "total": 5
    }
    """
    try:
        platforms = PlatformService.get_all_platforms(include_inactive=False)
        return jsonify({
            "platforms": platforms,
            "total": len(platforms)
        }), 200
    except Exception as e:
        logger.error(f"Error listing active platforms: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/platforms/<int:platform_id>', methods=['GET'])
@require_pm_admin
def get_platform(platform_id: int):
    """
    Get a single platform by ID.
    
    Response:
    {
        "platform": {...}
    }
    """
    try:
        platform = PlatformService.get_platform_by_id(platform_id)
        if not platform:
            return jsonify({
                "error": "Not Found",
                "message": f"Platform {platform_id} not found"
            }), 404
        
        return jsonify({
            "platform": platform.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error getting platform: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/platforms', methods=['POST'])
@require_pm_admin
def create_platform():
    """
    Create a new scraper platform.
    
    Request body:
    {
        "name": "ziprecruiter",
        "display_name": "ZipRecruiter",
        "base_url": "https://ziprecruiter.com",
        "is_active": true,
        "priority": 7,
        "description": "ZipRecruiter job platform"
    }
    
    Response:
    {
        "message": "Platform created",
        "platform": {...}
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Bad Request",
                "message": "Request body is required"
            }), 400
        
        if 'name' not in data:
            return jsonify({
                "error": "Bad Request",
                "message": "Platform name is required"
            }), 400
        
        if 'display_name' not in data:
            return jsonify({
                "error": "Bad Request",
                "message": "Display name is required"
            }), 400
        
        platform = PlatformService.create_platform(
            name=data['name'],
            display_name=data['display_name'],
            base_url=data.get('base_url'),
            is_active=data.get('is_active', True),
            priority=data.get('priority', 10),
            description=data.get('description')
        )
        
        return jsonify({
            "message": "Platform created",
            "platform": platform.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating platform: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/platforms/<int:platform_id>', methods=['PUT'])
@require_pm_admin
def update_platform(platform_id: int):
    """
    Update an existing platform.
    
    Request body (all fields optional):
    {
        "display_name": "Updated Name",
        "base_url": "https://new-url.com",
        "is_active": false,
        "priority": 5,
        "description": "Updated description"
    }
    
    Response:
    {
        "message": "Platform updated",
        "platform": {...}
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Bad Request",
                "message": "Request body is required"
            }), 400
        
        platform = PlatformService.update_platform(platform_id, **data)
        
        if not platform:
            return jsonify({
                "error": "Not Found",
                "message": f"Platform {platform_id} not found"
            }), 404
        
        return jsonify({
            "message": "Platform updated",
            "platform": platform.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error updating platform: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/platforms/<int:platform_id>', methods=['DELETE'])
@require_pm_admin
def delete_platform(platform_id: int):
    """
    Delete a platform.
    
    Response:
    {
        "message": "Platform deleted"
    }
    """
    try:
        success = PlatformService.delete_platform(platform_id)
        
        if not success:
            return jsonify({
                "error": "Not Found",
                "message": f"Platform {platform_id} not found"
            }), 404
        
        return jsonify({
            "message": "Platform deleted"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting platform: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/platforms/stats', methods=['GET'])
@require_pm_admin
def get_platform_stats():
    """
    Get platform usage statistics.
    
    Response:
    {
        "total": 6,
        "active": 5,
        "inactive": 1,
        "by_platform": {...}
    }
    """
    try:
        platforms = PlatformService.get_all_platforms_stats(days=7)
        total = len(platforms)
        active = sum(1 for p in platforms if p.get('is_active'))
        inactive = total - active
        return jsonify({
            'total': total,
            'active': active,
            'inactive': inactive,
            'platforms': platforms
        }), 200
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500
