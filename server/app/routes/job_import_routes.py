"""
Job Import Routes
API endpoints for importing job postings from external platforms.
Only accessible by PM_ADMIN (product owner).
"""
import os
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from pathlib import Path
import logging

from app.middleware.pm_admin import require_pm_admin
from app.services.job_import_service import JobImportService
from config.settings import settings

logger = logging.getLogger(__name__)

job_import_bp = Blueprint('job_import', __name__, url_prefix='/api/jobs')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@job_import_bp.route('/import', methods=['POST'])
@require_pm_admin
def import_jobs():
    """
    Import jobs from uploaded JSON file.
    
    Only accessible by PM_ADMIN.
    
    Request:
        - file: JSON file (multipart/form-data)
        - platform: Platform name (indeed, dice, techfetch, glassdoor, monster)
        - update_existing: Whether to update existing jobs (optional, default: true)
    
    Response:
        {
            "success": true,
            "batch_id": "indeed_20251116_123456",
            "statistics": {
                "total_jobs": 100,
                "new_jobs": 85,
                "updated_jobs": 10,
                "failed_jobs": 5,
                "duplicates_removed": 3
            }
        }
    """
    try:
        # Validate file upload
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided',
                'message': 'Please upload a JSON file'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'error': 'No file selected',
                'message': 'Please select a file to upload'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Invalid file type',
                'message': 'Only JSON files are allowed'
            }), 400
        
        # Get platform from form data
        platform = request.form.get('platform', '').lower()
        valid_platforms = ['indeed', 'dice', 'techfetch', 'glassdoor', 'monster']
        
        if platform not in valid_platforms:
            return jsonify({
                'error': 'Invalid platform',
                'message': f'Platform must be one of: {", ".join(valid_platforms)}'
            }), 400
        
        # Get update_existing flag (default: true)
        update_existing = request.form.get('update_existing', 'true').lower() == 'true'
        
        # Create temporary upload directory
        upload_dir = Path(settings.storage_local_path) / 'temp' / 'jobs'
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_file_path = upload_dir / filename
        file.save(str(temp_file_path))
        
        logger.info(f"PM_ADMIN {g.user_id} uploaded job file: {filename} for platform: {platform}")
        
        # Import jobs using service
        service = JobImportService()
        batch = service.import_from_json(
            file_path=str(temp_file_path),
            platform=platform,
            update_existing=update_existing
        )
        
        # Clean up temp file
        try:
            temp_file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")
        
        # Return success response
        return jsonify({
            'success': True,
            'message': f'Successfully imported jobs from {platform}',
            'batch_id': batch.batch_id,
            'statistics': {
                'total_jobs': batch.total_jobs,
                'new_jobs': batch.new_jobs,
                'updated_jobs': batch.updated_jobs,
                'failed_jobs': batch.failed_jobs,
                'success_rate': batch.success_rate,
                'duration_seconds': batch.duration_seconds
            },
            'batch': batch.to_dict()
        }), 200
        
    except FileNotFoundError as e:
        logger.error(f"File not found during import: {e}")
        return jsonify({
            'error': 'File not found',
            'message': str(e)
        }), 404
        
    except ValueError as e:
        logger.error(f"Validation error during import: {e}")
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Job import failed: {e}", exc_info=True)
        return jsonify({
            'error': 'Import failed',
            'message': 'An error occurred while importing jobs. Please check the file format and try again.',
            'details': str(e) if settings.DEBUG else None
        }), 500


@job_import_bp.route('/batches', methods=['GET'])
@require_pm_admin
def get_import_batches():
    """
    Get list of job import batches with statistics.
    
    Only accessible by PM_ADMIN.
    
    Query Parameters:
        - platform: Filter by platform (optional)
        - status: Filter by status (optional)
        - limit: Number of results (default: 50, max: 200)
        - offset: Pagination offset (default: 0)
    
    Response:
        {
            "batches": [...],
            "total": 100,
            "limit": 50,
            "offset": 0
        }
    """
    try:
        from app.models.job_import_batch import JobImportBatch
        from sqlalchemy import select, func
        from app import db
        
        # Get query parameters
        platform = request.args.get('platform')
        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = select(JobImportBatch).order_by(JobImportBatch.started_at.desc())
        
        if platform:
            query = query.where(JobImportBatch.platform == platform.lower())
        
        if status:
            query = query.where(JobImportBatch.import_status == status.upper())
        
        # Get total count
        count_query = select(func.count()).select_from(JobImportBatch)
        if platform:
            count_query = count_query.where(JobImportBatch.platform == platform.lower())
        if status:
            count_query = count_query.where(JobImportBatch.import_status == status.upper())
        
        total = db.session.scalar(count_query)
        
        # Get paginated results
        query = query.limit(limit).offset(offset)
        batches = db.session.scalars(query).all()
        
        return jsonify({
            'batches': [batch.to_dict() for batch in batches],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch import batches: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch batches',
            'message': str(e) if settings.DEBUG else 'An error occurred'
        }), 500


