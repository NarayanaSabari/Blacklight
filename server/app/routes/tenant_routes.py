"""Tenant API routes - Requires PM Admin authentication."""

from flask import Blueprint, jsonify, request
from app.services import TenantService, PortalUserService
from app.middleware import require_pm_admin
from app.schemas.tenant_schema import (
    TenantCreateSchema,
    TenantUpdateSchema,
    TenantChangePlanSchema,
    TenantSuspendSchema,
    TenantFilterSchema,
    TenantDeleteSchema,
)

bp = Blueprint("tenants", __name__, url_prefix="/api/tenants")


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


def get_changed_by() -> str:
    """
    Get changed_by identifier from request context.
    This will be set by PM Admin middleware.
    Format: "pm_admin:123"
    """
    # This will be set by middleware after we implement it
    pm_admin = getattr(request, "pm_admin", None)
    if pm_admin:
        return f"pm_admin:{pm_admin.get('user_id')}"
    return "pm_admin:unknown"


@bp.route("", methods=["POST"])
@require_pm_admin
def create_tenant():
    """
    Create a new tenant with tenant admin user.
    
    Requires: PM Admin authentication
    
    Request body: TenantCreateSchema
    
    Returns:
        201: Created tenant
        400: Validation error
        409: Slug or email already exists
    """
    try:
        data = TenantCreateSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        tenant = TenantService.create_tenant(data, changed_by)

        return jsonify({
            "tenant": tenant.model_dump(),
            "message": "Tenant created successfully"
        }), 201

    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("", methods=["GET"])
