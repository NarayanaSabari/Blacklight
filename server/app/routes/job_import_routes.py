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
        
        logger.info(f"PM_ADMIN {g.user.id} uploaded job file: {filename} for platform: {platform}")
        
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
    Get overall job import statistics.
    
    Only accessible by PM_ADMIN.
    
    Response:
        {
            "total_jobs": 5000,
            "jobs_by_platform": {...},
            "total_batches": 50,
            "recent_imports": [...]
        }
    """
    try:
        from app.models.job_posting import JobPosting
        from app.models.job_import_batch import JobImportBatch
        from sqlalchemy import select, func
        from app import db
        
        # Total jobs
        total_jobs = db.session.scalar(select(func.count()).select_from(JobPosting))
        
        # Jobs by platform
        platform_stats = db.session.execute(
            select(JobPosting.platform, func.count(JobPosting.id).label('count'))
            .group_by(JobPosting.platform)
        ).all()
        
        jobs_by_platform = {stat.platform: stat.count for stat in platform_stats}
        
        # Total batches
        total_batches = db.session.scalar(select(func.count()).select_from(JobImportBatch))
        
        # Recent imports (last 10)
        recent_batches = db.session.scalars(
            select(JobImportBatch)
            .order_by(JobImportBatch.started_at.desc())
            .limit(10)
        ).all()
        
        return jsonify({
            'total_jobs': total_jobs,
            'jobs_by_platform': jobs_by_platform,
            'total_batches': total_batches,
            'recent_imports': [batch.to_dict() for batch in recent_batches]
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch import statistics: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch statistics',
            'message': str(e) if settings.DEBUG else 'An error occurred'
        }), 500
