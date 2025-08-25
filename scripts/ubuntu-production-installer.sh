#!/bin/bash

# FileWallBall Ubuntu Production 환경 자동 설치 스크립트
# Ubuntu 18.04, 20.04, 22.04, 24.04 LTS 지원

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="FileWallBall"
MIN_RAM_GB=2
MIN_DISK_GB=10
SUPPORTED_UBUNTU_VERSIONS=("18.04" "20.04" "22.04" "24.04")

# Logging
LOG_FILE="/tmp/filewallball-install.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "${BLUE}🚀 FileWallBall Ubuntu Production 환경 자동 설치 스크립트${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo "설치 로그: $LOG_FILE"
echo ""

# Function to log messages
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        echo -e "${RED}❌ 이 스크립트는 root 사용자로 실행하면 안됩니다.${NC}"
        echo -e "${YELLOW}일반 사용자로 실행하고 sudo 권한을 사용하세요.${NC}"
        exit 1
    fi
}

# Function to check sudo privileges
check_sudo() {
    echo -e "${YELLOW}🔐 sudo 권한 확인 중...${NC}"
    if ! sudo -n true 2>/dev/null; then
        echo -e "${YELLOW}sudo 비밀번호를 입력해주세요:${NC}"
        sudo -v
    fi
    echo -e "${GREEN}✅ sudo 권한 확인 완료${NC}"
}

# Function to check Ubuntu version
check_ubuntu_version() {
    echo -e "${BLUE}🔍 Ubuntu 버전 확인 중...${NC}"
    
    # Check if running on Ubuntu
    if ! command -v lsb_release &> /dev/null; then
        echo -e "${RED}❌ lsb_release 명령어를 찾을 수 없습니다.${NC}"
        echo -e "${YELLOW}이 스크립트는 Ubuntu 환경에서만 실행할 수 있습니다.${NC}"
        exit 1
    fi
    
    local ubuntu_version=$(lsb_release -rs)
    local ubuntu_codename=$(lsb_release -cs)
    
    echo -e "${CYAN}📋 현재 Ubuntu 버전: $ubuntu_version ($ubuntu_codename)${NC}"
    
    # Check if version is supported
    local supported=false
    for version in "${SUPPORTED_UBUNTU_VERSIONS[@]}"; do
        if [[ "$ubuntu_version" == "$version" ]]; then
            supported=true
            break
        fi
    done
    
    if [[ "$supported" == true ]]; then
        echo -e "${GREEN}✅ Ubuntu $ubuntu_version 지원됨${NC}"
        log_message "INFO" "Ubuntu $ubuntu_version ($ubuntu_codename) 지원 확인됨"
    else
        echo -e "${YELLOW}⚠️  Ubuntu $ubuntu_version은 공식적으로 지원되지 않습니다.${NC}"
        echo -e "${YELLOW}계속 진행하시겠습니까? (y/N):${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${RED}설치를 중단합니다.${NC}"
            exit 1
        fi
        echo -e "${YELLOW}⚠️  지원되지 않는 버전에서 계속 진행합니다.${NC}"
        log_message "WARNING" "지원되지 않는 Ubuntu 버전 $ubuntu_version에서 설치 진행"
    fi
}

# Function to check system requirements
check_system_requirements() {
    echo -e "${BLUE}🔍 시스템 요구사항 확인 중...${NC}"
    
    # Check RAM
    local total_ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_ram_mb=$((total_ram_kb / 1024))
    local total_ram_gb=$((total_ram_mb / 1024))
    
    echo -e "${CYAN}📊 시스템 메모리: ${total_ram_mb}MB (${total_ram_gb}GB)${NC}"
    
    if [[ $total_ram_mb -lt $((MIN_RAM_GB * 1024)) ]]; then
        echo -e "${RED}❌ 최소 ${MIN_RAM_GB}GB RAM이 필요합니다. 현재: ${total_ram_gb}GB${NC}"
        log_message "ERROR" "RAM 부족: ${total_ram_gb}GB < ${MIN_RAM_GB}GB"
        exit 1
    fi
    
    # Check available disk space
    local available_disk_kb=$(df / | awk 'NR==2{print $4}')
    local available_disk_mb=$((available_disk_kb / 1024))
    local available_disk_gb=$((available_disk_mb / 1024))
    
    echo -e "${CYAN}📊 사용 가능한 디스크 공간: ${available_disk_mb}MB (${available_disk_gb}GB)${NC}"
    
    if [[ $available_disk_mb -lt $((MIN_DISK_GB * 1024)) ]]; then
        echo -e "${RED}❌ 최소 ${MIN_DISK_GB}GB 디스크 공간이 필요합니다. 현재: ${available_disk_gb}GB${NC}"
        log_message "ERROR" "디스크 공간 부족: ${available_disk_gb}GB < ${MIN_DISK_GB}GB"
        exit 1
    fi
    
    # Check CPU cores
    local cpu_cores=$(nproc)
    echo -e "${CYAN}📊 CPU 코어 수: $cpu_cores${NC}"
    
    if [[ $cpu_cores -lt 1 ]]; then
        echo -e "${RED}❌ 최소 1개 CPU 코어가 필요합니다.${NC}"
        log_message "ERROR" "CPU 코어 부족: $cpu_cores < 1"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 시스템 요구사항 충족${NC}"
    log_message "INFO" "시스템 요구사항 확인 완료: RAM ${total_ram_gb}GB, 디스크 ${available_disk_gb}GB, CPU ${cpu_cores}코어"
}

# Function to check network connectivity
check_network_connectivity() {
    echo -e "${BLUE}🌐 네트워크 연결 확인 중...${NC}"
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 &> /dev/null; then
        echo -e "${GREEN}✅ 인터넷 연결 확인됨${NC}"
        log_message "INFO" "인터넷 연결 확인됨"
    else
        echo -e "${RED}❌ 인터넷 연결을 확인할 수 없습니다.${NC}"
        echo -e "${YELLOW}네트워크 설정을 확인하고 다시 시도하세요.${NC}"
        log_message "ERROR" "인터넷 연결 실패"
        exit 1
    fi
    
    # Check DNS resolution
    if nslookup google.com &> /dev/null; then
        echo -e "${GREEN}✅ DNS 해석 확인됨${NC}"
        log_message "INFO" "DNS 해석 확인됨"
    else
        echo -e "${YELLOW}⚠️  DNS 해석에 문제가 있을 수 있습니다.${NC}"
        log_message "WARNING" "DNS 해석 문제 가능성"
    fi
    
    # Check required ports availability
    local required_ports=(8000 13306 16379)
    local port_available=true
    
    for port in "${required_ports[@]}"; do
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            echo -e "${YELLOW}⚠️  포트 $port가 이미 사용 중입니다.${NC}"
            port_available=false
            log_message "WARNING" "포트 $port 이미 사용 중"
        fi
    done
    
    if [[ "$port_available" == true ]]; then
        echo -e "${GREEN}✅ 필요한 포트들이 사용 가능합니다${NC}"
        log_message "INFO" "필요한 포트들 사용 가능 확인"
    else
        echo -e "${YELLOW}⚠️  일부 포트가 이미 사용 중입니다.${NC}"
        echo -e "${YELLOW}설치를 계속 진행하시겠습니까? (y/N):${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${RED}설치를 중단합니다.${NC}"
            exit 1
        fi
        echo -e "${YELLOW}⚠️  포트 충돌 가능성을 인지하고 계속 진행합니다.${NC}"
        log_message "WARNING" "포트 충돌 가능성을 인지하고 설치 진행"
    fi
}

