"""OAuth services for email integration."""

from .gmail_oauth import GmailOAuthService
from .outlook_oauth import OutlookOAuthService

__all__ = [
    "GmailOAuthService",
    "OutlookOAuthService",
]
