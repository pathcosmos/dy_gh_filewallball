#!/bin/bash

# FileWallBall Database Connection Test Script
# This script tests database connections from various sources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD:-"FileWallBall_Root_2025!"}
DB_NAME=${DB_NAME:-"filewallball_db"}
DB_USER=${DB_USER:-"filewallball_user"}
DB_PASSWORD=${DB_PASSWORD:-"FileWallBall_User_2025!"}
DB_PORT=${DB_PORT:-13306}
DB_HOST=${DB_HOST:-"localhost"}

echo -e "${BLUE}🧪 FileWallBall Database Connection Test Script${NC}"
echo -e "${BLUE}==============================================${NC}"
echo ""

echo -e "${YELLOW}📋 Test Configuration:${NC}"
echo "  Root Password: ${DB_ROOT_PASSWORD}"
echo "  Database Name: ${DB_NAME}"
echo "  User: ${DB_USER}"
echo "  User Password: ${DB_PASSWORD}"
echo "  Port: ${DB_PORT}"
echo "  Host: ${DB_HOST}"
echo ""

# Function to check if MariaDB container is running
check_container_running() {
    if docker ps | grep -q "filewallball-mariadb"; then
        return 0
    else
        return 1
    fi
}

# Function to test container internal connections
test_container_connections() {
    echo -e "${BLUE}🔧 Testing Container Internal Connections${NC}"
    echo -e "${BLUE}==========================================${NC}"
    
    if ! check_container_running; then
        echo -e "${RED}❌ MariaDB container is not running${NC}"
        return 1
    fi
    
    # Test root connection from container
    echo -e "${YELLOW}🔑 Testing root connection from container...${NC}"
    if docker exec filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "SELECT 'Root connection successful' as status, VERSION() as version;" 2>/dev/null; then
        echo -e "${GREEN}✅ Root connection from container successful${NC}"
    else
        echo -e "${RED}❌ Root connection from container failed${NC}"
        return 1
    fi
    
    # Test filewallball user connection from container
    echo -e "${YELLOW}👤 Testing filewallball user connection from container...${NC}"
    if docker exec filewallball-mariadb mysql -u "${DB_USER}" -p"${DB_PASSWORD}" -e "SELECT 'FileWallBall user connection successful' as status, DATABASE() as current_db;" 2>/dev/null; then
        echo -e "${GREEN}✅ FileWallBall user connection from container successful${NC}"
    else
        echo -e "${RED}❌ FileWallBall user connection from container failed${NC}"
        return 1
    fi
    
    # Test database access
    echo -e "${YELLOW}🗄️  Testing database access...${NC}"
    if docker exec filewallball-mariadb mysql -u "${DB_USER}" -p"${DB_PASSWORD}" -e "USE ${DB_NAME}; SHOW TABLES;" 2>/dev/null; then
        echo -e "${GREEN}✅ Database access successful${NC}"
    else
        echo -e "${RED}❌ Database access failed${NC}"
        return 1
    fi
    
    echo ""
}

# Function to test host connections
test_host_connections() {
    echo -e "${BLUE}🏠 Testing Host Connections${NC}"
    echo -e "${BLUE}==========================${NC}"
    
    # Check if mysql client is available
    if ! command -v mysql &> /dev/null; then
        echo -e "${YELLOW}⚠️  MySQL client not found on host, skipping host connection tests${NC}"
        echo "  To install MySQL client:"
        echo "    Ubuntu/Debian: sudo apt install mysql-client"
        echo "    CentOS/RHEL: sudo yum install mysql"
        echo "    macOS: brew install mysql-client"
        echo ""
        return 0
    fi
    
    # Test root connection from host
    echo -e "${YELLOW}🔑 Testing root connection from host...${NC}"
    if mysql -h "${DB_HOST}" -P "${DB_PORT}" -u root -p"${DB_ROOT_PASSWORD}" -e "SELECT 'Root connection from host successful' as status, VERSION() as version;" 2>/dev/null; then
        echo -e "${GREEN}✅ Root connection from host successful${NC}"
    else
        echo -e "${RED}❌ Root connection from host failed${NC}"
        return 1
    fi
    
    # Test filewallball user connection from host
    echo -e "${YELLOW}👤 Testing filewallball user connection from host...${NC}"
    if mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASSWORD}" -e "SELECT 'FileWallBall user connection from host successful' as status, DATABASE() as current_db;" 2>/dev/null; then
        echo -e "${GREEN}✅ FileWallBall user connection from host successful${NC}"
    else
        echo -e "${RED}❌ FileWallBall user connection from host failed${NC}"
        return 1
    fi
    
    # Test database access from host
    echo -e "${YELLOW}🗄️  Testing database access from host...${NC}"
    if mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASSWORD}" -e "USE ${DB_NAME}; SHOW TABLES;" 2>/dev/null; then
        echo -e "${GREEN}✅ Database access from host successful${NC}"
    else
        echo -e "${RED}❌ Database access from host failed${NC}"
        return 1
    fi
    
    echo ""
}

