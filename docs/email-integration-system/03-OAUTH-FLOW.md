# OAuth Flow Implementation

## Overview

This document details the OAuth2 implementation for Gmail and Outlook integration. Users connect their email accounts through a secure OAuth flow, and tokens are stored encrypted for background sync.

## OAuth Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           USER INITIATES OAUTH                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: User clicks "Connect Gmail" or "Connect Outlook" in Settings        │
│                                                                               │
│  Frontend: POST /api/integrations/email/initiate                              │
│  Body: { "provider": "gmail" | "outlook" }                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Backend generates OAuth URL with state token                         │
│                                                                               │
│  - Generate random state token                                                │
│  - Store state in Redis: integration_oauth:{state} → {user_id, tenant_id}    │
│  - TTL: 10 minutes                                                            │
│  - Return authorization URL                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: User redirected to Google/Microsoft login                            │
│                                                                               │
│  Gmail:   https://accounts.google.com/o/oauth2/v2/auth?...                   │
│  Outlook: https://login.microsoftonline.com/common/oauth2/v2.0/authorize?... │
│                                                                               │
│  User logs in and grants permission                                           │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Provider redirects to callback URL with auth code                    │
│                                                                               │
│  GET /api/integrations/email/callback/{provider}?code=xxx&state=yyy          │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Backend exchanges code for tokens                                    │
│                                                                               │
│  - Validate state token from Redis                                            │
│  - Exchange auth code for access_token + refresh_token                        │
│  - Get user email address from provider                                       │
│  - Encrypt tokens using Fernet                                                │
│  - Store in UserEmailIntegration table                                        │
│  - Delete state from Redis                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Redirect user back to frontend with success                          │
│                                                                               │
│  Redirect: {FRONTEND_URL}/settings/integrations?status=success&provider=gmail │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Gmail OAuth Configuration

### Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable Gmail API: APIs & Services → Library → Gmail API → Enable
4. Configure OAuth consent screen:
   - User Type: External
   - Scopes: `https://www.googleapis.com/auth/gmail.readonly`
   - App name, logo, privacy policy, etc.
5. Create OAuth credentials:
   - Application type: Web application
   - Authorized redirect URIs: `{BACKEND_URL}/api/integrations/email/callback/gmail`

### Environment Variables

```bash
# .env
GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5001/api/integrations/email/callback/gmail
```

### Gmail OAuth Code

```python
# app/services/oauth/gmail_oauth.py
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config.settings import settings
import secrets

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailOAuthService:
    """Handles Gmail OAuth2 flow."""
    
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_oauth_redirect_uri]
            }
        }
    
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri=settings.google_oauth_redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',  # Get refresh token
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent to get refresh token
        )
        
        return auth_url
    
    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri=settings.google_oauth_redirect_uri
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': credentials.expiry.isoformat() if credentials.expiry else None,
        }
    
    def get_user_email(self, access_token: str) -> str:
        """Get the email address of the authenticated user."""
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        return profile['emailAddress']
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret
        )
        
        credentials.refresh(Request())
        
        return {
            'access_token': credentials.token,
            'token_expiry': credentials.expiry.isoformat() if credentials.expiry else None,
        }
```

## Outlook OAuth Configuration

### Azure Portal Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to Azure Active Directory → App registrations → New registration
3. Configure:
   - Name: Blacklight Email Integration
   - Supported account types: Accounts in any organizational directory and personal Microsoft accounts
   - Redirect URI: Web → `{BACKEND_URL}/api/integrations/email/callback/outlook`
4. Note the Application (client) ID
5. Create client secret: Certificates & secrets → New client secret
6. Configure API permissions:
   - Microsoft Graph → Delegated permissions → Mail.Read
   - Grant admin consent (optional, depends on org settings)

### Environment Variables

```bash
# .env
MICROSOFT_OAUTH_CLIENT_ID=your_azure_client_id
MICROSOFT_OAUTH_CLIENT_SECRET=your_azure_client_secret
MICROSOFT_OAUTH_REDIRECT_URI=http://localhost:5001/api/integrations/email/callback/outlook
MICROSOFT_OAUTH_TENANT=common  # or specific tenant ID
```

### Outlook OAuth Code

