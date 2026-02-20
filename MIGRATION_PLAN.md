# Blacklight GCP Migration Plan

**Created:** 2026-02-20
**Source Project:** `mvp-blacklight` (account: `srimswathi8@gmail.com`)
**Target Project:** TBD (new GCP account)
**Region:** `asia-south1`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Assessment](#2-current-state-assessment)
3. [What Has Been Backed Up](#3-what-has-been-backed-up)
4. [What Could NOT Be Backed Up](#4-what-could-not-be-backed-up)
5. [Source Infrastructure Inventory](#5-source-infrastructure-inventory)
6. [Database Details](#6-database-details)
7. [Production Environment Variables](#7-production-environment-variables)
8. [GitHub Actions Workflow Analysis](#8-github-actions-workflow-analysis)
9. [Migration Phases](#9-migration-phases)
10. [Migration Scripts Reference](#10-migration-scripts-reference)
11. [Critical Warnings](#11-critical-warnings)
12. [Action Items for You](#12-action-items-for-you)
13. [Post-Migration Validation](#13-post-migration-validation)
14. [Estimated Timeline](#14-estimated-timeline)

---

## 1. Executive Summary

We are migrating the entire Blacklight platform from the old GCP project (`mvp-blacklight`) to a new GCP account. The old project's billing is disabled/delinquent, which blocks access to some resources (GCS, Redis, Artifact Registry, Secret Manager) but Cloud SQL and Cloud Run are still accessible.

### What's done

- Database has been dumped locally (3.1 MB, 37 tables, 41,886 rows) -- ready to restore
- 6 migration scripts created in `scripts/migration/`
- All production environment variables captured from the live Cloud Run service
- All 4 GitHub Actions workflows analyzed for hardcoded values that need updating

### What's blocked

- GCS files (16 files, 2.63 MiB -- mostly candidate resumes) cannot be downloaded until billing is re-enabled on the source project, OR they can be re-uploaded after migration

### Downtime

- Acceptable per your instructions. No blue-green or zero-downtime strategy needed.

---

## 2. Current State Assessment

### Source Project Health

| Resource | Status | Accessible? |
|----------|--------|-------------|
| Cloud SQL (`bl-db`) | RUNNABLE | YES |
| Cloud Run (3 services) | Running | YES |
| GCS Bucket | Exists | NO (billing blocked) |
| Redis (Memorystore) | Exists | NO (billing blocked) |
| Artifact Registry | Exists | NO (billing blocked) |
| Secret Manager | Exists | NO (billing blocked) |
| Compute VMs (2) | TERMINATED | N/A |

### Key Insight

Cloud SQL and Cloud Run are still running despite billing being disabled. This is likely temporary -- Google will eventually shut them down. The database dump was captured while access was still available.

---

## 3. What Has Been Backed Up

### Database Dump (COMPLETED)

| Item | Details |
|------|---------|
| **File** | `scripts/migration/dumps/blacklight_dump_20260220_115831.dump` |
| **Format** | PostgreSQL custom format (supports `pg_restore`) |
| **Size** | 3.1 MB |
| **Tables** | 37 |
| **Total Rows** | 41,886 |
| **Alembic Version** | `e9b4594d7067` |
| **Method** | `pg_dump` via Cloud SQL Auth Proxy (local laptop) |
| **Verified** | `pg_restore --list` shows 528 TOC entries, all data/indexes intact |

**Largest tables:**
| Table | Rows | Size |
|-------|------|------|
| `processed_emails` | 40,711 | ~19 MB |
| `job_postings` | 465 | - |
| `candidates` | 15 | - |
| `global_roles` | 66 | - |

**pgvector embeddings preserved:**
- `candidates`: 15/15 have embeddings
- `global_roles`: 66/66 have embeddings
- `job_postings`: 0/465 (never generated -- not a migration issue)

**Tenants in database:**
1. Acme Corporation
2. TechStart Inc
3. Global Recruiters LLC
4. Quantipeak

### Production Environment Variables (CAPTURED)

All env vars and secrets from the live Cloud Run `blacklight-backend` service have been captured (see Section 7 below). These include database URLs, API keys, OAuth credentials, encryption keys, etc.

---

## 4. What Could NOT Be Backed Up

### GCS Files (BLOCKED)

| Item | Details |
|------|---------|
| **Bucket** | `gs://mvp-blacklight-files` |
| **Files** | 16 files, 2.63 MiB total |
| **Contents** | 15 candidate resume PDFs + 1 old DB backup |
| **Why blocked** | Billing disabled on source project |

**Options to recover:**
1. **Re-enable billing** on `mvp-blacklight` temporarily, download files, then disable again
2. **Re-upload resumes** manually after migration (if you have local copies)
3. **Accept the loss** -- these are just 15 test resumes, not critical production data

---

## 5. Source Infrastructure Inventory

### Cloud Run Services (3)

| Service | Image | Memory | CPU | Min/Max Instances |
|---------|-------|--------|-----|-------------------|
| `blacklight-backend` | `backend:latest` | 1 GiB | 1 | 0/5 |
| `blacklight-portal` | `portal:latest` | 512 MiB | 1 | 0/5 |
| `blacklight-central` | `central:latest` | 512 MiB | 1 | 0/3 |

### Cloud SQL

| Setting | Value |
|---------|-------|
| Instance | `bl-db` |
| Version | PostgreSQL 15 |
| Tier | `db-custom-2-4096` (2 vCPU, 4 GB RAM) |
| Storage | 10 GB (auto-increase) |
| IP | Private only (`10.84.0.3`) |
| Extensions | pgvector 0.8.1 |
| Database | `postgres` |
| User | `postgres` |
| Connection | `mvp-blacklight:asia-south1:bl-db` |

### Redis (Memorystore)

| Setting | Value |
|---------|-------|
| Instance | `blacklight-redis` |
| Version | Redis 7.0 |
| Size | 1 GB |
| Tier | Basic |
| IP | `10.101.79.27` |

### GCS Bucket

| Setting | Value |
|---------|-------|
| Name | `mvp-blacklight-files` |
| Location | `asia-south1` |
| Files | 16 (2.63 MiB) |
| Access | Uniform bucket-level |

### Networking

| Resource | Details |
|----------|---------|
| VPC | `blacklight-vpc` (auto subnet mode) |
| VPC Connector | `blacklight-connector` (`10.8.0.0/28`) |
| Private Services | VPC peering for Cloud SQL |

### Artifact Registry

| Setting | Value |
|---------|-------|
| Repository | `blacklight` |
| Format | Docker |
| Location | `asia-south1` |

### Service Accounts

| Account | Purpose |
|---------|---------|
| `blacklight-backend@mvp-blacklight.iam` | Cloud Run backend service identity |
| `github-deployer@mvp-blacklight.iam` | GitHub Actions CI/CD |
| Default compute SA | Compute Engine |

### Workload Identity Federation

| Setting | Value |
|---------|-------|
| Pool | `github-pool` |
| Provider | `github-provider` |
| Project Number | `642824921295` |
| Full Provider Path | `projects/642824921295/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |

### Compute Engine VMs (both TERMINATED)

| VM | Type | Purpose | Status |
|----|------|---------|--------|
| `inngest-server` | e2-small | Self-hosted Inngest | TERMINATED |
| `email-scraper` | c4-standard-4 | Email scraping | TERMINATED |

### External Services

| Service | Details |
|---------|---------|
| Google OAuth | Client ID: `259077698611-...` (for Gmail email sync) |
| Microsoft OAuth | Client ID: `62b62b68-...` (for Outlook email sync) |
| Gmail SMTP | `sabariokg@gmail.com` via `smtp.gmail.com:587` |
| Gemini AI | Model: `gemini-2.5-flash`, Embeddings: `gemini-embedding-001` |
| Inngest | Self-hosted on GCE VM (now terminated) at `http://35.200.184.121:8288/` |

---

## 6. Database Details

### Connection Info (Source)

```
Host: 10.84.0.3 (private IP, via VPC)
Port: 5432
Database: postgres
User: postgres
Password: 3FXymdgrCsyb5vImv8lBtc7W
Connection Name: mvp-blacklight:asia-south1:bl-db
```

### Schema Overview

37 tables managed by Alembic (current head: `e9b4594d7067`). Key tables:

| Category | Tables |
|----------|--------|
| Core | `tenants`, `users`, `roles`, `permissions` |
| Recruiting | `candidates`, `job_postings`, `job_applications`, `global_roles` |
| Email | `email_integrations`, `processed_emails`, `email_sync_states` |
| AI/Matching | `candidate_job_matches` (pgvector embeddings on candidates + global_roles) |
| System | `alembic_version` |

### pgvector Configuration

- Extension version: 0.8.1
- Embedding dimension: 768 (Gemini `gemini-embedding-001`)
- Vector columns on `candidates` table and `global_roles` table

---

## 7. Production Environment Variables

These are the exact values currently set on the `blacklight-backend` Cloud Run service. You need these when setting up the new project.

### Variables That MUST Stay The Same

| Variable | Value | Why |
|----------|-------|-----|
| `TOKEN_ENCRYPTION_KEY` | (captured -- Fernet key) | Encrypts OAuth tokens in DB. Changing it breaks all email integrations. |
| `SECRET_KEY` | (captured) | Flask session signing. Changing invalidates sessions but won't break data. |
| `GOOGLE_OAUTH_CLIENT_ID` | `259077698611-...` | Unless you create a new OAuth app |
| `GOOGLE_OAUTH_CLIENT_SECRET` | (captured) | Unless you create a new OAuth app |
| `MICROSOFT_OAUTH_CLIENT_ID` | `62b62b68-...` | Unless you create a new Azure app |
| `MICROSOFT_OAUTH_CLIENT_SECRET` | (captured) | Unless you create a new Azure app |
| `GOOGLE_API_KEY` | (captured) | Gemini AI API key |
| `SMTP_PASSWORD` | (captured) | Gmail app password |

### Variables That WILL Change (new project)

| Variable | Old Value | New Value |
|----------|-----------|-----------|
| `DATABASE_URL` | `postgresql://postgres:3FXy...@/postgres?host=/cloudsql/mvp-blacklight:asia-south1:bl-db` | `postgresql://postgres:NEW_PASS@/postgres?host=/cloudsql/NEW_PROJECT:asia-south1:bl-db` |
| `REDIS_URL` | `redis://10.101.79.27:6379/0` | `redis://NEW_REDIS_IP:6379/0` |
| `REDIS_CACHE_URL` | `redis://10.101.79.27:6379/1` | `redis://NEW_REDIS_IP:6379/1` |
| `GCS_BUCKET_NAME` | `mvp-blacklight-files` | `NEW_PROJECT-files` |
| `GCS_PROJECT_ID` | `mvp-blacklight` | `NEW_PROJECT_ID` |
| `FRONTEND_BASE_URL` | `https://blacklight-portal-bi6eujysoa-el.a.run.app/portal` | New Cloud Run portal URL |
| `CORS_ORIGINS` | `*` | New portal + central URLs |
| `INNGEST_SERVE_HOST` | `https://blacklight-backend-bi6eujysoa-el.a.run.app` | New backend URL |
| `INNGEST_BASE_URL` | `http://35.200.184.121:8288/` | New Inngest server URL |
| `GOOGLE_OAUTH_REDIRECT_URI` | `https://blacklight-backend-bi6eujysoa-el.a.run.app/api/integrations/email/callback/gmail` | New backend URL + same path |
| `MICROSOFT_OAUTH_REDIRECT_URI` | `https://blacklight-backend-bi6eujysoa-el.a.run.app/api/integrations/email/callback/outlook` | New backend URL + same path |
| `GCS_CREDENTIALS_JSON` | Secret Manager ref `gcs-credentials:latest` | New service account key JSON |

### Variables That Stay The Same (static config)

```
ENVIRONMENT=production
STORAGE_BACKEND=gcs
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=sabariokg@gmail.com
SMTP_FROM_EMAIL=sabariokg@gmail.com
SMTP_FROM_NAME=BlackLight Company HR
AI_PARSING_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSION=768
LOG_LEVEL=info
INNGEST_DEV=false
INNGEST_SERVE_PATH=/api/inngest
EMAIL_SYNC_ENABLED=true
EMAIL_SYNC_FREQUENCY_MINUTES=15
EMAIL_SYNC_INITIAL_LOOKBACK_DAYS=10
EMAIL_SYNC_MAX_EMAILS_PER_PAGE=100
MICROSOFT_OAUTH_TENANT=common
```

---

## 8. GitHub Actions Workflow Analysis

### Files That Need Updating

All 4 workflow files contain hardcoded references to the old project:

#### 1. `.github/workflows/deploy-backend.yml` (Most Complex)

| Line | Current Value | What to Change |
|------|---------------|----------------|
| 60 | `projects/642824921295/locations/global/...` | New project number in WIF provider path |
| 61 | `github-deployer@mvp-blacklight.iam.gserviceaccount.com` | New project ID in service account |
| 98 | `blacklight-backend@mvp-blacklight.iam.gserviceaccount.com` | New project ID in `--service-account` |
| 99 | `projects/mvp-blacklight/locations/asia-south1/connectors/blacklight-connector` | New project ID in `--vpc-connector` |
| 104 | `https://blacklight-portal-bi6eujysoa-el.a.run.app/portal` | New portal Cloud Run URL |
| 106 | `mvp-blacklight-files` | New GCS bucket name |
| 107 | `mvp-blacklight` | New project ID for GCS |
| 111 | `sabariokg@gmail.com` | Update if changing SMTP sender |
| 114 | `sabariokg@gmail.com` | Update if changing SMTP sender |
| 123 | `redis://10.101.79.27:6379/0` | New Redis IP |
| 124 | `redis://10.101.79.27:6379/1` | New Redis IP |
| 126 | `http://35.200.184.121:8288/` | New Inngest URL |
| 129 | `https://blacklight-backend-bi6eujysoa-el.a.run.app` | New backend URL |
| 134 | `https://blacklight-backend-bi6eujysoa-el.a.run.app/api/integrations/email/callback/gmail` | New backend URL |
| 141 | `https://blacklight-backend-bi6eujysoa-el.a.run.app/api/integrations/email/callback/outlook` | New backend URL |
| 143 | `gcs-credentials:latest` | Update secret name if different |

#### 2. `.github/workflows/deploy-portal.yml`

| Line | Current Value | What to Change |
|------|---------------|----------------|
| 48 | `projects/642824921295/locations/global/...` | New WIF provider path |
| 49 | `github-deployer@mvp-blacklight.iam.gserviceaccount.com` | New service account |

#### 3. `.github/workflows/deploy-central.yml`

| Line | Current Value | What to Change |
|------|---------------|----------------|
| 48 | `projects/642824921295/locations/global/...` | New WIF provider path |
| 49 | `github-deployer@mvp-blacklight.iam.gserviceaccount.com` | New service account |

#### 4. `.github/workflows/deploy-all.yml`

This workflow uses `credentials_json` (service account key) instead of WIF. No hardcoded project-specific values in the file -- everything comes from secrets. However, the `GCP_SA_KEY` secret needs to be a key from the new project's service account.

### GitHub Secrets to Update (14 total)

| Secret | Change Required | Notes |
|--------|----------------|-------|
| `GCP_PROJECT_ID` | YES | New project ID |
| `GCP_SA_KEY` | YES | New service account JSON key |
| `DATABASE_URL` | YES | New Cloud SQL connection string |
| `BACKEND_URL` | YES | New backend Cloud Run URL |
| `GCS_CREDENTIALS_JSON` | YES | New GCS service account key JSON |
| `SECRET_KEY` | KEEP SAME | Flask secret key |
| `GOOGLE_API_KEY` | KEEP SAME | Gemini API key (unless you want a new one) |
| `TOKEN_ENCRYPTION_KEY` | **MUST KEEP SAME** | Fernet key for OAuth token encryption |
| `SMTP_PASSWORD` | KEEP SAME | Gmail app password |
| `GOOGLE_OAUTH_CLIENT_ID` | KEEP SAME | Unless creating new OAuth app |
| `GOOGLE_OAUTH_CLIENT_SECRET` | KEEP SAME | Unless creating new OAuth app |
| `MICROSOFT_OAUTH_CLIENT_ID` | KEEP SAME | Unless creating new Azure app |
| `MICROSOFT_OAUTH_CLIENT_SECRET` | KEEP SAME | Unless creating new Azure app |
| `INNGEST_EVENT_KEY` | KEEP/NEW | Depends on Inngest setup |
| `INNGEST_SIGNING_KEY` | KEEP/NEW | Depends on Inngest setup |

---

## 9. Migration Phases

### Phase 1: Database Dump -- DONE

The database has already been dumped to `scripts/migration/dumps/blacklight_dump_20260220_115831.dump`.

### Phase 2: Create Target GCP Infrastructure

Run `scripts/migration/02-setup-target-project.sh <NEW_PROJECT_ID>`

This script creates:
- GCP project (if needed) + enables APIs
- VPC network + private IP range + VPC peering
- Serverless VPC Access connector
- Cloud SQL instance (PostgreSQL 15, pgvector enabled)
- Redis (Memorystore, 1 GB Basic)
- GCS bucket
- Artifact Registry repository
- Service accounts (`blacklight-backend`, `github-deployer`)
- Workload Identity Federation pool + provider
- Secret Manager secrets (empty, need to populate)
- GCS service account key

**Estimated time:** 15-20 minutes (Cloud SQL and Redis take 5-10 min each)

### Phase 3: Restore Database

Run `scripts/migration/03-restore-target-db.sh <NEW_PROJECT_ID> <DUMP_FILE>`

This script:
1. Starts Cloud SQL Auth Proxy to new instance (port 5433)
2. Enables pgvector extension
3. Restores the dump using `pg_restore`
4. Verifies table counts, extensions, and vector columns

**Estimated time:** 2-5 minutes

### Phase 4: Migrate GCS Files

Run `scripts/migration/04-migrate-gcs-files.sh <NEW_PROJECT_ID>`

**BLOCKED** -- Requires billing on source project. Options:
1. Re-enable billing temporarily
2. Re-upload files manually
3. Skip (only 15 test resumes)

### Phase 5: Deploy Services

Run `scripts/migration/05-deploy-services.sh <NEW_PROJECT_ID>`

This script:
1. Configures Docker for new Artifact Registry
2. Builds and pushes backend, portal, and central images
3. Deploys all three Cloud Run services
4. Prompts for DATABASE_URL and other secrets

**Estimated time:** 10-15 minutes

### Phase 6: Post-Migration Configuration

Run `scripts/migration/06-post-migration.sh <NEW_PROJECT_ID>`

This script outputs all the manual steps needed:
1. Update Google OAuth redirect URI
2. Update Microsoft OAuth redirect URI
3. Update GitHub Actions secrets (14 secrets)
4. Update GitHub Actions workflow files (hardcoded values)
5. Update backend environment variables (CORS, frontend URL, etc.)
6. Validation checklist

---

## 10. Migration Scripts Reference

All scripts are in `scripts/migration/`:

| Script | Purpose | Status |
|--------|---------|--------|
| `01-dump-source-db.sh` | Dump source DB via Cloud SQL Auth Proxy | DONE (dump exists) |
| `02-setup-target-project.sh` | Create all target GCP infrastructure | Ready to run |
| `03-restore-target-db.sh` | Restore dump to target Cloud SQL | Ready to run |
| `04-migrate-gcs-files.sh` | Copy GCS files between buckets | BLOCKED (billing) |
| `05-deploy-services.sh` | Build, push, and deploy Cloud Run services | Ready to run |
| `06-post-migration.sh` | Post-migration checklist and commands | Ready to run |

### Prerequisites for Running Scripts

- `gcloud` CLI installed and authenticated
- `cloud-sql-proxy` installed (`brew install cloud-sql-proxy`)
- PostgreSQL 17 client tools installed (`brew install postgresql@17`)
  - `pg_dump` at `/opt/homebrew/opt/postgresql@17/bin/pg_dump`
  - `pg_restore` at `/opt/homebrew/opt/postgresql@17/bin/pg_restore`
  - `psql` at `/opt/homebrew/opt/postgresql@17/bin/psql`
- Docker installed and running
- Billing enabled on the new GCP project

---

## 11. Critical Warnings

### 1. TOKEN_ENCRYPTION_KEY Must Not Change

The `TOKEN_ENCRYPTION_KEY` is a Fernet symmetric encryption key used to encrypt OAuth access/refresh tokens stored in the database. If you change this key, **all stored OAuth tokens become undecryptable** and every user's email sync integration (Gmail/Outlook) will break. They would need to re-authorize.

**Action:** Copy the exact same `TOKEN_ENCRYPTION_KEY` value to the new project.

### 2. OAuth Redirect URIs Must Be Updated

After deploying to the new project, the backend will have a new Cloud Run URL. You must update the redirect URIs in:

- **Google Cloud Console** (OAuth 2.0 Client): `https://NEW_BACKEND_URL/api/integrations/email/callback/gmail`
- **Azure Portal** (App Registration): `https://NEW_BACKEND_URL/api/integrations/email/callback/outlook`

If these aren't updated, OAuth flows will fail with redirect_uri_mismatch errors.

### 3. Inngest Server Is Down

The self-hosted Inngest server VM (`inngest-server`, IP `35.200.184.121`) is TERMINATED. You need to either:
- Set up a new Inngest server VM in the new project
- Migrate to Inngest Cloud (managed service)
- Keep Inngest features disabled until resolved

### 4. GCS Files Cannot Be Downloaded

Billing is disabled on the source project. GCS downloads are blocked. The 16 files (15 resumes + 1 DB backup) cannot be copied until billing is re-enabled.

### 5. Alembic Migration State

The database dump includes the `alembic_version` table (head: `e9b4594d7067`). After restore, the target database will be at the same migration state. **Do NOT run `flask db upgrade`** unless there are new migrations that haven't been applied.

### 6. Database Name Is `postgres`, Not `blacklight-dev`

Some docs reference `blacklight-dev` as the database name. The actual production database is `postgres`. The migration scripts are configured correctly for this.

---

## 12. Action Items for You

### Before Migration (Required)

- [ ] **Create a new GCP project** (or provide the project ID if already created)
- [ ] **Link a billing account** to the new project
- [ ] **Authenticate gcloud** to the new account: `gcloud auth login`
- [ ] **Decide on Inngest strategy**: new VM, Inngest Cloud, or disable?
- [ ] **Decide on GCS files**: re-enable billing to copy, re-upload, or skip?

### During Migration (Script-Guided)

- [ ] Run `02-setup-target-project.sh <NEW_PROJECT_ID>`
- [ ] Set the new postgres password when prompted
- [ ] Populate Secret Manager secrets
- [ ] Run `03-restore-target-db.sh <NEW_PROJECT_ID> <DUMP_FILE>`
- [ ] Run `04-migrate-gcs-files.sh` (if billing re-enabled)
- [ ] Run `05-deploy-services.sh <NEW_PROJECT_ID>`
- [ ] Enter DATABASE_URL when prompted

### After Migration (Manual Steps)

- [ ] Update **Google OAuth redirect URI** in Google Cloud Console
- [ ] Update **Microsoft OAuth redirect URI** in Azure Portal
- [ ] Update **GitHub Actions secrets** (5 must change, see Section 8)
- [ ] Update **GitHub Actions workflow files** (hardcoded values, see Section 8)
- [ ] Update backend env vars for CORS, frontend URL, OAuth redirects
- [ ] Run validation checklist (Section 13)
- [ ] Bind WIF to your GitHub repo (command printed by setup script)

### Information Needed From You

1. **New GCP project ID** -- What do you want to name it?
2. **New database password** -- Choose a strong password for the postgres user
3. **GitHub repository path** -- e.g., `your-org/Blacklight` (for WIF binding)
4. **Inngest decision** -- Self-hosted VM, Inngest Cloud, or disable?
5. **GCS decision** -- Re-enable billing to copy files, or skip?
6. **Keep same OAuth apps?** -- Or create new Google/Microsoft OAuth applications?

---

## 13. Post-Migration Validation

After all services are deployed, verify:

| Check | Command / Action | Expected |
|-------|------------------|----------|
| Backend health | `curl https://NEW_BACKEND_URL/health` | 200 OK |
| Portal loads | Open new portal URL in browser | Login page |
| Central loads | Open new central URL in browser | Admin login page |
| DB connectivity | Login via portal, check data loads | Tenants/candidates visible |
| File upload | Upload a resume through portal | File saved to new GCS bucket |
| File download | Download an existing resume | File downloads (only if GCS migrated) |
| AI parsing | Parse a new resume | Gemini API returns parsed data |
| Email sync | Re-authorize Gmail/Outlook | OAuth flow completes, emails sync |
| Inngest | Check Inngest dashboard | Functions registered (if server running) |

---

## 14. Estimated Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: DB Dump | DONE | -- |
| Phase 2: Infrastructure Setup | 15-20 min | 20 min |
| Phase 3: DB Restore | 2-5 min | 25 min |
| Phase 4: GCS Migration | 2-5 min (if unblocked) | 30 min |
| Phase 5: Deploy Services | 10-15 min | 45 min |
| Phase 6: Post-Migration Config | 15-30 min (manual) | 1-1.5 hours |
| Validation | 15-30 min | 1.5-2 hours |

**Total estimated time: 1.5-2 hours** (assuming no blockers)

---

## Appendix: File Locations

| File | Purpose |
|------|---------|
| `scripts/migration/dumps/blacklight_dump_20260220_115831.dump` | Database backup (3.1 MB) |
| `scripts/migration/01-dump-source-db.sh` | DB dump script |
| `scripts/migration/02-setup-target-project.sh` | Infrastructure setup |
| `scripts/migration/03-restore-target-db.sh` | DB restore script |
| `scripts/migration/04-migrate-gcs-files.sh` | GCS file copy script |
| `scripts/migration/05-deploy-services.sh` | Cloud Run deployment |
| `scripts/migration/06-post-migration.sh` | Post-migration checklist |
| `CLOUD_RUN_MIGRATION.md` | Previous VM-to-Cloud Run migration guide |
| `.github/workflows/deploy-backend.yml` | Backend CI/CD (needs updating) |
| `.github/workflows/deploy-portal.yml` | Portal CI/CD (needs updating) |
| `.github/workflows/deploy-central.yml` | Central CI/CD (needs updating) |
| `.github/workflows/deploy-all.yml` | Full deploy CI/CD (needs updating) |
| `credentials/` | GCS credential files |
