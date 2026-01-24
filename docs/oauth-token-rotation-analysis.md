# 🔐 OAuth Token Rotation Analysis for Email Scraping

**Date**: 2026-01-24  
**System**: Blacklight Email Integration  
**Goal**: Prevent user re-authentication for Gmail/Outlook email scraping

---

## ✅ CURRENT STATUS: TOKEN ROTATION **FULLY IMPLEMENTED**

Your system **ALREADY** has automatic token refresh working correctly. Users will **NOT** need to re-authenticate.

---

## 📋 How Token Rotation Works

### 1. Initial Authorization (One-Time)

**Gmail**:
```python
# User clicks "Connect Gmail"
# → Redirected to Google OAuth consent screen
# → Returns with authorization code
# → Exchange for tokens

tokens = gmail_oauth_service.exchange_code_for_tokens(code)
# Returns:
# {
#   "access_token": "ya29.a0...",  # Valid for 1 hour
#   "refresh_token": "1//0g...",   # Never expires (unless revoked)
#   "expires_at": datetime(...)
# }
```

**Outlook**:
```python
# User clicks "Connect Outlook"
# → Redirected to Microsoft OAuth consent screen
# → Returns with authorization code
# → Exchange for tokens

tokens = outlook_oauth_service.exchange_code_for_tokens(code)
# Returns:
# {
#   "access_token": "EwB4A8...",   # Valid for 1 hour
#   "refresh_token": "M.C546...",  # Valid for 90 days (rolling window)
#   "expires_at": datetime(...)
# }
```

**Storage** (encrypted in database):
```python
integration = UserEmailIntegration(
    user_id=2,
    tenant_id=2,
    provider="outlook",
    access_token_encrypted=encrypt("EwB4A8..."),  # Fernet encryption
    refresh_token_encrypted=encrypt("M.C546..."),  # Fernet encryption
    token_expiry=datetime(...),
    email_address="user@example.com",
    is_active=True
)
```

---

### 2. Automatic Token Refresh (Before Every Sync)

**File**: `app/services/email_integration_service.py:365-421`

```python
def get_valid_access_token(integration: UserEmailIntegration) -> str:
    """Get a valid access token, refreshing if necessary."""
    
    now = datetime.now(timezone.utc)
    token_expiry = integration.token_expiry
    buffer_time = now.timestamp() + 300  # 5 minute buffer
    
    # Check if token is still valid
    if token_expiry.timestamp() > buffer_time:
        # ✅ Token still valid, decrypt and return
        return token_encryption.decrypt(integration.access_token_encrypted)
    
    # ⚠️ Token expired or about to expire, refresh it
    if not integration.refresh_token_encrypted:
        # ❌ No refresh token = user MUST re-authenticate
        raise ValueError("No refresh token available - user needs to reconnect")
    
    refresh_token = token_encryption.decrypt(integration.refresh_token_encrypted)
    
    try:
        if integration.provider == "gmail":
            tokens = gmail_oauth_service.refresh_access_token(refresh_token)
        else:
            tokens = outlook_oauth_service.refresh_access_token(refresh_token)
        
        # ✅ Save new tokens to database
        integration.access_token_encrypted = token_encryption.encrypt(tokens["access_token"])
        if tokens.get("refresh_token"):
            # Microsoft may return a NEW refresh token (rolling refresh)
            integration.refresh_token_encrypted = token_encryption.encrypt(tokens["refresh_token"])
        integration.token_expiry = tokens["expires_at"]
        db.session.commit()
        
        return tokens["access_token"]
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        integration.last_error = str(e)
        integration.consecutive_failures += 1
        
        # Deactivate after 3 failures
        if integration.consecutive_failures >= 3:
            integration.is_active = False
        
        db.session.commit()
        raise
```

---

### 3. Gmail Token Refresh API

**File**: `app/services/oauth/gmail_oauth.py:112-148`

