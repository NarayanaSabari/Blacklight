#!/bin/bash

# Stop local development Docker services

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Blacklight local services...${NC}\n"

# Stop Docker services
docker-compose -f docker-compose.local.yml down

echo -e "\n${GREEN}✅ All services stopped!${NC}"
echo -e "${YELLOW}💡 Data is preserved in Docker volumes${NC}"
echo -e "${YELLOW}   To remove volumes too, run: docker-compose -f docker-compose.local.yml down -v${NC}\n"
