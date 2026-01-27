"""Tenant Service - Core tenant management operations."""

import logging
import re
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified
import bcrypt

from app import db
from app.models import (
    Tenant,
    PortalUser,
    SubscriptionPlan,
    TenantSubscriptionHistory,
    Role,
    Candidate,
    JobApplication,
    CandidateDocument,
)
from app.models.tenant import TenantStatus, BillingCycle
from app.schemas.tenant_schema import (
    TenantCreateSchema,
    TenantUpdateSchema,
    TenantChangePlanSchema,
    TenantSuspendSchema,
    TenantDeleteSchema,
    TenantFilterSchema,
    TenantResponseSchema,
    TenantListResponseSchema,
    TenantStatsSchema,
    TenantDeleteResponseSchema,
)
from app.services import AuditLogService

logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant management operations."""

    @staticmethod
    def _extract_user_id(changed_by: str) -> int | None:
        """
        Extract user ID from changed_by string.
        
        Args:
            changed_by: String in format "pm_admin:123"
            
        Returns:
            User ID as integer, or None if invalid format
        """
        try:
            if ":" in changed_by:
                return int(changed_by.split(":")[1])
        except (ValueError, IndexError):
            pass
        return None

    @staticmethod
    def _generate_slug(name: str) -> str:
        """
        Generate a URL-friendly slug from tenant name.

        Args:
            name: Tenant company name

        Returns:
            Generated slug
        """
        # Convert to lowercase, replace spaces/special chars with hyphens
        slug = name.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")

        # Ensure it starts with a letter
        if slug and not slug[0].isalpha():
            slug = "t-" + slug

        return slug or "tenant"

    @staticmethod
    def _validate_slug_unique(slug: str, exclude_tenant_id: Optional[int] = None) -> bool:
        """
        Check if slug is unique across all tenants.

        Args:
            slug: Slug to validate
            exclude_tenant_id: Tenant ID to exclude from check (for updates)

        Returns:
            True if unique

        Raises:
            ValueError: If slug already exists
        """
        query = select(Tenant).where(Tenant.slug == slug)

        if exclude_tenant_id:
            query = query.where(Tenant.id != exclude_tenant_id)

        existing = db.session.scalar(query)

        if existing:
            raise ValueError(f"Tenant with slug '{slug}' already exists")

        return True

    @staticmethod
    def _validate_email_unique(email: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Check if email is globally unique across all portal users.

        Args:
            email: Email to validate
            exclude_user_id: User ID to exclude from check (for updates)

        Returns:
            True if unique

        Raises:
            ValueError: If email already exists
        """
        query = select(PortalUser).where(PortalUser.email == email)

        if exclude_user_id:
            query = query.where(PortalUser.id != exclude_user_id)

        existing = db.session.scalar(query)

        if existing:
            raise ValueError(f"Email '{email}' is already in use")

        return True

    @staticmethod
    def create_tenant(data: TenantCreateSchema, changed_by: str) -> TenantResponseSchema:
        """
        Create a new tenant with tenant admin user.

        Args:
            data: Tenant creation data including admin user details
            changed_by: Identifier of user creating tenant (format: "pm_admin:123")

        Returns:
            TenantResponseSchema with created tenant

        Raises:
            ValueError: If validation fails or subscription plan not found
        """
        # Validate subscription plan exists
        plan = db.session.get(SubscriptionPlan, data.subscription_plan_id)
        if not plan:
            raise ValueError(
                f"Subscription plan with ID {data.subscription_plan_id} not found"
            )

        # Generate slug if not provided
        slug = data.slug
        if not slug:
            slug = TenantService._generate_slug(data.name)

        # Validate slug uniqueness
        TenantService._validate_slug_unique(slug)

        # Validate admin email uniqueness
        TenantService._validate_email_unique(data.tenant_admin_email)

        # Create tenant
        tenant = Tenant(
            name=data.name,
            slug=slug,
            company_email=data.company_email,
            company_phone=data.company_phone,
            subscription_plan_id=data.subscription_plan_id,
            status=TenantStatus.ACTIVE,
            billing_cycle=data.billing_cycle,
        )
        db.session.add(tenant)
        db.session.flush()  # Get tenant.id without committing

        # Hash admin password
        password_hash = bcrypt.hashpw(
            data.tenant_admin_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Get TENANT_ADMIN role
        tenant_admin_role = db.session.scalar(
            select(Role).where(Role.name == "TENANT_ADMIN").where(Role.is_system_role == True)
        )
        if not tenant_admin_role:
            raise ValueError("TENANT_ADMIN system role not found. Run migrations to seed roles.")

        # Create tenant admin user
        admin_user = PortalUser(
            tenant_id=tenant.id,
            email=data.tenant_admin_email,
            password_hash=password_hash,
            first_name=data.tenant_admin_first_name,
            last_name=data.tenant_admin_last_name,
            is_active=True,
        )
        admin_user.roles.append(tenant_admin_role) # Assign the role
        db.session.add(admin_user)

        # Extract PM admin user ID for history tracking
        pm_admin_id = TenantService._extract_user_id(changed_by)

        # Create subscription history entry
        history = TenantSubscriptionHistory(
            tenant_id=tenant.id,
            subscription_plan_id=plan.id,
            billing_cycle=data.billing_cycle,
            started_at=datetime.utcnow(),
            changed_by=pm_admin_id,
            notes="Initial subscription on tenant creation",
        )
        db.session.add(history)

        # Commit transaction
        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="CREATE",
            entity_type="Tenant",
            entity_id=tenant.id,
            changed_by=changed_by,
            changes={
                "name": data.name,
                "slug": slug,
                "subscription_plan_id": data.subscription_plan_id,
                "billing_cycle": data.billing_cycle.value if data.billing_cycle else None,
                "tenant_admin_email": data.tenant_admin_email,
            },
        )

        logger.info(f"Tenant created: {tenant.id} ({slug}) by {changed_by}")

        # Trigger tenant welcome email via Inngest
        try:
            import inngest
            from app.inngest import inngest_client
            from config.settings import settings
            
            # Build admin full name
            admin_name = f"{data.tenant_admin_first_name}"
            if data.tenant_admin_last_name:
                admin_name += f" {data.tenant_admin_last_name}"
            
            # Get portal login URL from settings (same as candidate invitation)
            login_url = f"{settings.frontend_base_url}/login"
            
            inngest_client.send_sync(
                inngest.Event(
                    name="email/tenant-welcome",
                    data={
                        "tenant_id": tenant.id,
                        "tenant_name": data.name,
                        "admin_email": data.tenant_admin_email,
                        "admin_name": admin_name,
                        "temporary_password": data.tenant_admin_password,
                        "login_url": login_url
                    }
                )
            )
            logger.info(f"Tenant welcome email event triggered for {data.tenant_admin_email}")
        except Exception as e:
            # Don't fail tenant creation if email trigger fails
            logger.error(f"Failed to trigger tenant welcome email: {e}")

        return TenantResponseSchema.model_validate(tenant)

    @staticmethod
    def get_tenant(
        identifier: int | str, include_plan: bool = True
    ) -> TenantResponseSchema:
        """
        Get tenant by ID or slug.

        Args:
            identifier: Tenant ID (int) or slug (str)
            include_plan: Whether to include subscription plan details

        Returns:
            TenantResponseSchema with tenant details

        Raises:
            ValueError: If tenant not found
        """
        if isinstance(identifier, int):
            # Use joinedload for eager loading
            query = select(Tenant).options(joinedload(Tenant.subscription_plan)).where(Tenant.id == identifier)
            tenant = db.session.scalar(query)
        else:
            query = select(Tenant).options(joinedload(Tenant.subscription_plan)).where(Tenant.slug == identifier)
            tenant = db.session.scalar(query)

        if not tenant:
            raise ValueError(f"Tenant '{identifier}' not found")

        return TenantResponseSchema.model_validate(tenant)

    @staticmethod
    def list_tenants(
        filters: Optional[TenantFilterSchema] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> TenantListResponseSchema:
        """
        List tenants with filtering and pagination.

        Args:
            filters: Optional filter criteria
            page: Page number (1-indexed)
            per_page: Items per page (max 100)

        Returns:
            TenantListResponseSchema with paginated tenants
        """
        # Enforce max per_page
        if per_page > 100:
            per_page = 100

        # Build query with eager loading of subscription_plan
        query = select(Tenant).options(joinedload(Tenant.subscription_plan))

        # Apply filters
        if filters:
            if filters.status:
                query = query.where(Tenant.status == filters.status)

            if filters.subscription_plan_id:
                query = query.where(
                    Tenant.subscription_plan_id == filters.subscription_plan_id
                )

            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        Tenant.name.ilike(search_term),
                        Tenant.slug.ilike(search_term),
                        Tenant.company_email.ilike(search_term),
                    )
                )

        # Order by created_at desc (newest first)
        query = query.order_by(Tenant.created_at.desc())

        # Execute paginated query
        pagination = db.paginate(
            query,
            page=page,
            per_page=per_page,
            error_out=False,
        )

        # Convert to response schemas
        tenants = [
            TenantResponseSchema.model_validate(tenant, from_attributes=True) for tenant in pagination.items
        ]

        return TenantListResponseSchema(
            items=tenants,
            total=pagination.total,
            page=page,
            per_page=per_page,
        )

    @staticmethod
    def update_tenant(
        tenant_id: int, data: TenantUpdateSchema, changed_by: str
    ) -> TenantResponseSchema:
        """
        Update tenant basic information.

        Args:
            tenant_id: Tenant ID to update
            data: Update data
            changed_by: Identifier of user updating tenant (format: "pm_admin:123")

        Returns:
            TenantResponseSchema with updated tenant

        Raises:
            ValueError: If tenant not found or validation fails
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        changes = {}

        # Update name
        if data.name is not None:
            if data.name != tenant.name:
                changes["name"] = (tenant.name, data.name)
                tenant.name = data.name

        # Update company_email
        if data.company_email is not None:
            if data.company_email != tenant.company_email:
                changes["company_email"] = (tenant.company_email, data.company_email)
                tenant.company_email = data.company_email

        # Update company_phone
        if data.company_phone is not None:
            if data.company_phone != tenant.company_phone:
                changes["company_phone"] = (tenant.company_phone, data.company_phone)
                tenant.company_phone = data.company_phone

        # Update settings
        if data.settings is not None:
            if data.settings != tenant.settings:
                changes["settings"] = (tenant.settings, data.settings)
                tenant.settings = data.settings

        # Commit if there are changes
        if changes:
            db.session.commit()

            # Log audit
            AuditLogService.log_action(
                action="UPDATE",
                entity_type="Tenant",
                entity_id=tenant_id,
                changed_by=changed_by,
                changes=changes,
            )

            logger.info(f"Tenant updated: {tenant_id} by {changed_by}")

        return TenantResponseSchema.model_validate(tenant)

    @staticmethod
    def change_subscription_plan(
        tenant_id: int, data: TenantChangePlanSchema, changed_by: str
    ) -> TenantResponseSchema:
        """
        Change tenant's subscription plan.

        Args:
            tenant_id: Tenant ID
            data: Plan change data
            changed_by: Identifier of user changing plan (format: "pm_admin:123")

        Returns:
            TenantResponseSchema with updated tenant

        Raises:
            ValueError: If tenant/plan not found or resource limits exceeded
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        new_plan = db.session.get(SubscriptionPlan, data.new_plan_id)
        if not new_plan:
            raise ValueError(
                f"Subscription plan with ID {data.new_plan_id} not found"
            )

        # Check if changing to same plan
        if tenant.subscription_plan_id == data.new_plan_id:
            if data.billing_cycle and data.billing_cycle == tenant.billing_cycle:
                raise ValueError("Tenant is already on this plan and billing cycle")

        # Validate new plan limits against current usage
        stats = TenantService.get_usage_stats(tenant_id)

        if stats.user_count > new_plan.max_users:
            raise ValueError(
                f"Cannot change to plan '{new_plan.name}': "
                f"Current users ({stats.user_count}) exceed plan limit ({new_plan.max_users})"
            )

        # TODO: Validate candidate and job limits when those features are implemented
        # if stats.candidates_count > new_plan.max_candidates:
        #     raise ValueError(...)
        # if stats.jobs_count > new_plan.max_jobs:
        #     raise ValueError(...)

        # End current subscription history (if exists)
        current_history = db.session.scalar(
            select(TenantSubscriptionHistory)
            .where(TenantSubscriptionHistory.tenant_id == tenant_id)
            .where(TenantSubscriptionHistory.ended_at == None)
            .order_by(TenantSubscriptionHistory.started_at.desc())
        )

        if current_history:
            current_history.ended_at = datetime.utcnow()
            current_history.notes = (
                f"{current_history.notes or ''}\nEnded for plan change to {new_plan.name}"
            ).strip()

        # Update tenant
        old_plan_id = tenant.subscription_plan_id
        old_billing_cycle = tenant.billing_cycle

        tenant.subscription_plan_id = data.new_plan_id
        if data.billing_cycle:
            tenant.billing_cycle = data.billing_cycle

        # Extract PM admin user ID for history tracking
        pm_admin_id = TenantService._extract_user_id(changed_by)

        # Create new subscription history entry
        history = TenantSubscriptionHistory(
            tenant_id=tenant_id,
            subscription_plan_id=data.new_plan_id,
            billing_cycle=data.billing_cycle or tenant.billing_cycle,
            started_at=datetime.utcnow(),
            changed_by=pm_admin_id,
            notes=data.reason or "Subscription plan changed",
        )
        db.session.add(history)

        # Commit transaction
        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="CHANGE_PLAN",
            entity_type="Tenant",
            entity_id=tenant_id,
            changed_by=changed_by,
            changes={
                "subscription_plan_id": (old_plan_id, data.new_plan_id),
                "billing_cycle": (
                    old_billing_cycle.value,
                    (data.billing_cycle or tenant.billing_cycle).value,
                ),
                "reason": data.reason,
            },
        )

        logger.info(
            f"Tenant {tenant_id} plan changed: {old_plan_id} -> {data.new_plan_id} by {changed_by}"
        )

        return TenantResponseSchema.model_validate(tenant)

    @staticmethod
    def suspend_tenant(
        tenant_id: int, data: TenantSuspendSchema, changed_by: str
    ) -> TenantResponseSchema:
        """
        Suspend a tenant (disables all portal user access).

        Args:
            tenant_id: Tenant ID to suspend
            data: Suspension data with reason
            changed_by: Identifier of user suspending tenant (format: "pm_admin:123")

        Returns:
            TenantResponseSchema with updated tenant

        Raises:
            ValueError: If tenant not found or already suspended
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        if tenant.status == TenantStatus.SUSPENDED:
            raise ValueError(f"Tenant {tenant_id} is already suspended")

        # Update tenant status
        old_status = tenant.status
        tenant.status = TenantStatus.SUSPENDED

        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="SUSPEND",
            entity_type="Tenant",
            entity_id=tenant_id,
            changed_by=changed_by,
            changes={
                "status": (old_status.value, TenantStatus.SUSPENDED.value),
                "reason": data.reason,
            },
        )

        logger.warning(
            f"Tenant suspended: {tenant_id} by {changed_by}. Reason: {data.reason}"
        )

        return TenantResponseSchema.model_validate(tenant)

    @staticmethod
    def reactivate_tenant(tenant_id: int, changed_by: str) -> TenantResponseSchema:
        """
        Reactivate a suspended tenant.

        Args:
            tenant_id: Tenant ID to reactivate
            changed_by: Identifier of user reactivating tenant (format: "pm_admin:123")

        Returns:
            TenantResponseSchema with updated tenant

        Raises:
            ValueError: If tenant not found or not suspended
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        if tenant.status != TenantStatus.SUSPENDED:
            raise ValueError(
                f"Tenant {tenant_id} is not suspended (current status: {tenant.status.value})"
            )

        # Update tenant status
        tenant.status = TenantStatus.ACTIVE

        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="REACTIVATE",
            entity_type="Tenant",
            entity_id=tenant_id,
            changed_by=changed_by,
            changes={
                "status": (TenantStatus.SUSPENDED.value, TenantStatus.ACTIVE.value),
            },
        )

        logger.info(f"Tenant reactivated: {tenant_id} by {changed_by}")

        return TenantResponseSchema.model_validate(tenant)

    @staticmethod
    def delete_tenant(
        tenant_id: int, data: TenantDeleteSchema, changed_by: str
    ) -> Dict[str, str]:
        """
        Delete a tenant (CASCADE deletes all portal users, preserves subscription history).

        Args:
            tenant_id: Tenant ID to delete
            data: Deletion data with reason
            changed_by: Identifier of user deleting tenant (format: "pm_admin:123")

        Returns:
            Dictionary with deletion confirmation message

        Raises:
            ValueError: If tenant not found
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        # Store tenant info for logging
        tenant_name = tenant.name
        slug = tenant.slug

        # Count portal users for confirmation
        users_count = db.session.scalar(
            select(func.count(PortalUser.id)).where(PortalUser.tenant_id == tenant_id)
        )

        # Log audit BEFORE deletion (since tenant will be gone)
        AuditLogService.log_action(
            action="DELETE",
            entity_type="Tenant",
            entity_id=tenant_id,
            changed_by=changed_by,
            changes={
                "name": tenant_name,
                "slug": slug,
                "users_deleted_count": users_count,
                "reason": data.reason,
            },
        )

        # Delete tenant (CASCADE will handle portal_users and subscription_history)
        db.session.delete(tenant)
        db.session.commit()
        db.session.expire_all()

        logger.warning(
            f"Tenant deleted: {tenant_id} ({slug}) with {users_count} users by {changed_by}. "
            f"Reason: {data.reason}"
        )

        return {
            "message": f"Tenant '{tenant_name}' (ID: {tenant_id}) deleted successfully",
            "users_deleted": users_count,
        }

    # === Resource Limit Checks ===

    @staticmethod
    def check_user_limit(tenant_id: int) -> bool:
        """
        Check if tenant has reached user limit.

        Args:
            tenant_id: Tenant ID

        Returns:
            True if under limit

        Raises:
            ValueError: If tenant not found or user limit exceeded
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        current_count = db.session.scalar(
            select(func.count(PortalUser.id)).where(PortalUser.tenant_id == tenant_id)
        )

        if current_count >= tenant.subscription_plan.max_users:
            raise ValueError(
                f"User limit reached ({tenant.subscription_plan.max_users}). "
                f"Upgrade plan to add more users."
            )

        return True

    @staticmethod
    def check_candidate_limit(tenant_id: int) -> bool:
        """
        Check if tenant has reached candidate limit.

        Args:
            tenant_id: Tenant ID

        Returns:
            True if under limit

        Raises:
            ValueError: If tenant not found or candidate limit exceeded

        Note:
            Placeholder implementation - will be completed when Candidate model is implemented
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        # TODO: Implement candidate counting when Candidate model exists
        # current_count = db.session.scalar(
        #     select(func.count(Candidate.id)).where(Candidate.tenant_id == tenant_id)
        # )
        # if current_count >= tenant.subscription_plan.max_candidates:
        #     raise ValueError(...)

        logger.debug(f"Candidate limit check skipped (not implemented): tenant {tenant_id}")
        return True

    @staticmethod
    def check_job_limit(tenant_id: int) -> bool:
        """
        Check if tenant has reached job posting limit.

        Args:
            tenant_id: Tenant ID

        Returns:
            True if under limit

        Raises:
            ValueError: If tenant not found or job limit exceeded

        Note:
            Placeholder implementation - will be completed when Job model is implemented
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        # TODO: Implement job counting when Job model exists
        # current_count = db.session.scalar(
        #     select(func.count(Job.id)).where(Job.tenant_id == tenant_id)
        # )
        # if current_count >= tenant.subscription_plan.max_jobs:
        #     raise ValueError(...)

        logger.debug(f"Job limit check skipped (not implemented): tenant {tenant_id}")
        return True

    @staticmethod
    def get_usage_stats(tenant_id: int) -> TenantStatsSchema:
        """
        Get current resource usage statistics for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            TenantStatsSchema with usage counts

        Raises:
            ValueError: If tenant not found
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        users_count = db.session.scalar(
            select(func.count(PortalUser.id)).where(PortalUser.tenant_id == tenant_id)
        ) or 0

        candidates_count = db.session.scalar(
            select(func.count(Candidate.id)).where(Candidate.tenant_id == tenant_id)
        ) or 0

        jobs_count = db.session.scalar(
            select(func.count(JobApplication.id)).where(
                JobApplication.candidate_id.in_(
                    select(Candidate.id).where(Candidate.tenant_id == tenant_id)
                )
            )
        ) or 0

        total_storage_bytes = db.session.scalar(
            select(func.sum(CandidateDocument.file_size)).where(
                CandidateDocument.tenant_id == tenant_id
            )
        ) or 0
        storage_used_gb = round(total_storage_bytes / (1024 ** 3), 2)

        user_usage_percent = (users_count / tenant.subscription_plan.max_users) * 100 if tenant.subscription_plan.max_users > 0 else 0
        candidate_usage_percent = (candidates_count / tenant.subscription_plan.max_candidates) * 100 if tenant.subscription_plan.max_candidates > 0 else 0
        job_usage_percent = (jobs_count / tenant.subscription_plan.max_jobs) * 100 if tenant.subscription_plan.max_jobs > 0 else 0
        storage_usage_percent = (storage_used_gb / tenant.subscription_plan.max_storage_gb) * 100 if tenant.subscription_plan.max_storage_gb > 0 else 0

        return TenantStatsSchema(
            tenant_id=tenant_id,
            tenant_name=tenant.name, # Added
            user_count=users_count, # Renamed from users_count
            candidate_count=candidates_count,
            job_count=jobs_count,
            storage_used_gb=storage_used_gb, # Added
            max_users=tenant.subscription_plan.max_users,
            max_candidates=tenant.subscription_plan.max_candidates,
            max_jobs=tenant.subscription_plan.max_jobs,
            max_storage_gb=tenant.subscription_plan.max_storage_gb, # Added
            user_usage_percent=user_usage_percent, # Added
            candidate_usage_percent=candidate_usage_percent, # Added
            job_usage_percent=job_usage_percent, # Added
            storage_usage_percent=storage_usage_percent, # Added
        )

    # =========================================================================
    # Document Requirements Management
    # =========================================================================

    @staticmethod
    def get_document_requirements(tenant_id: int) -> list:
        """
        Get document requirements for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of document requirement dictionaries
            
        Raises:
            ValueError: If tenant not found
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")
        
        # Get requirements from settings, default to empty list
        settings = tenant.settings or {}
        return settings.get('required_documents', [])

    @staticmethod
    def update_document_requirements(
        tenant_id: int,
        requirements: list,
        changed_by: str
    ) -> list:
        """
        Update document requirements for a tenant.
        
        Args:
            tenant_id: Tenant ID
            requirements: List of document requirement dictionaries
            changed_by: Identifier of user making the change
            
        Returns:
            Updated list of document requirements
            
        Raises:
            ValueError: If tenant not found
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")
        
        # Get current settings or create empty dict
        current_settings = tenant.settings or {}
        old_requirements = current_settings.get('required_documents', [])
        
        # Create a new dict to ensure SQLAlchemy detects the change
        new_settings = dict(current_settings)
        new_settings['required_documents'] = requirements
        tenant.settings = new_settings
        
        # Flag the column as modified to ensure SQLAlchemy persists the JSONB change
        flag_modified(tenant, 'settings')
        
        db.session.commit()
        
        # Log audit
        AuditLogService.log_action(
            action="UPDATE",
            entity_type="TenantDocumentRequirements",
            entity_id=tenant_id,
            changed_by=changed_by,
            changes={
                "required_documents": (old_requirements, requirements)
            },
        )
        
        logger.info(f"Document requirements updated for tenant {tenant_id} by {changed_by}")
        
        return requirements

    @staticmethod
    def get_document_requirements_by_token(token: str) -> list:
        """
        Get document requirements for a tenant using invitation token.
        Public method for onboarding flow.
        
        Args:
            token: Invitation token
            
        Returns:
            List of document requirement dictionaries
            
        Raises:
            ValueError: If token is invalid
        """
        from app.models.candidate_invitation import CandidateInvitation
        
        invitation = db.session.scalar(
            select(CandidateInvitation).where(CandidateInvitation.token == token)
        )
        
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        return TenantService.get_document_requirements(invitation.tenant_id)
