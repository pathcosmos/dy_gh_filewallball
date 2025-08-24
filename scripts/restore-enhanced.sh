#!/bin/bash

# Enhanced FileWallBall Restore Script
# This script provides comprehensive restore functionality with verification and rollback

set -e

# Configuration
BACKUP_DIR="/host-backups"
DB_BACKUP_DIR="/backup/db"
UPLOADS_BACKUP_DIR="/backup/uploads"
LOGS_BACKUP_DIR="/backup/logs"
CONFIG_BACKUP_DIR="/backup/config"
RESTORE_DIR="/restore"
ROLLBACK_DIR="/rollback"
VERIFY_RESTORE=${VERIFY_RESTORE:-true}
CREATE_ROLLBACK=${CREATE_ROLLBACK:-true}
RESTORE_TYPE=${RESTORE_TYPE:-full}  # full, database, uploads, logs, config

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
    log "Checking restore prerequisites..."
    
    # Check if required tools are available
    command -v mysql >/dev/null 2>&1 || { error "mysql is required but not installed"; exit 1; }
    command -v tar >/dev/null 2>&1 || { error "tar is required but not installed"; exit 1; }
    command -v gzip >/dev/null 2>&1 || { error "gzip is required but not installed"; exit 1; }
    
    # Check if GPG is available for encrypted backups
    command -v gpg >/dev/null 2>&1 || { warn "gpg not available - encrypted backups cannot be restored"; }
    
    log "Prerequisites check passed"
}

