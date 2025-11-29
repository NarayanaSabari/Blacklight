#!/bin/bash

# =============================================================================
# Blacklight Deployment Script
# =============================================================================
# This script deploys the Blacklight application using Docker Compose
# Run with: bash deploy.sh
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Blacklight Deployment Script${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# =============================================================================
# 1. Prerequisites Check
# =============================================================================
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please run setup-vm.sh first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please run setup-vm.sh first.${NC}"
    exit 1
fi

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${RED}❌ .env.production file not found.${NC}"
    echo -e "${YELLOW}Please copy .env.production.example to .env.production and configure it:${NC}"
    echo -e "  cp .env.production.example .env.production"
    echo -e "  vim .env.production"
    exit 1
fi

# Check if GCS credentials exist
if [ ! -f server/gcs-credentials.json ]; then
    echo -e "${YELLOW}⚠️  Warning: server/gcs-credentials.json not found.${NC}"
    echo -e "${YELLOW}File uploads to Google Cloud Storage will not work.${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if SSL certificates exist
if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
    echo -e "${YELLOW}⚠️  Warning: SSL certificates not found in nginx/ssl/${NC}"
    echo -e "${YELLOW}HTTPS will not work. Run setup-vm.sh to generate self-signed certificates.${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# =============================================================================
# 2. Load Environment Variables
# =============================================================================
echo -e "${YELLOW}🔧 Loading environment variables...${NC}"
source .env.production
export $(grep -v '^#' .env.production | xargs)
echo -e "${GREEN}✅ Environment loaded${NC}"
echo ""

# =============================================================================
# 3. Validate Configuration
# =============================================================================
echo -e "${YELLOW}🔍 Validating configuration...${NC}"

VALIDATION_FAILED=0

# Check critical variables
if [ "$SECRET_KEY" == "CHANGE_ME_TO_STRONG_RANDOM_SECRET_KEY" ]; then
    echo -e "${RED}❌ SECRET_KEY not set in .env.production${NC}"
    VALIDATION_FAILED=1
fi

if [ "$POSTGRES_PASSWORD" == "CHANGE_ME_TO_STRONG_PASSWORD" ]; then
    echo -e "${RED}❌ POSTGRES_PASSWORD not set in .env.production${NC}"
    VALIDATION_FAILED=1
fi

if [[ "$GEMINI_API_KEY" == *"YOUR_"* ]] || [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  GEMINI_API_KEY not configured - AI features will not work${NC}"
fi

if [[ "$GCS_BUCKET_NAME" == *"your-"* ]] || [ -z "$GCS_BUCKET_NAME" ]; then
    echo -e "${YELLOW}⚠️  GCS_BUCKET_NAME not configured - file uploads will not work${NC}"
fi

if [ $VALIDATION_FAILED -eq 1 ]; then
    echo -e "${RED}❌ Configuration validation failed. Please update .env.production${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration validated${NC}"
echo ""

# =============================================================================
# 4. Validate Docker Compose File
# =============================================================================
echo -e "${YELLOW}🐳 Validating docker-compose.production.yml...${NC}"
docker compose -f docker-compose.production.yml config > /dev/null
echo -e "${GREEN}✅ Docker Compose file is valid${NC}"
echo ""

# =============================================================================
# 5. Pull/Build Images
# =============================================================================
echo -e "${YELLOW}🏗️  Building Docker images...${NC}"
echo -e "${BLUE}This may take 10-15 minutes on first deployment...${NC}"
docker compose -f docker-compose.production.yml build --no-cache
echo -e "${GREEN}✅ Images built successfully${NC}"
echo ""

# =============================================================================
# 6. Stop Existing Containers
# =============================================================================
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker compose -f docker-compose.production.yml down || true
echo -e "${GREEN}✅ Existing containers stopped${NC}"
echo ""

# =============================================================================
# 7. Start Database First
# =============================================================================
echo -e "${YELLOW}💾 Starting database...${NC}"
docker compose -f docker-compose.production.yml up -d postgres redis
echo -e "${BLUE}Waiting for database to be healthy...${NC}"
sleep 10

# Wait for PostgreSQL to be ready
MAX_RETRIES=30
RETRY_COUNT=0
while ! docker compose -f docker-compose.production.yml exec -T postgres pg_isready -U postgres -d blacklight > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}❌ Database failed to start after $MAX_RETRIES attempts${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Waiting for database... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

echo -e "${GREEN}✅ Database is ready${NC}"
echo ""

# =============================================================================
# 8. Run Database Migrations
# =============================================================================
echo -e "${YELLOW}🔄 Running database migrations...${NC}"

# Start backend temporarily for migrations
docker compose -f docker-compose.production.yml up -d backend
sleep 5

# Run migrations
docker compose -f docker-compose.production.yml exec -T backend python manage.py migrate || {
    echo -e "${RED}❌ Database migration failed${NC}"
    echo -e "${YELLOW}Attempting to initialize database...${NC}"
    docker compose -f docker-compose.production.yml exec -T backend python manage.py init
}

# Optional: Seed database (comment out if not needed)
# docker compose -f docker-compose.production.yml exec -T backend python manage.py seed

echo -e "${GREEN}✅ Database migrations completed${NC}"
echo ""

# =============================================================================
# 9. Start All Services
# =============================================================================
echo -e "${YELLOW}🚀 Starting all services...${NC}"
docker compose -f docker-compose.production.yml up -d
echo -e "${GREEN}✅ All services started${NC}"
echo ""

# =============================================================================
# 10. Health Checks
# =============================================================================
echo -e "${YELLOW}🏥 Performing health checks...${NC}"
sleep 10

# Check backend health
echo -n "Checking backend... "
if docker compose -f docker-compose.production.yml exec -T backend curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Check portal frontend
echo -n "Checking portal... "
if docker compose -f docker-compose.production.yml exec -T portal curl -sf http://localhost:8080/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Check centrald frontend
echo -n "Checking centrald... "
if docker compose -f docker-compose.production.yml exec -T centrald curl -sf http://localhost:8080/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Check nginx
echo -n "Checking nginx... "
if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

echo ""

# =============================================================================
# 11. Display Status
# =============================================================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${YELLOW}📊 Container Status:${NC}"
docker compose -f docker-compose.production.yml ps
echo ""

echo -e "${YELLOW}🌐 Access URLs:${NC}"
echo -e "  Portal:    ${GREEN}http://localhost/portal${NC} or ${GREEN}https://localhost/portal${NC}"
echo -e "  CentralD:  ${GREEN}http://localhost/centrald${NC} or ${GREEN}https://localhost/centrald${NC}"
echo -e "  API:       ${GREEN}http://localhost/api${NC} or ${GREEN}https://localhost/api${NC}"
echo -e "  Health:    ${GREEN}http://localhost/health${NC}"
echo ""

echo -e "${YELLOW}🔧 Management Tools (optional):${NC}"
echo -e "  pgAdmin:   ${BLUE}http://localhost:5050${NC} (start with: docker compose -f docker-compose.production.yml --profile tools up -d)"
echo -e "  Redis UI:  ${BLUE}http://localhost:8081${NC}"
echo ""

echo -e "${YELLOW}📝 Useful Commands:${NC}"
echo -e "  View logs:        ${BLUE}docker compose -f docker-compose.production.yml logs -f${NC}"
echo -e "  View backend logs:${BLUE}docker compose -f docker-compose.production.yml logs -f backend${NC}"
echo -e "  Stop services:    ${BLUE}docker compose -f docker-compose.production.yml down${NC}"
echo -e "  Restart services: ${BLUE}docker compose -f docker-compose.production.yml restart${NC}"
echo -e "  Run backup:       ${BLUE}bash backup.sh${NC}"
echo ""

echo -e "${YELLOW}🔒 Security Reminder:${NC}"
echo -e "  - Update ALLOWED_HOSTS and CORS_ORIGINS in .env.production for your domain"
echo -e "  - Replace self-signed SSL certificate with Let's Encrypt"
echo -e "  - Regularly backup your database using backup.sh"
echo ""
