"""Email Integration Service.

Manages email integrations for users - connecting Gmail/Outlook accounts,
storing encrypted tokens, and managing integration lifecycle.
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select

from app import db
from app.models.processed_email import ProcessedEmail
from app.models.user_email_integration import UserEmailIntegration
from app.services.oauth.gmail_oauth import gmail_oauth_service
from app.services.oauth.outlook_oauth import outlook_oauth_service
from app.utils.encryption import token_encryption

logger = logging.getLogger(__name__)


class EmailIntegrationService:
    """Service for managing email integrations."""
    
    @staticmethod
    def get_integrations_for_user(user_id: int, tenant_id: int) -> list[UserEmailIntegration]:
        """
        Get all email integrations for a user.
        
        Args:
            user_id: Portal user ID
            tenant_id: Tenant ID
            
        Returns:
            List of UserEmailIntegration objects
        """
        stmt = select(UserEmailIntegration).where(
            UserEmailIntegration.user_id == user_id,
            UserEmailIntegration.tenant_id == tenant_id,
        )
        return list(db.session.scalars(stmt).all())
    
    @staticmethod
    def get_integration(integration_id: int, user_id: int, tenant_id: int) -> Optional[UserEmailIntegration]:
        """
        Get a specific email integration.
        
        Args:
            integration_id: Integration ID
            user_id: Portal user ID
            tenant_id: Tenant ID
            
        Returns:
            UserEmailIntegration object or None
        """
        stmt = select(UserEmailIntegration).where(
            UserEmailIntegration.id == integration_id,
            UserEmailIntegration.user_id == user_id,
            UserEmailIntegration.tenant_id == tenant_id,
        )
        return db.session.scalar(stmt)
    
    @staticmethod
    def get_integration_by_provider(
        user_id: int,
        tenant_id: int,
        provider: str,
    ) -> Optional[UserEmailIntegration]:
        """
        Get integration by provider.
        
        Args:
            user_id: Portal user ID
            tenant_id: Tenant ID
            provider: 'gmail' or 'outlook'
            
        Returns:
            UserEmailIntegration object or None
        """
        stmt = select(UserEmailIntegration).where(
            UserEmailIntegration.user_id == user_id,
            UserEmailIntegration.tenant_id == tenant_id,
            UserEmailIntegration.provider == provider,
        )
        return db.session.scalar(stmt)
    
    @staticmethod
    def get_active_integrations(tenant_id: Optional[int] = None) -> list[UserEmailIntegration]:
        """
        Get all active email integrations.
        
        Args:
            tenant_id: Optional filter by tenant
            
        Returns:
            List of active UserEmailIntegration objects
        """
        stmt = select(UserEmailIntegration).where(
            UserEmailIntegration.is_active == True,
        )
        
        if tenant_id:
            stmt = stmt.where(UserEmailIntegration.tenant_id == tenant_id)
        
        return list(db.session.scalars(stmt).all())
    
    @staticmethod
    def generate_oauth_state(user_id: int, tenant_id: int) -> str:
        """
        Generate OAuth state parameter for CSRF protection.
        
        Args:
            user_id: Portal user ID
            tenant_id: Tenant ID
            
        Returns:
            State string in format: user_id:tenant_id:nonce
        """
        nonce = secrets.token_urlsafe(16)
        return f"{user_id}:{tenant_id}:{nonce}"
    
    @staticmethod
    def parse_oauth_state(state: str) -> tuple[int, int, str]:
        """
        Parse OAuth state parameter.
        
        Args:
            state: State string
            
        Returns:
            Tuple of (user_id, tenant_id, nonce)
        """
        parts = state.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid OAuth state format")
        
        return int(parts[0]), int(parts[1]), parts[2]
    
    @staticmethod
    def initiate_gmail_connection(user_id: int, tenant_id: int) -> str:
        """
        Start Gmail OAuth flow.
        
        Args:
            user_id: Portal user ID
            tenant_id: Tenant ID
            
        Returns:
            Authorization URL to redirect user to
        """
        state = EmailIntegrationService.generate_oauth_state(user_id, tenant_id)
        return gmail_oauth_service.get_authorization_url(state)
    
    @staticmethod
    def initiate_outlook_connection(user_id: int, tenant_id: int) -> str:
        """
        Start Outlook OAuth flow.
        
        Args:
            user_id: Portal user ID
            tenant_id: Tenant ID
            
        Returns:
            Authorization URL to redirect user to
        """
        state = EmailIntegrationService.generate_oauth_state(user_id, tenant_id)
        return outlook_oauth_service.get_authorization_url(state)
    
    @staticmethod
    def complete_gmail_connection(code: str, state: str) -> UserEmailIntegration:
        """
        Complete Gmail OAuth flow and create/update integration.
        
        Args:
            code: Authorization code from Google
            state: State parameter from OAuth callback
            
        Returns:
            Created or updated UserEmailIntegration
        """
        # Parse state
        user_id, tenant_id, _ = EmailIntegrationService.parse_oauth_state(state)
        
        # Exchange code for tokens
        tokens = gmail_oauth_service.exchange_code_for_tokens(code)
        
        # Get user email
        email_address = gmail_oauth_service.get_user_email(tokens["access_token"])
        
        # Check for existing integration
        existing = EmailIntegrationService.get_integration_by_provider(
            user_id, tenant_id, "gmail"
        )
        
        if existing:
            # Update existing integration
            existing.access_token_encrypted = token_encryption.encrypt(tokens["access_token"])
            if tokens.get("refresh_token"):
                existing.refresh_token_encrypted = token_encryption.encrypt(tokens["refresh_token"])
            existing.token_expiry = tokens["expires_at"]
            existing.email_address = email_address
            existing.is_active = True
            existing.last_error = None
            existing.consecutive_failures = 0
            db.session.commit()
            logger.info(f"Updated Gmail integration for user {user_id}")
            return existing
        
        # Create new integration
        integration = UserEmailIntegration(
            user_id=user_id,
            tenant_id=tenant_id,
            provider="gmail",
            access_token_encrypted=token_encryption.encrypt(tokens["access_token"]),
            refresh_token_encrypted=token_encryption.encrypt(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
            token_expiry=tokens["expires_at"],
            email_address=email_address,
            is_active=True,
        )
        
        db.session.add(integration)
        db.session.commit()
        logger.info(f"Created Gmail integration for user {user_id}")
        
        return integration
    
    @staticmethod
    def complete_outlook_connection(code: str, state: str) -> UserEmailIntegration:
        """
        Complete Outlook OAuth flow and create/update integration.
        
        Args:
            code: Authorization code from Microsoft
            state: State parameter from OAuth callback
            
        Returns:
            Created or updated UserEmailIntegration
        """
        # Parse state
        user_id, tenant_id, _ = EmailIntegrationService.parse_oauth_state(state)
        
        # Exchange code for tokens
        tokens = outlook_oauth_service.exchange_code_for_tokens(code)
        
        # Get user email
        email_address = outlook_oauth_service.get_user_email(tokens["access_token"])
        
        # Check for existing integration
        existing = EmailIntegrationService.get_integration_by_provider(
            user_id, tenant_id, "outlook"
        )
        
        if existing:
            # Update existing integration
            existing.access_token_encrypted = token_encryption.encrypt(tokens["access_token"])
            if tokens.get("refresh_token"):
                existing.refresh_token_encrypted = token_encryption.encrypt(tokens["refresh_token"])
            existing.token_expiry = tokens["expires_at"]
            existing.email_address = email_address
            existing.is_active = True
            existing.last_error = None
            existing.consecutive_failures = 0
            db.session.commit()
            logger.info(f"Updated Outlook integration for user {user_id}")
            return existing
        
        # Create new integration
        integration = UserEmailIntegration(
            user_id=user_id,
            tenant_id=tenant_id,
            provider="outlook",
            access_token_encrypted=token_encryption.encrypt(tokens["access_token"]),
            refresh_token_encrypted=token_encryption.encrypt(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
            token_expiry=tokens["expires_at"],
            email_address=email_address,
            is_active=True,
        )
        
        db.session.add(integration)
        db.session.commit()
        logger.info(f"Created Outlook integration for user {user_id}")
        
        return integration
    
    @staticmethod
    def disconnect_integration(
        integration_id: int,
        user_id: int,
        tenant_id: int,
    ) -> bool:
        """
        Disconnect and delete an email integration.
        
        Args:
            integration_id: Integration ID
            user_id: Portal user ID
            tenant_id: Tenant ID
            
        Returns:
            True if successfully deleted
        """
        integration = EmailIntegrationService.get_integration(
            integration_id, user_id, tenant_id
        )
        
        if not integration:
            raise ValueError("Integration not found")
        
        # Try to revoke tokens
        try:
            access_token = token_encryption.decrypt(integration.access_token_encrypted)
            if integration.provider == "gmail":
                gmail_oauth_service.revoke_token(access_token)
            else:
                outlook_oauth_service.revoke_token(access_token)
        except Exception as e:
            logger.warning(f"Failed to revoke token: {e}")
        
        # Delete processed emails for this integration
        stmt = delete(ProcessedEmail).where(ProcessedEmail.integration_id == integration_id)
        db.session.execute(stmt)
        
        # Delete integration
        db.session.delete(integration)
        db.session.commit()
        db.session.expire_all()
        
        logger.info(f"Disconnected {integration.provider} integration for user {user_id}")
        return True
    
    @staticmethod
    def toggle_integration(
        integration_id: int,
        user_id: int,
        tenant_id: int,
        is_active: bool,
    ) -> UserEmailIntegration:
        """
        Toggle integration active status.
        
        Args:
            integration_id: Integration ID
            user_id: Portal user ID
            tenant_id: Tenant ID
            is_active: New active status
            
        Returns:
            Updated UserEmailIntegration
        """
        integration = EmailIntegrationService.get_integration(
            integration_id, user_id, tenant_id
        )
        
        if not integration:
            raise ValueError("Integration not found")
        
        integration.is_active = is_active
        db.session.commit()
        
        return integration
    
    @staticmethod
    def get_valid_access_token(integration: UserEmailIntegration) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            integration: UserEmailIntegration object
            
        Returns:
            Valid access token
        """
        # Check if token is expired or about to expire (5 min buffer)
        now = datetime.now(timezone.utc)
        token_expiry = integration.token_expiry
        
        # Make token_expiry timezone-aware if it isn't
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)
        
        buffer_time = now.timestamp() + 300  # 5 minute buffer
        
        if token_expiry.timestamp() > buffer_time:
            # Token is still valid
            return token_encryption.decrypt(integration.access_token_encrypted)
        
        # Token needs refresh
        if not integration.refresh_token_encrypted:
            raise ValueError("No refresh token available - user needs to reconnect")
        
        refresh_token = token_encryption.decrypt(integration.refresh_token_encrypted)
        
        try:
            if integration.provider == "gmail":
                tokens = gmail_oauth_service.refresh_access_token(refresh_token)
            else:
                tokens = outlook_oauth_service.refresh_access_token(refresh_token)
            
            # Update stored tokens
            integration.access_token_encrypted = token_encryption.encrypt(tokens["access_token"])
            if tokens.get("refresh_token"):
                integration.refresh_token_encrypted = token_encryption.encrypt(tokens["refresh_token"])
            integration.token_expiry = tokens["expires_at"]
            db.session.commit()
            
            return tokens["access_token"]
            
        except Exception as e:
            logger.error(f"Token refresh failed for integration {integration.id}: {e}")
            integration.last_error = str(e)
            integration.consecutive_failures = (integration.consecutive_failures or 0) + 1
            
            # Deactivate if too many failures
            if integration.consecutive_failures >= 3:
                integration.is_active = False
                logger.warning(f"Deactivated integration {integration.id} due to repeated failures")
            
            db.session.commit()
            raise
    
    @staticmethod
    def get_integration_stats(user_id: int, tenant_id: int) -> dict:
        """
        Get statistics for user's email integrations.
        
        Args:
            user_id: Portal user ID
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with integration stats
        """
        integrations = EmailIntegrationService.get_integrations_for_user(user_id, tenant_id)
        
        stats = {
            "gmail": {
                "connected": False,
                "email": None,
                "is_active": False,
                "emails_processed": 0,
                "jobs_created": 0,
                "last_synced": None,
            },
            "outlook": {
                "connected": False,
                "email": None,
                "is_active": False,
                "emails_processed": 0,
                "jobs_created": 0,
                "last_synced": None,
            },
        }
        
        for integration in integrations:
            provider = integration.provider
            stats[provider] = {
                "connected": True,
                "integration_id": integration.id,
                "email": integration.email_address,
                "is_active": integration.is_active,
                "emails_processed": integration.emails_processed_count or 0,
                "jobs_created": integration.jobs_created_count or 0,
                "last_synced": integration.last_synced_at.isoformat() if integration.last_synced_at else None,
                "last_error": integration.last_error,
            }
        
        return stats


# Singleton instance
email_integration_service = EmailIntegrationService()
