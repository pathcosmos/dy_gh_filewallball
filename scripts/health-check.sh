#!/bin/bash

# Health check script for Docker containers
# This script provides comprehensive health checking for different services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Health check for MariaDB
check_mariadb() {
    local host="${DB_HOST:-localhost}"
    local port="${DB_PORT:-3306}"
    local user="${DB_USER:-root}"
    local password="${DB_PASSWORD:-}"
    
    log "Checking MariaDB health at $host:$port..."
    
    if mysqladmin ping -h "$host" -P "$port" -u "$user" -p"$password" >/dev/null 2>&1; then
        log "${GREEN}✓ MariaDB is healthy${NC}"
        return 0
    else
        log "${RED}✗ MariaDB health check failed${NC}"
        return 1
    fi
}

# Health check for FastAPI application
check_fastapi() {
    local port="${APP_PORT:-8000}"
    local health_url="http://localhost:$port/health"
    
    log "Checking FastAPI health at $health_url..."
    
    if curl -f -s "$health_url" >/dev/null 2>&1; then
        log "${GREEN}✓ FastAPI is healthy${NC}"
        return 0
    else
        log "${RED}✗ FastAPI health check failed${NC}"
        return 1
    fi
}

# Health check for Redis
check_redis() {
    local host="${REDIS_HOST:-localhost}"
    local port="${REDIS_PORT:-6379}"
    local password="${REDIS_PASSWORD:-}"
    
    log "Checking Redis health at $host:$port..."
    
    if redis-cli -h "$host" -p "$port" ${password:+-a "$password"} ping >/dev/null 2>&1; then
        log "${GREEN}✓ Redis is healthy${NC}"
        return 0
    else
        log "${RED}✗ Redis health check failed${NC}"
        return 1
    fi
}

# Health check for Nginx
check_nginx() {
    local port="${NGINX_PORT:-80}"
    local health_url="http://localhost:$port/health"
    
    log "Checking Nginx health at $health_url..."
    
    if curl -f -s "$health_url" >/dev/null 2>&1; then
        log "${GREEN}✓ Nginx is healthy${NC}"
        return 0
    else
        log "${RED}✗ Nginx health check failed${NC}"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    local threshold=90
    local usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    log "Checking disk space usage: ${usage}%"
    
    if [ "$usage" -lt "$threshold" ]; then
        log "${GREEN}✓ Disk space is sufficient${NC}"
        return 0
    else
        log "${YELLOW}⚠ Disk space usage is high: ${usage}%${NC}"
        return 1
    fi
}

# Check memory usage
check_memory() {
    local threshold=90
    local usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    
    log "Checking memory usage: ${usage}%"
    
    if [ "$usage" -lt "$threshold" ]; then
        log "${GREEN}✓ Memory usage is acceptable${NC}"
        return 0
    else
        log "${YELLOW}⚠ Memory usage is high: ${usage}%${NC}"
        return 1
    fi
}

# Main health check function
main() {
    local service="$1"
    local exit_code=0
    
    log "Starting health check for service: $service"
    
    case "$service" in
        "mariadb")
            check_mariadb || exit_code=1
            ;;
        "fastapi"|"app")
            check_fastapi || exit_code=1
            ;;
        "redis")
            check_redis || exit_code=1
            ;;
        "nginx")
            check_nginx || exit_code=1
            ;;
        "system")
            check_disk_space || exit_code=1
            check_memory || exit_code=1
            ;;
        "all")
            check_mariadb || exit_code=1
            check_fastapi || exit_code=1
            check_redis || exit_code=1
            check_nginx || exit_code=1
            check_disk_space || exit_code=1
            check_memory || exit_code=1
            ;;
        *)
            log "${RED}Unknown service: $service${NC}"
            log "Available services: mariadb, fastapi, redis, nginx, system, all"
            exit 1
            ;;
    esac
    
    if [ $exit_code -eq 0 ]; then
        log "${GREEN}All health checks passed${NC}"
    else
        log "${RED}Some health checks failed${NC}"
    fi
    
    exit $exit_code
}

# Run main function with provided arguments
main "${1:-all}"
