"""
Scraper API Routes

External API endpoints for job scrapers to:
1. Fetch next role from queue (GET /api/scraper/queue/next-role)
2. Post jobs for a role (POST /api/scraper/queue/jobs)
3. Report session failure (POST /api/scraper/queue/fail)

Authentication: X-Scraper-API-Key header
"""
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g

from app import db
from app.models.scraper_api_key import ScraperApiKey
from app.services.scrape_queue_service import ScrapeQueueService

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
    Get next role from the scrape queue.
    
    Response:
    {
        "session_id": "uuid",
        "role": {
            "id": 1,
            "name": "Python Developer",
            "aliases": ["Python Dev", "Python Engineer"],
            "category": "Engineering",
            "candidate_count": 50
        }
    }
    
    Returns 204 No Content if queue is empty.
    """
    try:
        result = ScrapeQueueService.get_next_role(g.scraper_key)
        
        if not result:
            return '', 204  # No content - queue empty
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting next role: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@scraper_bp.route('/queue/jobs', methods=['POST'])
@require_scraper_auth
def post_jobs():
    """
    Post jobs for a role and complete the scrape session.
    
    Request body:
    {
        "session_id": "uuid",
        "jobs": [
            {
                "job_id": "external-123",
                "platform": "monster",
                "title": "Senior Python Developer",
                "company": "TechCorp",
                "location": "San Francisco, CA",
                "description": "Full description...",
                "requirements": "5+ years...",
                "salary": "$150K - $180K",
                "job_url": "https://...",
                "posted_date": "2025-12-01",
                "skills": ["Python", "AWS", "PostgreSQL"]
            }
        ]
    }
    
    Response:
    {
        "session_id": "uuid",
        "role_name": "Python Developer",
        "jobs_found": 47,
        "jobs_imported": 42,
        "jobs_skipped": 5,
        "duration_seconds": 125,
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
    jobs = data.get('jobs', [])
    
    if not session_id:
        return jsonify({
            "error": "Bad Request",
            "message": "session_id required"
        }), 400
    
    try:
        result = ScrapeQueueService.complete_session(
            session_id=session_id,
            jobs_data=jobs,
            scraper_key=g.scraper_key
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
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
