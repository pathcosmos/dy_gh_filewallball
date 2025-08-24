#!/bin/bash

# Enhanced FileWallBall Backup Script
# This script provides comprehensive backup strategy with compression, encryption, and verification

set -e

# Configuration
BACKUP_DIR="/host-backups"
DB_BACKUP_DIR="/backup/db"
UPLOADS_BACKUP_DIR="/backup/uploads"
LOGS_BACKUP_DIR="/backup/logs"
CONFIG_BACKUP_DIR="/backup/config"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
COMPRESSION_LEVEL=${COMPRESSION_LEVEL:-6}
ENCRYPT_BACKUP=${ENCRYPT_BACKUP:-false}
VERIFY_BACKUP=${VERIFY_BACKUP:-true}
BACKUP_TYPE=${BACKUP_TYPE:-full}  # full, incremental, differential
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ID="backup_${BACKUP_TYPE}_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking backup prerequisites..."
    
    # Check if required tools are available
    command -v mysqldump >/dev/null 2>&1 || { error "mysqldump is required but not installed"; exit 1; }
    command -v tar >/dev/null 2>&1 || { error "tar is required but not installed"; exit 1; }
    command -v gzip >/dev/null 2>&1 || { error "gzip is required but not installed"; exit 1; }
    
    # Check if encryption is requested and gpg is available
    if [ "$ENCRYPT_BACKUP" = "true" ]; then
        command -v gpg >/dev/null 2>&1 || { error "gpg is required for encryption but not installed"; exit 1; }
        if [ -z "$GPG_KEY_ID" ]; then
            error "GPG_KEY_ID is required when encryption is enabled"
            exit 1
        fi
    fi
    
    log "Prerequisites check passed"
}

# Function to create backup directories
create_backup_dirs() {
    log "Creating backup directories..."
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/database"
    mkdir -p "$BACKUP_DIR/uploads"
    mkdir -p "$BACKUP_DIR/logs"
    mkdir -p "$BACKUP_DIR/config"
    mkdir -p "$BACKUP_DIR/metadata"
    
    log "Backup directories created successfully"
}

# Function to backup database
backup_database() {
    local backup_file="$DB_BACKUP_DIR/db_${BACKUP_ID}.sql"
    local compressed_file="${backup_file}.gz"
    
    log "Creating database backup..."
    
    # Create database backup with additional options
    if mysqldump \
        -h mariadb \
        -u root \
        -p"$DB_ROOT_PASSWORD" \
        --all-databases \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --add-drop-database \
        --add-drop-table \
        --add-drop-trigger \
        --hex-blob \
        --opt \
        --quote-names \
        --skip-lock-tables \
        > "$backup_file"; then
        
        log "Database backup created successfully"
        
        # Compress backup
        if gzip -${COMPRESSION_LEVEL} "$backup_file"; then
            log "Database backup compressed successfully"
            
            # Copy to host
            cp "$compressed_file" "$BACKUP_DIR/database/"
            
            # Get file size
            local file_size=$(du -h "$BACKUP_DIR/database/$(basename "$compressed_file")" | cut -f1)
            log "Database backup size: $file_size"
            
            # Clean up temporary file
            rm -f "$compressed_file"
            
            return 0
        else
            error "Database backup compression failed"
            return 1
        fi
    else
        error "Database backup failed"
        return 1
    fi
}

# Function to backup file storage
backup_file_storage() {
    local backup_file="$UPLOADS_BACKUP_DIR/uploads_${BACKUP_ID}.tar.gz"
    
    log "Creating file storage backup..."
    
    # Create incremental backup if requested
    local incremental_flag=""
    if [ "$BACKUP_TYPE" = "incremental" ] && [ -f "/backup/last_backup_timestamp" ]; then
        local last_backup=$(cat "/backup/last_backup_timestamp")
        incremental_flag="--newer-mtime='$last_backup'"
        info "Creating incremental backup since $last_backup"
    fi
    
    # Check if uploads directory exists and has content
    if [ ! -d "/app/uploads" ] || [ -z "$(ls -A /app/uploads 2>/dev/null)" ]; then
        warn "Uploads directory is empty or does not exist, skipping file storage backup"
        return 0
    fi
    
    # Create file backup with compression
    if tar -czf "$backup_file" \
        --exclude='*.tmp' \
        --exclude='*.log' \
        --exclude='*.cache' \
        --exclude='.git' \
        --exclude='node_modules' \
        -C /app/uploads .; then
        
        log "File storage backup created successfully"
        
        # Copy to host
        cp "$backup_file" "$BACKUP_DIR/uploads/"
        
        # Get file size
        local file_size=$(du -h "$BACKUP_DIR/uploads/$(basename "$backup_file")" | cut -f1)
        log "File storage backup size: $file_size"
        
        # Clean up temporary file
        rm -f "$backup_file"
        
        return 0
    else
        error "File storage backup failed"
        return 1
    fi
}

