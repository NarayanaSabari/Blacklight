# Configuration

## Overview

This document describes all configuration options for the Email Integration system.

## Environment Variables

### Required for Gmail Integration

```bash
# Google OAuth (Gmail API)
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5001/api/integrations/email/callback/gmail

# Production
# GOOGLE_OAUTH_REDIRECT_URI=https://api.blacklight.com/api/integrations/email/callback/gmail
```

### Required for Outlook Integration

```bash
# Microsoft OAuth (Graph API)
MICROSOFT_OAUTH_CLIENT_ID=your-azure-app-client-id
MICROSOFT_OAUTH_CLIENT_SECRET=your-azure-app-secret
MICROSOFT_OAUTH_REDIRECT_URI=http://localhost:5001/api/integrations/email/callback/outlook
MICROSOFT_OAUTH_TENANT=common  # or specific tenant ID for single-org apps

# Production
# MICROSOFT_OAUTH_REDIRECT_URI=https://api.blacklight.com/api/integrations/email/callback/outlook
```

### Token Encryption

```bash
# Encryption key for OAuth tokens (32 url-safe base64-encoded bytes)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=your-32-byte-base64-key
```

### Optional Configuration

```bash
# Email sync settings (defaults shown)
EMAIL_SYNC_FREQUENCY_MINUTES=15
EMAIL_SYNC_LOOKBACK_DAYS=7
EMAIL_SYNC_MAX_EMAILS_PER_BATCH=50
EMAIL_SYNC_ENABLED=true

# AI parsing (uses existing GOOGLE_API_KEY)
# GOOGLE_API_KEY=your-gemini-api-key  # Already configured for other features
```

## Settings Class Updates

Add to `config/settings.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Google OAuth (Gmail)
    google_oauth_client_id: str = Field(default="", env="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field(default="", env="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: str = Field(
        default="http://localhost:5001/api/integrations/email/callback/gmail",
        env="GOOGLE_OAUTH_REDIRECT_URI"
    )
    
    # Microsoft OAuth (Outlook)
    microsoft_oauth_client_id: str = Field(default="", env="MICROSOFT_OAUTH_CLIENT_ID")
    microsoft_oauth_client_secret: str = Field(default="", env="MICROSOFT_OAUTH_CLIENT_SECRET")
    microsoft_oauth_redirect_uri: str = Field(
        default="http://localhost:5001/api/integrations/email/callback/outlook",
        env="MICROSOFT_OAUTH_REDIRECT_URI"
    )
    microsoft_oauth_tenant: str = Field(default="common", env="MICROSOFT_OAUTH_TENANT")
    
    # Token encryption
    token_encryption_key: str = Field(default="", env="TOKEN_ENCRYPTION_KEY")
    
    # Email sync settings
    email_sync_frequency_minutes: int = Field(default=15, env="EMAIL_SYNC_FREQUENCY_MINUTES")
    email_sync_lookback_days: int = Field(default=7, env="EMAIL_SYNC_LOOKBACK_DAYS")
    email_sync_max_emails: int = Field(default=50, env="EMAIL_SYNC_MAX_EMAILS_PER_BATCH")
    email_sync_enabled: bool = Field(default=True, env="EMAIL_SYNC_ENABLED")
```

## Google Cloud Console Setup

### 1. Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to **APIs & Services** → **Enabled APIs**
4. Enable **Gmail API**
5. Navigate to **APIs & Services** → **Credentials**
6. Click **Create Credentials** → **OAuth client ID**
7. Select **Web application**
8. Add authorized redirect URIs:
   - Development: `http://localhost:5001/api/integrations/email/callback/gmail`
   - Production: `https://api.yourdomain.com/api/integrations/email/callback/gmail`
9. Copy Client ID and Client Secret

### 2. Configure OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type
3. Fill in app information:
   - App name: Blacklight HR
   - User support email: your email
   - Developer contact: your email