# Function to check existing installations
check_existing_installations() {
    echo -e "${BLUE}🔍 기존 설치 확인 중...${NC}"
    
    local existing_installations=()
    
    # Check Docker
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version)
        echo -e "${CYAN}🐳 Docker: $docker_version${NC}"
        existing_installations+=("Docker")
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version)
        echo -e "${CYAN}🐙 Docker Compose: $compose_version${NC}"
        existing_installations+=("Docker Compose")
    fi
    
    # Check if FileWallBall is already running
    if docker ps --format "table {{.Names}}" 2>/dev/null | grep -q "filewallball"; then
        echo -e "${YELLOW}⚠️  FileWallBall 컨테이너가 이미 실행 중입니다.${NC}"
        existing_installations+=("FileWallBall")
    fi
    
    # Check if ports are in use by FileWallBall
    if netstat -tlnp 2>/dev/null | grep -q ":8000.*filewallball"; then
        echo -e "${YELLOW}⚠️  FileWallBall이 포트 8000에서 실행 중입니다.${NC}"
        existing_installations+=("FileWallBall Port 8000")
    fi
    
    if [[ ${#existing_installations[@]} -gt 0 ]]; then
        echo -e "${YELLOW}📋 발견된 기존 설치:${NC}"
        for item in "${existing_installations[@]}"; do
            echo -e "${YELLOW}  - $item${NC}"
        done
        
        echo -e "${YELLOW}기존 설치를 업그레이드하거나 새로 설치하시겠습니까? (u/N):${NC}"
        read -r response
        if [[ "$response" =~ ^[Uu]$ ]]; then
            echo -e "${YELLOW}⚠️  기존 설치를 업그레이드합니다.${NC}"
            log_message "INFO" "기존 설치 업그레이드 모드로 진행"
        else
            echo -e "${YELLOW}⚠️  새로 설치합니다. 기존 데이터는 보존됩니다.${NC}"
            log_message "INFO" "새로 설치 모드로 진행"
        fi
    else
        echo -e "${GREEN}✅ 기존 설치가 발견되지 않았습니다. 새로 설치합니다.${NC}"
        log_message "INFO" "새로 설치 모드로 진행"
    fi
}

# Function to show system information summary
show_system_summary() {
    echo -e "${BLUE}📊 시스템 정보 요약${NC}"
    echo -e "${BLUE}==================${NC}"
    
    local ubuntu_version=$(lsb_release -rs)
    local ubuntu_codename=$(lsb_release -cs)
    local total_ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_ram_gb=$((total_ram_kb / 1024 / 1024))
    local available_disk_kb=$(df / | awk 'NR==2{print $4}')
    local available_disk_gb=$((available_disk_kb / 1024 / 1024))
    local cpu_cores=$(nproc)
    
    echo -e "${CYAN}운영체제:${NC} Ubuntu $ubuntu_version ($ubuntu_codename)"
    echo -e "${CYAN}메모리:${NC} ${total_ram_gb}GB"
    echo -e "${CYAN}디스크 공간:${NC} ${available_disk_gb}GB"
    echo -e "${CYAN}CPU 코어:${NC} $cpu_cores"
    echo -e "${CYAN}사용자:${NC} $USER"
    echo -e "${CYAN}sudo 권한:${NC} $(sudo -n true 2>/dev/null && echo "사용 가능" || echo "확인 필요")"
    echo ""
    
    log_message "INFO" "시스템 정보 요약: Ubuntu $ubuntu_version, RAM ${total_ram_gb}GB, 디스크 ${available_disk_gb}GB, CPU ${cpu_cores}코어"
}

# Function to confirm installation
confirm_installation() {
    echo -e "${BLUE}📋 설치 계획${NC}"
    echo -e "${BLUE}==========${NC}"
    echo -e "${CYAN}1.${NC} Ubuntu 환경 검증"
    echo -e "${CYAN}2.${NC} Docker 및 Docker Compose 설치"
    echo -e "${CYAN}3.${NC} FileWallBall 소스 코드 다운로드"
    echo -e "${CYAN}4.${NC} 데이터베이스 설정 (MariaDB + Redis)"
    echo -e "${CYAN}5.${NC} Production 환경 설정"
    echo -e "${CYAN}6.${NC} 서비스 시작 및 검증"
    echo -e "${CYAN}7.${NC} 설치 가이드 생성"
    echo ""
    
    echo -e "${YELLOW}⚠️  이 설치 과정은 다음을 수행합니다:${NC}"
    echo -e "${YELLOW}  - Docker 및 Docker Compose 설치${NC}"
    echo -e "${YELLOW}  - 시스템 패키지 업데이트${NC}"
    echo -e "${YELLOW}  - 방화벽 설정 변경${NC}"
    echo -e "${YELLOW}  - 서비스 자동 시작 설정${NC}"
    echo ""
    
    echo -e "${YELLOW}설치를 계속 진행하시겠습니까? (y/N):${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${RED}설치를 중단합니다.${NC}"
        log_message "INFO" "사용자에 의해 설치 중단"
        exit 0
    fi
    
    echo -e "${GREEN}✅ 설치를 시작합니다...${NC}"
    log_message "INFO" "사용자 확인 후 설치 시작"
}

# Function to install Docker
install_docker() {
    echo -e "${BLUE}🐳 Docker 설치 중...${NC}"
    
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version)
        echo -e "${GREEN}✅ Docker 이미 설치됨: $docker_version${NC}"
        log_message "INFO" "Docker 이미 설치됨: $docker_version"
        return 0
    fi
    
    echo -e "${YELLOW}📦 Docker 설치를 시작합니다...${NC}"
    
    # Update package list
    echo -e "${CYAN}📋 패키지 목록 업데이트 중...${NC}"
    sudo apt-get update
    
    # Install required packages
    echo -e "${CYAN}📦 필수 패키지 설치 중...${NC}"
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common
    
    # Add Docker's official GPG key
    echo -e "${CYAN}🔑 Docker GPG 키 추가 중...${NC}"
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo -e "${CYAN}📦 Docker 저장소 추가 중...${NC}"
    local ubuntu_codename=$(lsb_release -cs)
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $ubuntu_codename stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package list again
    sudo apt-get update
    
    # Install Docker
    echo -e "${CYAN}🐳 Docker 설치 중...${NC}"
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add user to docker group
    echo -e "${CYAN}👤 사용자를 docker 그룹에 추가 중...${NC}"
    sudo usermod -aG docker $USER
    
    # Start and enable Docker service
    echo -e "${CYAN}🚀 Docker 서비스 시작 중...${NC}"
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # Verify installation
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version)
        echo -e "${GREEN}✅ Docker 설치 완료: $docker_version${NC}"
        log_message "INFO" "Docker 설치 완료: $docker_version"
        
        # Show docker group information
        echo -e "${YELLOW}⚠️  사용자를 docker 그룹에 추가했습니다.${NC}"
        echo -e "${YELLOW}변경사항을 적용하려면 로그아웃 후 다시 로그인하거나 다음 명령어를 실행하세요:${NC}"
        echo -e "${CYAN}  newgrp docker${NC}"
    else
        echo -e "${RED}❌ Docker 설치 실패${NC}"
        log_message "ERROR" "Docker 설치 실패"
        exit 1
    fi
}

# Function to install Docker Compose
install_docker_compose() {
    echo -e "${BLUE}🐙 Docker Compose 설치 중...${NC}"
    
    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version)
        echo -e "${GREEN}✅ Docker Compose 이미 설치됨: $compose_version${NC}"
        log_message "INFO" "Docker Compose 이미 설치됨: $compose_version"
        return 0
    fi
    
    echo -e "${YELLOW}📦 Docker Compose 설치를 시작합니다...${NC}"
    
    # Install Docker Compose
    echo -e "${CYAN}🐙 Docker Compose 다운로드 중...${NC}"
    local compose_version="v2.24.5"
    sudo curl -L "https://github.com/docker/compose/releases/download/$compose_version/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # Make it executable
    echo -e "${CYAN}🔐 실행 권한 설정 중...${NC}"
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Verify installation
    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version)
        echo -e "${GREEN}✅ Docker Compose 설치 완료: $compose_version${NC}"
        log_message "INFO" "Docker Compose 설치 완료: $compose_version"
    else
        echo -e "${RED}❌ Docker Compose 설치 실패${NC}"
        log_message "ERROR" "Docker Compose 설치 실패"
        exit 1
    fi
}

# Function to verify Docker installation
verify_docker_installation() {
    echo -e "${BLUE}🔍 Docker 설치 검증 중...${NC}"
    
    # Test Docker
    if docker --version &> /dev/null; then
        echo -e "${GREEN}✅ Docker 명령어 실행 가능${NC}"
    else
        echo -e "${RED}❌ Docker 명령어 실행 실패${NC}"
        return 1
    fi
    
    # Test Docker Compose
    if docker-compose --version &> /dev/null; then
        echo -e "${GREEN}✅ Docker Compose 명령어 실행 가능${NC}"
    else
        echo -e "${RED}❌ Docker Compose 명령어 실행 실패${NC}"
        return 1
    fi
    
    # Test Docker daemon
    if sudo docker info &> /dev/null; then
        echo -e "${GREEN}✅ Docker 데몬 정상 동작${NC}"
    else
        echo -e "${RED}❌ Docker 데몬 동작 실패${NC}"
        return 1
    fi
    
    # Test Docker Compose
    if docker-compose --help &> /dev/null; then
        echo -e "${GREEN}✅ Docker Compose 정상 동작${NC}"
    else
        echo -e "${RED}❌ Docker Compose 동작 실패${NC}"
        return 1
    fi
    
    echo -e "${GREEN}🎉 Docker 설치 검증 완료!${NC}"
    log_message "INFO" "Docker 설치 검증 완료"
}

