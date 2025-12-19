# OAuth Setup Guide - Gmail & Outlook Integration

This guide provides step-by-step instructions for obtaining OAuth credentials for Gmail and Outlook email integrations.

---

## Table of Contents

1. [Gmail OAuth Setup (Google Cloud Console)](#gmail-oauth-setup)
2. [Outlook OAuth Setup (Microsoft Azure Portal)](#outlook-oauth-setup)
3. [Token Encryption Key](#token-encryption-key)
4. [Environment Variables Summary](#environment-variables-summary)
5. [Testing the Integration](#testing-the-integration)
6. [Troubleshooting](#troubleshooting)

---

## Gmail OAuth Setup

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click **"New Project"**
4. Enter a project name (e.g., "Blacklight Email Integration")
5. Click **"Create"**
6. Wait for the project to be created, then select it

### Step 2: Enable Gmail API

1. In the Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for **"Gmail API"**
3. Click on **Gmail API**
4. Click **"Enable"**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **"External"** user type (or "Internal" if using Google Workspace)
3. Click **"Create"**
4. Fill in the required fields:
   - **App name**: Blacklight HR Platform
   - **User support email**: Your email address
   - **Developer contact email**: Your email address
5. Click **"Save and Continue"**

#### Add Scopes

1. Click **"Add or Remove Scopes"**
2. Add the following scopes:
   - `https://www.googleapis.com/auth/gmail.readonly` - Read emails
   - `https://www.googleapis.com/auth/userinfo.email` - Get user email
   - `openid` - OpenID Connect
3. Click **"Update"**
4. Click **"Save and Continue"**

#### Add Test Users (For Development)

1. Click **"Add Users"**
2. Add email addresses that will test the integration
3. Click **"Save and Continue"**
4. Click **"Back to Dashboard"**

### Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"+ Create Credentials"** → **"OAuth client ID"**
3. Select **"Web application"** as Application type
4. Enter a name (e.g., "Blacklight Web Client")
5. Add **Authorized JavaScript origins**:
   ```
   http://localhost:5173          (Development frontend)
   http://localhost:5000          (Development backend)
   https://your-domain.com        (Production)
   ```
6. Add **Authorized redirect URIs**:
   ```
   http://localhost:5000/api/email-integrations/callback/gmail    (Development)
   https://your-domain.com/api/email-integrations/callback/gmail  (Production)
   ```
7. Click **"Create"**

### Step 5: Copy Your Credentials

After creation, you'll see a dialog with:
- **Client ID**: `xxxxxxxxxx.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xxxxxxxxxx`

Copy these values to your `.env` file:

```env
GOOGLE_CLIENT_ID=xxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxx
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5000/api/email-integrations/callback/gmail
```

### Step 6: Publish the App (For Production)

For development, your app is in "Testing" mode and only test users can use it.

For production:
1. Go to **OAuth consent screen**
2. Click **"Publish App"**
3. You may need to go through Google's verification process if using sensitive scopes

---

## Outlook OAuth Setup

### Step 1: Create an Azure Account

1. Go to [Azure Portal](https://portal.azure.com/)
2. Sign in with your Microsoft account (or create one)
3. If you don't have an Azure subscription, you can use the free tier

### Step 2: Register an Application

1. In Azure Portal, search for **"App registrations"** in the top search bar
2. Click **"App registrations"**
3. Click **"+ New registration"**
4. Fill in the registration form:
   - **Name**: Blacklight HR Platform
   - **Supported account types**: Select one:
     - **"Accounts in any organizational directory and personal Microsoft accounts"** (Recommended for multi-tenant)
     - **"Accounts in this organizational directory only"** (Single tenant)
   - **Redirect URI**: 
     - Platform: **Web**
     - URI: `http://localhost:5000/api/email-integrations/callback/outlook`
5. Click **"Register"**

### Step 3: Note Your Application Details

After registration, you'll be on the app's Overview page. Copy these values:

- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
  - Use `common` for multi-tenant apps (recommended)
  - Use the specific tenant ID for single-tenant apps

### Step 4: Create a Client Secret

1. In the left sidebar, click **"Certificates & secrets"**
2. Click **"+ New client secret"**
3. Enter a description (e.g., "Blacklight Production")
4. Select expiration:
   - 6 months (recommended for development)
   - 12 months
   - 24 months
   - Custom
5. Click **"Add"**
6. **IMPORTANT**: Copy the **Value** immediately (it won't be shown again!)
   - The **Value** is your client secret (not the Secret ID)

### Step 5: Configure API Permissions

1. In the left sidebar, click **"API permissions"**
2. Click **"+ Add a permission"**
3. Select **"Microsoft Graph"**
4. Select **"Delegated permissions"**
5. Search and add these permissions:
   - `Mail.Read` - Read user mail
   - `User.Read` - Sign in and read user profile
   - `offline_access` - Maintain access to data (for refresh tokens)
6. Click **"Add permissions"**

Your permissions should look like:

| API / Permission | Type | Status |
|-----------------|------|--------|
| Microsoft Graph - Mail.Read | Delegated | ✓ Granted |
| Microsoft Graph - User.Read | Delegated | ✓ Granted |
| Microsoft Graph - offline_access | Delegated | ✓ Granted |

### Step 6: Grant Admin Consent (Optional)

If you're an admin and want to pre-approve for all users:
1. Click **"Grant admin consent for [Your Organization]"**
2. Click **"Yes"**

This is optional - users can consent individually when they connect.

### Step 7: Add Redirect URIs for Production

1. In the left sidebar, click **"Authentication"**
2. Under **"Web"** → **"Redirect URIs"**, add:
   ```
   http://localhost:5000/api/email-integrations/callback/outlook    (Development)
   https://your-domain.com/api/email-integrations/callback/outlook  (Production)
   ```
3. Click **"Save"**

### Step 8: Copy Your Credentials

Add these to your `.env` file:

```env
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=your-secret-value-here
MICROSOFT_OAUTH_REDIRECT_URI=http://localhost:5000/api/email-integrations/callback/outlook
MICROSOFT_TENANT_ID=common
```

---

## Token Encryption Key

OAuth tokens are encrypted before storing in the database using Fernet symmetric encryption.

### Generate an Encryption Key

Run this Python command to generate a secure key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Output example:
```
Zq3t8K_example_key_here_xyz123456789=
```

Add to your `.env` file:

```env
TOKEN_ENCRYPTION_KEY=Zq3t8K_example_key_here_xyz123456789=
```

> ⚠️ **IMPORTANT**: 
> - Never share or commit this key
> - If you lose this key, all stored OAuth tokens become unreadable
> - Use different keys for development and production

---

## Environment Variables Summary

Here's a complete summary of all required environment variables:

```env
# ============================================
# EMAIL INTEGRATION - OAUTH CONFIGURATION
# ============================================

# ----- Gmail OAuth (Google Cloud Console) -----
# Get these from: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5000/api/email-integrations/callback/gmail

# ----- Outlook OAuth (Azure Portal) -----
# Get these from: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=your-client-secret-value
MICROSOFT_OAUTH_REDIRECT_URI=http://localhost:5000/api/email-integrations/callback/outlook
MICROSOFT_TENANT_ID=common

# ----- Token Encryption -----
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=your-generated-fernet-key

# ----- Email Sync Settings -----
EMAIL_SYNC_ENABLED=true
EMAIL_SYNC_FREQUENCY_MINUTES=15
EMAIL_SYNC_LOOKBACK_DAYS=7
EMAIL_SYNC_MAX_EMAILS_PER_SYNC=50

# ----- AI Parsing (Google Gemini) -----
# Get from: https://aistudio.google.com/app/apikey
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
```

---

## Testing the Integration

### 1. Verify Environment Variables

```bash
cd server
python -c "from config.settings import settings; print('Gmail:', settings.GOOGLE_CLIENT_ID[:20] if settings.GOOGLE_CLIENT_ID else 'NOT SET')"
```

### 2. Test Gmail Connection

1. Start the backend server
2. Log in as a recruiter/team lead
3. Go to **Settings** → **Integrations**
4. Click **"Connect Gmail"**
5. You should be redirected to Google's OAuth consent screen
6. Select your account and grant permissions
7. You should be redirected back and see "Connected" status

### 3. Test Outlook Connection

1. Click **"Connect Outlook"**
2. You should be redirected to Microsoft's login page
3. Sign in and grant permissions
4. You should be redirected back and see "Connected" status

### 4. Verify Email Sync

1. After connecting, click the **sync icon** to trigger a manual sync
2. Check the server logs for sync activity
3. Go to **Email Jobs** page to see any discovered jobs

---

## Troubleshooting

### Gmail Issues

#### "Access blocked: This app's request is invalid"
- **Cause**: Redirect URI mismatch
- **Fix**: Ensure `GOOGLE_OAUTH_REDIRECT_URI` exactly matches the one in Google Cloud Console

#### "This app isn't verified"
- **Cause**: App is in testing mode
- **Fix**: Add your email to test users in OAuth consent screen, or publish the app

#### "Error 403: access_denied"
- **Cause**: User denied permission or app not published
- **Fix**: Add user to test users or publish the app

### Outlook Issues

#### "AADSTS50011: The reply URL specified in the request does not match"
- **Cause**: Redirect URI mismatch
- **Fix**: Ensure `MICROSOFT_OAUTH_REDIRECT_URI` exactly matches the one in Azure Portal

#### "AADSTS7000218: The request body must contain: client_secret"
- **Cause**: Client secret not set or expired
- **Fix**: Create a new client secret in Azure Portal

#### "AADSTS650053: Application needs to be consented"
- **Cause**: Required permissions not granted
- **Fix**: Grant admin consent or let users consent individually

### General Issues

#### "Invalid encryption key"
- **Cause**: `TOKEN_ENCRYPTION_KEY` is invalid or missing
- **Fix**: Generate a new key using the Fernet command

#### "Callback URL not found"
- **Cause**: Routes not registered
- **Fix**: Ensure the email integration blueprint is registered in `app/__init__.py`

---

## Quick Reference Links

| Service | Console Link |
|---------|-------------|
| Google Cloud Console | https://console.cloud.google.com/apis/credentials |
| Google OAuth Consent | https://console.cloud.google.com/apis/credentials/consent |
| Azure App Registrations | https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade |
| Google Gemini API Keys | https://aistudio.google.com/app/apikey |

---

## Security Best Practices

1. **Never commit credentials** - Use environment variables or secrets manager
2. **Rotate secrets regularly** - Set calendar reminders for secret expiration
3. **Use separate credentials** - Different keys for dev/staging/production
4. **Monitor OAuth usage** - Check Google/Azure dashboards for unusual activity
5. **Limit scopes** - Only request permissions you actually need
6. **Encrypt tokens at rest** - Always use `TOKEN_ENCRYPTION_KEY`