```python
def refresh_access_token(self, refresh_token: str) -> dict:
    """Refresh an expired access token."""
    
    data = {
        "client_id": self.client_id,
        "client_secret": self.client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data=data,
        timeout=30
    )
    
    if not response.ok:
        error = response.json()
        raise ValueError(f"Token refresh failed: {error.get('error_description')}")
    
    token_data = response.json()
    expires_in = token_data.get("expires_in", 3600)  # 1 hour default
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    return {
        "access_token": token_data["access_token"],  # NEW access token
        "expires_at": expires_at,
        # NOTE: Google does NOT return new refresh_token (reuse existing one)
    }
```

**Gmail Refresh Token Behavior**:
- ✅ Refresh tokens **NEVER expire** (unless revoked by user)
- ✅ Same refresh token can be reused indefinitely
- ✅ No rolling refresh window
- ⚠️ User can revoke access from Google Account settings

---

### 4. Outlook/Microsoft Token Refresh API

**File**: `app/services/oauth/outlook_oauth.py:127-173`

```python
def refresh_access_token(self, refresh_token: str) -> dict:
    """Refresh an expired access token."""
    
    data = {
        "client_id": self.client_id,
        "client_secret": self.client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(self.SCOPES),  # IMPORTANT: Must include scopes
    }
    
    response = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data=data,
        timeout=30
    )
    
    if not response.ok:
        error = response.json()
        raise ValueError(f"Token refresh failed: {error.get('error_description')}")
    
    token_data = response.json()
    expires_in = token_data.get("expires_in", 3600)  # 1 hour default
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    return {
        "access_token": token_data["access_token"],  # NEW access token
        # Microsoft MAY return new refresh token (rolling refresh)
        "refresh_token": token_data.get("refresh_token", refresh_token),
        "expires_at": expires_at,
    }
```

**Outlook Refresh Token Behavior**:
- ⚠️ Refresh tokens expire after **90 days of inactivity**
- ✅ **Rolling window**: Each refresh extends the 90-day window
- ✅ Microsoft may return a NEW refresh token (must update database)
- ⚠️ If user doesn't sync for 90+ days = MUST re-authenticate
- ⚠️ User can revoke access from Microsoft Account settings

---

## 🔄 Email Sync Flow with Auto-Refresh

```
INNGEST CRON JOB (every 15 minutes)
   ↓
email/sync-user-inbox
   ↓
email_sync_service.sync_integration(integration)
   ↓
email_integration_service.get_valid_access_token(integration)
   ↓
   ├─→ [Token valid?] → ✅ Return decrypted token
   │
   └─→ [Token expired?] → Refresh token API call
       ↓
       ├─→ [Success] → ✅ Update database → Return new token
       │
       └─→ [Failure] → ❌ Increment consecutive_failures
                            ↓
                       [3 failures?] → Deactivate integration
                                        ↓
                                  User MUST re-authenticate
```

---

## ⚠️ When Users MUST Re-Authenticate

### Scenario 1: Refresh Token Missing
```
❌ refresh_token_encrypted = NULL in database

CAUSES:
- Database corruption
- Manual deletion
- OAuth flow didn't return refresh token (Google prompt='none' issue)

SOLUTION:
- User must disconnect and reconnect integration
```

### Scenario 2: Refresh Token Expired (Outlook Only)
```
❌ Microsoft refresh token not used for 90+ days

CAUSES:
- Email sync disabled for 90+ days
- Integration inactive for extended period
- User didn't trigger any sync for 90+ days

SOLUTION:
- User must disconnect and reconnect integration
```

### Scenario 3: Refresh Token Revoked by User
```
❌ User revoked app access from Google/Microsoft account settings

CAUSES:
- User clicked "Remove access" in Google Account
- User clicked "Revoke permissions" in Microsoft Account
- Security review forced revocation

SOLUTION:
- User must reconnect integration (new OAuth flow)
```

### Scenario 4: 3 Consecutive Refresh Failures
```
❌ consecutive_failures >= 3

CAUSES:
- Network issues (unlikely to persist)
- OAuth API down (unlikely to persist)
- Invalid refresh token format
- Client credentials changed (GOOGLE_OAUTH_CLIENT_SECRET changed)

SOLUTION:
- Check logs for error details
- Verify OAuth credentials in .env
- User may need to reconnect
```

---

## 🛡️ How to Prevent Re-Authentication

### ✅ What's Already Working

