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

# Start Docker services (PostgreSQL, Redis, and Inngest)
echo -e "\n${BLUE}🐳 Starting PostgreSQL, Redis, and Inngest Dev Server...${NC}"
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be healthy
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 3

# Check if services are healthy
until docker-compose -f docker-compose.local.yml ps | grep -q "healthy"; do
    echo -e "${YELLOW}   Still waiting for services...${NC}"
    sleep 2
done

echo -e "${GREEN}✅ PostgreSQL, Redis, and Inngest are ready!${NC}\n"

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
echo -e "   • Inngest Dashboard:  ${GREEN}http://localhost:8288${NC}"
echo -e "   • pgAdmin (optional): ${GREEN}http://localhost:5050${NC}"
echo -e "   • Redis Commander:    ${GREEN}http://localhost:8081${NC}\n"

echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "   • Press Ctrl+C to stop the Flask server"
echo -e "   • Run './stop-local.sh' to stop all Docker services"
echo -e "   • View Inngest workflows at http://localhost:8288"
echo -e "   • Run 'docker-compose -f docker-compose.local.yml --profile tools up -d' for pgAdmin/Redis Commander\n"

# Run Flask development server
export FLASK_APP=wsgi.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Run the server
flask run --host=0.0.0.0 --port=5000