4. Add scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/userinfo.email`
5. Add test users (for development)
6. Submit for verification (for production)

## Azure Portal Setup (Outlook)

### 1. Register Application

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Configure:
   - Name: Blacklight Email Integration
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
   - Redirect URI: Web → `http://localhost:5001/api/integrations/email/callback/outlook`
5. Click **Register**
6. Copy **Application (client) ID**

### 2. Create Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add description and expiry
4. Copy the **Value** (not the ID)

### 3. Configure API Permissions

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add:
   - `Mail.Read`
   - `User.Read`
   - `offline_access`
6. Click **Grant admin consent** (if you're an admin)

## Docker Configuration

Add to `docker-compose.yml`:

```yaml
services:
  app:
    environment:
      # Gmail OAuth
      - GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID}
      - GOOGLE_OAUTH_CLIENT_SECRET=${GOOGLE_OAUTH_CLIENT_SECRET}
      - GOOGLE_OAUTH_REDIRECT_URI=${GOOGLE_OAUTH_REDIRECT_URI}
      
      # Outlook OAuth
      - MICROSOFT_OAUTH_CLIENT_ID=${MICROSOFT_OAUTH_CLIENT_ID}
      - MICROSOFT_OAUTH_CLIENT_SECRET=${MICROSOFT_OAUTH_CLIENT_SECRET}
      - MICROSOFT_OAUTH_REDIRECT_URI=${MICROSOFT_OAUTH_REDIRECT_URI}
      - MICROSOFT_OAUTH_TENANT=${MICROSOFT_OAUTH_TENANT:-common}
      
      # Encryption
      - TOKEN_ENCRYPTION_KEY=${TOKEN_ENCRYPTION_KEY}
      
      # Email sync
      - EMAIL_SYNC_ENABLED=${EMAIL_SYNC_ENABLED:-true}
```

## Production Checklist

- [ ] Generate strong `TOKEN_ENCRYPTION_KEY` (Fernet key)
- [ ] Set up HTTPS for OAuth redirect URIs
- [ ] Configure Google OAuth consent screen for production
- [ ] Submit Google OAuth app for verification
- [ ] Configure Azure app registration for production
- [ ] Update redirect URIs to production domains
- [ ] Enable email sync in environment
- [ ] Set appropriate sync frequency for load

## Generating Encryption Key

```bash
# Python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output example:
# 8sFzH6SxJvKlYqW3m9Bb2rNc5tUe7gXh1oA4zPdI0jM=
```

## Validation

Check configuration on startup:

```python
# app/__init__.py or startup
from config.settings import settings

def validate_email_integration_config():
    """Validate email integration configuration."""
    errors = []
    
    if settings.email_sync_enabled:
        # Check Gmail config
        if settings.google_oauth_client_id and not settings.google_oauth_client_secret:
            errors.append("GOOGLE_OAUTH_CLIENT_SECRET required when client ID is set")
        
        # Check Outlook config  
        if settings.microsoft_oauth_client_id and not settings.microsoft_oauth_client_secret:
            errors.append("MICROSOFT_OAUTH_CLIENT_SECRET required when client ID is set")
        
        # Check encryption key
        if not settings.token_encryption_key:
            errors.append("TOKEN_ENCRYPTION_KEY required for email integration")
    
    if errors:
        print("Email Integration Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True
```

## Feature Flags

Disable email integration per tenant:

```python
# In Tenant.settings JSON column
{
    "email_integration_enabled": true,
    "allowed_providers": ["gmail", "outlook"]  # or just ["gmail"]
}
```

Check in routes:

```python
@integration_bp.route('/email/initiate', methods=['POST'])
@require_portal_auth
@with_tenant_context
def initiate_email_oauth():
    tenant = db.session.get(Tenant, g.tenant_id)
    settings = tenant.settings or {}
    
    if not settings.get('email_integration_enabled', True):
        return error_response("Email integration is not enabled for this tenant", 403)
    
    # ... rest of handler
```