@require_pm_admin
def list_tenants():
    """
    List all tenants with filtering and pagination.
    
    Requires: PM Admin authentication
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - status: Filter by status (ACTIVE, SUSPENDED, INACTIVE)
        - subscription_plan_id: Filter by plan ID
        - search: Search in company_name, slug, billing_email
    
    Returns:
        200: List of tenants with pagination
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        # Build filters
        filters_data = {}
        if request.args.get("status"):
            filters_data["status"] = request.args.get("status")
        if request.args.get("subscription_plan_id"):
            filters_data["subscription_plan_id"] = request.args.get(
                "subscription_plan_id", type=int
            )
        if request.args.get("search"):
            filters_data["search"] = request.args.get("search")

        filters = TenantFilterSchema.model_validate(filters_data) if filters_data else None

        result = TenantService.list_tenants(
            filters=filters,
            page=page,
            per_page=per_page,
        )

        return jsonify(result.model_dump()), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)


# ============================================================================
# SPECIFIC SUB-RESOURCE ROUTES - Must be defined BEFORE generic routes
# ============================================================================


@bp.route("/<string:identifier>/stats", methods=["GET"])
@require_pm_admin
def get_tenant_stats(identifier: str):
    """
    Get tenant resource usage statistics.
    
    Requires: PM Admin authentication
    
    Path params:
        - identifier: Tenant ID (integer) or slug (string)
    
    Returns:
        200: Usage statistics
        404: Tenant not found
    """
    try:
        # Convert identifier to int if possible
        try:
            tenant_id = int(identifier)
        except ValueError:
            # Get tenant by slug first to get ID
            tenant = TenantService.get_tenant(identifier)
            tenant_id = tenant.id

        stats = TenantService.get_usage_stats(tenant_id)

        return jsonify(stats.model_dump()), 200

    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<string:identifier>/users", methods=["GET"])
@require_pm_admin
def get_tenant_users(identifier: str):
    """
    Get all users for a specific tenant.
    
    Requires: PM Admin authentication
    
    Path params:
        - identifier: Tenant ID (integer) or slug (string)
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - search: Search in email, first_name, last_name
        - role_id: Filter by role ID
        - is_active: Filter by active status (true/false)
    
    Returns:
        200: List of tenant users with pagination
        404: Tenant not found
    """
    try:
        # Convert identifier to int if possible
        try:
            tenant_id = int(identifier)
        except ValueError:
            # Get tenant by slug first to get ID
            tenant = TenantService.get_tenant(identifier)
            tenant_id = tenant.id
        
        # Get query params
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
        
        # Get users from PortalUserService
        result = PortalUserService.list_users(
            tenant_id=tenant_id,
            page=page,
            per_page=per_page,
            search=search,
            role_id=role_id,
            is_active=is_active,
        )
        
        return jsonify(result.model_dump()), 200
    
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)


@bp.route("/<string:identifier>/change-plan", methods=["POST"])
@require_pm_admin
def change_subscription_plan(identifier: str):
    """
    Change tenant's subscription plan.
    
    Requires: PM Admin authentication
    
    Path params:
        - identifier: Tenant ID (integer) or slug (string)
    
    Request body: TenantChangePlanSchema
    
    Returns:
        200: Updated tenant
        400: Validation error or limit exceeded
        404: Tenant or plan not found
    """
    try:
        data = TenantChangePlanSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        # Convert identifier to int if possible
        try:
            tenant_id = int(identifier)
        except ValueError:
            # Get tenant by slug first to get ID
            tenant = TenantService.get_tenant(identifier)
            tenant_id = tenant.id

        tenant = TenantService.change_subscription_plan(tenant_id, data, changed_by)

        return jsonify({
            "tenant": tenant.model_dump(),
            "message": "Subscription plan changed successfully"
        }), 200

    except ValueError as e:
        status = 404 if "not found" in str(e).lower() else 400
        return error_response(str(e), status)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<string:identifier>/suspend", methods=["POST"])
@require_pm_admin
def suspend_tenant(identifier: str):
    """
    Suspend a tenant (disables all portal user access).
    
    Requires: PM Admin authentication
    
    Path params:
        - identifier: Tenant ID (integer) or slug (string)
    
    Request body: TenantSuspendSchema
    
    Returns:
        200: Suspended tenant
        400: Already suspended
        404: Tenant not found
    """
    try:
        data = TenantSuspendSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        # Convert identifier to int if possible
        try:
            tenant_id = int(identifier)
        except ValueError:
            # Get tenant by slug first to get ID
            tenant = TenantService.get_tenant(identifier)
            tenant_id = tenant.id

        tenant = TenantService.suspend_tenant(tenant_id, data, changed_by)

        return jsonify({
            "tenant": tenant.model_dump(),
            "message": "Tenant suspended successfully"
        }), 200

    except ValueError as e:
        status = 404 if "not found" in str(e).lower() else 400
        return error_response(str(e), status)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<string:identifier>/activate", methods=["POST"])
@require_pm_admin
def reactivate_tenant(identifier: str):
    """
    Reactivate a suspended tenant.
    
    Requires: PM Admin authentication
    
    Path params:
        - identifier: Tenant ID (integer) or slug (string)
    
    Returns:
        200: Reactivated tenant
        400: Not suspended
        404: Tenant not found
    """
    try:
        changed_by = get_changed_by()

        # Convert identifier to int if possible
        try:
            tenant_id = int(identifier)
        except ValueError:
            # Get tenant by slug first to get ID
            tenant = TenantService.get_tenant(identifier)
            tenant_id = tenant.id

        tenant = TenantService.reactivate_tenant(tenant_id, changed_by)

        return jsonify({
            "tenant": tenant.model_dump(),
            "message": "Tenant activated successfully"
        }), 200

    except ValueError as e:
        status = 404 if "not found" in str(e).lower() else 400
        return error_response(str(e), status)
    except Exception as e:
        return error_response(str(e), 500)


# ============================================================================
# GENERIC IDENTIFIER ROUTES - Must be defined AFTER specific routes
# ============================================================================


@bp.route("/<string:identifier>", methods=["GET"])
@require_pm_admin
def get_tenant(identifier: str):
    """
    Get tenant by ID or slug.
    
    Requires: PM Admin authentication
    
    Path params:
        - identifier: Tenant ID (integer) or slug (string)
    
    Returns:
        200: Tenant details
        404: Tenant not found
    """
    try:
        # Try to parse as integer ID first
        try:
            tenant_id = int(identifier)
            tenant = TenantService.get_tenant(tenant_id)
        except ValueError:
            # Not an integer, treat as slug
            tenant = TenantService.get_tenant(identifier)
        
        return jsonify({"tenant": tenant.model_dump()}), 200

    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<string:identifier>", methods=["PUT"])
@require_pm_admin
def update_tenant(identifier: str):
    """
    Update tenant by ID or slug.
    
    Requires: PM Admin authentication
    
    Path params:
        - identifier: Tenant ID (integer) or slug (string)
    
    Request body: TenantUpdateSchema
    
    Returns:
        200: Updated tenant
        400: Validation error
        404: Tenant not found
    """
    try:
        data = TenantUpdateSchema.model_validate(request.get_json())
        changed_by = get_changed_by()

        # Convert identifier to int if possible
        try:
            tenant_id = int(identifier)
        except ValueError:
            # Get tenant by slug first to get ID
            tenant = TenantService.get_tenant(identifier)
            tenant_id = tenant.id

        tenant = TenantService.update_tenant(tenant_id, data, changed_by)

        return jsonify({
            "tenant": tenant.model_dump(),
            "message": "Tenant updated successfully"
        }), 200

    except ValueError as e:
        status = 404 if "not found" in str(e).lower() else 400
        return error_response(str(e), status)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<string:identifier>", methods=["DELETE"])
@require_pm_admin
def delete_tenant(identifier: str):
    """
    Delete a tenant.

    Requires: PM Admin authentication

    Path params:
        - identifier: Tenant ID (integer) or slug (string)

    Request body: TenantDeleteSchema

    Returns:
        200: Deletion confirmation
        400: Validation error
        404: Tenant not found
    """
    try:
        # Get JSON body - force parsing even for DELETE
        json_data = request.get_json(force=True, silent=True) or {}
        data = TenantDeleteSchema.model_validate(json_data)
        changed_by = get_changed_by()

        # Convert identifier to int if possible
        try:
            tenant_id = int(identifier)
        except ValueError:
            # Get tenant by slug first to get ID
            tenant = TenantService.get_tenant(identifier)
            tenant_id = tenant.id

        result = TenantService.delete_tenant(tenant_id, data, changed_by)

        return jsonify(result), 200

    except ValueError as e:
        status = 404 if "not found" in str(e).lower() else 400
        return error_response(str(e), status)
    except Exception as e:
        return error_response(str(e), 500)

