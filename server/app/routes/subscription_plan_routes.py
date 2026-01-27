"""Subscription Plan API routes."""

from typing import Optional
from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from app.services import SubscriptionPlanService
from app.middleware import require_pm_admin
from app.schemas.subscription_plan_schema import (
    CustomPlanCreateSchema,
    CustomPlanUpdateSchema,
)

bp = Blueprint("subscription_plans", __name__, url_prefix="/api/subscription-plans")


def error_response(message: str, status: int = 400, details: Optional[dict] = None):
    """Helper to create error responses."""
    response = {
        "error": "Error",
        "message": message,
        "status": status,
    }
    if details:
        response["details"] = details
    return jsonify(response), status


@bp.route("", methods=["GET"])
@require_pm_admin
def list_plans():
    """
    List all subscription plans.
    
    Requires: PM Admin authentication
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - include_inactive: Include inactive plans (default: false)
    
    Returns:
        200: List of subscription plans with pagination
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        include_inactive = request.args.get("include_inactive", "false").lower() == "true"

        result = SubscriptionPlanService.list_plans(
            page=page,
            per_page=per_page,
            include_inactive=include_inactive,
        )

        # Return in the format expected by frontend: { plans: [...] }
        return jsonify({
            "plans": [plan.model_dump() for plan in result.items],
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
        }), 200

    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<int:plan_id>", methods=["GET"])
@require_pm_admin
def get_plan(plan_id: int):
    """
    Get a subscription plan by ID.
    
    Requires: PM Admin authentication
    
    Path params:
        - plan_id: Subscription plan ID
    
    Returns:
        200: Subscription plan details
        404: Plan not found
    """
    try:
        plan = SubscriptionPlanService.get_plan(plan_id)
        return jsonify({"plan": plan.model_dump()}), 200

    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<int:plan_id>/usage", methods=["GET"])
@require_pm_admin
def get_plan_usage(plan_id: int):
    """
    Get subscription plan usage statistics.
    
    Requires: PM Admin authentication
    
    Path params:
        - plan_id: Subscription plan ID
    
    Returns:
        200: Plan details with tenant counts
        404: Plan not found
    """
    try:
        usage = SubscriptionPlanService.get_plan_usage(plan_id)
        return jsonify(usage.model_dump()), 200

    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/custom", methods=["POST"])
@require_pm_admin
def create_custom_plan():
    try:
        data = CustomPlanCreateSchema.model_validate(request.get_json())
    except ValidationError as e:
        return error_response("Validation failed", 400, e.errors())
    
    try:
        plan = SubscriptionPlanService.create_custom_plan(
            tenant_id=data.tenant_id,
            plan_data=data,
            created_by="pm_admin"
        )
        return jsonify({"plan": plan.model_dump()}), 201
    
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<int:plan_id>", methods=["PUT"])
@require_pm_admin
def update_custom_plan(plan_id: int):
    try:
        data = CustomPlanUpdateSchema.model_validate(request.get_json())
    except ValidationError as e:
        return error_response("Validation failed", 400, e.errors())
    
    try:
        plan = SubscriptionPlanService.update_custom_plan(
            plan_id=plan_id,
            updates=data,
            updated_by="pm_admin"
        )
        return jsonify({"plan": plan.model_dump()}), 200
    
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/<int:plan_id>", methods=["DELETE"])
@require_pm_admin
def delete_custom_plan(plan_id: int):
    try:
        SubscriptionPlanService.delete_custom_plan(
            plan_id=plan_id,
            deleted_by="pm_admin"
        )
        return '', 204
    
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/tenants/<int:tenant_id>/available", methods=["GET"])
@require_pm_admin
def get_available_plans_for_tenant(tenant_id: int):
    try:
        include_inactive = request.args.get("include_inactive", "false").lower() == "true"
        
        plans = SubscriptionPlanService.list_plans_for_tenant(
            tenant_id=tenant_id,
            include_inactive=include_inactive
        )
        return jsonify({"plans": [plan.model_dump() for plan in plans]}), 200
    
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)
