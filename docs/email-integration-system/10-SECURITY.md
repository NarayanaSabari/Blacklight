# Security Considerations

## Overview

This document outlines security measures and best practices for the Email Integration system.

## OAuth Security

### 1. State Token Protection (CSRF)

```python
# State tokens prevent CSRF attacks during OAuth flow

# Generation
state = secrets.token_urlsafe(32)  # 256-bit random token

# Storage in Redis with TTL
redis_client.setex(
    f'integration_oauth:{state}',
    600,  # 10 minute TTL
    json.dumps({'user_id': user_id, 'tenant_id': tenant_id})
)

# Validation on callback
state_data = redis_client.get(f'integration_oauth:{state}')
if not state_data:
    raise SecurityError("Invalid or expired state token")

# One-time use
redis_client.delete(f'integration_oauth:{state}')
```

### 2. Token Encryption at Rest

All OAuth tokens are encrypted before storage using Fernet symmetric encryption:

```python
from cryptography.fernet import Fernet

class TokenEncryption:
    def __init__(self):
        # Key from environment variable
        self.fernet = Fernet(settings.token_encryption_key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt token for storage."""
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt token for use."""
        return self.fernet.decrypt(ciphertext.encode()).decode()
```

**Key Management:**
- Encryption key stored in environment variable, never in code
- Key should be rotated periodically (requires re-encryption migration)
- Use separate keys per environment (dev/staging/prod)

### 3. Minimal Scope Principle

Only request read-only access:

| Provider | Scopes | Purpose |
|----------|--------|---------|
| Gmail | `gmail.readonly` | Read emails only, no send/delete |
| Outlook | `Mail.Read` | Read emails only, no modifications |
| Both | `offline_access` | Get refresh tokens for background sync |

### 4. HTTPS Enforcement

OAuth redirect URIs must use HTTPS in production:

```python
# In production config
if not settings.google_oauth_redirect_uri.startswith('https://'):
    if settings.environment == 'production':
        raise ConfigurationError("OAuth redirect must use HTTPS in production")
```

## Data Security

### 1. Tenant Isolation

Email-sourced jobs are strictly isolated by tenant:

```python
# Query always includes tenant filter
jobs = (
    db.session.query(JobPosting)
    .filter(JobPosting.is_email_sourced == True)
    .filter(JobPosting.source_tenant_id == g.tenant_id)  # Enforced
    .all()
)
```

### 2. User Authorization

Only the integration owner can manage their integration:

```python
def verify_integration_ownership(integration_id: int, user_id: int) -> bool:
    integration = db.session.get(UserEmailIntegration, integration_id)
    if not integration:
        return False
    return integration.user_id == user_id
```

### 3. Email Content Handling

- Email bodies are processed but not permanently stored
- Only extracted job data is saved
- Original email metadata (subject, sender) stored for attribution

```python
# What we store
job = JobPosting(
    source_email_subject=email.subject[:500],  # Truncated
    source_email_sender=email.sender[:255],    # Email only
    source_email_date=email.received_at,
    source_email_id=email.message_id,          # For deduplication
    # email body is NOT stored
)
```

### 4. Processed Email Tracking

Store minimal metadata for deduplication:

```python
class ProcessedEmail(BaseModel):
    email_message_id = db.Column(db.String(255))  # RFC 2822 ID
    email_subject = db.Column(db.String(500))      # Truncated
    email_sender = db.Column(db.String(255))       # Email address only
    # Full email body is NOT stored
```

## Access Control

### 1. Role-Based Permissions

| Action | TENANT_ADMIN | MANAGER | TEAM_LEAD | RECRUITER |
|--------|--------------|---------|-----------|-----------|
| Connect email | ✅ | ✅ | ✅ | ✅ |
| View own integration | ✅ | ✅ | ✅ | ✅ |
| View all integrations | ✅ | ❌ | ❌ | ❌ |
| View email jobs | ✅ | ✅ | ✅ | ✅ |
| Delete email jobs | ✅ | ✅ | ❌ | ❌ |

### 2. Middleware Stack

```python
@integration_bp.route('/email/<int:integration_id>', methods=['DELETE'])
@require_portal_auth           # JWT validation
@with_tenant_context           # Tenant isolation
def disconnect_integration(integration_id: int):
    # Additional ownership check
    if not verify_integration_ownership(integration_id, g.user_id):
        return error_response("Not authorized", 403)
```

## Token Lifecycle

### 1. Token Expiry Handling

