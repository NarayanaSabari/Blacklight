# Blacklight - Cloud Run Migration Guide

This guide walks you through migrating Blacklight from a Docker Compose VM deployment to Google Cloud Run with managed services.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Phase 1: Set Up Managed Services](#3-phase-1-set-up-managed-services)
4. [Phase 2: Prepare Docker Images](#4-phase-2-prepare-docker-images)
5. [Phase 3: Deploy to Cloud Run](#5-phase-3-deploy-to-cloud-run)
6. [Phase 4: Set Up CI/CD](#6-phase-4-set-up-cicd)
7. [Phase 5: Inngest Configuration](#7-phase-5-inngest-configuration)
8. [Environment Variables Reference](#8-environment-variables-reference)
9. [Cost Estimation](#9-cost-estimation)
10. [Rollback Plan](#10-rollback-plan)

---

## 1. Architecture Overview

### Current Architecture (Docker Compose on VM)

```
┌─────────────────────────────────────────────────────────────────┐
│                         VM Instance                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │ Nginx   │ │ Backend │ │ Portal  │ │ Central │ │ Inngest  │  │
│  │ :80/443 │ │  :5000  │ │  :5174  │ │  :5173  │ │  :8288   │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘  │
│       │           │           │           │           │         │
│  ┌────┴───────────┴───────────┴───────────┴───────────┴────┐   │
│  │                   Docker Network                         │   │
│  └────┬────────────────────────────────────────────────┬───┘   │
│       │                                                 │       │
│  ┌────┴────┐                                      ┌────┴────┐  │
│  │ Postgres│                                      │  Redis  │  │
│  │  :5432  │                                      │  :6379  │  │
│  └─────────┘                                      └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Target Architecture (Cloud Run + Managed Services)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Platform                              │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                     Cloud Run Services                               │ │
│  │              (Each with auto-generated HTTPS URL)                    │ │
│  │                                                                      │ │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐            │ │
│  │  │  Cloud Run  │     │  Cloud Run  │     │  Cloud Run  │            │ │
│  │  │   Backend   │     │   Portal    │     │   Central   │            │ │
│  │  │  (Flask)    │     │  (React)    │     │  (React)    │            │ │
│  │  │             │     │             │     │             │            │ │
│  │  │ xxx.run.app │     │ yyy.run.app │     │ zzz.run.app │            │ │
│  │  └──────┬──────┘     └─────────────┘     └─────────────┘            │ │
│  └─────────┼───────────────────────────────────────────────────────────┘ │
│            │                                                              │
│            │  ┌───────────────────────────────────────────────────┐      │
│            │  │                Inngest Cloud                       │      │
│            │  │        (Managed Background Jobs)                   │      │
│            │  │            inngest.com                             │      │
│            └──┼───────────────────────────────────────────────────┘      │
│               │                                                           │
│    ┌──────────┴──────┐   ┌─────────────────┐   ┌─────────────────┐       │
│    │    Cloud SQL    │   │   Memorystore   │   │  Cloud Storage  │       │
│    │   (Postgres)    │   │    (Redis)      │   │   (GCS Bucket)  │       │
│    └─────────────────┘   └─────────────────┘   └─────────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Changes

| Component | VM (Current) | Cloud Run (Target) |
|-----------|--------------|-------------------|
| **Backend** | Docker Container | Cloud Run Service (auto HTTPS URL) |
| **Portal Frontend** | Docker + Nginx | Cloud Run Service (auto HTTPS URL) |
| **Central Frontend** | Docker + Nginx | Cloud Run Service (auto HTTPS URL) |
| **PostgreSQL** | Docker Container | Cloud SQL for PostgreSQL |
| **Redis** | Docker Container | Memorystore for Redis |
| **Nginx/SSL** | Docker Container | **Not needed** (Cloud Run provides HTTPS) |
| **Load Balancer** | N/A | **Not needed** (using Cloud Run URLs directly) |
| **Inngest** | Self-hosted Container | Inngest Cloud (SaaS) |
| **File Storage** | GCS (already) | GCS (no change) |

### Service URLs

After deployment, you'll have three separate URLs:

| Service | Example URL |
|---------|-------------|
| **Backend API** | `https://blacklight-backend-xxxxx-el.a.run.app` |
| **Portal (HR)** | `https://blacklight-portal-xxxxx-el.a.run.app` |
| **Central (Admin)** | `https://blacklight-central-xxxxx-el.a.run.app` |

> **Note:** Cloud Run automatically provides HTTPS with managed SSL certificates. No custom domain or load balancer needed!

---

## 2. Prerequisites

### Required Tools

```bash
# Install Google Cloud CLI
brew install google-cloud-sdk   # macOS
# OR
curl https://sdk.cloud.google.com | bash   # Linux

# Authenticate
gcloud auth login
gcloud auth application-default login

# Install Docker (if not already)
# https://docs.docker.com/get-docker/
```

### GCP Project Setup

```bash
# Set your project
export PROJECT_ID="your-project-id"
export REGION="asia-south1"  # Mumbai (closest to your users)

gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com \
  vpcaccess.googleapis.com \
  servicenetworking.googleapis.com
```

---

## 3. Phase 1: Set Up Managed Services

### 3.1 Create VPC for Private Connectivity

```bash
# Create a VPC network for private connectivity
gcloud compute networks create blacklight-vpc \
  --subnet-mode=auto

# Create an IP range for Google managed services (required for Cloud SQL private IP)
gcloud compute addresses create google-managed-services-blacklight-vpc \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=blacklight-vpc

# Create private connection between VPC and Google services
# This enables Cloud SQL and Memorystore to use private IPs
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-blacklight-vpc \
  --network=blacklight-vpc

# Wait for peering to complete (takes 1-2 minutes)
# You should see "done: true" when complete
echo "Waiting for VPC peering to complete..."
sleep 60

# Verify peering is active
gcloud services vpc-peerings list --network=blacklight-vpc

# Create VPC Access Connector (required for Cloud Run -> Cloud SQL/Redis)
gcloud compute networks vpc-access connectors create blacklight-connector \
  --region=$REGION \
  --network=blacklight-vpc \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=10
```

### 3.2 Create Cloud SQL (PostgreSQL with pgvector)

```bash
# Create Cloud SQL instance with pgvector support
gcloud sql instances create bl-db \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-4096 \
  --region=$REGION \
  --storage-size=10GB \
  --storage-auto-increase \
  --availability-type=zonal \
  --network=blacklight-vpc \
  --no-assign-ip

# Set root password
gcloud sql users set-password postgres \
  --instance=bl-db \
  --password="YOUR_SECURE_PASSWORD"

# Create application database
gcloud sql databases create blacklight-dev --instance=bl-db

# Create application user
gcloud sql users create blacklight \
  --instance=bl-db \
  --password="YOUR_APP_PASSWORD"
```

**Important:** Note the private IP of your Cloud SQL instance:
```bash
gcloud sql instances describe bl-db --format='value(ipAddresses.ipAddress)'
```

### 3.3 Enable pgvector Extension

Connect to your database and enable pgvector:

```bash
# Use Cloud SQL Proxy for connection
gcloud sql connect bl-db --user=postgres --database=blacklight-dev

# In psql:
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### 3.4 Create Memorystore (Redis)

```bash
# Create Redis instance
gcloud redis instances create blacklight-redis \
  --size=1 \
  --region=$REGION \
  --network=blacklight-vpc \
  --redis-version=redis_7_0 \
  --tier=basic

# Get the Redis host IP
gcloud redis instances describe blacklight-redis \
  --region=$REGION \
  --format='value(host)'
```

### 3.5 Create Artifact Registry

```bash
# Create container registry
gcloud artifacts repositories create blacklight \
  --repository-format=docker \
  --location=$REGION \
  --description="Blacklight container images"

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### 3.6 Set Up Secret Manager

```bash
# Store sensitive credentials in Secret Manager
echo -n "your-secret-key" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "your-db-password" | gcloud secrets create DATABASE_PASSWORD --data-file=-
echo -n "your-google-api-key" | gcloud secrets create GOOGLE_API_KEY --data-file=-
echo -n "your-token-encryption-key" | gcloud secrets create TOKEN_ENCRYPTION_KEY --data-file=-
echo -n "your-inngest-event-key" | gcloud secrets create INNGEST_EVENT_KEY --data-file=-
echo -n "your-inngest-signing-key" | gcloud secrets create INNGEST_SIGNING_KEY --data-file=-

# For OAuth secrets
echo -n "your-google-oauth-client-secret" | gcloud secrets create GOOGLE_OAUTH_CLIENT_SECRET --data-file=-
echo -n "your-microsoft-oauth-client-secret" | gcloud secrets create MICROSOFT_OAUTH_CLIENT_SECRET --data-file=-

# For SMTP
echo -n "your-smtp-password" | gcloud secrets create SMTP_PASSWORD --data-file=-

# Upload GCS credentials file
gcloud secrets create GCS_CREDENTIALS --data-file=./credentials/gcs-credentials.json
```

---

## 4. Phase 2: Prepare Docker Images

### 4.1 Backend Dockerfile for Cloud Run

The Cloud Run optimized Dockerfile is already created at `server/Dockerfile.cloudrun`.

Key differences from VM Dockerfile:
- Uses `$PORT` environment variable (Cloud Run sets this to 8080)
- Single worker with more threads (Cloud Run scales horizontally via instances)
- Longer timeout for cold starts
- No HEALTHCHECK directive (Cloud Run handles this)

### 4.2 Build and Push Images

```bash
# Set variables
export REGION="asia-south1"
export PROJECT_ID="your-project-id"
export REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight"

# Build and push Backend
docker build -t ${REGISTRY}/backend:latest \
  -f server/Dockerfile.cloudrun \
  ./server
docker push ${REGISTRY}/backend:latest
```

**For frontends, we need to know the backend URL first. Deploy backend, get the URL, then build frontends.**

---

## 5. Phase 3: Deploy to Cloud Run

### 5.1 Create Service Account

```bash
# Create service account for Cloud Run
gcloud iam service-accounts create blacklight-backend \
  --display-name="Blacklight Backend Service"

export SA_EMAIL="blacklight-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin"
```

### 5.2 Deploy Backend Service

```bash
# Set variables
export REGION="asia-south1"
export PROJECT_ID="your-project-id"
export REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight"
export SA_EMAIL="blacklight-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Get your Cloud SQL connection name
export CLOUD_SQL_CONNECTION=$(gcloud sql instances describe bl-db --format='value(connectionName)')

# Get Redis IP
export REDIS_HOST=$(gcloud redis instances describe blacklight-redis --region=$REGION --format='value(host)')

# Deploy backend
gcloud run deploy blacklight-backend \
  --image=${REGISTRY}/backend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=$SA_EMAIL \
  --vpc-connector=blacklight-connector \
  --vpc-egress=private-ranges-only \
  --add-cloudsql-instances=$CLOUD_SQL_CONNECTION \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=300 \
  --concurrency=80 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="DATABASE_URL=postgresql://blacklight:YOUR_PASSWORD@/blacklight-dev?host=/cloudsql/${CLOUD_SQL_CONNECTION}" \
  --set-env-vars="REDIS_URL=redis://${REDIS_HOST}:6379/0" \
  --set-env-vars="REDIS_CACHE_URL=redis://${REDIS_HOST}:6379/1" \
  --set-env-vars="STORAGE_BACKEND=gcs" \
  --set-env-vars="GCS_BUCKET_NAME=your-bucket-name" \
  --set-env-vars="GCS_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="AI_PARSING_PROVIDER=gemini" \
  --set-env-vars="GEMINI_MODEL=gemini-1.5-flash" \
  --set-env-vars="LOG_LEVEL=INFO" \
  --set-secrets="SECRET_KEY=SECRET_KEY:latest" \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
  --set-secrets="TOKEN_ENCRYPTION_KEY=TOKEN_ENCRYPTION_KEY:latest" \
  --set-secrets="INNGEST_EVENT_KEY=INNGEST_EVENT_KEY:latest" \
  --set-secrets="INNGEST_SIGNING_KEY=INNGEST_SIGNING_KEY:latest" \
  --set-secrets="GOOGLE_OAUTH_CLIENT_SECRET=GOOGLE_OAUTH_CLIENT_SECRET:latest" \
  --set-secrets="MICROSOFT_OAUTH_CLIENT_SECRET=MICROSOFT_OAUTH_CLIENT_SECRET:latest" \
  --set-secrets="SMTP_PASSWORD=SMTP_PASSWORD:latest"
```

### 5.3 Get Backend URL and Update CORS

```bash
# Get the backend URL
export BACKEND_URL=$(gcloud run services describe blacklight-backend --region=$REGION --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"

# Note this URL - you'll need it for frontend builds
# Example: https://blacklight-backend-xxxxx-el.a.run.app
```

### 5.4 Build and Push Frontend Images

Now that we have the backend URL, build the frontends:

```bash
# Build and push Portal (pointing to backend URL)
docker build -t ${REGISTRY}/portal:latest \
  --build-arg VITE_API_BASE_URL=${BACKEND_URL} \
  --build-arg VITE_ENVIRONMENT=production \
  --build-arg VITE_BASE_PATH=/ \
  ./ui/portal
docker push ${REGISTRY}/portal:latest

# Build and push Central (pointing to backend URL)
docker build -t ${REGISTRY}/central:latest \
  --build-arg VITE_API_BASE_URL=${BACKEND_URL} \
  --build-arg VITE_ENVIRONMENT=production \
  --build-arg VITE_BASE_PATH=/ \
  ./ui/centralD
docker push ${REGISTRY}/central:latest
```

### 5.5 Deploy Frontend Services

```bash
# Deploy Portal
gcloud run deploy blacklight-portal \
  --image=${REGISTRY}/portal:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --timeout=60 \
  --concurrency=100

# Deploy Central Dashboard
gcloud run deploy blacklight-central \
  --image=${REGISTRY}/central:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=60 \
  --concurrency=100
```

### 5.6 Get All Service URLs

```bash
# Get all URLs
echo "=== Your Cloud Run Service URLs ==="
echo ""
echo "Backend API:"
gcloud run services describe blacklight-backend --region=$REGION --format='value(status.url)'
echo ""
echo "Portal (HR/Recruiter):"
gcloud run services describe blacklight-portal --region=$REGION --format='value(status.url)'
echo ""
echo "Central (Admin Dashboard):"
gcloud run services describe blacklight-central --region=$REGION --format='value(status.url)'
```

### 5.7 Update Backend CORS Settings

Update the backend to allow requests from the frontend URLs:

```bash
# Get frontend URLs
export PORTAL_URL=$(gcloud run services describe blacklight-portal --region=$REGION --format='value(status.url)')
export CENTRAL_URL=$(gcloud run services describe blacklight-central --region=$REGION --format='value(status.url)')

# Update backend with CORS settings
gcloud run services update blacklight-backend \
  --region=$REGION \
  --set-env-vars="CORS_ORIGINS=${PORTAL_URL},${CENTRAL_URL}" \
  --set-env-vars="FRONTEND_BASE_URL=${PORTAL_URL}"
```

### 5.8 Update OAuth Redirect URIs

**Important:** Update your OAuth applications (Google Cloud Console & Azure Portal) with the new redirect URIs:

```
# Gmail OAuth Redirect URI
https://blacklight-backend-xxxxx-el.a.run.app/api/integrations/email/callback/gmail

# Outlook OAuth Redirect URI  
https://blacklight-backend-xxxxx-el.a.run.app/api/integrations/email/callback/outlook
```

Then update the backend environment:

```bash
gcloud run services update blacklight-backend \
  --region=$REGION \
  --set-env-vars="GOOGLE_OAUTH_REDIRECT_URI=${BACKEND_URL}/api/integrations/email/callback/gmail" \
  --set-env-vars="MICROSOFT_OAUTH_REDIRECT_URI=${BACKEND_URL}/api/integrations/email/callback/outlook"
```

---

## 6. Phase 4: Set Up CI/CD

### 6.1 Create Cloud Build Configuration

Create `cloudbuild.yaml` in your repository root:

```yaml
# cloudbuild.yaml - Blacklight Cloud Run Deployment
#
# This builds and deploys all three services to Cloud Run.
# Frontend builds require the backend URL, so we deploy backend first.

steps:
  # ============================================================================
  # Step 1: Build Backend
  # ============================================================================
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/backend:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/backend:latest'
      - '-f'
      - 'server/Dockerfile.cloudrun'
      - './server'
    id: 'build-backend'

  # ============================================================================
  # Step 2: Push Backend Image
  # ============================================================================
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/backend']
    waitFor: ['build-backend']
    id: 'push-backend'

  # ============================================================================
  # Step 3: Deploy Backend and Get URL
  # ============================================================================
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        gcloud run deploy blacklight-backend \
          --image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/backend:${SHORT_SHA} \
          --region=${_REGION} \
          --quiet
        
        # Get backend URL and save for frontend builds
        BACKEND_URL=$(gcloud run services describe blacklight-backend --region=${_REGION} --format='value(status.url)')
        echo "BACKEND_URL=$${BACKEND_URL}" > /workspace/backend_url.env
        echo "Backend deployed at: $${BACKEND_URL}"
    waitFor: ['push-backend']
    id: 'deploy-backend'

  # ============================================================================
  # Step 4: Build Portal with Backend URL
  # ============================================================================
  - name: 'gcr.io/cloud-builders/docker'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        source /workspace/backend_url.env
        docker build -t ${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/portal:${SHORT_SHA} \
          -t ${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/portal:latest \
          --build-arg VITE_API_BASE_URL=$${BACKEND_URL} \
          --build-arg VITE_ENVIRONMENT=production \
          --build-arg VITE_BASE_PATH=/ \
          ./ui/portal
    waitFor: ['deploy-backend']
    id: 'build-portal'

  # ============================================================================
  # Step 5: Build Central with Backend URL
  # ============================================================================
  - name: 'gcr.io/cloud-builders/docker'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        source /workspace/backend_url.env
        docker build -t ${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/central:${SHORT_SHA} \
          -t ${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/central:latest \
          --build-arg VITE_API_BASE_URL=$${BACKEND_URL} \
          --build-arg VITE_ENVIRONMENT=production \
          --build-arg VITE_BASE_PATH=/ \
          ./ui/centralD
    waitFor: ['deploy-backend']
    id: 'build-central'

  # ============================================================================
  # Step 6: Push Frontend Images
  # ============================================================================
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/portal']
    waitFor: ['build-portal']
    id: 'push-portal'

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/central']
    waitFor: ['build-central']
    id: 'push-central'

  # ============================================================================
  # Step 7: Deploy Frontends
  # ============================================================================
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'blacklight-portal'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/portal:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--quiet'
    waitFor: ['push-portal']
    id: 'deploy-portal'

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'blacklight-central'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/blacklight/central:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--quiet'
    waitFor: ['push-central']
    id: 'deploy-central'

  # ============================================================================
  # Step 8: Update Backend CORS with Frontend URLs
  # ============================================================================
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        PORTAL_URL=$(gcloud run services describe blacklight-portal --region=${_REGION} --format='value(status.url)')
        CENTRAL_URL=$(gcloud run services describe blacklight-central --region=${_REGION} --format='value(status.url)')
        
        gcloud run services update blacklight-backend \
          --region=${_REGION} \
          --update-env-vars="CORS_ORIGINS=$${PORTAL_URL},$${CENTRAL_URL}" \
          --update-env-vars="FRONTEND_BASE_URL=$${PORTAL_URL}" \
          --quiet
        
        echo ""
        echo "=== Deployment Complete ==="
        echo "Backend:  $(gcloud run services describe blacklight-backend --region=${_REGION} --format='value(status.url)')"
        echo "Portal:   $${PORTAL_URL}"
        echo "Central:  $${CENTRAL_URL}"
    waitFor: ['deploy-portal', 'deploy-central']
    id: 'update-cors'

substitutions:
  _REGION: asia-south1

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_8'

timeout: '2400s'  # 40 minutes
```

### 6.2 Create Build Trigger

```bash
# Option 1: GitHub trigger (if using GitHub)
gcloud builds triggers create github \
  --name="blacklight-deploy" \
  --repo-owner="YOUR_GITHUB_USERNAME" \
  --repo-name="Blacklight" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml"

# Option 2: Manual trigger
gcloud builds submit --config=cloudbuild.yaml
```

---

## 7. Phase 5: Inngest Configuration

### 7.1 Migrate to Inngest Cloud

Since we're no longer self-hosting Inngest, you need to use Inngest Cloud:

1. **Sign up for Inngest Cloud:** https://app.inngest.com

2. **Create a new app** called `blacklight` and get your:
   - Event Key (for sending events)
   - Signing Key (for verifying webhooks)

3. **Store keys in Secret Manager** (if not already done):

```bash
echo -n "your-inngest-event-key" | gcloud secrets create INNGEST_EVENT_KEY --data-file=-
echo -n "your-inngest-signing-key" | gcloud secrets create INNGEST_SIGNING_KEY --data-file=-
```

4. **Update backend environment variables:**

```bash
export BACKEND_URL=$(gcloud run services describe blacklight-backend --region=$REGION --format='value(status.url)')

gcloud run services update blacklight-backend \
  --region=$REGION \
  --set-env-vars="INNGEST_DEV=false" \
  --update-secrets="INNGEST_EVENT_KEY=INNGEST_EVENT_KEY:latest" \
  --update-secrets="INNGEST_SIGNING_KEY=INNGEST_SIGNING_KEY:latest"
```

5. **Register your Inngest endpoint** in the Inngest Cloud dashboard:
   - Go to https://app.inngest.com
   - Navigate to your app → Deploy
   - Add sync URL: `https://blacklight-backend-xxxxx-el.a.run.app/api/inngest`
   - Click "Sync"

### 7.2 Verify Inngest Functions

After syncing, you should see these functions in the Inngest dashboard:
- `parse-resume`
- `match-resume-to-jobs`
- `sync-gmail-emails`
- `sync-outlook-emails`
- `process-email-job`
- etc.

---

## 8. Environment Variables Reference

### Backend (Cloud Run)

| Variable | Description | Source |
|----------|-------------|--------|
| `ENVIRONMENT` | `production` | env-var |
| `SECRET_KEY` | Flask secret | Secret Manager |
| `DATABASE_URL` | Cloud SQL connection | env-var (with socket) |
| `REDIS_URL` | Memorystore URL | env-var |
| `REDIS_CACHE_URL` | Memorystore cache URL | env-var |
| `CORS_ORIGINS` | Frontend URLs (comma-separated) | env-var |
| `FRONTEND_BASE_URL` | Portal URL (for email links) | env-var |
| `GOOGLE_API_KEY` | Gemini API key | Secret Manager |
| `GCS_BUCKET_NAME` | Storage bucket | env-var |
| `GCS_PROJECT_ID` | GCP project | env-var |
| `INNGEST_DEV` | `false` for Cloud | env-var |
| `INNGEST_EVENT_KEY` | Inngest event key | Secret Manager |
| `INNGEST_SIGNING_KEY` | Inngest signing key | Secret Manager |
| `TOKEN_ENCRYPTION_KEY` | OAuth token encryption | Secret Manager |
| `GOOGLE_OAUTH_CLIENT_ID` | Gmail OAuth | env-var |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Gmail OAuth secret | Secret Manager |
| `GOOGLE_OAUTH_REDIRECT_URI` | Gmail callback URL | env-var |
| `MICROSOFT_OAUTH_CLIENT_ID` | Outlook OAuth | env-var |
| `MICROSOFT_OAUTH_CLIENT_SECRET` | Outlook OAuth secret | Secret Manager |
| `MICROSOFT_OAUTH_REDIRECT_URI` | Outlook callback URL | env-var |
| `SMTP_*` | Email settings | env-var / Secret Manager |

### Frontend (Build-time Args)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend Cloud Run URL |
| `VITE_ENVIRONMENT` | `production` |
| `VITE_BASE_PATH` | `/` (root, since each app has its own URL) |

---

## 9. Cost Estimation

### Monthly Cost Breakdown (Estimated)

| Service | Specification | Est. Cost/Month |
|---------|--------------|-----------------|
| **Cloud Run - Backend** | 2 vCPU, 2GB, min 1 instance | $30-50 |
| **Cloud Run - Portal** | 1 vCPU, 512MB, min 0 | $5-15 |
| **Cloud Run - Central** | 1 vCPU, 512MB, min 0 | $3-10 |
| **Cloud SQL** | db-custom-2-4096, 20GB | $50-70 |
| **Memorystore Redis** | 1GB Basic | $30-40 |
| **Artifact Registry** | ~5GB storage | $1-2 |
| **VPC Connector** | 2 instances | $10-15 |
| **Inngest Cloud** | Free tier / Pro | $0-25 |
| **Cloud Storage** | Existing bucket | ~$5 |
| **Total** | | **$130-230/month** |

> **Note:** No Load Balancer cost! Saved ~$18-25/month by using Cloud Run URLs directly.

### Cost Optimization Tips

1. **Use committed use discounts** for Cloud SQL (up to 52% off)
2. **Set min-instances=0** for frontends during low traffic
3. **Monitor with Cloud Monitoring** to right-size resources
4. **Consider Cloud SQL shared CPU** for dev/staging environments

---

## 10. Rollback Plan

### If Migration Fails

1. **Keep VM running** until Cloud Run is fully tested
2. **Database backup:** Export data before migration
3. **Quick switch:** Just use VM URLs instead of Cloud Run URLs

### Rollback Steps

```bash
# If you need to rollback, simply:
# 1. Point your apps/bookmarks back to the VM URLs
# 2. Stop/delete Cloud Run services if needed

gcloud run services delete blacklight-backend --region=$REGION --quiet
gcloud run services delete blacklight-portal --region=$REGION --quiet
gcloud run services delete blacklight-central --region=$REGION --quiet
```

---

## Migration Checklist

- [ ] **Phase 1: Managed Services**
  - [ ] Create VPC and VPC Connector
  - [ ] Create Cloud SQL instance with pgvector
  - [ ] Create Memorystore Redis
  - [ ] Create Artifact Registry
  - [ ] Set up Secret Manager secrets

- [ ] **Phase 2: Docker Images**
  - [ ] Verify Cloud Run Dockerfile exists (`server/Dockerfile.cloudrun`)
  - [ ] Build and push backend image

- [ ] **Phase 3: Cloud Run Deployment**
  - [ ] Create service account with permissions
  - [ ] Deploy backend service
  - [ ] Get backend URL
  - [ ] Build and push frontend images (with backend URL)
  - [ ] Deploy portal service
  - [ ] Deploy central service
  - [ ] Update CORS settings
  - [ ] Update OAuth redirect URIs

- [ ] **Phase 4: CI/CD**
  - [ ] Create `cloudbuild.yaml`
  - [ ] Set up Cloud Build trigger

- [ ] **Phase 5: Inngest**
  - [ ] Sign up for Inngest Cloud
  - [ ] Store keys in Secret Manager
  - [ ] Update backend environment
  - [ ] Register endpoint in Inngest dashboard
  - [ ] Verify functions are synced

- [ ] **Final Verification**
  - [ ] Test backend API endpoints
  - [ ] Test Portal login and features
  - [ ] Test Central login and features
  - [ ] Test OAuth flows (Gmail/Outlook)
  - [ ] Test file uploads to GCS
  - [ ] Test Inngest background jobs (resume parsing, email sync)
  - [ ] Monitor Cloud Logging for errors

---

## Quick Reference: Your Service URLs

After deployment, bookmark these URLs:

| Service | URL |
|---------|-----|
| **Backend API** | `https://blacklight-backend-xxxxx-el.a.run.app` |
| **Portal (HR)** | `https://blacklight-portal-xxxxx-el.a.run.app` |
| **Central (Admin)** | `https://blacklight-central-xxxxx-el.a.run.app` |
| **Inngest Dashboard** | `https://app.inngest.com` |
| **Cloud Console** | `https://console.cloud.google.com/run?project=YOUR_PROJECT` |

---

## Support & Resources

- **Cloud Run Documentation:** https://cloud.google.com/run/docs
- **Cloud SQL Documentation:** https://cloud.google.com/sql/docs
- **Inngest Cloud:** https://www.inngest.com/docs
- **GCP Pricing Calculator:** https://cloud.google.com/products/calculator

---

*Last updated: January 2026*
