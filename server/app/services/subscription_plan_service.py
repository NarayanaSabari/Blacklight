"""Subscription Plan Service - Read-only operations for subscription plans."""

from typing import Optional
from sqlalchemy import select, func
from app import db
from app.models import SubscriptionPlan, Tenant
from app.schemas.subscription_plan_schema import (
    SubscriptionPlanResponseSchema,
    SubscriptionPlanListResponseSchema,
    SubscriptionPlanUsageSchema,
)


class SubscriptionPlanService:
    """Service for subscription plan operations."""

    @staticmethod
    def get_plan(plan_id: int) -> SubscriptionPlanResponseSchema:
        """
        Get a subscription plan by ID.

        Args:
            plan_id: The plan ID to retrieve

        Returns:
            SubscriptionPlanResponseSchema with plan details

        Raises:
            ValueError: If plan not found
        """
        plan = db.session.get(SubscriptionPlan, plan_id)
        if not plan:
            raise ValueError(f"Subscription plan with ID {plan_id} not found")

        return SubscriptionPlanResponseSchema.model_validate(plan)

    @staticmethod
    def list_plans(
        page: int = 1,
        per_page: int = 20,
        include_inactive: bool = False,
    ) -> SubscriptionPlanListResponseSchema:
        """
        List all subscription plans with pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Number of items per page (max 100)
            include_inactive: Whether to include inactive plans

        Returns:
            SubscriptionPlanListResponseSchema with paginated plans
        """
        # Enforce max per_page
        if per_page > 100:
            per_page = 100

        # Build query
        query = select(SubscriptionPlan)

        # Filter out inactive plans unless requested
        if not include_inactive:
            query = query.where(SubscriptionPlan.is_active == True)

        # Order by sort_order, then name
        query = query.order_by(
            SubscriptionPlan.sort_order.asc(),
            SubscriptionPlan.name.asc(),
        )

        # Execute paginated query
        pagination = db.paginate(
            query,
            page=page,
            per_page=per_page,
            error_out=False,
        )

        # Convert to response schemas
        plans = [
            SubscriptionPlanResponseSchema.model_validate(plan)
            for plan in pagination.items
        ]

        return SubscriptionPlanListResponseSchema(
            items=plans,
            total=pagination.total,
            page=page,
            per_page=per_page,
        )

    @staticmethod
    def get_plan_usage(plan_id: int) -> SubscriptionPlanUsageSchema:
        """
        Get usage statistics for a subscription plan.

        Args:
            plan_id: The plan ID to get usage for

        Returns:
            SubscriptionPlanUsageSchema with usage stats

        Raises:
            ValueError: If plan not found
        """
        # Verify plan exists
        plan = db.session.get(SubscriptionPlan, plan_id)
        if not plan:
            raise ValueError(f"Subscription plan with ID {plan_id} not found")

        # Count active tenants on this plan
        active_tenants_count = db.session.scalar(
            select(func.count(Tenant.id))
            .where(Tenant.subscription_plan_id == plan_id)
            .where(Tenant.status == "ACTIVE")
        )

        # Count total tenants on this plan (all statuses)
        total_tenants_count = db.session.scalar(
            select(func.count(Tenant.id))
            .where(Tenant.subscription_plan_id == plan_id)
        )

        # Convert plan to response schema and add usage data
        plan_data = SubscriptionPlanResponseSchema.model_validate(plan)

        return SubscriptionPlanUsageSchema(
            plan=plan_data,
            active_tenants_count=active_tenants_count or 0,
            total_tenants_count=total_tenants_count or 0,
        )

    # NOTE: Create, Update, and Deactivate operations are intentionally NOT implemented
    # as per Phase 1 requirements. Subscription plans are seeded and considered
    # configuration data managed by system administrators through database migrations
    # or direct database operations, not through the API.
