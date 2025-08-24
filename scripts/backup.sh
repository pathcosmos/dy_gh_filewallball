#!/bin/bash

# FileWallBall Backup Script
# This script creates backups of the database and file storage

set -e

# Configuration
BACKUP_DIR="/host-backups"
DB_BACKUP_DIR="/backup/db"
UPLOADS_BACKUP_DIR="/backup/uploads"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Create backup directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/uploads"

log "Starting FileWallBall backup process..."

# Database backup
log "Creating database backup..."
if mysqldump -h mariadb -u root -p"$DB_ROOT_PASSWORD" --all-databases > "$DB_BACKUP_DIR/full_backup_$TIMESTAMP.sql"; then
    log "Database backup completed successfully"
    # Copy to host
    cp "$DB_BACKUP_DIR/full_backup_$TIMESTAMP.sql" "$BACKUP_DIR/database/"
else
    error "Database backup failed"
    exit 1
fi

# File storage backup
log "Creating file storage backup..."
if tar -czf "$UPLOADS_BACKUP_DIR/uploads_backup_$TIMESTAMP.tar.gz" -C /app/uploads .; then
    log "File storage backup completed successfully"
    # Copy to host
    cp "$UPLOADS_BACKUP_DIR/uploads_backup_$TIMESTAMP.tar.gz" "$BACKUP_DIR/uploads/"
else
    error "File storage backup failed"
    exit 1
fi

# Cleanup old backups
log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR/database" -name "*.sql" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR/uploads" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Create backup manifest
cat > "$BACKUP_DIR/backup_manifest_$TIMESTAMP.txt" << EOF
FileWallBall Backup Manifest
============================
Backup Date: $(date)
Retention Days: $RETENTION_DAYS

Database Backup:
- File: full_backup_$TIMESTAMP.sql
- Size: $(du -h "$BACKUP_DIR/database/full_backup_$TIMESTAMP.sql" | cut -f1)

File Storage Backup:
- File: uploads_backup_$TIMESTAMP.tar.gz
- Size: $(du -h "$BACKUP_DIR/uploads/uploads_backup_$TIMESTAMP.tar.gz" | cut -f1)

Backup Location: $BACKUP_DIR
EOF

log "Backup process completed successfully!"
log "Backup location: $BACKUP_DIR"
log "Manifest file: backup_manifest_$TIMESTAMP.txt"
