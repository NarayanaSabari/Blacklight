#!/bin/bash
# =============================================================================
# STEP 1: Dump the source Cloud SQL database to local machine
# =============================================================================
# Prerequisites:
#   - gcloud CLI authenticated to source project (mvp-blacklight)
#   - cloud-sql-proxy installed (brew install cloud-sql-proxy)
#   - PostgreSQL 17 client tools installed (brew install postgresql@17)
#
# Usage: ./01-dump-source-db.sh
# =============================================================================

set -euo pipefail

# ---- Configuration ----
SOURCE_PROJECT="mvp-blacklight"
SOURCE_INSTANCE="bl-db"
SOURCE_CONNECTION="mvp-blacklight:asia-south1:bl-db"
SOURCE_DB="postgres"  # The database to dump
SOURCE_USER="postgres"
PROXY_PORT=5432
PG_DUMP="/opt/homebrew/opt/postgresql@17/bin/pg_dump"
DUMP_DIR="$(dirname "$0")/dumps"
DUMP_FILE="${DUMP_DIR}/blacklight_dump_$(date +%Y%m%d_%H%M%S).sql"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Blacklight Database Dump (Source Project) ===${NC}"
echo ""
echo "Source Project:    ${SOURCE_PROJECT}"
echo "Source Instance:   ${SOURCE_INSTANCE}"
echo "Source Database:   ${SOURCE_DB}"
echo "Dump File:         ${DUMP_FILE}"
echo ""

# ---- Step 1: Verify gcloud auth ----
echo -e "${YELLOW}[1/5] Verifying gcloud authentication...${NC}"
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null)
echo "  Current project: ${CURRENT_PROJECT}"
echo "  Current account: ${CURRENT_ACCOUNT}"

if [ "${CURRENT_PROJECT}" != "${SOURCE_PROJECT}" ]; then
    echo -e "${YELLOW}  Switching to source project...${NC}"
    gcloud config set project "${SOURCE_PROJECT}"
fi

# ---- Step 2: Verify Cloud SQL instance is accessible ----
echo -e "${YELLOW}[2/5] Verifying Cloud SQL instance...${NC}"
INSTANCE_STATUS=$(gcloud sql instances describe "${SOURCE_INSTANCE}" --format="value(state)" 2>&1)
if [ "${INSTANCE_STATUS}" != "RUNNABLE" ]; then
    echo -e "${RED}  ERROR: Cloud SQL instance is not RUNNABLE (status: ${INSTANCE_STATUS})${NC}"
    echo "  You may need to start the instance first."
    exit 1
fi
echo -e "${GREEN}  Instance is RUNNABLE${NC}"

# ---- Step 3: Create dump directory ----
echo -e "${YELLOW}[3/5] Creating dump directory...${NC}"
mkdir -p "${DUMP_DIR}"

# ---- Step 4: Start Cloud SQL Auth Proxy ----
echo -e "${YELLOW}[4/5] Starting Cloud SQL Auth Proxy on port ${PROXY_PORT}...${NC}"
echo "  Connection: ${SOURCE_CONNECTION}"

# Kill any existing proxy on this port
lsof -ti:${PROXY_PORT} | xargs kill -9 2>/dev/null || true
sleep 1

cloud-sql-proxy "${SOURCE_CONNECTION}" \
    --port="${PROXY_PORT}" \
    --auto-iam-authn \
    &
PROXY_PID=$!
echo "  Proxy PID: ${PROXY_PID}"

# Wait for proxy to be ready
echo "  Waiting for proxy to be ready..."
sleep 5

# Verify proxy is listening
if ! lsof -i:${PROXY_PORT} > /dev/null 2>&1; then
    echo -e "${RED}  ERROR: Cloud SQL Proxy failed to start${NC}"
    exit 1
fi
echo -e "${GREEN}  Proxy is ready${NC}"

# ---- Step 5: Run pg_dump ----
echo -e "${YELLOW}[5/5] Running pg_dump...${NC}"
echo "  This may take a while depending on database size..."
echo ""
echo -e "${YELLOW}  NOTE: You will be prompted for the '${SOURCE_USER}' password.${NC}"
echo -e "${YELLOW}  Check your .env.production or .env.vm for DATABASE_URL to find the password.${NC}"
echo ""

# Run pg_dump with custom format (supports pg_restore) AND plain SQL backup
# Custom format (for pg_restore - faster, supports parallel restore)
DUMP_FILE_CUSTOM="${DUMP_DIR}/blacklight_dump_$(date +%Y%m%d_%H%M%S).dump"

${PG_DUMP} \
    -h 127.0.0.1 \
    -p "${PROXY_PORT}" \
    -U "${SOURCE_USER}" \
    -d "${SOURCE_DB}" \
    --format=custom \
    --verbose \
    --no-owner \
    --no-privileges \
    --file="${DUMP_FILE_CUSTOM}" \
    2>&1

DUMP_EXIT=$?

# Also create a plain SQL dump for inspection
${PG_DUMP} \
    -h 127.0.0.1 \
    -p "${PROXY_PORT}" \
    -U "${SOURCE_USER}" \
    -d "${SOURCE_DB}" \
    --format=plain \
    --verbose \
    --no-owner \
    --no-privileges \
    --file="${DUMP_FILE}" \
    2>&1

# ---- Cleanup: Stop proxy ----
echo ""
echo "Stopping Cloud SQL Auth Proxy..."
kill "${PROXY_PID}" 2>/dev/null || true
wait "${PROXY_PID}" 2>/dev/null || true

if [ ${DUMP_EXIT} -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== Database dump completed successfully! ===${NC}"
    echo ""
    echo "Dump files:"
    echo "  Custom format (for pg_restore): ${DUMP_FILE_CUSTOM}"
    echo "  Plain SQL (for inspection):     ${DUMP_FILE}"
    echo ""
    ls -lh "${DUMP_FILE_CUSTOM}" "${DUMP_FILE}" 2>/dev/null
    echo ""
    echo -e "${GREEN}Next step: Run 02-setup-target-project.sh to set up the target GCP project${NC}"
else
    echo -e "${RED}=== Database dump FAILED (exit code: ${DUMP_EXIT}) ===${NC}"
    exit 1
fi
