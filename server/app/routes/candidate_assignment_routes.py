"""Candidate Assignment routes for managing candidate assignments and notifications."""

from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
import logging

from app import db
from app.models import PortalUser
from app.services import CandidateAssignmentService, AuditLogService
from app.schemas import (
    AssignCandidateSchema,
    ReassignCandidateSchema,
    UnassignCandidateSchema,
    MarkNotificationReadSchema,
    AssignCandidateResponseSchema,
    ReassignCandidateResponseSchema,
    UnassignCandidateResponseSchema,
    AssignmentHistoryResponseSchema,
    UserAssignedCandidatesResponseSchema,
    CandidateAssignmentsResponseSchema,
    NotificationsResponseSchema,
)
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context

logger = logging.getLogger(__name__)

assignment_bp = Blueprint('candidate_assignment', __name__, url_prefix='/api/candidates/assignments')


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses."""
    return jsonify({
        'error': 'Error',
        'message': message,
        'status': status,
        'details': details or {}
    }), status


# ==================== Assignment Management Endpoints ====================

@assignment_bp.route('/assign', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.assign')
def assign_candidate():
    """
    Assign a candidate to a recruiter or manager.
    
    Request Body: AssignCandidateSchema
    Returns: AssignCandidateResponseSchema
    Permissions: candidates.assign (HIRING_MANAGER, MANAGER)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = AssignCandidateSchema.model_validate(request.get_json())
        
        # Assign candidate
        result = CandidateAssignmentService.assign_candidate(
            candidate_id=data.candidate_id,
            assigned_to_user_id=data.assigned_to_user_id,
            assigned_by_user_id=user_id,
            assignment_reason=data.assignment_reason,
            changed_by=f"portal_user:{user_id}",
            tenant_id=tenant_id
        )
        
        logger.info(f"Candidate {data.candidate_id} assigned to user {data.assigned_to_user_id} by user {user_id}")
        
        return jsonify(result), 201
        
    except ValidationError as e:
        logger.warning(f"Validation error in assign_candidate: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in assign_candidate: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error assigning candidate: {str(e)}", exc_info=True)
        return error_response("Failed to assign candidate", 500)


