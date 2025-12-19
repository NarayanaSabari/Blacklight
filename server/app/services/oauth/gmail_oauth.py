"""Gmail OAuth service for email integration.

Handles OAuth flow for Gmail using Google OAuth 2.0.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config.settings import settings

logger = logging.getLogger(__name__)


class GmailOAuthService:
    """Service for Gmail OAuth authentication."""
    
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]
    
    # Google OAuth endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def __init__(self):
        """Initialize Gmail OAuth service."""
        self.client_id = settings.google_oauth_client_id
        self.client_secret = settings.google_oauth_client_secret
        self.redirect_uri = settings.google_oauth_redirect_uri
    
    def is_configured(self) -> bool:
        """Check if Gmail OAuth is properly configured."""
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
            raise ValueError("Gmail OAuth is not configured. Check GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.")
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
            "include_granted_scopes": "true",
        }
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dictionary with access_token, refresh_token, expires_at
        """
        if not self.is_configured():
            raise ValueError("Gmail OAuth is not configured.")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        
        response = requests.post(self.TOKEN_URL, data=data, timeout=30)
        
        if not response.ok:
            error_data = response.json()
            logger.error(f"Gmail token exchange failed: {error_data}")
            raise ValueError(f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        token_data = response.json()
        
        # Calculate token expiry time
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),  # May not be returned on subsequent auths
            "expires_at": expires_at,
            "token_type": token_data.get("token_type", "Bearer"),
        }
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token from initial authorization
            
        Returns:
            Dictionary with new access_token and expires_at
        """
        if not self.is_configured():
            raise ValueError("Gmail OAuth is not configured.")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        response = requests.post(self.TOKEN_URL, data=data, timeout=30)
        
        if not response.ok:
            error_data = response.json()
            logger.error(f"Gmail token refresh failed: {error_data}")
            raise ValueError(f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        token_data = response.json()
        
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return {
            "access_token": token_data["access_token"],
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
        
        response = requests.get(self.USERINFO_URL, headers=headers, timeout=30)
        
        if not response.ok:
            logger.error(f"Failed to get user info: {response.text}")
            raise ValueError("Failed to get user email from Google")
        
        user_info = response.json()
        return user_info.get("email", "")
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke an access or refresh token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if revocation successful
        """
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            return response.ok
        except Exception as e:
            logger.warning(f"Token revocation failed: {e}")
            return False
    
    def build_gmail_service(self, access_token: str, refresh_token: Optional[str] = None):
        """
        Build Gmail API service client.
        
        Args:
            access_token: Valid access token
            refresh_token: Optional refresh token for auto-refresh
            
        Returns:
            Gmail API service object
        """
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=self.TOKEN_URL,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        
        return build("gmail", "v1", credentials=credentials)
    
    def validate_token(self, access_token: str) -> bool:
        """
        Validate if an access token is still valid.
        
        Args:
            access_token: Token to validate
            
        Returns:
            True if token is valid
        """
        try:
            response = requests.get(
                f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}",
                timeout=30,
            )
            return response.ok
        except Exception:
            return False


# Singleton instance
gmail_oauth_service = GmailOAuthService()
