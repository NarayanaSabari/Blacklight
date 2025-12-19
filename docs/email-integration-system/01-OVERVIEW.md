# Email Integration System - Overview

## Introduction

The Email Integration System enables Recruiters and Team Leads to connect their Gmail or Outlook accounts to Blacklight. Once connected, the system automatically scans their inbox for job requirement emails matching their tenant's candidate preferred roles, parses the job details using AI, and creates tenant-specific job postings.

## Business Value

1. **Automated Job Discovery**: Recruiters receive job requirements via email from vendors, clients, and other sources. This system automatically captures those opportunities.
2. **Reduced Manual Entry**: No need to manually copy-paste job details from emails into the system.
3. **Candidate-Role Matching**: Only fetches emails relevant to the tenant's candidate pool (based on preferred roles).
4. **Source Attribution**: Every email-sourced job shows which recruiter/team lead it came from.
5. **Tenant Isolation**: Email-sourced jobs are visible only within the tenant, unlike global scraped jobs.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BLACKLIGHT PORTAL                                   │
│                                                                                  │
│  ┌─────────────┐    ┌─────────────────────┐    ┌─────────────────────────────┐  │
│  │   Settings  │    │   Integration Page   │    │      Email Jobs Page        │  │
│  │    Page     │───▶│  Gmail | Outlook     │    │  View tenant email jobs     │  │
│  └─────────────┘    │  Connect buttons     │    │  with source attribution    │  │
│                     └──────────┬───────────┘    └─────────────────────────────┘  │
│                                │                              ▲                  │
└────────────────────────────────│──────────────────────────────│──────────────────┘
                                 │ OAuth Flow                   │ API
                                 ▼                              │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (Flask)                                     │
│                                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────────┐   │
│  │  OAuth Routes    │    │  Email Jobs API   │    │  Integration Routes      │   │
│  │  /auth/google    │    │  /email-jobs      │    │  /integrations           │   │
│  │  /auth/microsoft │    │                   │    │                          │   │
│  └────────┬─────────┘    └──────────────────┘    └──────────────────────────┘   │
│           │                        ▲                                             │
│           ▼                        │                                             │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        UserEmailIntegration Model                         │   │
│  │  - OAuth tokens (encrypted)                                               │   │
│  │  - Integration type (gmail/outlook)                                       │   │
│  │  - Last sync timestamp                                                    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Triggers
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              INNGEST (Background Jobs)                            │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                     sync-email-jobs (Cron: every 15 min)                     │ │
│  │                                                                              │ │
│  │  Step 1: Get all active email integrations                                   │ │
│  │  Step 2: For each integration:                                               │ │
│  │          - Get tenant's candidate preferred roles                            │ │
│  │          - Normalize roles to keywords                                       │ │
│  │          - Fetch emails with matching subjects (Layer 1)                     │ │
│  │          - Parse email content with AI (Layer 2)                             │ │
│  │          - Create EmailSourcedJob records                                    │ │
│  │  Step 3: Update last_synced_at timestamp                                     │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ API Calls
                                 ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL EMAIL PROVIDERS                                  │
│                                                                                    │
│  ┌────────────────────────────┐    ┌────────────────────────────────────────────┐ │
│  │       Gmail API            │    │         Microsoft Graph API                 │ │
│  │  (messages.list/get)       │    │     (messages endpoint)                     │ │
│  │  Scopes: gmail.readonly    │    │  Scopes: Mail.Read                          │ │
│  └────────────────────────────┘    └────────────────────────────────────────────┘ │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. OAuth Integration
- **Gmail**: OAuth2 with `gmail.readonly` scope
- **Outlook**: OAuth2 with Microsoft Graph `Mail.Read` scope
- Secure token storage with encryption (Fernet)
- Automatic token refresh handling

### 2. Smart Email Filtering (Layer 1 - Subject Line)
- Fetches tenant's candidate preferred roles
- Normalizes roles using existing `AIRoleNormalizationService`
- Searches email subjects for matching keywords
- Example: "Senior Python Developer" → searches for "python developer", "python dev"

### 3. AI-Powered Email Parsing (Layer 2 - Content)
- Uses Google Gemini to parse email body
- Extracts structured job data:
  - Job Title
  - Company Name
  - Location
  - Job Description
  - Required Skills
  - Job Type (Full-time, Contract, etc.)
  - Salary Range (if mentioned)
  - Client/Vendor info

### 4. Tenant-Scoped Jobs
- Email-sourced jobs are tenant-specific (unlike global scraped jobs)
- Each job tracks `sourced_by_user_id` for attribution
- Jobs appear in a dedicated "Email Jobs" section

### 5. Source Attribution
- Every email job shows which recruiter/team lead sourced it
- Tracks original email metadata (sender, date, subject)
- Enables performance tracking by recruiter

## User Roles & Permissions

| Role | Can Connect Email | Can View Email Jobs | Can Sync Manually |
|------|-------------------|---------------------|-------------------|
| TENANT_ADMIN | ✅ | ✅ (all tenant jobs) | ✅ |
| MANAGER | ✅ | ✅ (all tenant jobs) | ✅ |
| TEAM_LEAD | ✅ | ✅ (all tenant jobs) | ✅ |
| RECRUITER | ✅ | ✅ (all tenant jobs) | ✅ |

## Technology Stack

- **OAuth Libraries**: `google-auth`, `google-auth-oauthlib`, `msal` (Microsoft)
- **Email APIs**: Gmail API v1, Microsoft Graph API v1.0
- **AI Parsing**: Google Gemini (gemini-2.5-flash)
- **Background Jobs**: Inngest (cron-based sync)
- **Token Encryption**: cryptography (Fernet)
- **Database**: PostgreSQL with encrypted columns

## Document Index

1. [01-OVERVIEW.md](01-OVERVIEW.md) - This document
2. [02-DATA-MODELS.md](02-DATA-MODELS.md) - Database models and schemas
3. [03-OAUTH-FLOW.md](03-OAUTH-FLOW.md) - OAuth implementation details
4. [04-EMAIL-SYNC-SERVICE.md](04-EMAIL-SYNC-SERVICE.md) - Email fetching and filtering
5. [05-AI-EMAIL-PARSER.md](05-AI-EMAIL-PARSER.md) - AI-powered email parsing
6. [06-INNGEST-WORKFLOWS.md](06-INNGEST-WORKFLOWS.md) - Background job implementation
7. [07-API-ENDPOINTS.md](07-API-ENDPOINTS.md) - REST API documentation
8. [08-FRONTEND-INTEGRATION.md](08-FRONTEND-INTEGRATION.md) - UI implementation
9. [09-CONFIGURATION.md](09-CONFIGURATION.md) - Environment variables and setup
10. [10-SECURITY.md](10-SECURITY.md) - Security considerations
