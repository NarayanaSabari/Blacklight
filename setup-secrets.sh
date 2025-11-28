#!/bin/bash
# =============================================================================
# Blacklight - Create Secrets in Google Secret Manager
# =============================================================================
# Run this script ONCE to set up all secrets before deployment
#
# Usage:
#   chmod +x setup-secrets.sh
#   ./setup-secrets.sh
# =============================================================================

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-blacklight-477315}"
REGION="${GCP_REGION:-us-central1}"

echo "Setting up secrets for project: $PROJECT_ID"
echo "=============================================="

# Function to create or update a secret
create_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3
    
    # Check if secret exists
    if gcloud secrets describe $secret_name --project=$PROJECT_ID &>/dev/null; then
        echo "Updating existing secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=- --project=$PROJECT_ID
    else
        echo "Creating new secret: $secret_name"
        gcloud secrets create $secret_name \
            --replication-policy="automatic" \
            --project=$PROJECT_ID \
            --labels="app=blacklight,env=production"
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=- --project=$PROJECT_ID
    fi
}

# Function to create secret from file
create_secret_from_file() {
    local secret_name=$1
    local file_path=$2
    
    if gcloud secrets describe $secret_name --project=$PROJECT_ID &>/dev/null; then
        echo "Updating existing secret: $secret_name"
        gcloud secrets versions add $secret_name --data-file="$file_path" --project=$PROJECT_ID
    else
        echo "Creating new secret: $secret_name"
        gcloud secrets create $secret_name \
            --replication-policy="automatic" \
            --project=$PROJECT_ID \
            --labels="app=blacklight,env=production"
        gcloud secrets versions add $secret_name --data-file="$file_path" --project=$PROJECT_ID
    fi
}

echo ""
echo "=== Creating secrets ==="
echo ""

# Prompt for values (or use defaults)
read -p "Enter SECRET_KEY (or press Enter to generate): " SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    echo "Generated SECRET_KEY: $SECRET_KEY"
fi

read -p "Enter DATABASE_URL: " DATABASE_URL
read -p "Enter REDIS_URL: " REDIS_URL
read -p "Enter GEMINI_API_KEY: " GEMINI_API_KEY
read -p "Enter SMTP_PASSWORD: " SMTP_PASSWORD
read -p "Enter INNGEST_EVENT_KEY: " INNGEST_EVENT_KEY
read -p "Enter INNGEST_SIGNING_KEY: " INNGEST_SIGNING_KEY
read -p "Enter path to GCS credentials JSON file: " GCS_CREDS_PATH

# Create secrets
create_secret "blacklight-secret-key" "$SECRET_KEY" "Flask secret key"
create_secret "blacklight-database-url" "$DATABASE_URL" "PostgreSQL connection string"
create_secret "blacklight-redis-url" "$REDIS_URL" "Redis connection string"
create_secret "blacklight-gemini-api-key" "$GEMINI_API_KEY" "Google Gemini API key"
create_secret "blacklight-smtp-password" "$SMTP_PASSWORD" "SMTP password for emails"
create_secret "blacklight-inngest-event-key" "$INNGEST_EVENT_KEY" "Inngest event key"
create_secret "blacklight-inngest-signing-key" "$INNGEST_SIGNING_KEY" "Inngest signing key"

if [ -f "$GCS_CREDS_PATH" ]; then
    create_secret_from_file "blacklight-gcs-credentials" "$GCS_CREDS_PATH"
else
    echo "WARNING: GCS credentials file not found at $GCS_CREDS_PATH"
fi

echo ""
echo "=== Secrets created successfully ==="
echo ""
echo "List all secrets:"
gcloud secrets list --project=$PROJECT_ID --filter="labels.app=blacklight"