@assignment_bp.route('/reassign', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.assign')
def reassign_candidate():
    """
    Reassign a candidate from current assignee to a new assignee.
    
    Request Body: ReassignCandidateSchema
    Returns: ReassignCandidateResponseSchema
    Permissions: candidates.assign (HIRING_MANAGER, MANAGER)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = ReassignCandidateSchema.model_validate(request.get_json())
        
        # Reassign candidate
        result = CandidateAssignmentService.reassign_candidate(
            candidate_id=data.candidate_id,
            new_assigned_to_user_id=data.new_assigned_to_user_id,
            assigned_by_user_id=user_id,
            assignment_reason=data.assignment_reason,
            changed_by=f"portal_user:{user_id}"
        )
        
        logger.info(f"Candidate {data.candidate_id} reassigned to user {data.new_assigned_to_user_id} by user {user_id}")
        
        return jsonify(result), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in reassign_candidate: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in reassign_candidate: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error reassigning candidate: {str(e)}", exc_info=True)
        return error_response("Failed to reassign candidate", 500)


@assignment_bp.route('/unassign', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.assign')
def unassign_candidate():
    """
    Unassign a candidate from their current assignee.
    
    Request Body: UnassignCandidateSchema
    Returns: UnassignCandidateResponseSchema
    Permissions: candidates.assign (HIRING_MANAGER, MANAGER)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = UnassignCandidateSchema.model_validate(request.get_json())
        
        # Unassign candidate
        result = CandidateAssignmentService.unassign_candidate(
            candidate_id=data.candidate_id,
            unassigned_by_user_id=user_id,
            changed_by=f"portal_user:{user_id}",
            tenant_id=tenant_id
        )
        
        logger.info(f"Candidate {data.candidate_id} unassigned by user {user_id}")
        
        return jsonify(result), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in unassign_candidate: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in unassign_candidate: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error unassigning candidate: {str(e)}", exc_info=True)
        return error_response("Failed to unassign candidate", 500)


# ==================== Assignment Query Endpoints ====================

@assignment_bp.route('/candidate/<int:candidate_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate_assignments(candidate_id):
    """
    Get assignment history for a specific candidate.
    
    Path Parameters:
        candidate_id: Candidate ID
    
    Query Parameters:
        include_notifications (optional): Include related notifications (default: false)
    
    Returns: List of assignments
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        include_notifications = request.args.get('include_notifications', 'false').lower() == 'true'
        
        assignments = CandidateAssignmentService.get_candidate_assignments(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            include_notifications=include_notifications
        )
        
        return jsonify({
            'assignments': assignments,
            'total': len(assignments),
            'candidate_id': candidate_id
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_candidate_assignments: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting candidate assignments: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve candidate assignments", 500)


@assignment_bp.route('/my-candidates', methods=['GET'])
@require_portal_auth
@with_tenant_context
def get_my_assigned_candidates():
    """
    Get candidates assigned to the current user.
    
    Query Parameters:
        status (optional): Filter by assignment status (PENDING, ACCEPTED, COMPLETED, CANCELLED)
        include_completed (optional): Include completed assignments (default: false)
    
    Returns: List of assigned candidates
    Permissions: candidates.view OR candidates.view_assigned
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Get user and check permissions
        user = db.session.get(PortalUser, user_id)
        if not user:
            return error_response("User not found", 404)
            
        has_permission = (
            user.has_permission('candidates.view') or 
            user.has_permission('candidates.view_assigned')
        )
        
        if not has_permission:
            return error_response(
                "Access denied: 'candidates.view' or 'candidates.view_assigned' permission required",
                403
            )
        
        status = request.args.get('status')
        include_completed = request.args.get('include_completed', 'false').lower() == 'true'
        
        candidates = CandidateAssignmentService.get_user_assigned_candidates(
            user_id=user_id,
            tenant_id=tenant_id,
            status_filter=status,
            include_completed=include_completed
        )
        
        return jsonify({
            'candidates': candidates,
            'total': len(candidates),
            'user_id': user_id,
            'filters': {
                'status': status,
                'include_completed': include_completed
            }
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_my_assigned_candidates: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting assigned candidates: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve assigned candidates", 500)


@assignment_bp.route('/history', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view_all')
def get_assignment_history():
    """
    Get recent assignment history for the tenant.
    
    Query Parameters:
        limit (optional): Maximum number of records to return (default: 50, max: 100)
        assigned_to_user_id (optional): Filter by assigned user
        assigned_by_user_id (optional): Filter by assigning user
    
    Returns: List of recent assignments
    Permissions: candidates.view_all (HIRING_MANAGER only)
    """
    try:
        tenant_id = g.tenant_id
        
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # Cap at 100
        
        assigned_to_user_id = request.args.get('assigned_to_user_id', type=int)
        assigned_by_user_id = request.args.get('assigned_by_user_id', type=int)
        
        history = CandidateAssignmentService.get_assignment_history(
            tenant_id=tenant_id,
            limit=limit,
            assigned_to_user_id=assigned_to_user_id,
            assigned_by_user_id=assigned_by_user_id
        )
        
        return jsonify({
            'assignments': history,
            'total': len(history),
            'limit': limit
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_assignment_history: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting assignment history: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve assignment history", 500)


# ==================== Notification Endpoints ====================

@assignment_bp.route('/notifications', methods=['GET'])
@require_portal_auth
@with_tenant_context
def get_user_notifications():
    """
    Get assignment notifications for the current user.
    
    Query Parameters:
        unread_only (optional): Only return unread notifications (default: false)
        limit (optional): Maximum number of notifications to return (default: 20, max: 50)
    
    Returns: NotificationsResponseSchema
    Permissions: Authenticated user (any role)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 50)  # Cap at 50
        
        result = CandidateAssignmentService.get_user_notifications(
            user_id=user_id,
            tenant_id=tenant_id,
            unread_only=unread_only,
            limit=limit
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_user_notifications: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve notifications", 500)


@assignment_bp.route('/notifications/read', methods=['POST'])
@require_portal_auth
@with_tenant_context
def mark_notification_read():
    """
    Mark a notification as read.
    
    Request Body: MarkNotificationReadSchema
    Returns: Success message
    Permissions: Authenticated user (notification must belong to user)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = MarkNotificationReadSchema.model_validate(request.get_json())
        
        # Mark notification as read
        CandidateAssignmentService.mark_notification_as_read(
            notification_id=data.notification_id,
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        logger.info(f"Notification {data.notification_id} marked as read by user {user_id}")
        
        return jsonify({
            'message': 'Notification marked as read',
            'notification_id': data.notification_id
        }), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in mark_notification_read: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in mark_notification_read: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
        return error_response("Failed to mark notification as read", 500)


@assignment_bp.route('/notifications/mark-all-read', methods=['POST'])
@require_portal_auth
@with_tenant_context
def mark_all_notifications_read():
    """
    Mark all notifications as read for the current user.
    
    Returns: Count of notifications marked as read
    Permissions: Authenticated user (any role)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Get all unread notifications
        result = CandidateAssignmentService.get_user_notifications(
            user_id=user_id,
            tenant_id=tenant_id,
            unread_only=True,
            limit=1000  # Get all unread
        )
        
        # Mark each as read
        marked_count = 0
        for notification in result['notifications']:
            try:
                CandidateAssignmentService.mark_notification_as_read(
                    notification_id=notification['id'],
                    user_id=user_id,
                    tenant_id=tenant_id
                )
                marked_count += 1
            except Exception as e:
                logger.warning(f"Failed to mark notification {notification['id']} as read: {str(e)}")
        
        logger.info(f"User {user_id} marked {marked_count} notifications as read")
        
        return jsonify({
            'message': f'{marked_count} notifications marked as read',
            'count': marked_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}", exc_info=True)
        return error_response("Failed to mark notifications as read", 500)