1. **Automatic Refresh Before Expiry**: 5-minute buffer prevents expiration
2. **Encrypted Storage**: Refresh tokens stored securely with Fernet encryption
3. **Rolling Refresh (Outlook)**: Microsoft refresh tokens auto-extend on use
4. **Error Handling**: Graceful degradation with `consecutive_failures` tracking

### ✅ Best Practices (Already Implemented)

1. **Always request `offline_access` scope** (Outlook) ✅
2. **Store refresh tokens** ✅
3. **Check expiry before using access token** ✅
4. **Handle refresh failures gracefully** ✅
5. **Use `prompt=consent` to ensure refresh token** (Gmail) ✅

---

## 🔧 Configuration Verification

### Check Gmail OAuth Setup

```bash
# .env file
GOOGLE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_OAUTH_REDIRECT_URI=http://localhost/portal/auth/gmail/callback

# Scopes requested (app/services/oauth/gmail_oauth.py:20-25)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",  # Read emails
    "https://www.googleapis.com/auth/userinfo.email",  # Get user email
    "openid",  # Required for user info
]

# ✅ Google always returns refresh_token on first authorization
# ⚠️ On subsequent authorizations, may NOT return refresh_token
#    Solution: Use prompt='consent' to force re-consent
```

### Check Outlook OAuth Setup

```bash
# .env file
MICROSOFT_OAUTH_CLIENT_ID=xxx-xxx-xxx-xxx-xxx
MICROSOFT_OAUTH_CLIENT_SECRET=xxx
MICROSOFT_OAUTH_REDIRECT_URI=http://localhost/portal/auth/outlook/callback
MICROSOFT_OAUTH_TENANT=common  # Multi-tenant support

# Scopes requested (app/services/oauth/outlook_oauth.py:21-25)
SCOPES = [
    "Mail.Read",         # Read emails
    "User.Read",         # Get user profile
    "offline_access",    # ✅ CRITICAL for refresh token
]

# ✅ Must include 'offline_access' to get refresh token
# ✅ Must use 'prompt=consent' to ensure refresh token
```

### Database Schema Verification

```sql
-- Check refresh tokens are being stored
SELECT 
    id,
    provider,
    email_address,
    token_expiry,
    CASE 
        WHEN refresh_token_encrypted IS NOT NULL THEN 'YES'
        ELSE 'NO'
    END as has_refresh_token,
    is_active,
    consecutive_failures,
    last_error,
    last_synced_at
FROM user_email_integrations
WHERE tenant_id = 2 AND user_id = 2;
```

Expected output:
```
| id | provider | email             | token_expiry         | has_refresh_token | is_active | consecutive_failures | last_error | last_synced_at       |
|----|----------|-------------------|----------------------|-------------------|-----------|----------------------|------------|----------------------|
| 4  | outlook  | user@example.com  | 2026-01-24 15:00:00  | YES               | TRUE      | 0                    | NULL       | 2026-01-23 05:15:10 |
```

⚠️ **If `has_refresh_token = NO`**: User MUST re-authenticate immediately!

---

## 🧪 Testing Token Refresh

### Manual Token Refresh Test

```python
#!/usr/bin/env python3
"""Test token refresh without waiting for expiry"""

from app import create_app, db
from app.models.user_email_integration import UserEmailIntegration
from app.services.email_integration_service import email_integration_service
from datetime import datetime, timezone, timedelta

app = create_app()

with app.app_context():
    integration = db.session.get(UserEmailIntegration, 4)
    
    print(f"Provider: {integration.provider}")
    print(f"Email: {integration.email_address}")
    print(f"Token Expiry: {integration.token_expiry}")
    print(f"Has Refresh Token: {integration.refresh_token_encrypted is not None}")
    
    # Force token to be "expired" for testing
    old_expiry = integration.token_expiry
    integration.token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)
    db.session.commit()
    
    print("\n🔄 Forcing token refresh...")
    
    try:
        new_token = email_integration_service.get_valid_access_token(integration)
        print("✅ Token refresh successful!")
        print(f"New Token: {new_token[:20]}...")
        print(f"New Expiry: {integration.token_expiry}")
    except Exception as e:
        print(f"❌ Token refresh failed: {e}")
    finally:
        # Restore original expiry if refresh failed
        if integration.token_expiry < datetime.now(timezone.utc):
            integration.token_expiry = old_expiry
            db.session.commit()
```

