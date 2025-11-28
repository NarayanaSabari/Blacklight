#!/bin/bash
# =============================================================================
# Blacklight Cloud Run Deployment Script
# =============================================================================
# This script deploys all Blacklight services to Google Cloud Run
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. Docker installed
#   3. Project ID set in GCP
#
# Usage:
#   ./deploy.sh [backend|portal|centrald|all]
#
# Examples:
#   ./deploy.sh all          # Deploy all services
#   ./deploy.sh backend      # Deploy only backend
#   ./deploy.sh portal       # Deploy only portal frontend
# =============================================================================

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-blacklight-477315}"
REGION="${GCP_REGION:-us-central1}"
REPOSITORY="gcr.io/${PROJECT_ID}"

# Service names
BACKEND_SERVICE="blacklight-api"
PORTAL_SERVICE="blacklight-portal"
CENTRALD_SERVICE="blacklight-centrald"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth print-identity-token &> /dev/null; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Configure Docker for GCR
configure_docker() {
    log_info "Configuring Docker for Google Container Registry..."
    gcloud auth configure-docker --quiet
}

# Build and deploy backend
deploy_backend() {
    log_info "Building backend Docker image..."
    
    cd server
    
    IMAGE="${REPOSITORY}/${BACKEND_SERVICE}:latest"
    
    docker build -t ${IMAGE} -f Dockerfile .
    
    log_info "Pushing image to GCR..."
    docker push ${IMAGE}
    
    log_info "Deploying to Cloud Run..."
    gcloud run deploy ${BACKEND_SERVICE} \
        --image ${IMAGE} \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --memory 1Gi \
        --cpu 1 \
        --min-instances 0 \
        --max-instances 10 \
        --timeout 300 \
        --concurrency 80 \
        --set-env-vars "ENVIRONMENT=production" \
        --set-secrets "SECRET_KEY=blacklight-secret-key:latest,DATABASE_URL=blacklight-database-url:latest,REDIS_URL=blacklight-redis-url:latest"
    
    cd ..
    
    # Get backend URL
    BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --region ${REGION} --format 'value(status.url)')
    log_info "Backend deployed at: ${BACKEND_URL}"
    
    echo ${BACKEND_URL}
}

# Build and deploy portal frontend
deploy_portal() {
    local BACKEND_URL=$1
    
    log_info "Building portal frontend Docker image..."
    
    cd ui/portal
    
    IMAGE="${REPOSITORY}/${PORTAL_SERVICE}:latest"
    
    docker build -t ${IMAGE} \
        --build-arg VITE_API_URL=${BACKEND_URL} \
        -f Dockerfile .
    
    log_info "Pushing image to GCR..."
    docker push ${IMAGE}
    
    log_info "Deploying to Cloud Run..."
    gcloud run deploy ${PORTAL_SERVICE} \
        --image ${IMAGE} \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --memory 256Mi \
        --cpu 1 \
        --min-instances 0 \
        --max-instances 5 \
        --timeout 60 \
        --concurrency 200
    
    cd ../..
    
    PORTAL_URL=$(gcloud run services describe ${PORTAL_SERVICE} --region ${REGION} --format 'value(status.url)')
    log_info "Portal deployed at: ${PORTAL_URL}"
}

# Build and deploy centralD frontend
deploy_centrald() {
    local BACKEND_URL=$1
    
    log_info "Building centralD frontend Docker image..."
    
    cd ui/centralD
    
    IMAGE="${REPOSITORY}/${CENTRALD_SERVICE}:latest"
    
    docker build -t ${IMAGE} \
        --build-arg VITE_API_URL=${BACKEND_URL} \
        -f Dockerfile .
    
    log_info "Pushing image to GCR..."
    docker push ${IMAGE}
    
    log_info "Deploying to Cloud Run..."
    gcloud run deploy ${CENTRALD_SERVICE} \
        --image ${IMAGE} \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --memory 256Mi \
        --cpu 1 \
        --min-instances 0 \
        --max-instances 3 \
        --timeout 60 \
        --concurrency 200
    
    cd ../..
    
    CENTRALD_URL=$(gcloud run services describe ${CENTRALD_SERVICE} --region ${REGION} --format 'value(status.url)')
    log_info "CentralD deployed at: ${CENTRALD_URL}"
}

# Main deployment function
deploy_all() {
    check_prerequisites
    configure_docker
    
    log_info "Starting full deployment..."
    
    # Deploy backend first to get URL
    BACKEND_URL=$(deploy_backend)
    
    # Deploy frontends with backend URL
    deploy_portal ${BACKEND_URL}
    deploy_centrald ${BACKEND_URL}
    
    log_info "============================================"
    log_info "Deployment complete!"
    log_info "============================================"
    log_info "Backend API: ${BACKEND_URL}"
    log_info "Portal: $(gcloud run services describe ${PORTAL_SERVICE} --region ${REGION} --format 'value(status.url)')"
    log_info "CentralD: $(gcloud run services describe ${CENTRALD_SERVICE} --region ${REGION} --format 'value(status.url)')"
}

# Parse command line arguments
case "${1:-all}" in
    backend)
        check_prerequisites
        configure_docker
        deploy_backend
        ;;
    portal)
        check_prerequisites
        configure_docker
        BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --region ${REGION} --format 'value(status.url)' 2>/dev/null || echo "")
        if [ -z "$BACKEND_URL" ]; then
            log_error "Backend not deployed yet. Deploy backend first or provide BACKEND_URL"
            exit 1
        fi
        deploy_portal ${BACKEND_URL}
        ;;
    centrald)
        check_prerequisites
        configure_docker
        BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --region ${REGION} --format 'value(status.url)' 2>/dev/null || echo "")
        if [ -z "$BACKEND_URL" ]; then
            log_error "Backend not deployed yet. Deploy backend first or provide BACKEND_URL"
            exit 1
        fi
        deploy_centrald ${BACKEND_URL}
        ;;
    all)
        deploy_all
        ;;
    *)
        echo "Usage: $0 [backend|portal|centrald|all]"
        exit 1
        ;;
esac
