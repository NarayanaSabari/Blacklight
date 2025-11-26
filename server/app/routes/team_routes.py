"""Team Management routes for managing team hierarchy and manager assignments."""

from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
import logging

from app.services import TeamManagementService, AuditLogService
from app.schemas import (
    AssignManagerSchema,
    RemoveManagerSchema,
    AssignManagerResponseSchema,
    RemoveManagerResponseSchema,
    TeamHierarchyResponseSchema,
    AvailableManagersResponseSchema,
)
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context

logger = logging.getLogger(__name__)

team_bp = Blueprint('team', __name__, url_prefix='/api/team')


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses."""
    return jsonify({
        'error': 'Error',
        'message': message,
        'status': status,
        'details': details or {}
    }), status


# ==================== Team Hierarchy Endpoints ====================

@team_bp.route('/hierarchy', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('users.view_team')
def get_team_hierarchy():
    """
    Get complete team hierarchy for the tenant.
    
    Returns: TeamHierarchyResponseSchema
    Permissions: users.view_team
    """
    try:
        tenant_id = g.tenant_id
        
        hierarchy = TeamManagementService.get_team_hierarchy(tenant_id)
        
        return jsonify({
            'top_level_users': hierarchy,
            'total_users': sum(1 for _ in _flatten_hierarchy(hierarchy))
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_team_hierarchy: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting team hierarchy: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve team hierarchy", 500)


def _flatten_hierarchy(users):
    """Helper to flatten hierarchical user list."""
    for user in users:
        yield user
        if user.get('team_members'):
            yield from _flatten_hierarchy(user['team_members'])


@team_bp.route('/managers', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('users.view_team')
def get_managers_list():
    """
    Get list of all managers (users who have team members).
    
    Query Parameters:
        role_name (optional): Filter by role name (e.g., MANAGER, HIRING_MANAGER)
    
    Returns: List of managers with team member counts
    Permissions: users.view_team
    """
    try:
        tenant_id = g.tenant_id
        role_name = request.args.get('role_name')
        
        managers = TeamManagementService.get_managers_list(tenant_id, role_name)
        
        return jsonify({
            'managers': managers,
            'total': len(managers)
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_managers_list: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting managers list: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve managers list", 500)


@team_bp.route('/available-managers', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('users.assign_manager')
def get_available_managers():
    """
    Get list of users who can be assigned as managers.
    Respects role hierarchy - only returns managers who can manage the target user.
    
    Query Parameters:
        exclude_user_id (optional): User ID to exclude from list
        for_user_id (optional): Target user ID to filter by role hierarchy
    
    Returns: List of available managers
    Permissions: users.assign_manager
    """
    try:
        tenant_id = g.tenant_id
        exclude_user_id = request.args.get('exclude_user_id', type=int)
        for_user_id = request.args.get('for_user_id', type=int)
        
        managers = TeamManagementService.get_available_managers(
            tenant_id, 
            exclude_user_id,
            for_user_id
        )
        
        return jsonify({
            'managers': managers,
            'total': len(managers)
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_available_managers: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting available managers: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve available managers", 500)


@team_bp.route('/user/<int:user_id>/team-members', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('users.view_team')
def get_user_team_members(user_id):
    """
    Get team members for a specific manager.
    
    Path Parameters:
        user_id: Manager's user ID
    
    Query Parameters:
        include_indirect (optional): Include indirect reports (default: false)
    
    Returns: List of team members
    Permissions: users.view_team
    """
    try:
        tenant_id = g.tenant_id
        include_indirect = request.args.get('include_indirect', 'false').lower() == 'true'
        
        team_members = TeamManagementService.get_user_team_members(
            manager_id=user_id,
            tenant_id=tenant_id,
            include_indirect=include_indirect
        )
        
        return jsonify({
            'team_members': team_members,
            'total': len(team_members),
            'manager_id': user_id,
            'include_indirect': include_indirect
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_user_team_members: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting team members: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve team members", 500)


# ==================== Manager Assignment Endpoints ====================

@team_bp.route('/assign-manager', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('users.assign_manager')
def assign_manager():
    """
    Assign a manager to a user.
    
    Request Body: AssignManagerSchema
    Returns: AssignManagerResponseSchema
    Permissions: users.assign_manager (HIRING_MANAGER only)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = AssignManagerSchema.model_validate(request.get_json())
        
        # Assign manager
        result = TeamManagementService.assign_manager_to_user(
            user_id=data.user_id,
            manager_id=data.manager_id,
            assigned_by_user_id=user_id,
            changed_by=f"portal_user:{user_id}",
            tenant_id=tenant_id
        )
        
        logger.info(f"Manager assigned: User {data.user_id} -> Manager {data.manager_id} by user {user_id}")
        
        return jsonify(result), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in assign_manager: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in assign_manager: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error assigning manager: {str(e)}", exc_info=True)
        return error_response("Failed to assign manager", 500)


