# Microsoft Email Integration Setup Guide

This guide walks you through setting up Microsoft/Outlook email integration for Blacklight using Azure Active Directory (Entra ID) and Microsoft Graph API.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Create Azure App Registration](#step-1-create-azure-app-registration)
4. [Step 2: Configure API Permissions](#step-2-configure-api-permissions)
5. [Step 3: Create Client Secret](#step-3-create-client-secret)
6. [Step 4: Configure Redirect URI](#step-4-configure-redirect-uri)
7. [Step 5: Configure Environment Variables](#step-5-configure-environment-variables)
8. [Step 6: Deploy and Test](#step-6-deploy-and-test)
9. [Troubleshooting](#troubleshooting)
10. [Security Best Practices](#security-best-practices)

---

## Overview

Blacklight integrates with Microsoft 365/Outlook to automatically sync and parse job-related emails from recruiter inboxes. This integration uses:

- **Microsoft Identity Platform (OAuth 2.0)** for secure authentication
- **Microsoft Graph API** for reading emails
- **Azure App Registration** for managing OAuth credentials

### How It Works

1. User clicks "Connect Outlook" in Blacklight settings
2. User is redirected to Microsoft login and grants permissions
3. Blacklight receives OAuth tokens and stores them securely (encrypted)
4. Background jobs periodically sync emails and parse job postings
5. Parsed jobs are matched with candidates automatically

---

## Prerequisites

- **Azure Account** with access to Azure Active Directory (Entra ID)
- **Microsoft 365 Business** or **Microsoft 365 Enterprise** subscription (for mailbox access)
- **Admin consent** capability (for granting API permissions)
- **Blacklight** deployed and accessible via HTTPS (recommended for production)

---

## Step 1: Create Azure App Registration

### 1.1 Navigate to Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Sign in with your Azure account

### 1.2 Open App Registrations

1. Search for **"App registrations"** in the top search bar
2. Click on **App registrations** under Services

### 1.3 Create New Registration

1. Click **+ New registration**
2. Fill in the registration form:

| Field | Value |
|-------|-------|
| **Name** | `Blacklight Email Integration` (or your preferred name) |
| **Supported account types** | Choose based on your needs (see below) |
| **Redirect URI** | Leave blank for now (we'll configure this later) |

#### Account Type Options:

| Option | Use Case |
|--------|----------|
| **Single tenant** | Only users from your organization can use this app |
| **Multitenant** | Users from any Azure AD organization can use this app |
| **Multitenant + Personal** | Any Azure AD org + personal Microsoft accounts (Outlook.com, Hotmail, etc.) |

> **Recommendation**: For most business use cases, choose **"Accounts in any organizational directory (Any Azure AD directory - Multitenant)"**

3. Click **Register**

### 1.4 Note Your Application Details

After registration, note these values from the **Overview** page:

| Field | Environment Variable |
|-------|---------------------|
| **Application (client) ID** | `MICROSOFT_OAUTH_CLIENT_ID` |
| **Directory (tenant) ID** | Used in `MICROSOFT_OAUTH_TENANT` (or use `common`) |

---

## Step 2: Configure API Permissions

### 2.1 Navigate to API Permissions

1. In your app registration, click **API permissions** in the left sidebar
2. Click **+ Add a permission**

### 2.2 Add Microsoft Graph Permissions

1. Select **Microsoft Graph**
2. Select **Delegated permissions** (user-level access)
3. Search for and add these permissions:

| Permission | Purpose |
|------------|---------|
| `Mail.Read` | Read user's emails to sync job postings |
| `User.Read` | Get user's email address and profile info |
| `offline_access` | Obtain refresh tokens for background sync |

4. Click **Add permissions**

### 2.3 Grant Admin Consent (If Required)

If your organization requires admin consent for these permissions:

1. Click **Grant admin consent for [Your Organization]**
2. Confirm by clicking **Yes**

> **Note**: The `Mail.Read` permission may require admin consent depending on your organization's policies.

### 2.4 Verify Permissions

Your API permissions should look like this:

```
Microsoft Graph (3)
├── Mail.Read         Delegated    ✓ Granted
├── offline_access    Delegated    ✓ Granted
└── User.Read         Delegated    ✓ Granted
```

---

## Step 3: Create Client Secret

### 3.1 Navigate to Certificates & Secrets

1. In your app registration, click **Certificates & secrets** in the left sidebar
2. Click **+ New client secret**

### 3.2 Create Secret

1. Fill in the form:
   - **Description**: `Blacklight Production` (or descriptive name)
   - **Expires**: Choose based on your security policy (recommended: 24 months)

2. Click **Add**

### 3.3 Copy Secret Value

> **IMPORTANT**: Copy the **Value** immediately! It will only be shown once.

| Field | Environment Variable |
|-------|---------------------|
| **Value** (the secret itself) | `MICROSOFT_OAUTH_CLIENT_SECRET` |

Store this securely - you'll need it for the environment configuration.

---

## Step 4: Configure Redirect URI

### 4.1 Navigate to Authentication

1. In your app registration, click **Authentication** in the left sidebar
2. Click **+ Add a platform**
3. Select **Web**

### 4.2 Configure Web Platform

Fill in the redirect URI based on your deployment:

| Environment | Redirect URI |
|-------------|--------------|
| **Production** | `https://your-domain.com/api/integrations/email/callback/outlook` |
| **Local Dev** | `http://localhost:5001/api/integrations/email/callback/outlook` |

> **Note**: Replace `your-domain.com` with your actual domain (e.g., `blacklight.sivaganesh.in`)

### 4.3 Configure Additional Settings

Under **Implicit grant and hybrid flows**:
- Leave both checkboxes **unchecked** (we use authorization code flow)

Under **Advanced settings**:
- **Allow public client flows**: **No** (we're using a confidential client)

4. Click **Configure**

### 4.4 Add Additional Redirect URIs (Optional)

If you need multiple environments:

1. Under **Web** > **Redirect URIs**, click **Add URI**
2. Add additional URIs for staging, development, etc.

Example redirect URIs:
```
https://blacklight.sivaganesh.in/api/integrations/email/callback/outlook
https://staging.blacklight.com/api/integrations/email/callback/outlook
http://localhost:5001/api/integrations/email/callback/outlook
```

---

## Step 5: Configure Environment Variables

### 5.1 Required Environment Variables

Add these to your `.env.production` file:

```bash
# ============================================================
# Microsoft OAuth (Outlook Email Integration)
# ============================================================

# Application (client) ID from Azure App Registration
MICROSOFT_OAUTH_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Client secret value (NOT the secret ID!)
MICROSOFT_OAUTH_CLIENT_SECRET=your-client-secret-value

# Redirect URI - must match exactly what's configured in Azure
MICROSOFT_OAUTH_REDIRECT_URI=https://your-domain.com/api/integrations/email/callback/outlook

# Tenant configuration
# Options:
#   - "common" = Any Azure AD + personal Microsoft accounts
#   - "organizations" = Any Azure AD organization only
#   - "consumers" = Personal Microsoft accounts only
#   - "<tenant-id>" = Specific organization only
MICROSOFT_OAUTH_TENANT=common
```

### 5.2 Token Encryption Key

Ensure you have a token encryption key for secure storage:

```bash
# Generate a secure 32-byte key (base64 encoded)
# Run: python -c "import secrets; print(secrets.token_urlsafe(32))"
TOKEN_ENCRYPTION_KEY=your-32-byte-base64-encoded-key
```

### 5.3 Example Complete Configuration

```bash
# Microsoft OAuth
MICROSOFT_OAUTH_CLIENT_ID=a1b2c3d4-e5f6-7890-abcd-ef1234567890
MICROSOFT_OAUTH_CLIENT_SECRET=abc123~secretvalue~xyz789
MICROSOFT_OAUTH_REDIRECT_URI=https://blacklight.sivaganesh.in/api/integrations/email/callback/outlook
MICROSOFT_OAUTH_TENANT=common

# Token Encryption (required for secure token storage)
TOKEN_ENCRYPTION_KEY=abcdefghijklmnopqrstuvwxyz123456
```

---

## Step 6: Deploy and Test

### 6.1 Deploy Changes

```bash
# Rebuild backend with new environment variables
./deploy.sh rebuild-backend
```

### 6.2 Test the Integration

1. **Log in** to Blacklight as a user with email integration permissions
2. Navigate to **Settings** > **Email Integration** (or similar)
3. Click **Connect Outlook**
4. You should be redirected to Microsoft login
5. Sign in with your Microsoft account
6. Grant the requested permissions
7. You should be redirected back to Blacklight with a success message

### 6.3 Verify Connection

Check that the connection is active:

```bash
# Via API
curl -X GET "https://your-domain.com/api/integrations/email/status" \
  -H "Authorization: Bearer <your-jwt-token>"
```

Expected response:
```json
{
  "gmail": {
    "is_connected": false,
    "is_configured": true
  },
  "outlook": {
    "is_connected": true,
    "is_configured": true,
    "email": "user@company.com",
    "last_synced": "2026-01-10T12:00:00Z"
  }
}
```

---

## Troubleshooting

### Error: "AADSTS50011: The redirect URI does not match"

**Cause**: The redirect URI in your environment doesn't match Azure configuration.

**Solution**:
1. Check `MICROSOFT_OAUTH_REDIRECT_URI` in your `.env.production`
2. Ensure it matches **exactly** what's configured in Azure (including http vs https, trailing slashes, etc.)

### Error: "AADSTS7000215: Invalid client secret"

**Cause**: The client secret is incorrect or expired.

**Solution**:
1. Generate a new client secret in Azure
2. Update `MICROSOFT_OAUTH_CLIENT_SECRET` in your environment
3. Redeploy the backend

### Error: "AADSTS65001: User consent required"

**Cause**: The user hasn't consented to the app permissions.

**Solution**:
1. Ensure `prompt=consent` is in the authorization URL (Blacklight does this by default)
2. Have an admin grant consent in Azure portal
3. Or have the user go through the OAuth flow again

### Error: "Token refresh failed"

**Cause**: The refresh token has expired or been revoked.

**Solution**:
1. Have the user disconnect and reconnect their Outlook account
2. Check if the user changed their Microsoft password (invalidates tokens)

### Emails Not Syncing

**Possible causes**:
1. **Circuit breaker open**: Too many API failures triggered protection
2. **Token expired**: Refresh token may have failed
3. **Inngest not running**: Background jobs not executing

**Debug steps**:
```bash
# Check Inngest dashboard
http://your-server:8288/runs

# Check backend logs
./deploy.sh logs backend

# Check circuit breaker status
curl "https://your-domain.com/api/integrations/email/circuit-status" \
  -H "Authorization: Bearer <token>"
```

---

## Security Best Practices

### 1. Use HTTPS in Production

Always use HTTPS for redirect URIs in production to protect OAuth tokens in transit.

### 2. Rotate Client Secrets Regularly

- Set calendar reminders before secret expiration
- Rotate secrets at least annually
- Use Azure Key Vault for secret management in enterprise environments

### 3. Principle of Least Privilege

Only request the permissions you need:
- `Mail.Read` (not `Mail.ReadWrite`)
- `User.Read` (minimal profile access)

### 4. Monitor Token Usage

- Review Azure AD sign-in logs periodically
- Set up alerts for unusual authentication patterns

### 5. Secure Token Storage

Blacklight encrypts OAuth tokens at rest using `TOKEN_ENCRYPTION_KEY`. Ensure this key is:
- Randomly generated (32+ bytes)
- Stored securely (not in version control)
- Backed up securely

### 6. Implement Token Revocation on User Removal

When a user is removed from Blacklight:
1. Revoke their email integration tokens
2. Delete stored tokens from the database

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/integrations/email/status` | GET | Check connection status |
| `/api/integrations/email/connect/outlook` | GET | Initiate OAuth flow |
| `/api/integrations/email/callback/outlook` | GET | OAuth callback handler |
| `/api/integrations/email/disconnect` | POST | Disconnect email integration |
| `/api/integrations/email/sync` | POST | Trigger manual email sync |

---

## Environment Variables Summary

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MICROSOFT_OAUTH_CLIENT_ID` | Yes | - | Azure App Client ID |
| `MICROSOFT_OAUTH_CLIENT_SECRET` | Yes | - | Azure App Client Secret |
| `MICROSOFT_OAUTH_REDIRECT_URI` | Yes | `localhost:5001/...` | OAuth callback URL |
| `MICROSOFT_OAUTH_TENANT` | No | `common` | Azure AD tenant setting |
| `TOKEN_ENCRYPTION_KEY` | Yes | - | Key for encrypting stored tokens |
| `EMAIL_SYNC_ENABLED` | No | `true` | Enable/disable email sync |
| `EMAIL_SYNC_FREQUENCY_MINUTES` | No | `15` | Sync interval in minutes |

---

## Support

For issues with this integration:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review Azure AD sign-in logs for authentication errors
3. Check Blacklight backend logs for API errors
4. Review Inngest dashboard for background job failures

---

*Last updated: January 2026*
