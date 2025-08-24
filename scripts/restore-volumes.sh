#!/bin/bash

# FileWallBall Volume Restore Script
# This script restores Docker volumes from backup files

set -e

# Configuration
BACKUP_DIR="./backups/volumes"
RESTORE_DIR="./restored_volumes"

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

# Function to show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -b, --backup-dir DIR    Backup directory (default: $BACKUP_DIR)"
    echo "  -r, --restore-dir DIR   Restore directory (default: $RESTORE_DIR)"
    echo "  -v, --volume NAME       Restore specific volume only"
    echo "  -t, --timestamp TS      Restore from specific timestamp (YYYYMMDD_HHMMSS)"
    echo "  -l, --list              List available backups"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --list                                    # List available backups"
    echo "  $0 --volume dy_gh_filewallball_uploads_dev_data  # Restore specific volume"
    echo "  $0 --timestamp 20250824_215514               # Restore from specific timestamp"
}

# Parse command line arguments
LIST_BACKUPS=false
SPECIFIC_VOLUME=""
SPECIFIC_TIMESTAMP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -r|--restore-dir)
            RESTORE_DIR="$2"
            shift 2
            ;;
        -v|--volume)
            SPECIFIC_VOLUME="$2"
            shift 2
            ;;
        -t|--timestamp)
            SPECIFIC_TIMESTAMP="$2"
            shift 2
            ;;
        -l|--list)
            LIST_BACKUPS=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    error "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Function to list available backups
list_backups() {
    log "Available backups in $BACKUP_DIR:"
    echo ""
    
    # Find all backup files
    BACKUP_FILES=$(find "$BACKUP_DIR" -name "*.tar.gz" | sort)
    
    if [ -z "$BACKUP_FILES" ]; then
        warn "No backup files found"
        return
    fi
    
    # Group by volume and timestamp
    declare -A volumes
    for file in $BACKUP_FILES; do
        filename=$(basename "$file")
        if [[ $filename =~ ^(.+)_([0-9]{8}_[0-9]{6})\.tar\.gz$ ]]; then
            volume="${BASH_REMATCH[1]}"
            timestamp="${BASH_REMATCH[2]}"
            volumes["$volume"]="${volumes[$volume]} $timestamp"
        fi
    done
    
    # Display grouped backups
    for volume in "${!volumes[@]}"; do
        echo "Volume: $volume"
        for timestamp in ${volumes[$volume]}; do
            backup_file="${BACKUP_DIR}/${volume}/${volume}_${timestamp}.tar.gz"
            if [ -f "$backup_file" ]; then
                size=$(du -h "$backup_file" | cut -f1)
                echo "  - $timestamp (Size: $size)"
            fi
        done
        echo ""
    done
}

# Function to restore volume
restore_volume() {
    local volume_name="$1"
    local timestamp="$2"
    
    if [ -z "$timestamp" ]; then
        # Find latest backup for the volume
        latest_backup=$(find "$BACKUP_DIR/$volume_name" -name "${volume_name}_*.tar.gz" | sort | tail -1)
        if [ -z "$latest_backup" ]; then
            error "No backup found for volume: $volume_name"
            return 1
        fi
        timestamp=$(basename "$latest_backup" | sed "s/${volume_name}_\(.*\)\.tar\.gz/\1/")
        log "Using latest backup timestamp: $timestamp"
    fi
    
    local backup_file="${BACKUP_DIR}/${volume_name}/${volume_name}_${timestamp}.tar.gz"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring volume $volume_name from timestamp $timestamp"
    
    # Create restore directory
    local restore_path="$RESTORE_DIR/$volume_name"
    mkdir -p "$restore_path"
    
    # Extract backup
    if tar -xzf "$backup_file" -C "$restore_path"; then
        log "Volume $volume_name restored successfully to $restore_path"
        
        # Show restored contents
        local file_count=$(find "$restore_path" -type f | wc -l)
        local dir_count=$(find "$restore_path" -type d | wc -l)
        log "Restored: $file_count files, $dir_count directories"
        
        return 0
    else
        error "Failed to restore volume $volume_name"
        return 1
    fi
}

# Main execution
if [ "$LIST_BACKUPS" = true ]; then
    list_backups
    exit 0
fi

# Create restore directory
mkdir -p "$RESTORE_DIR"

log "Starting FileWallBall volume restore process..."

if [ -n "$SPECIFIC_VOLUME" ]; then
    # Restore specific volume
    if [ -n "$SPECIFIC_TIMESTAMP" ]; then
        restore_volume "$SPECIFIC_VOLUME" "$SPECIFIC_TIMESTAMP"
    else
        restore_volume "$SPECIFIC_VOLUME"
    fi
else
    # Restore all volumes
    VOLUMES=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "dy_gh_filewallball_*" | sort)
    
    for volume_dir in $VOLUMES; do
        volume_name=$(basename "$volume_dir")
        if [ -n "$SPECIFIC_TIMESTAMP" ]; then
            restore_volume "$volume_name" "$SPECIFIC_TIMESTAMP"
        else
            restore_volume "$volume_name"
        fi
    done
fi

log "Volume restore process completed successfully!"
log "Restore location: $RESTORE_DIR"
