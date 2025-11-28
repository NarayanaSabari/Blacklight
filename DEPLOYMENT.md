# Blacklight Cloud Run Deployment Guide

This guide explains how to deploy Blacklight to Google Cloud Run with **auto-scaling**.

## Architecture

Blacklight is deployed as **3 separate Cloud Run services**:

| Service | Description | Resources | Auto-Scale |
|---------|-------------|-----------|------------|
| `blacklight-api` | Flask backend API | 2 CPU, 2GB RAM | 0-100 instances |
| `blacklight-portal` | React frontend (tenant portal) | 1 CPU, 256MB RAM | 0-10 instances |
| `blacklight-centrald` | React frontend (admin platform) | 1 CPU, 256MB RAM | 0-5 instances |

### Infrastructure Services

| Service | Provider | Notes |
|---------|----------|-------|
| **Database** | Cloud SQL PostgreSQL | Or Neon/Supabase |
| **Redis** | Upstash (recommended) | Or Memorystore |
| **File Storage** | Google Cloud Storage | Already configured |
| **Background Jobs** | Inngest Cloud | NOT self-hosted |
| **Logging** | Cloud Logging | Automatic |
| **AI/ML** | Google Gemini API | Resume parsing |

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed locally
4. **Inngest Account** at https://inngest.com (free tier available)

## Step-by-Step Deployment

### Step 1: Set up GCP Project

```bash
# Set your project
export GCP_PROJECT_ID=blacklight-477315
export GCP_REGION=us-central1
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com
```

### Step 2: Set up Database (Choose One)

#### Option A: Cloud SQL PostgreSQL (Recommended)

```bash
# Create Cloud SQL instance
gcloud sql instances create blacklight-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$GCP_REGION \
    --root-password=YOUR_SECURE_PASSWORD

# Create database
gcloud sql databases create blacklight --instance=blacklight-db

# Create user
gcloud sql users create blacklight_user \
    --instance=blacklight-db \
    --password=YOUR_SECURE_PASSWORD

# Get connection name
gcloud sql instances describe blacklight-db --format='value(connectionName)'
# Output: blacklight-477315:us-central1:blacklight-db

# DATABASE_URL format for Cloud Run:
# postgresql://blacklight_user:PASSWORD@/blacklight?host=/cloudsql/blacklight-477315:us-central1:blacklight-db
```

#### Option B: Neon (Serverless PostgreSQL - Cheaper)

1. Go to https://neon.tech
2. Create a new project
3. Copy the connection string (already in correct format)

### Step 3: Set up Redis (Choose One)

#### Option A: Upstash (Recommended - Serverless)

1. Go to https://upstash.com
2. Create a Redis database
3. Copy the `UPSTASH_REDIS_REST_URL` - use it as `REDIS_URL`

#### Option B: Memorystore for Redis

```bash
gcloud redis instances create blacklight-redis \
    --size=1 \
    --region=$GCP_REGION \
    --redis-version=redis_7_0

# Get IP (requires VPC connector for Cloud Run)
gcloud redis instances describe blacklight-redis --region=$GCP_REGION --format='value(host)'
```

### Step 4: Set up Inngest (Background Jobs)

1. Go to https://app.inngest.com
2. Create an account/sign in
3. Create a new app called "Blacklight"
4. Go to **Manage** → **Keys**
5. Copy:
   - **Event Key** → `INNGEST_EVENT_KEY`
   - **Signing Key** → `INNGEST_SIGNING_KEY`

### Step 5: Create Secrets in Secret Manager