# Function to backup logs
backup_logs() {
    local backup_file="$LOGS_BACKUP_DIR/logs_${BACKUP_ID}.tar.gz"
    
    log "Creating logs backup..."
    
    # Check if logs directory exists and has content
    if [ ! -d "/app/logs" ] || [ -z "$(ls -A /app/logs 2>/dev/null)" ]; then
        warn "Logs directory is empty or does not exist, skipping logs backup"
        return 0
    fi
    
    # Create logs backup
    if tar -czf "$backup_file" \
        --exclude='*.tmp' \
        --exclude='*.cache' \
        -C /app/logs .; then
        
        log "Logs backup created successfully"
        
        # Copy to host
        cp "$backup_file" "$BACKUP_DIR/logs/"
        
        # Get file size
        local file_size=$(du -h "$BACKUP_DIR/logs/$(basename "$backup_file")" | cut -f1)
        log "Logs backup size: $file_size"
        
        # Clean up temporary file
        rm -f "$backup_file"
        
        return 0
    else
        warn "Logs backup failed (continuing...)"
        return 0
    fi
}

# Function to backup configuration
backup_configuration() {
    local backup_file="$CONFIG_BACKUP_DIR/config_${BACKUP_ID}.tar.gz"
    
    log "Creating configuration backup..."
    
    # Check if required files exist
    local missing_files=()
    [ ! -f "/app/docker-compose.yml" ] && missing_files+=("docker-compose.yml")
    [ ! -f "/app/Dockerfile" ] && missing_files+=("Dockerfile")
    [ ! -d "/app/nginx" ] && missing_files+=("nginx/")
    [ ! -d "/app/scripts" ] && missing_files+=("scripts/")
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        warn "Missing configuration files: ${missing_files[*]}, skipping config backup"
        return 0
    fi
    
    # Create config backup
    if tar -czf "$backup_file" \
        -C /app \
        docker-compose.yml \
        Dockerfile \
        nginx/ \
        scripts/; then
        
        log "Configuration backup created successfully"
        
        # Copy to host
        cp "$backup_file" "$BACKUP_DIR/config/"
        
        # Get file size
        local file_size=$(du -h "$BACKUP_DIR/config/$(basename "$backup_file")" | cut -f1)
        log "Configuration backup size: $file_size"
        
        # Clean up temporary file
        rm -f "$backup_file"
        
        return 0
    else
        warn "Configuration backup failed (continuing...)"
        return 0
    fi
}

# Function to encrypt backup (if requested)
encrypt_backup() {
    if [ "$ENCRYPT_BACKUP" = "true" ]; then
        log "Encrypting backup files..."
        
        # Encrypt database backup
        local db_backup="$BACKUP_DIR/database/db_${BACKUP_ID}.sql.gz"
        if [ -f "$db_backup" ]; then
            if gpg --recipient "$GPG_KEY_ID" --encrypt "$db_backup"; then
                log "Database backup encrypted successfully"
                rm -f "$db_backup"  # Remove unencrypted version
            else
                error "Database backup encryption failed"
                return 1
            fi
        fi
        
        # Encrypt file storage backup
        local uploads_backup="$BACKUP_DIR/uploads/uploads_${BACKUP_ID}.tar.gz"
        if [ -f "$uploads_backup" ]; then
            if gpg --recipient "$GPG_KEY_ID" --encrypt "$uploads_backup"; then
                log "File storage backup encrypted successfully"
                rm -f "$uploads_backup"  # Remove unencrypted version
            else
                error "File storage backup encryption failed"
                return 1
            fi
        fi
        
        # Encrypt logs backup
        local logs_backup="$BACKUP_DIR/logs/logs_${BACKUP_ID}.tar.gz"
        if [ -f "$logs_backup" ]; then
            if gpg --recipient "$GPG_KEY_ID" --encrypt "$logs_backup"; then
                log "Logs backup encrypted successfully"
                rm -f "$logs_backup"  # Remove unencrypted version
            else
                warn "Logs backup encryption failed (continuing...)"
            fi
        fi
        
        # Encrypt configuration backup
        local config_backup="$BACKUP_DIR/config/config_${BACKUP_ID}.tar.gz"
        if [ -f "$config_backup" ]; then
            if gpg --recipient "$GPG_KEY_ID" --encrypt "$config_backup"; then
                log "Configuration backup encrypted successfully"
                rm -f "$config_backup"  # Remove unencrypted version
            else
                warn "Configuration backup encryption failed (continuing...)"
            fi
        fi
    fi
}

