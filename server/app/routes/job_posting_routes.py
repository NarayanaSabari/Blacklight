"""
Job Posting Routes
API endpoints for job posting management and viewing.
Includes both scraped jobs (global) and email-sourced jobs (tenant-specific).
"""
import logging
from flask import Blueprint, jsonify, request, g
from sqlalchemy import select, or_, func, and_

from app import db
from app.models.job_posting import JobPosting
from app.models.portal_user import PortalUser
from app.models.processed_email import ProcessedEmail
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


def _add_sourced_by_info(job_dict: dict, job: JobPosting) -> dict:
    """Add sourced_by user info to job dict if email-sourced."""
    if job.is_email_sourced and job.sourced_by_user_id:
        user = db.session.get(PortalUser, job.sourced_by_user_id)
        if user:
            job_dict["sourced_by"] = {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
            }
    return job_dict


@job_posting_bp.route('/<int:job_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_job_posting(job_id: int):
    """
    Get detailed information about a specific job posting.
    
    GET /api/job-postings/:id
    
    For email-sourced jobs, only the source tenant can access.
    For scraped jobs, all tenants can access.
    
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        # Fetch job posting
        job = db.session.get(JobPosting, job_id)
        
        if not job:
            return error_response(f"Job posting {job_id} not found", 404)
        
        # Email-sourced jobs are tenant-specific
        if job.is_email_sourced and job.source_tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        job_dict = job.to_dict()
        job_dict = _add_sourced_by_info(job_dict, job)
        
        return jsonify(job_dict), 200
        
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
    - sort_by: string (posted_date, title, company, salary_min, created_at)
    - sort_order: string (asc, desc)
    - source: string (all, email, scraped) - NEW: filter by job source
    - platform: string (filter by specific platform: indeed, dice, email, etc.)
    - sourced_by: int (filter email jobs by user ID who sourced them)
    
    Returns:
    - Scraped jobs (global) visible to all tenants
    - Email-sourced jobs only visible to their source tenant
    
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
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # New filters for unified job view
        source = request.args.get('source', 'all')  # all, email, scraped
        platform = request.args.get('platform')  # indeed, dice, email, etc.
        sourced_by = request.args.get('sourced_by', type=int)
        
        # Build base query with tenant visibility rules:
        # - Scraped jobs (is_email_sourced=False): visible to all
        # - Email jobs (is_email_sourced=True): only visible to source_tenant_id
        if source == 'email':
            # Only email-sourced jobs for this tenant
            query = select(JobPosting).where(
                JobPosting.is_email_sourced == True,
                JobPosting.source_tenant_id == tenant_id
            )
        elif source == 'scraped':
            # Only scraped jobs (global)
            query = select(JobPosting).where(
                JobPosting.is_email_sourced == False
            )
        else:
            # All jobs: scraped (global) + email (tenant-specific)
            query = select(JobPosting).where(
                or_(
                    JobPosting.is_email_sourced == False,
                    and_(
                        JobPosting.is_email_sourced == True,
                        JobPosting.source_tenant_id == tenant_id
                    )
                )
            )
        
        # Apply filters
        if status:
            query = query.where(JobPosting.status == status)
        
        if platform:
            query = query.where(JobPosting.platform == platform)
        
        if sourced_by:
            query = query.where(JobPosting.sourced_by_user_id == sourced_by)
        
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
                JobPosting.description.ilike(f'%{search}%'),
                func.array_to_string(JobPosting.skills, ',').ilike(f'%{search}%')
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
        
        sort_field = valid_sort_fields.get(sort_by, JobPosting.created_at)
        if sort_order.lower() == 'desc':
            query = query.order_by(sort_field.desc().nullslast())
        else:
            query = query.order_by(sort_field.asc().nullslast())
        
        # Get total count with same filters
        count_query = select(func.count(JobPosting.id))
        
        # Apply same visibility rules for count
        if source == 'email':
            count_query = count_query.where(
                JobPosting.is_email_sourced == True,
                JobPosting.source_tenant_id == tenant_id
            )
        elif source == 'scraped':
            count_query = count_query.where(JobPosting.is_email_sourced == False)
        else:
            count_query = count_query.where(
                or_(
                    JobPosting.is_email_sourced == False,
                    and_(
                        JobPosting.is_email_sourced == True,
                        JobPosting.source_tenant_id == tenant_id
                    )
                )
            )
        
        if status:
            count_query = count_query.where(JobPosting.status == status)
        if platform:
            count_query = count_query.where(JobPosting.platform == platform)
        if sourced_by:
            count_query = count_query.where(JobPosting.sourced_by_user_id == sourced_by)
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
        
        # Build response with sourced_by info for email jobs
        jobs_list = []
        for job in jobs:
            job_dict = job.to_dict()
            job_dict = _add_sourced_by_info(job_dict, job)
            jobs_list.append(job_dict)
        
        return jsonify({
            'jobs': jobs_list,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 0
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing job postings: {str(e)}")
        return error_response(f"Failed to list job postings: {str(e)}", 500)


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
        tenant_id = g.tenant_id
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
        
        # Visibility rules: scraped (global) + email (tenant-specific)
        visibility_filter = or_(
            JobPosting.is_email_sourced == False,
            and_(
                JobPosting.is_email_sourced == True,
                JobPosting.source_tenant_id == tenant_id
            )
        )
        
        query = (
            select(JobPosting)
            .where(and_(search_filter, visibility_filter, JobPosting.status == 'ACTIVE'))
            .order_by(JobPosting.posted_date.desc().nullslast())
            .limit(50)
        )
        
        jobs = db.session.scalars(query).all()
        
        jobs_list = []
        for job in jobs:
            job_dict = job.to_dict()
            job_dict = _add_sourced_by_info(job_dict, job)
            jobs_list.append(job_dict)
        
        return jsonify(jobs_list), 200
        
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
    
    Returns stats for both scraped and email-sourced jobs.
    
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        # Visibility filter for all stats
        visibility_filter = or_(
            JobPosting.is_email_sourced == False,
            and_(
                JobPosting.is_email_sourced == True,
                JobPosting.source_tenant_id == tenant_id
            )
        )
        
        # Get counts
        total_jobs = db.session.scalar(
            select(func.count(JobPosting.id)).where(visibility_filter)
        )
        
        active_jobs = db.session.scalar(
            select(func.count(JobPosting.id))
            .where(visibility_filter, JobPosting.status == 'ACTIVE')
        )
        
        remote_jobs = db.session.scalar(
            select(func.count(JobPosting.id))
            .where(visibility_filter, JobPosting.is_remote == True)
        )
        
        # Scraped vs Email breakdown
        scraped_jobs = db.session.scalar(
            select(func.count(JobPosting.id))
            .where(JobPosting.is_email_sourced == False)
        )
        
        email_jobs = db.session.scalar(
            select(func.count(JobPosting.id))
            .where(
                JobPosting.is_email_sourced == True,
                JobPosting.source_tenant_id == tenant_id
            )
        )
        
        # Get unique companies and locations
        unique_companies = db.session.scalar(
            select(func.count(func.distinct(JobPosting.company)))
            .where(visibility_filter)
        )
        
        unique_locations = db.session.scalar(
            select(func.count(func.distinct(JobPosting.location)))
            .where(visibility_filter)
        )
        
        # Platform breakdown
        platform_counts = db.session.execute(
            select(JobPosting.platform, func.count(JobPosting.id))
            .where(visibility_filter)
            .group_by(JobPosting.platform)
        ).all()
        
        by_platform = {row[0]: row[1] for row in platform_counts if row[0]}
        
        # Email jobs by team member
        email_by_user = []
        if email_jobs > 0:
            user_counts = db.session.execute(
                select(
                    JobPosting.sourced_by_user_id,
                    func.count(JobPosting.id),
                )
                .where(
                    JobPosting.is_email_sourced == True,
                    JobPosting.source_tenant_id == tenant_id,
                    JobPosting.sourced_by_user_id.isnot(None),
                )
                .group_by(JobPosting.sourced_by_user_id)
            ).all()
            
            for user_id, count in user_counts:
                user = db.session.get(PortalUser, user_id)
                if user:
                    email_by_user.append({
                        "user_id": user_id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "jobs_count": count,
                    })
        
        # Email processing stats
        emails_processed = db.session.scalar(
            select(func.count(ProcessedEmail.id))
            .where(ProcessedEmail.tenant_id == tenant_id)
        ) or 0
        
        emails_converted = db.session.scalar(
            select(func.count(ProcessedEmail.id))
            .where(
                ProcessedEmail.tenant_id == tenant_id,
                ProcessedEmail.job_id.isnot(None),
            )
        ) or 0
        
        return jsonify({
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'remote_jobs': remote_jobs,
            'unique_companies': unique_companies,
            'unique_locations': unique_locations,
            # Source breakdown
            'scraped_jobs': scraped_jobs,
            'email_jobs': email_jobs,
            'by_platform': by_platform,
            # Email stats
            'email_by_user': email_by_user,
            'emails_processed': emails_processed,
            'emails_converted': emails_converted,
            'email_conversion_rate': round(emails_converted / emails_processed * 100, 1) if emails_processed > 0 else 0,
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job statistics: {str(e)}")
        return error_response("Failed to get job statistics", 500)


@job_posting_bp.route('/sources', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_job_sources():
    """
    Get list of available job sources/platforms.
    
    GET /api/job-postings/sources
    
    Returns:
        List of platforms with job counts for filtering UI.
    """
    try:
        tenant_id = g.tenant_id
        
        # Visibility filter
        visibility_filter = or_(
            JobPosting.is_email_sourced == False,
            and_(
                JobPosting.is_email_sourced == True,
                JobPosting.source_tenant_id == tenant_id
            )
        )
        
        # Get platforms with counts
        platform_counts = db.session.execute(
            select(JobPosting.platform, func.count(JobPosting.id))
            .where(visibility_filter)
            .group_by(JobPosting.platform)
            .order_by(func.count(JobPosting.id).desc())
        ).all()
        
        sources = []
        for platform, count in platform_counts:
            if platform:
                sources.append({
                    'platform': platform,
                    'count': count,
                    'is_email': platform == 'email',
                    'display_name': platform.title() if platform != 'email' else 'Email Integration'
                })
        
        return jsonify({
            'sources': sources,
            'total_sources': len(sources)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job sources: {str(e)}")
        return error_response("Failed to get job sources", 500)


@job_posting_bp.route('/team-sources', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_team_job_sources():
    """
    Get jobs grouped by team member who sourced them (email jobs).
    
    GET /api/job-postings/team-sources
    
    Query params:
    - page: int (default 1)
    - per_page: int (default 20)
    - user_id: int (filter by specific user)
    
    Returns:
        List of team members with their sourced jobs.
    """
    try:
        tenant_id = g.tenant_id
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        user_id_filter = request.args.get('user_id', type=int)
        
        # Get all users who have sourced jobs
        user_query = (
            select(
                JobPosting.sourced_by_user_id,
                func.count(JobPosting.id).label('job_count')
            )
            .where(
                JobPosting.is_email_sourced == True,
                JobPosting.source_tenant_id == tenant_id,
                JobPosting.sourced_by_user_id.isnot(None)
            )
            .group_by(JobPosting.sourced_by_user_id)
            .order_by(func.count(JobPosting.id).desc())
        )
        
        if user_id_filter:
            user_query = user_query.where(JobPosting.sourced_by_user_id == user_id_filter)
        
        user_results = db.session.execute(user_query).all()
        
        team_sources = []
        for user_id, job_count in user_results:
            user = db.session.get(PortalUser, user_id)
            if not user:
                continue
            
            # Get jobs for this user (paginated)
            jobs_query = (
                select(JobPosting)
                .where(
                    JobPosting.is_email_sourced == True,
                    JobPosting.source_tenant_id == tenant_id,
                    JobPosting.sourced_by_user_id == user_id
                )
                .order_by(JobPosting.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            
            jobs = db.session.scalars(jobs_query).all()
            
            team_sources.append({
                'user': {
                    'id': user.id,
                    'name': f"{user.first_name} {user.last_name}",
                    'email': user.email,
                },
                'job_count': job_count,
                'jobs': [job.to_dict(include_description=False) for job in jobs]
            })
        
        return jsonify({
            'team_sources': team_sources,
            'total_team_members': len(team_sources),
            'page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting team job sources: {str(e)}")
        return error_response("Failed to get team job sources", 500)