```bash
# Run the setup script
chmod +x setup-secrets.sh
./setup-secrets.sh

# Or manually create each secret:

# 1. Secret Key (generate random)
echo -n "$(openssl rand -hex 32)" | \
    gcloud secrets create blacklight-secret-key --data-file=- --replication-policy="automatic"

# 2. Database URL
echo -n "postgresql://blacklight_user:PASSWORD@/blacklight?host=/cloudsql/blacklight-477315:us-central1:blacklight-db" | \
    gcloud secrets create blacklight-database-url --data-file=-

# 3. Redis URL
echo -n "redis://default:PASSWORD@us1-xyz.upstash.io:6379" | \
    gcloud secrets create blacklight-redis-url --data-file=-

# 4. Gemini API Key
echo -n "AIzaSyBJxTplIZXDXyQRLcxjuZ9EotkIE3p2NtM" | \
    gcloud secrets create blacklight-gemini-api-key --data-file=-

# 5. SMTP Password
echo -n "rkmz ndbd wtbb nhjb" | \
    gcloud secrets create blacklight-smtp-password --data-file=-

# 6. Inngest Keys
echo -n "YOUR_INNGEST_EVENT_KEY" | \
    gcloud secrets create blacklight-inngest-event-key --data-file=-

echo -n "YOUR_INNGEST_SIGNING_KEY" | \
    gcloud secrets create blacklight-inngest-signing-key --data-file=-

# 7. GCS Credentials (from file)
gcloud secrets create blacklight-gcs-credentials --data-file=./blacklight-bucket.json
```

### Step 6: Grant Cloud Run Access to Secrets

```bash
# Get Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant access to all secrets
for SECRET in blacklight-secret-key blacklight-database-url blacklight-redis-url \
              blacklight-gemini-api-key blacklight-smtp-password \
              blacklight-inngest-event-key blacklight-inngest-signing-key \
              blacklight-gcs-credentials; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor"
done
```

### Step 7: Deploy with Cloud Build

```bash
# From project root directory
gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=_PROJECT_ID=$GCP_PROJECT_ID,_REGION=$GCP_REGION
```

### Step 8: Configure Inngest Webhook

After deployment, configure Inngest to call your Cloud Run service:

1. Go to https://app.inngest.com → Your App → **Manage**
2. Add **Serve URL**: `https://blacklight-api-HASH.us-central1.run.app/api/inngest`
3. Click **Sync**

## Environment Variables Reference

### Stored in Secret Manager (Sensitive)

| Secret Name | Description |
|-------------|-------------|
| `blacklight-secret-key` | Flask secret key |
| `blacklight-database-url` | PostgreSQL connection |
| `blacklight-redis-url` | Redis connection |
| `blacklight-gemini-api-key` | Gemini AI API key |
| `blacklight-smtp-password` | Email password |
| `blacklight-inngest-event-key` | Inngest event key |
| `blacklight-inngest-signing-key` | Inngest signing key |
| `blacklight-gcs-credentials` | GCS service account JSON |

### Set Directly in Cloud Run (Non-Sensitive)

| Variable | Value |
|----------|-------|
| `ENVIRONMENT` | production |
| `FLASK_ENV` | production |
| `FLASK_DEBUG` | false |
| `LOG_LEVEL` | INFO |
| `LOG_FORMAT` | json |
| `STORAGE_BACKEND` | gcs |
| `GCS_BUCKET_NAME` | blacklight_freelance |
| `GCS_PROJECT_ID` | blacklight-477315 |
| `AI_PARSING_PROVIDER` | gemini |
| `GEMINI_MODEL` | gemini-2.5-flash |
| `MAX_FILE_SIZE_MB` | 10 |
| `SMTP_HOST` | smtp.gmail.com |
| `SMTP_PORT` | 587 |
| `SMTP_USE_TLS` | true |
| `SMTP_FROM_EMAIL` | sabariokg@gmail.com |
| `SMTP_FROM_NAME` | BlackLight Company HR |
| `SMTP_USERNAME` | sabariokg@gmail.com |
| `INNGEST_DEV` | false |
| `CORS_ORIGINS` | (frontend URLs) |
| `FRONTEND_BASE_URL` | (portal URL) |

## Auto-Scaling Configuration

The backend is configured for auto-scaling:

```yaml
min-instances: 0      # Scale to zero when idle (cost savings)
max-instances: 100    # Scale up to 100 instances under load
concurrency: 80       # 80 concurrent requests per instance
cpu: 2                # 2 vCPUs per instance
memory: 2Gi           # 2GB RAM per instance
```

### How Auto-Scaling Works

1. **Scale to Zero**: When no traffic, instances scale down to 0 (no cost)
2. **Cold Start**: First request after idle takes ~2-5 seconds
3. **Scale Up**: New instances spin up when concurrency > 80%
4. **Scale Down**: Instances terminate after idle timeout

### To Reduce Cold Starts (Optional)

Set minimum instances to 1:
```bash
gcloud run services update blacklight-api \
    --min-instances=1 \
    --region=us-central1
```

## Monitoring

### View Logs

```bash
# Backend logs
gcloud run services logs read blacklight-api --region us-central1

# Stream logs in real-time
gcloud run services logs tail blacklight-api --region us-central1

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=50
```

### Cloud Run Console

- **Dashboard**: https://console.cloud.google.com/run
- **Logs**: https://console.cloud.google.com/logs
- **Monitoring**: https://console.cloud.google.com/monitoring

## Troubleshooting

### Container fails to start

1. Check logs: `gcloud run services logs read blacklight-api --region us-central1`
2. Verify all secrets are created and accessible
3. Test locally with Docker:
   ```bash
   docker run -p 8080:8080 -e PORT=8080 gcr.io/$PROJECT_ID/blacklight-api
   ```

### Database connection issues

1. Ensure Cloud SQL Admin API is enabled
2. Add Cloud SQL Client role to Cloud Run service account:
   ```bash
   gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="serviceAccount:${SERVICE_ACCOUNT}" \
       --role="roles/cloudsql.client"
   ```
3. Check connection string format

### CORS errors

1. Verify `CORS_ORIGINS` includes both frontend URLs
2. No trailing slashes in URLs
3. Update and redeploy if URLs changed

### Inngest not receiving events

1. Verify webhook URL is configured in Inngest dashboard
2. Check `INNGEST_SIGNING_KEY` is correct
3. Ensure `/api/inngest` endpoint is accessible

## Cost Estimation

| Service | Configuration | Est. Monthly Cost |
|---------|--------------|-------------------|
| Cloud Run (API) | 2 CPU, 2GB, scale to zero | $0 - $50 |
| Cloud Run (Portal) | 1 CPU, 256MB | $0 - $10 |
| Cloud Run (CentralD) | 1 CPU, 256MB | $0 - $5 |
| Cloud SQL | db-f1-micro | ~$10/month |
| Upstash Redis | Free tier | $0 |
| Cloud Storage | Per GB | ~$0.02/GB |
| Inngest | Free tier (25K events) | $0 |

**Total**: ~$10-75/month depending on usage

## Security Best Practices

1. **Never** commit `.env` or secrets to version control
2. Use Secret Manager for all sensitive values
3. Enable Cloud Armor for DDoS protection (optional)
4. Use Cloud IAM for fine-grained access control
5. Enable audit logging

## Custom Domain Setup (Optional)

```bash
# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
    --service blacklight-portal \
    --domain portal.yourdomain.com \
    --region us-central1

# Get DNS records to configure
gcloud run domain-mappings describe \
    --domain portal.yourdomain.com \
    --region us-central1
```

## Updating the Deployment

```bash
# Redeploy after code changes
gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=_PROJECT_ID=$GCP_PROJECT_ID

# Or update just the backend
cd server
docker build -t gcr.io/$GCP_PROJECT_ID/blacklight-api:latest .
docker push gcr.io/$GCP_PROJECT_ID/blacklight-api:latest
gcloud run deploy blacklight-api \
    --image gcr.io/$GCP_PROJECT_ID/blacklight-api:latest \
    --region us-central1
```
