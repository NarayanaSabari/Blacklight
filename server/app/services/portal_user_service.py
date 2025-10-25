"""Portal User Service - Tenant-specific user management."""

import logging
from typing import Optional
from sqlalchemy import select, or_
import bcrypt

from app import db
from app.models import PortalUser, Tenant
from app.models.portal_user import PortalUserRole
from app.models.tenant import TenantStatus
from app.schemas.portal_user_schema import (
    PortalUserCreateSchema,
    PortalUserUpdateSchema,
    PortalUserResetPasswordSchema,
    PortalUserResponseSchema,
    PortalUserListResponseSchema,
)
from app.services import AuditLogService
from app.services.tenant_service import TenantService

logger = logging.getLogger(__name__)


class PortalUserService:
    """Service for portal user management operations."""

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
    def create_user(
        data: PortalUserCreateSchema, created_by_user_id: int, changed_by: str
    ) -> PortalUserResponseSchema:
        """
        Create a new portal user within a tenant.

        Args:
            data: User creation data
            created_by_user_id: ID of the user creating this user (must be TENANT_ADMIN)
            changed_by: Identifier for audit log (format: "portal_user:123")

        Returns:
            PortalUserResponseSchema with created user

        Raises:
            ValueError: If validation fails or permissions denied
        """
        # Verify creator is TENANT_ADMIN
        creator = db.session.get(PortalUser, created_by_user_id)
        if not creator:
            raise ValueError("Creator user not found")

        if creator.role != PortalUserRole.TENANT_ADMIN:
            raise ValueError("Only TENANT_ADMIN users can create new users")

        # Verify tenant exists and is active
        tenant = db.session.get(Tenant, data.tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {data.tenant_id} not found")

        if tenant.status != TenantStatus.ACTIVE:
            raise ValueError(
                f"Cannot create user for tenant with status: {tenant.status.value}"
            )

        # Verify creator belongs to same tenant
        if creator.tenant_id != data.tenant_id:
            raise ValueError("Cannot create users for other tenants")

        # Check user limit before creation
        TenantService.check_user_limit(data.tenant_id)

        # Validate email uniqueness globally
        PortalUserService._validate_email_unique(data.email)

        # Hash password
        password_hash = bcrypt.hashpw(
            data.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Create user
        user = PortalUser(
            tenant_id=data.tenant_id,
            email=data.email,
            password_hash=password_hash,
            first_name=data.first_name,
            last_name=data.last_name,
            role=data.role,
            is_active=data.is_active if data.is_active is not None else True,
        )
        db.session.add(user)
        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="CREATE",
            entity_type="PortalUser",
            entity_id=user.id,
            changed_by=changed_by,
            changes={
                "email": data.email,
                "first_name": data.first_name,
                "last_name": data.last_name,
                "role": data.role.value,
                "tenant_id": data.tenant_id,
            },
        )

        logger.info(
            f"Portal user created: {user.id} ({data.email}) in tenant {data.tenant_id} by {changed_by}"
        )

        return PortalUserResponseSchema.model_validate(user)

    @staticmethod
    def get_user(user_id: int, requester_tenant_id: Optional[int] = None) -> PortalUserResponseSchema:
        """
        Get a portal user by ID.

        Args:
            user_id: User ID to retrieve
            requester_tenant_id: Tenant ID of requester (for access control)

        Returns:
            PortalUserResponseSchema with user details

        Raises:
            ValueError: If user not found or access denied
        """
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # If requester_tenant_id is provided, verify same tenant
        if requester_tenant_id is not None and user.tenant_id != requester_tenant_id:
            raise ValueError("Access denied: User belongs to different tenant")

        return PortalUserResponseSchema.model_validate(user)

    @staticmethod
    def list_users(
        tenant_id: int,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role: Optional[PortalUserRole] = None,
        is_active: Optional[bool] = None,
    ) -> PortalUserListResponseSchema:
        """
        List portal users within a tenant.

        Args:
            tenant_id: Tenant ID to list users for
            page: Page number (1-indexed)
            per_page: Items per page (max 100)
            search: Search term for email, first_name, last_name
            role: Filter by user role
            is_active: Filter by active status

        Returns:
            PortalUserListResponseSchema with paginated users
        """
        # Enforce max per_page
        if per_page > 100:
            per_page = 100

        # Build query
        query = select(PortalUser).where(PortalUser.tenant_id == tenant_id)

        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    PortalUser.email.ilike(search_term),
                    PortalUser.first_name.ilike(search_term),
                    PortalUser.last_name.ilike(search_term),
                )
            )

        if role:
            query = query.where(PortalUser.role == role)

        if is_active is not None:
            query = query.where(PortalUser.is_active == is_active)

        # Order by created_at desc
        query = query.order_by(PortalUser.created_at.desc())

        # Execute paginated query
        pagination = db.paginate(
            query,
            page=page,
            per_page=per_page,
            error_out=False,
        )

        # Convert to response schemas
        users = [
            PortalUserResponseSchema.model_validate(user) for user in pagination.items
        ]

        return PortalUserListResponseSchema(
            items=users,
            total=pagination.total,
            page=page,
            per_page=per_page,
        )

    @staticmethod
    def update_user(
        user_id: int,
        data: PortalUserUpdateSchema,
        updated_by_user_id: int,
        changed_by: str,
    ) -> PortalUserResponseSchema:
        """
        Update a portal user.

        Args:
            user_id: User ID to update
            data: Update data
            updated_by_user_id: ID of user performing update (must be TENANT_ADMIN)
            changed_by: Identifier for audit log (format: "portal_user:123")

        Returns:
            PortalUserResponseSchema with updated user

        Raises:
            ValueError: If user not found, validation fails, or permissions denied
        """
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Verify updater is TENANT_ADMIN
        updater = db.session.get(PortalUser, updated_by_user_id)
        if not updater:
            raise ValueError("Updater user not found")

        if updater.role != PortalUserRole.TENANT_ADMIN:
            raise ValueError("Only TENANT_ADMIN users can update users")

        # Verify same tenant
        if updater.tenant_id != user.tenant_id:
            raise ValueError("Cannot update users from other tenants")

        changes = {}

        # Update email (with global uniqueness check)
        if data.email is not None and data.email != user.email:
            PortalUserService._validate_email_unique(data.email, exclude_user_id=user_id)
            changes["email"] = (user.email, data.email)
            user.email = data.email

        # Update first_name
        if data.first_name is not None and data.first_name != user.first_name:
            changes["first_name"] = (user.first_name, data.first_name)
            user.first_name = data.first_name

        # Update last_name
        if data.last_name is not None and data.last_name != user.last_name:
            changes["last_name"] = (user.last_name, data.last_name)
            user.last_name = data.last_name

        # Update role
        if data.role is not None and data.role != user.role:
            changes["role"] = (user.role.value, data.role.value)
            user.role = data.role

        # Update is_active
        if data.is_active is not None and data.is_active != user.is_active:
            changes["is_active"] = (user.is_active, data.is_active)
            user.is_active = data.is_active

        # Commit if there are changes
        if changes:
            db.session.commit()

            # Log audit
            AuditLogService.log_action(
                action="UPDATE",
                entity_type="PortalUser",
                entity_id=user_id,
                changed_by=changed_by,
                changes=changes,
            )

            logger.info(f"Portal user updated: {user_id} by {changed_by}")

        return PortalUserResponseSchema.model_validate(user)

    @staticmethod
    def delete_user(user_id: int, deleted_by_user_id: int, changed_by: str) -> dict:
        """
        Delete a portal user.

        Args:
            user_id: User ID to delete
            deleted_by_user_id: ID of user performing deletion (must be TENANT_ADMIN)
            changed_by: Identifier for audit log (format: "portal_user:123")

        Returns:
            Dictionary with deletion confirmation

        Raises:
            ValueError: If user not found, permissions denied, or self-deletion attempt
        """
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Verify deleter is TENANT_ADMIN
        deleter = db.session.get(PortalUser, deleted_by_user_id)
        if not deleter:
            raise ValueError("Deleter user not found")

        if deleter.role != PortalUserRole.TENANT_ADMIN:
            raise ValueError("Only TENANT_ADMIN users can delete users")

        # Verify same tenant
        if deleter.tenant_id != user.tenant_id:
            raise ValueError("Cannot delete users from other tenants")

        # Prevent self-deletion
        if user_id == deleted_by_user_id:
            raise ValueError("Cannot delete your own account")

        # Store user info for logging
        email = user.email
        full_name = f"{user.first_name} {user.last_name}"
        tenant_id = user.tenant_id

        # Log audit BEFORE deletion
        AuditLogService.log_action(
            action="DELETE",
            entity_type="PortalUser",
            entity_id=user_id,
            changed_by=changed_by,
            changes={
                "email": email,
                "full_name": full_name,
                "tenant_id": tenant_id,
            },
        )

        # Delete user
        db.session.delete(user)
        db.session.commit()

        logger.info(f"Portal user deleted: {user_id} ({email}) by {changed_by}")

        return {
            "message": f"User '{full_name}' ({email}) deleted successfully",
        }

    @staticmethod
    def reset_password(
        user_id: int, data: PortalUserResetPasswordSchema, changed_by: str
    ) -> PortalUserResponseSchema:
        """
        Reset a portal user's password.

        Args:
            user_id: User ID to reset password for
            data: Password reset data
            changed_by: Identifier for audit log (format: "portal_user:123" or "pm_admin:456")

        Returns:
            PortalUserResponseSchema with updated user

        Raises:
            ValueError: If user not found
        """
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Hash new password
        password_hash = bcrypt.hashpw(
            data.new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user.password_hash = password_hash

        db.session.commit()

        # Log audit (don't include password in changes)
        AuditLogService.log_action(
            action="RESET_PASSWORD",
            entity_type="PortalUser",
            entity_id=user_id,
            changed_by=changed_by,
            changes={"email": user.email},
        )

        logger.info(f"Portal user password reset: {user_id} by {changed_by}")

        return PortalUserResponseSchema.model_validate(user)
