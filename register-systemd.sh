#!/bin/bash

# FileWallBall API - SystemD Service Registration Script
# 이 스크립트는 FileWallBall API 서비스를 systemctl로 관리할 수 있도록 등록합니다.

set -e

# 색상 코드 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 스크립트 디렉토리 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="filewallball"
SERVICE_FILE="${SCRIPT_DIR}/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/system"

log_info "FileWallBall API SystemD 서비스 등록을 시작합니다..."

# root 권한 확인
if [[ $EUID -ne 0 ]]; then
    log_error "이 스크립트는 root 권한으로 실행되어야 합니다."
    log_info "다음과 같이 실행하세요: sudo $0"
    exit 1
fi

# 서비스 파일 존재 확인
if [[ ! -f "$SERVICE_FILE" ]]; then
    log_error "서비스 파일을 찾을 수 없습니다: $SERVICE_FILE"
    exit 1
fi

log_info "서비스 파일 확인: $SERVICE_FILE"

# 기존 서비스가 실행 중인지 확인하고 중지
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_warning "기존 $SERVICE_NAME 서비스가 실행 중입니다. 중지합니다..."
    systemctl stop "$SERVICE_NAME"
fi

# 기존 서비스가 활성화되어 있는지 확인하고 비활성화
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    log_warning "기존 $SERVICE_NAME 서비스가 활성화되어 있습니다. 비활성화합니다..."
    systemctl disable "$SERVICE_NAME"
fi

# 서비스 파일을 systemd 디렉토리로 복사
log_info "서비스 파일을 systemd 디렉토리로 복사합니다..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
log_success "서비스 파일이 복사되었습니다: $SYSTEMD_DIR/${SERVICE_NAME}.service"

# systemd 설정 다시 로드
log_info "systemd 설정을 다시 로드합니다..."
systemctl daemon-reload
log_success "systemd 설정이 다시 로드되었습니다."

# 서비스 활성화 (부팅 시 자동 시작)
log_info "서비스를 활성화합니다..."
systemctl enable "$SERVICE_NAME"
log_success "서비스가 활성화되었습니다. (부팅 시 자동 시작)"

# 필요한 Python 패키지 확인
log_info "Python 환경 및 패키지를 확인합니다..."
cd "$SCRIPT_DIR"

# requirements.txt가 있으면 패키지 설치 확인
if [[ -f "requirements.txt" ]]; then
    log_info "Python 패키지 의존성을 확인합니다..."
    python3 -c "
import sys
missing_packages = []
try:
    import fastapi
    import uvicorn
    import sqlalchemy
except ImportError as e:
    missing_packages.append(str(e))

if missing_packages:
    print('경고: 일부 필수 패키지가 누락되었을 수 있습니다.')
    print('pip install -r requirements.txt 명령을 실행하세요.')
    sys.exit(1)
else:
    print('필수 패키지가 모두 설치되어 있습니다.')
"
    if [[ $? -ne 0 ]]; then
        log_warning "일부 필수 패키지가 누락되었을 수 있습니다."
        read -p "pip install -r requirements.txt를 실행하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pip3 install -r requirements.txt
        fi
    fi
fi

# 환경 변수 파일 확인
if [[ ! -f ".env" ]]; then
    log_warning ".env 파일이 없습니다."
    if [[ -f ".env.example" ]]; then
        log_info ".env.example 파일을 복사하여 .env 파일을 생성합니다."
        cp ".env.example" ".env"
        log_warning "필요한 환경 변수를 .env 파일에서 수정하세요."
    fi
fi

# 서비스 시작
log_info "서비스를 시작합니다..."
systemctl start "$SERVICE_NAME"

# 서비스 상태 확인
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_success "FileWallBall API 서비스가 성공적으로 시작되었습니다!"
else
    log_error "서비스 시작에 실패했습니다."
    log_info "상태를 확인하려면 다음 명령을 실행하세요:"
    echo "  systemctl status $SERVICE_NAME"
    echo "  journalctl -u $SERVICE_NAME -f"
    exit 1
fi

echo
log_success "=== 설치가 완료되었습니다! ==="
echo
echo "이제 다음 명령어로 서비스를 관리할 수 있습니다:"
echo "  • 서비스 시작:    sudo systemctl start $SERVICE_NAME"
echo "  • 서비스 중지:    sudo systemctl stop $SERVICE_NAME"
echo "  • 서비스 재시작:  sudo systemctl restart $SERVICE_NAME"
echo "  • 서비스 상태:    sudo systemctl status $SERVICE_NAME"
echo "  • 로그 확인:      sudo journalctl -u $SERVICE_NAME -f"
echo "  • 부팅 시 자동 시작 해제: sudo systemctl disable $SERVICE_NAME"
echo
log_info "API 서비스는 http://localhost:8000 에서 접근할 수 있습니다."
log_info "API 문서는 http://localhost:8000/docs 에서 확인할 수 있습니다."