```python
def get_valid_access_token(integration: UserEmailIntegration) -> str:
    """Get valid token, refreshing if needed."""
    
    # Check expiry with buffer
    if integration.token_expiry:
        buffer = timedelta(minutes=5)
        if datetime.utcnow() >= (integration.token_expiry - buffer):
            # Proactively refresh
            refresh_token(integration)
    
    return decrypt(integration.access_token_encrypted)
```

### 2. Refresh Token Revocation

When user disconnects:

```python
def disconnect_integration(integration_id: int, user_id: int):
    integration = db.session.get(UserEmailIntegration, integration_id)
    
    # Revoke token at provider (best effort)
    try:
        if integration.provider == 'gmail':
            revoke_google_token(integration)
        else:
            revoke_microsoft_token(integration)
    except Exception:
        pass  # Continue with deletion even if revocation fails
    
    # Delete from database
    db.session.delete(integration)
    db.session.commit()
```

### 3. Token Rotation on Refresh

Some providers rotate refresh tokens. Always store new tokens:

```python
def refresh_token(integration):
    new_tokens = oauth_service.refresh(
        decrypt(integration.refresh_token_encrypted)
    )
    
    integration.access_token_encrypted = encrypt(new_tokens['access_token'])
    
    # Store new refresh token if rotated
    if new_tokens.get('refresh_token'):
        integration.refresh_token_encrypted = encrypt(new_tokens['refresh_token'])
    
    db.session.commit()
```

## Error Handling

### 1. Token Expiry Errors

```python
class TokenExpiredError(Exception):
    """Raised when refresh token is invalid."""
    pass

def handle_token_error(integration):
    """Handle token-related errors."""
    integration.is_active = False
    integration.last_sync_status = 'failed'
    integration.last_sync_error = 'Authentication expired. Please reconnect.'
    db.session.commit()
    
    # Notify user via Inngest
    inngest_client.send_sync(
        inngest.Event(
            name="email/integration-error",
            data={
                'integration_id': integration.id,
                'error_type': 'token_expired'
            }
        )
    )
```

### 2. Rate Limit Handling

```python
def handle_rate_limit(integration, retry_after: int):
    """Handle API rate limit errors."""
    # Exponential backoff already handled by Inngest retries
    integration.last_sync_error = f'Rate limited. Retry after {retry_after}s'
    db.session.commit()
    
    # Re-raise to trigger Inngest retry
    raise Exception(f"Rate limited: retry after {retry_after}s")
```

## Audit Logging

Log security-relevant events:

```python
from app.services.audit_log_service import AuditLogService

# On integration create
AuditLogService.log_action(
    action='EMAIL_INTEGRATION_CONNECTED',
    entity_type='UserEmailIntegration',
    entity_id=integration.id,
    user_id=user_id,
    tenant_id=tenant_id,
    details={'provider': provider, 'email': email_address}
)

# On disconnect
AuditLogService.log_action(
    action='EMAIL_INTEGRATION_DISCONNECTED',
    entity_type='UserEmailIntegration',
    entity_id=integration_id,
    user_id=user_id,
    tenant_id=tenant_id
)

# On token refresh failure
AuditLogService.log_action(
    action='EMAIL_INTEGRATION_AUTH_FAILED',
    entity_type='UserEmailIntegration',
    entity_id=integration.id,
    user_id=integration.user_id,
    tenant_id=integration.tenant_id,
    details={'error': 'Token refresh failed'}
)
```

## Security Checklist

### Development
- [ ] Use test OAuth credentials (not production)
- [ ] Use localhost redirect URIs
- [ ] Test with test email accounts only

### Pre-Production
- [ ] Generate strong TOKEN_ENCRYPTION_KEY
- [ ] Verify HTTPS on all OAuth redirect URIs
- [ ] Review OAuth scopes (minimal required)
- [ ] Test token refresh flow
- [ ] Test disconnection flow
- [ ] Verify tenant isolation in queries

### Production
- [ ] Enable audit logging
- [ ] Set up monitoring for auth failures
- [ ] Configure alerts for rate limit errors
- [ ] Document token rotation policy
- [ ] Plan for encryption key rotation
- [ ] Regular security review of OAuth apps

## Incident Response

### Compromised Encryption Key

1. Generate new encryption key
2. Stop all email sync jobs
3. Run migration to re-encrypt all tokens with new key
4. Update environment variable
5. Restart services
6. Resume sync jobs

### Compromised OAuth Credentials

1. Revoke credentials at provider (Google/Microsoft)
2. Generate new OAuth credentials
3. Update environment variables
4. Users will need to re-authenticate
5. Notify affected users

### Data Breach

1. Disable email sync feature
2. Revoke all integration tokens at providers
3. Delete encrypted tokens from database
4. Audit access logs
5. Notify affected users per compliance requirements
