"""
Job Posting Service
Business logic for job posting queries with optimized N+1 elimination
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.orm import joinedload

from app import db
from app.models.job_posting import JobPosting
from app.models.portal_user import PortalUser
from app.models.processed_email import ProcessedEmail

logger = logging.getLogger(__name__)


class JobPostingService:
    """Service for optimized job posting queries"""
    
    @staticmethod
    def _get_visibility_filter(tenant_id: int, source: str = 'all'):
        """
        Build visibility filter for multi-tenant job access.
        
        Args:
            tenant_id: Current tenant ID
            source: Filter by source ('all', 'email', 'scraped')
            
        Returns:
            SQLAlchemy filter condition
        """
        if source == 'email':
            # Only email-sourced jobs for this tenant
            return and_(
                JobPosting.is_email_sourced.is_(True),
                JobPosting.source_tenant_id == tenant_id
            )
        elif source == 'scraped':
            # Only scraped jobs (global)
            return JobPosting.is_email_sourced.is_(False)
        else:
            # All jobs: scraped (global) + email (tenant-specific)
            return or_(
                JobPosting.is_email_sourced.is_(False),
                and_(
                    JobPosting.is_email_sourced.is_(True),
                    JobPosting.source_tenant_id == tenant_id
                )
            )
    
    @staticmethod
    def _get_email_direct_link(provider: str, message_id: str, thread_id: Optional[str], 
                               email_address: str) -> Optional[str]:
        """
        Generate direct link to open email in provider's web interface.
        
        Args:
            provider: Email provider ('gmail' or 'outlook')
            message_id: Email message ID
            thread_id: Email thread ID (optional)
            email_address: User's email address
            
        Returns:
            Direct URL to email or None
        """
        if provider == 'gmail':
            if thread_id:
                return f"https://mail.google.com/mail/u/{email_address}/#all/{thread_id}"
            return None
        elif provider == 'outlook':
            if message_id:
                # Outlook web URL format (simplified)
                return f"https://outlook.office.com/mail/inbox/id/{message_id}"
            return None
        return None
    
    @staticmethod
    def list_jobs_optimized(
        tenant_id: int,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        location: Optional[str] = None,
        is_remote: Optional[bool] = None,
        sort_by: str = 'date',
        sort_order: str = 'desc',
        source: str = 'all',
        platform: Optional[str] = None,
        sourced_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List job postings with optimized eager loading to eliminate N+1 queries.
        
        Args:
            tenant_id: Current tenant ID
            page: Page number (1-indexed)
            per_page: Results per page (max 100)
            status: Filter by status ('active', 'inactive', 'closed')
            search: Search in title, company, location, description, skills
            location: Filter by location (partial match)
            is_remote: Filter by remote flag
            sort_by: Sort field ('date', 'posted_date', 'title', 'company', 'salary_min', 'created_at')
            sort_order: Sort direction ('asc', 'desc')
            source: Filter by source ('all', 'email', 'scraped')
            platform: Filter by platform ('indeed', 'dice', 'email', etc.)
            sourced_by: Filter by user ID who sourced email jobs
            
        Returns:
            Dict with 'jobs', 'total', 'page', 'per_page', 'pages'
        """
        # Build base query with visibility filter
        visibility_filter = JobPostingService._get_visibility_filter(tenant_id, source)
        query = select(JobPosting).where(visibility_filter)
        
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
            query = query.where(JobPosting.is_remote == is_remote)
        
        search_filter = None
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
        if sort_by == 'date':
            # COALESCE: prefer posted_date, fall back to created_at
            sort_field = coalesce(
                func.cast(JobPosting.posted_date, db.DateTime),
                JobPosting.created_at
            )
        else:
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
        
        # Eager load sourced_by_user to prevent N+1
        # Type ignore for SQLAlchemy relationship property
        query = query.options(joinedload(JobPosting.sourced_by_user))  # type: ignore[arg-type]
        
        # Get total count with same filters (for pagination)
        count_query = select(func.count(JobPosting.id)).where(visibility_filter)
        
        if status:
            count_query = count_query.where(JobPosting.status == status)
        if platform:
            count_query = count_query.where(JobPosting.platform == platform)
        if sourced_by:
            count_query = count_query.where(JobPosting.sourced_by_user_id == sourced_by)
        if location:
            count_query = count_query.where(JobPosting.location.ilike(f'%{location}%'))
        if is_remote is not None:
            count_query = count_query.where(JobPosting.is_remote == is_remote)
        if search and search_filter is not None:
            count_query = count_query.where(search_filter)
        
        total = db.session.scalar(count_query) or 0
        
        # Execute paginated query
        jobs = db.session.scalars(
            query.offset((page - 1) * per_page).limit(per_page)
        ).unique().all()  # .unique() required when using joinedload
        
        # Batch fetch email integration data for all email-sourced jobs
        email_jobs = [job for job in jobs if job.is_email_sourced and job.source_email_id]
        email_integrations = {}
        
        if email_jobs:
            # Single query to fetch all email integration data
            email_ids = [job.source_email_id for job in email_jobs]
            processed_emails_query = select(ProcessedEmail).where(
                ProcessedEmail.email_message_id.in_(email_ids),
                ProcessedEmail.integration_id.isnot(None)
            ).options(joinedload(ProcessedEmail.integration))  # type: ignore[arg-type]
            
            processed_emails = db.session.scalars(processed_emails_query).unique().all()
            
            # Build lookup map: email_message_id -> integration
            for pe in processed_emails:
                if pe.integration:
                    email_integrations[pe.email_message_id] = {
                        'provider': pe.integration.provider,
                        'email_address': pe.integration.email_address,
                        'thread_id': pe.email_thread_id,
                    }
        
        # Build response with sourced_by info (already loaded via eager loading)
        jobs_list = []
        for job in jobs:
            job_dict = job.to_dict()
            
            # Add sourced_by user info (no extra query - already loaded)
            if job.is_email_sourced and job.sourced_by_user:
                job_dict["sourced_by"] = {
                    "id": job.sourced_by_user.id,
                    "first_name": job.sourced_by_user.first_name,
                    "last_name": job.sourced_by_user.last_name,
                    "email": job.sourced_by_user.email,
                }
                
                # Add email integration details (from batch fetch)
                if job.source_email_id in email_integrations:
                    integration_data = email_integrations[job.source_email_id]
                    email_direct_link = JobPostingService._get_email_direct_link(
                        provider=integration_data['provider'],
                        message_id=job.source_email_id,
                        thread_id=integration_data.get('thread_id'),
                        email_address=integration_data['email_address']
                    )
                    
                    job_dict["email_integration"] = {
                        "provider": integration_data['provider'],
                        "email_address": integration_data['email_address'],
                        "email_direct_link": email_direct_link,
                    }
            
            jobs_list.append(job_dict)
        
        return {
            'jobs': jobs_list,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 0
        }
    
    @staticmethod
    def get_statistics_optimized(tenant_id: int) -> Dict[str, Any]:
        """
        Get job posting statistics with optimized single-query aggregation.
        
        Uses conditional aggregation to combine multiple COUNT queries into one.
        
        Args:
            tenant_id: Current tenant ID
            
        Returns:
            Dict with statistics about job postings
        """
        # Visibility filter for stats
        visibility_filter = JobPostingService._get_visibility_filter(tenant_id, 'all')
        
        # Single aggregated query with conditional counts
        stats_query = select(
            func.count(JobPosting.id).label('total_jobs'),
            func.count(case((JobPosting.status == 'ACTIVE', 1))).label('active_jobs'),
            func.count(case((JobPosting.is_remote.is_(True), 1))).label('remote_jobs'),
            func.count(case((JobPosting.is_email_sourced.is_(False), 1))).label('scraped_jobs'),
            func.count(case(
                (and_(
                    JobPosting.is_email_sourced.is_(True),
                    JobPosting.source_tenant_id == tenant_id
                ), 1)
            )).label('email_jobs'),
            func.count(func.distinct(JobPosting.company)).label('unique_companies'),
            func.count(func.distinct(JobPosting.location)).label('unique_locations'),
        ).where(visibility_filter)
        
        result = db.session.execute(stats_query).first()
        
        if not result:
            return {
                'total_jobs': 0,
                'active_jobs': 0,
                'remote_jobs': 0,
                'unique_companies': 0,
                'unique_locations': 0,
                'scraped_jobs': 0,
                'email_jobs': 0,
                'by_platform': {},
                'email_by_user': [],
                'emails_processed': 0,
                'emails_converted': 0,
                'email_conversion_rate': 0,
            }
        
        # Platform breakdown (separate query - can't aggregate with above)
        platform_counts = db.session.execute(
            select(JobPosting.platform, func.count(JobPosting.id))
            .where(visibility_filter)
            .group_by(JobPosting.platform)
        ).all()
        
        by_platform = {row[0]: row[1] for row in platform_counts if row[0]}
        
        # Email jobs by team member (only if email jobs exist)
        email_by_user = []
        if result.email_jobs and result.email_jobs > 0:
            user_counts = db.session.execute(
                select(
                    JobPosting.sourced_by_user_id,
                    func.count(JobPosting.id),
                )
                .where(
                    JobPosting.is_email_sourced.is_(True),
                    JobPosting.source_tenant_id == tenant_id,
                    JobPosting.sourced_by_user_id.isnot(None),
                )
                .group_by(JobPosting.sourced_by_user_id)
            ).all()
            
            # Batch fetch user details
            user_ids = [row[0] for row in user_counts]
            users_query = select(PortalUser).where(PortalUser.id.in_(user_ids))
            users = {user.id: user for user in db.session.scalars(users_query).all()}
            
            for user_id, count in user_counts:
                user = users.get(user_id)
                if user:
                    email_by_user.append({
                        "user_id": user_id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "jobs_count": count,
                    })
        
        # Email processing stats (tenant-specific)
        email_stats_query = select(
            func.count(ProcessedEmail.id).label('emails_processed'),
            func.count(case((ProcessedEmail.job_id.isnot(None), 1))).label('emails_converted'),
        ).where(ProcessedEmail.tenant_id == tenant_id)
        
        email_stats = db.session.execute(email_stats_query).first()
        emails_processed = email_stats.emails_processed if email_stats and email_stats.emails_processed else 0
        emails_converted = email_stats.emails_converted if email_stats and email_stats.emails_converted else 0
        
        return {
            'total_jobs': result.total_jobs or 0,
            'active_jobs': result.active_jobs or 0,
            'remote_jobs': result.remote_jobs or 0,
            'unique_companies': result.unique_companies or 0,
            'unique_locations': result.unique_locations or 0,
            # Source breakdown
            'scraped_jobs': result.scraped_jobs or 0,
            'email_jobs': result.email_jobs or 0,
            'by_platform': by_platform,
            # Email stats
            'email_by_user': email_by_user,
            'emails_processed': emails_processed,
            'emails_converted': emails_converted,
            'email_conversion_rate': round(emails_converted / emails_processed * 100, 1) if emails_processed > 0 else 0,
        }
