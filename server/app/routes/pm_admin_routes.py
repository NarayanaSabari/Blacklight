"""PM Admin API routes - Platform Management operations."""

from flask import Blueprint, jsonify, request
from app import db
from app.services import PMAdminService, PMAdminAuthService
from app.middleware import require_pm_admin
from app.schemas.pm_admin_schema import (
    PMAdminUserCreateSchema,
    PMAdminUserUpdateSchema,
    PMAdminLoginSchema,
    ResetTenantAdminPasswordSchema,
)

bp = Blueprint("pm_admin", __name__, url_prefix="/api/pm-admin")


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


def get_current_admin() -> dict:
    """
    Get current authenticated PM admin from request context.
    This will be set by PM admin middleware.
    """
    return getattr(request, "pm_admin", {})


def get_changed_by() -> str:
    """
    Get changed_by identifier from request context.
    Format: "pm_admin:123"
    """
    admin = get_current_admin()
    admin_id = admin.get("user_id", "unknown")
    return f"pm_admin:{admin_id}"


# === Authentication Endpoints ===


@bp.route("/auth/debug-admin", methods=["GET"])
def debug_admin():
    """Debug endpoint to check admin user in database."""
    from app.models import PMAdminUser
    from sqlalchemy import select
    
    admin = db.session.scalar(select(PMAdminUser).where(PMAdminUser.email == "admin@blacklight.com"))
    
    if not admin:
        return jsonify({"error": "No admin found with email admin@blacklight.com"}), 404
    
    return jsonify({
        "id": admin.id,
        "email": admin.email,
        "first_name": admin.first_name,
        "last_name": admin.last_name,
        "is_active": admin.is_active,
        "password_hash_length": len(admin.password_hash) if admin.password_hash else 0,
        "password_hash_starts_with": admin.password_hash[:10] if admin.password_hash else None,
        "failed_attempts": admin.failed_login_attempts,
        "is_locked": admin.is_locked,
    }), 200


@bp.route("/auth/fix-admin-password", methods=["POST"])
def fix_admin_password():
    """Fix admin password by resetting to bcrypt hash."""
    import bcrypt
    from app.models import PMAdminUser
    from sqlalchemy import select
    
    admin = db.session.scalar(select(PMAdminUser).where(PMAdminUser.email == "admin@blacklight.com"))
    
    if not admin:
        return jsonify({"error": "No admin found"}), 404
    
    # Set password to Admin@123 with bcrypt
    password = "Admin@123"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    admin.password_hash = password_hash
    admin.failed_login_attempts = 0
    admin.locked_until = None
    
    db.session.commit()
    
    return jsonify({
        "message": "Password reset successfully",
        "email": admin.email,
        "new_password_hash_starts_with": password_hash[:10],
    }), 200


@bp.route("/auth/login", methods=["POST"])
def login():
    """
    Login PM admin (no authentication required).
    
    Request body: PMAdminLoginSchema
    
    Returns:
        200: Login successful with tokens
        401: Invalid credentials, account locked, or inactive
    """
    try:
        data = PMAdminLoginSchema.model_validate(request.get_json())

        result = PMAdminAuthService.login(data.email, data.password)

        return jsonify(result.model_dump()), 200

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/auth/logout", methods=["POST"])
@require_pm_admin
def logout():
    """
    Logout PM admin (requires authentication).
    
    Headers:
        - Authorization: Bearer <access_token>
    
    Returns:
        200: Logout successful
    """
    try:
        admin = get_current_admin()
        admin_id = admin.get("user_id")

        # Get access token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        access_token = auth_header.replace("Bearer ", "").strip()

        result = PMAdminAuthService.logout(admin_id, access_token)

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

        result = PMAdminAuthService.refresh_token(refresh_token)

        return jsonify(result.model_dump()), 200

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/current", methods=["GET"])
@require_pm_admin
def get_current_admin_route():
    """
    Get current authenticated PM admin user details.
    
    Requires: PM Admin authentication
    
    Returns:
        200: Current admin user details
        401: Not authenticated
    """
    try:
        admin_id = request.pm_admin.get("user_id")
        admin = PMAdminService.get_admin(admin_id)
        
        return jsonify(admin.model_dump()), 200
    
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


# === PM Admin Management Endpoints ===


@bp.route("/admins", methods=["POST"])
@require_pm_admin
def create_admin():
    """
    Create a new PM admin user.
    
    Requires: PM Admin authentication
    
    Request body: PMAdminUserCreateSchema
    
    Returns:
        201: Created admin
        400: Validation error
    """
    try:
        data = PMAdminUserCreateSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        admin = PMAdminService.create_admin(data, changed_by)

        return jsonify(admin.model_dump()), 201

    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/admins", methods=["GET"])
@require_pm_admin
def list_admins():
    """
    List all PM admin users.
    
    Requires: PM Admin authentication
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - search: Search in email, first_name, last_name
        - is_active: Filter by active status (true/false)
    
    Returns:
        200: List of admins with pagination
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search")
        is_active_str = request.args.get("is_active")

        # Parse is_active boolean
        is_active = None
        if is_active_str:
            is_active = is_active_str.lower() == "true"

        result = PMAdminService.list_admins(
            page=page,
            per_page=per_page,
            search=search,
            is_active=is_active,
        )

        return jsonify(result.model_dump()), 200

    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/admins/<int:admin_id>", methods=["GET"])
@require_pm_admin
def get_admin(admin_id: int):
    """
    Get PM admin by ID.
    
    Requires: PM Admin authentication
    
    Path params:
        - admin_id: Admin ID
    
    Returns:
        200: Admin details
        404: Admin not found
    """
    try:
        admin = PMAdminService.get_admin(admin_id)

        return jsonify(admin.model_dump()), 200

    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/admins/<int:admin_id>", methods=["PATCH"])
@require_pm_admin
def update_admin(admin_id: int):
    """
    Update PM admin.
    
    Requires: PM Admin authentication
    
    Path params:
        - admin_id: Admin ID
    
    Request body: PMAdminUserUpdateSchema
    
    Returns:
        200: Updated admin
        400: Validation error
        404: Admin not found
    """
    try:
        data = PMAdminUserUpdateSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        admin = PMAdminService.update_admin(admin_id, data, changed_by)

        return jsonify(admin.model_dump()), 200

    except ValueError as e:
        status = 404 if "not found" in str(e).lower() else 400
        return error_response(str(e), status)
    except Exception as e:
        return error_response(str(e), 500)


# === Special PM Admin Privilege Endpoints ===


@bp.route("/reset-tenant-admin-password", methods=["POST"])
@require_pm_admin
def reset_tenant_admin_password():
    """
    Reset a tenant admin's password (PM Admin privilege).
    
    Requires: PM Admin authentication
    
    Request body: ResetTenantAdminPasswordSchema
    
    Returns:
        200: Password reset successful
        400: User not found or not TENANT_ADMIN
    """
    try:
        data = ResetTenantAdminPasswordSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        result = PMAdminService.reset_tenant_admin_password(data, changed_by)

        return jsonify(result), 200

    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)
