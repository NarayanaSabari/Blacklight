#!/bin/bash
# =============================================================================
# STEP 4: Migrate GCS bucket files from source to target project
# =============================================================================
# Prerequisites:
#   - gcloud CLI authenticated with access to BOTH projects
#   - gsutil available
#
# Usage: ./04-migrate-gcs-files.sh <NEW_PROJECT_ID>
# Example: ./04-migrate-gcs-files.sh blacklight-new-123
# =============================================================================

set -euo pipefail

# ---- Configuration ----
NEW_PROJECT_ID="${1:?Usage: $0 <NEW_PROJECT_ID>}"
SOURCE_BUCKET="gs://mvp-blacklight-files"
TARGET_BUCKET="gs://${NEW_PROJECT_ID}-files"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== GCS File Migration ===${NC}"
echo ""
echo "Source Bucket: ${SOURCE_BUCKET}"
echo "Target Bucket: ${TARGET_BUCKET}"
echo ""

# ---- Step 1: Check source bucket ----
echo -e "${YELLOW}[1/4] Checking source bucket...${NC}"
echo "Source bucket contents:"
gsutil ls "${SOURCE_BUCKET}/" 2>&1
echo ""
echo "Source bucket size:"
gsutil du -sh "${SOURCE_BUCKET}/" 2>&1
echo ""

# ---- Step 2: Verify target bucket exists ----
echo -e "${YELLOW}[2/4] Verifying target bucket...${NC}"
if gsutil ls "${TARGET_BUCKET}/" &>/dev/null; then
    echo -e "${GREEN}  Target bucket exists${NC}"
else
    echo "  Target bucket does not exist. Creating..."
    gcloud storage buckets create "${TARGET_BUCKET}" \
        --location=asia-south1 \
        --uniform-bucket-level-access \
        --project="${NEW_PROJECT_ID}"
    echo -e "${GREEN}  Created${NC}"
fi
echo ""

# ---- Step 3: Copy files ----
echo -e "${YELLOW}[3/4] Copying files (with parallel threads)...${NC}"
echo "  This copies all files preserving directory structure."
echo ""

gsutil -m cp -r "${SOURCE_BUCKET}/*" "${TARGET_BUCKET}/" 2>&1

echo ""

# ---- Step 4: Verify ----
echo -e "${YELLOW}[4/4] Verifying migration...${NC}"
echo ""
echo "Source file count:"
gsutil ls -r "${SOURCE_BUCKET}/**" 2>/dev/null | wc -l
echo ""
echo "Target file count:"
gsutil ls -r "${TARGET_BUCKET}/**" 2>/dev/null | wc -l
echo ""
echo "Target bucket size:"
gsutil du -sh "${TARGET_BUCKET}/" 2>&1
echo ""

echo -e "${GREEN}=== GCS File Migration Complete ===${NC}"
echo ""
echo -e "${GREEN}Next step: Run 05-deploy-services.sh to deploy Cloud Run services${NC}"
