#!/bin/bash
# =============================================================================
# STEP 6: Post-migration tasks - OAuth updates, GitHub Actions, validation
# =============================================================================
# Prerequisites:
#   - Steps 01-05 completed
#   - All Cloud Run services deployed
#
# Usage: ./06-post-migration.sh <NEW_PROJECT_ID>
# =============================================================================

set -euo pipefail

# ---- Configuration ----
NEW_PROJECT_ID="${1:?Usage: $0 <NEW_PROJECT_ID>}"
REGION="asia-south1"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}=== Post-Migration Tasks ===${NC}"
echo ""

# ---- Get service URLs ----
echo -e "${YELLOW}[1/6] Getting deployed service URLs...${NC}"
BACKEND_URL=$(gcloud run services describe blacklight-backend \
    --region="${REGION}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(status.url)" 2>/dev/null || echo "NOT_DEPLOYED")
PORTAL_URL=$(gcloud run services describe blacklight-portal \
    --region="${REGION}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(status.url)" 2>/dev/null || echo "NOT_DEPLOYED")
CENTRAL_URL=$(gcloud run services describe blacklight-central \
    --region="${REGION}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(status.url)" 2>/dev/null || echo "NOT_DEPLOYED")

echo "  Backend: ${BACKEND_URL}"
echo "  Portal:  ${PORTAL_URL}"
echo "  Central: ${CENTRAL_URL}"
echo ""

# ---- Get project number for WIF ----
PROJECT_NUMBER=$(gcloud projects describe "${NEW_PROJECT_ID}" --format="value(projectNumber)" 2>/dev/null || echo "UNKNOWN")

# =============================================================================
# OAuth Updates Checklist
# =============================================================================
echo -e "${CYAN}--- [2/6] OAuth Configuration Updates Required ---${NC}"
echo ""
echo -e "${YELLOW}A) Google OAuth (Gmail Integration):${NC}"
echo "   Go to: https://console.cloud.google.com/apis/credentials"
echo "   Update the OAuth 2.0 Client redirect URI to:"
echo "   ${BACKEND_URL}/api/integrations/email/callback/gmail"
echo ""
echo -e "${YELLOW}B) Microsoft OAuth (Outlook Integration):${NC}"
echo "   Go to: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps"
echo "   App ID: 62b62b68-594a-479f-ab9f-3a0a5b0d02ca"
echo "   Update the redirect URI to:"
echo "   ${BACKEND_URL}/api/integrations/email/callback/outlook"
echo ""

# =============================================================================
# GitHub Actions Updates
# =============================================================================
echo -e "${CYAN}--- [3/6] GitHub Actions Secrets to Update ---${NC}"
echo ""
echo "Go to: https://github.com/YOUR_ORG/YOUR_REPO/settings/secrets/actions"
echo ""
echo "Update these secrets:"
echo "  GCP_PROJECT_ID          = ${NEW_PROJECT_ID}"
echo "  GCP_SA_KEY              = (new service account key JSON)"
echo "  DATABASE_URL            = postgresql://postgres:PASSWORD@/postgres?host=/cloudsql/${NEW_PROJECT_ID}:${REGION}:bl-db"
echo "  BACKEND_URL             = ${BACKEND_URL}"
echo "  GCS_CREDENTIALS_JSON    = (new GCS credentials from credentials/new-gcs-credentials.json)"
echo ""
echo "Keep these secrets the same (unless you want to change them):"
echo "  SECRET_KEY              = (keep same)"
echo "  GOOGLE_API_KEY          = (keep same or generate new)"
echo "  TOKEN_ENCRYPTION_KEY    = (MUST keep same - encrypts stored OAuth tokens)"
echo "  SMTP_PASSWORD           = (keep same)"
echo "  INNGEST_EVENT_KEY       = (keep same or generate new)"
echo "  INNGEST_SIGNING_KEY     = (keep same or generate new)"
echo ""

echo -e "${YELLOW}  WARNING: TOKEN_ENCRYPTION_KEY MUST remain the same!${NC}"
echo "  It's used to encrypt/decrypt stored OAuth tokens in the database."
echo "  Changing it will invalidate all email sync integrations."
echo ""

