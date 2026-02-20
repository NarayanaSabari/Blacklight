#!/bin/bash
# =============================================================================
# STEP 5: Deploy Cloud Run services to target project
# =============================================================================
# Prerequisites:
#   - Steps 01-04 completed
#   - gcloud CLI authenticated to target project
#   - Docker images built (or CI/CD will handle)
#   - All secrets populated in Secret Manager
#
# Usage: ./05-deploy-services.sh <NEW_PROJECT_ID>
# Example: ./05-deploy-services.sh blacklight-new-123
# =============================================================================

set -euo pipefail

# ---- Configuration ----
NEW_PROJECT_ID="${1:?Usage: $0 <NEW_PROJECT_ID>}"
REGION="asia-south1"
AR_REGISTRY="${REGION}-docker.pkg.dev/${NEW_PROJECT_ID}/blacklight"
VPC_CONNECTOR="projects/${NEW_PROJECT_ID}/locations/${REGION}/connectors/blacklight-connector"
BACKEND_SA="blacklight-backend@${NEW_PROJECT_ID}.iam.gserviceaccount.com"
REPO_ROOT="$(dirname "$0")/../.."

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}=== Deploy Cloud Run Services ===${NC}"
echo ""
echo "Project:  ${NEW_PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Registry: ${AR_REGISTRY}"
echo ""

# ---- Step 1: Configure Docker for Artifact Registry ----
echo -e "${YELLOW}[1/7] Configuring Docker for Artifact Registry...${NC}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
echo -e "${GREEN}  Done${NC}"
echo ""

# ---- Step 2: Build & Push Backend ----
echo -e "${YELLOW}[2/7] Building and pushing backend image...${NC}"
docker build \
    -t "${AR_REGISTRY}/backend:latest" \
    -f "${REPO_ROOT}/server/Dockerfile.cloudrun" \
    "${REPO_ROOT}/server/" \
    2>&1
docker push "${AR_REGISTRY}/backend:latest" 2>&1
echo -e "${GREEN}  Done${NC}"
echo ""

# ---- Step 3: Build & Push Portal ----
echo -e "${YELLOW}[3/7] Building and pushing portal image...${NC}"

# Get the backend URL for the portal build
echo "  Enter the backend Cloud Run URL (e.g., https://blacklight-backend-xxxxx.a.run.app):"
read -r BACKEND_URL
BACKEND_URL="${BACKEND_URL:-https://blacklight-backend-placeholder.a.run.app}"

docker build \
    -t "${AR_REGISTRY}/portal:latest" \
    --build-arg VITE_API_BASE_URL="${BACKEND_URL}" \
    --build-arg VITE_ENVIRONMENT=production \
    -f "${REPO_ROOT}/ui/portal/Dockerfile" \
    "${REPO_ROOT}/ui/portal/" \
    2>&1
docker push "${AR_REGISTRY}/portal:latest" 2>&1
echo -e "${GREEN}  Done${NC}"
echo ""

# ---- Step 4: Build & Push Central ----
echo -e "${YELLOW}[4/7] Building and pushing central dashboard image...${NC}"
docker build \
    -t "${AR_REGISTRY}/central:latest" \
    --build-arg VITE_API_BASE_URL="${BACKEND_URL}" \
    --build-arg VITE_ENVIRONMENT=production \
    -f "${REPO_ROOT}/ui/centralD/Dockerfile" \
    "${REPO_ROOT}/ui/centralD/" \
    2>&1
docker push "${AR_REGISTRY}/central:latest" 2>&1
echo -e "${GREEN}  Done${NC}"
echo ""

# ---- Step 5: Get infrastructure details ----
echo -e "${YELLOW}[5/7] Getting infrastructure details...${NC}"

SQL_CONNECTION=$(gcloud sql instances describe bl-db \
    --project="${NEW_PROJECT_ID}" \
    --format="value(connectionName)")
echo "  SQL Connection: ${SQL_CONNECTION}"

REDIS_IP=$(gcloud redis instances describe blacklight-redis \
    --region="${REGION}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(host)")
echo "  Redis IP: ${REDIS_IP}"
echo ""

# ---- Step 6: Deploy Backend to Cloud Run ----
echo -e "${YELLOW}[6/7] Deploying backend to Cloud Run...${NC}"
echo ""
echo -e "${YELLOW}  IMPORTANT: You need to set the DATABASE_URL and other env vars.${NC}"
echo "  Update the values below before running:"
echo ""

# NOTE: The DATABASE_URL needs the actual password.
# Format: postgresql://postgres:PASSWORD@/postgres?host=/cloudsql/CONNECTION_NAME

cat <<EOF

  === MANUAL DEPLOY COMMAND (update values first) ===

  gcloud run deploy blacklight-backend \\
    --image="${AR_REGISTRY}/backend:latest" \\
    --region="${REGION}" \\
    --platform=managed \\
    --service-account="${BACKEND_SA}" \\
    --vpc-connector="${VPC_CONNECTOR}" \\
    --vpc-egress=private-ranges-only \\
    --allow-unauthenticated \\
    --memory=1Gi \\
    --cpu=1 \\
    --timeout=300 \\
    --concurrency=80 \\
    --min-instances=0 \\
    --max-instances=5 \\
    --add-cloudsql-instances="${SQL_CONNECTION}" \\
    --set-secrets="GCS_CREDENTIALS_JSON=GCS_CREDENTIALS_JSON:latest" \\
    --set-env-vars="\\
