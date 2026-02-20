#!/bin/bash
# =============================================================================
# STEP 2: Set up the target GCP project with all infrastructure
# =============================================================================
# Prerequisites:
#   - gcloud CLI authenticated to the NEW GCP account
#   - Billing enabled on the new account
#
# Usage: ./02-setup-target-project.sh <NEW_PROJECT_ID>
# Example: ./02-setup-target-project.sh blacklight-new-123
# =============================================================================

set -euo pipefail

# ---- Configuration ----
NEW_PROJECT_ID="${1:?Usage: $0 <NEW_PROJECT_ID>}"
REGION="asia-south1"
VPC_NAME="blacklight-vpc"
CONNECTOR_NAME="blacklight-connector"
SQL_INSTANCE_NAME="bl-db"
SQL_TIER="db-custom-2-4096"
SQL_DB_NAME="postgres"
SQL_USER="postgres"
REDIS_INSTANCE_NAME="blacklight-redis"
REDIS_SIZE_GB=1
GCS_BUCKET_NAME="${NEW_PROJECT_ID}-files"
AR_REPO_NAME="blacklight"
BACKEND_SA_NAME="blacklight-backend"
DEPLOYER_SA_NAME="github-deployer"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Target GCP Project ===${NC}"
echo ""
echo "Project ID:  ${NEW_PROJECT_ID}"
echo "Region:      ${REGION}"
echo ""

# ---- Helper function ----
run_step() {
    local step_num="$1"
    local step_desc="$2"
    shift 2
    echo -e "${YELLOW}[${step_num}] ${step_desc}${NC}"
    if "$@" 2>&1; then
        echo -e "${GREEN}  Done${NC}"
    else
        echo -e "${RED}  WARNING: Command failed (may already exist). Continuing...${NC}"
    fi
    echo ""
}

# =============================================================================
# PHASE 1: Project Setup
# =============================================================================
echo -e "${CYAN}--- Phase 1: Project Setup ---${NC}"

run_step "1/20" "Setting active project" \
    gcloud config set project "${NEW_PROJECT_ID}"

# If the project doesn't exist yet, create it
echo -e "${YELLOW}[1b/20] Checking if project exists...${NC}"
if ! gcloud projects describe "${NEW_PROJECT_ID}" &>/dev/null; then
    echo "  Project does not exist. Creating..."
    gcloud projects create "${NEW_PROJECT_ID}" --name="Blacklight"
    echo -e "${YELLOW}  IMPORTANT: You need to link a billing account!${NC}"
    echo "  Run: gcloud billing projects link ${NEW_PROJECT_ID} --billing-account=YOUR_BILLING_ACCOUNT_ID"
    echo "  Find your billing account: gcloud billing accounts list"
    echo ""
    read -p "  Press Enter after you've linked billing, or Ctrl+C to abort..."
else
    echo -e "${GREEN}  Project exists${NC}"
fi
echo ""

run_step "2/20" "Enabling required APIs" \
    gcloud services enable \
        run.googleapis.com \
        sqladmin.googleapis.com \
        redis.googleapis.com \
        artifactregistry.googleapis.com \
        secretmanager.googleapis.com \
        compute.googleapis.com \
        vpcaccess.googleapis.com \
        servicenetworking.googleapis.com \
        iam.googleapis.com \
        iamcredentials.googleapis.com \
        cloudresourcemanager.googleapis.com \
        --project="${NEW_PROJECT_ID}"

# =============================================================================
# PHASE 2: Network Infrastructure
# =============================================================================
echo -e "${CYAN}--- Phase 2: Network Infrastructure ---${NC}"

run_step "3/20" "Creating VPC network" \
    gcloud compute networks create "${VPC_NAME}" \
        --subnet-mode=auto \
        --project="${NEW_PROJECT_ID}"

run_step "4/20" "Allocating private IP range for Cloud SQL" \
    gcloud compute addresses create google-managed-services-${VPC_NAME} \
        --global \
        --purpose=VPC_PEERING \
        --prefix-length=16 \
        --network="${VPC_NAME}" \
        --project="${NEW_PROJECT_ID}"

