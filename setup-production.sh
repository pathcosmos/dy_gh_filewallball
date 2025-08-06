#!/bin/bash
# FileWallBall Production Setup Script
# ===================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 FileWallBall 운영환경 설정 시작...${NC}"

# 현재 디렉토리 확인
CURRENT_DIR=$(pwd)
PROJECT_DIR="/home/lanco/cursor/temp_git/dy_gh_filewallball"

if [ "$CURRENT_DIR" != "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️  프로젝트 디렉토리로 이동: $PROJECT_DIR${NC}"
    cd "$PROJECT_DIR"
fi

# 1. SECRET_KEY 생성
echo -e "${BLUE}🔐 SECRET_KEY 생성 중...${NC}"
if command -v python3 &> /dev/null; then
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    echo -e "${GREEN}✅ SECRET_KEY 생성 완료${NC}"
else
    echo -e "${RED}❌ Python3가 설치되지 않았습니다.${NC}"
    exit 1
fi

# 2. 로그 디렉토리 생성
echo -e "${BLUE}📁 로그 디렉토리 설정...${NC}"
LOG_DIR="/var/log/filewallball"

if [ ! -d "$LOG_DIR" ]; then
    if sudo mkdir -p "$LOG_DIR" 2>/dev/null; then
        sudo chown lanco:lanco "$LOG_DIR"
        echo -e "${GREEN}✅ 로그 디렉토리 생성: $LOG_DIR${NC}"
    else
        echo -e "${YELLOW}⚠️  sudo 권한이 없어 로컬 로그 디렉토리 사용: ./logs${NC}"
        LOG_DIR="./logs"
        mkdir -p "$LOG_DIR"
    fi
else
    echo -e "${GREEN}✅ 로그 디렉토리 이미 존재: $LOG_DIR${NC}"
fi

# 3. 환경변수 파일 업데이트
echo -e "${BLUE}⚙️  환경변수 설정...${NC}"
if [ -f ".env" ]; then
    # 기존 SECRET_KEY 제거 후 새로운 값 추가
    sed -i '/^SECRET_KEY=/d' .env
    echo "SECRET_KEY=\"$SECRET_KEY\"" >> .env
    
    # LOG_FILE 설정
    sed -i '/^LOG_FILE=/d' .env
    echo "LOG_FILE=\"$LOG_DIR/app.log\"" >> .env
    
    echo -e "${GREEN}✅ .env 파일 업데이트 완료${NC}"
else
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다. .env.simple을 복사합니다.${NC}"
    cp .env.simple .env
    echo "SECRET_KEY=\"$SECRET_KEY\"" >> .env
    echo "LOG_FILE=\"$LOG_DIR/app.log\"" >> .env
fi

# 4. systemd 서비스 파일 생성
echo -e "${BLUE}🔧 systemd 서비스 파일 생성...${NC}"
SERVICE_FILE="filewallball.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=FileWallBall API Server
After=network.target

[Service]
Type=exec
User=lanco
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/uvicorn app.main_simple:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=DB_HOST=pathcosmos.iptime.org
Environment=DB_PORT=33377
Environment=DB_NAME=filewallball
Environment=DB_USER=filewallball
Environment=DB_PASSWORD="jK9#zQ$p&2@f!L7^xY*"
Environment=SECRET_KEY="$SECRET_KEY"
Environment=LOG_FILE="$LOG_DIR/app.log"
Environment=UPLOAD_DIR="$PROJECT_DIR/uploads"

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ systemd 서비스 파일 생성 완료${NC}"

# 5. systemd 서비스 설치 (sudo 권한이 있는 경우)
if sudo systemctl --version &> /dev/null; then
    echo -e "${BLUE}📝 systemd 서비스 등록...${NC}"
    if sudo cp "$SERVICE_FILE" "/etc/systemd/system/" 2>/dev/null; then
        sudo systemctl daemon-reload
        sudo systemctl enable filewallball
        echo -e "${GREEN}✅ systemd 서비스 등록 완료${NC}"
        echo -e "${BLUE}   서비스 시작: sudo systemctl start filewallball${NC}"
        echo -e "${BLUE}   서비스 상태: sudo systemctl status filewallball${NC}"
    else
        echo -e "${YELLOW}⚠️  systemd 서비스 등록 실패 (권한 부족)${NC}"
        echo -e "${YELLOW}   수동으로 다음 명령어를 실행하세요:${NC}"
        echo -e "${YELLOW}   sudo cp $SERVICE_FILE /etc/systemd/system/${NC}"
        echo -e "${YELLOW}   sudo systemctl daemon-reload${NC}"
        echo -e "${YELLOW}   sudo systemctl enable filewallball${NC}"
    fi
fi

# 6. 방화벽 설정 안내
echo -e "${BLUE}🔥 방화벽 설정 안내...${NC}"
if command -v ufw &> /dev/null; then
    echo -e "${YELLOW}   UFW 방화벽 설정:${NC}"
    echo -e "${YELLOW}   sudo ufw allow 8000/tcp${NC}"
elif command -v iptables &> /dev/null; then
    echo -e "${YELLOW}   iptables 방화벽 설정:${NC}"
    echo -e "${YELLOW}   sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT${NC}"
fi

# 7. 설정 완료 확인
echo ""
echo -e "${GREEN}🎉 FileWallBall 운영환경 설정 완료!${NC}"
echo ""
echo -e "${BLUE}📋 설정 요약:${NC}"
echo -e "   SECRET_KEY: ${GREEN}생성됨 (32자)${NC}"
echo -e "   로그 파일: ${GREEN}$LOG_DIR/app.log${NC}"
echo -e "   서비스 파일: ${GREEN}$SERVICE_FILE${NC}"
echo -e "   업로드 디렉토리: ${GREEN}$PROJECT_DIR/uploads${NC}"
echo ""
echo -e "${BLUE}🚀 서비스 시작 방법:${NC}"
echo -e "   1. systemd 사용: ${GREEN}sudo systemctl start filewallball${NC}"
echo -e "   2. 직접 실행: ${GREEN}./start_app.sh${NC}"
echo ""
echo -e "${BLUE}📊 상태 확인:${NC}"
echo -e "   - API 테스트: ${GREEN}curl http://localhost:8000/health${NC}"
echo -e "   - 로그 확인: ${GREEN}tail -f $LOG_DIR/app.log${NC}"
echo -e "   - 서비스 상태: ${GREEN}sudo systemctl status filewallball${NC}"
echo ""
echo -e "${YELLOW}⚠️  추가 설정이 필요한 항목:${NC}"
echo -e "   - CORS 도메인 제한 (CORS_ORIGINS 환경변수)"
echo -e "   - Nginx 리버스 프록시 설정"
echo -e "   - 데이터베이스 백업 스크립트"
echo -e "   - 로그 순환 설정 (logrotate)"
echo ""
echo -e "${BLUE}📖 자세한 내용은 INFRASTRUCTURE_CHECKLIST.md 참고${NC}"