# Function to verify backup integrity
verify_backup() {
    if [ "$VERIFY_BACKUP" = "true" ]; then
        log "Verifying backup integrity..."
        
        local verification_failed=false
        
        # Verify database backup
        local db_backup="$BACKUP_DIR/database/db_${BACKUP_ID}.sql.gz"
        if [ -f "$db_backup" ]; then
            if gzip -t "$db_backup" 2>/dev/null; then
                log "Database backup verification passed"
            else
                error "Database backup verification failed"
                verification_failed=true
            fi
        fi
        
        # Verify file storage backup
        local uploads_backup="$BACKUP_DIR/uploads/uploads_${BACKUP_ID}.tar.gz"
        if [ -f "$uploads_backup" ]; then
            if tar -tzf "$uploads_backup" >/dev/null 2>&1; then
                log "File storage backup verification passed"
            else
                error "File storage backup verification failed"
                verification_failed=true
            fi
        fi
        
        # Verify logs backup
        local logs_backup="$BACKUP_DIR/logs/logs_${BACKUP_ID}.tar.gz"
        if [ -f "$logs_backup" ]; then
            if tar -tzf "$logs_backup" >/dev/null 2>&1; then
                log "Logs backup verification passed"
            else
                warn "Logs backup verification failed"
            fi
        fi
        
        # Verify configuration backup
        local config_backup="$BACKUP_DIR/config/config_${BACKUP_ID}.tar.gz"
        if [ -f "$config_backup" ]; then
            if tar -tzf "$config_backup" >/dev/null 2>&1; then
                log "Configuration backup verification passed"
            else
                warn "Configuration backup verification failed"
            fi
        fi
        
        if [ "$verification_failed" = "true" ]; then
            error "Backup verification failed"
            return 1
        fi
        
        log "All backup verifications passed"
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    
    local deleted_count=0
    
    # Clean up database backups
    deleted_count=$((deleted_count + $(find "$BACKUP_DIR/database" -name "*.sql.gz*" -mtime +$RETENTION_DAYS -delete 2>/dev/null | wc -l)))
    
    # Clean up file storage backups
    deleted_count=$((deleted_count + $(find "$BACKUP_DIR/uploads" -name "*.tar.gz*" -mtime +$RETENTION_DAYS -delete 2>/dev/null | wc -l)))
    
    # Clean up logs backups
    deleted_count=$((deleted_count + $(find "$BACKUP_DIR/logs" -name "*.tar.gz*" -mtime +$RETENTION_DAYS -delete 2>/dev/null | wc -l)))
    
    # Clean up configuration backups
    deleted_count=$((deleted_count + $(find "$BACKUP_DIR/config" -name "*.tar.gz*" -mtime +$RETENTION_DAYS -delete 2>/dev/null | wc -l)))
    
    log "Cleaned up $deleted_count old backup files"
}

