"""
Submission routes for tracking candidate submissions to job postings.
Core ATS (Applicant Tracking System) functionality.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
import logging
from datetime import datetime

from app import db
from app.services.submission_service import SubmissionService
from app.schemas.submission_schema import (
    SubmissionCreateSchema,
    ExternalSubmissionCreateSchema,
    SubmissionUpdateSchema,
    SubmissionStatusUpdateSchema,
    SubmissionInterviewScheduleSchema,
    SubmissionActivityCreateSchema,
    SubmissionFilterSchema,
    SubmissionResponse,
    SubmissionListResponse,
    SubmissionActivityResponse,
    SubmissionStatsResponse,
)
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context

logger = logging.getLogger(__name__)

submission_bp = Blueprint('submission', __name__, url_prefix='/api/submissions')


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses"""
    return jsonify({
        'error': 'Error',
        'message': message,
        'status': status,
        'details': details or {}
    }), status


def get_service() -> SubmissionService:
    """Get submission service for current tenant."""
    return SubmissionService(tenant_id=g.tenant_id)


# ==================== CRUD Endpoints ====================

@submission_bp.route('', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.create')
def create_submission():
    """
    Create a new submission (submit candidate to job).
    
    Request Body: SubmissionCreateSchema
    Returns: SubmissionResponse
    """
    try:
        # Validate request body
        data = SubmissionCreateSchema.model_validate(request.get_json())
        
        # Create submission
        service = get_service()
        submission = service.create_submission(
            user_id=g.user_id,
            candidate_id=data.candidate_id,
            job_posting_id=data.job_posting_id,
            vendor_company=data.vendor_company,
            vendor_contact_name=data.vendor_contact_name,
            vendor_contact_email=data.vendor_contact_email,
            vendor_contact_phone=data.vendor_contact_phone,
            client_company=data.client_company,
            bill_rate=data.bill_rate,
            pay_rate=data.pay_rate,
            rate_type=data.rate_type or 'HOURLY',
            currency=data.currency or 'USD',
            submission_notes=data.submission_notes,
            cover_letter=data.cover_letter,
            tailored_resume_id=data.tailored_resume_id,
            priority=data.priority or 'MEDIUM',
            is_hot=data.is_hot or False,
            follow_up_date=data.follow_up_date,
        )
        
        # Return response with related data
        response_data = submission.to_dict(
            include_candidate=True,
            include_job=True,
            include_submitted_by=True
        )
        
        logger.info(f"Created submission {submission.id} by user {g.user_id}")
        
        return jsonify(response_data), 201
    
    except ValidationError as e:
        logger.warning(f"Validation error creating submission: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except ValueError as e:
        # Business logic errors (duplicate, not found, etc.)
        logger.warning(f"Business error creating submission: {e}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"Error creating submission: {e}", exc_info=True)
        return error_response(f"Failed to create submission: {str(e)}", 500)


@submission_bp.route('/external', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.create')
def create_external_submission():
    """
    Create a new submission to an external job (not in portal).
    
    This allows recruiters to track submissions to jobs they found
    outside the portal (LinkedIn, Dice, company websites, etc.).
    
    Request Body: ExternalSubmissionCreateSchema
    Returns: SubmissionResponse
    """
    try:
        # Validate request body
        data = ExternalSubmissionCreateSchema.model_validate(request.get_json())
        
        # Create external submission
        service = get_service()
        submission = service.create_external_submission(
            user_id=g.user_id,
            candidate_id=data.candidate_id,
            external_job_title=data.external_job_title,
            external_job_company=data.external_job_company,
            external_job_location=data.external_job_location,
            external_job_url=data.external_job_url,
            external_job_description=data.external_job_description,
            vendor_company=data.vendor_company,
            vendor_contact_name=data.vendor_contact_name,
            vendor_contact_email=data.vendor_contact_email,
            vendor_contact_phone=data.vendor_contact_phone,
            client_company=data.client_company,
            bill_rate=data.bill_rate,
            pay_rate=data.pay_rate,
            rate_type=data.rate_type or 'HOURLY',
            currency=data.currency or 'USD',
            submission_notes=data.submission_notes,
            priority=data.priority or 'MEDIUM',
            is_hot=data.is_hot or False,
            follow_up_date=data.follow_up_date,
        )
        
        # Return response with related data
        response_data = submission.to_dict(
            include_candidate=True,
            include_job=True,
            include_submitted_by=True
        )
        
        logger.info(f"Created external submission {submission.id} by user {g.user_id}")
        
        return jsonify(response_data), 201
    
    except ValidationError as e:
        logger.warning(f"Validation error creating external submission: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except ValueError as e:
        # Business logic errors (not found, etc.)
        logger.warning(f"Business error creating external submission: {e}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"Error creating external submission: {e}", exc_info=True)
        return error_response(f"Failed to create external submission: {str(e)}", 500)


@submission_bp.route('/<int:submission_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_submission(submission_id: int):
    """
    Get a submission by ID.
    
    Query params:
    - include_activities: Include activity log (default: false)
    
    Returns: SubmissionResponse
    """
    try:
        service = get_service()
        
        include_activities = request.args.get('include_activities', 'false').lower() == 'true'
        
        submission = service.get_submission(
            submission_id=submission_id,
            include_candidate=True,
            include_job=True,
            include_activities=include_activities
        )
        
        if not submission:
            return error_response("Submission not found", 404)
        
        response_data = submission.to_dict(
            include_candidate=True,
            include_job=True,
            include_submitted_by=True,
            include_activities=include_activities
        )
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Error getting submission {submission_id}: {e}", exc_info=True)
        return error_response(f"Failed to get submission: {str(e)}", 500)


@submission_bp.route('', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def list_submissions():
    """
    List submissions with filters and pagination.
    
    Query Params:
    - status: Filter by single status
    - statuses: Filter by multiple statuses (comma-separated)
    - candidate_id: Filter by candidate
    - job_posting_id: Filter by job
    - submitted_by_user_id: Filter by submitting user
    - vendor_company: Filter by vendor (partial match)
    - client_company: Filter by client (partial match)
    - priority: Filter by priority
    - is_hot: Filter by hot flag
    - is_active: Filter active submissions only
    - submitted_after: Filter by date
    - submitted_before: Filter by date
    - page: Page number (default 1)
    - per_page: Items per page (default 20)
    - sort_by: Field to sort by (default: submitted_at)
    - sort_order: asc or desc (default: desc)
    
    Returns: SubmissionListResponse
    """
    try:
        service = get_service()
        
        # Parse query parameters
        status = request.args.get('status')
        statuses_param = request.args.get('statuses')
        statuses = statuses_param.split(',') if statuses_param else None
        
        candidate_id = request.args.get('candidate_id', type=int)
        job_posting_id = request.args.get('job_posting_id', type=int)
        submitted_by_user_id = request.args.get('submitted_by_user_id', type=int)
        vendor_company = request.args.get('vendor_company')
        client_company = request.args.get('client_company')
        priority = request.args.get('priority')
        is_hot = request.args.get('is_hot')
        is_active = request.args.get('is_active')
        
        # Parse date filters
        submitted_after = None
        submitted_before = None
        if request.args.get('submitted_after'):
            submitted_after = datetime.fromisoformat(request.args.get('submitted_after').replace('Z', '+00:00'))
        if request.args.get('submitted_before'):
            submitted_before = datetime.fromisoformat(request.args.get('submitted_before').replace('Z', '+00:00'))
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        sort_by = request.args.get('sort_by', 'submitted_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Convert string booleans
        if is_hot is not None:
            is_hot = is_hot.lower() == 'true'
        if is_active is not None:
            is_active = is_active.lower() == 'true'
        
        # Fetch submissions
        submissions, total = service.get_submissions(
            status=status,
            statuses=statuses,
            candidate_id=candidate_id,
            job_posting_id=job_posting_id,
            submitted_by_user_id=submitted_by_user_id,
            vendor_company=vendor_company,
            client_company=client_company,
            priority=priority,
            is_hot=is_hot,
            is_active=is_active,
            submitted_after=submitted_after,
            submitted_before=submitted_before,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Convert to response
        items = [
            s.to_dict(include_candidate=True, include_job=True, include_submitted_by=True)
            for s in submissions
        ]
        
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        return jsonify({
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing submissions: {e}", exc_info=True)
        return error_response(f"Failed to list submissions: {str(e)}", 500)


@submission_bp.route('/<int:submission_id>', methods=['PUT'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.edit')
def update_submission(submission_id: int):
    """
    Update a submission.
    
    Request Body: SubmissionUpdateSchema
    Returns: SubmissionResponse
    """
    try:
        # Validate request body
        data = SubmissionUpdateSchema.model_validate(request.get_json())
        
        service = get_service()
        
        submission = service.update_submission(
            submission_id=submission_id,
            user_id=g.user_id,
            data=data.model_dump(exclude_unset=True)
        )
        
        response_data = submission.to_dict(
            include_candidate=True,
            include_job=True,
            include_submitted_by=True
        )
        
        logger.info(f"Updated submission {submission_id} by user {g.user_id}")
        
        return jsonify(response_data), 200
    
    except ValidationError as e:
        logger.warning(f"Validation error updating submission {submission_id}: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except ValueError as e:
        logger.warning(f"Business error updating submission {submission_id}: {e}")
        return error_response(str(e), 404 if "not found" in str(e).lower() else 400)
    
    except Exception as e:
        logger.error(f"Error updating submission {submission_id}: {e}", exc_info=True)
        return error_response(f"Failed to update submission: {str(e)}", 500)


@submission_bp.route('/<int:submission_id>/status', methods=['PUT'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.edit')
def update_submission_status(submission_id: int):
    """
    Update submission status with activity logging.
    
    Request Body: SubmissionStatusUpdateSchema
    Returns: SubmissionResponse
    """
    try:
        # Validate request body
        data = SubmissionStatusUpdateSchema.model_validate(request.get_json())
        
        service = get_service()
        
        submission = service.update_status(
            submission_id=submission_id,
            user_id=g.user_id,
            new_status=data.status,
            note=data.note,
            rejection_reason=data.rejection_reason,
            rejection_stage=data.rejection_stage,
            withdrawal_reason=data.withdrawal_reason,
            placement_start_date=data.placement_start_date,
            placement_end_date=data.placement_end_date,
            placement_duration_months=data.placement_duration_months
        )
        
        response_data = submission.to_dict(
            include_candidate=True,
            include_job=True,
            include_submitted_by=True,
            include_activities=True
        )
        
        logger.info(f"Updated submission {submission_id} status to {data.status} by user {g.user_id}")
        
        return jsonify(response_data), 200
    
    except ValidationError as e:
        logger.warning(f"Validation error updating submission status {submission_id}: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except ValueError as e:
        logger.warning(f"Business error updating submission status {submission_id}: {e}")
        return error_response(str(e), 404 if "not found" in str(e).lower() else 400)
    
    except Exception as e:
        logger.error(f"Error updating submission status {submission_id}: {e}", exc_info=True)
        return error_response(f"Failed to update submission status: {str(e)}", 500)


@submission_bp.route('/<int:submission_id>', methods=['DELETE'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.delete')
def delete_submission(submission_id: int):
    """
    Delete a submission (idempotent).
    
    Returns: Success message
    """
    try:
        service = get_service()
        
        success = service.delete_submission(submission_id)
        
        if not success:
            logger.warning(f"Submission {submission_id} not found (may be already deleted)")
            return jsonify({
                'message': 'Submission deleted successfully',
                'submission_id': submission_id,
                'already_deleted': True
            }), 200
        
        logger.info(f"Deleted submission {submission_id} by user {g.user_id}")
        
        return jsonify({
            'message': 'Submission deleted successfully',
            'submission_id': submission_id
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting submission {submission_id}: {e}", exc_info=True)
        return error_response(f"Failed to delete submission: {str(e)}", 500)


# ==================== Activity Endpoints ====================

@submission_bp.route('/<int:submission_id>/activities', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_submission_activities(submission_id: int):
    """
    Get activity log for a submission.
    
    Query params:
    - limit: Maximum activities to return (default 50)
    - activity_type: Filter by activity type
    
    Returns: List of SubmissionActivityResponse
    """
    try:
        service = get_service()
        
        # Verify submission exists
        submission = service.get_submission(submission_id)
        if not submission:
            return error_response("Submission not found", 404)
        
        limit = request.args.get('limit', 50, type=int)
        activity_type = request.args.get('activity_type')
        
        activities = service.get_activities(
            submission_id=submission_id,
            limit=limit,
            activity_type=activity_type
        )
        
        return jsonify({
            'submission_id': submission_id,
            'activities': [a.to_dict() for a in activities],
            'total': len(activities)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting activities for submission {submission_id}: {e}", exc_info=True)
        return error_response(f"Failed to get activities: {str(e)}", 500)


@submission_bp.route('/<int:submission_id>/activities', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.edit')
def add_submission_activity(submission_id: int):
    """
    Add a note/activity to a submission.
    
    Request Body: SubmissionActivityCreateSchema
    Returns: SubmissionActivityResponse
    """
    try:
        # Validate request body
        data = SubmissionActivityCreateSchema.model_validate(request.get_json())
        
        service = get_service()
        
        activity = service.add_activity(
            submission_id=submission_id,
            user_id=g.user_id,
            activity_type=data.activity_type,
            content=data.content,
            metadata=data.metadata
        )
        
        logger.info(f"Added {data.activity_type} activity to submission {submission_id} by user {g.user_id}")
        
        return jsonify(activity.to_dict()), 201
    
    except ValidationError as e:
        logger.warning(f"Validation error adding activity: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except ValueError as e:
        logger.warning(f"Business error adding activity: {e}")
        return error_response(str(e), 404 if "not found" in str(e).lower() else 400)
    
    except Exception as e:
        logger.error(f"Error adding activity to submission {submission_id}: {e}", exc_info=True)
        return error_response(f"Failed to add activity: {str(e)}", 500)


# ==================== Interview Scheduling ====================

@submission_bp.route('/<int:submission_id>/interview', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.edit')
def schedule_interview(submission_id: int):
    """
    Schedule an interview for a submission.
    
    Request Body: SubmissionInterviewScheduleSchema
    Returns: SubmissionResponse
    """
    try:
        # Validate request body
        data = SubmissionInterviewScheduleSchema.model_validate(request.get_json())
        
        service = get_service()
        
        submission = service.schedule_interview(
            submission_id=submission_id,
            user_id=g.user_id,
            interview_scheduled_at=data.interview_scheduled_at,
            interview_type=data.interview_type,
            interview_location=data.interview_location,
            interview_notes=data.interview_notes
        )
        
        response_data = submission.to_dict(
            include_candidate=True,
            include_job=True,
            include_submitted_by=True,
            include_activities=True
        )
        
        logger.info(f"Scheduled interview for submission {submission_id} by user {g.user_id}")
        
        return jsonify(response_data), 200
    
    except ValidationError as e:
        logger.warning(f"Validation error scheduling interview: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except ValueError as e:
        logger.warning(f"Business error scheduling interview: {e}")
        return error_response(str(e), 404 if "not found" in str(e).lower() else 400)
    
    except Exception as e:
        logger.error(f"Error scheduling interview for submission {submission_id}: {e}", exc_info=True)
        return error_response(f"Failed to schedule interview: {str(e)}", 500)


# ==================== Relationship Queries ====================

@submission_bp.route('/my', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_my_submissions():
    """
    Get submissions made by the current user.
    
    Query params:
    - is_active_only: Only return active submissions (default: false)
    
    Returns: List of submissions
    """
    try:
        service = get_service()
        
        is_active_only = request.args.get('is_active_only', 'false').lower() == 'true'
        
        submissions = service.get_user_submissions(
            user_id=g.user_id,
            is_active_only=is_active_only
        )
        
        return jsonify({
            'submissions': [
                s.to_dict(include_candidate=True, include_job=True)
                for s in submissions
            ],
            'total': len(submissions)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting user submissions: {e}", exc_info=True)
        return error_response(f"Failed to get submissions: {str(e)}", 500)


@submission_bp.route('/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_submission_stats():
    """
    Get submission statistics.
    
    Query params:
    - user_id: Optional filter by user (default: all users)
    - days_back: Days to look back for time-based stats (default: 30)
    
    Returns: SubmissionStatsResponse
    """
    try:
        service = get_service()
        
        user_id = request.args.get('user_id', type=int)
        days_back = request.args.get('days_back', 30, type=int)
        
        stats = service.get_stats(user_id=user_id, days_back=days_back)
        
        return jsonify(stats), 200
    
    except Exception as e:
        logger.error(f"Error getting submission stats: {e}", exc_info=True)
        return error_response(f"Failed to get statistics: {str(e)}", 500)


@submission_bp.route('/submitters', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_submitters():
    """
    Get list of users who have made submissions (for filter dropdown).
    
    Returns list of users with their submission counts.
    
    GET /api/submissions/submitters
    
    Returns:
    - submitters: List of {id, first_name, last_name, email, submission_count}
    """
    from sqlalchemy import select, func
    from app.models.submission import Submission
    from app.models.portal_user import PortalUser
    
    try:
        tenant_id = g.tenant_id
        
        # Get users who have made submissions in this tenant
        query = (
            select(
                PortalUser.id,
                PortalUser.first_name,
                PortalUser.last_name,
                PortalUser.email,
                func.count(Submission.id).label('submission_count')
            )
            .join(Submission, Submission.submitted_by_user_id == PortalUser.id)
            .where(Submission.tenant_id == tenant_id)
            .group_by(PortalUser.id)
            .order_by(func.count(Submission.id).desc())
        )
        
        results = db.session.execute(query).all()
        
        submitters = [
            {
                'id': row.id,
                'first_name': row.first_name,
                'last_name': row.last_name,
                'email': row.email,
                'submission_count': row.submission_count
            }
            for row in results
        ]
        
        return jsonify({'submitters': submitters}), 200
    
    except Exception as e:
        logger.error(f"Error getting submitters: {e}", exc_info=True)
        return error_response(f"Failed to get submitters: {str(e)}", 500)


@submission_bp.route('/follow-ups', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_follow_ups():
    """
    Get submissions with upcoming or overdue follow-ups.
    
    Query params:
    - user_id: Filter by user (default: current user)
    - days_ahead: Days to look ahead for upcoming (default: 7)
    - include_overdue: Include overdue follow-ups (default: true)
    
    Returns: Follow-up submissions grouped by status
    """
    try:
        service = get_service()
        
        user_id = request.args.get('user_id', g.user_id, type=int)
        days_ahead = request.args.get('days_ahead', 7, type=int)
        include_overdue = request.args.get('include_overdue', 'true').lower() == 'true'
        
        upcoming = service.get_upcoming_follow_ups(user_id=user_id, days_ahead=days_ahead)
        overdue = service.get_overdue_follow_ups(user_id=user_id) if include_overdue else []
        
        return jsonify({
            'upcoming': [
                s.to_dict(include_candidate=True, include_job=True)
                for s in upcoming
            ],
            'overdue': [
                s.to_dict(include_candidate=True, include_job=True)
                for s in overdue
            ],
            'total_upcoming': len(upcoming),
            'total_overdue': len(overdue)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting follow-ups: {e}", exc_info=True)
        return error_response(f"Failed to get follow-ups: {str(e)}", 500)


# ==================== Candidate/Job Specific Routes ====================
# These are alternative entry points for the same data

@submission_bp.route('/by-candidate/<int:candidate_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_candidate_submissions(candidate_id: int):
    """
    Get all submissions for a specific candidate.
    
    Returns: List of submissions for the candidate
    """
    try:
        service = get_service()
        
        submissions = service.get_candidate_submissions(
            candidate_id=candidate_id,
            include_job=True
        )
        
        return jsonify({
            'candidate_id': candidate_id,
            'submissions': [
                s.to_dict(include_job=True, include_submitted_by=True)
                for s in submissions
            ],
            'total': len(submissions)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting submissions for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to get submissions: {str(e)}", 500)


@submission_bp.route('/by-job/<int:job_posting_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def get_job_submissions(job_posting_id: int):
    """
    Get all submissions for a specific job posting.
    
    Returns: List of submissions for the job
    """
    try:
        service = get_service()
        
        submissions = service.get_job_submissions(
            job_posting_id=job_posting_id,
            include_candidate=True
        )
        
        return jsonify({
            'job_posting_id': job_posting_id,
            'submissions': [
                s.to_dict(include_candidate=True, include_submitted_by=True)
                for s in submissions
            ],
            'total': len(submissions)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting submissions for job {job_posting_id}: {e}", exc_info=True)
        return error_response(f"Failed to get submissions: {str(e)}", 500)


@submission_bp.route('/check-duplicate', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('submissions.view')
def check_duplicate():
    """
    Check if a submission already exists for candidate-job pair.
    
    Query params:
    - candidate_id: Candidate ID (required)
    - job_posting_id: Job posting ID (required)
    
    Returns: Existing submission if found, null otherwise
    """
    try:
        candidate_id = request.args.get('candidate_id', type=int)
        job_posting_id = request.args.get('job_posting_id', type=int)
        
        if not candidate_id or not job_posting_id:
            return error_response("candidate_id and job_posting_id are required", 400)
        
        service = get_service()
        
        existing = service.check_duplicate(candidate_id, job_posting_id)
        
        if existing:
            return jsonify({
                'exists': True,
                'submission': existing.to_dict(include_candidate=True, include_job=True)
            }), 200
        
        return jsonify({
            'exists': False,
            'submission': None
        }), 200
    
    except Exception as e:
        logger.error(f"Error checking duplicate: {e}", exc_info=True)
        return error_response(f"Failed to check duplicate: {str(e)}", 500)


# ==================== Health Check ====================

@submission_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'submission',
        'message': 'Submission service is running'
    }), 200
