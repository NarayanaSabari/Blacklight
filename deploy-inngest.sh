#!/bin/bash
# =============================================================================
# Inngest Server Deployment Script (VM only)
# =============================================================================
# Usage: ./deploy-inngest.sh [command]
# Commands:
#   start       - Start Inngest server and dependencies
#   stop        - Stop all services
#   restart     - Restart all services
#   logs        - View Inngest logs
#   status      - Check service status
#   sync        - Trigger function sync with backend
#   clean       - Remove all containers and volumes (DESTRUCTIVE!)
# =============================================================================

set -e

COMPOSE_FILE="docker-compose.inngest.yml"
ENV_FILE=".env.inngest"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed."
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available."
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env.inngest file not found!"
        log_info "Copy .env.inngest.example to .env.inngest and configure it."
        exit 1
    fi
}

start_services() {
    check_prerequisites
    log_info "Starting Inngest server..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build
    
    log_info "Waiting for services to be healthy..."
    sleep 15
    
    docker compose -f $COMPOSE_FILE ps
    
    log_info ""
    log_info "Inngest server started!"
    log_info "Dashboard: http://$(hostname -I | awk '{print $1}'):8288"
    log_info ""
    log_info "Next: Trigger sync from backend or wait for first event"
}

stop_services() {
    log_info "Stopping Inngest server..."
    docker compose -f $COMPOSE_FILE down
    log_info "Services stopped."
}

restart_services() {
    log_info "Restarting Inngest server..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE restart
    log_info "Services restarted."
}

show_logs() {
    docker compose -f $COMPOSE_FILE logs -f inngest
}

show_status() {
    docker compose -f $COMPOSE_FILE ps
    echo ""
    log_info "Health check:"
    curl -s http://localhost:8288/health && echo " - Inngest is healthy" || echo " - Inngest is not responding"
}

sync_functions() {
    log_info "Triggering function sync..."
    
    # Read backend URL from env file
    BACKEND_URL=$(grep BACKEND_URL $ENV_FILE | cut -d '=' -f2)
    
    if [ -z "$BACKEND_URL" ]; then
        log_error "BACKEND_URL not found in $ENV_FILE"
        exit 1
    fi
    
    log_info "Syncing with backend: $BACKEND_URL"
    
    # Trigger sync by calling the backend's inngest endpoint
    curl -s -X PUT "$BACKEND_URL/api/inngest" && log_info "Sync triggered successfully" || log_error "Sync failed"
}

clean_all() {
    log_warn "This will remove ALL containers, volumes, and data!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        docker compose -f $COMPOSE_FILE down -v --remove-orphans
        log_info "Cleanup complete."
    else
        log_info "Cleanup cancelled."
    fi
}

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    sync)
        sync_functions
        ;;
    clean)
        clean_all
        ;;
    *)
        echo "Inngest Server Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start       Start Inngest server and dependencies"
        echo "  stop        Stop all services"
        echo "  restart     Restart all services"
        echo "  logs        View Inngest logs"
        echo "  status      Check service status"
        echo "  sync        Trigger function sync with backend"
        echo "  clean       Remove all containers and volumes (DESTRUCTIVE!)"
        ;;
esac