# Function to list available backups
list_backups() {
    log "Available backups:"
    
    echo ""
    echo "=== Database Backups ==="
    if [ -d "$BACKUP_DIR/database" ]; then
        for backup in "$BACKUP_DIR/database"/*.sql.gz*; do
            if [ -f "$backup" ]; then
                local size=$(du -h "$backup" | cut -f1)
                local date=$(stat -c %y "$backup" | cut -d' ' -f1)
                echo "  $(basename "$backup") - $size - $date"
            fi
        done
    else
        echo "  No database backups found"
    fi
    
    echo ""
    echo "=== File Storage Backups ==="
    if [ -d "$BACKUP_DIR/uploads" ]; then
        for backup in "$BACKUP_DIR/uploads"/*.tar.gz*; do
            if [ -f "$backup" ]; then
                local size=$(du -h "$backup" | cut -f1)
                local date=$(stat -c %y "$backup" | cut -d' ' -f1)
                echo "  $(basename "$backup") - $size - $date"
            fi
        done
    else
        echo "  No file storage backups found"
    fi
    
    echo ""
    echo "=== Logs Backups ==="
    if [ -d "$BACKUP_DIR/logs" ]; then
        for backup in "$BACKUP_DIR/logs"/*.tar.gz*; do
            if [ -f "$backup" ]; then
                local size=$(du -h "$backup" | cut -f1)
                local date=$(stat -c %y "$backup" | cut -d' ' -f1)
                echo "  $(basename "$backup") - $size - $date"
            fi
        done
    else
        echo "  No logs backups found"
    fi
    
    echo ""
    echo "=== Configuration Backups ==="
    if [ -d "$BACKUP_DIR/config" ]; then
        for backup in "$BACKUP_DIR/config"/*.tar.gz*; do
            if [ -f "$backup" ]; then
                local size=$(du -h "$backup" | cut -f1)
                local date=$(stat -c %y "$backup" | cut -d' ' -f1)
                echo "  $(basename "$backup") - $size - $date"
            fi
        done
    else
        echo "  No configuration backups found"
    fi
}

# Function to decrypt backup if encrypted
decrypt_backup() {
    local backup_file="$1"
    
    if [[ "$backup_file" == *.gpg ]]; then
        log "Decrypting backup: $backup_file"
        
        local decrypted_file="${backup_file%.gpg}"
        if gpg --decrypt "$backup_file" > "$decrypted_file"; then
            log "Backup decrypted successfully"
            echo "$decrypted_file"
        else
            error "Failed to decrypt backup: $backup_file"
            return 1
        fi
    else
        echo "$backup_file"
    fi
}

# Function to create rollback point
create_rollback_point() {
    if [ "$CREATE_ROLLBACK" = "true" ]; then
        local rollback_id="rollback_$(date +%Y%m%d_%H%M%S)"
        local rollback_dir="$ROLLBACK_DIR/$rollback_id"
        
        log "Creating rollback point: $rollback_id"
        
        mkdir -p "$rollback_dir"
        
        # Backup current database
        if mysqldump -h mariadb -u root -p"$DB_ROOT_PASSWORD" --all-databases > "$rollback_dir/database.sql" 2>/dev/null; then
            log "Database rollback point created"
        else
            warn "Failed to create database rollback point"
        fi
        
        # Backup current uploads
        if tar -czf "$rollback_dir/uploads.tar.gz" -C /app/uploads . 2>/dev/null; then
            log "Uploads rollback point created"
        else
            warn "Failed to create uploads rollback point"
        fi
        
        # Backup current logs
        if tar -czf "$rollback_dir/logs.tar.gz" -C /app/logs . 2>/dev/null; then
            log "Logs rollback point created"
        else
            warn "Failed to create logs rollback point"
        fi
        
        # Create rollback manifest
        cat > "$rollback_dir/rollback_manifest.txt" << EOF
Rollback Point: $rollback_id
Created: $(date)
Reason: Pre-restore backup
EOF
        
        log "Rollback point created: $rollback_dir"
    fi
}

# Function to restore database
restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Database backup file not specified"
        return 1
    fi
    
    log "Restoring database from: $backup_file"
    
    # Decrypt if needed
    local actual_backup_file=$(decrypt_backup "$backup_file")
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Decompress if needed
    local sql_file="$actual_backup_file"
    if [[ "$actual_backup_file" == *.gz ]]; then
        log "Decompressing database backup..."
        sql_file="${actual_backup_file%.gz}"
        if ! gzip -d "$actual_backup_file"; then
            error "Failed to decompress database backup"
            return 1
        fi
    fi
    
    # Restore database
    log "Restoring database..."
    if mysql -h mariadb -u root -p"$DB_ROOT_PASSWORD" < "$sql_file"; then
        log "Database restored successfully"
        
        # Clean up temporary files
        if [ "$actual_backup_file" != "$backup_file" ]; then
            rm -f "$actual_backup_file"
        fi
        if [ "$sql_file" != "$actual_backup_file" ]; then
            rm -f "$sql_file"
        fi
        
        return 0
    else
        error "Database restore failed"
        return 1
    fi
}

# Function to restore file storage
restore_file_storage() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "File storage backup file not specified"
        return 1
    fi
    
    log "Restoring file storage from: $backup_file"
    
    # Decrypt if needed
    local actual_backup_file=$(decrypt_backup "$backup_file")
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Create temporary restore directory
    local temp_restore_dir="/tmp/restore_uploads_$$"
    mkdir -p "$temp_restore_dir"
    
    # Extract backup
    log "Extracting file storage backup..."
    if tar -xzf "$actual_backup_file" -C "$temp_restore_dir"; then
        log "File storage backup extracted successfully"
        
        # Stop application to prevent file conflicts
        log "Stopping application to prevent file conflicts..."
        docker-compose stop app 2>/dev/null || true
        
        # Backup current uploads
        if [ -d "/app/uploads" ]; then
            mv /app/uploads "/app/uploads_backup_$(date +%Y%m%d_%H%M%S)"
        fi
        
        # Restore uploads
        mv "$temp_restore_dir" /app/uploads
        chmod -R 755 /app/uploads
        
        log "File storage restored successfully"
        
        # Clean up temporary files
        if [ "$actual_backup_file" != "$backup_file" ]; then
            rm -f "$actual_backup_file"
        fi
        
        # Restart application
        log "Restarting application..."
        docker-compose start app 2>/dev/null || true
        
        return 0
    else
        error "File storage restore failed"
        rm -rf "$temp_restore_dir"
        return 1
    fi
}

# Function to restore logs
restore_logs() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Logs backup file not specified"
        return 1
    fi
    
    log "Restoring logs from: $backup_file"
    
    # Decrypt if needed
    local actual_backup_file=$(decrypt_backup "$backup_file")
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Create temporary restore directory
    local temp_restore_dir="/tmp/restore_logs_$$"
    mkdir -p "$temp_restore_dir"
    
    # Extract backup
    log "Extracting logs backup..."
    if tar -xzf "$actual_backup_file" -C "$temp_restore_dir"; then
        log "Logs backup extracted successfully"
        
        # Backup current logs
        if [ -d "/app/logs" ]; then
            mv /app/logs "/app/logs_backup_$(date +%Y%m%d_%H%M%S)"
        fi
        
        # Restore logs
        mv "$temp_restore_dir" /app/logs
        chmod -R 755 /app/logs
        
        log "Logs restored successfully"
        
        # Clean up temporary files
        if [ "$actual_backup_file" != "$backup_file" ]; then
            rm -f "$actual_backup_file"
        fi
        
        return 0
    else
        error "Logs restore failed"
        rm -rf "$temp_restore_dir"
        return 1
    fi
}

# Function to restore configuration
restore_configuration() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Configuration backup file not specified"
        return 1
    fi
    
    log "Restoring configuration from: $backup_file"
    
    # Decrypt if needed
    local actual_backup_file=$(decrypt_backup "$backup_file")
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Create temporary restore directory
    local temp_restore_dir="/tmp/restore_config_$$"
    mkdir -p "$temp_restore_dir"
    
    # Extract backup
    log "Extracting configuration backup..."
    if tar -xzf "$actual_backup_file" -C "$temp_restore_dir"; then
        log "Configuration backup extracted successfully"
        
        # Backup current configuration
        if [ -d "/app/config_backup" ]; then
            rm -rf "/app/config_backup"
        fi
        mkdir -p /app/config_backup
        
        # Backup current files
        cp -r /app/docker-compose*.yml /app/config_backup/ 2>/dev/null || true
        cp -r /app/Dockerfile /app/config_backup/ 2>/dev/null || true
        cp -r /app/nginx /app/config_backup/ 2>/dev/null || true
        cp -r /app/scripts /app/config_backup/ 2>/dev/null || true
        
        # Restore configuration files
        cp -r "$temp_restore_dir"/* /app/
        chmod -R 755 /app/scripts
        
        log "Configuration restored successfully"
        
        # Clean up temporary files
        if [ "$actual_backup_file" != "$backup_file" ]; then
            rm -f "$actual_backup_file"
        fi
        rm -rf "$temp_restore_dir"
        
        return 0
    else
        error "Configuration restore failed"
        rm -rf "$temp_restore_dir"
        return 1
    fi
}

# Function to verify restore
verify_restore() {
    if [ "$VERIFY_RESTORE" = "true" ]; then
        log "Verifying restore..."
        
        local verification_failed=false
        
        # Verify database
        if mysql -h mariadb -u root -p"$DB_ROOT_PASSWORD" -e "SHOW DATABASES;" >/dev/null 2>&1; then
            log "Database restore verification passed"
        else
            error "Database restore verification failed"
            verification_failed=true
        fi
        
        # Verify uploads directory
        if [ -d "/app/uploads" ] && [ "$(ls -A /app/uploads 2>/dev/null)" ]; then
            log "File storage restore verification passed"
        else
            warn "File storage restore verification failed"
        fi
        
        # Verify logs directory
        if [ -d "/app/logs" ]; then
            log "Logs restore verification passed"
        else
            warn "Logs restore verification failed"
        fi
        
        # Verify configuration files
        if [ -f "/app/docker-compose.yml" ]; then
            log "Configuration restore verification passed"
        else
            warn "Configuration restore verification failed"
        fi
        
        if [ "$verification_failed" = "true" ]; then
            error "Restore verification failed"
            return 1
        fi
        
        log "All restore verifications passed"
    fi
}

# Function to show restore help
show_help() {
    echo "Usage: $0 [options] <backup_file>"
    echo ""
    echo "Options:"
    echo "  --type <type>        Restore type: full, database, uploads, logs, config (default: full)"
    echo "  --no-rollback        Skip creating rollback point"
    echo "  --no-verify          Skip restore verification"
    echo "  --list               List available backups"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --type database db_backup_full_20250101_120000.sql.gz"
    echo "  $0 --type uploads uploads_backup_full_20250101_120000.tar.gz"
    echo "  $0 --list"
    echo ""
    echo "Note: For encrypted backups, ensure GPG is configured with the appropriate keys."
}

# Main restore function
main() {
    local backup_file=""
    local restore_type="$RESTORE_TYPE"
    local create_rollback="$CREATE_ROLLBACK"
    local verify_restore="$VERIFY_RESTORE"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                restore_type="$2"
                shift 2
                ;;
            --no-rollback)
                create_rollback="false"
                shift
                ;;
            --no-verify)
                verify_restore="false"
                shift
                ;;
            --list)
                list_backups
                exit 0
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                backup_file="$1"
                shift
                ;;
        esac
    done
    
    # Check if backup file is specified (unless listing)
    if [ -z "$backup_file" ]; then
        error "Backup file must be specified"
        show_help
        exit 1
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Create restore directories
    mkdir -p "$RESTORE_DIR"
    mkdir -p "$ROLLBACK_DIR"
    
    log "Starting enhanced FileWallBall restore process..."
    log "Restore type: $restore_type"
    log "Create rollback: $create_rollback"
    log "Verify restore: $verify_restore"
    
    # Create rollback point
    if [ "$create_rollback" = "true" ]; then
        create_rollback_point
    fi
    
    # Perform restore based on type
    case "$restore_type" in
        "full")
            log "Performing full restore..."
            
            # Extract backup type from filename
            if [[ "$backup_file" == *"db_"* ]]; then
                restore_database "$backup_file"
            elif [[ "$backup_file" == *"uploads_"* ]]; then
                restore_file_storage "$backup_file"
            elif [[ "$backup_file" == *"logs_"* ]]; then
                restore_logs "$backup_file"
            elif [[ "$backup_file" == *"config_"* ]]; then
                restore_configuration "$backup_file"
            else
                error "Cannot determine backup type from filename: $backup_file"
                exit 1
            fi
            ;;
        "database")
            restore_database "$backup_file"
            ;;
        "uploads")
            restore_file_storage "$backup_file"
            ;;
        "logs")
            restore_logs "$backup_file"
            ;;
        "config")
            restore_configuration "$backup_file"
            ;;
        *)
            error "Unknown restore type: $restore_type"
            exit 1
            ;;
    esac
    
    # Verify restore
    if [ "$verify_restore" = "true" ]; then
        verify_restore
    fi
    
    log "Enhanced restore process completed successfully!"
    log "Restore type: $restore_type"
    log "Backup file: $backup_file"
    
    if [ "$create_rollback" = "true" ]; then
        log "Rollback point created in: $ROLLBACK_DIR"
    fi
}

# Run main function
main "$@"