@job_import_bp.route('/batches/<batch_id>', methods=['GET'])
@require_pm_admin
def get_batch_details(batch_id: str):
    """
    Get detailed information about a specific import batch.
    
    Only accessible by PM_ADMIN.
    
    Response:
        {
            "batch": {...},
            "error_log": [...]
        }
    """
    try:
        from app.models.job_import_batch import JobImportBatch
        from sqlalchemy import select
        from app import db
        
        batch = db.session.scalar(
            select(JobImportBatch).where(JobImportBatch.batch_id == batch_id)
        )
        
        if not batch:
            return jsonify({
                'error': 'Batch not found',
                'message': f'No import batch found with ID: {batch_id}'
            }), 404
        
        return jsonify({
            'batch': batch.to_dict(),
            'error_log': batch.error_log or []
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch batch details: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch batch details',
            'message': str(e) if settings.DEBUG else 'An error occurred'
        }), 500


@job_import_bp.route('/statistics', methods=['GET'])
@require_pm_admin
def get_import_statistics():
    """
    Get detailed job import statistics with platform-level breakdown.
    
    Only accessible by PM_ADMIN.
    
    Query params:
        limit: Number of recent imports to return (default: 10, max: 50)
        include_platforms: Include platform-level details (default: true)
    
    Response:
        {
            "total_jobs": 5000,
            "jobs_by_platform": {...},
            "total_batches": 50,
            "recent_imports": [...],
            "summary": {
                "total_sessions": 100,
                "successful_sessions": 95,
                "failed_sessions": 5,
                "success_rate": 95.0,
                "total_jobs_imported": 5000,
                "avg_jobs_per_session": 50,
                "avg_duration_seconds": 120
            },
            "platform_health": {...}
        }
    """
    try:
        from app.models.job_posting import JobPosting
        from app.models.job_import_batch import JobImportBatch
        from app.models.scrape_session import ScrapeSession
        from app.models.session_platform_status import SessionPlatformStatus
        from sqlalchemy import select, func, case
        from app import db
        
        limit = min(int(request.args.get('limit', 10)), 50)
        include_platforms = request.args.get('include_platforms', 'true').lower() == 'true'
        
        # Total jobs
        total_jobs = db.session.scalar(select(func.count()).select_from(JobPosting)) or 0
        
        # Jobs by platform
        platform_stats = db.session.execute(
            select(JobPosting.platform, func.count(JobPosting.id).label('count'))
            .group_by(JobPosting.platform)
        ).all()
        
        jobs_by_platform = {stat.platform or 'unknown': stat.count for stat in platform_stats}
        
        # Total batches (from JobImportBatch)
        total_batches = db.session.scalar(select(func.count()).select_from(JobImportBatch)) or 0
        
        # Session-level aggregations
        session_stats = db.session.execute(
            select(
                func.count(ScrapeSession.id).label('total'),
                func.sum(case((ScrapeSession.status == 'completed', 1), else_=0)).label('completed'),
                func.sum(case((ScrapeSession.status == 'failed', 1), else_=0)).label('failed'),
                func.sum(case((ScrapeSession.status == 'in_progress', 1), else_=0)).label('in_progress'),
                func.sum(case((ScrapeSession.status == 'timeout', 1), else_=0)).label('timeout'),
                func.sum(ScrapeSession.jobs_imported).label('total_imported'),
                func.sum(ScrapeSession.jobs_skipped).label('total_skipped'),
                func.sum(ScrapeSession.jobs_found).label('total_found'),
                func.avg(ScrapeSession.duration_seconds).label('avg_duration')
            )
        ).first()
        
        total_sessions = session_stats.total or 0
        total_batches = total_batches + total_sessions
        
        # Calculate success rate
        completed_sessions = session_stats.completed or 0
        failed_sessions = (session_stats.failed or 0) + (session_stats.timeout or 0)
        success_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0
        
        # Platform health - aggregate per platform performance
        platform_health_query = db.session.execute(
            select(
                SessionPlatformStatus.platform_name,
                func.count(SessionPlatformStatus.id).label('total_attempts'),
                func.sum(case((SessionPlatformStatus.status == 'completed', 1), else_=0)).label('successful'),
                func.sum(case((SessionPlatformStatus.status == 'failed', 1), else_=0)).label('failed'),
                func.sum(SessionPlatformStatus.jobs_imported).label('jobs_imported'),
                func.sum(SessionPlatformStatus.jobs_skipped).label('jobs_skipped'),
                func.avg(SessionPlatformStatus.duration_seconds).label('avg_duration')
            )
            .group_by(SessionPlatformStatus.platform_name)
        ).all()
        
        platform_health = {}
        for ph in platform_health_query:
            total_attempts = ph.total_attempts or 0
            successful = ph.successful or 0
            platform_health[ph.platform_name] = {
                'total_attempts': total_attempts,
                'successful': successful,
                'failed': ph.failed or 0,
                'success_rate': round((successful / total_attempts * 100), 1) if total_attempts > 0 else 0,
                'jobs_imported': ph.jobs_imported or 0,
                'jobs_skipped': ph.jobs_skipped or 0,
                'avg_duration_seconds': round(ph.avg_duration or 0, 1)
            }
        
        # Recent imports with detailed platform breakdown
        recent_imports = []
        
        # From JobImportBatch (legacy/manual imports)
        recent_batches = db.session.scalars(
            select(JobImportBatch)
            .order_by(JobImportBatch.started_at.desc())
            .limit(5)
        ).all()
        
        for batch in recent_batches:
            recent_imports.append({
                **batch.to_dict(),
                'source': 'manual_import',
                'platforms': []
            })
        
        # From ScrapeSession (scraper imports) with platform details
        recent_sessions = db.session.scalars(
            select(ScrapeSession)
            .order_by(ScrapeSession.started_at.desc())
            .limit(limit)
        ).all()
        
        for session in recent_sessions:
            session_data = {
                'batch_id': str(session.session_id),
                'source': 'scraper',
                'import_status': session.status,
                'role_name': session.role_name,
                'scraper_name': session.scraper_name,
                
                # Job counts
                'total_jobs': session.jobs_found or 0,
                'new_jobs': session.jobs_imported or 0,
                'updated_jobs': 0,
                'skipped_jobs': session.jobs_skipped or 0,
                'failed_jobs': 0,  # Will be calculated from platforms
                
                # Platform summary
                'platforms_total': session.platforms_total or 0,
                'platforms_completed': session.platforms_completed or 0,
                'platforms_failed': session.platforms_failed or 0,
                'platforms_pending': max(0, (session.platforms_total or 0) - (session.platforms_completed or 0)),
                
                # Timing
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'completed_at': session.completed_at.isoformat() if session.completed_at else None,
                'duration_seconds': session.duration_seconds,
                'duration_formatted': format_duration(session.duration_seconds) if session.duration_seconds else None,
                
                # Error info
                'error_message': session.error_message,
                'session_notes': session.session_notes,
                
                # Platform breakdown
                'platforms': []
            }
            
            # Include platform-level details if requested
            if include_platforms:
                platform_statuses = db.session.scalars(
                    select(SessionPlatformStatus)
                    .where(SessionPlatformStatus.session_id == session.session_id)
                    .order_by(SessionPlatformStatus.platform_name)
                ).all()
                
                total_failed_jobs = 0
                for ps in platform_statuses:
                    platform_data = {
                        'platform_name': ps.platform_name,
                        'status': ps.status,
                        'status_label': get_status_label(ps.status),
                        'jobs_found': ps.jobs_found or 0,
                        'jobs_imported': ps.jobs_imported or 0,
                        'jobs_skipped': ps.jobs_skipped or 0,
                        'error_message': ps.error_message,
                        'started_at': ps.started_at.isoformat() if ps.started_at else None,
                        'completed_at': ps.completed_at.isoformat() if ps.completed_at else None,
                        'duration_seconds': ps.duration_seconds,
                        'duration_formatted': format_duration(ps.duration_seconds) if ps.duration_seconds else None
                    }
                    session_data['platforms'].append(platform_data)
                    
                    # Count failed jobs from failed platforms
                    if ps.status == 'failed':
                        total_failed_jobs += ps.jobs_found or 0
                
                session_data['failed_jobs'] = total_failed_jobs
            
            recent_imports.append(session_data)
        
        # Sort by started_at descending
        recent_imports.sort(key=lambda x: x.get('started_at') or '', reverse=True)
        recent_imports = recent_imports[:limit]
        
        return jsonify({
            'total_jobs': total_jobs,
            'jobs_by_platform': jobs_by_platform,
            'total_batches': total_batches,
            'recent_imports': recent_imports,
            'summary': {
                'total_sessions': total_sessions,
                'successful_sessions': completed_sessions,
                'failed_sessions': failed_sessions,
                'in_progress_sessions': session_stats.in_progress or 0,
                'timeout_sessions': session_stats.timeout or 0,
                'success_rate': success_rate,
                'total_jobs_imported': session_stats.total_imported or 0,
                'total_jobs_skipped': session_stats.total_skipped or 0,
                'total_jobs_found': session_stats.total_found or 0,
                'avg_jobs_per_session': round((session_stats.total_imported or 0) / total_sessions, 1) if total_sessions > 0 else 0,
                'avg_duration_seconds': round(session_stats.avg_duration or 0, 1)
            },
            'platform_health': platform_health
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch import statistics: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch statistics',
            'message': str(e) if settings.DEBUG else 'An error occurred'
        }), 500


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string."""
    if not seconds:
        return None
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def get_status_label(status: str) -> str:
    """Get human-readable status label."""
    labels = {
        'pending': 'Pending',
        'in_progress': 'In Progress',
        'completed': 'Completed',
        'failed': 'Failed',
        'skipped': 'Skipped',
        'timeout': 'Timed Out'
    }
    return labels.get(status, status.title())
