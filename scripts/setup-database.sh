#!/bin/bash

# FileWallBall Database Setup Script
# This script sets up the database with proper root password and remote access for filewallball user

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

echo -e "${BLUE}🚀 FileWallBall Database Setup Script${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Root Password: ${DB_ROOT_PASSWORD}"
echo "  Database Name: ${DB_NAME}"
echo "  User: ${DB_USER}"
echo "  User Password: ${DB_PASSWORD}"
echo "  Port: ${DB_PORT}"
echo "  Host: ${DB_HOST}"
echo ""

# Function to check if MariaDB is running
check_mariadb_running() {
    if docker ps | grep -q "filewallball-mariadb"; then
        return 0
    else
        return 1
    fi
}

# Function to start MariaDB if not running
start_mariadb() {
    echo -e "${YELLOW}🔧 Starting MariaDB container...${NC}"
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d mariadb
    elif [ -f "docker-compose.dev.yml" ]; then
        docker-compose -f docker-compose.dev.yml up -d mariadb
    elif [ -f "docker-compose.prod.yml" ]; then
        docker-compose -f docker-compose.prod.yml up -d mariadb
    else
        echo -e "${RED}❌ No docker-compose file found!${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}⏳ Waiting for MariaDB to be ready...${NC}"
    sleep 30
    
    # Wait for MariaDB to be healthy
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec filewallball-mariadb mysqladmin ping -h localhost -u root -p"${DB_ROOT_PASSWORD}" --silent; then
            echo -e "${GREEN}✅ MariaDB is ready!${NC}"
            break
        fi
        
        echo -e "${YELLOW}⏳ Attempt ${attempt}/${max_attempts}: Waiting for MariaDB...${NC}"
        sleep 10
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo -e "${RED}❌ MariaDB failed to start within expected time${NC}"
        exit 1
    fi
}