# Function to create backup manifest
create_backup_manifest() {
    local manifest_file="$BACKUP_DIR/metadata/backup_manifest_${BACKUP_ID}.json"
    
    log "Creating backup manifest..."
    
    # Create JSON manifest
    cat > "$manifest_file" << EOF
{
  "backup_id": "${BACKUP_ID}",
  "backup_type": "${BACKUP_TYPE}",
  "timestamp": "$(date -Iseconds)",
  "retention_days": ${RETENTION_DAYS},
  "compression_level": ${COMPRESSION_LEVEL},
  "encrypted": ${ENCRYPT_BACKUP},
  "verified": ${VERIFY_BACKUP},
  "files": {
    "database": {
      "file": "db_${BACKUP_ID}.sql.gz",
      "size": "$(du -h "$BACKUP_DIR/database/db_${BACKUP_ID}.sql.gz" 2>/dev/null | cut -f1 || echo "N/A")",
      "checksum": "$(sha256sum "$BACKUP_DIR/database/db_${BACKUP_ID}.sql.gz" 2>/dev/null | cut -d' ' -f1 || echo "N/A")"
    },
    "uploads": {
      "file": "uploads_${BACKUP_ID}.tar.gz",
      "size": "$(du -h "$BACKUP_DIR/uploads/uploads_${BACKUP_ID}.tar.gz" 2>/dev/null | cut -f1 || echo "N/A")",
      "checksum": "$(sha256sum "$BACKUP_DIR/uploads/uploads_${BACKUP_ID}.tar.gz" 2>/dev/null | cut -d' ' -f1 || echo "N/A")"
    },
    "logs": {
      "file": "logs_${BACKUP_ID}.tar.gz",
      "size": "$(du -h "$BACKUP_DIR/logs/logs_${BACKUP_ID}.tar.gz" 2>/dev/null | cut -f1 || echo "N/A")",
      "checksum": "$(sha256sum "$BACKUP_DIR/logs/logs_${BACKUP_ID}.tar.gz" 2>/dev/null | cut -d' ' -f1 || echo "N/A")"
    },
    "config": {
      "file": "config_${BACKUP_ID}.tar.gz",
      "size": "$(du -h "$BACKUP_DIR/config/config_${BACKUP_ID}.tar.gz" 2>/dev/null | cut -f1 || echo "N/A")",
      "checksum": "$(sha256sum "$BACKUP_DIR/config/config_${BACKUP_ID}.tar.gz" 2>/dev/null | cut -d' ' -f1 || echo "N/A")"
    }
  },
  "system_info": {
    "hostname": "$(hostname)",
    "docker_version": "$(docker --version 2>/dev/null || echo 'N/A')",
    "disk_usage": "$(df -h / | tail -1 | awk '{print $5}')",
    "memory_usage": "$(free -h | grep Mem | awk '{print $3 "/" $2}')"
  }
}
EOF
    
    log "Backup manifest created: $manifest_file"
}

# Function to update backup timestamp
update_backup_timestamp() {
    echo "$(date -Iseconds)" > "/backup/last_backup_timestamp"
    log "Backup timestamp updated"
}

# Main backup function
main() {
    local start_time=$(date +%s)
    
    log "Starting enhanced FileWallBall backup process..."
    log "Backup type: $BACKUP_TYPE"
    log "Compression level: $COMPRESSION_LEVEL"
    log "Encryption: $ENCRYPT_BACKUP"
    log "Verification: $VERIFY_BACKUP"
    
    # Check prerequisites
    check_prerequisites
    
    # Create backup directories
    create_backup_dirs
    
    # Perform backups
    local backup_failed=false
    
    if ! backup_database; then
        backup_failed=true
    fi
    
    if ! backup_file_storage; then
        backup_failed=true
    fi
    
    if ! backup_logs; then
        warn "Logs backup failed (continuing...)"
    fi
    
    if ! backup_configuration; then
        warn "Configuration backup failed (continuing...)"
    fi
    
    # Encrypt backups if requested
    if [ "$backup_failed" = "false" ]; then
        encrypt_backup
    fi
    
    # Verify backups if requested
    if [ "$backup_failed" = "false" ]; then
        verify_backup
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Create backup manifest
    create_backup_manifest
    
    # Update backup timestamp
    update_backup_timestamp
    
    # Calculate backup duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ "$backup_failed" = "false" ]; then
        log "Enhanced backup process completed successfully!"
        log "Backup location: $BACKUP_DIR"
        log "Backup duration: ${duration} seconds"
        log "Backup ID: $BACKUP_ID"
    else
        error "Enhanced backup process completed with errors"
        exit 1
    fi
}

# Run main function
main "$@"