# Function to download FileWallBall source code
download_filewallball_source() {
    echo -e "${BLUE}📥 FileWallBall 소스 코드 다운로드 중...${NC}"
    
    local target_dir="filewallball"
    local repo_url="https://github.com/pathcosmos/dy_gh_filewallball.git"
    
    if [[ -d "$target_dir" ]]; then
        echo -e "${YELLOW}⚠️  FileWallBall 소스 코드가 이미 존재합니다.${NC}"
        echo -e "${YELLOW}기존 소스를 업데이트하시겠습니까? (y/N):${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}📥 기존 소스 업데이트 중...${NC}"
            cd "$target_dir"
            git fetch origin
            git reset --hard origin/main
            cd ..
            echo -e "${GREEN}✅ 소스 코드 업데이트 완료${NC}"
            log_message "INFO" "FileWallBall 소스 코드 업데이트 완료"
        else
            echo -e "${CYAN}📁 기존 소스 코드를 사용합니다.${NC}"
            log_message "INFO" "기존 FileWallBall 소스 코드 사용"
        fi
    else
        echo -e "${CYAN}📥 FileWallBall 소스 코드를 다운로드합니다...${NC}"
        
        # Check if git is available
        if ! command -v git &> /dev/null; then
            echo -e "${YELLOW}📦 Git 설치 중...${NC}"
            sudo apt-get update
            sudo apt-get install -y git
        fi
        
        # Clone repository
        if git clone "$repo_url" "$target_dir"; then
            echo -e "${GREEN}✅ FileWallBall 소스 코드 다운로드 완료${NC}"
            log_message "INFO" "FileWallBall 소스 코드 다운로드 완료"
        else
            echo -e "${RED}❌ FileWallBall 소스 코드 다운로드 실패${NC}"
            log_message "ERROR" "FileWallBall 소스 코드 다운로드 실패"
            exit 1
        fi
    fi
    
    # Navigate to project directory
    cd "$target_dir"
    echo -e "${CYAN}📁 프로젝트 디렉토리: $(pwd)${NC}"
}

# Function to create production environment file
create_production_env() {
    echo -e "${BLUE}⚙️  Production 환경 설정 파일 생성 중...${NC}"
    
    local env_file=".env.prod"
    
    if [[ -f "$env_file" ]]; then
        echo -e "${YELLOW}⚠️  $env_file 파일이 이미 존재합니다.${NC}"
        echo -e "${YELLOW}기존 파일을 덮어쓰시겠습니까? (y/N):${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}📁 기존 환경 설정 파일을 사용합니다.${NC}"
            return 0
        fi
    fi
    
    # Generate secure passwords
    local root_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    local user_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    local master_key=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    
    echo -e "${CYAN}🔐 보안 비밀번호 생성 중...${NC}"
    
    # Create production environment file
    cat > "$env_file" << EOF
# FileWallBall Production Environment Configuration
# Generated by Ubuntu Production Installer

# Database Configuration
DB_ROOT_PASSWORD=${root_password}
DB_NAME=filewallball_db
DB_USER=filewallball_user
DB_PASSWORD=${user_password}
DB_PORT=13306
DB_HOST=mariadb

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Application Configuration
APP_PORT=8000
DEBUG=false
LOG_LEVEL=WARNING
ENVIRONMENT=production
MASTER_KEY=${master_key}

# File Storage Configuration
HOST_UPLOAD_DIR=./uploads
STORAGE_TYPE=local
MAX_FILE_SIZE=104857600

# Security Configuration
SECRET_KEY=${master_key}
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Backup Configuration
BACKUP_RETENTION_DAYS=7
BACKUP_SCHEDULE="0 2 * * *"
EOF

    echo -e "${GREEN}✅ Production 환경 설정 파일 생성 완료${NC}"
    echo -e "${CYAN}📋 생성된 설정:${NC}"
    echo -e "${CYAN}  - DB Root Password: ${root_password}${NC}"
    echo -e "${CYAN}  - DB User Password: ${user_password}${NC}"
    echo -e "${CYAN}  - Master Key: ${master_key}${NC}"
    
    log_message "INFO" "Production 환경 설정 파일 생성 완료"
    
    # Save passwords to a secure file for reference
    cat > ".env.prod.passwords" << EOF
# FileWallBall Production Passwords
# IMPORTANT: Keep this file secure and delete after first use
DB_ROOT_PASSWORD=${root_password}
DB_USER_PASSWORD=${user_password}
MASTER_KEY=${master_key}
EOF
    
    chmod 600 ".env.prod.passwords"
    echo -e "${YELLOW}⚠️  비밀번호가 .env.prod.passwords 파일에 저장되었습니다.${NC}"
    echo -e "${YELLOW}보안을 위해 이 파일을 안전한 곳에 보관하고 필요시 삭제하세요.${NC}"
}

# Function to setup database integrated (calling existing setup-database.sh)
setup_database_integrated() {
    echo -e "${BLUE}🗄️  통합 데이터베이스 설정 시작...${NC}"
    
    # Check if setup-database.sh exists
    if [[ ! -f "scripts/setup-database.sh" ]]; then
        echo -e "${RED}❌ scripts/setup-database.sh 파일을 찾을 수 없습니다.${NC}"
        log_message "ERROR" "setup-database.sh 파일 없음"
        exit 1
    fi
    
    # Make script executable
    chmod +x scripts/setup-database.sh
    
    # Set environment variables for database setup
    export DB_ROOT_PASSWORD=$(grep DB_ROOT_PASSWORD .env.prod | cut -d'=' -f2)
    export DB_NAME=$(grep DB_NAME .env.prod | cut -d'=' -f2)
    export DB_USER=$(grep DB_USER .env.prod | cut -d'=' -f2)
    export DB_PASSWORD=$(grep DB_PASSWORD .env.prod | cut -d'=' -f2)
    export DB_PORT=$(grep DB_PORT .env.prod | cut -d'=' -f2)
    
    echo -e "${CYAN}📋 데이터베이스 설정 정보:${NC}"
    echo -e "${CYAN}  - Root Password: ${DB_ROOT_PASSWORD}${NC}"
    echo -e "${CYAN}  - Database: ${DB_NAME}${NC}"
    echo -e "${CYAN}  - User: ${DB_USER}${NC}"
    echo -e "${CYAN}  - Port: ${DB_PORT}${NC}"
    
    # Start MariaDB and Redis containers
    echo -e "${CYAN}🐳 MariaDB 및 Redis 컨테이너 시작 중...${NC}"
    if docker-compose -f docker-compose.prod.yml up -d mariadb redis; then
        echo -e "${GREEN}✅ MariaDB 및 Redis 컨테이너 시작 완료${NC}"
        log_message "INFO" "MariaDB 및 Redis 컨테이너 시작 완료"
    else
        echo -e "${RED}❌ MariaDB 및 Redis 컨테이너 시작 실패${NC}"
        log_message "ERROR" "MariaDB 및 Redis 컨테이너 시작 실패"
        exit 1
    fi
    
    # Wait for containers to be ready
    echo -e "${CYAN}⏳ 컨테이너 준비 대기 중...${NC}"
    sleep 30
    
    # Run database setup script
    echo -e "${CYAN}📝 데이터베이스 설정 스크립트 실행 중...${NC}"
    if ./scripts/setup-database.sh --setup-only; then
        echo -e "${GREEN}✅ 데이터베이스 설정 완료${NC}"
        log_message "INFO" "데이터베이스 설정 완료"
    else
        echo -e "${RED}❌ 데이터베이스 설정 실패${NC}"
        log_message "ERROR" "데이터베이스 설정 실패"
        exit 1
    fi
    
    # Test database connection
    echo -e "${CYAN}🧪 데이터베이스 연결 테스트 중...${NC}"
    if ./scripts/test-db-connection.sh --container-only; then
        echo -e "${GREEN}✅ 데이터베이스 연결 테스트 성공${NC}"
        log_message "INFO" "데이터베이스 연결 테스트 성공"
    else
        echo -e "${RED}❌ 데이터베이스 연결 테스트 실패${NC}"
        log_message "ERROR" "데이터베이스 연결 테스트 실패"
        exit 1
    fi
}

# Function to setup production environment
setup_production_environment() {
    echo -e "${BLUE}⚙️  FileWallBall 프로덕션 환경 설정 중...${NC}"
    
    # Create necessary directories
    echo -e "${CYAN}📁 필요한 디렉토리 생성 중...${NC}"
    local directories=("uploads" "logs" "backups" "ssl" "config")
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            echo -e "${GREEN}✅ 디렉토리 생성: $dir${NC}"
        else
            echo -e "${CYAN}📁 디렉토리 이미 존재: $dir${NC}"
        fi
    done
    
    # Set proper permissions
    echo -e "${CYAN}🔐 디렉토리 권한 설정 중...${NC}"
    chmod 755 uploads logs backups ssl config
    chmod 700 .env.prod .env.prod.passwords 2>/dev/null || true
    
    # Setup firewall (optional)
    setup_firewall
    
    # Setup SSL (optional)
    setup_ssl_optional
    
    # Create production configuration
    create_production_config
    
    echo -e "${GREEN}✅ 프로덕션 환경 설정 완료${NC}"
    log_message "INFO" "프로덕션 환경 설정 완료"
}

