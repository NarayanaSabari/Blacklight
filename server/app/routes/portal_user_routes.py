"""Portal User API routes - Requires Portal authentication."""

from flask import Blueprint, jsonify, request
from app.services import PortalUserService, PortalAuthService
from app.middleware.portal_auth import require_portal_auth, require_tenant_admin, require_permission
from app.schemas.portal_user_schema import (
    PortalUserCreateSchema,
    PortalUserUpdateSchema,
    PortalUserResetPasswordSchema,
    PortalLoginSchema,
    UserRoleAssignmentSchema,
)

bp = Blueprint("portal_users", __name__, url_prefix="/api/portal")


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses."""
    response = {
        "error": "Error",
        "message": message,
        "status": status,
    }
    if details:
        response["details"] = details
    return jsonify(response), status


def get_current_user() -> dict:
    """
    Get current authenticated portal user from request context.
    This will be set by portal auth middleware.
    """
    return getattr(request, "portal_user", {})


def get_changed_by() -> str:
    """
    Get changed_by identifier from request context.
    Format: "portal_user:123"
    """
    user = get_current_user()
    user_id = user.get("user_id", "unknown")
    return f"portal_user:{user_id}"


# === Authentication Endpoints ===


@bp.route("/auth/login", methods=["POST"])
def login():
    """
    Login portal user (no authentication required).
    
    Request body: PortalLoginSchema
    
    Returns:
        200: Login successful with tokens
        401: Invalid credentials or account inactive
    """
    try:
        data = PortalLoginSchema.model_validate(request.get_json())

        result = PortalAuthService.login(data.email, data.password)

        return jsonify(result.model_dump()), 200

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/auth/logout", methods=["POST"])
@require_portal_auth
def logout():
    """
    Logout portal user (requires authentication).
    
    Headers:
        - Authorization: Bearer <access_token>
    
    Returns:
        200: Logout successful
    """
    try:
        user = get_current_user()
        user_id = user.get("user_id")

        # Get access token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        access_token = auth_header.replace("Bearer ", "").strip()

        result = PortalAuthService.logout(user_id, access_token)

        return jsonify(result), 200

    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/auth/refresh", methods=["POST"])
def refresh_token():
    """
    Refresh access token using refresh token (no authentication required).
    
    Request body:
        - refresh_token: JWT refresh token
    
    Returns:
        200: New access token
        401: Invalid or expired refresh token
    """
    try:
        data = request.get_json()
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            return error_response("refresh_token is required", 400)

        result = PortalAuthService.refresh_token(refresh_token)

        return jsonify(result.model_dump()), 200

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        return error_response(str(e), 500)


# === User Management Endpoints (Require TENANT_ADMIN) ===


@bp.route("/users", methods=["POST"])
@require_tenant_admin
@require_permission('users.create')
def create_user():
    """
    Create a new portal user within tenant.
    
    Requires: Portal authentication (TENANT_ADMIN only)
    
    Request body: PortalUserCreateSchema
    
    Returns:
        201: Created user
        400: Validation error or limit exceeded
        403: Not authorized (not TENANT_ADMIN)
    """
    try:
        current_user = get_current_user()
        current_user_id = current_user.get("user_id")

        data = PortalUserCreateSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        user = PortalUserService.create_user(data, current_user_id, changed_by)

        return jsonify(user.model_dump()), 201

    except ValueError as e:
        # Check if it's a permission error
        if "TENANT_ADMIN" in str(e):
            return error_response(str(e), 403)
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/users", methods=["GET"])
@require_portal_auth
@require_permission('users.view')
def list_users():
    """
    List portal users within current tenant.
    
    Requires: Portal authentication
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - search: Search in email, first_name, last_name
        - role: Filter by role (TENANT_ADMIN, RECRUITER, MANAGER, TEAM_LEAD)
        - is_active: Filter by active status (true/false)
    
    Returns:
        200: List of users with pagination
    """
    try:
        current_user = get_current_user()
        tenant_id = current_user.get("tenant_id")

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search")
        role_id_str = request.args.get("role_id")
        is_active_str = request.args.get("is_active")

        # Parse role_id
        role_id = None
        if role_id_str:
            try:
                role_id = int(role_id_str)
            except ValueError:
                return error_response(f"Invalid role_id: {role_id_str}", 400)

        # Parse is_active boolean
        is_active = None
        if is_active_str:
            is_active = is_active_str.lower() == "true"

        result = PortalUserService.list_users(
            tenant_id=tenant_id,
            page=page,
            per_page=per_page,
            search=search,
            role_id=role_id,
            is_active=is_active,
        )

        return jsonify(result.model_dump()), 200

    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/users/<int:user_id>", methods=["GET"])
@require_portal_auth
@require_permission('users.view')
def get_user(user_id: int):
    """
    Get portal user by ID.
    
    Requires: Portal authentication (same tenant only)
    
    Path params:
        - user_id: User ID
    
    Returns:
        200: User details
        403: Access denied (different tenant)
        404: User not found
    """
    try:
        current_user = get_current_user()
        tenant_id = current_user.get("tenant_id")

        user = PortalUserService.get_user(user_id, requester_tenant_id=tenant_id)

        return jsonify(user.model_dump()), 200

    except ValueError as e:
        if "Access denied" in str(e):
            return error_response(str(e), 403)
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/users/<int:user_id>", methods=["PATCH"])
@require_tenant_admin
@require_permission('users.edit')
def update_user(user_id: int):
    """
    Update portal user.
    
    Requires: Portal authentication (TENANT_ADMIN only)
    
    Path params:
        - user_id: User ID
    
    Request body: PortalUserUpdateSchema
    
    Returns:
        200: Updated user
        400: Validation error
        403: Not authorized (not TENANT_ADMIN)
        404: User not found
    """
    try:
        current_user = get_current_user()
        current_user_id = current_user.get("user_id")

        data = PortalUserUpdateSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        user = PortalUserService.update_user(user_id, data, current_user_id, changed_by)

        return jsonify(user.model_dump()), 200

    except ValueError as e:
        if "TENANT_ADMIN" in str(e):
            return error_response(str(e), 403)
        elif "not found" in str(e).lower():
            return error_response(str(e), 404)
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_tenant_admin
@require_permission('users.delete')
def delete_user(user_id: int):
    """
    Delete portal user.
    
    Requires: Portal authentication (TENANT_ADMIN only)
    
    Path params:
        - user_id: User ID
    
    Returns:
        200: Deletion confirmation
        403: Not authorized (not TENANT_ADMIN or self-deletion)
        404: User not found
    """
    try:
        current_user = get_current_user()
        current_user_id = current_user.get("user_id")
        changed_by = get_changed_by()

        result = PortalUserService.delete_user(user_id, current_user_id, changed_by)

        return jsonify(result), 200

    except ValueError as e:
        if "TENANT_ADMIN" in str(e) or "Cannot delete your own" in str(e):
            return error_response(str(e), 403)
        elif "not found" in str(e).lower():
            return error_response(str(e), 404)
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@require_tenant_admin
@require_permission('users.reset_password')
def reset_password(user_id: int):
    """
    Reset portal user password.
    
    Requires: Portal authentication (TENANT_ADMIN only)
    
    Path params:
        - user_id: User ID
    
    Request body: PortalUserResetPasswordSchema
    
    Returns:
        200: Password reset successful
        403: Not authorized
        404: User not found
    """
    try:
        current_user = get_current_user()
        current_user_id = current_user.get("user_id")
        changed_by = get_changed_by()

        # Verify current user is TENANT_ADMIN
        current_user_obj = PortalUserService.get_user(current_user_id)
        if not current_user_obj.is_tenant_admin:
            return error_response("Only TENANT_ADMIN can reset passwords", 403)

        data = PortalUserResetPasswordSchema.model_validate(request.get_json())

        user = PortalUserService.reset_password(user_id, data, changed_by)

        return jsonify(user.model_dump()), 200

    except ValueError as e:
        if "not found" in str(e).lower():
            return error_response(str(e), 404)
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/users/<int:user_id>/roles", methods=["PUT"])
@require_tenant_admin
@require_permission('users.manage_roles')
def assign_user_roles(user_id: int):
    """
    Assign roles to a portal user.
    
    Requires: Portal authentication (TENANT_ADMIN only)
    
    Path params:
        - user_id: User ID
        
    Request body: UserRoleAssignmentSchema
    
    Returns:
        200: Updated user with assigned roles
        400: Validation error
        403: Not authorized (not TENANT_ADMIN or trying to assign roles from other tenants)
        404: User or role not found
    """
    try:
        current_user = get_current_user()
        changed_by = get_changed_by()
        requester_tenant_id = current_user.get("tenant_id")

        data = UserRoleAssignmentSchema.model_validate(request.get_json())

        user = PortalUserService.assign_roles_to_user(
            user_id=user_id,
            role_ids=data.role_ids,
            changed_by=changed_by,
            requester_tenant_id=requester_tenant_id
        )

        return jsonify(user.model_dump()), 200

    except ValueError as e:
        if "Access denied" in str(e) or "TENANT_ADMIN" in str(e):
            return error_response(str(e), 403)
        elif "not found" in str(e).lower():
            return error_response(str(e), 404)
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


# =============================================================================
# Tenant Settings - Document Requirements
# =============================================================================

@bp.route("/settings/document-requirements", methods=["GET"])
@require_portal_auth
@require_permission('settings.view')
def get_document_requirements():
    """
    Get document requirements for the current tenant.
    
    Requires: Portal authentication with settings.view permission
    
    Returns:
        200: List of document requirements
        404: Tenant not found
    """
    try:
        from app.services import TenantService
        
        current_user = get_current_user()
        tenant_id = current_user.get("tenant_id")
        
        requirements = TenantService.get_document_requirements(tenant_id)
        
        return jsonify({
            "requirements": requirements
        }), 200
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/settings/document-requirements", methods=["PUT"])
@require_portal_auth
@require_permission('settings.edit')
def update_document_requirements():
    """
    Update document requirements for the current tenant.
    
    Requires: Portal authentication with settings.edit permission
    
    Request body: {
        "requirements": [
            {
                "id": "uuid",
                "document_type": "id_proof",
                "label": "Government ID",
                "description": "Passport, Driver's License, or State ID",
                "is_required": true,
                "display_order": 1,
                "allowed_file_types": ["pdf", "jpg", "jpeg", "png"],
                "max_file_size_mb": 5
            }
        ]
    }
    
    Returns:
        200: Updated list of document requirements
        400: Validation error
        404: Tenant not found
    """
    try:
        from app.services import TenantService
        from app.schemas.tenant_schema import DocumentRequirementsUpdateSchema
        
        current_user = get_current_user()
        tenant_id = current_user.get("tenant_id")
        changed_by = get_changed_by()
        
        # Validate request body
        data = DocumentRequirementsUpdateSchema.model_validate(request.get_json())
        
        # Convert Pydantic models to dicts for storage
        requirements_dicts = [req.model_dump() for req in data.requirements]
        
        updated_requirements = TenantService.update_document_requirements(
            tenant_id=tenant_id,
            requirements=requirements_dicts,
            changed_by=changed_by
        )
        
        return jsonify({
            "message": "Document requirements updated successfully",
            "requirements": updated_requirements
        }), 200
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)
