#!/bin/bash
# =============================================================================
# STEP 3: Restore database dump to target Cloud SQL instance
# =============================================================================
# Prerequisites:
#   - Step 01 completed (dump file exists)
#   - Step 02 completed (target Cloud SQL instance exists)
#   - gcloud CLI authenticated to the NEW GCP account/project
#   - cloud-sql-proxy installed
#   - PostgreSQL 17 client tools installed
#
# Usage: ./03-restore-target-db.sh <NEW_PROJECT_ID> <DUMP_FILE>
# Example: ./03-restore-target-db.sh blacklight-new-123 dumps/blacklight_dump_20260220.dump
# =============================================================================

set -euo pipefail

# ---- Configuration ----
NEW_PROJECT_ID="${1:?Usage: $0 <NEW_PROJECT_ID> <DUMP_FILE>}"
DUMP_FILE="${2:?Usage: $0 <NEW_PROJECT_ID> <DUMP_FILE>}"
REGION="asia-south1"
SQL_INSTANCE_NAME="bl-db"
TARGET_DB="postgres"
TARGET_USER="postgres"
PROXY_PORT=5433  # Different port to avoid conflicts
PG_RESTORE="/opt/homebrew/opt/postgresql@17/bin/pg_restore"
PSQL="/opt/homebrew/opt/postgresql@17/bin/psql"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Blacklight Database Restore (Target Project) ===${NC}"
echo ""
echo "Target Project:    ${NEW_PROJECT_ID}"
echo "Target Instance:   ${SQL_INSTANCE_NAME}"
echo "Target Database:   ${TARGET_DB}"
echo "Dump File:         ${DUMP_FILE}"
echo ""

# ---- Verify dump file exists ----
if [ ! -f "${DUMP_FILE}" ]; then
    echo -e "${RED}ERROR: Dump file not found: ${DUMP_FILE}${NC}"
    echo "Run 01-dump-source-db.sh first to create the dump."
    exit 1
fi

echo "Dump file size: $(ls -lh "${DUMP_FILE}" | awk '{print $5}')"
echo ""

# ---- Step 1: Set project ----
echo -e "${YELLOW}[1/6] Setting active project to ${NEW_PROJECT_ID}...${NC}"
gcloud config set project "${NEW_PROJECT_ID}"

# ---- Step 2: Get connection name ----
echo -e "${YELLOW}[2/6] Getting Cloud SQL connection name...${NC}"
TARGET_CONNECTION=$(gcloud sql instances describe "${SQL_INSTANCE_NAME}" \
    --project="${NEW_PROJECT_ID}" \
    --format="value(connectionName)" 2>&1)
echo "  Connection: ${TARGET_CONNECTION}"

# ---- Step 3: Start Cloud SQL Auth Proxy ----
echo -e "${YELLOW}[3/6] Starting Cloud SQL Auth Proxy on port ${PROXY_PORT}...${NC}"

# Kill any existing proxy on this port
lsof -ti:${PROXY_PORT} | xargs kill -9 2>/dev/null || true
sleep 1

cloud-sql-proxy "${TARGET_CONNECTION}" \
    --port="${PROXY_PORT}" \
    &
PROXY_PID=$!
echo "  Proxy PID: ${PROXY_PID}"

# Wait for proxy
echo "  Waiting for proxy to be ready..."
sleep 5

if ! lsof -i:${PROXY_PORT} > /dev/null 2>&1; then
    echo -e "${RED}  ERROR: Cloud SQL Proxy failed to start${NC}"
    exit 1
fi
echo -e "${GREEN}  Proxy is ready${NC}"

# ---- Step 4: Enable pgvector extension ----
echo -e "${YELLOW}[4/6] Enabling pgvector extension...${NC}"
echo "  You will be prompted for the postgres password."

${PSQL} \
    -h 127.0.0.1 \
    -p "${PROXY_PORT}" \
    -U "${TARGET_USER}" \
    -d "${TARGET_DB}" \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" \
    2>&1 || echo -e "${RED}  WARNING: Could not enable pgvector. You may need to enable it manually.${NC}"

echo -e "${GREEN}  pgvector extension enabled${NC}"

# ---- Step 5: Restore database ----
echo -e "${YELLOW}[5/6] Restoring database from dump...${NC}"
echo -e "${YELLOW}  NOTE: You will be prompted for the '${TARGET_USER}' password.${NC}"
echo ""

# Determine format based on file extension
if [[ "${DUMP_FILE}" == *.dump ]]; then
    echo "  Using pg_restore (custom format)..."
    ${PG_RESTORE} \
        -h 127.0.0.1 \
        -p "${PROXY_PORT}" \
        -U "${TARGET_USER}" \
        -d "${TARGET_DB}" \
        --verbose \
        --no-owner \
        --no-privileges \
        --single-transaction \
        "${DUMP_FILE}" \
        2>&1
    RESTORE_EXIT=$?
elif [[ "${DUMP_FILE}" == *.sql ]]; then
    echo "  Using psql (plain SQL format)..."
    ${PSQL} \
        -h 127.0.0.1 \
        -p "${PROXY_PORT}" \
        -U "${TARGET_USER}" \
        -d "${TARGET_DB}" \
        -f "${DUMP_FILE}" \
        2>&1
    RESTORE_EXIT=$?
else
    echo -e "${RED}  ERROR: Unknown dump file format. Expected .dump or .sql${NC}"
    kill "${PROXY_PID}" 2>/dev/null || true
    exit 1
fi

# ---- Step 6: Verify restore ----
echo -e "${YELLOW}[6/6] Verifying restore...${NC}"

echo ""
echo "--- Table row counts ---"
${PSQL} \
    -h 127.0.0.1 \
    -p "${PROXY_PORT}" \
    -U "${TARGET_USER}" \
    -d "${TARGET_DB}" \
    -c "
SELECT schemaname, relname AS table_name, n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
" 2>&1

echo ""
echo "--- Installed extensions ---"
${PSQL} \
    -h 127.0.0.1 \
    -p "${PROXY_PORT}" \
    -U "${TARGET_USER}" \
    -d "${TARGET_DB}" \
    -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;" 2>&1

echo ""
echo "--- Check pgvector columns ---"
${PSQL} \
    -h 127.0.0.1 \
    -p "${PROXY_PORT}" \
    -U "${TARGET_USER}" \
    -d "${TARGET_DB}" \
    -c "
SELECT table_name, column_name, udt_name
FROM information_schema.columns
WHERE udt_name = 'vector'
ORDER BY table_name;
" 2>&1

# ---- Cleanup ----
echo ""
echo "Stopping Cloud SQL Auth Proxy..."
kill "${PROXY_PID}" 2>/dev/null || true
wait "${PROXY_PID}" 2>/dev/null || true

if [ ${RESTORE_EXIT} -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== Database restore completed successfully! ===${NC}"
    echo ""
    echo -e "${GREEN}Next step: Run 04-migrate-gcs-files.sh to copy GCS files${NC}"
else
    echo ""
    echo -e "${RED}=== Database restore completed with warnings (exit code: ${RESTORE_EXIT}) ===${NC}"
    echo "  pg_restore may return non-zero for warnings that are safe to ignore."
    echo "  Check the output above for actual errors."
fi
