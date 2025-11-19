"""
Job Posting Routes
API endpoints for job posting management and viewing.
"""
import logging
from flask import Blueprint, jsonify, request, g
from sqlalchemy import select, or_, func, and_

from app import db
from app.models.job_posting import JobPosting
from app.middleware.portal_auth import require_portal_auth
from app.middleware.tenant_context import with_tenant_context
from app.middleware.portal_auth import require_permission

logger = logging.getLogger(__name__)

job_posting_bp = Blueprint('job_postings', __name__, url_prefix='/api/job-postings')


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses"""
    response = {
        'error': 'Error',
        'message': message,
        'status': status
    }
    if details:
        response['details'] = details
    return jsonify(response), status


@job_posting_bp.route('/<int:job_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_job_posting(job_id: int):
    """
    Get detailed information about a specific job posting.
    
    GET /api/job-postings/:id
    
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        # Fetch job posting
        job = db.session.get(JobPosting, job_id)
        
        if not job:
            return error_response(f"Job posting {job_id} not found", 404)
        
        # Check if job belongs to tenant (if tenant_id field exists)
        if hasattr(job, 'tenant_id') and job.tenant_id and job.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        return jsonify(job.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error fetching job posting {job_id}: {str(e)}")
        return error_response("Failed to fetch job posting", 500)


@job_posting_bp.route('', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def list_job_postings():
    """
    List all job postings with optional filters and pagination.
    
    GET /api/job-postings
    
    Query params:
    - page: int (default 1)
    - per_page: int (default 20, max 100)
    - status: string (active, inactive, closed)
    - search: string (search in title, company, location, description)
    - location: string (filter by location)
    - is_remote: boolean
    - sort_by: string (posted_date, title, company, salary_min)
    - sort_order: string (asc, desc)
    
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        search = request.args.get('search')
        location = request.args.get('location')
        is_remote = request.args.get('is_remote')
        sort_by = request.args.get('sort_by', 'posted_date')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = select(JobPosting)
        
        # Apply filters
        if status:
            query = query.where(JobPosting.status == status)
        
        if location:
            query = query.where(JobPosting.location.ilike(f'%{location}%'))
        
        if is_remote is not None:
            is_remote_bool = is_remote.lower() in ('true', '1', 'yes')
            query = query.where(JobPosting.is_remote == is_remote_bool)
        
        if search:
            search_filter = or_(
                JobPosting.title.ilike(f'%{search}%'),
                JobPosting.company.ilike(f'%{search}%'),
                JobPosting.location.ilike(f'%{search}%'),
                JobPosting.description.ilike(f'%{search}%')
            )
            query = query.where(search_filter)
        
        # Apply sorting
        valid_sort_fields = {
            'posted_date': JobPosting.posted_date,
            'title': JobPosting.title,
            'company': JobPosting.company,
            'salary_min': JobPosting.salary_min,
            'created_at': JobPosting.created_at
        }
        
        sort_field = valid_sort_fields.get(sort_by, JobPosting.posted_date)
        if sort_order.lower() == 'desc':
            query = query.order_by(sort_field.desc().nullslast())
        else:
            query = query.order_by(sort_field.asc().nullslast())
        
        # Get total count
        count_query = select(func.count()).select_from(JobPosting)
        if status:
            count_query = count_query.where(JobPosting.status == status)
        if location:
            count_query = count_query.where(JobPosting.location.ilike(f'%{location}%'))
        if is_remote is not None:
            count_query = count_query.where(JobPosting.is_remote == is_remote_bool)
        if search:
            count_query = count_query.where(search_filter)
        
        total = db.session.scalar(count_query)
        
        # Execute paginated query
        jobs = db.session.scalars(
            query.offset((page - 1) * per_page).limit(per_page)
        ).all()
        
        return jsonify({
            'jobs': [job.to_dict() for job in jobs],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 0
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing job postings: {str(e)}")
        return error_response("Failed to list job postings", 500)


@job_posting_bp.route('/search', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def search_job_postings():
    """
    Search job postings by query string.
    
    GET /api/job-postings/search?q=python developer
    
    Permissions: candidates.view
    """
    try:
        query_string = request.args.get('q', '').strip()
        
        if not query_string:
            return jsonify([]), 200
        
        # Search in multiple fields
        search_filter = or_(
            JobPosting.title.ilike(f'%{query_string}%'),
            JobPosting.company.ilike(f'%{query_string}%'),
            JobPosting.location.ilike(f'%{query_string}%'),
            JobPosting.description.ilike(f'%{query_string}%')
        )
        
        query = (
            select(JobPosting)
            .where(and_(search_filter, JobPosting.status == 'active'))
            .order_by(JobPosting.posted_date.desc().nullslast())
            .limit(50)
        )
        
        jobs = db.session.scalars(query).all()
        
        return jsonify([job.to_dict() for job in jobs]), 200
        
    except Exception as e:
        logger.error(f"Error searching job postings: {str(e)}")
        return error_response("Failed to search job postings", 500)


@job_posting_bp.route('/statistics', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_job_statistics():
    """
    Get statistics about job postings.
    
    GET /api/job-postings/statistics
    
    Permissions: candidates.view
    """
    try:
        # Get counts by status
        total_jobs = db.session.scalar(select(func.count(JobPosting.id)))
        
        active_jobs = db.session.scalar(
            select(func.count(JobPosting.id))
            .where(JobPosting.status == 'active')
        )
        
        remote_jobs = db.session.scalar(
            select(func.count(JobPosting.id))
            .where(JobPosting.is_remote == True)
        )
        
        # Get unique companies and locations
        unique_companies = db.session.scalar(
            select(func.count(func.distinct(JobPosting.company)))
        )
        
        unique_locations = db.session.scalar(
            select(func.count(func.distinct(JobPosting.location)))
        )
        
        return jsonify({
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'remote_jobs': remote_jobs,
            'unique_companies': unique_companies,
            'unique_locations': unique_locations
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job statistics: {str(e)}")
        return error_response("Failed to get job statistics", 500)
