"""PM Admin Service - Platform Management admin operations."""

import logging
from typing import Optional
from sqlalchemy import select, or_
import bcrypt

from app import db
from app.models import PMAdminUser, PortalUser
from app.schemas.pm_admin_schema import (
    PMAdminUserCreateSchema,
    PMAdminUserUpdateSchema,
    PMAdminUserResponseSchema,
    PMAdminUserListResponseSchema,
    ResetTenantAdminPasswordSchema,
)
from app.services import AuditLogService

logger = logging.getLogger(__name__)


class PMAdminService:
    """Service for PM Admin user management operations."""

    @staticmethod
    def _validate_email_unique(email: str, exclude_admin_id: Optional[int] = None) -> bool:
        """
        Check if email is unique across all PM admin users.

        Args:
            email: Email to validate
            exclude_admin_id: Admin ID to exclude from check (for updates)

        Returns:
            True if unique

        Raises:
            ValueError: If email already exists
        """
        query = select(PMAdminUser).where(PMAdminUser.email == email)

        if exclude_admin_id:
            query = query.where(PMAdminUser.id != exclude_admin_id)

        existing = db.session.scalar(query)

        if existing:
            raise ValueError(f"PM Admin email '{email}' is already in use")

        return True

    @staticmethod
    def create_admin(
        data: PMAdminUserCreateSchema, changed_by: str
    ) -> PMAdminUserResponseSchema:
        """
        Create a new PM Admin user.

        Args:
            data: PM Admin creation data
            changed_by: Identifier for audit log (format: "pm_admin:123")

        Returns:
            PMAdminUserResponseSchema with created admin

        Raises:
            ValueError: If validation fails
        """
        # Validate email uniqueness
        PMAdminService._validate_email_unique(data.email)

        # Hash password
        password_hash = bcrypt.hashpw(
            data.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Create PM Admin
        admin = PMAdminUser(
            email=data.email,
            password_hash=password_hash,
            first_name=data.first_name,
            last_name=data.last_name,
            is_active=data.is_active if data.is_active is not None else True,
        )
        db.session.add(admin)
        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="CREATE",
            entity_type="PMAdminUser",
            entity_id=admin.id,
            changed_by=changed_by,
            changes={
                "email": data.email,
                "first_name": data.first_name,
                "last_name": data.last_name,
            },
        )

        logger.info(f"PM Admin created: {admin.id} ({data.email}) by {changed_by}")

        return PMAdminUserResponseSchema.model_validate(admin)

    @staticmethod
    def get_admin(admin_id: int) -> PMAdminUserResponseSchema:
        """
        Get a PM Admin user by ID.

        Args:
            admin_id: Admin ID to retrieve

        Returns:
            PMAdminUserResponseSchema with admin details

        Raises:
            ValueError: If admin not found
        """
        admin = db.session.get(PMAdminUser, admin_id)
        if not admin:
            raise ValueError(f"PM Admin with ID {admin_id} not found")

        return PMAdminUserResponseSchema.model_validate(admin)

    @staticmethod
    def list_admins(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PMAdminUserListResponseSchema:
        """
        List PM Admin users with pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page (max 100)
            search: Search term for email, first_name, last_name
            is_active: Filter by active status

        Returns:
            PMAdminUserListResponseSchema with paginated admins
        """
        # Enforce max per_page
        if per_page > 100:
            per_page = 100

        # Build query
        query = select(PMAdminUser)

        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    PMAdminUser.email.ilike(search_term),
                    PMAdminUser.first_name.ilike(search_term),
                    PMAdminUser.last_name.ilike(search_term),
                )
            )

        if is_active is not None:
            query = query.where(PMAdminUser.is_active == is_active)

        # Order by created_at desc
        query = query.order_by(PMAdminUser.created_at.desc())

        # Execute paginated query
        pagination = db.paginate(
            query,
            page=page,
            per_page=per_page,
            error_out=False,
        )

        # Convert to response schemas
        admins = [
            PMAdminUserResponseSchema.model_validate(admin) for admin in pagination.items
        ]

        return PMAdminUserListResponseSchema(
            items=admins,
            total=pagination.total,
            page=page,
            per_page=per_page,
        )

    @staticmethod
    def update_admin(
        admin_id: int, data: PMAdminUserUpdateSchema, changed_by: str
    ) -> PMAdminUserResponseSchema:
        """
        Update a PM Admin user.

        Args:
            admin_id: Admin ID to update
            data: Update data
            changed_by: Identifier for audit log (format: "pm_admin:123")

        Returns:
            PMAdminUserResponseSchema with updated admin

        Raises:
            ValueError: If admin not found or validation fails
        """
        admin = db.session.get(PMAdminUser, admin_id)
        if not admin:
            raise ValueError(f"PM Admin with ID {admin_id} not found")

        changes = {}

        # Update email (with uniqueness check)
        if data.email is not None and data.email != admin.email:
            PMAdminService._validate_email_unique(data.email, exclude_admin_id=admin_id)
            changes["email"] = (admin.email, data.email)
            admin.email = data.email

        # Update first_name
        if data.first_name is not None and data.first_name != admin.first_name:
            changes["first_name"] = (admin.first_name, data.first_name)
            admin.first_name = data.first_name

        # Update last_name
        if data.last_name is not None and data.last_name != admin.last_name:
            changes["last_name"] = (admin.last_name, data.last_name)
            admin.last_name = data.last_name

        # Update phone
        if data.phone is not None and data.phone != admin.phone:
            changes["phone"] = (admin.phone, data.phone)
            admin.phone = data.phone

        # Update is_active
        if data.is_active is not None and data.is_active != admin.is_active:
            changes["is_active"] = (admin.is_active, data.is_active)
            admin.is_active = data.is_active

        # Commit if there are changes
        if changes:
            db.session.commit()

            # Log audit
            AuditLogService.log_action(
                action="UPDATE",
                entity_type="PMAdminUser",
                entity_id=admin_id,
                changed_by=changed_by,
                changes=changes,
            )

            logger.info(f"PM Admin updated: {admin_id} by {changed_by}")

        return PMAdminUserResponseSchema.model_validate(admin)

    @staticmethod
    def reset_tenant_admin_password(
        data: ResetTenantAdminPasswordSchema, changed_by: str
    ) -> dict:
        """
        Reset a tenant admin's password (PM Admin privilege).

        Args:
            data: Password reset data with portal_user_id
            changed_by: Identifier for audit log (format: "pm_admin:123")

        Returns:
            Dictionary with reset confirmation

        Raises:
            ValueError: If user not found or not a TENANT_ADMIN
        """
        # Get portal user
        portal_user = db.session.get(PortalUser, data.portal_user_id)
        if not portal_user:
            raise ValueError(f"Portal user with ID {data.portal_user_id} not found")

        # Verify user is TENANT_ADMIN
        if portal_user.role.name != "TENANT_ADMIN":
            raise ValueError(
                f"User {data.portal_user_id} is not a TENANT_ADMIN "
                f"(current role: {portal_user.role.name})"
            )

        # Hash new password
        password_hash = bcrypt.hashpw(
            data.new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        portal_user.password_hash = password_hash

        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="RESET_TENANT_ADMIN_PASSWORD",
            entity_type="PortalUser",
            entity_id=data.portal_user_id,
            changed_by=changed_by,
            changes={
                "email": portal_user.email,
                "tenant_id": portal_user.tenant_id,
                "reset_by_pm_admin": True,
            },
        )

        logger.info(
            f"Tenant admin password reset: portal_user_id={data.portal_user_id} "
            f"({portal_user.email}) by PM Admin {changed_by}"
        )

        return {
            "message": f"Password reset successfully for tenant admin '{portal_user.email}'",
            "portal_user_id": data.portal_user_id,
        }

    @staticmethod
    def change_password(admin_id: int, current_password: str, new_password: str) -> dict:
        """
        Change a PM Admin user's own password.

        Args:
            admin_id: Admin ID
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            Dictionary with success message

        Raises:
            ValueError: If admin not found or current password incorrect
        """
        admin = db.session.get(PMAdminUser, admin_id)
        if not admin:
            raise ValueError(f"PM Admin with ID {admin_id} not found")

        # Verify current password
        if not bcrypt.checkpw(current_password.encode("utf-8"), admin.password_hash.encode("utf-8")):
            raise ValueError("Current password is incorrect")

        # Validate new password length
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")

        # Hash and set new password
        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        admin.password_hash = password_hash
        db.session.commit()

        logger.info(f"PM Admin password changed: {admin_id}")

        return {"message": "Password changed successfully"}

    @staticmethod
    def reset_admin_password(admin_id: int, new_password: str, changed_by: str) -> dict:
        """
        Reset another PM Admin user's password (PM Admin privilege).

        Args:
            admin_id: Admin ID to reset password for
            new_password: New password to set
            changed_by: Identifier for audit log (format: "pm_admin:123")

        Returns:
            Dictionary with success message

        Raises:
            ValueError: If admin not found or validation fails
        """
        admin = db.session.get(PMAdminUser, admin_id)
        if not admin:
            raise ValueError(f"PM Admin with ID {admin_id} not found")

        # Validate new password length
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")

        # Hash and set new password
        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        admin.password_hash = password_hash
        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="RESET_PASSWORD",
            entity_type="PMAdminUser",
            entity_id=admin_id,
            changed_by=changed_by,
            changes={
                "email": admin.email,
                "reset_by_pm_admin": True,
            },
        )

        logger.info(f"PM Admin password reset: {admin_id} ({admin.email}) by {changed_by}")

        return {"message": f"Password reset successfully for admin '{admin.email}'"}

    @staticmethod
    def delete_admin(admin_id: int, changed_by: str) -> dict:
        """
        Delete a PM Admin user.

        Args:
            admin_id: Admin ID to delete
            changed_by: Identifier for audit log (format: "pm_admin:123")

        Returns:
            Dictionary with deletion confirmation

        Raises:
            ValueError: If admin not found
        """
        admin = db.session.get(PMAdminUser, admin_id)
        if not admin:
            raise ValueError(f"PM Admin with ID {admin_id} not found")

        email = admin.email

        # Log audit before deletion
        AuditLogService.log_action(
            action="DELETE",
            entity_type="PMAdminUser",
            entity_id=admin_id,
            changed_by=changed_by,
            changes={
                "email": email,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
            },
        )

        db.session.delete(admin)
        db.session.commit()
        db.session.expire_all()

        logger.info(f"PM Admin deleted: {admin_id} ({email}) by {changed_by}")

        return {"message": f"PM Admin '{email}' deleted successfully"}
