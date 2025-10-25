"""Subscription Plan API routes."""

from flask import Blueprint, jsonify, request
from app.services import SubscriptionPlanService
from app.middleware import require_pm_admin

bp = Blueprint("subscription_plans", __name__, url_prefix="/api/subscription-plans")


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
