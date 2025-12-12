# CentralD Dashboard Guide

## Overview

The CentralD Dashboard (`http://localhost/central/dashboard`) is the PM_ADMIN (Platform Manager Administrator) interface for monitoring and managing the job matching system. This dashboard provides visibility into:

- **Role Queue Management**: Review, approve, reject, and merge normalized roles
- **Scraper Monitoring**: Track active scrapers and scrape sessions
- **API Key Management**: Create and manage scraper API keys
- **Job Import Statistics**: Monitor job import activity

## Authentication

Access requires **PM_ADMIN** authentication:
- Login at `http://localhost/central/login`
- Only users with `PM_ADMIN` role can access this dashboard

## Dashboard Components

### 1. Stats Cards

Located at the top, showing real-time statistics:

| Stat | Description |
|------|-------------|
| **Pending Queue** | Roles waiting in the scrape queue |
| **Active Scrapers** | Scrapers currently running (sessions updated in last 10 min) |
| **New Roles** | Roles added (pending review/scraping) |
| **Jobs Imported** | Jobs imported in the last 24 hours |
| **Active API Keys** | Number of active scraper API keys |

### 2. Role Queue Table

**Purpose**: Manage normalized roles from candidate approvals.

When a candidate is approved:
1. Their preferred roles are normalized using AI/embedding similarity
2. Normalized roles appear in the `global_roles` table with `queue_status='pending'`
3. PM_ADMIN reviews and manages these roles

#### Role Queue Columns

| Column | Description |
|--------|-------------|
| **Role Name** | Normalized canonical role name |
| **Category** | Role category (Engineering, Data Science, etc.) |
| **Priority** | Queue priority: urgent, high, normal, low |
| **Candidates** | Number of candidates wanting this role |
| **Similar Roles** | Similar existing roles found via embedding |

#### Action Buttons

| Button | Icon | Action | Backend Endpoint |
|--------|------|--------|------------------|
| **Approve** | ✓ (green) | Keeps role in scrape queue with `pending` status | `POST /api/roles/{id}/approve` |
| **Merge** | ⑂ (blue) | Merge this role into an existing approved role | `POST /api/roles/{id}/merge` |
| **Reject** | ✕ (red) | Remove role from queue, sets status to `rejected` | `POST /api/roles/{id}/reject` |

### 3. Scraper Monitoring Panel

Shows active and recent scrape sessions:

| Field | Description |
|-------|-------------|
| **Scraper Key** | Name of the API key used |
| **Role** | Role being scraped |
| **Status** | `in_progress`, `completed`, `failed` |
| **Jobs Found** | Number of jobs found |
| **Jobs Imported** | Number of jobs successfully imported |
| **Duration** | Time taken for the session |

### 4. API Keys Manager

Manage scraper API keys for external scrapers:

| Action | Description |
|--------|-------------|
| **Create Key** | Generate new API key (shown once, save it!) |
| **Pause** | Temporarily disable key |
| **Revoke** | Permanently revoke key |
| **Resume** | Re-enable paused key |

### 5. Jobs Preview

Preview of recently imported jobs across all platforms.

## Role Status Workflow

```
Candidate Approved
       ↓
Role Normalized (AI/Embedding)
       ↓
Role added to global_roles
with queue_status='pending'
       ↓
  ┌────┴────┐
  ↓         ↓         ↓
APPROVE   MERGE    REJECT
  ↓         ↓         ↓
Status    Merged   Status
'approved' into    'rejected'
  ↓       target
Scraper picks up role
(status → 'processing')
  ↓
Jobs imported
(status → 'completed')
  ↓
After 24h, status → 'pending' (refresh)
```

## Queue Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Role is newly created, awaiting PM_ADMIN review |
| `approved` | Role has been approved by PM_ADMIN, in the scrape queue |
| `processing` | A scraper is currently fetching jobs for this role |
| `completed` | Role was recently scraped (within 24h) |
| `rejected` | Role was rejected by PM_ADMIN |

## Priority Levels

| Priority | Use Case |
|----------|----------|
| `urgent` | High-value roles, manual escalation needed |
| `high` | Roles with many candidates waiting |
| `normal` | Regular queue processing (default) |
| `low` | Background refresh for stale roles |

## API Endpoints Reference

### Global Roles (PM_ADMIN only)

```
GET    /api/roles                    - List all roles
GET    /api/roles/{id}               - Get role details
POST   /api/roles/{id}/approve       - Approve role (keep in queue)
POST   /api/roles/{id}/reject        - Reject role (remove from queue)
POST   /api/roles/{id}/merge         - Merge into target role
PUT    /api/roles/{id}/priority      - Update role priority
```

### Scraper Monitoring (PM_ADMIN only)

```
GET    /api/scraper-monitoring/stats          - Dashboard statistics
GET    /api/scraper-monitoring/sessions       - List scrape sessions
GET    /api/scraper-monitoring/api-keys       - List API keys
POST   /api/scraper-monitoring/api-keys       - Create new API key
PATCH  /api/scraper-monitoring/api-keys/{id}  - Update key status
DELETE /api/scraper-monitoring/api-keys/{id}  - Revoke key
```

## Troubleshooting

### Actions Not Working

1. **Check Network Tab**: Open browser DevTools (F12) → Network tab
2. **Look for API errors**: Check if requests are returning 4xx or 5xx errors
3. **Verify Authentication**: Ensure PM_ADMIN token is valid (try re-logging)
4. **Check Backend Logs**: `docker logs blacklight-backend -f`

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Buttons not responding | API returning error | Check DevTools Network tab |
| 401 Unauthorized | Token expired | Re-login to CentralD |
| 403 Forbidden | Not PM_ADMIN role | Verify user has PM_ADMIN role |
| No roles appearing | No candidates approved | Approve candidates to trigger normalization |
| Toast not showing | UI component issue | Check browser console for errors |

### Verifying Role Normalization is Working

1. Approve a candidate with preferred roles
2. Check backend logs for:
   ```
   [INNGEST] ✅ Role normalization event sent for candidate X
   [ROLE-NORM] Starting normalization for candidate X
   [ROLE-NORM] ✅ 'Role Name' -> 'Normalized Name'
   ```
3. Role should appear in CentralD Dashboard → Role Queue

## Database Tables

| Table | Purpose |
|-------|---------|
| `global_roles` | Normalized roles with embeddings and queue status |
| `candidate_global_roles` | Links candidates to their global roles |
| `scrape_sessions` | Records of scraper activity |
| `scraper_api_keys` | API keys for external scrapers |
| `job_postings` | Imported job listings |
| `role_job_mappings` | Links roles to their matching jobs |
