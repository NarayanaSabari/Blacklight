#!/bin/bash

# Blacklight Local Development Runner
# This script starts only DB/Redis in Docker and runs Flask natively

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Blacklight Local Development Setup${NC}\n"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo -e "${YELLOW}💡 Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    echo -e "${YELLOW}   Or via Homebrew: brew install uv${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Check if virtual environment exists, if not create it with uv
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment with uv (Python 3.11)...${NC}"
    uv venv .venv --python 3.11
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Install/update dependencies with uv (much faster than pip)
echo -e "${BLUE}📚 Installing dependencies with uv (resolving all transitive dependencies)...${NC}"
# Use --resolution highest to ensure all transitive dependencies are resolved
uv pip install --resolution highest -r requirements-dev.txt

# Start Docker services (PostgreSQL and Redis only - Inngest runs separately)
echo -e "\n${BLUE}🐳 Starting PostgreSQL and Redis...${NC}"
docker-compose -f docker-compose.local.yml up -d postgres redis

# Wait for services to be healthy
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 3

# Check each service individually
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Check PostgreSQL
    PG_STATUS=$(docker inspect blacklight-postgres-local --format='{{.State.Health.Status}}' 2>/dev/null || echo "not_found")
    
    # Check Redis
    REDIS_STATUS=$(docker inspect blacklight-redis-local --format='{{.State.Health.Status}}' 2>/dev/null || echo "not_found")
    
    if [ "$PG_STATUS" = "healthy" ] && [ "$REDIS_STATUS" = "healthy" ]; then
        echo -e "${GREEN}✅ PostgreSQL and Redis are healthy!${NC}"
        echo -e "   • PostgreSQL: ${GREEN}healthy${NC}"
        echo -e "   • Redis:      ${GREEN}healthy${NC}\n"
        break
    else
        echo -e "${YELLOW}   PostgreSQL: $PG_STATUS | Redis: $REDIS_STATUS${NC}"
        RETRY_COUNT=$((RETRY_COUNT + 1))
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Services failed to become healthy after $MAX_RETRIES attempts${NC}"
    echo -e "${YELLOW}💡 Run 'docker-compose -f docker-compose.local.yml logs' to check logs${NC}"
    exit 1
fi

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env created. Please review and update if needed.${NC}\n"
fi

# Initialize database if needed
echo -e "${BLUE}💾 Checking database...${NC}"
if python manage.py init 2>/dev/null; then
    echo -e "${GREEN}✅ Database initialized${NC}"
    
    # Seed data
    read -p "$(echo -e ${YELLOW}Do you want to seed the database with sample data? [y/N]:${NC} )" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python manage.py seed
        echo -e "${GREEN}✅ Database seeded${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Database already exists${NC}"
fi

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Setup Complete! Starting Flask development server...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "${BLUE}📊 Service URLs:${NC}"
echo -e "   • Flask API:          ${GREEN}http://localhost:5000${NC}"
echo -e "   • API Health:         ${GREEN}http://localhost:5000/api/health${NC}"
echo -e "   • pgAdmin (optional): ${GREEN}http://localhost:5050${NC}"
echo -e "   • Redis Commander:    ${GREEN}http://localhost:8081${NC}\n"

echo -e "${YELLOW}💡 Next Steps:${NC}"
echo -e "   ${YELLOW}1. Start Inngest in a separate terminal:${NC}"
echo -e "      ${BLUE}npx inngest-cli@latest dev${NC}"
echo -e "   ${YELLOW}2. Inngest Dashboard will be at: ${GREEN}http://localhost:8288${NC}\n"

echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "   • Press Ctrl+C to stop the Flask server"
echo -e "   • Run './stop-local.sh' to stop Docker services"
echo -e "   • Run 'docker-compose -f docker-compose.local.yml --profile tools up -d' for pgAdmin/Redis Commander\n"

# Run Flask development server
export FLASK_APP=wsgi.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Run the server
flask run --host=0.0.0.0 --port=5000
