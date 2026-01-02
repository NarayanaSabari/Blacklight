#!/bin/bash
# =============================================================================
# Blacklight Production Deployment Script
# =============================================================================
# Usage: ./deploy.sh [command]
# Commands:
#   start              - Build and start all services
#   stop               - Stop all services
#   restart            - Restart all services
#   logs [service]     - View logs (optionally for specific service)
#   status             - Check service status
#   init               - Initialize database (create tables)
#   migrate            - Run database migrations
#   seed               - Seed the database
#   shell              - Open shell in backend container
#   rebuild-frontend   - Rebuild frontend containers
#   rebuild-backend    - Rebuild backend container
#   rebuild            - Rebuild all containers
#   recreate-nginx     - Recreate nginx (reload config)
#   create-inngest-db  - Create inngest database
#   sync-inngest       - Sync Inngest functions
#   ssl-init           - Obtain SSL certificate from Let's Encrypt
#   ssl-renew          - Renew SSL certificates
#   ssl-status         - Check certificate status
#   ssl-test           - Test certificate request (dry-run)
#   clean              - Remove all containers and volumes (DESTRUCTIVE!)
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
    
    # Auto-sync Inngest functions
    log_info "Syncing Inngest functions..."
    sleep 5  # Give backend a moment to fully initialize
    sync_inngest 2>/dev/null || log_warn "Inngest sync may need manual trigger. Run './deploy.sh sync-inngest' if functions don't appear."
    
    log_info "Deployment complete!"
    log_info "Portal (HR): http://localhost:5174"
    log_info "Central (Admin): http://localhost:5173"
    log_info "Backend API: http://localhost:5000"
    log_info "Inngest Dashboard: http://localhost:8288"
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

recreate_nginx() {
    log_info "Recreating nginx container..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --force-recreate nginx
    log_info "Nginx container recreated and config reloaded."
}

# =============================================================================
# SSL Certificate Management
# =============================================================================

ssl_init() {
    DOMAIN=${2:-"blacklight.sivaganesh.in"}
    EMAIL=${3:-""}
    INCLUDE_WWW=${4:-""}
    
    log_info "Initializing SSL certificates for $DOMAIN..."
    
    # Create certbot directories if they don't exist
    mkdir -p certbot/www certbot/conf
    
    # Check if nginx is running
    if ! docker compose -f $COMPOSE_FILE ps nginx 2>/dev/null | grep -q "Up"; then
        log_error "Nginx container is not running. Start services first with './deploy.sh start'"
        exit 1
    fi
    
    # Build email argument
    EMAIL_ARG=""
    if [ -n "$EMAIL" ]; then
        EMAIL_ARG="--email $EMAIL"
    else
        EMAIL_ARG="--register-unsafely-without-email"
        log_warn "No email provided. Using --register-unsafely-without-email"
    fi
    
    # Build domain arguments
    DOMAIN_ARGS="-d $DOMAIN"
    if [ "$INCLUDE_WWW" = "--with-www" ]; then
        DOMAIN_ARGS="-d $DOMAIN -d www.$DOMAIN"
        log_info "Including www.$DOMAIN in certificate"
    fi
    
    log_info "Requesting certificate from Let's Encrypt..."
    docker compose -f $COMPOSE_FILE run --rm certbot certonly \
        --webroot \
        -w /var/www/certbot \
        $DOMAIN_ARGS \
        $EMAIL_ARG \
        --agree-tos \
        --no-eff-email \
        --force-renewal
    
    if [ $? -eq 0 ]; then
        log_info "SSL certificate obtained successfully!"
        log_info ""
        log_info "Next steps:"
        log_info "1. Edit nginx/nginx.conf and uncomment the HTTPS server block"
        log_info "2. Run: ./deploy.sh recreate-nginx"
        log_info ""
        log_info "To auto-renew certificates, add a cron job:"
        log_info "  0 0 * * 0 cd $(pwd) && ./deploy.sh ssl-renew >> /var/log/certbot-renew.log 2>&1"
    else
        log_error "Failed to obtain SSL certificate!"
        log_info "Make sure:"
        log_info "  - Your domain points to this server's IP"
        log_info "  - Port 80 is accessible from the internet"
        log_info "  - Nginx is running and serving /.well-known/acme-challenge/"
    fi
}

ssl_renew() {
    log_info "Renewing SSL certificates..."
    
    docker compose -f $COMPOSE_FILE run --rm certbot renew
    
    if [ $? -eq 0 ]; then
        log_info "Certificate renewal complete. Reloading nginx..."
        docker compose -f $COMPOSE_FILE exec nginx nginx -s reload
        log_info "Nginx reloaded with new certificates."
    else
        log_warn "Certificate renewal completed with warnings. Check output above."
    fi
}

ssl_status() {
    log_info "Checking SSL certificate status..."
    
    if [ ! -d "certbot/conf/live" ]; then
        log_warn "No certificates found. Run './deploy.sh ssl-init <domain> [email]' first."
        exit 0
    fi
    
    # List all certificates
    docker compose -f $COMPOSE_FILE run --rm certbot certificates
}

