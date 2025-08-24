#!/bin/bash

# Log monitoring script for Docker containers
# This script monitors logs for errors, warnings, and performance issues

set -e

# Configuration
LOG_DIR="${LOG_DIR:-./logs}"
MAX_LOG_SIZE="${MAX_LOG_SIZE:-100M}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"
ERROR_THRESHOLD="${ERROR_THRESHOLD:-10}"
WARNING_THRESHOLD="${WARNING_THRESHOLD:-50}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to monitor container logs
monitor_container_logs() {
    local container_name="$1"
    local log_file="$LOG_DIR/${container_name}.log"
    
    log "Monitoring logs for container: $container_name"
    
    # Create log file if it doesn't exist
    touch "$log_file"
    
    # Monitor logs in real-time
    docker logs -f "$container_name" 2>&1 | while IFS= read -r line; do
        # Add timestamp to log line
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$timestamp] $line" >> "$log_file"
        
        # Check for errors and warnings
        if echo "$line" | grep -qi "error\|exception\|fail\|critical"; then
            echo -e "[$timestamp] ${RED}ERROR: $line${NC}" >&2
        elif echo "$line" | grep -qi "warn\|warning"; then
            echo -e "[$timestamp] ${YELLOW}WARNING: $line${NC}" >&2
        fi
    done
}

# Function to analyze log files
analyze_logs() {
    local container_name="$1"
    local log_file="$LOG_DIR/${container_name}.log"
    
    if [ ! -f "$log_file" ]; then
        log "${YELLOW}Log file not found: $log_file${NC}"
        return 1
    fi
    
    log "Analyzing logs for container: $container_name"
    
    # Count different log levels
    local error_count=$(grep -ci "error\|exception\|fail\|critical" "$log_file" || echo "0")
    local warning_count=$(grep -ci "warn\|warning" "$log_file" || echo "0")
    local info_count=$(grep -ci "info" "$log_file" || echo "0")
    local total_lines=$(wc -l < "$log_file")
    
    echo "=== Log Analysis for $container_name ==="
    echo "Total log lines: $total_lines"
    echo "Errors: $error_count"
    echo "Warnings: $warning_count"
    echo "Info messages: $info_count"
    
    # Check thresholds
    if [ "$error_count" -gt "$ERROR_THRESHOLD" ]; then
        log "${RED}⚠ High error count: $error_count (threshold: $ERROR_THRESHOLD)${NC}"
    fi
    
    if [ "$warning_count" -gt "$WARNING_THRESHOLD" ]; then
        log "${YELLOW}⚠ High warning count: $warning_count (threshold: $WARNING_THRESHOLD)${NC}"
    fi
    
    # Show recent errors
    if [ "$error_count" -gt 0 ]; then
        echo ""
        echo "Recent errors:"
        grep -i "error\|exception\|fail\|critical" "$log_file" | tail -5
    fi
    
    # Show recent warnings
    if [ "$warning_count" -gt 0 ]; then
        echo ""
        echo "Recent warnings:"
        grep -i "warn\|warning" "$log_file" | tail -5
    fi
}

# Function to rotate logs
rotate_logs() {
    local container_name="$1"
    local log_file="$LOG_DIR/${container_name}.log"
    
    if [ ! -f "$log_file" ]; then
        return 0
    fi
    
    local file_size=$(du -h "$log_file" | cut -f1)
    local size_in_bytes=$(du -b "$log_file" | cut -f1)
    local max_size_bytes=$(numfmt --from=iec "$MAX_LOG_SIZE")
    
    if [ "$size_in_bytes" -gt "$max_size_bytes" ]; then
        log "Rotating log file for $container_name (size: $file_size)"
        
        # Create backup with timestamp
        local backup_file="$log_file.$(date +%Y%m%d_%H%M%S).bak"
        mv "$log_file" "$backup_file"
        
        # Compress backup
        gzip "$backup_file"
        
        # Create new empty log file
        touch "$log_file"
        
        log "Log rotated: $backup_file.gz"
    fi
}

# Function to clean old logs
cleanup_old_logs() {
    log "Cleaning up old log files (older than $LOG_RETENTION_DAYS days)"
    
    local deleted_count=0
    local current_time=$(date +%s)
    local retention_seconds=$((LOG_RETENTION_DAYS * 24 * 60 * 60))
    
    for log_file in "$LOG_DIR"/*.log.*.bak.gz; do
        if [ -f "$log_file" ]; then
            local file_time=$(stat -c %Y "$log_file")
            local age=$((current_time - file_time))
            
            if [ "$age" -gt "$retention_seconds" ]; then
                rm "$log_file"
                deleted_count=$((deleted_count + 1))
                log "Deleted old log file: $log_file"
            fi
        fi
    done
    
    log "Cleanup completed. Deleted $deleted_count old log files."
}

# Function to show log statistics
show_log_stats() {
    log "Log Statistics:"
    echo "=== Log Directory: $LOG_DIR ==="
    
    local total_size=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1 || echo "0")
    local file_count=$(find "$LOG_DIR" -name "*.log*" 2>/dev/null | wc -l || echo "0")
    
    echo "Total size: $total_size"
    echo "Total files: $file_count"
    
    echo ""
    echo "Container log files:"
    for log_file in "$LOG_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            local size=$(du -h "$log_file" | cut -f1)
            local lines=$(wc -l < "$log_file")
            echo "  $(basename "$log_file"): $size, $lines lines"
        fi
    done
}

# Main function
main() {
    local action="$1"
    local container_name="$2"
    
    case "$action" in
        "monitor")
            if [ -z "$container_name" ]; then
                log "${RED}Container name required for monitor action${NC}"
                exit 1
            fi
            monitor_container_logs "$container_name"
            ;;
        "analyze")
            if [ -z "$container_name" ]; then
                log "${RED}Container name required for analyze action${NC}"
                exit 1
            fi
            analyze_logs "$container_name"
            ;;
        "rotate")
            if [ -z "$container_name" ]; then
                log "${RED}Container name required for rotate action${NC}"
                exit 1
            fi
            rotate_logs "$container_name"
            ;;
        "cleanup")
            cleanup_old_logs
            ;;
        "stats")
            show_log_stats
            ;;
        "help"|"--help"|"-h")
            echo "Usage: $0 <action> [container_name]"
            echo ""
            echo "Actions:"
            echo "  monitor <container>  - Monitor container logs in real-time"
            echo "  analyze <container>  - Analyze log files for errors/warnings"
            echo "  rotate <container>   - Rotate log files if they exceed size limit"
            echo "  cleanup             - Clean up old log files"
            echo "  stats               - Show log statistics"
            echo "  help                - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 monitor filewallball-app"
            echo "  $0 analyze filewallball-mariadb"
            echo "  $0 rotate filewallball-app"
            echo "  $0 cleanup"
            echo "  $0 stats"
            ;;
        *)
            log "${RED}Unknown action: $action${NC}"
            log "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with provided arguments
main "$@"
