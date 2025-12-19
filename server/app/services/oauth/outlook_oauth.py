"""Outlook OAuth service for email integration.

Handles OAuth flow for Outlook/Microsoft 365 using Microsoft Identity Platform (MSAL).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import requests

from config.settings import settings

logger = logging.getLogger(__name__)


class OutlookOAuthService:
    """Service for Outlook/Microsoft 365 OAuth authentication."""
    
    SCOPES = [
        "Mail.Read",
        "User.Read",
        "offline_access",  # Required for refresh tokens
    ]
    
    # Microsoft Identity Platform endpoints
    AUTHORITY_URL = "https://login.microsoftonline.com"
    GRAPH_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self):
        """Initialize Outlook OAuth service."""
        self.client_id = settings.microsoft_oauth_client_id
        self.client_secret = settings.microsoft_oauth_client_secret
        self.redirect_uri = settings.microsoft_oauth_redirect_uri
        self.tenant = settings.microsoft_oauth_tenant  # 'common' for multi-tenant
    
    @property
    def auth_url(self) -> str:
        """Get authorization endpoint URL."""
        return f"{self.AUTHORITY_URL}/{self.tenant}/oauth2/v2.0/authorize"
    
    @property
    def token_url(self) -> str:
        """Get token endpoint URL."""
        return f"{self.AUTHORITY_URL}/{self.tenant}/oauth2/v2.0/token"
    
    def is_configured(self) -> bool:
        """Check if Outlook OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth authorization URL.
        
        Args:
            state: State parameter for CSRF protection (user_id:tenant_id:nonce)
            
        Returns:
            Authorization URL to redirect user to
        """
        if not self.is_configured():
            raise ValueError("Outlook OAuth is not configured. Check MICROSOFT_OAUTH_CLIENT_ID and MICROSOFT_OAUTH_CLIENT_SECRET.")
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "response_mode": "query",
            "prompt": "consent",  # Force consent to ensure we get refresh token
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dictionary with access_token, refresh_token, expires_at
        """
        if not self.is_configured():
            raise ValueError("Outlook OAuth is not configured.")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES),
        }
        
        response = requests.post(
            self.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        
        if not response.ok:
            error_data = response.json()
            logger.error(f"Outlook token exchange failed: {error_data}")
            raise ValueError(f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        token_data = response.json()
        
        # Calculate token expiry time
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": expires_at,
            "token_type": token_data.get("token_type", "Bearer"),
        }
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token from initial authorization
            
        Returns:
            Dictionary with new access_token, refresh_token, expires_at
        """
        if not self.is_configured():
            raise ValueError("Outlook OAuth is not configured.")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(self.SCOPES),
        }
        
        response = requests.post(
            self.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        
        if not response.ok:
            error_data = response.json()
            logger.error(f"Outlook token refresh failed: {error_data}")
            raise ValueError(f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        token_data = response.json()
        
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", refresh_token),  # May return new refresh token
            "expires_at": expires_at,
            "token_type": token_data.get("token_type", "Bearer"),
        }
    
    def get_user_email(self, access_token: str) -> str:
        """
        Get the email address of the authenticated user.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User's email address
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(f"{self.GRAPH_URL}/me", headers=headers, timeout=30)
        
        if not response.ok:
            logger.error(f"Failed to get user info: {response.text}")
            raise ValueError("Failed to get user email from Microsoft Graph")
        
        user_info = response.json()
        # Microsoft Graph returns 'mail' or 'userPrincipalName'
        return user_info.get("mail") or user_info.get("userPrincipalName", "")
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke/sign out user session.
        
        Note: Microsoft doesn't have a direct token revocation endpoint like Google.
        The best approach is to delete the stored tokens.
        
        Args:
            token: Token to revoke (not used, kept for API consistency)
            
        Returns:
            True (tokens should be deleted from storage)
        """
        # Microsoft doesn't support direct token revocation
        # Just return True, and caller should delete stored tokens
        logger.info("Microsoft token revocation requested - tokens should be deleted from storage")
        return True
    
    def get_messages(
        self,
        access_token: str,
        folder: str = "inbox",
        top: int = 50,
        filter_query: Optional[str] = None,
        select_fields: Optional[list] = None,
    ) -> list:
        """
        Fetch messages from user's mailbox.
        
        Args:
            access_token: Valid access token
            folder: Mail folder to fetch from ('inbox', 'sentitems', etc.)
            top: Maximum number of messages to return
            filter_query: OData filter query (e.g., "receivedDateTime ge 2024-01-01")
            select_fields: List of fields to select
            
        Returns:
            List of message objects
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Build query parameters
        params = {"$top": top}
        
        if filter_query:
            params["$filter"] = filter_query
        
        if select_fields:
            params["$select"] = ",".join(select_fields)
        else:
            # Default fields for job email processing
            params["$select"] = "id,subject,body,from,receivedDateTime,hasAttachments"
        
        # Order by newest first
        params["$orderby"] = "receivedDateTime desc"
        
        url = f"{self.GRAPH_URL}/me/mailFolders/{folder}/messages"
        
        response = requests.get(url, headers=headers, params=params, timeout=60)
        
        if not response.ok:
            logger.error(f"Failed to fetch messages: {response.text}")
            raise ValueError(f"Failed to fetch messages: {response.status_code}")
        
        data = response.json()
        return data.get("value", [])
    
    def get_message_by_id(self, access_token: str, message_id: str) -> dict:
        """
        Fetch a single message by ID.
        
        Args:
            access_token: Valid access token
            message_id: Message ID
            
        Returns:
            Message object
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        url = f"{self.GRAPH_URL}/me/messages/{message_id}"
        params = {"$select": "id,subject,body,from,receivedDateTime,hasAttachments,conversationId"}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if not response.ok:
            logger.error(f"Failed to fetch message: {response.text}")
            raise ValueError(f"Failed to fetch message: {response.status_code}")
        
        return response.json()
    
    def validate_token(self, access_token: str) -> bool:
        """
        Validate if an access token is still valid.
        
        Args:
            access_token: Token to validate
            
        Returns:
            True if token is valid
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                f"{self.GRAPH_URL}/me",
                headers=headers,
                timeout=30,
            )
            return response.ok
        except Exception:
            return False


# Singleton instance
outlook_oauth_service = OutlookOAuthService()