# Function to test network connectivity
test_network_connectivity() {
    echo -e "${BLUE}🌐 Testing Network Connectivity${NC}"
    echo -e "${BLUE}==============================${NC}"
    
    # Test port connectivity
    echo -e "${YELLOW}🔌 Testing port connectivity...${NC}"
    if nc -z "${DB_HOST}" "${DB_PORT}" 2>/dev/null; then
        echo -e "${GREEN}✅ Port ${DB_PORT} is accessible on ${DB_HOST}${NC}"
    else
        echo -e "${RED}❌ Port ${DB_PORT} is not accessible on ${DB_HOST}${NC}"
        echo -e "${YELLOW}  This might be expected if the database is not running or firewall is blocking${NC}"
    fi
    
    # Test Docker network
    echo -e "${YELLOW}🐳 Testing Docker network...${NC}"
    if docker network ls | grep -q "app-network"; then
        echo -e "${GREEN}✅ Docker network 'app-network' exists${NC}"
        
        # Show network details
        echo -e "${YELLOW}📊 Network details:${NC}"
        docker network inspect app-network --format='{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{end}}' 2>/dev/null || echo "  No containers in network"
    else
        echo -e "${YELLOW}⚠️  Docker network 'app-network' not found${NC}"
    fi
    
    echo ""
}

# Function to test user permissions
test_user_permissions() {
    echo -e "${BLUE}🔐 Testing User Permissions${NC}"
    echo -e "${BLUE}==========================${NC}"
    
    if ! check_container_running; then
        echo -e "${RED}❌ MariaDB container is not running${NC}"
        return 1
    fi
    
    # Test root permissions
    echo -e "${YELLOW}🔑 Testing root permissions...${NC}"
    if docker exec filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "SHOW GRANTS FOR 'root'@'localhost';" 2>/dev/null; then
        echo -e "${GREEN}✅ Root permissions retrieved successfully${NC}"
    else
        echo -e "${RED}❌ Failed to retrieve root permissions${NC}"
    fi
    
    # Test filewallball user permissions
    echo -e "${YELLOW}👤 Testing filewallball user permissions...${NC}"
    if docker exec filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "SHOW GRANTS FOR '${DB_USER}'@'%';" 2>/dev/null; then
        echo -e "${GREEN}✅ FileWallBall user permissions retrieved successfully${NC}"
    else
        echo -e "${RED}❌ Failed to retrieve FileWallBall user permissions${NC}"
    fi
    
    # Test filewallball user localhost permissions
    echo -e "${YELLOW}🏠 Testing filewallball user localhost permissions...${NC}"
    if docker exec filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "SHOW GRANTS FOR '${DB_USER}'@'localhost';" 2>/dev/null; then
        echo -e "${GREEN}✅ FileWallBall user localhost permissions retrieved successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  FileWallBall user localhost permissions not found (this might be expected)${NC}"
    fi
    
    echo ""
}