@team_bp.route('/remove-manager', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('users.assign_manager')
def remove_manager():
    """
    Remove manager assignment from a user.
    
    Request Body: RemoveManagerSchema
    Returns: RemoveManagerResponseSchema
    Permissions: users.assign_manager (HIRING_MANAGER only)
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request body
        data = RemoveManagerSchema.model_validate(request.get_json())
        
        # Remove manager
        result = TeamManagementService.remove_manager_assignment(
            user_id=data.user_id,
            removed_by_user_id=user_id,
            changed_by=f"portal_user:{user_id}"
        )
        
        logger.info(f"Manager removed from user {data.user_id} by user {user_id}")
        
        return jsonify(result), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in remove_manager: {str(e)}")
        return error_response("Invalid request data", 400, {'validation_errors': e.errors()})
    except ValueError as e:
        logger.warning(f"Business logic error in remove_manager: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error removing manager: {str(e)}", exc_info=True)
        return error_response("Failed to remove manager", 500)


# ==================== Hierarchical Team View Endpoints ====================

@team_bp.route('/my-team-members', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view_assigned')
def get_my_team_members():
    """
    Get current user's direct team members with candidate counts.
    Used for hierarchical "Your Candidates" view.
    
    Returns: List of team members with candidate and sub-team counts
    Permissions: candidates.view_assigned
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        team_members = TeamManagementService.get_hierarchical_team_members(
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        return jsonify({
            'team_members': team_members,
            'total': len(team_members)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting my team members: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve team members", 500)


@team_bp.route('/members/<int:member_id>/candidates', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view_assigned')
def get_team_member_candidates(member_id):
    """
    Get candidates assigned to a specific team member.
    
    Path Parameters:
        member_id: Team member's user ID
    
    Returns: List of candidates assigned to the team member
    Permissions: candidates.view_assigned
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Verify the requester has access to view this team member's candidates
        candidates = TeamManagementService.get_team_member_candidates(
            member_id=member_id,
            requester_id=user_id,
            tenant_id=tenant_id
        )
        
        return jsonify({
            'candidates': candidates,
            'total': len(candidates),
            'member_id': member_id
        }), 200
        
    except ValueError as e:
        logger.warning(f"Authorization error in get_team_member_candidates: {str(e)}")
        return error_response(str(e), 403)
    except Exception as e:
        logger.error(f"Error getting team member candidates: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve candidates", 500)


@team_bp.route('/<int:member_id>/team-members', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view_assigned')
def get_member_team_members(member_id):
    """
    Get a specific member's direct team members (for drill-down navigation).
    Used when drilling down into a manager's team in hierarchical view.
    
    Path Parameters:
        member_id: Member's user ID to get their team
    
    Returns: List of team members with candidate and sub-team counts
    Permissions: candidates.view_assigned
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Verify the requester has access to view this member's team
        # Use _is_in_hierarchy to check authorization
        from app.services import TeamManagementService
        
        # Check if requester is authorized
        if not TeamManagementService._is_in_hierarchy(user_id, member_id, tenant_id):
            return error_response("You do not have permission to view this member's team", 403)
        
        team_members = TeamManagementService.get_hierarchical_team_members(
            user_id=member_id,  # Get the specified member's team
            tenant_id=tenant_id
        )
        
        return jsonify({
            'team_members': team_members,
            'total': len(team_members)
        }), 200
        
    except ValueError as e:
        logger.warning(f"Authorization error in get_member_team_members: {str(e)}")
        return error_response(str(e), 403)
    except Exception as e:
        logger.error(f"Error getting member's team members: {str(e)}", exc_info=True)
        return error_response("Failed to retrieve team members", 500)