ENVIRONMENT=production,\\
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@/postgres?host=/cloudsql/${SQL_CONNECTION},\\
REDIS_URL=redis://${REDIS_IP}:6379/0,\\
REDIS_CACHE_URL=redis://${REDIS_IP}:6379/1,\\
STORAGE_BACKEND=gcs,\\
GCS_BUCKET_NAME=${NEW_PROJECT_ID}-files,\\
GCS_PROJECT_ID=${NEW_PROJECT_ID},\\
AI_PARSING_PROVIDER=gemini,\\
GEMINI_MODEL=gemini-2.5-flash,\\
GEMINI_EMBEDDING_MODEL=gemini-embedding-001,\\
GEMINI_EMBEDDING_DIMENSION=768,\\
SMTP_ENABLED=true,\\
SMTP_HOST=smtp.gmail.com,\\
SMTP_PORT=587,\\
SMTP_USE_TLS=true,\\
EMAIL_SYNC_ENABLED=true,\\
INNGEST_DEV=false\\
" \\
    --project="${NEW_PROJECT_ID}"

EOF

echo -e "${YELLOW}  Do you want to deploy now with placeholder values? (y/n)${NC}"
read -r DEPLOY_NOW

if [ "${DEPLOY_NOW}" = "y" ]; then
    echo "  Enter the DATABASE_URL (postgresql://postgres:PASS@/postgres?host=/cloudsql/${SQL_CONNECTION}):"
    read -rs DB_URL

    gcloud run deploy blacklight-backend \
        --image="${AR_REGISTRY}/backend:latest" \
        --region="${REGION}" \
        --platform=managed \
        --service-account="${BACKEND_SA}" \
        --vpc-connector="${VPC_CONNECTOR}" \
        --vpc-egress=private-ranges-only \
        --allow-unauthenticated \
        --memory=1Gi \
        --cpu=1 \
        --timeout=300 \
        --concurrency=80 \
        --min-instances=0 \
        --max-instances=5 \
        --add-cloudsql-instances="${SQL_CONNECTION}" \
        --set-secrets="GCS_CREDENTIALS_JSON=GCS_CREDENTIALS_JSON:latest" \
        --set-env-vars="\
ENVIRONMENT=production,\
DATABASE_URL=${DB_URL},\
REDIS_URL=redis://${REDIS_IP}:6379/0,\
REDIS_CACHE_URL=redis://${REDIS_IP}:6379/1,\
STORAGE_BACKEND=gcs,\
GCS_BUCKET_NAME=${NEW_PROJECT_ID}-files,\
GCS_PROJECT_ID=${NEW_PROJECT_ID},\
AI_PARSING_PROVIDER=gemini,\
GEMINI_MODEL=gemini-2.5-flash,\
GEMINI_EMBEDDING_MODEL=gemini-embedding-001,\
GEMINI_EMBEDDING_DIMENSION=768,\
SMTP_ENABLED=true,\
SMTP_HOST=smtp.gmail.com,\
SMTP_PORT=587,\
SMTP_USE_TLS=true,\
EMAIL_SYNC_ENABLED=true,\
INNGEST_DEV=false\
" \
        --project="${NEW_PROJECT_ID}" \
        2>&1

    # Get the backend URL
    BACKEND_URL=$(gcloud run services describe blacklight-backend \
        --region="${REGION}" \
        --project="${NEW_PROJECT_ID}" \
        --format="value(status.url)")
    echo ""
    echo -e "${GREEN}  Backend deployed at: ${BACKEND_URL}${NC}"
fi

echo ""

# ---- Step 7: Deploy Frontend Services ----
echo -e "${YELLOW}[7/7] Deploying frontend services...${NC}"

# Portal
echo "Deploying portal..."
gcloud run deploy blacklight-portal \
    --image="${AR_REGISTRY}/portal:latest" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --timeout=60 \
    --concurrency=100 \
    --min-instances=0 \
    --max-instances=5 \
    --project="${NEW_PROJECT_ID}" \
    2>&1

PORTAL_URL=$(gcloud run services describe blacklight-portal \
    --region="${REGION}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(status.url)")
echo -e "${GREEN}  Portal deployed at: ${PORTAL_URL}${NC}"

# Central
echo "Deploying central dashboard..."
gcloud run deploy blacklight-central \
    --image="${AR_REGISTRY}/central:latest" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --timeout=60 \
    --concurrency=100 \
    --min-instances=0 \
    --max-instances=3 \
    --project="${NEW_PROJECT_ID}" \
    2>&1

CENTRAL_URL=$(gcloud run services describe blacklight-central \
    --region="${REGION}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(status.url)")
echo -e "${GREEN}  Central deployed at: ${CENTRAL_URL}${NC}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}=== All Services Deployed! ===${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Backend:  ${BACKEND_URL:-PENDING}"
echo "Portal:   ${PORTAL_URL:-PENDING}"
echo "Central:  ${CENTRAL_URL:-PENDING}"
echo ""
echo -e "${GREEN}Next step: Run 06-post-migration.sh for OAuth updates and validation${NC}"