```python
# app/services/oauth/outlook_oauth.py
import msal
import requests
from config.settings import settings

OUTLOOK_SCOPES = ['Mail.Read', 'User.Read', 'offline_access']

class OutlookOAuthService:
    """Handles Microsoft/Outlook OAuth2 flow."""
    
    def __init__(self):
        self.client_id = settings.microsoft_oauth_client_id
        self.client_secret = settings.microsoft_oauth_client_secret
        self.redirect_uri = settings.microsoft_oauth_redirect_uri
        self.authority = f"https://login.microsoftonline.com/{settings.microsoft_oauth_tenant}"
        
        self.msal_app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=OUTLOOK_SCOPES,
            state=state,
            redirect_uri=self.redirect_uri
        )
        return auth_url
    
    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        result = self.msal_app.acquire_token_by_authorization_code(
            code,
            scopes=OUTLOOK_SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        if 'error' in result:
            raise Exception(f"OAuth error: {result.get('error_description', result['error'])}")
        
        return {
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token'),
            'token_expiry': result.get('expires_in'),  # Seconds until expiry
        }
    
    def get_user_email(self, access_token: str) -> str:
        """Get the email address of the authenticated user."""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers
        )
        response.raise_for_status()
        user_data = response.json()
        return user_data.get('mail') or user_data.get('userPrincipalName')
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        # MSAL handles token caching, but for explicit refresh:
        accounts = self.msal_app.get_accounts()
        
        # Use refresh token directly via token endpoint
        token_url = f"{self.authority}/oauth2/v2.0/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': ' '.join(OUTLOOK_SCOPES)
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        result = response.json()
        
        return {
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token', refresh_token),
            'token_expiry': result.get('expires_in'),
        }
```

## Integration Routes

```python
# app/routes/integration_routes.py
from flask import Blueprint, request, redirect, g, jsonify
from app.middleware.auth import require_portal_auth, with_tenant_context
from app.services.oauth.gmail_oauth import GmailOAuthService
from app.services.oauth.outlook_oauth import OutlookOAuthService
from app.services.email_integration_service import EmailIntegrationService
from app.utils.redis_client import redis_client
from config.settings import settings
import secrets
import json

integration_bp = Blueprint('integrations', __name__, url_prefix='/api/integrations')

gmail_oauth = GmailOAuthService()
outlook_oauth = OutlookOAuthService()
email_integration_service = EmailIntegrationService()

OAUTH_STATE_TTL = 600  # 10 minutes


@integration_bp.route('/email/initiate', methods=['POST'])
@require_portal_auth
@with_tenant_context
def initiate_email_oauth():
    """Initiate OAuth flow for email integration."""
    data = request.get_json()
    provider = data.get('provider')
    
    if provider not in ['gmail', 'outlook']:
        return jsonify({'error': 'Invalid provider'}), 400
    
    # Generate state token
    state = secrets.token_urlsafe(32)
    
    # Store state in Redis with user context
    state_data = {
        'user_id': g.user_id,
        'tenant_id': g.tenant_id,
        'provider': provider
    }
    redis_client.setex(
        f'integration_oauth:{state}',
        OAUTH_STATE_TTL,
        json.dumps(state_data)
    )
    
    # Generate authorization URL
    if provider == 'gmail':
        auth_url = gmail_oauth.get_authorization_url(state)
    else:
        auth_url = outlook_oauth.get_authorization_url(state)
    
    return jsonify({'authorization_url': auth_url})


@integration_bp.route('/email/callback/<provider>', methods=['GET'])
def email_oauth_callback(provider: str):
    """Handle OAuth callback from provider."""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    frontend_url = settings.frontend_url
    
    # Handle OAuth errors
    if error:
        return redirect(f'{frontend_url}/settings/integrations?status=error&message={error}')
    
    if not code or not state:
        return redirect(f'{frontend_url}/settings/integrations?status=error&message=missing_params')
    
    # Validate state token
    state_key = f'integration_oauth:{state}'
    state_data_raw = redis_client.get(state_key)
    
    if not state_data_raw:
        return redirect(f'{frontend_url}/settings/integrations?status=error&message=invalid_state')
    
    state_data = json.loads(state_data_raw)
    redis_client.delete(state_key)  # One-time use
    
    user_id = state_data['user_id']
    tenant_id = state_data['tenant_id']
    
    try:
        # Exchange code for tokens
        if provider == 'gmail':
            tokens = gmail_oauth.exchange_code_for_tokens(code)
            email_address = gmail_oauth.get_user_email(tokens['access_token'])
        elif provider == 'outlook':
            tokens = outlook_oauth.exchange_code_for_tokens(code)
            email_address = outlook_oauth.get_user_email(tokens['access_token'])
        else:
            return redirect(f'{frontend_url}/settings/integrations?status=error&message=invalid_provider')
        
        # Save integration
        email_integration_service.create_or_update_integration(
            user_id=user_id,
            tenant_id=tenant_id,
            provider=provider,
            email_address=email_address,
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_expiry=tokens.get('token_expiry')
        )
        
        return redirect(f'{frontend_url}/settings/integrations?status=success&provider={provider}')
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return redirect(f'{frontend_url}/settings/integrations?status=error&message=token_exchange_failed')


@integration_bp.route('/email', methods=['GET'])
@require_portal_auth
@with_tenant_context
def list_email_integrations():
    """List user's email integrations."""
    integrations = email_integration_service.get_user_integrations(g.user_id)
    return jsonify({
        'integrations': [i.to_dict() for i in integrations]
    })


@integration_bp.route('/email/<int:integration_id>', methods=['DELETE'])
@require_portal_auth
@with_tenant_context
def disconnect_email_integration(integration_id: int):
    """Disconnect an email integration."""
    success = email_integration_service.disconnect_integration(
        integration_id=integration_id,
        user_id=g.user_id
    )
    
    if not success:
        return jsonify({'error': 'Integration not found'}), 404
    
    return jsonify({'message': 'Integration disconnected successfully'})


@integration_bp.route('/email/<int:integration_id>/sync', methods=['POST'])
@require_portal_auth
@with_tenant_context
def trigger_manual_sync(integration_id: int):
    """Trigger a manual email sync."""
    from app.inngest import inngest_client
    import inngest
    
    # Verify ownership
    integration = email_integration_service.get_integration_by_id(
        integration_id=integration_id,
        user_id=g.user_id
    )
    
    if not integration:
        return jsonify({'error': 'Integration not found'}), 404
    
    # Trigger Inngest sync job
    inngest_client.send_sync(
        inngest.Event(
            name="email/sync-user-inbox",
            data={
                'integration_id': integration_id,
                'user_id': g.user_id,
                'tenant_id': g.tenant_id,
                'manual_trigger': True
            }
        )
    )
    
    return jsonify({'message': 'Sync triggered successfully'})
```

