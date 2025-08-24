#!/bin/bash

# Service Manager Script for Docker Compose
# This script manages service dependencies and startup order

set -e

# Configuration
COMPOSE_FILE="docker-compose.yml"
COMPOSE_DEV_FILE="docker-compose.dev.yml"
COMPOSE_PROD_FILE="docker-compose.prod.yml"
LOG_DIR="${LOG_DIR:-./logs}"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-300}"

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

# Function to wait for service health
wait_for_service_health() {
    local service_name="$1"
    local timeout="$2"
    local elapsed=0
    local interval=5
    
    log "Waiting for $service_name to be healthy (timeout: ${timeout}s)..."
    
    while [ $elapsed -lt $timeout ]; do
        if docker-compose ps | grep "$service_name" | grep -q "healthy"; then
            log "${GREEN}✓ $service_name is healthy${NC}"
            return 0
        fi
        
        log "Waiting for $service_name to be healthy... (${elapsed}s elapsed)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    log "${RED}✗ Timeout waiting for $service_name to be healthy${NC}"
    return 1
}

# Function to check service dependencies
check_dependencies() {
    local service_name="$1"
    
    log "Checking dependencies for $service_name..."
    
    case "$service_name" in
        "mariadb")
            # MariaDB has no dependencies
            log "${GREEN}✓ MariaDB has no dependencies${NC}"
            return 0
            ;;
        "app")
            # App depends on MariaDB
            if wait_for_service_health "mariadb" "$HEALTH_CHECK_TIMEOUT"; then
                log "${GREEN}✓ MariaDB dependency satisfied${NC}"
                return 0
            else
                log "${RED}✗ MariaDB dependency not satisfied${NC}"
                return 1
            fi
            ;;
        "nginx")
            # Nginx depends on App
            if wait_for_service_health "app" "$HEALTH_CHECK_TIMEOUT"; then
                log "${GREEN}✓ App dependency satisfied${NC}"
                return 0
            else
                log "${RED}✗ App dependency not satisfied${NC}"
                return 1
            fi
            ;;
        "redis"|"redis-dev")
            # Redis has no dependencies
            log "${GREEN}✓ Redis has no dependencies${NC}"
            return 0
            ;;
        "adminer")
            # Adminer depends on MariaDB
            if wait_for_service_health "mariadb" "$HEALTH_CHECK_TIMEOUT"; then
                log "${GREEN}✓ MariaDB dependency satisfied${NC}"
                return 0
            else
                log "${RED}✗ MariaDB dependency not satisfied${NC}"
                return 1
            fi
            ;;
        *)
            log "${YELLOW}⚠ Unknown service: $service_name${NC}"
            return 0
            ;;
    esac
}

# Function to start services in order
start_services_ordered() {
    local environment="$1"
    local compose_files=""
    
    case "$environment" in
        "dev"|"development")
            compose_files="-f $COMPOSE_FILE -f $COMPOSE_DEV_FILE"
            log "Starting development environment..."
            ;;
        "prod"|"production")
            compose_files="-f $COMPOSE_FILE -f $COMPOSE_PROD_FILE"
            log "Starting production environment..."
            ;;
        *)
            compose_files="-f $COMPOSE_FILE"
            log "Starting base environment..."
            ;;
    esac
    
    # Start MariaDB first
    log "Starting MariaDB..."
    docker-compose $compose_files up -d mariadb
    
    # Wait for MariaDB to be healthy
    if ! wait_for_service_health "mariadb" "$HEALTH_CHECK_TIMEOUT"; then
        log "${RED}Failed to start MariaDB${NC}"
        return 1
    fi
    
    # Start Redis (if available)
    if docker-compose $compose_files config --services | grep -q "redis"; then
        log "Starting Redis..."
        docker-compose $compose_files up -d redis
        
        # Wait a bit for Redis to start
        sleep 5
        
        # Get the actual Redis service name
        local redis_service_name=$(docker-compose $compose_files config --services | grep redis | head -1)
        
        if ! wait_for_service_health "$redis_service_name" "$HEALTH_CHECK_TIMEOUT"; then
            log "${YELLOW}Warning: Redis failed to start, but continuing...${NC}"
        fi
    fi
    
    # Start FastAPI App
    log "Starting FastAPI App..."
    docker-compose $compose_files up -d app
    
    if ! wait_for_service_health "app" "$HEALTH_CHECK_TIMEOUT"; then
        log "${RED}Failed to start FastAPI App${NC}"
        return 1
    fi
    
    # Start Adminer (if available)
    if docker-compose $compose_files config --services | grep -q "adminer"; then
        log "Starting Adminer..."
        docker-compose $compose_files up -d adminer
        
        if ! wait_for_service_health "adminer" "$HEALTH_CHECK_TIMEOUT"; then
            log "${YELLOW}Warning: Adminer failed to start, but continuing...${NC}"
        fi
    fi
    
    # Start Nginx (if available and not in profiles)
    if docker-compose $compose_files config --services | grep -q "nginx"; then
        log "Starting Nginx..."
        docker-compose $compose_files up -d nginx
        
        if ! wait_for_service_health "nginx" "$HEALTH_CHECK_TIMEOUT"; then
            log "${YELLOW}Warning: Nginx failed to start, but continuing...${NC}"
        fi
    fi
    
    log "${GREEN}✓ All services started successfully${NC}"
}

