"""Portal Authentication Service - JWT-based authentication for tenant portal users."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import bcrypt

from app import db, redis_client
from app.models import PortalUser, Tenant
from app.models.tenant import TenantStatus
from app.schemas.portal_user_schema import PortalLoginResponseSchema, PortalUserResponseSchema
from config.settings import settings  # Use global settings instance

logger = logging.getLogger(__name__)


class PortalAuthService:
    """Service for Portal user authentication operations."""

    # Token configuration
    ACCESS_TOKEN_EXPIRY = timedelta(hours=8)  # 8 hours for portal users
    REFRESH_TOKEN_EXPIRY = timedelta(days=14)  # 14 days
    REDIS_REFRESH_KEY_PREFIX = "portal_refresh:"
    REDIS_BLACKLIST_KEY_PREFIX = "portal_blacklist:"

    @staticmethod
    def _generate_access_token(user_data: dict) -> str:
        """
        Generate JWT access token for portal user.

        Args:
            user_data: Dictionary with user data (from PortalUserResponseSchema)

        Returns:
            JWT access token string
        """
        payload = {
            "user_id": user_data['id'],
            "email": user_data['email'],
            "tenant_id": user_data['tenant_id'],
            "role_id": user_data['roles'][0]['id'] if user_data['roles'] and len(user_data['roles']) > 0 else None,
            "role_name": user_data['roles'][0]['name'] if user_data['roles'] and len(user_data['roles']) > 0 else None,
            "type": "portal",
            "exp": datetime.utcnow() + PortalAuthService.ACCESS_TOKEN_EXPIRY,
            "iat": datetime.utcnow(),
        }

        logger.debug(f"User data for token generation: {user_data}")
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    @staticmethod
    def _generate_refresh_token(user: PortalUser) -> str:
        """
        Generate JWT refresh token for portal user and store in Redis.

        Args:
            user: PortalUser instance

        Returns:
            JWT refresh token string
        """
        payload = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "type": "portal_refresh",
            "exp": datetime.utcnow() + PortalAuthService.REFRESH_TOKEN_EXPIRY,
            "iat": datetime.utcnow(),
        }

        refresh_token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

        # Store refresh token in Redis with expiry
        redis_key = f"{PortalAuthService.REDIS_REFRESH_KEY_PREFIX}{user.id}"
        redis_client.setex(
            redis_key,
            int(PortalAuthService.REFRESH_TOKEN_EXPIRY.total_seconds()),
            refresh_token,
        )

        return refresh_token

    @staticmethod
    def _verify_password(user: PortalUser, password: str) -> bool:
        """
        Verify password against stored hash.

        Args:
            user: PortalUser instance
            password: Plain text password

        Returns:
            True if password matches
        """
        return bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        )

    @staticmethod
    def login(email: str, password: str) -> PortalLoginResponseSchema:
        """
        Authenticate portal user and generate tokens.
        Email is globally unique, so no tenant slug is required.

        Args:
            email: Portal user email (globally unique)
            password: Plain text password

        Returns:
            PortalLoginResponseSchema with tokens and user info

        Raises:
            ValueError: If authentication fails, account inactive, or tenant suspended
        """
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        logger.debug(f"Attempting login for email: {email}")

        # Get user by email (globally unique) with relationships eagerly loaded
        user = db.session.scalar(
            select(PortalUser)
            .where(PortalUser.email == email)
            .options(joinedload(PortalUser.roles), joinedload(PortalUser.tenant))
        )
        logger.debug(f"User query result: {user}")

        if not user:
            raise ValueError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise ValueError("Account is inactive. Contact your administrator.")
        logger.debug(f"User is active: {user.is_active}")

        # Check if tenant is active
        tenant = db.session.get(Tenant, user.tenant_id)
        if not tenant:
            raise ValueError("Tenant not found. Contact support.")
        logger.debug(f"Tenant status: {tenant.status}")

        if tenant.status == TenantStatus.SUSPENDED:
            raise ValueError(
                "Your organization's account is suspended. Contact support."
            )

        if tenant.status == TenantStatus.INACTIVE:
            raise ValueError(
                "Your organization's account is inactive. Contact support."
            )

        # Verify password
        if not PortalAuthService._verify_password(user, password):
            raise ValueError("Invalid email or password")
        logger.debug("Password verified successfully.")

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        logger.debug(f"Last login updated for user: {user.id}")

        # Generate tokens
        # Explicitly convert user object to dict using its to_dict method
        user_data_dict = user.to_dict(include_roles=True, include_permissions=True)
        logger.debug(f"User data dict from to_dict(): {user_data_dict}")
        user_data = PortalUserResponseSchema.model_validate(user_data_dict).model_dump()
        logger.debug(f"User data after model_validate: {user_data}")
        access_token = PortalAuthService._generate_access_token(user_data)
        refresh_token = PortalAuthService._generate_refresh_token(user)

        logger.info(
            f"Portal user logged in: {user.id} ({user.email}) "
            f"tenant_id={user.tenant_id}"
        )

        return PortalLoginResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=int(PortalAuthService.ACCESS_TOKEN_EXPIRY.total_seconds()),
            user=user_data,
        )

    @staticmethod
    def logout(user_id: int, access_token: str) -> Dict[str, str]:
        """
        Logout portal user by blacklisting access token and removing refresh token.

        Args:
            user_id: Portal user ID
            access_token: JWT access token to blacklist

        Returns:
            Dictionary with logout confirmation
        """
        # Blacklist access token (store until its expiry)
        blacklist_key = f"{PortalAuthService.REDIS_BLACKLIST_KEY_PREFIX}{access_token}"
        redis_client.setex(
            blacklist_key,
            int(PortalAuthService.ACCESS_TOKEN_EXPIRY.total_seconds()),
            "1",
        )

        # Remove refresh token from Redis
        refresh_key = f"{PortalAuthService.REDIS_REFRESH_KEY_PREFIX}{user_id}"
        redis_client.delete(refresh_key)

        logger.info(f"Portal user logged out: {user_id}")

        return {"message": "Logged out successfully"}

    @staticmethod
    def refresh_token(refresh_token: str) -> PortalLoginResponseSchema:
        """
        Generate new access token using refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            PortalLoginResponseSchema with new access token

        Raises:
            ValueError: If refresh token is invalid or expired
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token, settings.secret_key, algorithms=["HS256"]
            )

            if payload.get("type") != "portal_refresh":
                raise ValueError("Invalid token type")

            user_id = payload.get("user_id")
            tenant_id = payload.get("tenant_id")

            # Verify refresh token exists in Redis
            redis_key = f"{PortalAuthService.REDIS_REFRESH_KEY_PREFIX}{user_id}"
            stored_token = redis_client.get(redis_key)

            if not stored_token or stored_token.decode("utf-8") != refresh_token:
                raise ValueError("Refresh token not found or invalid")

            # Get user
            user = db.session.get(PortalUser, user_id)
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")

            # Check tenant is still active
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant or tenant.status != TenantStatus.ACTIVE:
                raise ValueError("Tenant is not active")

            # Generate new access token
            access_token = PortalAuthService._generate_access_token(user)

            logger.info(f"Portal user token refreshed: {user_id}")

            return PortalLoginResponseSchema(
                access_token=access_token,
                refresh_token=refresh_token,  # Keep same refresh token
                token_type="Bearer",
                expires_in=int(PortalAuthService.ACCESS_TOKEN_EXPIRY.total_seconds()),
                user=PortalUserResponseSchema.model_validate(user),
            )

        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid refresh token: {str(e)}")

    @staticmethod
    def validate_token(access_token: str) -> Dict:
        """
        Validate JWT access token and return payload.

        Args:
            access_token: JWT access token

        Returns:
            Dictionary with token payload

        Raises:
            ValueError: If token is invalid, expired, blacklisted, or tenant inactive
        """
        # Check if token is blacklisted
        blacklist_key = f"{PortalAuthService.REDIS_BLACKLIST_KEY_PREFIX}{access_token}"
        if redis_client.exists(blacklist_key):
            raise ValueError("Token has been revoked")

        try:
            # Decode token
            payload = jwt.decode(
                access_token, settings.secret_key, algorithms=["HS256"]
            )

            if payload.get("type") != "portal":
                raise ValueError("Invalid token type")

            # Verify user exists and is active
            user_id = payload.get("user_id")
            user = db.session.get(PortalUser, user_id)

            if not user:
                raise ValueError("User not found")

            if not user.is_active:
                raise ValueError("User account is inactive")

            # Verify tenant is active
            tenant_id = payload.get("tenant_id")
            tenant = db.session.get(Tenant, tenant_id)

            if not tenant:
                raise ValueError("Tenant not found")

            if tenant.status != TenantStatus.ACTIVE:
                raise ValueError(
                    f"Tenant is not active (status: {tenant.status.value})"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
