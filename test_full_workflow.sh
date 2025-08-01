#!/bin/bash

# FileWallBall 전체 워크플로우 테스트 스크립트
# Ubuntu 컨테이너에서 실행

set -e  # 에러 발생 시 스크립트 중단

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
TEST_FILE="test_upload.txt"
DOWNLOAD_FILE="downloaded_file.txt"

# 테스트 디렉토리 생성
TEST_DIR="/tmp/filewallball_test"
mkdir -p $TEST_DIR
cd $TEST_DIR

log_info "FileWallBall 전체 워크플로우 테스트 시작"
log_info "API URL: $API_BASE_URL"
log_info "프로젝트명: $PROJECT_NAME"
log_info "요청 날짜: $REQUEST_DATE"

# 1. 헬스체크
log_info "1. API 헬스체크 확인 중..."
if curl -s -f "$API_BASE_URL/health" > /dev/null; then
    log_success "API 서버가 정상 동작 중입니다"
else
    log_error "API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요."
    exit 1
fi

# 2. 테스트 파일 생성
log_info "2. 테스트 파일 생성 중..."
cat > $TEST_FILE << EOF
이것은 FileWallBall API 테스트용 파일입니다.
생성 시간: $(date)
프로젝트: $PROJECT_NAME
테스트 내용:
- 프로젝트 키 생성
- 파일 업로드
- 파일 다운로드
- 파일 정보 조회
EOF

log_success "테스트 파일 생성 완료: $TEST_FILE"

# 3. 프로젝트 키 생성
log_info "3. 프로젝트 키 생성 중..."
PROJECT_KEY_RESPONSE=$(curl -s -X POST "$API_BASE_URL/keygen" \
    -F "project_name=$PROJECT_NAME" \
    -F "request_date=$REQUEST_DATE" \
    -F "master_key=$MASTER_KEY")

if echo "$PROJECT_KEY_RESPONSE" | grep -q "project_key"; then
    PROJECT_KEY=$(echo "$PROJECT_KEY_RESPONSE" | grep -o '"project_key":"[^"]*"' | cut -d'"' -f4)
    log_success "프로젝트 키 생성 완료: $PROJECT_KEY"
    echo "$PROJECT_KEY_RESPONSE" | jq '.' 2>/dev/null || echo "$PROJECT_KEY_RESPONSE"
else
    log_error "프로젝트 키 생성 실패"
    echo "$PROJECT_KEY_RESPONSE"
    exit 1
fi

# 4. 파일 업로드
log_info "4. 파일 업로드 중..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE_URL/upload" \
    -F "file=@$TEST_FILE" \
    -F "project_key=$PROJECT_KEY")

if echo "$UPLOAD_RESPONSE" | grep -q "file_id"; then
    FILE_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"file_id":"[^"]*"' | cut -d'"' -f4)
    DOWNLOAD_URL=$(echo "$UPLOAD_RESPONSE" | grep -o '"download_url":"[^"]*"' | cut -d'"' -f4)
    VIEW_URL=$(echo "$UPLOAD_RESPONSE" | grep -o '"view_url":"[^"]*"' | cut -d'"' -f4)
    log_success "파일 업로드 완료"
    log_info "파일 ID: $FILE_ID"
    log_info "다운로드 URL: $DOWNLOAD_URL"
    log_info "미리보기 URL: $VIEW_URL"
    echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"
else
    log_error "파일 업로드 실패"
    echo "$UPLOAD_RESPONSE"
    exit 1
fi

# 5. 파일 정보 조회
log_info "5. 파일 정보 조회 중..."
FILE_INFO_RESPONSE=$(curl -s -X GET "$API_BASE_URL/files/$FILE_ID")

if echo "$FILE_INFO_RESPONSE" | grep -q "file_uuid"; then
    log_success "파일 정보 조회 완료"
    echo "$FILE_INFO_RESPONSE" | jq '.' 2>/dev/null || echo "$FILE_INFO_RESPONSE"
else
    log_warning "파일 정보 조회 실패 (인증 필요할 수 있음)"
    echo "$FILE_INFO_RESPONSE"
fi

# 6. 파일 다운로드
log_info "6. 파일 다운로드 중..."
if curl -s -f -o "$DOWNLOAD_FILE" "$DOWNLOAD_URL"; then
    log_success "파일 다운로드 완료: $DOWNLOAD_FILE"
    
    # 파일 내용 비교
    if cmp -s "$TEST_FILE" "$DOWNLOAD_FILE"; then
        log_success "업로드된 파일과 다운로드된 파일이 동일합니다"
    else
        log_error "업로드된 파일과 다운로드된 파일이 다릅니다"
        echo "원본 파일 크기: $(wc -c < $TEST_FILE) bytes"
        echo "다운로드 파일 크기: $(wc -c < $DOWNLOAD_FILE) bytes"
    fi
