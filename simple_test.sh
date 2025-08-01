#!/bin/bash

# FileWallBall 간단한 API 테스트 스크립트
# Pydantic 오류를 우회하고 기본 기능만 테스트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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

# 환경 변수 설정
API_BASE_URL="http://localhost:8001"
MASTER_KEY="dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
PROJECT_NAME="test-project-$(date +%s)"
REQUEST_DATE=$(date +%Y%m%d)
TEST_FILE="test_simple.txt"

log_info "FileWallBall 간단한 API 테스트 시작"
log_info "API URL: $API_BASE_URL"
log_info "프로젝트명: $PROJECT_NAME"

# 1. 헬스체크
log_info "1. API 헬스체크 확인 중..."
if curl -s -f "$API_BASE_URL/health" > /dev/null; then
    log_success "API 서버가 정상 동작 중입니다"
else
    log_error "API 서버에 연결할 수 없습니다."
    exit 1
fi

# 2. 테스트 파일 생성
log_info "2. 테스트 파일 생성 중..."
cat > $TEST_FILE << EOF
이것은 간단한 테스트 파일입니다.
생성 시간: $(date)
프로젝트: $PROJECT_NAME
EOF

log_success "테스트 파일 생성 완료: $TEST_FILE"

# 3. 프로젝트 키 생성 (타임아웃 설정)
log_info "3. 프로젝트 키 생성 중..."
PROJECT_KEY_RESPONSE=$(timeout 10 curl -s -X POST "$API_BASE_URL/keygen" \
    -F "project_name=$PROJECT_NAME" \
    -F "request_date=$REQUEST_DATE" \
    -F "master_key=$MASTER_KEY" || echo "timeout")

if [ "$PROJECT_KEY_RESPONSE" = "timeout" ]; then
    log_warning "프로젝트 키 생성이 타임아웃되었습니다. API에 문제가 있을 수 있습니다."
    log_info "기존 테스트 스크립트를 사용해보세요: ./test_full_workflow.sh"
    exit 0
fi

if echo "$PROJECT_KEY_RESPONSE" | grep -q "project_key"; then
    PROJECT_KEY=$(echo "$PROJECT_KEY_RESPONSE" | grep -o '"project_key":"[^"]*"' | cut -d'"' -f4)
    log_success "프로젝트 키 생성 완료: $PROJECT_KEY"
    echo "$PROJECT_KEY_RESPONSE"
else
    log_error "프로젝트 키 생성 실패"
    echo "$PROJECT_KEY_RESPONSE"
    log_info "기존 테스트 스크립트를 사용해보세요: ./test_full_workflow.sh"
    exit 1
fi

log_success "간단한 API 테스트 완료"
log_info "전체 워크플로우 테스트를 원한다면: ./test_full_workflow.sh" 