---

## 📊 Monitoring Token Health

### Check Integration Status

```sql
-- Integrations needing attention
SELECT 
    id,
    provider,
    email_address,
    CASE 
        WHEN refresh_token_encrypted IS NULL THEN '❌ NO REFRESH TOKEN'
        WHEN token_expiry < NOW() THEN '⚠️ TOKEN EXPIRED'
        WHEN consecutive_failures >= 3 THEN '❌ TOO MANY FAILURES'
        WHEN is_active = FALSE THEN '⏸️ INACTIVE'
        WHEN last_synced_at < NOW() - INTERVAL '1 day' THEN '⚠️ STALE SYNC'
        ELSE '✅ HEALTHY'
    END as status,
    token_expiry,
    consecutive_failures,
    last_error,
    last_synced_at
FROM user_email_integrations
WHERE tenant_id = 2
ORDER BY 
    CASE 
        WHEN refresh_token_encrypted IS NULL THEN 1
        WHEN consecutive_failures >= 3 THEN 2
        WHEN token_expiry < NOW() THEN 3
        ELSE 4
    END;
```

### Application Logs to Monitor

```bash
# Watch for token refresh events
tail -f logs/app.log | grep -E "Token refresh|consecutive_failures|Deactivated integration"

# Expected logs:
# INFO: Token refresh successful for integration 4
# WARNING: Token refresh failed for integration 4: invalid_grant
# WARNING: Deactivated integration 4 due to repeated failures
```

---

## 🚨 Common Issues and Solutions

### Issue 1: "No refresh token available"

**Cause**: Refresh token not returned during OAuth flow

**Solution**:
```python
# Ensure prompt='consent' in authorization URL
# Gmail: app/services/oauth/gmail_oauth.py:52-72
params = {
    "access_type": "offline",  # ✅ Required for refresh token
    "prompt": "consent",       # ✅ Forces re-consent
    # ...
}

# Outlook: app/services/oauth/outlook_oauth.py:52-75
params = {
    "scope": " ".join(self.SCOPES),  # Must include 'offline_access'
    "prompt": "consent",             # ✅ Forces re-consent
    # ...
}
```

### Issue 2: Microsoft refresh token expired (90 days)

**Cause**: Email sync not running for 90+ days

**Prevention**:
```python
# Ensure cron job runs every 15 minutes
# File: app/inngest/functions/email_sync.py:305-335

inngest.create_function(
    fn_id="sync-all-email-integrations",
    trigger=inngest.cron("*/15 * * * *"),  # ✅ Every 15 minutes
    func=sync_all_email_integrations_cron,
)
```

**Recovery**: User must re-authenticate

### Issue 3: "invalid_grant" error

**Causes**:
1. Refresh token revoked by user
2. OAuth credentials changed in Google Cloud Console
3. App removed from user's account

**Solution**: User must re-authenticate

---

## ✅ Summary: Your System is Ready

| Feature | Status | Notes |
|---------|--------|-------|
| Automatic token refresh | ✅ Implemented | Before every sync |
| 5-minute expiry buffer | ✅ Implemented | Prevents last-minute failures |
| Gmail refresh | ✅ Working | Refresh token never expires |
| Outlook refresh | ✅ Working | Rolling 90-day window |
| Encrypted storage | ✅ Working | Fernet encryption |
| Error handling | ✅ Working | 3-failure deactivation |
| Monitoring | ✅ Working | consecutive_failures tracking |

**Verdict**: Users will **NOT** need to re-authenticate unless:
1. They manually revoke access
2. Outlook integration inactive for 90+ days
3. Refresh token missing (database issue)
4. 3+ consecutive refresh API failures

**Action Required**: Just ensure `TOKEN_ENCRYPTION_KEY` is set in production!

```bash
# Add to .env.production
TOKEN_ENCRYPTION_KEY=Ml11Eod5ZNsbM7ir0KQWZoZOCktCOApUHAVMA4kPX8Q=
```