run_step "5/20" "Creating VPC peering for Cloud SQL private IP" \
    gcloud services vpc-peerings connect \
        --service=servicenetworking.googleapis.com \
        --ranges=google-managed-services-${VPC_NAME} \
        --network="${VPC_NAME}" \
        --project="${NEW_PROJECT_ID}"

run_step "6/20" "Creating Serverless VPC Access connector" \
    gcloud compute networks vpc-access connectors create "${CONNECTOR_NAME}" \
        --region="${REGION}" \
        --network="${VPC_NAME}" \
        --range=10.8.0.0/28 \
        --min-instances=2 \
        --max-instances=10 \
        --project="${NEW_PROJECT_ID}"

# =============================================================================
# PHASE 3: Cloud SQL (PostgreSQL 15 + pgvector)
# =============================================================================
echo -e "${CYAN}--- Phase 3: Cloud SQL ---${NC}"

echo -e "${YELLOW}[7/20] Creating Cloud SQL instance (this takes 5-10 minutes)...${NC}"
gcloud sql instances create "${SQL_INSTANCE_NAME}" \
    --database-version=POSTGRES_15 \
    --tier="${SQL_TIER}" \
    --region="${REGION}" \
    --network="${VPC_NAME}" \
    --no-assign-ip \
    --storage-size=10GB \
    --storage-auto-increase \
    --availability-type=zonal \
    --project="${NEW_PROJECT_ID}" \
    2>&1 || echo -e "${RED}  WARNING: Instance creation may have failed${NC}"
echo -e "${GREEN}  Done${NC}"
echo ""

run_step "8/20" "Setting postgres user password" \
    bash -c 'echo "Enter password for postgres user:" && read -s DB_PASSWORD && gcloud sql users set-password postgres --instance='"${SQL_INSTANCE_NAME}"' --password="${DB_PASSWORD}" --project='"${NEW_PROJECT_ID}"''

echo -e "${YELLOW}[8b/20] Enabling pgvector extension...${NC}"
echo "  NOTE: pgvector will be enabled after database restore via:"
echo "  CREATE EXTENSION IF NOT EXISTS vector;"
echo ""

# Also add the database flags for pgvector
run_step "8c/20" "Adding CloudSQL database flags for pgvector" \
    gcloud sql instances patch "${SQL_INSTANCE_NAME}" \
        --database-flags=cloudsql.enable_pgvector=on \
        --project="${NEW_PROJECT_ID}"

# =============================================================================
# PHASE 4: Redis (Memorystore)
# =============================================================================
echo -e "${CYAN}--- Phase 4: Redis (Memorystore) ---${NC}"

echo -e "${YELLOW}[9/20] Creating Redis instance (this takes 5-10 minutes)...${NC}"
gcloud redis instances create "${REDIS_INSTANCE_NAME}" \
    --size="${REDIS_SIZE_GB}" \
    --region="${REGION}" \
    --redis-version=redis_7_0 \
    --network="projects/${NEW_PROJECT_ID}/global/networks/${VPC_NAME}" \
    --tier=basic \
    --project="${NEW_PROJECT_ID}" \
    2>&1 || echo -e "${RED}  WARNING: Redis creation may have failed${NC}"
echo -e "${GREEN}  Done${NC}"
echo ""

# Get Redis IP for later
echo -e "${YELLOW}[9b/20] Getting Redis IP...${NC}"
REDIS_IP=$(gcloud redis instances describe "${REDIS_INSTANCE_NAME}" \
    --region="${REGION}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(host)" 2>/dev/null || echo "UNKNOWN")
echo "  Redis IP: ${REDIS_IP}"
echo ""

# =============================================================================
# PHASE 5: GCS Bucket
# =============================================================================
echo -e "${CYAN}--- Phase 5: Cloud Storage ---${NC}"

run_step "10/20" "Creating GCS bucket" \
    gcloud storage buckets create "gs://${GCS_BUCKET_NAME}" \
        --location="${REGION}" \
        --uniform-bucket-level-access \
        --project="${NEW_PROJECT_ID}"