# Function to stop services in reverse order
stop_services_ordered() {
    local environment="$1"
    local compose_files=""
    
    case "$environment" in
        "dev"|"development")
            compose_files="-f $COMPOSE_FILE -f $COMPOSE_DEV_FILE"
            log "Stopping development environment..."
            ;;
        "prod"|"production")
            compose_files="-f $COMPOSE_FILE -f $COMPOSE_PROD_FILE"
            log "Stopping production environment..."
            ;;
        *)
            compose_files="-f $COMPOSE_FILE"
            log "Stopping base environment..."
            ;;
    esac
    
    # Stop services in reverse dependency order
    log "Stopping Nginx..."
    docker-compose $compose_files stop nginx 2>/dev/null || true
    
    log "Stopping Adminer..."
    docker-compose $compose_files stop adminer 2>/dev/null || true
    
    log "Stopping FastAPI App..."
    docker-compose $compose_files stop app 2>/dev/null || true
    
    log "Stopping Redis..."
    docker-compose $compose_files stop redis 2>/dev/null || true
    
    log "Stopping MariaDB..."
    docker-compose $compose_files stop mariadb 2>/dev/null || true
    
    log "${GREEN}✓ All services stopped successfully${NC}"
}

# Function to restart services
restart_services() {
    local environment="$1"
    
    log "Restarting services for $environment environment..."
    
    stop_services_ordered "$environment"
    sleep 5
    start_services_ordered "$environment"
}

# Function to show service status
show_service_status() {
    local environment="$1"
    local compose_files=""
    
    case "$environment" in
        "dev"|"development")
            compose_files="-f $COMPOSE_FILE -f $COMPOSE_DEV_FILE"
            ;;
        "prod"|"production")
            compose_files="-f $COMPOSE_FILE -f $COMPOSE_PROD_FILE"
            ;;
        *)
            compose_files="-f $COMPOSE_FILE"
            ;;
    esac
    
    log "Service status for $environment environment:"
    docker-compose $compose_files ps
    
    echo ""
    log "Service health status:"
    docker-compose $compose_files ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

# Function to show service logs
show_service_logs() {
    local service_name="$1"
    local lines="${2:-50}"
    
    if [ -z "$service_name" ]; then
        log "${RED}Service name required${NC}"
        return 1
    fi
    
    log "Showing last $lines lines of logs for $service_name:"
    docker-compose logs --tail="$lines" "$service_name"
}

# Main function
main() {
    local action="$1"
    local environment="$2"
    local service_name="$3"
    
    case "$action" in
        "start")
            if [ -z "$environment" ]; then
                environment="dev"
            fi
            start_services_ordered "$environment"
            ;;
        "stop")
            if [ -z "$environment" ]; then
                environment="dev"
            fi
            stop_services_ordered "$environment"
            ;;
        "restart")
            if [ -z "$environment" ]; then
                environment="dev"
            fi
            restart_services "$environment"
            ;;
        "status")
            if [ -z "$environment" ]; then
                environment="dev"
            fi
            show_service_status "$environment"
            ;;
        "logs")
            show_service_logs "$environment" "$service_name"
            ;;
        "health")
            if [ -z "$environment" ]; then
                environment="dev"
            fi
            log "Checking health for $environment environment..."
            docker-compose -f "$COMPOSE_FILE" -f "$COMPOSE_DEV_FILE" ps | grep -E "(healthy|unhealthy)"
            ;;
        "help"|"--help"|"-h")
            echo "Usage: $0 <action> [environment] [service]"
            echo ""
            echo "Actions:"
            echo "  start [env]     - Start services in dependency order"
            echo "  stop [env]      - Stop services in reverse dependency order"
            echo "  restart [env]   - Restart all services"
            echo "  status [env]    - Show service status"
            echo "  logs <service>  - Show service logs"
            echo "  health [env]    - Show service health status"
            echo "  help            - Show this help message"
            echo ""
            echo "Environments:"
            echo "  dev (default)   - Development environment"
            echo "  prod            - Production environment"
            echo "  base            - Base environment only"
            echo ""
            echo "Examples:"
            echo "  $0 start dev"
            echo "  $0 stop prod"
            echo "  $0 restart dev"
            echo "  $0 status dev"
            echo "  $0 logs filewallball-app"
            echo "  $0 health prod"
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