# Function to setup firewall
setup_firewall() {
    echo -e "${BLUE}🔥 방화벽 설정 중...${NC}"
    
    if command -v ufw &> /dev/null; then
        echo -e "${YELLOW}⚠️  UFW 방화벽이 활성화되어 있습니다.${NC}"
        echo -e "${YELLOW}FileWallBall 서비스를 위한 포트를 열시겠습니까? (y/N):${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}🔓 필요한 포트 열기 중...${NC}"
            
            # Allow SSH (port 22)
            sudo ufw allow 22/tcp
            echo -e "${GREEN}✅ SSH 포트 (22) 허용${NC}"
            
            # Allow FileWallBall API (port 8000)
            sudo ufw allow 8000/tcp
            echo -e "${GREEN}✅ FileWallBall API 포트 (8000) 허용${NC}"
            
            # Allow HTTP/HTTPS if needed
            echo -e "${YELLOW}HTTP (80) 및 HTTPS (443) 포트를 열시겠습니까? (y/N):${NC}"
            read -r http_response
            if [[ "$http_response" =~ ^[Yy]$ ]]; then
                sudo ufw allow 80/tcp
                sudo ufw allow 443/tcp
                echo -e "${GREEN}✅ HTTP (80) 및 HTTPS (443) 포트 허용${NC}"
            fi
            
            # Show firewall status
            echo -e "${CYAN}📊 방화벽 상태:${NC}"
            sudo ufw status numbered
            
            log_message "INFO" "방화벽 설정 완료"
        else
            echo -e "${YELLOW}⚠️  방화벽 설정을 건너뜁니다.${NC}"
            log_message "INFO" "방화벽 설정 건너뜀"
        fi
    else
        echo -e "${YELLOW}⚠️  UFW가 설치되지 않았습니다. 방화벽 설정을 건너뜁니다.${NC}"
        log_message "WARNING" "UFW 미설치로 방화벽 설정 건너뜀"
    fi
}

# Function to setup SSL (optional)
setup_ssl_optional() {
    echo -e "${BLUE}🔒 SSL 인증서 설정 (선택사항)${NC}"
    
    echo -e "${YELLOW}도메인이 있으면 입력하세요 (없으면 Enter):${NC}"
    read -r domain
    
    if [[ -n "$domain" ]]; then
        echo -e "${CYAN}🌐 도메인: $domain${NC}"
        
        # Check if certbot is available
        if command -v certbot &> /dev/null; then
            echo -e "${GREEN}✅ Certbot이 이미 설치되어 있습니다.${NC}"
        else
            echo -e "${YELLOW}📦 Certbot 설치 중...${NC}"
            sudo apt-get update
            sudo apt-get install -y certbot python3-certbot-nginx
            echo -e "${GREEN}✅ Certbot 설치 완료${NC}"
        fi
        
        echo -e "${CYAN}🔒 SSL 인증서 설정 가이드:${NC}"
        echo -e "${YELLOW}1. Nginx 설정 파일을 생성하세요:${NC}"
        echo -e "${CYAN}   sudo nano /etc/nginx/sites-available/$domain${NC}"
        echo -e "${YELLOW}2. SSL 인증서를 발급받으세요:${NC}"
        echo -e "${CYAN}   sudo certbot --nginx -d $domain${NC}"
        echo -e "${YELLOW}3. Nginx를 활성화하고 재시작하세요:${NC}"
        echo -e "${CYAN}   sudo ln -s /etc/nginx/sites-available/$domain /etc/nginx/sites-enabled/${NC}"
        echo -e "${CYAN}   sudo systemctl restart nginx${NC}"
        
        log_message "INFO" "SSL 설정 가이드 제공: $domain"
    else
        echo -e "${CYAN}📝 도메인이 없습니다. SSL 설정을 건너뜁니다.${NC}"
        log_message "INFO" "도메인 없음으로 SSL 설정 건너뜀"
    fi
}

# Function to create production configuration
create_production_config() {
    echo -e "${BLUE}⚙️  프로덕션 설정 파일 생성 중...${NC}"
    
    # Create production docker-compose override
    local compose_prod="docker-compose.prod.yml"
    
    if [[ ! -f "$compose_prod" ]]; then
        echo -e "${CYAN}📝 프로덕션 Docker Compose 파일 생성 중...${NC}"
        
        cat > "$compose_prod" << 'EOF'
version: '3.8'

services:
  app:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=WARNING
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  mariadb:
    environment:
      - MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
      - MYSQL_DATABASE=${DB_NAME}
      - MYSQL_USER=${DB_USER}
      - MYSQL_PASSWORD=${DB_PASSWORD}
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    restart: always

  redis:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
    restart: always

volumes:
  mariadb_data:
    driver: local
  redis_data:
    driver: local
  uploads_data:
    driver: local
  logs_data:
    driver: local
  backups_data:
    driver: local
EOF

        echo -e "${GREEN}✅ 프로덕션 Docker Compose 파일 생성 완료${NC}"
        log_message "INFO" "프로덕션 Docker Compose 파일 생성 완료"
    else
        echo -e "${CYAN}📁 프로덕션 Docker Compose 파일이 이미 존재합니다.${NC}"
    fi
    
    # Create systemd service file for auto-start
    create_systemd_service
}

# Function to create systemd service
create_systemd_service() {
    echo -e "${BLUE}🚀 Systemd 서비스 파일 생성 중...${NC}"
    
    local service_file="/etc/systemd/system/filewallball.service"
    local current_dir=$(pwd)
    
    if [[ -f "$service_file" ]]; then
        echo -e "${YELLOW}⚠️  Systemd 서비스 파일이 이미 존재합니다.${NC}"
        echo -e "${YELLOW}기존 파일을 덮어쓰시겠습니까? (y/N):${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}📁 기존 서비스 파일을 사용합니다.${NC}"
            return 0
        fi
    fi
    
    # Create systemd service file
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=FileWallBall Production Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$current_dir
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
ExecReload=/usr/local/bin/docker-compose -f docker-compose.prod.yml restart
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable filewallball.service
    
    echo -e "${GREEN}✅ Systemd 서비스 파일 생성 완료${NC}"
    echo -e "${CYAN}📋 서비스 관리 명령어:${NC}"
    echo -e "${CYAN}  - 시작: sudo systemctl start filewallball${NC}"
    echo -e "${CYAN}  - 중지: sudo systemctl stop filewallball${NC}"
    echo -e "${CYAN}  - 재시작: sudo systemctl restart filewallball${NC}"
    echo -e "${CYAN}  - 상태 확인: sudo systemctl status filewallball${NC}"
    
    log_message "INFO" "Systemd 서비스 파일 생성 완료"
}

# Function to start FileWallBall services
start_filewallball_services() {
    echo -e "${BLUE}🚀 FileWallBall 서비스 시작 중...${NC}"
    
    # Start all services
    echo -e "${CYAN}🐳 모든 서비스 시작 중...${NC}"
    if docker-compose -f docker-compose.prod.yml up -d; then
        echo -e "${GREEN}✅ 모든 서비스 시작 완료${NC}"
        log_message "INFO" "모든 서비스 시작 완료"
    else
        echo -e "${RED}❌ 서비스 시작 실패${NC}"
        log_message "ERROR" "서비스 시작 실패"
        exit 1
    fi
    
    # Wait for services to be ready
    echo -e "${CYAN}⏳ 서비스 준비 대기 중...${NC}"
    sleep 60
    
    echo -e "${GREEN}🎉 FileWallBall 서비스 시작 완료!${NC}"
    log_message "INFO" "FileWallBall 서비스 시작 완료"
}

# Function to check service status
check_services() {
    echo -e "${BLUE}🔍 서비스 상태 확인 중...${NC}"
    
    local services=("filewallball" "mariadb" "redis")
    local all_healthy=true
    
    for service in "${services[@]}"; do
        echo -e "${CYAN}📊 $service 서비스 상태 확인 중...${NC}"
        
        if docker-compose -f docker-compose.prod.yml ps $service | grep -q "Up"; then
            local status=$(docker-compose -f docker-compose.prod.yml ps $service --format "table {{.Status}}")
            echo -e "${GREEN}✅ $service 서비스 정상: $status${NC}"
            log_message "INFO" "$service 서비스 정상: $status"
        else
            echo -e "${RED}❌ $service 서비스 문제 발생${NC}"
            log_message "ERROR" "$service 서비스 문제 발생"
            all_healthy=false
            
            # Show logs for failed service
            echo -e "${YELLOW}📋 $service 서비스 로그:${NC}"
            docker-compose -f docker-compose.prod.yml logs --tail=20 $service
        fi
    done
    
    if [[ "$all_healthy" == true ]]; then
        echo -e "${GREEN}✅ 모든 서비스가 정상 동작 중입니다.${NC}"
        log_message "INFO" "모든 서비스 정상 동작"
        return 0
    else
        echo -e "${RED}❌ 일부 서비스에 문제가 있습니다.${NC}"
        log_message "ERROR" "일부 서비스 문제 발생"
        return 1
    fi
}