# Function to setup database
setup_database() {
    echo -e "${YELLOW}🔧 Setting up database...${NC}"
    
    # Create SQL script for database setup
    cat > /tmp/setup_db.sql << EOF
-- FileWallBall Database Setup Script
-- This script sets up the database with proper permissions

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE ${DB_NAME};

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL UNIQUE,
    project_key VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_project_key (project_key),
    INDEX idx_project_name (project_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create files table
CREATE TABLE IF NOT EXISTS files (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    file_uuid VARCHAR(36) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_extension VARCHAR(20) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64),
    storage_path VARCHAR(500) NOT NULL,
    file_category_id SMALLINT,
    owner_id INT,
    project_key_id INT,
    is_public BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_file_uuid (file_uuid),
    INDEX idx_original_filename (original_filename),
    INDEX idx_file_extension (file_extension),
    INDEX idx_mime_type (mime_type),
    INDEX idx_file_size (file_size),
    INDEX idx_file_hash (file_hash),
    INDEX idx_is_deleted (is_deleted),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create project_files table
CREATE TABLE IF NOT EXISTS project_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    file_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES files(file_uuid) ON DELETE CASCADE,
    UNIQUE KEY unique_project_file (project_id, file_id),
    INDEX idx_project_id (project_id),
    INDEX idx_file_id (file_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default project
INSERT IGNORE INTO projects (project_name, project_key) VALUES 
('default', 'default-project-key-12345');

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_files_created_at_desc ON files(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_files_original_filename_asc ON files(original_filename ASC);
CREATE INDEX IF NOT EXISTS idx_files_file_size_asc ON files(file_size ASC);

-- Grant permissions to filewallball user with remote access
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';

-- Grant additional permissions for backup and maintenance
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER ON *.* TO '${DB_USER}'@'%';
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER ON *.* TO '${DB_USER}'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;

-- Show current users and their hosts
SELECT User, Host FROM mysql.user WHERE User IN ('root', '${DB_USER}');
EOF

    # Execute the SQL script
    echo -e "${YELLOW}📝 Executing database setup script...${NC}"
    docker exec -i filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" < /tmp/setup_db.sql
    
    # Clean up temporary file
    rm -f /tmp/setup_db.sql
    
    echo -e "${GREEN}✅ Database setup completed!${NC}"
}

# Function to test database connections
test_connections() {
    echo -e "${YELLOW}🧪 Testing database connections...${NC}"
    
    # Test root connection
    echo -e "${BLUE}🔑 Testing root connection...${NC}"
    if docker exec filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "SELECT 'Root connection successful' as status;" 2>/dev/null; then
        echo -e "${GREEN}✅ Root connection successful${NC}"
    else
        echo -e "${RED}❌ Root connection failed${NC}"
        return 1
    fi
    
    # Test filewallball user connection
    echo -e "${BLUE}👤 Testing filewallball user connection...${NC}"
    if docker exec filewallball-mariadb mysql -u "${DB_USER}" -p"${DB_PASSWORD}" -e "SELECT 'FileWallBall user connection successful' as status;" 2>/dev/null; then
        echo -e "${GREEN}✅ FileWallBall user connection successful${NC}"
    else
        echo -e "${RED}❌ FileWallBall user connection failed${NC}"
        return 1
    fi
    
    # Test external connection (if host is not localhost)
    if [ "$DB_HOST" != "localhost" ] && [ "$DB_HOST" != "127.0.0.1" ]; then
        echo -e "${BLUE}🌐 Testing external connection from ${DB_HOST}...${NC}"
        if mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASSWORD}" -e "SELECT 'External connection successful' as status;" 2>/dev/null; then
            echo -e "${GREEN}✅ External connection successful${NC}"
        else
            echo -e "${YELLOW}⚠️  External connection failed (this might be expected if not running from ${DB_HOST})${NC}"
        fi
    fi
    
    echo -e "${GREEN}✅ All connection tests completed!${NC}"
}

# Function to show connection information
show_connection_info() {
    echo -e "${BLUE}📊 Database Connection Information${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    echo -e "${YELLOW}🔑 Root Access:${NC}"
    echo "  Host: ${DB_HOST}"
    echo "  Port: ${DB_PORT}"
    echo "  User: root"
    echo "  Password: ${DB_ROOT_PASSWORD}"
    echo ""
    echo -e "${YELLOW}👤 FileWallBall User Access:${NC}"
    echo "  Host: ${DB_HOST}"
    echo "  Port: ${DB_PORT}"
    echo "  Database: ${DB_NAME}"
    echo "  User: ${DB_USER}"
    echo "  Password: ${DB_PASSWORD}"
    echo ""
    echo -e "${YELLOW}🔗 Connection Examples:${NC}"
    echo "  # Root connection (from host)"
    echo "  mysql -h ${DB_HOST} -P ${DB_PORT} -u root -p${DB_ROOT_PASSWORD}"
    echo ""
    echo "  # FileWallBall user connection (from host)"
    echo "  mysql -h ${DB_HOST} -P ${DB_PORT} -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME}"
    echo ""
    echo "  # Root connection (from container)"
    echo "  docker exec -it filewallball-mariadb mysql -u root -p${DB_ROOT_PASSWORD}"
    echo ""
    echo "  # FileWallBall user connection (from container)"
    echo "  docker exec -it filewallball-mariadb mysql -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME}"
    echo ""
    echo -e "${YELLOW}🌐 Remote Access:${NC}"
    echo "  The filewallball user has been configured to accept connections from any host (%)"
    echo "  This allows external applications to connect to the database"
    echo ""
}

# Function to create environment file
create_env_file() {
    echo -e "${YELLOW}📝 Creating .env file...${NC}"
    
    cat > .env << EOF
# FileWallBall Environment Variables
# Generated by setup-database.sh

# Database Configuration
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_PORT=${DB_PORT}

# Application Configuration
APP_PORT=18000
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development

# File Storage Configuration
HOST_UPLOAD_DIR=./uploads
STORAGE_TYPE=local
MAX_FILE_SIZE=104857600

# Redis Configuration (Optional)
REDIS_HOST=localhost
REDIS_PORT=16379
REDIS_PASSWORD=
REDIS_DB=0

# Nginx Configuration (Optional)
NGINX_PORT=80
NGINX_SSL_PORT=443

# Backup Configuration
BACKUP_RETENTION_DAYS=7
BACKUP_SCHEDULE="0 2 * * *"

# Security Configuration
SECRET_KEY=your_super_secret_key_change_this_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

    echo -e "${GREEN}✅ .env file created successfully!${NC}"
    echo -e "${YELLOW}⚠️  Please review and modify the .env file as needed${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Starting FileWallBall Database Setup...${NC}"
    echo ""
    
    # Check if MariaDB is running
    if ! check_mariadb_running; then
        echo -e "${YELLOW}⚠️  MariaDB container is not running${NC}"
        start_mariadb
    else
        echo -e "${GREEN}✅ MariaDB container is already running${NC}"
    fi
    
    # Setup database
    setup_database
    
    # Test connections
    test_connections
    
    # Show connection information
    show_connection_info
    
    # Create environment file if it doesn't exist
    if [ ! -f ".env" ]; then
        create_env_file
    else
        echo -e "${YELLOW}⚠️  .env file already exists, skipping creation${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Database setup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📚 Next steps:${NC}"
    echo "  1. Review the connection information above"
    echo "  2. Test connections from your application"
    echo "  3. Update your application configuration if needed"
    echo "  4. Run 'docker-compose up -d' to start all services"
    echo ""
}

# Check if script is run with arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo -e "${BLUE}FileWallBall Database Setup Script${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --test-only     Only test existing connections"
    echo "  --setup-only    Only setup database (skip tests)"
    echo ""
    echo "Environment Variables:"
    echo "  DB_ROOT_PASSWORD    Root password for MariaDB"
    echo "  DB_NAME            Database name"
    echo "  DB_USER            FileWallBall user name"
    echo "  DB_PASSWORD        FileWallBall user password"
    echo "  DB_PORT            Database port"
    echo "  DB_HOST            Database host"
    echo ""
    exit 0
elif [ "$1" = "--test-only" ]; then
    echo -e "${BLUE}🧪 Running connection tests only...${NC}"
    if check_mariadb_running; then
        test_connections
        show_connection_info
    else
        echo -e "${RED}❌ MariaDB container is not running${NC}"
        exit 1
    fi
elif [ "$1" = "--setup-only" ]; then
    echo -e "${BLUE}🔧 Running database setup only...${NC}"
    if check_mariadb_running; then
        setup_database
        show_connection_info
    else
        echo -e "${RED}❌ MariaDB container is not running${NC}"
        exit 1
    fi
else
    # Run main setup
    main
fi
