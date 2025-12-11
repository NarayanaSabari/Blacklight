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
        
        # Pending queue count (roles waiting to be scraped)
        pending_queue = db.session.scalar(
            db.select(func.count(GlobalRole.id))
            .where(GlobalRole.queue_status == 'pending')
        ) or 0
        
        # Jobs imported in time period
        jobs_imported = db.session.scalar(
            db.select(func.count(JobPosting.id))
            .where(JobPosting.imported_at >= since)
        ) or 0
        
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
            "jobs_found": s.jobs_found,
            "jobs_imported": s.jobs_imported,
            "jobs_skipped": s.jobs_skipped,
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
        
        return jsonify({
            "api_keys": [{
                "id": k.id,
                "name": k.name,
                "description": k.description,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "total_requests": k.total_requests,
                "total_jobs_imported": k.total_jobs_imported,
                "rate_limit_per_minute": k.rate_limit_per_minute,
                "created_at": k.created_at.isoformat(),
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
        raw_key, api_key = ScraperApiKey.create_new_key(
            name=data['name'],
            description=data.get('description'),
            created_by=getattr(g, 'pm_admin_id', None),
            rate_limit_per_minute=data.get('rate_limit_per_minute', 60)
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            "id": api_key.id,
            "name": api_key.name,
            "api_key": raw_key,  # Only returned on create
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
