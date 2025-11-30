"""PM Admin Authentication Service - JWT-based authentication for Platform Management admins."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import bcrypt

from app import db, redis_client
from app.models import PMAdminUser
from app.schemas.pm_admin_schema import PMAdminLoginResponseSchema
from config.settings import settings  # Use global settings instance

logger = logging.getLogger(__name__)


class PMAdminAuthService:
    """Service for PM Admin authentication operations."""

    # Token configuration
    ACCESS_TOKEN_EXPIRY = timedelta(hours=24)  # 24 hours for PM admin
    REFRESH_TOKEN_EXPIRY = timedelta(days=30)  # 30 days
    REDIS_REFRESH_KEY_PREFIX = "pm_admin_refresh:"
    REDIS_BLACKLIST_KEY_PREFIX = "pm_admin_blacklist:"

    # Account lockout configuration
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=30)

    @staticmethod
    def _generate_access_token(admin: PMAdminUser) -> str:
        """
        Generate JWT access token for PM admin.

        Args:
            admin: PMAdminUser instance

        Returns:
            JWT access token string
        """
        payload = {
            "user_id": admin.id,
            "email": admin.email,
            "type": "pm_admin",
            "exp": datetime.utcnow() + PMAdminAuthService.ACCESS_TOKEN_EXPIRY,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    @staticmethod
    def _generate_refresh_token(admin: PMAdminUser) -> str:
        """
        Generate JWT refresh token for PM admin and store in Redis.

        Args:
            admin: PMAdminUser instance

        Returns:
            JWT refresh token string
        """
        payload = {
            "user_id": admin.id,
            "type": "pm_admin_refresh",
            "exp": datetime.utcnow() + PMAdminAuthService.REFRESH_TOKEN_EXPIRY,
            "iat": datetime.utcnow(),
        }

        refresh_token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

        # Store refresh token in Redis with expiry (if Redis is available)
        if redis_client:
            redis_key = f"{PMAdminAuthService.REDIS_REFRESH_KEY_PREFIX}{admin.id}"
            redis_client.setex(
                redis_key,
                int(PMAdminAuthService.REFRESH_TOKEN_EXPIRY.total_seconds()),
                refresh_token,
            )

        return refresh_token

    @staticmethod
    def _verify_password(admin: PMAdminUser, password: str) -> bool:
        """
        Verify password against stored hash.

        Args:
            admin: PMAdminUser instance
            password: Plain text password

        Returns:
            True if password matches
        """
        return bcrypt.checkpw(
            password.encode("utf-8"), admin.password_hash.encode("utf-8")
        )

    @staticmethod
    def _handle_failed_login(admin: PMAdminUser) -> None:
        """
        Handle failed login attempt (increment counter, lock if needed).

        Args:
            admin: PMAdminUser instance
        """
        admin.failed_login_attempts += 1

        if admin.failed_login_attempts >= PMAdminAuthService.MAX_FAILED_ATTEMPTS:
            admin.locked_until = datetime.utcnow() + PMAdminAuthService.LOCKOUT_DURATION
            logger.warning(
                f"PM Admin account locked: {admin.id} ({admin.email}) "
                f"until {admin.locked_until}"
            )

        db.session.commit()

    @staticmethod
    def _reset_failed_attempts(admin: PMAdminUser) -> None:
        """
        Reset failed login attempts counter on successful login.

        Args:
            admin: PMAdminUser instance
        """
        if admin.failed_login_attempts > 0 or admin.locked_until:
            admin.failed_login_attempts = 0
            admin.locked_until = None
            db.session.commit()

    @staticmethod
    def login(email: str, password: str) -> PMAdminLoginResponseSchema:
        """
        Authenticate PM admin and generate tokens.

        Args:
            email: PM admin email
            password: Plain text password

        Returns:
            PMAdminLoginResponseSchema with tokens and admin info

        Raises:
            ValueError: If authentication fails or account is locked/inactive
        """
        from sqlalchemy import select

        # Get admin by email
        admin = db.session.scalar(select(PMAdminUser).where(PMAdminUser.email == email))

        if not admin:
            raise ValueError("Invalid email or password")

        # Check if account is locked
        if admin.is_locked:
            raise ValueError(
                f"Account is locked until {admin.locked_until.isoformat()}. "
                f"Please try again later."
            )

        # Check if account is active
        if not admin.is_active:
            raise ValueError("Account is inactive. Contact system administrator.")

        # Verify password
        if not PMAdminAuthService._verify_password(admin, password):
            PMAdminAuthService._handle_failed_login(admin)
            raise ValueError("Invalid email or password")

        # Reset failed attempts on successful login
        PMAdminAuthService._reset_failed_attempts(admin)

        # Update last login
        admin.last_login = datetime.utcnow()
        db.session.commit()

        # Generate tokens
        access_token = PMAdminAuthService._generate_access_token(admin)
        refresh_token = PMAdminAuthService._generate_refresh_token(admin)

        logger.info(f"PM Admin logged in: {admin.id} ({admin.email})")

        from app.schemas.pm_admin_schema import PMAdminUserResponseSchema

        return PMAdminLoginResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=int(PMAdminAuthService.ACCESS_TOKEN_EXPIRY.total_seconds()),
            admin=PMAdminUserResponseSchema.model_validate(admin),
        )

    @staticmethod
    def logout(admin_id: int, access_token: str) -> Dict[str, str]:
        """
        Logout PM admin by blacklisting access token and removing refresh token.

        Args:
            admin_id: PM admin ID
            access_token: JWT access token to blacklist

        Returns:
            Dictionary with logout confirmation
        """
        if redis_client:
            # Blacklist access token (store until its expiry)
            blacklist_key = f"{PMAdminAuthService.REDIS_BLACKLIST_KEY_PREFIX}{access_token}"
            redis_client.setex(
                blacklist_key,
                int(PMAdminAuthService.ACCESS_TOKEN_EXPIRY.total_seconds()),
                "1",
            )

            # Remove refresh token from Redis
            refresh_key = f"{PMAdminAuthService.REDIS_REFRESH_KEY_PREFIX}{admin_id}"
            redis_client.delete(refresh_key)

        logger.info(f"PM Admin logged out: {admin_id}")

        return {"message": "Logged out successfully"}

    @staticmethod
    def refresh_token(refresh_token: str) -> PMAdminLoginResponseSchema:
        """
        Generate new access token using refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            PMAdminLoginResponseSchema with new access token

        Raises:
            ValueError: If refresh token is invalid or expired
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token, settings.secret_key, algorithms=["HS256"]
            )

            if payload.get("type") != "pm_admin_refresh":
                raise ValueError("Invalid token type")

            admin_id = payload.get("user_id")

            # Verify refresh token exists in Redis (if Redis is available)
            if redis_client:
                redis_key = f"{PMAdminAuthService.REDIS_REFRESH_KEY_PREFIX}{admin_id}"
                stored_token = redis_client.get(redis_key)

                if stored_token and stored_token.decode("utf-8") != refresh_token:
                    raise ValueError("Refresh token not found or invalid")

            # Get admin
            admin = db.session.get(PMAdminUser, admin_id)
            if not admin or not admin.is_active:
                raise ValueError("Admin not found or inactive")

            # Generate new access token
            access_token = PMAdminAuthService._generate_access_token(admin)

            logger.info(f"PM Admin token refreshed: {admin_id}")

            from app.schemas.pm_admin_schema import PMAdminUserResponseSchema

            return PMAdminLoginResponseSchema(
                access_token=access_token,
                refresh_token=refresh_token,  # Keep same refresh token
                token_type="Bearer",
                expires_in=int(PMAdminAuthService.ACCESS_TOKEN_EXPIRY.total_seconds()),
                admin=PMAdminUserResponseSchema.model_validate(admin),
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
            ValueError: If token is invalid, expired, or blacklisted
        """
        # Check if token is blacklisted (if Redis is available)
        if redis_client:
            blacklist_key = f"{PMAdminAuthService.REDIS_BLACKLIST_KEY_PREFIX}{access_token}"
            if redis_client.exists(blacklist_key):
                raise ValueError("Token has been revoked")

        try:
            # Decode token
            payload = jwt.decode(
                access_token, settings.secret_key, algorithms=["HS256"]
            )

            if payload.get("type") != "pm_admin":
                raise ValueError("Invalid token type")

            # Verify admin exists and is active
            admin_id = payload.get("user_id")
            admin = db.session.get(PMAdminUser, admin_id)

            if not admin:
                raise ValueError("Admin not found")

            if not admin.is_active:
                raise ValueError("Admin account is inactive")

            return payload

        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
