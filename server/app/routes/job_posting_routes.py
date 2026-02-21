"""
Job Posting Routes
API endpoints for job posting management and viewing.
Includes both scraped jobs (global) and email-sourced jobs (tenant-specific).
"""
import logging
from flask import Blueprint, jsonify, request, g
from sqlalchemy import select, or_, func, and_, case
from sqlalchemy.sql.functions import coalesce

from app import db
from app.models.job_posting import JobPosting
from app.models.portal_user import PortalUser
from app.models.processed_email import ProcessedEmail
from app.models.user_email_integration import UserEmailIntegration
from app.models.candidate_job_match import CandidateJobMatch
from app.models.candidate import Candidate
from app.services.job_posting_service import JobPostingService
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


def _get_email_direct_link(
    provider: str,
    message_id: str,
    thread_id: str = None,
    email_address: str = None
) -> str:
    """
    Generate a direct link to open the email in Gmail or Outlook web.
    
    Args:
        provider: 'gmail' or 'outlook'
        message_id: The email message ID
        thread_id: Optional thread ID (used for Gmail thread view)
        email_address: Optional email address (for Gmail multi-account)
    
    Returns:
        URL string to open the email, or None if not supported
    """
    from urllib.parse import quote
    
    if provider == "gmail":
        # Use thread_id if available for better UX (shows full conversation)
        target_id = thread_id or message_id
        if email_address:
            # Multi-account support: use email address in URL
            return f"https://mail.google.com/mail/u/{quote(email_address)}/#all/{target_id}"
        return f"https://mail.google.com/mail/u/0/#all/{target_id}"
    
    elif provider == "outlook":
        # Outlook deeplink format for Office 365
        # Note: For personal accounts (outlook.com), users may need outlook.live.com
        return f"https://outlook.office365.com/mail/deeplink/read/{message_id}"
    
    return None


def _add_sourced_by_info(job_dict: dict, job: JobPosting) -> dict:
    """Add sourced_by user info and email integration details to job dict if email-sourced."""
    if job.is_email_sourced and job.sourced_by_user_id:
        user = db.session.get(PortalUser, job.sourced_by_user_id)
        if user:
            job_dict["sourced_by"] = {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            }
        
        # Get email integration details (provider and connected email address)
        # Query ProcessedEmail to find which integration was used for this job
        if job.source_email_id:
            processed_email = db.session.scalar(
                select(ProcessedEmail).where(
                    ProcessedEmail.job_id == job.id,
                    ProcessedEmail.email_message_id == job.source_email_id
                )
            )
            if processed_email and processed_email.integration_id:
                integration = db.session.get(UserEmailIntegration, processed_email.integration_id)
                if integration:
                    # Generate direct link to open the email
                    email_direct_link = _get_email_direct_link(
                        provider=integration.provider,
                        message_id=job.source_email_id,
                        thread_id=processed_email.email_thread_id,
                        email_address=integration.email_address
                    )
                    
                    job_dict["email_integration"] = {
                        "provider": integration.provider,  # 'gmail' or 'outlook'
                        "email_address": integration.email_address,
                        "email_direct_link": email_direct_link,  # Direct link to open email
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
        
        # Fetch matched candidates (score >= 50, top 10, ordered by score desc)
        match_stmt = (
            select(CandidateJobMatch, Candidate)
            .join(Candidate, CandidateJobMatch.candidate_id == Candidate.id)
            .where(
                CandidateJobMatch.job_posting_id == job_id,
                CandidateJobMatch.match_score >= 50
            )
            .order_by(CandidateJobMatch.match_score.desc())
            .limit(10)
        )
        match_results = db.session.execute(match_stmt).all()
        
        job_dict['matched_candidates'] = [
            {
                'candidate_id': match.id,
                'name': f"{candidate.first_name or ''} {candidate.last_name or ''}".strip() or 'Unknown',
                'match_score': float(match.match_score),
                'match_grade': match.match_grade,
            }
            for match, candidate in match_results
        ]
        job_dict['matched_candidates_count'] = len(match_results)
        
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
        is_remote_str = request.args.get('is_remote')
        sort_by = request.args.get('sort_by', 'date')
        sort_order = request.args.get('sort_order', 'desc')
        source = request.args.get('source', 'all')
        platform = request.args.get('platform')
        sourced_by = request.args.get('sourced_by', type=int)
        
        is_remote = None
        if is_remote_str is not None:
            is_remote = is_remote_str.lower() in ('true', '1', 'yes')
        
        result = JobPostingService.list_jobs_optimized(
            tenant_id=tenant_id,
            page=page,
            per_page=per_page,
            status=status,
            search=search,
            location=location,
            is_remote=is_remote,
            sort_by=sort_by,
            sort_order=sort_order,
            source=source,
            platform=platform,
            sourced_by=sourced_by,
        )
        
        return jsonify(result), 200
        
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
        
        stats = JobPostingService.get_statistics_optimized(tenant_id)
        
        return jsonify(stats), 200
        
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