## Token Refresh Strategy

Tokens are refreshed proactively before they expire:

```python
# app/services/email_integration_service.py
from datetime import datetime, timedelta

class EmailIntegrationService:
    
    TOKEN_REFRESH_BUFFER = timedelta(minutes=5)  # Refresh 5 min before expiry
    
    def get_valid_access_token(self, integration: UserEmailIntegration) -> str:
        """Get a valid access token, refreshing if necessary."""
        from app.utils.encryption import token_encryption
        
        # Check if token needs refresh
        if integration.token_expiry:
            if datetime.utcnow() >= (integration.token_expiry - self.TOKEN_REFRESH_BUFFER):
                self._refresh_token(integration)
        
        return token_encryption.decrypt(integration.access_token_encrypted)
    
    def _refresh_token(self, integration: UserEmailIntegration):
        """Refresh the access token."""
        from app.utils.encryption import token_encryption
        from app.services.oauth.gmail_oauth import GmailOAuthService
        from app.services.oauth.outlook_oauth import OutlookOAuthService
        
        refresh_token = token_encryption.decrypt(integration.refresh_token_encrypted)
        
        if integration.provider == 'gmail':
            new_tokens = GmailOAuthService().refresh_access_token(refresh_token)
        else:
            new_tokens = OutlookOAuthService().refresh_access_token(refresh_token)
        
        # Update stored tokens
        integration.access_token_encrypted = token_encryption.encrypt(new_tokens['access_token'])
        if new_tokens.get('refresh_token'):
            integration.refresh_token_encrypted = token_encryption.encrypt(new_tokens['refresh_token'])
        if new_tokens.get('token_expiry'):
            if isinstance(new_tokens['token_expiry'], int):
                integration.token_expiry = datetime.utcnow() + timedelta(seconds=new_tokens['token_expiry'])
            else:
                integration.token_expiry = datetime.fromisoformat(new_tokens['token_expiry'])
        
        db.session.commit()
```

## Security Considerations

1. **State Token**: Random, one-time use, stored in Redis with TTL
2. **Token Encryption**: All OAuth tokens encrypted at rest using Fernet
3. **HTTPS Only**: OAuth callbacks must use HTTPS in production
4. **Scope Limitation**: Only request `readonly`/`Mail.Read` - no write access
5. **User Verification**: Callback validates state and associates with correct user
6. **Token Rotation**: Refresh tokens updated when provider rotates them

## Required Dependencies

```txt
# requirements.txt additions
google-auth>=2.22.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.95.0
msal>=1.24.0
cryptography>=41.0.0
```
