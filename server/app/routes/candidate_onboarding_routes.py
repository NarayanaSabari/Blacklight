"""Candidate Onboarding routes for managing the onboarding workflow."""

from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
import logging

from app.services import CandidateService, AuditLogService, InvitationService # Added InvitationService
from app.schemas import (
    OnboardCandidateSchema,
    ApproveCandidateSchema,
    RejectCandidateSchema,
    UpdateOnboardingStatusSchema,
    GetOnboardingCandidatesQuerySchema,
    OnboardCandidateResponseSchema,
    ApproveCandidateResponseSchema,
    RejectCandidateResponseSchema,
    OnboardingCandidatesListResponseSchema,
    OnboardingStatsSchema,
    InvitationResponseSchema, # Added
    InvitationListResponseSchema, # Added
)
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint('candidate_onboarding', __name__, url_prefix='/api/candidates/onboarding')
candidate_service = CandidateService()


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses."""
    return jsonify({
        'error': 'Error',
        'message': message,
        'status': status,
        'details': details or {}
    }), status


@onboarding_bp.route('/invitations', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def list_submitted_invitations():
    """
    Get submitted invitations for review (paginated).
    
    Query Parameters:
        page (optional): Page number (default: 1)
        per_page (optional): Results per page (default: 20, max: 100)
        status (optional): Filter by invitation status (should be 'submitted')
        search (optional): Search by candidate name or email
    
    Returns: InvitationListResponseSchema
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', 'submitted') # Default to 'submitted'
        search_query = request.args.get('search')
        
        if status_filter != 'submitted':
            return error_response("This endpoint only supports 'submitted' status filter", 400)
        
        invitations, total = InvitationService.list_invitations(
            tenant_id=tenant_id,
            status_filter=status_filter,
            email_filter=search_query, # Reuse email_filter for search
            page=page,
            per_page=per_page
        )
        
        # Build response
        items = []
        for inv in invitations:
            items.append(InvitationResponseSchema.model_validate({
                **inv.to_dict(),
                "is_expired": inv.is_expired,
                "is_valid": inv.is_valid,
                "can_be_resent": inv.can_be_resent,
            }).model_dump())
        
        response = InvitationListResponseSchema(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if total > 0 else 0
        )
        
        return jsonify(response.model_dump()), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in list_submitted_invitations: {str(e)}")
        return error_response("Invalid query parameters", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in list_submitted_invitations: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error listing submitted invitations: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve submitted invitations", 500)


# ==================== Onboarding Action Endpoints ====================

@onboarding_bp.route('/onboard', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.onboard')
def onboard_candidate():
    """
    Mark a candidate as onboarded.
    
    Request Body: OnboardCandidateSchema
    Returns: OnboardCandidateResponseSchema
    Permissions: candidates.onboard (MANAGER, RECRUITER)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = OnboardCandidateSchema.model_validate(request.get_json())
        
        # Onboard candidate
        candidate = candidate_service.onboard_candidate(
            candidate_id=data.candidate_id,
            onboarded_by_user_id=user_id,
            changed_by=f"portal_user:{user_id}",
            tenant_id=tenant_id
        )
        
        logger.info(f"Candidate {data.candidate_id} onboarded by user {user_id}")
        
        return jsonify({
            'message': 'Candidate onboarded successfully',
            'candidate_id': candidate.id,
            'onboarding_status': candidate.onboarding_status,
            'onboarded_at': candidate.onboarded_at.isoformat() if candidate.onboarded_at else None,
            'onboarded_by_user_id': candidate.onboarded_by_user_id
        }), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in onboard_candidate: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in onboard_candidate: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error onboarding candidate: {str(e)}", exc_info=True)
        return error_response("Failed to onboard candidate", 500)


@onboarding_bp.route('/approve', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.approve')
def approve_candidate():
    """
    Approve an onboarded candidate (HR approval).
    
    Request Body: ApproveCandidateSchema
    Returns: ApproveCandidateResponseSchema
    Permissions: candidates.approve (HIRING_MANAGER only)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = ApproveCandidateSchema.model_validate(request.get_json())
        
        # Approve candidate
        candidate = candidate_service.approve_candidate(
            candidate_id=data.candidate_id,
            approved_by_user_id=user_id,
            changed_by=f"portal_user:{user_id}",
            tenant_id=tenant_id
        )
        
        logger.info(f"Candidate {data.candidate_id} approved by user {user_id}")
        
        return jsonify({
            'message': 'Candidate approved successfully',
            'candidate_id': candidate.id,
            'onboarding_status': candidate.onboarding_status,
            'approved_at': candidate.approved_at.isoformat() if candidate.approved_at else None,
            'approved_by_user_id': candidate.approved_by_user_id
        }), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in approve_candidate: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in approve_candidate: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error approving candidate: {str(e)}", exc_info=True)
        return error_response("Failed to approve candidate", 500)


@onboarding_bp.route('/reject', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.approve')
def reject_candidate():
    """
    Reject an onboarded candidate with reason (HR rejection).
    
    Request Body: RejectCandidateSchema
    Returns: RejectCandidateResponseSchema
    Permissions: candidates.approve (HIRING_MANAGER only)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = RejectCandidateSchema.model_validate(request.get_json())
        
        # Reject candidate
        candidate = candidate_service.reject_candidate(
            candidate_id=data.candidate_id,
            rejection_reason=data.rejection_reason,
            rejected_by_user_id=user_id,
            changed_by=f"portal_user:{user_id}",
            tenant_id=tenant_id
        )
        
        logger.info(f"Candidate {data.candidate_id} rejected by user {user_id}: {data.rejection_reason}")
        
        return jsonify({
            'message': 'Candidate rejected successfully',
            'candidate_id': candidate.id,
            'onboarding_status': candidate.onboarding_status,
            'rejected_at': candidate.rejected_at.isoformat() if candidate.rejected_at else None,
            'rejected_by_user_id': candidate.rejected_by_user_id,
            'rejection_reason': candidate.rejection_reason
        }), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in reject_candidate: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in reject_candidate: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error rejecting candidate: {str(e)}", exc_info=True)
        return error_response("Failed to reject candidate", 500)


@onboarding_bp.route('/status', methods=['PATCH'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.update')
def update_onboarding_status():
    """
    Update candidate onboarding status directly.
    
    Request Body: UpdateOnboardingStatusSchema
    Returns: Updated candidate info
    Permissions: candidates.update (HIRING_MANAGER, MANAGER)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = UpdateOnboardingStatusSchema.model_validate(request.get_json())
        
        # Update status
        candidate = candidate_service.update_onboarding_status(
            candidate_id=data.candidate_id,
            new_status=data.new_status,
            changed_by=f"portal_user:{user_id}",
            tenant_id=tenant_id
        )
        
        logger.info(f"Candidate {data.candidate_id} status updated to {data.new_status} by user {user_id}")
        
        return jsonify({
            'message': 'Onboarding status updated successfully',
            'candidate_id': candidate.id,
            'onboarding_status': candidate.onboarding_status
        }), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in update_onboarding_status: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in update_onboarding_status: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error updating onboarding status: {str(e)}", exc_info=True)
        return error_response("Failed to update onboarding status", 500)


# ==================== Onboarding Query Endpoints ====================

@onboarding_bp.route('/pending', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_pending_candidates():
    """
    Get candidates pending onboarding (paginated).
    
    Query Parameters:
        page (optional): Page number (default: 1)
        per_page (optional): Results per page (default: 20, max: 100)
        status (optional): Filter by onboarding status
        assigned_to_user_id (optional): Filter by assigned user
    
    Returns: OnboardingCandidatesResponseSchema
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        # Parse query parameters using schema
        query_params = GetOnboardingCandidatesQuerySchema.model_validate({
            'page': request.args.get('page', 1, type=int),
            'per_page': request.args.get('per_page', 20, type=int),
            'status_filter': request.args.get('status'),
            'assigned_to_user_id': request.args.get('assigned_to_user_id', type=int)
        })
        
        # Get candidates
        result = candidate_service.get_candidates_for_onboarding(
            tenant_id=tenant_id,
            page=query_params.page,
            per_page=query_params.per_page,
            status_filter=query_params.status_filter,
            assigned_to_user_id=query_params.assigned_to_user_id
        )
        
        return jsonify(result), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in get_pending_candidates: {str(e)}")
        return error_response("Invalid query parameters", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in get_pending_candidates: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting pending candidates: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve pending candidates", 500)


@onboarding_bp.route('/my-pending', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_my_pending_candidates():
    """
    Get candidates assigned to current user that are pending onboarding.
    
    Query Parameters:
        page (optional): Page number (default: 1)
        per_page (optional): Results per page (default: 20, max: 100)
        status (optional): Filter by onboarding status
    
    Returns: OnboardingCandidatesResponseSchema
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Parse query parameters
        query_params = GetOnboardingCandidatesQuerySchema.model_validate({
            'page': request.args.get('page', 1, type=int),
            'per_page': request.args.get('per_page', 20, type=int),
            'status_filter': request.args.get('status'),
            'assigned_to_user_id': user_id  # Filter to current user
        })
        
        # Get candidates
        result = candidate_service.get_candidates_for_onboarding(
            tenant_id=tenant_id,
            page=query_params.page,
            per_page=query_params.per_page,
            status_filter=query_params.status_filter,
            assigned_to_user_id=user_id
        )
        
        return jsonify(result), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in get_my_pending_candidates: {str(e)}")
        return error_response("Invalid query parameters", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in get_my_pending_candidates: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting my pending candidates: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve your pending candidates", 500)


@onboarding_bp.route('/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_onboarding_stats():
    """
    Get onboarding statistics (counts by status).
    
    Query Parameters:
        assigned_to_user_id (optional): Filter to specific user's assignments
    
    Returns: OnboardingStatsResponseSchema
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        assigned_to_user_id = request.args.get('assigned_to_user_id', type=int)
        
        # Get counts for each status
        from app.models import Candidate
        from app import db
        from sqlalchemy import select, func
        
        query = select(
            Candidate.onboarding_status,
            func.count(Candidate.id).label('count')
        ).where(
            Candidate.tenant_id == tenant_id
        )
        
        # Filter by assigned user if specified
        if assigned_to_user_id:
            query = query.where(
                (Candidate.manager_id == assigned_to_user_id) |
                (Candidate.recruiter_id == assigned_to_user_id)
            )
        
        # Group by status
        query = query.group_by(Candidate.onboarding_status)
        
        result = db.session.execute(query).all()
        
        # Build stats dict
        stats = {
            'pending_assignment': 0,
            'assigned': 0,
            'pending_onboarding': 0,
            'onboarded': 0,
            'approved': 0,
            'rejected': 0,
            'total': 0
        }
        
        for status, count in result:
            if status:
                status_key = status.lower()
                if status_key in stats:
                    stats[status_key] = count
                stats['total'] += count
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting onboarding stats: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve onboarding statistics", 500)


@onboarding_bp.route('/candidate/<int:candidate_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate_onboarding_details(candidate_id):
    """
    Get detailed onboarding information for a specific candidate.
    
    Path Parameters:
        candidate_id: Candidate ID
    
    Returns: CandidateOnboardingInfoSchema
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        from app.models import Candidate
        from app import db
        from sqlalchemy import select
        
        # Get candidate with related users
        query = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id
        )
        
        candidate = db.session.scalar(query)
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        # Build response with related user info
        response = {
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'email': candidate.email,
            'phone': candidate.phone,
            'onboarding_status': candidate.onboarding_status,
            'manager_id': candidate.manager_id,
            'recruiter_id': candidate.recruiter_id,
            'onboarded_by_user_id': candidate.onboarded_by_user_id,
            'onboarded_at': candidate.onboarded_at.isoformat() if candidate.onboarded_at else None,
            'approved_by_user_id': candidate.approved_by_user_id,
            'approved_at': candidate.approved_at.isoformat() if candidate.approved_at else None,
            'rejected_by_user_id': candidate.rejected_by_user_id,
            'rejected_at': candidate.rejected_at.isoformat() if candidate.rejected_at else None,
            'rejection_reason': candidate.rejection_reason,
            'created_at': candidate.created_at.isoformat(),
            'updated_at': candidate.updated_at.isoformat()
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting candidate onboarding details: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve candidate details", 500)
