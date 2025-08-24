#!/bin/bash

# FileWallBall Volume Backup Script
# This script creates backups of all Docker volumes

set -e

# Configuration
BACKUP_DIR="./backups/volumes"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

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

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "Starting FileWallBall volume backup process..."

# Get list of project volumes
VOLUMES=$(docker volume ls --filter "label=com.docker.compose.project=dy_gh_filewallball" --format "{{.Name}}")

if [ -z "$VOLUMES" ]; then
    error "No volumes found for project dy_gh_filewallball"
    exit 1
fi

# Backup each volume
for VOLUME in $VOLUMES; do
    log "Backing up volume: $VOLUME"
    
    # Create volume backup directory
    VOLUME_BACKUP_DIR="$BACKUP_DIR/$VOLUME"
    mkdir -p "$VOLUME_BACKUP_DIR"
    
    # Create backup using docker run with volume mount
    if docker run --rm \
        -v "$VOLUME:/source:ro" \
        -v "$(pwd)/$VOLUME_BACKUP_DIR:/backup" \
        alpine:latest \
        tar -czf "/backup/${VOLUME}_${TIMESTAMP}.tar.gz" -C /source .; then
        
        log "Volume $VOLUME backed up successfully"
        
        # Get backup file size
        BACKUP_FILE="${VOLUME_BACKUP_DIR}/${VOLUME}_${TIMESTAMP}.tar.gz"
        if [ -f "$BACKUP_FILE" ]; then
            BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log "Backup size: $BACKUP_SIZE"
        fi
    else
        error "Failed to backup volume $VOLUME"
        exit 1
    fi
done

# Cleanup old backups
log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Create backup manifest
cat > "$BACKUP_DIR/volume_backup_manifest_$TIMESTAMP.txt" << EOF
FileWallBall Volume Backup Manifest
==================================
Backup Date: $(date)
Retention Days: $RETENTION_DAYS

Volumes Backed Up:
$(echo "$VOLUMES" | while read -r vol; do
    echo "- $vol"
done)

Backup Location: $BACKUP_DIR
Total Volumes: $(echo "$VOLUMES" | wc -l)

Backup Files:
$(find "$BACKUP_DIR" -name "*_${TIMESTAMP}.tar.gz" -exec basename {} \; | sort)
EOF

log "Volume backup process completed successfully!"
log "Backup location: $BACKUP_DIR"
log "Manifest file: volume_backup_manifest_$TIMESTAMP.txt"
log "Total volumes backed up: $(echo "$VOLUMES" | wc -l)"