# Function to test API health
test_api_health() {
    echo -e "${BLUE}🧪 API 헬스체크 테스트 중...${NC}"
    
    local max_attempts=30
    local attempt=1
    local api_url="http://localhost:8000/health"
    
    echo -e "${CYAN}🌐 API 엔드포인트: $api_url${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        echo -e "${CYAN}📡 API 응답 테스트 중... ($attempt/$max_attempts)${NC}"
        
        if curl -s -f "$api_url" | grep -q "ok"; then
            local response=$(curl -s "$api_url")
            echo -e "${GREEN}✅ API 헬스체크 성공: $response${NC}"
            log_message "INFO" "API 헬스체크 성공: $response"
            return 0
        else
            echo -e "${YELLOW}⏳ API 시작 대기 중... ($attempt/$max_attempts)${NC}"
            sleep 5
            ((attempt++))
        fi
    done
    
    echo -e "${RED}❌ API 헬스체크 실패 (최대 시도 횟수 초과)${NC}"
    log_message "ERROR" "API 헬스체크 실패 - 최대 시도 횟수 초과"
    
    # Show API service logs
    echo -e "${YELLOW}📋 API 서비스 로그:${NC}"
    docker-compose -f docker-compose.prod.yml logs --tail=30 app
    
    return 1
}

# Function to test file upload functionality
test_file_upload() {
    echo -e "${BLUE}🧪 파일 업로드 기능 테스트 중...${NC}"
    
    # Create test file
    local test_file="test_upload.txt"
    local test_content="FileWallBall Ubuntu Production Installer Test - $(date)"
    
    echo "$test_content" > "$test_file"
    echo -e "${CYAN}📝 테스트 파일 생성: $test_file${NC}"
    
    # Test file upload
    echo -e "${CYAN}📤 파일 업로드 테스트 중...${NC}"
    local upload_response=$(curl -s -X POST \
        -F "file=@$test_file" \
        -F "project_key=test_project" \
        "http://localhost:8000/api/v1/upload")
    
    # Check response
    if echo "$upload_response" | grep -q "file_id"; then
        local file_id=$(echo "$upload_response" | grep -o '"file_id":"[^"]*"' | cut -d'"' -f4)
        echo -e "${GREEN}✅ 파일 업로드 테스트 성공${NC}"
        echo -e "${CYAN}📋 업로드된 파일 ID: $file_id${NC}"
        log_message "INFO" "파일 업로드 테스트 성공: $file_id"
        
        # Test file download
        test_file_download "$file_id"
        
        # Clean up test file
        rm -f "$test_file"
        return 0
    else
        echo -e "${RED}❌ 파일 업로드 테스트 실패${NC}"
        echo -e "${YELLOW}📋 응답 내용: $upload_response${NC}"
        log_message "ERROR" "파일 업로드 테스트 실패: $upload_response"
        
        # Clean up test file
        rm -f "$test_file"
        return 1
    fi
}

# Function to test file download
test_file_download() {
    local file_id="$1"
    
    echo -e "${CYAN}📥 파일 다운로드 테스트 중...${NC}"
    
    local download_url="http://localhost:8000/api/v1/download/$file_id"
    local downloaded_file="test_download.txt"
    
    if curl -s -f -o "$downloaded_file" "$download_url"; then
        local original_content=$(cat "test_upload.txt" 2>/dev/null || echo "test content")
        local downloaded_content=$(cat "$downloaded_file")
        
        if [[ "$original_content" == "$downloaded_content" ]]; then
            echo -e "${GREEN}✅ 파일 다운로드 테스트 성공${NC}"
            log_message "INFO" "파일 다운로드 테스트 성공"
        else
            echo -e "${RED}❌ 파일 다운로드 테스트 실패 - 내용 불일치${NC}"
            log_message "ERROR" "파일 다운로드 테스트 실패 - 내용 불일치"
        fi
        
        # Clean up
        rm -f "$downloaded_file"
    else
        echo -e "${RED}❌ 파일 다운로드 테스트 실패${NC}"
        log_message "ERROR" "파일 다운로드 테스트 실패"
    fi
}

# Function to test database connectivity
test_database_connectivity() {
    echo -e "${BLUE}🧪 데이터베이스 연결 테스트 중...${NC}"
    
    # Test MariaDB connection
    echo -e "${CYAN}🗄️  MariaDB 연결 테스트 중...${NC}"
    if docker-compose -f docker-compose.prod.yml exec -T mariadb mysql -u filewallball_user -p"${DB_PASSWORD}" -e "SELECT 1;" &>/dev/null; then
        echo -e "${GREEN}✅ MariaDB 연결 성공${NC}"
        log_message "INFO" "MariaDB 연결 성공"
    else
        echo -e "${RED}❌ MariaDB 연결 실패${NC}"
        log_message "ERROR" "MariaDB 연결 실패"
        return 1
    fi
    
    # Test Redis connection
    echo -e "${CYAN}🔴 Redis 연결 테스트 중...${NC}"
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping | grep -q "PONG"; then
        echo -e "${GREEN}✅ Redis 연결 성공${NC}"
        log_message "INFO" "Redis 연결 성공"
    else
        echo -e "${RED}❌ Redis 연결 실패${NC}"
        log_message "ERROR" "Redis 연결 실패"
        return 1
    fi
    
    echo -e "${GREEN}✅ 데이터베이스 연결 테스트 완료${NC}"
    log_message "INFO" "데이터베이스 연결 테스트 완료"
    return 0
}

# Function to comprehensive verification
comprehensive_verification() {
    echo -e "${BLUE}🔍 FileWallBall 서비스 종합 검증 시작${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    # Check service status
    if ! check_services; then
        echo -e "${RED}❌ 서비스 상태 확인 실패${NC}"
        return 1
    fi
    
    # Test API health
    if ! test_api_health; then
        echo -e "${RED}❌ API 헬스체크 실패${NC}"
        return 1
    fi
    
    # Test database connectivity
    if ! test_database_connectivity; then
        echo -e "${RED}❌ 데이터베이스 연결 테스트 실패${NC}"
        return 1
    fi
    
    # Test file upload functionality
    if ! test_file_upload; then
        echo -e "${RED}❌ 파일 업로드 기능 테스트 실패${NC}"
        return 1
    fi
    
    echo -e "${GREEN}🎉 모든 검증 테스트 통과!${NC}"
    log_message "INFO" "모든 검증 테스트 통과"
    return 0
}

# Function to troubleshoot common issues
troubleshoot_common_issues() {
    echo -e "${BLUE}🔧 일반적인 문제 해결 중...${NC}"
    
    # Check if containers are running
    echo -e "${CYAN}🐳 컨테이너 상태 확인 중...${NC}"
    docker-compose -f docker-compose.prod.yml ps
    
    # Check container logs
    echo -e "${CYAN}📋 컨테이너 로그 확인 중...${NC}"
    echo -e "${YELLOW}📋 App 서비스 로그:${NC}"
    docker-compose -f docker-compose.prod.yml logs --tail=20 app
    
    echo -e "${YELLOW}📋 MariaDB 서비스 로그:${NC}"
    docker-compose -f docker-compose.prod.yml logs --tail=20 mariadb
    
    echo -e "${YELLOW}📋 Redis 서비스 로그:${NC}"
    docker-compose -f docker-compose.prod.yml logs --tail=20 redis
    
    # Check system resources
    echo -e "${CYAN}📊 시스템 리소스 확인 중...${NC}"
    echo -e "${YELLOW}📊 메모리 사용량:${NC}"
    free -h
    
    echo -e "${YELLOW}📊 디스크 사용량:${NC}"
    df -h
    
    echo -e "${YELLOW}📊 Docker 디스크 사용량:${NC}"
    docker system df
    
    # Check network connectivity
    echo -e "${CYAN}🌐 네트워크 연결 확인 중...${NC}"
    echo -e "${YELLOW}🌐 포트 상태:${NC}"
    netstat -tlnp | grep -E ":(8000|13306|6379)"
    
    echo -e "${YELLOW}🌐 Docker 네트워크:${NC}"
    docker network ls
    
    # Provide troubleshooting suggestions
    echo -e "${BLUE}💡 문제 해결 제안:${NC}"
    echo -e "${CYAN}1. 서비스 재시작:${NC}"
    echo -e "${YELLOW}   docker-compose -f docker-compose.prod.yml restart${NC}"
    
    echo -e "${CYAN}2. 컨테이너 재생성:${NC}"
    echo -e "${YELLOW}   docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml up -d${NC}"
    
    echo -e "${CYAN}3. 로그 실시간 모니터링:${NC}"
    echo -e "${YELLOW}   docker-compose -f docker-compose.prod.yml logs -f${NC}"
    
    echo -e "${CYAN}4. 시스템 리소스 정리:${NC}"
    echo -e "${YELLOW}   docker system prune -f${NC}"
    
    log_message "INFO" "일반적인 문제 해결 완료"
}

