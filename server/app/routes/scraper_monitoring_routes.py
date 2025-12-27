"""
Scraper Monitoring Routes (PM_ADMIN)

Dashboard endpoints for monitoring scraper activity, sessions, and API keys.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import func, desc

from app import db
from app.models.scraper_api_key import ScraperApiKey
from app.models.scrape_session import ScrapeSession
from app.models.session_platform_status import SessionPlatformStatus
from app.models.global_role import GlobalRole
from app.models.job_posting import JobPosting
from app.models.role_location_queue import RoleLocationQueue
from app.middleware import require_pm_admin

logger = logging.getLogger(__name__)

scraper_monitoring_bp = Blueprint(
    'scraper_monitoring', 
    __name__, 
    url_prefix='/api/scraper-monitoring'
)


@scraper_monitoring_bp.route('/stats', methods=['GET'])
@require_pm_admin
def get_scraper_stats():
    """
    Get aggregated scraper statistics for dashboard.
    
    Query params:
    - hours: Time range in hours (default: 24)
    
    Response:
    {
        "active_scrapers": 3,
        "pending_queue": 247,
        "jobs_imported_24h": 1543,
        "sessions_24h": {
            "total": 156,
            "completed": 142,
            "failed": 8,
            "in_progress": 6
        },
        "avg_duration_seconds": 125,
        "total_api_keys": 5,
        "active_api_keys": 4
    }
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Active scrapers (with in_progress session in last 10 minutes)
        active_cutoff = datetime.utcnow() - timedelta(minutes=10)
        active_scrapers = db.session.scalar(
            db.select(func.count(func.distinct(ScrapeSession.scraper_key_id)))
            .where(
                ScrapeSession.updated_at >= active_cutoff,
                ScrapeSession.status == 'in_progress'
            )
        ) or 0
        
        # Pending queue count (roles ready to be scraped - approved status)
        pending_queue = db.session.scalar(
            db.select(func.count(GlobalRole.id))
            .where(GlobalRole.queue_status == 'approved')
        ) or 0
        
        # Jobs imported in time period
        jobs_imported = db.session.scalar(
            db.select(func.count(JobPosting.id))
            .where(JobPosting.imported_at >= since)
        ) or 0
        
        # Jobs stats from sessions (found, imported, skipped)
        jobs_stats = db.session.execute(
            db.select(
                func.coalesce(func.sum(ScrapeSession.jobs_found), 0).label('total_found'),
                func.coalesce(func.sum(ScrapeSession.jobs_imported), 0).label('total_imported'),
                func.coalesce(func.sum(ScrapeSession.jobs_skipped), 0).label('total_skipped')
            )
            .where(ScrapeSession.created_at >= since)
        ).first()
        
        # Session statistics
        session_stats = db.session.execute(
            db.select(
                ScrapeSession.status,
                func.count(ScrapeSession.id).label('count')
            )
            .where(ScrapeSession.created_at >= since)
            .group_by(ScrapeSession.status)
        ).all()
        
        sessions_by_status = {row[0]: row[1] for row in session_stats}
        
        # Average duration of completed sessions
        avg_duration = db.session.scalar(
            db.select(func.avg(ScrapeSession.duration_seconds))
            .where(
                ScrapeSession.status == 'completed',
                ScrapeSession.created_at >= since
            )
        ) or 0
        
        # API key counts
        total_keys = db.session.scalar(
            db.select(func.count(ScraperApiKey.id))
        ) or 0
        
        active_keys = db.session.scalar(
            db.select(func.count(ScraperApiKey.id))
            .where(ScraperApiKey.is_active == True)
        ) or 0
        
        # Count of roles that need PM_ADMIN review (newly normalized, awaiting approval)
        # These are roles with queue_status='pending' that were recently created
        # For the dashboard, we show all pending roles as "Roles to Review"
        pending_roles_count = pending_queue  # Same as pending queue for now
        
        # =========================================================================
        # LOCATION ANALYTICS
        # =========================================================================
        
        # Sessions with location (role+location scraping) vs without
        location_session_counts = db.session.execute(
            db.select(
                func.count(ScrapeSession.id).filter(ScrapeSession.location.isnot(None)).label('with_location'),
                func.count(ScrapeSession.id).filter(ScrapeSession.location.is_(None)).label('without_location')
            )
            .where(ScrapeSession.created_at >= since)
        ).first()
        
        # Jobs by location (top 10 locations by jobs imported in last 24h)
        jobs_by_location = db.session.execute(
            db.select(
                ScrapeSession.location,
                func.sum(ScrapeSession.jobs_found).label('jobs_found'),
                func.sum(ScrapeSession.jobs_imported).label('jobs_imported'),
                func.count(ScrapeSession.id).label('session_count')
            )
            .where(
                ScrapeSession.created_at >= since,
                ScrapeSession.location.isnot(None)
            )
            .group_by(ScrapeSession.location)
            .order_by(func.sum(ScrapeSession.jobs_imported).desc())
            .limit(10)
        ).all()
        
        # Role+Location queue stats
        location_queue_stats = db.session.execute(
            db.select(
                RoleLocationQueue.queue_status,
                func.count(RoleLocationQueue.id).label('count')
            )
            .group_by(RoleLocationQueue.queue_status)
        ).all()
        
        location_queue_by_status = {row[0]: row[1] for row in location_queue_stats}
        
        # Unique locations in queue
        unique_locations_in_queue = db.session.scalar(
            db.select(func.count(func.distinct(RoleLocationQueue.location)))
        ) or 0
        
        # Total role+location entries
        total_location_entries = db.session.scalar(
            db.select(func.count(RoleLocationQueue.id))
        ) or 0
        
        return jsonify({
            "active_scrapers": active_scrapers,
            "pending_queue": pending_queue,
            "pending_roles_count": pending_roles_count,  # For dashboard "Roles to Review" card
            "jobs_imported_24h": jobs_imported,
            "jobs_imported_today": jobs_imported,  # Alias for frontend compatibility
            "jobs_stats_24h": {
                "total_found": int(jobs_stats.total_found) if jobs_stats else 0,
                "total_imported": int(jobs_stats.total_imported) if jobs_stats else 0,
                "total_skipped": int(jobs_stats.total_skipped) if jobs_stats else 0,
                "success_rate": round((int(jobs_stats.total_imported) / int(jobs_stats.total_found) * 100) if jobs_stats and jobs_stats.total_found > 0 else 0, 1)
            },
            "sessions_24h": {
                "total": sum(sessions_by_status.values()),
                "completed": sessions_by_status.get('completed', 0),
                "failed": sessions_by_status.get('failed', 0),
                "in_progress": sessions_by_status.get('in_progress', 0),
                "timeout": sessions_by_status.get('timeout', 0)
            },
            "avg_duration_seconds": int(avg_duration),
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
            "location_analytics": {
                "sessions_with_location": location_session_counts.with_location if location_session_counts else 0,
                "sessions_without_location": location_session_counts.without_location if location_session_counts else 0,
                "top_locations": [
                    {
                        "location": row.location,
                        "jobs_found": int(row.jobs_found) if row.jobs_found else 0,
                        "jobs_imported": int(row.jobs_imported) if row.jobs_imported else 0,
                        "session_count": int(row.session_count) if row.session_count else 0
                    }
                    for row in jobs_by_location
                ],
                "queue": {
                    "total": total_location_entries,
                    "pending": location_queue_by_status.get('pending', 0),
                    "approved": location_queue_by_status.get('approved', 0),
                    "processing": location_queue_by_status.get('processing', 0),
                    "completed": location_queue_by_status.get('completed', 0),
                    "unique_locations": unique_locations_in_queue
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting scraper stats: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/sessions', methods=['GET'])
@require_pm_admin
def get_recent_sessions():
    """
    Get recent scrape sessions for dashboard monitoring.
    
    Query params:
    - scraper_key_id: Filter by scraper key
    - status: Filter by status
    - hours: Time range (default: 24)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    """
    try:
        scraper_key_id = request.args.get('scraper_key_id', type=int)
        status = request.args.get('status')
        hours = request.args.get('hours', 24, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = db.select(ScrapeSession).where(ScrapeSession.started_at >= since)
        
        if scraper_key_id:
            query = query.where(ScrapeSession.scraper_key_id == scraper_key_id)
        if status:
            query = query.where(ScrapeSession.status == status)
        
        query = query.order_by(desc(ScrapeSession.started_at))
        
        pagination = db.paginate(query, page=page, per_page=per_page)
        
        sessions = [{
            "id": s.id,
            "session_id": str(s.session_id),
            "scraper_name": s.scraper_name,
            "scraper_key_id": s.scraper_key_id,
            "role_id": s.global_role_id,
            "role_name": s.role_name,
            "location": s.location,
            "role_location_queue_id": s.role_location_queue_id,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "duration_seconds": s.duration_seconds,
            "jobs_found": s.jobs_found or 0,
            "jobs_imported": s.jobs_imported or 0,
            "jobs_skipped": s.jobs_skipped or 0,
            "platforms_total": s.platforms_total or 0,
            "platforms_completed": s.platforms_completed or 0,
            "platforms_failed": s.platforms_failed or 0,
            "error_message": s.error_message
        } for s in pagination.items]
        
        return jsonify({
            "sessions": sessions,
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/sessions/<session_id>', methods=['GET'])
@require_pm_admin
def get_session_details(session_id: str):
    """
    Get detailed session information including platform-level statuses.
    
    Path params:
    - session_id: UUID of the session
    
    Returns detailed session info with all platform statuses and error messages.
    """
    try:
        # Get session by UUID
        session = db.session.scalar(
            db.select(ScrapeSession).where(ScrapeSession.session_id == session_id)
        )
        
        if not session:
            return jsonify({
                "error": "Not Found",
                "message": f"Session with ID {session_id} not found"
            }), 404
        
        # Get platform statuses for this session (session_id in platform_status is UUID)
        platform_statuses = db.session.scalars(
            db.select(SessionPlatformStatus)
            .where(SessionPlatformStatus.session_id == session.session_id)
            .order_by(SessionPlatformStatus.started_at.asc())
        ).all()
        
        # Build platform details
        platforms = []
        for ps in platform_statuses:
            platforms.append({
                "id": ps.id,
                "platform_name": ps.platform_name,
                "status": ps.status,
                "jobs_found": ps.jobs_found or 0,
                "jobs_imported": ps.jobs_imported or 0,
                "jobs_skipped": ps.jobs_skipped or 0,
                "started_at": ps.started_at.isoformat() if ps.started_at else None,
                "completed_at": ps.completed_at.isoformat() if ps.completed_at else None,
                "duration_seconds": ps.duration_seconds,
                "error_message": ps.error_message
            })
        
        # Build session response
        session_data = {
            "id": session.id,
            "session_id": str(session.session_id),
            "scraper_name": session.scraper_name,
            "scraper_key_id": session.scraper_key_id,
            "role_id": session.global_role_id,
            "role_name": session.role_name,
            "location": session.location,
            "role_location_queue_id": session.role_location_queue_id,
            "status": session.status,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "duration_seconds": session.duration_seconds,
            "jobs_found": session.jobs_found or 0,
            "jobs_imported": session.jobs_imported or 0,
            "jobs_skipped": session.jobs_skipped or 0,
            "platforms_total": session.platforms_total or 0,
            "platforms_completed": session.platforms_completed or 0,
            "platforms_failed": session.platforms_failed or 0,
            "error_message": session.error_message,
            "platform_statuses": platforms
        }
        
        return jsonify(session_data), 200
        
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/sessions/<session_id>/terminate', methods=['POST'])
@require_pm_admin
def terminate_session(session_id: str):
    """
    Terminate a session and return the role to the queue.
    
    Use this to manually stop a stuck/hanging session and allow the role
    to be picked up again by another scraper.
    
    Path params:
    - session_id: UUID of the session to terminate
    
    Response:
    {
        "session_id": "uuid",
        "status": "terminated",
        "role_id": 42,
        "role_name": "Python Developer",
        "role_returned_to_queue": true,
        "message": "Session terminated. Role 'Python Developer' has been returned to the queue."
    }
    """
    from app.services.scrape_queue_service import ScrapeQueueService
    
    try:
        result = ScrapeQueueService.terminate_session(session_id)
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Terminate session error: {e}")
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error terminating session {session_id}: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/api-keys', methods=['GET'])
@require_pm_admin
def get_api_keys():
    """
    Get all scraper API keys (for management dashboard).
    """
    try:
        keys = db.session.scalars(
            db.select(ScraperApiKey).order_by(desc(ScraperApiKey.created_at))
        ).all()
        
        def get_status(k):
            if k.revoked_at:
                return 'revoked'
            elif not k.is_active:
                return 'paused'
            return 'active'
        
        return jsonify({
            "api_keys": [{
                "id": k.id,
                "name": k.name,
                "description": k.description,
                "key_prefix": k.key_hash[:12] + "..." if k.key_hash else None,
                "status": get_status(k),
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "total_requests": k.total_requests,
                "total_jobs_scraped": k.total_jobs_imported or 0,
                "total_jobs_imported": k.total_jobs_imported or 0,
                "total_sessions_completed": k.total_requests or 0,
                "rate_limit_per_minute": k.rate_limit_per_minute,
                "created_at": k.created_at.isoformat(),
                "expires_at": None,
                "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None
            } for k in keys]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting API keys: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/api-keys', methods=['POST'])
@require_pm_admin
def create_api_key():
    """
    Create a new scraper API key.
    
    Request body:
    {
        "name": "Production Scraper 1",
        "description": "Main production scraper",
        "rate_limit_per_minute": 60
    }
    
    Response includes the raw key (only shown once):
    {
        "id": 1,
        "name": "Production Scraper 1",
        "api_key": "sk_live_abc123...",  // Only returned on create
        "message": "Store this key securely - it won't be shown again"
    }
    """
    from flask import g
    
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "name is required"
        }), 400
    
    try:
        # Create new key
        api_key, raw_key = ScraperApiKey.create_new_key(
            name=data['name'],
            description=data.get('description'),
            created_by_id=getattr(g, 'pm_admin_id', None),
            rate_limit=data.get('rate_limit_per_minute', 60)
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            "api_key": {
                "id": api_key.id,
                "name": api_key.name,
                "key_prefix": api_key.key_hash[:12] + "..." if api_key.key_hash else None,
                "status": "active",
                "total_jobs_scraped": 0,
                "total_sessions_completed": 0,
                "last_used_at": None,
                "created_at": api_key.created_at.isoformat(),
                "expires_at": None
            },
            "raw_key": raw_key,
            "message": "Store this key securely - it won't be shown again"
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/api-keys/<int:key_id>/revoke', methods=['POST'])
@require_pm_admin
def revoke_api_key(key_id: int):
    """
    Revoke an API key.
    """
    from flask import g
    
    try:
        api_key = db.session.get(ScraperApiKey, key_id)
        
        if not api_key:
            return jsonify({
                "error": "Not Found",
                "message": f"API key {key_id} not found"
            }), 404
        
        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_by = getattr(g, 'pm_admin_id', None)
        
        db.session.commit()
        
        return jsonify({
            "id": api_key.id,
            "name": api_key.name,
            "is_active": False,
            "revoked_at": api_key.revoked_at.isoformat(),
            "message": "API key revoked"
        }), 200
        
    except Exception as e:
        logger.error(f"Error revoking API key {key_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/api-keys/<int:key_id>/activate', methods=['POST'])
@require_pm_admin
def activate_api_key(key_id: int):
    """
    Reactivate a revoked API key.
    """
    try:
        api_key = db.session.get(ScraperApiKey, key_id)
        
        if not api_key:
            return jsonify({
                "error": "Not Found",
                "message": f"API key {key_id} not found"
            }), 404
        
        api_key.is_active = True
        api_key.revoked_at = None
        api_key.revoked_by = None
        
        db.session.commit()
        
        return jsonify({
            "id": api_key.id,
            "name": api_key.name,
            "is_active": True,
            "message": "API key activated"
        }), 200
        
    except Exception as e:
        logger.error(f"Error activating API key {key_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/api-keys/<int:key_id>', methods=['PATCH'])
@require_pm_admin
def update_api_key_status(key_id: int):
    """
    Update API key status (pause/activate).
    """
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "status is required"
        }), 400
    
    status = data.get('status')
    if status not in ('active', 'paused'):
        return jsonify({
            "error": "Bad Request",
            "message": "status must be 'active' or 'paused'"
        }), 400
    
    try:
        api_key = db.session.get(ScraperApiKey, key_id)
        
        if not api_key:
            return jsonify({
                "error": "Not Found",
                "message": f"API key {key_id} not found"
            }), 404
        
        if api_key.revoked_at:
            return jsonify({
                "error": "Bad Request",
                "message": "Cannot update status of a revoked key"
            }), 400
        
        api_key.is_active = (status == 'active')
        db.session.commit()
        
        def get_status(k):
            if k.revoked_at:
                return 'revoked'
            elif not k.is_active:
                return 'paused'
            return 'active'
        
        return jsonify({
            "api_key": {
                "id": api_key.id,
                "name": api_key.name,
                "key_prefix": api_key.key_hash[:12] + "..." if api_key.key_hash else None,
                "status": get_status(api_key),
                "total_jobs_scraped": api_key.total_jobs_imported or 0,
                "total_sessions_completed": api_key.total_requests or 0,
                "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                "created_at": api_key.created_at.isoformat(),
                "expires_at": None
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating API key {key_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@require_pm_admin
def delete_api_key(key_id: int):
    """
    Revoke/delete an API key.
    """
    from flask import g
    
    try:
        api_key = db.session.get(ScraperApiKey, key_id)
        
        if not api_key:
            return jsonify({
                "error": "Not Found",
                "message": f"API key {key_id} not found"
            }), 404
        
        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_by = getattr(g, 'pm_admin_id', None)
        
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        logger.error(f"Error deleting API key {key_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/activity', methods=['GET'])
@require_pm_admin
def get_activity_feed():
    """
    Get recent activity feed for dashboard.
    
    Combines sessions, role changes, and key events.
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 50, type=int)
        since = datetime.utcnow() - timedelta(hours=hours)
        
        activities = []
        
        # Recent sessions
        sessions = db.session.scalars(
            db.select(ScrapeSession)
            .where(ScrapeSession.created_at >= since)
            .order_by(desc(ScrapeSession.created_at))
            .limit(limit)
        ).all()
        
        for s in sessions:
            if s.status == 'completed':
                activities.append({
                    "type": "session_completed",
                    "timestamp": s.completed_at.isoformat() if s.completed_at else s.created_at.isoformat(),
                    "message": f"{s.jobs_imported} jobs imported for {s.role_name}",
                    "details": {
                        "session_id": str(s.session_id),
                        "scraper": s.scraper_name,
                        "role": s.role_name,
                        "jobs_imported": s.jobs_imported
                    }
                })
            elif s.status == 'failed':
                activities.append({
                    "type": "session_failed",
                    "timestamp": s.completed_at.isoformat() if s.completed_at else s.created_at.isoformat(),
                    "message": f"Scrape failed for {s.role_name}: {s.error_message}",
                    "details": {
                        "session_id": str(s.session_id),
                        "scraper": s.scraper_name,
                        "role": s.role_name,
                        "error": s.error_message
                    }
                })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            "activities": activities[:limit]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting activity feed: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


# ============================================================================
# JOB POSTINGS ENDPOINTS (PM_ADMIN)
# ============================================================================

@scraper_monitoring_bp.route('/jobs', methods=['GET'])
@require_pm_admin
def list_all_jobs():
    """
    List all job postings in the database with filters and pagination.
    
    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 100)
    - search: Search in title, company, location
    - platform: Filter by platform (linkedin, indeed, monster, dice, glassdoor, techfetch)
    - location: Filter by location (exact match or contains)
    - status: Filter by status (ACTIVE, EXPIRED, CLOSED)
    - is_remote: Filter remote jobs (true/false)
    - role_id: Filter by normalized role ID
    - sort_by: Sort field (created_at, posted_date, title, company, salary_min)
    - sort_order: asc or desc (default: desc)
    
    Response:
    {
        "jobs": [...],
        "total": 1543,
        "page": 1,
        "per_page": 50,
        "pages": 31,
        "filters": {
            "platforms": ["linkedin", "indeed", ...],
            "statuses": ["ACTIVE", "EXPIRED"],
            "locations": ["New York, NY", "San Francisco, CA", ...]
        }
    }
    """
    from sqlalchemy import or_
    
    try:
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        platform = request.args.get('platform')
        location = request.args.get('location', '').strip()
        status = request.args.get('status')
        is_remote = request.args.get('is_remote')
        role_id = request.args.get('role_id', type=int)
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build base query
        query = db.select(JobPosting)
        count_query = db.select(func.count(JobPosting.id))
        
        # Apply filters
        filters = []
        
        if search:
            search_filter = or_(
                JobPosting.title.ilike(f'%{search}%'),
                JobPosting.company.ilike(f'%{search}%'),
                JobPosting.location.ilike(f'%{search}%')
            )
            filters.append(search_filter)
        
        if location:
            filters.append(JobPosting.location.ilike(f'%{location}%'))
        
        if platform:
            filters.append(JobPosting.platform == platform)
        
        if status:
            filters.append(JobPosting.status == status)
        
        if is_remote is not None:
            is_remote_bool = is_remote.lower() in ('true', '1', 'yes')
            filters.append(JobPosting.is_remote == is_remote_bool)
        
        if role_id:
            filters.append(JobPosting.normalized_role_id == role_id)
        
        # Apply filters to queries
        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)
        
        # Apply sorting
        sort_columns = {
            'created_at': JobPosting.created_at,
            'posted_date': JobPosting.posted_date,
            'title': JobPosting.title,
            'company': JobPosting.company,
            'salary_min': JobPosting.salary_min,
            'imported_at': JobPosting.imported_at
        }
        
        sort_column = sort_columns.get(sort_by, JobPosting.created_at)
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc().nullslast())
        else:
            query = query.order_by(sort_column.desc().nullslast())
        
        # Get total count
        total = db.session.scalar(count_query) or 0
        
        # Execute paginated query
        jobs = db.session.scalars(
            query.offset((page - 1) * per_page).limit(per_page)
        ).all()
        
        # Get available filter options
        platforms = db.session.scalars(
            db.select(JobPosting.platform)
            .distinct()
            .where(JobPosting.platform.isnot(None))
            .order_by(JobPosting.platform)
        ).all()
        
        statuses = db.session.scalars(
            db.select(JobPosting.status)
            .distinct()
            .where(JobPosting.status.isnot(None))
            .order_by(JobPosting.status)
        ).all()
        
        # Get top 50 most common locations for filter dropdown
        location_counts = db.session.execute(
            db.select(JobPosting.location, func.count(JobPosting.id).label('count'))
            .where(JobPosting.location.isnot(None))
            .where(JobPosting.location != '')
            .group_by(JobPosting.location)
            .order_by(desc(func.count(JobPosting.id)))
            .limit(50)
        ).all()
        locations = [loc[0] for loc in location_counts]
        
        return jsonify({
            "jobs": [job.to_dict(include_description=False) for job in jobs],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total > 0 else 0,
            "filters": {
                "platforms": list(platforms),
                "statuses": list(statuses),
                "locations": locations
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/jobs/<int:job_id>', methods=['GET'])
@require_pm_admin
def get_job_detail(job_id: int):
    """
    Get detailed information about a specific job posting.
    
    Response includes full description and related data.
    """
    try:
        job = db.session.get(JobPosting, job_id)
        
        if not job:
            return jsonify({
                "error": "Not Found",
                "message": f"Job posting {job_id} not found"
            }), 404
        
        result = job.to_dict(include_description=True)
        
        # Add scraper info if available
        if job.scraped_by_key:
            result['scraper_name'] = job.scraped_by_key.name
        
        if job.normalized_role:
            result['role_name'] = job.normalized_role.name
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/jobs/statistics', methods=['GET'])
@require_pm_admin
def get_job_statistics():
    """
    Get aggregate statistics about all job postings.
    
    Response:
    {
        "total_jobs": 15432,
        "jobs_by_platform": {
            "linkedin": 5000,
            "indeed": 4000,
            ...
        },
        "jobs_by_status": {
            "ACTIVE": 12000,
            "EXPIRED": 3000,
            ...
        },
        "remote_jobs": 3200,
        "unique_companies": 2100,
        "jobs_today": 150,
        "jobs_this_week": 890
    }
    """
    from datetime import date
    
    try:
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        # Total jobs
        total_jobs = db.session.scalar(
            db.select(func.count(JobPosting.id))
        ) or 0
        
        # Jobs by platform
        platform_stats = db.session.execute(
            db.select(
                JobPosting.platform,
                func.count(JobPosting.id).label('count')
            )
            .group_by(JobPosting.platform)
            .order_by(desc('count'))
        ).all()
        jobs_by_platform = {row[0]: row[1] for row in platform_stats}
        
        # Jobs by status
        status_stats = db.session.execute(
            db.select(
                JobPosting.status,
                func.count(JobPosting.id).label('count')
            )
            .group_by(JobPosting.status)
        ).all()
        jobs_by_status = {row[0]: row[1] for row in status_stats}
        
        # Remote jobs
        remote_jobs = db.session.scalar(
            db.select(func.count(JobPosting.id))
            .where(JobPosting.is_remote == True)
        ) or 0
        
        # Unique companies
        unique_companies = db.session.scalar(
            db.select(func.count(func.distinct(JobPosting.company)))
        ) or 0
        
        # Jobs today
        jobs_today = db.session.scalar(
            db.select(func.count(JobPosting.id))
            .where(func.date(JobPosting.created_at) == today)
        ) or 0
        
        # Jobs this week
        jobs_this_week = db.session.scalar(
            db.select(func.count(JobPosting.id))
            .where(func.date(JobPosting.created_at) >= week_ago)
        ) or 0
        
        return jsonify({
            "total_jobs": total_jobs,
            "jobs_by_platform": jobs_by_platform,
            "jobs_by_status": jobs_by_status,
            "remote_jobs": remote_jobs,
            "unique_companies": unique_companies,
            "jobs_today": jobs_today,
            "jobs_this_week": jobs_this_week
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job statistics: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


# ============================================================================
# ROLE LOCATION QUEUE ENDPOINTS
# ============================================================================

@scraper_monitoring_bp.route('/role-location-queue', methods=['GET'])
@require_pm_admin
def get_role_location_queue():
    """
    Get role+location queue entries for dashboard monitoring.
    
    Query params:
    - status: Filter by status (pending, approved, processing, completed, rejected)
    - search: Search by role name or location
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    
    Response:
    {
        "entries": [...],
        "total": 100,
        "page": 1,
        "per_page": 50,
        "stats": {
            "by_status": {...},
            "total_entries": 100
        }
    }
    """
    try:
        from app.models.role_location_queue import RoleLocationQueue
        
        status_filter = request.args.get('status')
        search = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Build query
        query = db.select(RoleLocationQueue).join(
            GlobalRole, RoleLocationQueue.global_role_id == GlobalRole.id
        )
        
        if status_filter and status_filter != 'all':
            query = query.where(RoleLocationQueue.queue_status == status_filter)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                db.or_(
                    GlobalRole.name.ilike(search_term),
                    RoleLocationQueue.location.ilike(search_term)
                )
            )
        
        # Order by priority and candidate count
        query = query.order_by(
            db.case(
                (RoleLocationQueue.priority == 'urgent', 4),
                (RoleLocationQueue.priority == 'high', 3),
                (RoleLocationQueue.priority == 'normal', 2),
                (RoleLocationQueue.priority == 'low', 1),
            ).desc(),
            RoleLocationQueue.candidate_count.desc()
        )
        
        # Get total count
        count_query = db.select(func.count(RoleLocationQueue.id))
        if status_filter and status_filter != 'all':
            count_query = count_query.where(RoleLocationQueue.queue_status == status_filter)
        total = db.session.scalar(count_query) or 0
        
        # Paginate
        query = query.offset((page - 1) * per_page).limit(per_page)
        entries = db.session.execute(query).scalars().all()
        
        # Get status counts
        status_counts = db.session.execute(
            db.select(
                RoleLocationQueue.queue_status,
                func.count(RoleLocationQueue.id)
            ).group_by(RoleLocationQueue.queue_status)
        ).all()
        
        return jsonify({
            "entries": [
                {
                    "id": entry.id,
                    "global_role_id": entry.global_role_id,
                    "role_name": entry.global_role.name if entry.global_role else None,
                    "location": entry.location,
                    "queue_status": entry.queue_status,
                    "priority": entry.priority,
                    "candidate_count": entry.candidate_count,
                    "total_jobs_scraped": entry.total_jobs_scraped or 0,
                    "last_scraped_at": entry.last_scraped_at.isoformat() if entry.last_scraped_at else None,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                    "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
                }
                for entry in entries
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "stats": {
                "by_status": {row[0]: row[1] for row in status_counts},
                "total_entries": sum(row[1] for row in status_counts)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting role location queue: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/role-location-queue/by-role/<int:role_id>', methods=['GET'])
@require_pm_admin
def get_locations_for_role(role_id: int):
    """
    Get all location queue entries for a specific role.
    
    Path params:
    - role_id: Global role ID
    
    Response:
    {
        "role_id": 42,
        "role_name": "Python Developer",
        "locations": [
            {
                "id": 1,
                "location": "New York, NY",
                "queue_status": "approved",
                "priority": "normal",
                "candidate_count": 5,
                "total_jobs_scraped": 120
            },
            ...
        ],
        "total_locations": 3
    }
    """
    try:
        from app.models.role_location_queue import RoleLocationQueue
        
        # Get the role
        role = db.session.get(GlobalRole, role_id)
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role with ID {role_id} not found"
            }), 404
        
        # Get all location entries for this role
        entries = db.session.query(RoleLocationQueue).filter(
            RoleLocationQueue.global_role_id == role_id
        ).order_by(
            RoleLocationQueue.candidate_count.desc(),
            RoleLocationQueue.location
        ).all()
        
        return jsonify({
            "role_id": role.id,
            "role_name": role.name,
            "locations": [
                {
                    "id": entry.id,
                    "location": entry.location,
                    "queue_status": entry.queue_status,
                    "priority": entry.priority,
                    "candidate_count": entry.candidate_count,
                    "total_jobs_scraped": entry.total_jobs_scraped or 0,
                    "last_scraped_at": entry.last_scraped_at.isoformat() if entry.last_scraped_at else None,
                }
                for entry in entries
            ],
            "total_locations": len(entries)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting locations for role {role_id}: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/role-location-queue/<int:entry_id>/approve', methods=['POST'])
@require_pm_admin
def approve_role_location_entry(entry_id: int):
    """Approve a role+location queue entry for scraping."""
    try:
        from app.models.role_location_queue import RoleLocationQueue
        
        entry = db.session.get(RoleLocationQueue, entry_id)
        if not entry:
            return jsonify({"error": "Not Found", "message": "Entry not found"}), 404
        
        if entry.queue_status not in ['pending', 'rejected']:
            return jsonify({
                "error": "Bad Request",
                "message": f"Cannot approve entry with status '{entry.queue_status}'"
            }), 400
        
        entry.queue_status = 'approved'
        entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Approved role+location entry {entry_id}: {entry.global_role.name} @ {entry.location}")
        
        return jsonify({
            "message": "Entry approved",
            "entry": entry.to_dict(include_role=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving role location entry: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/role-location-queue/<int:entry_id>/reject', methods=['POST'])
@require_pm_admin
def reject_role_location_entry(entry_id: int):
    """Reject a role+location queue entry."""
    try:
        from app.models.role_location_queue import RoleLocationQueue
        
        entry = db.session.get(RoleLocationQueue, entry_id)
        if not entry:
            return jsonify({"error": "Not Found", "message": "Entry not found"}), 404
        
        if entry.queue_status not in ['pending', 'approved']:
            return jsonify({
                "error": "Bad Request",
                "message": f"Cannot reject entry with status '{entry.queue_status}'"
            }), 400
        
        entry.queue_status = 'rejected'
        entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Rejected role+location entry {entry_id}: {entry.global_role.name} @ {entry.location}")
        
        return jsonify({
            "message": "Entry rejected",
            "entry": entry.to_dict(include_role=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting role location entry: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/role-location-queue/<int:entry_id>/priority', methods=['PATCH'])
@require_pm_admin
def update_role_location_priority(entry_id: int):
    """Update priority of a role+location queue entry."""
    try:
        from app.models.role_location_queue import RoleLocationQueue
        
        data = request.get_json() or {}
        priority = data.get('priority')
        
        if priority not in ['urgent', 'high', 'normal', 'low']:
            return jsonify({
                "error": "Bad Request",
                "message": "Invalid priority. Must be: urgent, high, normal, low"
            }), 400
        
        entry = db.session.get(RoleLocationQueue, entry_id)
        if not entry:
            return jsonify({"error": "Not Found", "message": "Entry not found"}), 404
        
        entry.priority = priority
        entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Updated priority for role+location entry {entry_id} to {priority}")
        
        return jsonify({
            "message": "Priority updated",
            "entry": entry.to_dict(include_role=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating role location priority: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/role-location-queue/<int:entry_id>', methods=['DELETE'])
@require_pm_admin
def delete_role_location_entry(entry_id: int):
    """Delete a role+location queue entry."""
    try:
        from app.models.role_location_queue import RoleLocationQueue
        
        entry = db.session.get(RoleLocationQueue, entry_id)
        if not entry:
            return jsonify({"error": "Not Found", "message": "Entry not found"}), 404
        
        role_name = entry.global_role.name if entry.global_role else "Unknown"
        location = entry.location
        
        db.session.delete(entry)
        db.session.commit()
        
        logger.info(f"Deleted role+location entry {entry_id}: {role_name} @ {location}")
        
        return jsonify({
            "message": "Entry deleted",
            "deleted_id": entry_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting role location entry: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/role-location-queue/bulk-approve', methods=['POST'])
@require_pm_admin
def bulk_approve_role_location_entries():
    """Bulk approve pending role+location queue entries."""
    try:
        from app.models.role_location_queue import RoleLocationQueue
        
        data = request.get_json() or {}
        entry_ids = data.get('entry_ids', [])
        
        if not entry_ids:
            # If no specific IDs, approve all pending
            entries = RoleLocationQueue.query.filter_by(queue_status='pending').all()
        else:
            entries = RoleLocationQueue.query.filter(
                RoleLocationQueue.id.in_(entry_ids),
                RoleLocationQueue.queue_status == 'pending'
            ).all()
        
        approved_count = 0
        for entry in entries:
            entry.queue_status = 'approved'
            entry.updated_at = datetime.utcnow()
            approved_count += 1
        
        db.session.commit()
        
        logger.info(f"Bulk approved {approved_count} role+location entries")
        
        return jsonify({
            "message": f"Approved {approved_count} entries",
            "approved_count": approved_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error bulk approving role location entries: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


# ============================================================================
# SESSION JOB LOGS ENDPOINTS
# ============================================================================

@scraper_monitoring_bp.route('/sessions/<session_id>/jobs', methods=['GET'])
@require_pm_admin
def get_session_job_logs(session_id: str):
    """
    Get all job logs for a session with detailed import status.
    
    Query params:
    - status: Filter by status (imported, skipped, error, all)
    - skip_reason: Filter by specific skip reason
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - include_raw_data: Include raw job data (default: false)
    - include_duplicate: Include duplicate job details (default: true)
    
    Response:
    {
        "session_id": "uuid",
        "session_info": {...},
        "summary": {
            "total": 100,
            "imported": 10,
            "skipped": 88,
            "error": 2,
            "skip_reasons": {...}
        },
        "jobs": [...],
        "pagination": {...}
    }
    """
    try:
        from uuid import UUID
        from app.models.session_job_log import SessionJobLog
        
        # Validate session exists
        session = ScrapeSession.query.filter_by(session_id=UUID(session_id)).first()
        if not session:
            return jsonify({
                "error": "Not Found",
                "message": f"Session {session_id} not found"
            }), 404
        
        # Parse query params
        status_filter = request.args.get('status', 'all')
        skip_reason_filter = request.args.get('skip_reason')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        include_raw_data = request.args.get('include_raw_data', 'false').lower() == 'true'
        include_duplicate = request.args.get('include_duplicate', 'true').lower() == 'true'
        
        # Build query
        query = SessionJobLog.query.filter_by(session_id=UUID(session_id))
        
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        
        if skip_reason_filter:
            query = query.filter_by(skip_reason=skip_reason_filter)
        
        # Order by job index
        query = query.order_by(SessionJobLog.job_index)
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get summary stats
        summary = SessionJobLog.get_session_summary(UUID(session_id))
        
        # Format response
        jobs = [
            log.to_dict(include_raw_data=include_raw_data, include_duplicate=include_duplicate)
            for log in pagination.items
        ]
        
        # Get session info
        session_info = {
            "session_id": str(session.session_id),
            "role_name": session.role_name,
            "location": session.location,
            "status": session.status,
            "scraper_name": session.scraper_name,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "duration_seconds": session.duration_seconds,
            "platforms_total": session.platforms_total,
            "platforms_completed": session.platforms_completed,
            "platforms_failed": session.platforms_failed,
            "jobs_found": session.jobs_found,
            "jobs_imported": session.jobs_imported,
            "jobs_skipped": session.jobs_skipped
        }
        
        return jsonify({
            "session_id": session_id,
            "session_info": session_info,
            "summary": summary,
            "jobs": jobs,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid session ID: {e}"
        }), 400
    except Exception as e:
        logger.error(f"Error getting session job logs: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/sessions/<session_id>/jobs/<int:job_log_id>', methods=['GET'])
@require_pm_admin
def get_session_job_log_detail(session_id: str, job_log_id: int):
    """
    Get detailed information for a single job log entry.
    
    Includes:
    - Raw job data as received from scraper
    - Full duplicate job details if applicable
    - Comparison between incoming and existing job
    
    Response:
    {
        "job_log": {...},
        "raw_job_data": {...},
        "duplicate_job": {...},
        "comparison": {...}  // Side-by-side comparison if duplicate
    }
    """
    try:
        from uuid import UUID
        from app.models.session_job_log import SessionJobLog
        
        # Get job log
        job_log = SessionJobLog.query.filter_by(
            id=job_log_id,
            session_id=UUID(session_id)
        ).first()
        
        if not job_log:
            return jsonify({
                "error": "Not Found",
                "message": f"Job log {job_log_id} not found in session {session_id}"
            }), 404
        
        # Build response
        response = {
            "job_log": job_log.to_dict(include_raw_data=True, include_duplicate=True),
            "raw_job_data": job_log.raw_job_data
        }
        
        # Add comparison if this was a duplicate skip
        if job_log.duplicate_job_id and job_log.duplicate_job:
            dup = job_log.duplicate_job
            incoming = job_log.raw_job_data
            
            response["duplicate_job"] = {
                "id": dup.id,
                "title": dup.title,
                "company": dup.company,
                "location": dup.location,
                "description": dup.description,
                "platform": dup.platform,
                "external_job_id": dup.external_job_id,
                "job_url": dup.job_url,
                "posted_date": dup.posted_date.isoformat() if dup.posted_date else None,
                "created_at": dup.created_at.isoformat() if dup.created_at else None,
                "skills": dup.skills,
                "salary_range": dup.salary_range,
                "experience_required": dup.experience_required,
                "is_remote": dup.is_remote
            }
            
            # Create side-by-side comparison
            response["comparison"] = {
                "title": {
                    "incoming": incoming.get("title"),
                    "existing": dup.title,
                    "match": (incoming.get("title") or "").lower().strip() == (dup.title or "").lower().strip()
                },
                "company": {
                    "incoming": incoming.get("company"),
                    "existing": dup.company,
                    "match": (incoming.get("company") or "").lower().strip() == (dup.company or "").lower().strip()
                },
                "location": {
                    "incoming": incoming.get("location"),
                    "existing": dup.location,
                    "match": (incoming.get("location") or "").lower().strip() == (dup.location or "").lower().strip()
                },
                "platform": {
                    "incoming": incoming.get("platform"),
                    "existing": dup.platform,
                    "match": incoming.get("platform") == dup.platform
                },
                "external_id": {
                    "incoming": incoming.get("jobId") or incoming.get("job_id") or incoming.get("external_job_id"),
                    "existing": dup.external_job_id,
                    "match": str(incoming.get("jobId") or incoming.get("job_id") or incoming.get("external_job_id") or "") == str(dup.external_job_id or "")
                },
                "description_preview": {
                    "incoming": (incoming.get("description") or "")[:200],
                    "existing": (dup.description or "")[:200],
                    "match": (incoming.get("description") or "")[:100].lower().strip() == (dup.description or "")[:100].lower().strip()
                }
            }
        
        # If imported, include the created job details
        if job_log.imported_job_id and job_log.imported_job:
            imp = job_log.imported_job
            response["imported_job"] = {
                "id": imp.id,
                "title": imp.title,
                "company": imp.company,
                "location": imp.location,
                "platform": imp.platform,
                "external_job_id": imp.external_job_id,
                "job_url": imp.job_url,
                "created_at": imp.created_at.isoformat() if imp.created_at else None
            }
        
        return jsonify(response), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid session ID: {e}"
        }), 400
    except Exception as e:
        logger.error(f"Error getting job log detail: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_monitoring_bp.route('/sessions/<session_id>/summary', methods=['GET'])
@require_pm_admin
def get_session_summary(session_id: str):
    """
    Get a summary of job import results for a session.
    
    Response:
    {
        "session_info": {...},
        "summary": {...},
        "platform_breakdown": [...],
        "skip_reasons_chart": [...]
    }
    """
    try:
        from uuid import UUID
        from app.models.session_job_log import SessionJobLog
        
        # Validate session exists
        session = ScrapeSession.query.filter_by(session_id=UUID(session_id)).first()
        if not session:
            return jsonify({
                "error": "Not Found",
                "message": f"Session {session_id} not found"
            }), 404
        
        # Get summary
        summary = SessionJobLog.get_session_summary(UUID(session_id))
        
        # Get platform statuses
        platform_statuses = SessionPlatformStatus.query.filter_by(
            session_id=UUID(session_id)
        ).all()
        
        platform_breakdown = []
        for ps in platform_statuses:
            platform_breakdown.append({
                "platform_name": ps.platform_name,
                "status": ps.status,
                "jobs_found": ps.jobs_found,
                "jobs_imported": ps.jobs_imported,
                "jobs_skipped": ps.jobs_skipped,
                "error_message": ps.error_message,
                "completed_at": ps.completed_at.isoformat() if ps.completed_at else None
            })
        
        # Format skip reasons for chart
        skip_reasons_chart = [
            {"reason": "Platform + ID Duplicate", "count": summary["skip_reasons"]["duplicate_platform_id"]},
            {"reason": "Title + Company + Location", "count": summary["skip_reasons"]["duplicate_title_company_location"]},
            {"reason": "Title + Company + Description", "count": summary["skip_reasons"]["duplicate_title_company_description"]},
            {"reason": "Missing Required Fields", "count": summary["skip_reasons"]["missing_required"]},
            {"reason": "Error During Import", "count": summary["skip_reasons"]["error"]}
        ]
        
        # Session info
        session_info = {
            "session_id": str(session.session_id),
            "role_name": session.role_name,
            "location": session.location,
            "status": session.status,
            "scraper_name": session.scraper_name,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "duration_seconds": session.duration_seconds
        }
        
        return jsonify({
            "session_info": session_info,
            "summary": summary,
            "platform_breakdown": platform_breakdown,
            "skip_reasons_chart": skip_reasons_chart
        }), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid session ID: {e}"
        }), 400
    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500
