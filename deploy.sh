#!/bin/bash
# =============================================================================
# Blacklight Production Deployment Script
# =============================================================================
# Usage: ./deploy.sh [command]
# Commands:
#   start     - Build and start all services
#   stop      - Stop all services
#   restart   - Restart all services
#   logs      - View logs
#   status    - Check service status
#   migrate   - Run database migrations
#   seed      - Seed the database
#   shell     - Open shell in backend container
#   clean     - Remove all containers and volumes (DESTRUCTIVE!)
# =============================================================================

set -e

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if docker-compose is available
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi

    # Check if .env.production exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env.production file not found!"
        log_info "Copy .env.production.example to .env.production and configure it."
        exit 1
    fi

    # Check if GCS credentials exist
    if [ ! -f "credentials/gcs-credentials.json" ]; then
        log_error "GCS credentials not found at credentials/gcs-credentials.json"
        log_info "Place your GCS service account key JSON file there."
        exit 1
    fi
}

start_services() {
    check_prerequisites
    log_info "Building and starting all services..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build
    log_info "Services started! Waiting for health checks..."
    sleep 10
    docker compose -f $COMPOSE_FILE ps
    log_info "Deployment complete!"
    log_info "Portal (HR): http://localhost:5174"
    log_info "Central (Admin): http://localhost:5173"
    log_info "Backend API: http://localhost:5000"
}

stop_services() {
    log_info "Stopping all services..."
    docker compose -f $COMPOSE_FILE down
    log_info "Services stopped."
}

restart_services() {
    log_info "Restarting all services..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE restart
    log_info "Services restarted."
}

show_logs() {
    SERVICE=${2:-""}
    if [ -n "$SERVICE" ]; then
        docker compose -f $COMPOSE_FILE logs -f $SERVICE
    else
        docker compose -f $COMPOSE_FILE logs -f
    fi
}

show_status() {
    docker compose -f $COMPOSE_FILE ps
}

run_migrations() {
    check_prerequisites
    log_info "Running database migrations..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec backend python manage.py migrate
    log_info "Migrations complete."
}

seed_all_database() {
    check_prerequisites
    log_info "Seeding database..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec backend python manage.py seed-all
    log_info "Database seeded."
}

init_database() {
    check_prerequisites
    log_info "Initializing database (creating tables)..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec backend python manage.py init
    log_info "Database initialized."
}

open_shell() {
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec backend /bin/bash
}

clean_all() {
    log_warn "This will remove ALL containers, volumes, and data!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        log_info "Cleaning up..."
        docker compose -f $COMPOSE_FILE down -v --remove-orphans
        log_info "Cleanup complete."
    else
        log_info "Cleanup cancelled."
    fi
}

rebuild_frontend() {
    SERVICE=${2:-""}
    if [ "$SERVICE" = "portal" ]; then
        log_info "Rebuilding portal frontend..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build portal
    elif [ "$SERVICE" = "central" ]; then
        log_info "Rebuilding central frontend..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build central
    else
        log_info "Rebuilding both frontends..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build portal central
    fi
    log_info "Frontend rebuild complete."
}

rebuild_backend() {
    check_prerequisites
    log_info "Rebuilding backend..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build backend
    log_info "Backend rebuild complete."
}

rebuild_all() {
    check_prerequisites
    log_info "Rebuilding all services..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build
    log_info "All services rebuilt."
}

# Main command handler
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
        show_logs "$@"
        ;;
    status)
        show_status
        ;;
    migrate)
        run_migrations
        ;;
    seed)
        seed_database
        ;;
    init)
        init_database
        ;;
    shell)
        open_shell
        ;;
    clean)
        clean_all
        ;;
    rebuild-frontend)
        rebuild_frontend "$@"
        ;;
    rebuild-backend)
        rebuild_backend
        ;;
    rebuild)
        rebuild_all
        ;;
    *)
        echo "Blacklight Production Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start              Build and start all services"
        echo "  stop               Stop all services"
        echo "  restart            Restart all services"
        echo "  logs [service]     View logs (optionally for specific service)"
        echo "  status             Check service status"
        echo "  init               Initialize database (create tables)"
        echo "  migrate            Run database migrations"
        echo "  seed               Seed the database"
        echo "  shell              Open shell in backend container"
        echo "  rebuild-frontend   Rebuild frontend containers (portal/central)"
        echo "  rebuild-backend    Rebuild backend container"
        echo "  rebuild            Rebuild all containers"
        echo "  clean              Remove all containers and volumes (DESTRUCTIVE!)"
        echo ""
        echo "Services: db, redis, backend, portal, central"
        ;;
esac
