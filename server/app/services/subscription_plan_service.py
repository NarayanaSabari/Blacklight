"""Subscription Plan Service - Read-only operations for subscription plans."""

from typing import Optional, List
from uuid import uuid4
from sqlalchemy import select, func
from app import db
from app.models import SubscriptionPlan, Tenant
from app.models.portal_user import PortalUser
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.schemas.subscription_plan_schema import (
    SubscriptionPlanResponseSchema,
    SubscriptionPlanListResponseSchema,
    SubscriptionPlanUsageSchema,
    CustomPlanCreateSchema,
    CustomPlanUpdateSchema,
    CustomPlanResponseSchema,
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
            total=pagination.total or 0,
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

    @staticmethod
    def create_custom_plan(
        tenant_id: int,
        plan_data: CustomPlanCreateSchema,
        created_by: str = "system"
    ) -> CustomPlanResponseSchema:
        """
        Create tenant-specific custom plan.
        
        Args:
            tenant_id: Tenant ID this custom plan is for
            plan_data: Custom plan creation data
            created_by: User who created the plan (for audit)
        
        Returns:
            CustomPlanResponseSchema with created plan details
        
        Raises:
            ValueError: If tenant not found or base plan invalid
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")
        
        base_plan = None
        if plan_data.base_plan_id:
            base_plan = db.session.get(SubscriptionPlan, plan_data.base_plan_id)
            if not base_plan:
                raise ValueError(f"Base plan with ID {plan_data.base_plan_id} not found")
            if base_plan.is_custom:
                raise ValueError("Cannot clone from another custom plan. Use standard plans only.")
        
        unique_name = f"{tenant.slug}_custom_{uuid4().hex[:8]}"
        
        if base_plan and not plan_data.features:
            features = base_plan.features.copy() if base_plan.features else {}
        else:
            features = plan_data.features or {}
        
        custom_plan = SubscriptionPlan(
            name=unique_name,
            display_name=plan_data.display_name,
            description=plan_data.description,
            price_monthly=plan_data.price_monthly,
            price_yearly=plan_data.price_yearly,
            max_users=plan_data.max_users,
            max_candidates=plan_data.max_candidates,
            max_jobs=plan_data.max_jobs,
            max_storage_gb=plan_data.max_storage_gb,
            features=features,
            is_custom=True,
            custom_for_tenant_id=tenant_id,
            is_active=True,
            sort_order=999,
        )
        
        db.session.add(custom_plan)
        db.session.commit()
        db.session.refresh(custom_plan)
        
        return CustomPlanResponseSchema.model_validate(custom_plan)

    @staticmethod
    def update_custom_plan(
        plan_id: int,
        updates: CustomPlanUpdateSchema,
        updated_by: str = "system"
    ) -> CustomPlanResponseSchema:
        """
        Update custom plan.
        
        Args:
            plan_id: Custom plan ID to update
            updates: Fields to update
            updated_by: User who updated the plan (for audit)
        
        Returns:
            CustomPlanResponseSchema with updated plan details
        
        Raises:
            ValueError: If plan not found, not custom, or downgrade validation fails
        """
        plan = db.session.get(SubscriptionPlan, plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        if not plan.is_custom:
            raise ValueError(f"Plan {plan_id} is not a custom plan. Only custom plans can be updated.")
        
        update_dict = updates.model_dump(exclude_unset=True)
        
        if plan.custom_for_tenant_id and any(
            key in update_dict for key in ['max_users', 'max_candidates', 'max_jobs']
        ):
            tenant_id = plan.custom_for_tenant_id
            
            if 'max_users' in update_dict:
                current_users = db.session.scalar(
                    select(func.count(PortalUser.id)).where(PortalUser.tenant_id == tenant_id)
                ) or 0
                if update_dict['max_users'] < current_users:
                    raise ValueError(
                        f"Cannot reduce max_users to {update_dict['max_users']}. "
                        f"Tenant currently has {current_users} users."
                    )
            
            if 'max_candidates' in update_dict:
                current_candidates = db.session.scalar(
                    select(func.count(Candidate.id)).where(Candidate.tenant_id == tenant_id)
                ) or 0
                if update_dict['max_candidates'] < current_candidates:
                    raise ValueError(
                        f"Cannot reduce max_candidates to {update_dict['max_candidates']}. "
                        f"Tenant currently has {current_candidates} candidates."
                    )
            
            if 'max_jobs' in update_dict:
                current_jobs = db.session.scalar(
                    select(func.count(JobPosting.id)).where(JobPosting.tenant_id == tenant_id)
                ) or 0
                if update_dict['max_jobs'] < current_jobs:
                    raise ValueError(
                        f"Cannot reduce max_jobs to {update_dict['max_jobs']}. "
                        f"Tenant currently has {current_jobs} jobs."
                    )
        
        for key, value in update_dict.items():
            setattr(plan, key, value)
        
        db.session.commit()
        db.session.refresh(plan)
        
        return CustomPlanResponseSchema.model_validate(plan)

    @staticmethod
    def delete_custom_plan(
        plan_id: int,
        deleted_by: str = "system"
    ) -> None:
        """
        Delete custom plan.
        
        Args:
            plan_id: Custom plan ID to delete
            deleted_by: User who deleted the plan (for audit)
        
        Raises:
            ValueError: If plan not found, not custom, or in use by tenants
        """
        plan = db.session.get(SubscriptionPlan, plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        if not plan.is_custom:
            raise ValueError(f"Plan {plan_id} is not a custom plan. Only custom plans can be deleted.")
        
        tenants_using = db.session.scalar(
            select(func.count(Tenant.id))
            .where(Tenant.subscription_plan_id == plan_id)
        )
        
        if tenants_using and tenants_using > 0:
            raise ValueError(
                f"Cannot delete custom plan {plan_id}. "
                f"{tenants_using} tenant(s) currently using this plan. "
                f"Change their plans before deleting."
            )
        
        db.session.delete(plan)
        db.session.commit()
        db.session.expire_all()

    @staticmethod
    def list_plans_for_tenant(
        tenant_id: int,
        include_inactive: bool = False
    ) -> List[CustomPlanResponseSchema]:
        """
        Get available plans for tenant.
        
        Returns:
        - All standard plans (is_custom=False)
        - Custom plans for this tenant (custom_for_tenant_id=tenant_id)
        
        Excludes custom plans for other tenants.
        
        Args:
            tenant_id: Tenant ID to get available plans for
            include_inactive: Whether to include inactive plans
        
        Returns:
            List of SubscriptionPlanResponseSchema
        
        Raises:
            ValueError: If tenant not found
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")
        
        query = select(SubscriptionPlan).where(
            db.or_(
                SubscriptionPlan.is_custom == False,
                SubscriptionPlan.custom_for_tenant_id == tenant_id
            )
        )
        
        if not include_inactive:
            query = query.where(SubscriptionPlan.is_active == True)
        
        query = query.order_by(
            SubscriptionPlan.sort_order.asc(),
            SubscriptionPlan.name.asc()
        )
        
        plans = db.session.scalars(query).all()
        
        return [CustomPlanResponseSchema.model_validate(plan) for plan in plans]

    # NOTE: Create, Update, and Deactivate operations for STANDARD plans are intentionally NOT implemented
    # as per Phase 1 requirements. Subscription plans are seeded and considered
    # configuration data managed by system administrators through database migrations
    # or direct database operations, not through the API.