# Function to generate installation documentation
generate_documentation() {
    echo -e "${BLUE}📚 FileWallBall 설치 가이드 문서 생성 중...${NC}"
    
    local guide_file="INSTALLATION_GUIDE.md"
    local current_dir=$(pwd)
    local ubuntu_version=$(lsb_release -rs)
    local ubuntu_codename=$(lsb_release -cs)
    
    # Get system information
    local total_ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_ram_gb=$((total_ram_kb / 1024 / 1024))
    local available_disk_kb=$(df / | awk 'NR==2{print $4}')
    local available_disk_gb=$((available_disk_kb / 1024 / 1024))
    local cpu_cores=$(nproc)
    
    # Get Docker versions
    local docker_version=$(docker --version 2>/dev/null || echo "Not installed")
    local compose_version=$(docker-compose --version 2>/dev/null || echo "Not installed")
    
    # Get service URLs
    local api_url="http://localhost:8000"
    local docs_url="http://localhost:8000/docs"
    local redoc_url="http://localhost:8000/redoc"
    local health_url="http://localhost:8000/health"
    
    # Create comprehensive installation guide
    cat > "$guide_file" << EOF
# FileWallBall Ubuntu Production 환경 설치 가이드

## 📋 설치 정보 요약

- **설치 날짜**: $(date '+%Y-%m-%d %H:%M:%S')
- **Ubuntu 버전**: $ubuntu_version ($ubuntu_codename)
- **시스템 사양**: ${total_ram_gb}GB RAM, ${available_disk_gb}GB 디스크, ${cpu_cores}코어 CPU
- **Docker 버전**: $docker_version
- **Docker Compose 버전**: $compose_version
- **설치 디렉토리**: $current_dir

## 🌟 지원 환경

- **Ubuntu LTS**: 18.04, 20.04, 22.04, 24.04
- **최소 요구사항**: 2GB RAM, 10GB 디스크 공간
- **권장 사양**: 4GB RAM, 20GB 디스크 공간

## 🚀 원클릭 설치

### 방법 1: 원격 스크립트 실행
\`\`\`bash
curl -fsSL https://raw.githubusercontent.com/pathcosmos/dy_gh_filewallball/main/scripts/ubuntu-production-installer.sh | bash
\`\`\`

### 방법 2: 로컬 스크립트 실행
\`\`\`bash
# 스크립트 다운로드
wget https://raw.githubusercontent.com/pathcosmos/dy_gh_filewallball/main/scripts/ubuntu-production-installer.sh

# 실행 권한 부여
chmod +x ubuntu-production-installer.sh

# 설치 실행
./ubuntu-production-installer.sh
\`\`\`

## 📦 수동 설치 단계

### 1. 환경 검증
\`\`\`bash
./ubuntu-production-installer.sh --validate
\`\`\`

### 2. Docker 설치
\`\`\`bash
# 패키지 업데이트
sudo apt-get update

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
\`\`\`

### 3. FileWallBall 소스 다운로드
\`\`\`bash
git clone https://github.com/pathcosmos/dy_gh_filewallball.git
cd dy_gh_filewallball
\`\`\`

### 4. 환경 설정
\`\`\`bash
# Production 환경 파일 생성
cp .env.example .env.prod

# 환경 변수 편집
nano .env.prod
\`\`\`

### 5. 데이터베이스 설정
\`\`\`bash
# 데이터베이스 설정 스크립트 실행
./scripts/setup-database.sh

# 연결 테스트
./scripts/test-db-connection.sh
\`\`\`

### 6. 서비스 시작
\`\`\`bash
# Production 모드로 시작
docker-compose -f docker-compose.prod.yml up -d

# 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps
\`\`\`

## 🔍 설치 후 확인

### 서비스 상태 확인
\`\`\`bash
# 컨테이너 상태
docker-compose -f docker-compose.prod.yml ps

# 서비스 로그
docker-compose -f docker-compose.prod.yml logs -f
\`\`\`

### API 테스트
\`\`\`bash
# 헬스체크
curl $health_url

# API 문서
curl $docs_url
\`\`\`

### 파일 업로드 테스트
\`\`\`bash
# 테스트 파일 생성
echo "test content" > test.txt

# 파일 업로드
curl -X POST \\
  -F "file=@test.txt" \\
  -F "project_key=test_project" \\
  $api_url/api/v1/upload

# 파일 다운로드
curl -O $api_url/api/v1/download/{file_id}
\`\`\`

## 🌐 접속 정보

- **API 서버**: $api_url
- **API 문서 (Swagger)**: $docs_url
- **API 문서 (ReDoc)**: $redoc_url
- **헬스체크**: $health_url
- **데이터베이스**: localhost:13306
- **Redis**: localhost:6379

## 🔧 서비스 관리

### Systemd 서비스 사용
\`\`\`bash
# 서비스 시작
sudo systemctl start filewallball

# 서비스 중지
sudo systemctl stop filewallball

# 서비스 재시작
sudo systemctl restart filewallball

# 서비스 상태 확인
sudo systemctl status filewallball

# 서비스 자동 시작 설정
sudo systemctl enable filewallball
\`\`\`

### Docker Compose 직접 사용
\`\`\`bash
# 서비스 시작
docker-compose -f docker-compose.prod.yml up -d

# 서비스 중지
docker-compose -f docker-compose.prod.yml down

# 서비스 재시작
docker-compose -f docker-compose.prod.yml restart

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
\`\`\`

## 🚨 문제 해결

### 일반적인 문제들

#### 1. 포트 충돌
\`\`\`bash
# 포트 사용 확인
sudo netstat -tlnp | grep :8000

# 충돌하는 프로세스 종료
sudo kill -9 {PID}
\`\`\`

#### 2. 데이터베이스 연결 실패
\`\`\`bash
# MariaDB 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps mariadb

# MariaDB 로그 확인
docker-compose -f docker-compose.prod.yml logs mariadb

# 데이터베이스 재시작
docker-compose -f docker-compose.prod.yml restart mariadb
\`\`\`

#### 3. 메모리 부족
\`\`\`bash
# 메모리 사용량 확인
free -h

# Docker 리소스 정리
docker system prune -f

# 불필요한 컨테이너 정리
docker container prune -f
\`\`\`

#### 4. 디스크 공간 부족
\`\`\`bash
# 디스크 사용량 확인
df -h

# Docker 디스크 사용량 확인
docker system df

# Docker 정리
docker system prune -af
\`\`\`

### 로그 분석
\`\`\`bash
# 실시간 로그 모니터링
docker-compose -f docker-compose.prod.yml logs -f

# 특정 서비스 로그
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f mariadb
docker-compose -f docker-compose.prod.yml logs -f redis

# 로그 파일 위치
tail -f logs/app.log
tail -f logs/db.log
\`\`\`

## 🔒 보안 설정

### 방화벽 설정
\`\`\`bash
# UFW 활성화
sudo ufw enable

# 필요한 포트만 열기
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # FileWallBall API
sudo ufw allow 80/tcp    # HTTP (선택사항)
sudo ufw allow 443/tcp   # HTTPS (선택사항)

# 방화벽 상태 확인
sudo ufw status numbered
\`\`\`

### SSL 인증서 설정 (Let's Encrypt)
\`\`\`bash
# Certbot 설치
sudo apt-get install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d yourdomain.com

# 자동 갱신 설정
sudo crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
\`\`\`

## 📊 모니터링 및 백업

### 시스템 모니터링
\`\`\`bash
# 리소스 사용량 모니터링
htop
iotop
nethogs

# Docker 리소스 모니터링
docker stats
\`\`\`

### 백업 설정
\`\`\`bash
# 데이터베이스 백업
docker-compose -f docker-compose.prod.yml exec mariadb mysqldump -u root -p filewallball_db > backup_\$(date +%Y%m%d_%H%M%S).sql

# 파일 백업
tar -czf uploads_backup_\$(date +%Y%m%d_%H%M%S).tar.gz uploads/

# 자동 백업 스크립트 생성
crontab -e
# 0 2 * * * /path/to/backup_script.sh
\`\`\`

## 🔄 업데이트 및 유지보수

### FileWallBall 업데이트
\`\`\`bash
# 소스 코드 업데이트
git pull origin main

# 컨테이너 재빌드
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
\`\`\`

### 시스템 업데이트
\`\`\`bash
# 패키지 업데이트
sudo apt-get update && sudo apt-get upgrade -y

# Docker 업데이트
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
\`\`\`

## 📞 지원 및 문의

- **GitHub Issues**: https://github.com/pathcosmos/dy_gh_filewallball/issues
- **문서**: $docs_url
- **API 문서**: $redoc_url

## 📝 설치 완료 체크리스트

- [ ] Ubuntu 환경 검증 완료
- [ ] Docker 및 Docker Compose 설치 완료
- [ ] FileWallBall 소스 코드 다운로드 완료
- [ ] 환경 설정 파일 생성 완료
- [ ] 데이터베이스 설정 완료
- [ ] 서비스 시작 및 동작 확인 완료
- [ ] API 테스트 완료
- [ ] 파일 업로드/다운로드 테스트 완료
- [ ] 방화벽 설정 완료 (선택사항)
- [ ] SSL 인증서 설정 완료 (선택사항)
- [ ] 백업 스크립트 설정 완료 (선택사항)
- [ ] 모니터링 설정 완료 (선택사항)

---

**설치 완료 시간**: $(date '+%Y-%m-%d %H:%M:%S')  
**설치 스크립트 버전**: Ubuntu Production Installer v1.0  
**생성자**: Ubuntu Production Installer Script
EOF

    echo -e "${GREEN}✅ 설치 가이드 문서 생성 완료${NC}"
    echo -e "${CYAN}📋 생성된 파일: $guide_file${NC}"
    
    # Create quick reference card
    create_quick_reference
    
    # Create troubleshooting guide
    create_troubleshooting_guide
    
    log_message "INFO" "설치 가이드 문서 생성 완료"
}

# Function to create quick reference card
create_quick_reference() {
    local ref_file="QUICK_REFERENCE.md"
    
    cat > "$ref_file" << EOF
# FileWallBall Quick Reference

## 🚀 빠른 시작
\`\`\`bash
# 서비스 시작
docker-compose -f docker-compose.prod.yml up -d

# 서비스 중지
docker-compose -f docker-compose.prod.yml down

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
\`\`\`

## 🔍 상태 확인
\`\`\`bash
# 서비스 상태
docker-compose -f docker-compose.prod.yml ps

# API 헬스체크
curl http://localhost:8000/health

# 시스템 리소스
docker stats
\`\`\`

## 🔧 문제 해결
\`\`\`bash
# 서비스 재시작
docker-compose -f docker-compose.prod.yml restart

# 컨테이너 재생성
docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f app
\`\`\`

## 📊 주요 포트
- **8000**: FileWallBall API
- **13306**: MariaDB
- **6379**: Redis

## 🌐 주요 URL
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
EOF

    echo -e "${GREEN}✅ 빠른 참조 카드 생성 완료${NC}"
    echo -e "${CYAN}📋 생성된 파일: $ref_file${NC}"
}

# Function to create troubleshooting guide
create_troubleshooting_guide() {
    local trouble_file="TROUBLESHOOTING.md"
    
    cat > "$trouble_file" << EOF
# FileWallBall 문제 해결 가이드

## 🚨 긴급 문제 해결

### 서비스가 시작되지 않음
1. Docker 상태 확인: \`sudo systemctl status docker\`
2. 포트 충돌 확인: \`sudo netstat -tlnp | grep :8000\`
3. 로그 확인: \`docker-compose -f docker-compose.prod.yml logs\`

### 데이터베이스 연결 실패
1. MariaDB 컨테이너 상태: \`docker-compose -f docker-compose.prod.yml ps mariadb\`
2. 데이터베이스 로그: \`docker-compose -f docker-compose.prod.yml logs mariadb\`
3. 연결 테스트: \`./scripts/test-db-connection.sh\`

### API 응답 없음
1. 컨테이너 상태: \`docker-compose -f docker-compose.prod.yml ps\`
2. API 로그: \`docker-compose -f docker-compose.prod.yml logs app\`
3. 네트워크 확인: \`curl -v http://localhost:8000/health\`

## 🔧 일반적인 문제들

### 메모리 부족
- Docker 리소스 제한 확인
- 불필요한 컨테이너 정리
- 시스템 스왑 설정

### 디스크 공간 부족
- Docker 이미지/컨테이너 정리
- 로그 파일 정리
- 백업 파일 관리

### 네트워크 문제
- 방화벽 설정 확인
- 포트 바인딩 확인
- Docker 네트워크 설정

## 📋 진단 명령어

### 시스템 진단
\`\`\`bash
# 시스템 리소스
free -h
df -h
top

# 네트워크 상태
netstat -tlnp
ss -tlnp
\`\`\`

### Docker 진단
\`\`\`bash
# 컨테이너 상태
docker ps -a
docker stats

# 이미지 정보
docker images
docker system df

# 네트워크 정보
docker network ls
docker network inspect bridge
\`\`\`

### 애플리케이션 진단
\`\`\`bash
# 서비스 상태
docker-compose -f docker-compose.prod.yml ps

# 로그 확인
docker-compose -f docker-compose.prod.yml logs --tail=50

# 환경 변수 확인
docker-compose -f docker-compose.prod.yml exec app env
\`\`\`

## 🆘 추가 지원

문제가 지속되면 다음 정보와 함께 [GitHub Issues](https://github.com/pathcosmos/dy_gh_filewallball/issues)에 문의하세요:

1. Ubuntu 버전: \`lsb_release -a\`
2. Docker 버전: \`docker --version\`
3. Docker Compose 버전: \`docker-compose --version\`
4. 시스템 사양: \`free -h && df -h && nproc\`
5. 에러 로그: \`docker-compose -f docker-compose.prod.yml logs\`
6. 환경 설정: \`cat .env.prod\` (비밀번호 제외)
EOF

    echo -e "${GREEN}✅ 문제 해결 가이드 생성 완료${NC}"
    echo -e "${CYAN}📋 생성된 파일: $trouble_file${NC}"
}

# Main FileWallBall source and database setup function
main_filewallball_setup() {
    echo -e "${BLUE}📥 FileWallBall 소스 및 데이터베이스 설정 시작${NC}"
    echo -e "${BLUE}=============================================${NC}"
    
    # Download source code
    download_filewallball_source
    
    # Create production environment file
    create_production_env
    
    # Setup database
    setup_database_integrated
    
    echo -e "${GREEN}🎉 FileWallBall 소스 및 데이터베이스 설정 완료!${NC}"
    log_message "INFO" "FileWallBall 소스 및 데이터베이스 설정 완료"
}

# Main Docker installation function
main_docker_installation() {
    echo -e "${BLUE}🐳 Docker 및 Docker Compose 설치 시작${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    # Install Docker
    install_docker
    
    # Install Docker Compose
    install_docker_compose
    
    # Verify installation
    verify_docker_installation
    
    echo -e "${GREEN}🎉 Docker 설치 완료!${NC}"
    log_message "INFO" "Docker 설치 완료"
}

# Main environment validation function
main_environment_validation() {
    echo -e "${BLUE}🔍 Ubuntu 환경 요구사항 분석 및 검증 시작${NC}"
    echo -e "${BLUE}=============================================${NC}"
    
    # Check if running as root
    check_root
    
    # Check sudo privileges
    check_sudo
    
    # Check Ubuntu version
    check_ubuntu_version
    
    # Check system requirements
    check_system_requirements
    
    # Check network connectivity
    check_network_connectivity
    
    # Check existing installations
    check_existing_installations
    
    # Show system summary
    show_system_summary
    
    # Confirm installation
    confirm_installation
    
    echo -e "${GREEN}🎉 환경 검증 완료! 설치를 진행할 수 있습니다.${NC}"
    log_message "INFO" "환경 검증 완료"
}

# Function to show installation summary
show_installation_summary() {
    echo -e "${BLUE}🎉 FileWallBall Ubuntu Production 환경 설치 완료!${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    local current_dir=$(pwd)
    local api_url="http://localhost:8000"
    local docs_url="http://localhost:8000/docs"
    local health_url="http://localhost:8000/health"
    
    echo -e "${GREEN}✅ 설치 완료된 구성 요소:${NC}"
    echo -e "${CYAN}  - Ubuntu 환경 검증${NC}"
    echo -e "${CYAN}  - Docker 및 Docker Compose${NC}"
    echo -e "${CYAN}  - FileWallBall 소스 코드${NC}"
    echo -e "${CYAN}  - 데이터베이스 설정 (MariaDB + Redis)${NC}"
    echo -e "${CYAN}  - Production 환경 설정${NC}"
    echo -e "${CYAN}  - 서비스 시작 및 검증${NC}"
    echo -e "${CYAN}  - 설치 가이드 문서${NC}"
    
    echo ""
    echo -e "${GREEN}🌐 접속 정보:${NC}"
    echo -e "${CYAN}  - API 서버: $api_url${NC}"
    echo -e "${CYAN}  - API 문서: $docs_url${NC}"
    echo -e "${CYAN}  - 헬스체크: $health_url${NC}"
    echo -e "${CYAN}  - 데이터베이스: localhost:13306${NC}"
    echo -e "${CYAN}  - Redis: localhost:6379${NC}"
    
    echo ""
    echo -e "${GREEN}📚 생성된 문서:${NC}"
    echo -e "${CYAN}  - INSTALLATION_GUIDE.md (상세 설치 가이드)${NC}"
    echo -e "${CYAN}  - QUICK_REFERENCE.md (빠른 참조 카드)${NC}"
    echo -e "${CYAN}  - TROUBLESHOOTING.md (문제 해결 가이드)${NC}"
    
    echo ""
    echo -e "${GREEN}🔧 서비스 관리:${NC}"
    echo -e "${CYAN}  - 서비스 시작: sudo systemctl start filewallball${NC}"
    echo -e "${CYAN}  - 서비스 중지: sudo systemctl stop filewallball${NC}"
    echo -e "${CYAN}  - 서비스 상태: sudo systemctl status filewallball${NC}"
    echo -e "${CYAN}  - 로그 확인: docker-compose -f docker-compose.prod.yml logs -f${NC}"
    
    echo ""
    echo -e "${GREEN}📊 다음 단계:${NC}"
    echo -e "${CYAN}1. 브라우저에서 $docs_url 접속하여 API 문서 확인${NC}"
    echo -e "${CYAN}2. 파일 업로드/다운로드 테스트 수행${NC}"
    echo -e "${CYAN}3. 방화벽 및 SSL 설정 (필요시)${NC}"
    echo -e "${CYAN}4. 백업 및 모니터링 설정 (권장)${NC}"
    
    echo ""
    echo -e "${YELLOW}⚠️  중요 사항:${NC}"
    echo -e "${YELLOW}  - .env.prod.passwords 파일을 안전한 곳에 보관하세요${NC}"
    echo -e "${YELLOW}  - 정기적인 백업을 설정하세요${NC}"
    echo -e "${YELLOW}  - 시스템 업데이트를 정기적으로 수행하세요${NC}"
    
    echo ""
    echo -e "${BLUE}📞 문제가 있으면 TROUBLESHOOTING.md 파일을 참조하세요${NC}"
    echo -e "${BLUE}또는 GitHub Issues에 문의하세요: https://github.com/lanco/filewallball/issues${NC}"
    
    log_message "INFO" "설치 완료 요약 표시"
}

# Function to cleanup temporary files
cleanup_temp_files() {
    echo -e "${BLUE}🧹 임시 파일 정리 중...${NC}"
    
    # Remove test files
    rm -f test_upload.txt test_download.txt 2>/dev/null || true
    
    # Remove password file if requested
    if [[ -f ".env.prod.passwords" ]]; then
        echo -e "${YELLOW}⚠️  .env.prod.passwords 파일이 생성되었습니다.${NC}"
        echo -e "${YELLOW}이 파일을 안전한 곳에 보관하고 필요시 삭제하세요.${NC}"
        echo -e "${YELLOW}지금 삭제하시겠습니까? (y/N):${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            rm -f .env.prod.passwords
            echo -e "${GREEN}✅ 비밀번호 파일 삭제 완료${NC}"
        fi
    fi
    
    # Clean up Docker system if requested
    echo -e "${YELLOW}Docker 시스템을 정리하시겠습니까? (y/N):${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        docker system prune -f
        echo -e "${GREEN}✅ Docker 시스템 정리 완료${NC}"
    fi
    
    log_message "INFO" "임시 파일 정리 완료"
}

# Main installation function
main_installation() {
    echo -e "${BLUE}🚀 FileWallBall Ubuntu Production 환경 자동 설치 시작${NC}"
    echo -e "${BLUE}=====================================================${NC}"
    
    local start_time=$(date +%s)
    
    # Step 1: Environment validation
    echo -e "${PURPLE}📋 Step 1/7: Ubuntu 환경 요구사항 분석 및 검증${NC}"
    main_environment_validation
    
    # Step 2: Docker installation
    echo -e "${PURPLE}📋 Step 2/7: Docker 및 Docker Compose 설치${NC}"
    main_docker_installation
    
    # Step 3: FileWallBall source and database setup
    echo -e "${PURPLE}📋 Step 3/7: FileWallBall 소스 및 데이터베이스 설정${NC}"
    main_filewallball_setup
    
    # Step 4: Production environment setup
    echo -e "${PURPLE}📋 Step 4/7: Production 환경 설정${NC}"
    setup_production_environment
    
    # Step 5: Start services
    echo -e "${PURPLE}📋 Step 5/7: FileWallBall 서비스 시작${NC}"
    start_filewallball_services
    
    # Step 6: Comprehensive verification
    echo -e "${PURPLE}📋 Step 6/7: 서비스 종합 검증${NC}"
    if comprehensive_verification; then
        echo -e "${GREEN}✅ 모든 검증 테스트 통과!${NC}"
    else
        echo -e "${RED}❌ 일부 검증 테스트 실패${NC}"
        echo -e "${YELLOW}문제 해결을 위해 다음 명령어를 실행하세요:${NC}"
        echo -e "${CYAN}  ./ubuntu-production-installer.sh --troubleshoot${NC}"
        
        # Ask if user wants to continue
        echo -e "${YELLOW}계속 진행하시겠습니까? (y/N):${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${RED}설치를 중단합니다.${NC}"
            log_message "ERROR" "사용자에 의해 설치 중단 - 검증 실패"
            exit 1
        fi
    fi
    
    # Step 7: Generate documentation
    echo -e "${PURPLE}📋 Step 7/7: 설치 가이드 문서 생성${NC}"
    generate_documentation
    
    # Calculate installation time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo ""
    echo -e "${GREEN}🎉 FileWallBall Ubuntu Production 환경 설치 완료!${NC}"
    echo -e "${CYAN}총 소요 시간: ${minutes}분 ${seconds}초${NC}"
    
    # Show installation summary
    show_installation_summary
    
    # Cleanup temporary files
    cleanup_temp_files
    
    log_message "INFO" "FileWallBall Ubuntu Production 환경 설치 완료 - 소요시간: ${minutes}분 ${seconds}초"
}

# Function to run troubleshooting
run_troubleshooting() {
    echo -e "${BLUE}🔧 FileWallBall 문제 해결 모드${NC}"
    echo -e "${BLUE}===============================${NC}"
    
    troubleshoot_common_issues
    
    echo -e "${GREEN}✅ 문제 해결 완료${NC}"
    echo -e "${YELLOW}위의 제안사항을 시도해보시고, 문제가 지속되면 GitHub Issues에 문의하세요.${NC}"
    
    log_message "INFO" "문제 해결 모드 실행 완료"
}

# Check if script is run with arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo -e "${BLUE}FileWallBall Ubuntu Production 환경 자동 설치 스크립트${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h        Show this help message"
    echo "  --validate        Run only environment validation"
    echo "  --troubleshoot    Run troubleshooting mode"
    echo "  --install         Run full installation (default)"
    echo ""
    echo "Examples:"
    echo "  $0                 # Run full installation"
    echo "  $0 --validate     # Run only validation"
    echo "  $0 --troubleshoot # Run troubleshooting mode"
    echo "  $0 --install      # Run full installation"
    echo ""
    echo "Description:"
    echo "  이 스크립트는 Ubuntu 환경에서 FileWallBall을 Production 모드로"
    echo "  자동 설치하는 완전 자동화 스크립트입니다."
    echo ""
    echo "  지원 환경: Ubuntu 18.04, 20.04, 22.04, 24.04 LTS"
    echo "  최소 요구사항: 2GB RAM, 10GB 디스크 공간"
    echo ""
    exit 0
elif [ "$1" = "--validate" ]; then
    echo -e "${BLUE}🧪 환경 검증만 실행합니다...${NC}"
    main_environment_validation
    echo -e "${GREEN}✅ 환경 검증 완료!${NC}"
    exit 0
elif [ "$1" = "--troubleshoot" ]; then
    echo -e "${BLUE}🔧 문제 해결 모드를 실행합니다...${NC}"
    run_troubleshooting
    exit 0
elif [ "$1" = "--install" ] || [ -z "$1" ]; then
    # Run full installation
    main_installation
else
    echo -e "${RED}❌ 알 수 없는 옵션: $1${NC}"
    echo -e "${YELLOW}사용법을 보려면 --help를 입력하세요.${NC}"
    exit 1
fi
