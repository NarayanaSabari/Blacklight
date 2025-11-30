#!/bin/bash

# =============================================================================
# Blacklight Backend Startup Script
# Exports all .env variables and starts Flask
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Blacklight Backend Startup${NC}\n"

# Change to script directory
cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found! Creating from .env.example...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env created. Please update it with your values.${NC}"
    else
        echo -e "${YELLOW}❌ .env.example not found either. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Clear Python cache to ensure fresh imports
echo -e "${BLUE}🧹 Clearing Python cache...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Export all variables from .env file
echo -e "${BLUE}📦 Loading environment variables from .env...${NC}"
set -a  # Automatically export all variables
source .env
set +a  # Stop auto-exporting

# Display key variables for verification
echo -e "\n${GREEN}✅ Environment Variables Loaded:${NC}"
echo -e "   ENVIRONMENT        = ${ENVIRONMENT:-not set}"
echo -e "   DATABASE_URL       = ${DATABASE_URL:0:50}..."
echo -e "   REDIS_URL          = ${REDIS_URL:-not set}"
echo -e "   STORAGE_BACKEND    = ${STORAGE_BACKEND:-not set}"
echo -e "   GCS_BUCKET_NAME    = ${GCS_BUCKET_NAME:-not set}"
echo -e "   GCS_CREDENTIALS_PATH = ${GCS_CREDENTIALS_PATH:-not set}"

# Verify GCS credentials file exists if using GCS
if [ "$STORAGE_BACKEND" = "gcs" ]; then
    if [ -f "$GCS_CREDENTIALS_PATH" ]; then
        echo -e "   ${GREEN}✅ GCS credentials file found${NC}"
    else
        echo -e "   ${YELLOW}⚠️  GCS credentials file NOT found at: $GCS_CREDENTIALS_PATH${NC}"
        echo -e "   ${YELLOW}   Please check the path or switch to STORAGE_BACKEND=local${NC}"
    fi
fi

echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Start Flask
echo -e "${GREEN}🌐 Starting Flask server on http://0.0.0.0:5000${NC}\n"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

exec flask run --host=0.0.0.0 --port=${PORT:-5000} --debug
