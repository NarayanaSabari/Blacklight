"""Portal User Service - Tenant-specific user management."""

import logging
from typing import Optional
from sqlalchemy import select, or_
import bcrypt

from app import db
from app.models import PortalUser, Tenant, Role, UserRole
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

        if not creator.is_tenant_admin:
            raise ValueError("Only TENANT_ADMIN users can create new users")

        # Get tenant_id from creator (schema doesn't have tenant_id)
        tenant_id = creator.tenant_id

        # Verify tenant exists and is active
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant with ID {tenant_id} not found")

        if tenant.status != TenantStatus.ACTIVE:
            raise ValueError(
                f"Cannot create user for tenant with status: {tenant.status.value}"
            )

        # Check user limit before creation
        TenantService.check_user_limit(tenant_id)

        # Validate email uniqueness globally
        PortalUserService._validate_email_unique(data.email)

        # Verify the role exists and belongs to the correct tenant
        role = db.session.get(Role, data.role_id)
        if not role:
            raise ValueError(f"Role with ID {data.role_id} not found")
        
        # Role must be either a system role or belong to the creator's tenant
        if not role.is_system_role and role.tenant_id != tenant_id:
            raise ValueError("Cannot assign role from different tenant")

        # Hash password
        password_hash = bcrypt.hashpw(
            data.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Create user
        user = PortalUser(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=password_hash,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()  # Flush to get user.id
        
        # Assign role to user
        user_role = UserRole(
            user_id=user.id,
            role_id=data.role_id
        )
        db.session.add(user_role)
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
                "tenant_id": tenant_id,
                "role_id": data.role_id,
            },
        )

        logger.info(
            f"Portal user created: {user.id} ({data.email}) in tenant {tenant_id} with role {data.role_id} by {changed_by}"
        )

        return PortalUserResponseSchema.model_validate(user.to_dict(include_roles=True, include_permissions=True))

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

        return PortalUserResponseSchema.model_validate(user.to_dict(include_roles=True, include_permissions=True))

    @staticmethod
    def list_users(
        tenant_id: int,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> PortalUserListResponseSchema:
        """
        List portal users within a tenant.

        Args:
            tenant_id: Tenant ID to list users for
            page: Page number (1-indexed)
            per_page: Items per page (max 100)
            search: Search term for email, first_name, last_name
            role_id: Filter by role ID
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

        if role_id:
            # Filter by role_id using the many-to-many relationship
            query = query.join(PortalUser.roles).where(Role.id == role_id)

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
            PortalUserResponseSchema.model_validate(user.to_dict(include_roles=True, include_permissions=True)) for user in pagination.items
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

        if not updater.is_tenant_admin:
            raise ValueError("Only TENANT_ADMIN users can update users")

        # Verify same tenant
        if updater.tenant_id != user.tenant_id:
            raise ValueError("Cannot update users from other tenants")

        changes = {}

        # Update first_name
        if data.first_name is not None and data.first_name != user.first_name:
            changes["first_name"] = (user.first_name, data.first_name)
            user.first_name = data.first_name

        # Update last_name
        if data.last_name is not None and data.last_name != user.last_name:
            changes["last_name"] = (user.last_name, data.last_name)
            user.last_name = data.last_name

        # Update phone
        if data.phone is not None and data.phone != user.phone:
            changes["phone"] = (user.phone, data.phone)
            user.phone = data.phone

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

        return PortalUserResponseSchema.model_validate(user.to_dict(include_roles=True))

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

        if not deleter.is_tenant_admin:
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

        return PortalUserResponseSchema.model_validate(user.to_dict(include_roles=True, include_permissions=True))

    @staticmethod
    def update_own_profile(
        user_id: int,
        data,
        changed_by: str,
    ) -> PortalUserResponseSchema:
        """
        Update current user's own profile.
        Users can only update their own first_name, last_name, and phone.

        Args:
            user_id: User ID to update
            data: Profile update data (first_name, last_name, phone)
            changed_by: Identifier for audit log

        Returns:
            PortalUserResponseSchema with updated user

        Raises:
            ValueError: If user not found
        """
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        changes = {}

        # Update first_name
        if data.first_name is not None and data.first_name != user.first_name:
            changes["first_name"] = (user.first_name, data.first_name)
            user.first_name = data.first_name

        # Update last_name
        if data.last_name is not None and data.last_name != user.last_name:
            changes["last_name"] = (user.last_name, data.last_name)
            user.last_name = data.last_name

        # Update phone
        if data.phone is not None and data.phone != user.phone:
            changes["phone"] = (user.phone, data.phone)
            user.phone = data.phone

        # Commit if there are changes
        if changes:
            db.session.commit()

            # Log audit
            AuditLogService.log_action(
                action="UPDATE_PROFILE",
                entity_type="PortalUser",
                entity_id=user_id,
                changed_by=changed_by,
                changes=changes,
            )

            logger.info(f"Portal user profile updated: {user_id} by {changed_by}")

        return PortalUserResponseSchema.model_validate(user.to_dict(include_roles=True, include_permissions=True))

    @staticmethod
    def change_own_password(
        user_id: int,
        current_password: str,
        new_password: str,
        changed_by: str,
    ) -> bool:
        """
        Change current user's own password.

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password to set
            changed_by: Identifier for audit log

        Returns:
            True if password changed successfully

        Raises:
            ValueError: If current password is incorrect or user not found
        """
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Verify current password
        if not bcrypt.checkpw(current_password.encode("utf-8"), user.password_hash.encode("utf-8")):
            raise ValueError("Current password is incorrect")

        # Hash new password
        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user.password_hash = password_hash

        db.session.commit()

        # Log audit (don't include password in changes)
        AuditLogService.log_action(
            action="CHANGE_PASSWORD",
            entity_type="PortalUser",
            entity_id=user_id,
            changed_by=changed_by,
            changes={"email": user.email},
        )

        logger.info(f"Portal user password changed: {user_id} by {changed_by}")

        return True