# =============================================================================
# GitHub Actions Workflow Updates
# =============================================================================
echo -e "${CYAN}--- [4/6] GitHub Actions Workflow File Updates ---${NC}"
echo ""
echo "Update these files with the new Workload Identity Provider:"
echo ""
echo "  .github/workflows/deploy-backend.yml"
echo "  .github/workflows/deploy-portal.yml"
echo "  .github/workflows/deploy-central.yml"
echo "  .github/workflows/deploy-all.yml"
echo ""
echo "Change the workload_identity_provider to:"
echo "  projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo ""
echo "Change the service_account to:"
echo "  github-deployer@${NEW_PROJECT_ID}.iam.gserviceaccount.com"
echo ""

# =============================================================================
# Environment Variable Updates in Backend
# =============================================================================
echo -e "${CYAN}--- [5/6] Backend Environment Variables to Update ---${NC}"
echo ""
echo "These env vars on the Cloud Run backend service need updating:"
echo ""
echo "  GOOGLE_OAUTH_REDIRECT_URI      = ${BACKEND_URL}/api/integrations/email/callback/gmail"
echo "  MICROSOFT_OAUTH_REDIRECT_URI   = ${BACKEND_URL}/api/integrations/email/callback/outlook"
echo "  FRONTEND_BASE_URL              = ${PORTAL_URL}"
echo "  CORS_ORIGINS                   = ${PORTAL_URL},${CENTRAL_URL}"
echo "  INNGEST_SERVE_HOST             = ${BACKEND_URL}"
echo "  INNGEST_BASE_URL               = (new Inngest server URL, if self-hosted)"
echo ""
echo "Run this to update:"
echo ""
echo "  gcloud run services update blacklight-backend \\"
echo "    --region=${REGION} \\"
echo "    --update-env-vars=\"\\"
echo "GOOGLE_OAUTH_REDIRECT_URI=${BACKEND_URL}/api/integrations/email/callback/gmail,\\"
echo "MICROSOFT_OAUTH_REDIRECT_URI=${BACKEND_URL}/api/integrations/email/callback/outlook,\\"
echo "FRONTEND_BASE_URL=${PORTAL_URL},\\"
echo "CORS_ORIGINS=${PORTAL_URL}\\,${CENTRAL_URL},\\"
echo "INNGEST_SERVE_HOST=${BACKEND_URL}\\"
echo "\" \\"
echo "    --project=${NEW_PROJECT_ID}"
echo ""

# =============================================================================
# Validation
# =============================================================================
echo -e "${CYAN}--- [6/6] Validation Checklist ---${NC}"
echo ""
echo "Run these checks to verify the migration:"
echo ""
echo "1. Health check:"
echo "   curl ${BACKEND_URL}/health"
echo ""
echo "2. Frontend loads:"
echo "   Open ${PORTAL_URL} in browser"
echo "   Open ${CENTRAL_URL} in browser"
echo ""
echo "3. Database connectivity:"
echo "   curl ${BACKEND_URL}/api/health/db  (if endpoint exists)"
echo ""
echo "4. File upload/download:"
echo "   Upload a test resume through the portal"
echo ""
echo "5. AI features:"
echo "   Parse a test resume to verify Gemini API connectivity"
echo ""
echo "6. Email sync:"
echo "   Re-authorize Gmail/Outlook OAuth (users need to re-auth)"
echo ""
echo "7. Inngest:"
echo "   Check Inngest dashboard for function registration"
echo ""

# ---- Final Summary ----
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}=== Migration Checklist Complete ===${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Old Project: mvp-blacklight"
echo "New Project: ${NEW_PROJECT_ID}"
echo ""
echo "IMPORTANT REMINDERS:"
echo "  - Keep the old project alive for 1-2 weeks as fallback"
echo "  - TOKEN_ENCRYPTION_KEY must be the same in both projects"
echo "  - Users with Gmail/Outlook sync will need to re-authorize"
echo "  - Inngest self-hosted server needs separate VM setup"
echo "  - Update DNS records if using custom domain"
echo ""
echo -e "${GREEN}Migration complete!${NC}"
