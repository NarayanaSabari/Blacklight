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
            "active_api_keys": active_keys
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
            "statuses": ["ACTIVE", "EXPIRED"]
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
        
        return jsonify({
            "jobs": [job.to_dict(include_description=False) for job in jobs],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total > 0 else 0,
            "filters": {
                "platforms": list(platforms),
                "statuses": list(statuses)
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