# =============================================================================
# PHASE 6: Artifact Registry
# =============================================================================
echo -e "${CYAN}--- Phase 6: Artifact Registry ---${NC}"

run_step "11/20" "Creating Artifact Registry repository" \
    gcloud artifacts repositories create "${AR_REPO_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --project="${NEW_PROJECT_ID}"

# =============================================================================
# PHASE 7: IAM Service Accounts
# =============================================================================
echo -e "${CYAN}--- Phase 7: IAM Service Accounts ---${NC}"

run_step "12/20" "Creating backend service account" \
    gcloud iam service-accounts create "${BACKEND_SA_NAME}" \
        --display-name="Blacklight Backend Service Account" \
        --project="${NEW_PROJECT_ID}"

BACKEND_SA_EMAIL="${BACKEND_SA_NAME}@${NEW_PROJECT_ID}.iam.gserviceaccount.com"

run_step "13/20" "Granting Cloud SQL Client role to backend SA" \
    gcloud projects add-iam-policy-binding "${NEW_PROJECT_ID}" \
        --member="serviceAccount:${BACKEND_SA_EMAIL}" \
        --role="roles/cloudsql.client"

run_step "14/20" "Granting Secret Manager Accessor role to backend SA" \
    gcloud projects add-iam-policy-binding "${NEW_PROJECT_ID}" \
        --member="serviceAccount:${BACKEND_SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor"

run_step "15/20" "Granting Storage Object Admin role to backend SA" \
    gcloud projects add-iam-policy-binding "${NEW_PROJECT_ID}" \
        --member="serviceAccount:${BACKEND_SA_EMAIL}" \
        --role="roles/storage.objectAdmin"

run_step "16/20" "Creating GitHub deployer service account" \
    gcloud iam service-accounts create "${DEPLOYER_SA_NAME}" \
        --display-name="GitHub Actions Deployer" \
        --project="${NEW_PROJECT_ID}"

DEPLOYER_SA_EMAIL="${DEPLOYER_SA_NAME}@${NEW_PROJECT_ID}.iam.gserviceaccount.com"

# Grant deployer necessary roles
for ROLE in roles/run.admin roles/artifactregistry.admin roles/iam.serviceAccountUser roles/storage.admin; do
    run_step "16b" "Granting ${ROLE} to deployer SA" \
        gcloud projects add-iam-policy-binding "${NEW_PROJECT_ID}" \
            --member="serviceAccount:${DEPLOYER_SA_EMAIL}" \
            --role="${ROLE}"
done

# =============================================================================
# PHASE 8: Workload Identity Federation (GitHub Actions)
# =============================================================================
echo -e "${CYAN}--- Phase 8: Workload Identity Federation ---${NC}"

echo -e "${YELLOW}[17/20] Setting up Workload Identity Federation for GitHub Actions...${NC}"

# Get project number
PROJECT_NUMBER=$(gcloud projects describe "${NEW_PROJECT_ID}" --format="value(projectNumber)")

# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
    --location="global" \
    --display-name="GitHub Actions Pool" \
    --project="${NEW_PROJECT_ID}" 2>&1 || echo "  Pool may already exist"

# Create Provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --project="${NEW_PROJECT_ID}" 2>&1 || echo "  Provider may already exist"

echo ""
echo -e "${YELLOW}  IMPORTANT: Update the repository attribute condition below with your GitHub repo:${NC}"
echo ""

# Bind the deployer SA to GitHub repo
# NOTE: User needs to update the repository name
GITHUB_REPO="YOUR_GITHUB_ORG/YOUR_REPO_NAME"
echo "  Run this command after updating the repo name:"
echo ""
echo "  gcloud iam service-accounts add-iam-policy-binding ${DEPLOYER_SA_EMAIL} \\"
echo "    --role='roles/iam.workloadIdentityUser' \\"
echo "    --member='principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}' \\"
echo "    --project='${NEW_PROJECT_ID}'"
echo ""

WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "  Workload Identity Provider: ${WIF_PROVIDER}"
echo "  (Save this for GitHub Actions workflow update)"
echo ""

# =============================================================================
# PHASE 9: Secret Manager
# =============================================================================
echo -e "${CYAN}--- Phase 9: Secret Manager ---${NC}"

echo -e "${YELLOW}[18/20] Creating secrets in Secret Manager...${NC}"
echo "  You'll need to add secret values manually."
echo ""

SECRETS=(
    "SECRET_KEY"
    "DATABASE_URL"
    "GOOGLE_API_KEY"
    "TOKEN_ENCRYPTION_KEY"
    "INNGEST_EVENT_KEY"
    "INNGEST_SIGNING_KEY"
    "GOOGLE_OAUTH_CLIENT_SECRET"
    "MICROSOFT_OAUTH_CLIENT_SECRET"
    "SMTP_PASSWORD"
    "GCS_CREDENTIALS_JSON"
)

for SECRET_NAME in "${SECRETS[@]}"; do
    echo "  Creating secret: ${SECRET_NAME}"
    gcloud secrets create "${SECRET_NAME}" \
        --replication-policy="automatic" \
        --project="${NEW_PROJECT_ID}" 2>/dev/null || echo "    (already exists)"
done

echo ""
echo -e "${YELLOW}  To add secret values, run for each secret:${NC}"
echo '  echo -n "YOUR_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=- --project='"${NEW_PROJECT_ID}"
echo ""

# Grant backend SA access to secrets
run_step "18b" "Granting backend SA access to all secrets" \
    bash -c "for s in ${SECRETS[*]}; do gcloud secrets add-iam-policy-binding \$s --member='serviceAccount:${BACKEND_SA_EMAIL}' --role='roles/secretmanager.secretAccessor' --project='${NEW_PROJECT_ID}' 2>/dev/null; done"

# =============================================================================
# PHASE 10: Create GCS Service Account Key (for file uploads)
# =============================================================================
echo -e "${CYAN}--- Phase 10: GCS Service Account Key ---${NC}"

run_step "19/20" "Creating GCS service account key for backend" \
    gcloud iam service-accounts keys create \
        "$(dirname "$0")/../../credentials/new-gcs-credentials.json" \
        --iam-account="${BACKEND_SA_EMAIL}" \
        --project="${NEW_PROJECT_ID}"

# =============================================================================
# Summary
# =============================================================================
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}=== Target Project Setup Complete! ===${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Project ID:          ${NEW_PROJECT_ID}"
echo "Project Number:      ${PROJECT_NUMBER}"
echo "Region:              ${REGION}"
echo ""
echo "Resources Created:"
echo "  VPC:               ${VPC_NAME}"
echo "  VPC Connector:     ${CONNECTOR_NAME}"
echo "  Cloud SQL:         ${SQL_INSTANCE_NAME} (PostgreSQL 15)"
echo "  Redis:             ${REDIS_INSTANCE_NAME} (IP: ${REDIS_IP})"
echo "  GCS Bucket:        gs://${GCS_BUCKET_NAME}"
echo "  Artifact Registry: ${AR_REPO_NAME}"
echo "  Backend SA:        ${BACKEND_SA_EMAIL}"
echo "  Deployer SA:       ${DEPLOYER_SA_EMAIL}"
echo "  WIF Provider:      ${WIF_PROVIDER}"
echo ""
echo "Secrets to populate: ${SECRETS[*]}"
echo ""
echo -e "${YELLOW}IMPORTANT NEXT STEPS:${NC}"
echo "  1. Set the postgres password (if not done): gcloud sql users set-password ..."
echo "  2. Populate all secrets in Secret Manager"
echo "  3. Update GitHub repo name in Workload Identity binding"
echo "  4. Run 03-restore-target-db.sh to restore the database"
echo "  5. Run 04-migrate-gcs-files.sh to copy GCS files"
echo ""
echo -e "${GREEN}Next step: Run 03-restore-target-db.sh${NC}"
