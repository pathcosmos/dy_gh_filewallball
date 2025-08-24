#!/bin/bash

# FileWallBall API 시작 스크립트
# ==============================

set -e

# 색상 설정
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 FileWallBall API 시작...${NC}"

# 업로드 디렉토리 생성
if [ ! -d "uploads" ]; then
    echo -e "${BLUE}📁 업로드 디렉토리 생성...${NC}"
    mkdir -p uploads
    chmod 755 uploads
fi

# 데이터베이스 연결 테스트
echo -e "${BLUE}🔍 데이터베이스 연결 테스트...${NC}"
if uv run python test_db_connection.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 데이터베이스 연결 성공${NC}"
else
    echo -e "${RED}❌ 데이터베이스 연결 실패${NC}"
    echo "데이터베이스 연결을 확인해주세요."
    exit 1
fi

# 애플리케이션 시작
echo -e "${GREEN}🌟 FileWallBall API 시작 중...${NC}"
echo -e "${GREEN}📚 API 문서: http://localhost:8000/docs${NC}"
echo -e "${GREEN}❤️  상태 확인: http://localhost:8000/health${NC}"
echo -e "${GREEN}📁 파일 업로드: http://localhost:8000/upload${NC}"
echo ""
echo -e "${BLUE}Ctrl+C로 서버를 중지할 수 있습니다.${NC}"
echo ""

# 서버 시작
uv run uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 --reload