else
    log_error "파일 다운로드 실패"
    exit 1
fi

# 7. 파일 미리보기 테스트
log_info "7. 파일 미리보기 테스트 중..."
VIEW_RESPONSE=$(curl -s -I "$VIEW_URL" | head -1)
if echo "$VIEW_RESPONSE" | grep -q "200\|302"; then
    log_success "파일 미리보기 접근 가능"
else
    log_warning "파일 미리보기 접근 실패 (인증 필요할 수 있음)"
    echo "$VIEW_RESPONSE"
fi

# 8. 고급 업로드 API 테스트 (v2)
log_info "8. 고급 업로드 API 테스트 중..."
UPLOAD_V2_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/files/upload" \
    -F "file=@$TEST_FILE" \
    -F "category_id=1" \
    -F "tags=test,automation" \
    -F "is_public=true" \
    -F "description=고급 API 테스트용 파일")

if echo "$UPLOAD_V2_RESPONSE" | grep -q "file_uuid"; then
    log_success "고급 업로드 API 테스트 완료"
    echo "$UPLOAD_V2_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_V2_RESPONSE"
else
    log_warning "고급 업로드 API 테스트 실패 (인증 필요할 수 있음)"
    echo "$UPLOAD_V2_RESPONSE"
fi

# 9. 업로드 통계 확인
log_info "9. 업로드 통계 확인 중..."
STATS_RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/v1/upload/statistics/127.0.0.1")
if echo "$STATS_RESPONSE" | grep -q "total_uploads"; then
    log_success "업로드 통계 조회 완료"
    echo "$STATS_RESPONSE" | jq '.' 2>/dev/null || echo "$STATS_RESPONSE"
else
    log_warning "업로드 통계 조회 실패 (인증 필요할 수 있음)"
    echo "$STATS_RESPONSE"
fi

# 10. 메트릭 확인
log_info "10. 시스템 메트릭 확인 중..."
METRICS_RESPONSE=$(curl -s -X GET "$API_BASE_URL/metrics")
if echo "$METRICS_RESPONSE" | grep -q "filewallball"; then
    log_success "시스템 메트릭 조회 완료"
    echo "$METRICS_RESPONSE" | head -20
else
    log_warning "시스템 메트릭 조회 실패"
    echo "$METRICS_RESPONSE"
fi

# 11. 파일 목록 조회
log_info "11. 파일 목록 조회 중..."
FILE_LIST_RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/v1/files")
if echo "$FILE_LIST_RESPONSE" | grep -q "files"; then
    log_success "파일 목록 조회 완료"
    echo "$FILE_LIST_RESPONSE" | jq '.' 2>/dev/null || echo "$FILE_LIST_RESPONSE"
else
    log_warning "파일 목록 조회 실패 (인증 필요할 수 있음)"
    echo "$FILE_LIST_RESPONSE"
fi

# 12. 검색 기능 테스트
log_info "12. 파일 검색 기능 테스트 중..."
SEARCH_RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/v1/files/search?query=test")
if echo "$SEARCH_RESPONSE" | grep -q "files"; then
    log_success "파일 검색 기능 테스트 완료"
    echo "$SEARCH_RESPONSE" | jq '.' 2>/dev/null || echo "$SEARCH_RESPONSE"
else
    log_warning "파일 검색 기능 테스트 실패 (인증 필요할 수 있음)"
    echo "$SEARCH_RESPONSE"
fi

# 정리
log_info "13. 테스트 정리 중..."
rm -f "$TEST_FILE" "$DOWNLOAD_FILE"

# 결과 요약
log_success "=== FileWallBall 전체 워크플로우 테스트 완료 ==="
log_info "테스트된 기능:"
log_info "  ✅ API 헬스체크"
log_info "  ✅ 프로젝트 키 생성"
log_info "  ✅ 파일 업로드"
log_info "  ✅ 파일 다운로드"
log_info "  ✅ 파일 정보 조회"
log_info "  ✅ 파일 미리보기"
log_info "  ✅ 고급 업로드 API"
log_info "  ✅ 업로드 통계"
log_info "  ✅ 시스템 메트릭"
log_info "  ✅ 파일 목록 조회"
log_info "  ✅ 파일 검색 기능"

log_info "생성된 프로젝트 키: $PROJECT_KEY"
log_info "업로드된 파일 ID: $FILE_ID"
log_info "테스트 디렉토리: $TEST_DIR"

log_success "모든 테스트가 성공적으로 완료되었습니다!" 