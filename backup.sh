#!/bin/bash

# =============================================================================
# Blacklight Backup Script
# =============================================================================
# This script creates backups of PostgreSQL database and uploads to GCS
# Run with: bash backup.sh
# Can be scheduled with cron: 0 2 * * * /path/to/backup.sh
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="/backups/blacklight"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="blacklight_backup_${TIMESTAMP}"
RETENTION_DAYS=30

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Blacklight Backup Script${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# =============================================================================
# Load Environment Variables
# =============================================================================
if [ -f .env.production ]; then
    source .env.production
    export $(grep -v '^#' .env.production | xargs)
else
    echo -e "${RED}❌ .env.production not found${NC}"
    exit 1
fi

# =============================================================================
# Create Backup Directory
# =============================================================================
mkdir -p $BACKUP_DIR
echo -e "${YELLOW}📁 Backup directory: $BACKUP_DIR${NC}"
echo ""

# =============================================================================
# Backup PostgreSQL Database
# =============================================================================
echo -e "${YELLOW}💾 Creating PostgreSQL backup...${NC}"

POSTGRES_BACKUP="$BACKUP_DIR/${BACKUP_NAME}.sql"
POSTGRES_BACKUP_COMPRESSED="$BACKUP_DIR/${BACKUP_NAME}.sql.gz"

# Create backup using pg_dump
docker compose -f docker-compose.production.yml exec -T postgres \
    pg_dump -U postgres -d blacklight --no-owner --no-acl > "$POSTGRES_BACKUP"

# Compress backup
gzip "$POSTGRES_BACKUP"

# Check if backup was created
if [ -f "$POSTGRES_BACKUP_COMPRESSED" ]; then
    BACKUP_SIZE=$(du -h "$POSTGRES_BACKUP_COMPRESSED" | cut -f1)
    echo -e "${GREEN}✅ Database backup created: ${BACKUP_NAME}.sql.gz ($BACKUP_SIZE)${NC}"
else
    echo -e "${RED}❌ Failed to create database backup${NC}"
    exit 1
fi

echo ""

# =============================================================================
# Backup Uploaded Files (if using local storage)
# =============================================================================
echo -e "${YELLOW}📦 Backing up uploaded files...${NC}"

UPLOADS_BACKUP="$BACKUP_DIR/${BACKUP_NAME}_uploads.tar.gz"

# Check if uploads directory exists in Docker volume
if docker compose -f docker-compose.production.yml exec -T backend test -d /app/uploads; then
    # Create tarball of uploads
    docker compose -f docker-compose.production.yml exec -T backend \
        tar czf - /app/uploads /app/storage 2>/dev/null > "$UPLOADS_BACKUP"
    
    if [ -f "$UPLOADS_BACKUP" ]; then
        UPLOADS_SIZE=$(du -h "$UPLOADS_BACKUP" | cut -f1)
        echo -e "${GREEN}✅ Uploads backup created: ${BACKUP_NAME}_uploads.tar.gz ($UPLOADS_SIZE)${NC}"
    else
        echo -e "${YELLOW}⚠️  No uploads to backup${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Using GCS for file storage, skipping uploads backup${NC}"
fi

echo ""

# =============================================================================
# Upload to Google Cloud Storage (Optional)
# =============================================================================
if [ ! -z "$GCS_BUCKET_NAME" ] && [ -f "server/gcs-credentials.json" ]; then
    echo -e "${YELLOW}☁️  Uploading to Google Cloud Storage...${NC}"
    
    # Check if gsutil is installed
    if command -v gsutil &> /dev/null; then
        # Upload database backup
        gsutil -q cp "$POSTGRES_BACKUP_COMPRESSED" "gs://$GCS_BUCKET_NAME/backups/database/"
        echo -e "${GREEN}✅ Database backup uploaded to GCS${NC}"
        
        # Upload files backup if exists
        if [ -f "$UPLOADS_BACKUP" ]; then
            gsutil -q cp "$UPLOADS_BACKUP" "gs://$GCS_BUCKET_NAME/backups/uploads/"
            echo -e "${GREEN}✅ Uploads backup uploaded to GCS${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  gsutil not installed. Skipping GCS upload.${NC}"
        echo -e "${YELLOW}Install with: curl https://sdk.cloud.google.com | bash${NC}"
    fi
    echo ""
fi

# =============================================================================
# Cleanup Old Backups
# =============================================================================
echo -e "${YELLOW}🧹 Cleaning up old backups (older than $RETENTION_DAYS days)...${NC}"

# Delete local backups older than retention period
find $BACKUP_DIR -name "blacklight_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "blacklight_backup_*_uploads.tar.gz" -mtime +$RETENTION_DAYS -delete

REMAINING_BACKUPS=$(ls -1 $BACKUP_DIR/blacklight_backup_*.sql.gz 2>/dev/null | wc -l)
echo -e "${GREEN}✅ Cleanup complete. ${REMAINING_BACKUPS} backups remaining${NC}"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Backup Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${YELLOW}📊 Backup Summary:${NC}"
echo -e "  Database:  $POSTGRES_BACKUP_COMPRESSED"
if [ -f "$UPLOADS_BACKUP" ]; then
    echo -e "  Uploads:   $UPLOADS_BACKUP"
fi
echo ""

echo -e "${YELLOW}📝 Restore Instructions:${NC}"
echo -e "  1. Stop the application:"
echo -e "     ${BLUE}docker compose -f docker-compose.production.yml down${NC}"
echo ""
echo -e "  2. Start database only:"
echo -e "     ${BLUE}docker compose -f docker-compose.production.yml up -d postgres${NC}"
echo ""
echo -e "  3. Restore database:"
echo -e "     ${BLUE}gunzip -c $POSTGRES_BACKUP_COMPRESSED | \\${NC}"
echo -e "     ${BLUE}docker compose -f docker-compose.production.yml exec -T postgres \\${NC}"
echo -e "     ${BLUE}psql -U postgres -d blacklight${NC}"
echo ""
echo -e "  4. Restore uploads (if backed up):"
echo -e "     ${BLUE}docker compose -f docker-compose.production.yml exec -T backend \\${NC}"
echo -e "     ${BLUE}tar xzf - < $UPLOADS_BACKUP${NC}"
echo ""
echo -e "  5. Restart application:"
echo -e "     ${BLUE}docker compose -f docker-compose.production.yml up -d${NC}"
echo ""

# =============================================================================
# Setup Cron Job Reminder
# =============================================================================
echo -e "${YELLOW}⏰ To schedule automatic backups, add to crontab:${NC}"
echo -e "   ${BLUE}crontab -e${NC}"
echo -e "   ${BLUE}# Add this line for daily backups at 2 AM:${NC}"
echo -e "   ${BLUE}0 2 * * * cd $(pwd) && bash backup.sh >> /var/log/blacklight-backup.log 2>&1${NC}"
echo ""