ssl_test() {
    DOMAIN=${2:-"blacklight.sivaganesh.in"}
    EMAIL=${3:-""}
    INCLUDE_WWW=${4:-""}
    
    log_info "Testing SSL certificate request (dry-run) for $DOMAIN..."
    
    # Create certbot directories if they don't exist
    mkdir -p certbot/www certbot/conf
    
    # Build email argument
    EMAIL_ARG=""
    if [ -n "$EMAIL" ]; then
        EMAIL_ARG="--email $EMAIL"
    else
        EMAIL_ARG="--register-unsafely-without-email"
    fi
    
    # Build domain arguments
    DOMAIN_ARGS="-d $DOMAIN"
    if [ "$INCLUDE_WWW" = "--with-www" ]; then
        DOMAIN_ARGS="-d $DOMAIN -d www.$DOMAIN"
        log_info "Including www.$DOMAIN in certificate"
    fi
    
    docker compose -f $COMPOSE_FILE run --rm certbot certonly \
        --webroot \
        -w /var/www/certbot \
        $DOMAIN_ARGS \
        $EMAIL_ARG \
        --agree-tos \
        --no-eff-email \
        --dry-run
    
    if [ $? -eq 0 ]; then
        log_info "Dry run successful! You can now run './deploy.sh ssl-init $DOMAIN $EMAIL' to obtain real certificates."
    else
        log_error "Dry run failed. Check the errors above."
    fi
}

create_inngest_db() {
    log_info "Creating inngest database..."
    
    # Check if db container is running (check for "Up" in status)
    if ! docker compose -f $COMPOSE_FILE ps db 2>/dev/null | grep -q "Up"; then
        log_error "Database container is not running. Start services first with './deploy.sh start'"
        exit 1
    fi
    
    # Create inngest database if it doesn't exist
    docker compose -f $COMPOSE_FILE exec -T db psql -U blacklight -d blacklight -tc "SELECT 1 FROM pg_database WHERE datname = 'inngest'" | grep -q 1 || \
        docker compose -f $COMPOSE_FILE exec -T db psql -U blacklight -d blacklight -c "CREATE DATABASE inngest;"
    
    # Grant privileges
    docker compose -f $COMPOSE_FILE exec -T db psql -U blacklight -d blacklight -c "GRANT ALL PRIVILEGES ON DATABASE inngest TO blacklight;" 2>/dev/null || true
    
    log_info "Inngest database created/verified successfully."
}

sync_inngest() {
    log_info "Syncing Inngest functions with backend..."
    
    # Check if inngest container is running
    if ! docker compose -f $COMPOSE_FILE ps inngest 2>/dev/null | grep -q "Up"; then
        log_error "Inngest container is not running. Start services first with './deploy.sh start'"
        exit 1
    fi
    
    # Check if backend container is running
    if ! docker compose -f $COMPOSE_FILE ps backend 2>/dev/null | grep -q "Up"; then
        log_error "Backend container is not running. Start services first with './deploy.sh start'"
        exit 1
    fi
    
    # Wait a moment for services to be ready
    sleep 2
    
    # Trigger sync by making a PUT request to the backend's inngest endpoint from within the network
    docker compose -f $COMPOSE_FILE exec -T backend curl -s -X PUT http://localhost:5000/api/inngest > /dev/null 2>&1 || true
    
    log_info "Inngest sync triggered. Check Inngest dashboard at http://localhost:8288 to verify functions are registered."
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
        seed_all_database
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
    create-inngest-db)
        create_inngest_db
        ;;
    sync-inngest)
        sync_inngest
        ;;
    recreate-nginx)
        recreate_nginx
        ;;
    ssl-init)
        ssl_init "$@"
        ;;
    ssl-renew)
        ssl_renew
        ;;
    ssl-status)
        ssl_status
        ;;
    ssl-test)
        ssl_test "$@"
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
        echo "  create-inngest-db  Create inngest database in PostgreSQL"
        echo "  sync-inngest       Sync Inngest functions with backend"
        echo "  recreate-nginx     Recreate nginx container (reload config)"
        echo "  clean              Remove all containers and volumes (DESTRUCTIVE!)"
        echo ""
        echo "SSL Certificate Commands:"
        echo "  ssl-init [domain] [email]   Obtain SSL certificate from Let's Encrypt"
        echo "  ssl-renew                   Renew SSL certificates"
        echo "  ssl-status                  Check certificate status"
        echo "  ssl-test [domain] [email]   Test certificate request (dry-run)"
        echo ""
        echo "Services: db, redis, backend, portal, central, nginx, inngest"
        echo ""
        echo "Examples:"
        echo "  ./deploy.sh start"
        echo "  ./deploy.sh logs backend"
        echo "  ./deploy.sh ssl-test blacklight.sivaganesh.in admin@example.com"
        echo "  ./deploy.sh ssl-init blacklight.sivaganesh.in admin@example.com"
        ;;
esac
