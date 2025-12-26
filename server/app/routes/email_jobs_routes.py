"""
Email Jobs Routes

API endpoints for viewing and managing jobs sourced from email integrations.
These jobs are tenant-specific (unlike global scraped jobs).
"""

import logging
from datetime import datetime

from flask import Blueprint, g, jsonify, request
from sqlalchemy import and_, desc, func, or_, select

from app import db
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context
from app.models.job_posting import JobPosting
from app.models.portal_user import PortalUser
from app.models.processed_email import ProcessedEmail
from app.models.user_email_integration import UserEmailIntegration

bp = Blueprint("email_jobs", __name__, url_prefix="/api/email-jobs")
logger = logging.getLogger(__name__)


def error_response(message: str, status: int = 400, details: dict = None):
    """Create a standardized error response."""
    return jsonify({
        "error": "Error",
        "message": message,
        "status": status,
        "details": details,
    }), status


# ============================================================================
# Email Jobs Listing
# ============================================================================

@bp.route("", methods=["GET"])
@require_portal_auth
@with_tenant_context
def list_email_jobs():
    """
    List jobs sourced from email integrations for the tenant.
    
    Query Parameters:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        sourced_by: Filter by user ID who sourced the job
        search: Search in title, company, skills
        status: Filter by job status (active, expired, etc.)
        
    Returns:
        Paginated list of email-sourced jobs
    """
    tenant_id = g.tenant_id
    
    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    
    # Filters
    sourced_by = request.args.get("sourced_by", type=int)
    search = request.args.get("search", "").strip()
    status = request.args.get("status")
    
    # Build query for email-sourced jobs in this tenant
    stmt = select(JobPosting).where(
        JobPosting.is_email_sourced == True,
        JobPosting.source_tenant_id == tenant_id,
    )
    
    if sourced_by:
        stmt = stmt.where(JobPosting.sourced_by_user_id == sourced_by)
    
    if status:
        stmt = stmt.where(JobPosting.status == status)
    
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                JobPosting.title.ilike(search_pattern),
                JobPosting.company.ilike(search_pattern),
                func.array_to_string(JobPosting.skills, ",").ilike(search_pattern),
            )
        )
    
    # Order by most recent first
    stmt = stmt.order_by(desc(JobPosting.created_at))
    
    # Paginate
    paginated = db.paginate(stmt, page=page, per_page=per_page)
    
    # Build response with source attribution
    jobs = []
    for job in paginated.items:
        job_dict = job.to_dict()
        
        # Get sourced by user info
        if job.sourced_by_user_id:
            user = db.session.get(PortalUser, job.sourced_by_user_id)
            if user:
                job_dict["sourced_by"] = {
                    "id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                }
        
        jobs.append(job_dict)
    
    return jsonify({
        "jobs": jobs,
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    }), 200


@bp.route("/<int:job_id>", methods=["GET"])
@require_portal_auth
@with_tenant_context
def get_email_job(job_id: int):
    """
    Get details of an email-sourced job.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job details with source information
    """
    tenant_id = g.tenant_id
    
    stmt = select(JobPosting).where(
        JobPosting.id == job_id,
        JobPosting.is_email_sourced == True,
        JobPosting.source_tenant_id == tenant_id,
    )
    job = db.session.scalar(stmt)
    
    if not job:
        return error_response("Job not found", status=404)
    
    job_dict = job.to_dict()
    
    # Add sourced by info
    if job.sourced_by_user_id:
        user = db.session.get(PortalUser, job.sourced_by_user_id)
        if user:
            job_dict["sourced_by"] = {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
            }
    
    return jsonify(job_dict), 200


@bp.route("/<int:job_id>", methods=["PUT"])
@require_portal_auth
@with_tenant_context
@require_permission("candidates.update")
def update_email_job(job_id: int):
    """
    Update an email-sourced job.
    
    Args:
        job_id: Job ID
        
    Returns:
        Updated job details
    """
    tenant_id = g.tenant_id
    
    stmt = select(JobPosting).where(
        JobPosting.id == job_id,
        JobPosting.is_email_sourced == True,
        JobPosting.source_tenant_id == tenant_id,
    )
    job = db.session.scalar(stmt)
    
    if not job:
        return error_response("Job not found", status=404)
    
    data = request.get_json()
    
    # Update allowed fields
    updateable_fields = [
        "title", "company", "location", "description", "job_type",
        "remote_type", "skills", "required_skills", "preferred_skills",
        "experience_years", "requirements", "min_rate", "max_rate",
        "min_salary", "max_salary", "employment_type", "duration_months",
        "status", "client_name",
    ]
    
    for field in updateable_fields:
        if field in data:
            setattr(job, field, data[field])
    
    job.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(job.to_dict()), 200


@bp.route("/<int:job_id>", methods=["DELETE"])
@require_portal_auth
@with_tenant_context
@require_permission("candidates.delete")
def delete_email_job(job_id: int):
    """
    Delete an email-sourced job.
    
    Args:
        job_id: Job ID
        
    Returns:
        Success message
    """
    tenant_id = g.tenant_id
    
    stmt = select(JobPosting).where(
        JobPosting.id == job_id,
        JobPosting.is_email_sourced == True,
        JobPosting.source_tenant_id == tenant_id,
    )
    job = db.session.scalar(stmt)
    
    if not job:
        return error_response("Job not found", status=404)
    
    db.session.delete(job)
    db.session.commit()
    
    return jsonify({"message": "Job deleted successfully"}), 200


# ============================================================================
# Email Jobs Statistics
# ============================================================================

@bp.route("/stats", methods=["GET"])
@require_portal_auth
@with_tenant_context
def get_email_jobs_stats():
    """
    Get statistics for email-sourced jobs in the tenant.
    
    Returns:
        Statistics including total jobs, by user, by provider
    """
    tenant_id = g.tenant_id
    
    # Total email jobs
    total_jobs = db.session.scalar(
        select(func.count(JobPosting.id)).where(
            JobPosting.is_email_sourced == True,
            JobPosting.source_tenant_id == tenant_id,
        )
    ) or 0
    
    # Jobs by status
    status_counts = db.session.execute(
        select(JobPosting.status, func.count(JobPosting.id))
        .where(
            JobPosting.is_email_sourced == True,
            JobPosting.source_tenant_id == tenant_id,
        )
        .group_by(JobPosting.status)
    ).all()
    
    by_status = {row[0]: row[1] for row in status_counts}
    
    # Jobs by user
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
    
    by_user = []
    for user_id, count in user_counts:
        user = db.session.get(PortalUser, user_id)
        if user:
            by_user.append({
                "user_id": user_id,
                "name": f"{user.first_name} {user.last_name}",
                "jobs_count": count,
            })
    
    # Total emails processed
    total_emails = db.session.scalar(
        select(func.count(ProcessedEmail.id))
        .where(ProcessedEmail.tenant_id == tenant_id)
    ) or 0
    
    # Emails that created jobs
    emails_with_jobs = db.session.scalar(
        select(func.count(ProcessedEmail.id))
        .where(
            ProcessedEmail.tenant_id == tenant_id,
            ProcessedEmail.job_id.isnot(None),
        )
    ) or 0
    
    return jsonify({
        "total_jobs": total_jobs,
        "by_status": by_status,
        "by_user": by_user,
        "emails_processed": total_emails,
        "emails_converted": emails_with_jobs,
        "conversion_rate": round(emails_with_jobs / total_emails * 100, 1) if total_emails > 0 else 0,
    }), 200


# ============================================================================
# Processed Emails
# ============================================================================

@bp.route("/emails", methods=["GET"])
@require_portal_auth
@with_tenant_context
def list_processed_emails():
    """
    List processed emails for the tenant.
    
    Query Parameters:
        page: Page number (default 1)
        per_page: Items per page (default 20)
        result: Filter by processing result (job_created, skipped, failed, error)
        integration_id: Filter by integration ID
        
    Returns:
        Paginated list of processed emails
    """
    tenant_id = g.tenant_id
    
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    result_filter = request.args.get("result")
    integration_id = request.args.get("integration_id", type=int)
    
    stmt = select(ProcessedEmail).where(
        ProcessedEmail.tenant_id == tenant_id
    )
    
    if result_filter:
        stmt = stmt.where(ProcessedEmail.processing_result == result_filter)
    
    if integration_id:
        stmt = stmt.where(ProcessedEmail.integration_id == integration_id)
    
    stmt = stmt.order_by(desc(ProcessedEmail.created_at))
    
    paginated = db.paginate(stmt, page=page, per_page=per_page)
    
    emails = []
    for email in paginated.items:
        emails.append({
            "id": email.id,
            "integration_id": email.integration_id,
            "email_message_id": email.email_message_id,
            "email_subject": email.email_subject,
            "email_sender": email.email_sender,
            "processing_result": email.processing_result,
            "job_id": email.job_id,
            "skip_reason": email.skip_reason,
            "parsing_confidence": email.parsing_confidence,
            "created_at": email.created_at.isoformat() if email.created_at else None,
        })
    
    return jsonify({
        "emails": emails,
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    }), 200