# Function to show connection examples
show_connection_examples() {
    echo -e "${BLUE}📚 Connection Examples${NC}"
    echo -e "${BLUE}====================${NC}"
    echo ""
    
    echo -e "${YELLOW}🔗 From Host Machine:${NC}"
    echo "  # Root connection"
    echo "  mysql -h ${DB_HOST} -P ${DB_PORT} -u root -p${DB_ROOT_PASSWORD}"
    echo ""
    echo "  # FileWallBall user connection"
    echo "  mysql -h ${DB_HOST} -P ${DB_PORT} -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME}"
    echo ""
    
    echo -e "${YELLOW}🐳 From Docker Container:${NC}"
    echo "  # Root connection"
    echo "  docker exec -it filewallball-mariadb mysql -u root -p${DB_ROOT_PASSWORD}"
    echo ""
    echo "  # FileWallBall user connection"
    echo "  docker exec -it filewallball-mariadb mysql -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME}"
    echo ""
    
    echo -e "${YELLOW}🔧 From Application:${NC}"
    echo "  # Connection string"
    echo "  mysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    echo ""
    echo "  # Environment variables"
    echo "  DB_HOST=${DB_HOST}"
    echo "  DB_PORT=${DB_PORT}"
    echo "  DB_NAME=${DB_NAME}"
    echo "  DB_USER=${DB_USER}"
    echo "  DB_PASSWORD=${DB_PASSWORD}"
    echo ""
}

# Function to run all tests
run_all_tests() {
    echo -e "${BLUE}🚀 Running All Database Connection Tests${NC}"
    echo ""
    
    local all_passed=true
    
    # Test container connections
    if test_container_connections; then
        echo -e "${GREEN}✅ Container connection tests passed${NC}"
    else
        echo -e "${RED}❌ Container connection tests failed${NC}"
        all_passed=false
    fi
    
    # Test host connections
    if test_host_connections; then
        echo -e "${GREEN}✅ Host connection tests passed${NC}"
    else
        echo -e "${RED}❌ Host connection tests failed${NC}"
        all_passed=false
    fi
    
    # Test network connectivity
    test_network_connectivity
    
    # Test user permissions
    if test_user_permissions; then
        echo -e "${GREEN}✅ User permission tests passed${NC}"
    else
        echo -e "${RED}❌ User permission tests failed${NC}"
        all_passed=false
    fi
    
    # Show results
    echo -e "${BLUE}📊 Test Results Summary${NC}"
    echo -e "${BLUE}=====================${NC}"
    
    if [ "$all_passed" = true ]; then
        echo -e "${GREEN}🎉 All critical tests passed!${NC}"
        echo -e "${GREEN}✅ Database is ready for use${NC}"
    else
        echo -e "${RED}⚠️  Some tests failed${NC}"
        echo -e "${YELLOW}Please review the errors above and fix any issues${NC}"
    fi
    
    echo ""
}

# Function to show help
show_help() {
    echo -e "${BLUE}FileWallBall Database Connection Test Script${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h           Show this help message"
    echo "  --container-only     Only test container connections"
    echo "  --host-only          Only test host connections"
    echo "  --network-only       Only test network connectivity"
    echo "  --permissions-only   Only test user permissions"
    echo "  --examples           Show connection examples"
    echo ""
    echo "Environment Variables:"
    echo "  DB_ROOT_PASSWORD     Root password for MariaDB"
    echo "  DB_NAME              Database name"
    echo "  DB_USER              FileWallBall user name"
    echo "  DB_PASSWORD          FileWallBall user password"
    echo "  DB_PORT              Database port"
    echo "  DB_HOST              Database host"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 --container-only   # Test only container connections"
    echo "  $0 --examples         # Show connection examples"
    echo ""
}

# Main execution
main() {
    case "${1:-}" in
        --help|-h)
            show_help
            ;;
        --container-only)
            test_container_connections
            ;;
        --host-only)
            test_host_connections
            ;;
        --network-only)
            test_network_connectivity
            ;;
        --permissions-only)
            test_user_permissions
            ;;
        --examples)
            show_connection_examples
            ;;
        "")
            run_all_tests
            show_connection_examples
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
