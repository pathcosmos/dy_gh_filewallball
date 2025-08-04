#!/bin/bash

set -e

# FileWallBall 전체 워크플로우 테스트 스크립트
echo "🔄 FileWallBall 전체 워크플로우 테스트 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 함수: 로그 출력
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 기본 설정
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TEST_RESULTS_DIR="${TEST_RESULTS_DIR:-test_results}"
UPLOAD_DIR="${UPLOAD_DIR:-test_uploads}"

# 테스트 결과 디렉토리 생성
mkdir -p "$TEST_RESULTS_DIR" "$UPLOAD_DIR"

# 테스트 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 함수: 테스트 실행 및 결과 기록
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_status="${3:-200}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_step "실행 중: $test_name"
    
    # 테스트 실행
    if eval "$test_command" > "$TEST_RESULTS_DIR/${test_name}.log" 2>&1; then
        # HTTP 상태 코드 확인
        if grep -q "HTTP/.* $expected_status" "$TEST_RESULTS_DIR/${test_name}.log" 2>/dev/null; then
            log_success "통과: $test_name"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            log_error "실패: $test_name (예상 상태: $expected_status)"
            cat "$TEST_RESULTS_DIR/${test_name}.log"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        log_error "실패: $test_name"
        cat "$TEST_RESULTS_DIR/${test_name}.log"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 함수: JSON 응답에서 값 추출
extract_json_value() {
    local json="$1"
    local key="$2"
    echo "$json" | jq -r ".$key" 2>/dev/null || echo ""
}

# 함수: API 헬스체크
check_api_health() {
    log_step "API 서비스 헬스체크..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$API_BASE_URL/health" > /dev/null 2>&1; then
            log_success "API 서비스가 준비되었습니다!"
            return 0
        fi
        
        log_info "API 서비스 대기 중... (시도 $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "API 서비스 헬스체크 실패!"
    return 1
}

# API 헬스체크
check_api_health

log_step "전체 워크플로우 테스트 시작..."

# 테스트 파일 생성
TEST_FILE="$UPLOAD_DIR/workflow_test.txt"
TEST_CONTENT="This is a test file for the complete FileWallBall workflow test. Created at $(date)."
echo "$TEST_CONTENT" > "$TEST_FILE"

# 1. 기본 헬스체크
run_test "workflow_health_check" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/health'" \
    "200"

# 2. V1 업로드 API로 파일 업로드
log_step "V1 업로드 API 테스트..."
V1_UPLOAD_RESPONSE=$(curl -s -w 'HTTP/%{http_code}' -X POST -F "file=@$TEST_FILE" "$API_BASE_URL/upload")
V1_FILE_ID=$(extract_json_value "$V1_UPLOAD_RESPONSE" "file_id")

if [ -n "$V1_FILE_ID" ] && [ "$V1_FILE_ID" != "null" ]; then
    log_success "V1 업로드 성공: 파일 ID = $V1_FILE_ID"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_error "V1 업로드 실패"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 3. V1 파일 정보 조회
if [ -n "$V1_FILE_ID" ] && [ "$V1_FILE_ID" != "null" ]; then
    run_test "v1_file_info" \
        "curl -s -w 'HTTP/%{http_code}' '$API_BASE_URL/files/$V1_FILE_ID'" \
        "200"
fi

# 4. V1 파일 다운로드
if [ -n "$V1_FILE_ID" ] && [ "$V1_FILE_ID" != "null" ]; then
    run_test "v1_file_download" \
        "curl -s -w 'HTTP/%{http_code}' -o '$TEST_RESULTS_DIR/v1_downloaded.txt' '$API_BASE_URL/download/$V1_FILE_ID'" \
        "200"
    
    # 다운로드된 파일 내용 확인
    if [ -f "$TEST_RESULTS_DIR/v1_downloaded.txt" ]; then
        if diff "$TEST_FILE" "$TEST_RESULTS_DIR/v1_downloaded.txt" > /dev/null; then
            log_success "V1 다운로드 파일 내용 일치"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_error "V1 다운로드 파일 내용 불일치"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi
fi

# 5. V2 업로드 API로 파일 업로드
log_step "V2 업로드 API 테스트..."
V2_UPLOAD_RESPONSE=$(curl -s -w 'HTTP/%{http_code}' -X POST -F "file=@$TEST_FILE" "$API_BASE_URL/api/v1/files/upload")
V2_FILE_ID=$(extract_json_value "$V2_UPLOAD_RESPONSE" "file_id")

if [ -n "$V2_FILE_ID" ] && [ "$V2_FILE_ID" != "null" ]; then
    log_success "V2 업로드 성공: 파일 ID = $V2_FILE_ID"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_error "V2 업로드 실패"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 6. V2 파일 정보 조회
if [ -n "$V2_FILE_ID" ] && [ "$V2_FILE_ID" != "null" ]; then
    run_test "v2_file_info" \
        "curl -s -w 'HTTP/%{http_code}' '$API_BASE_URL/api/v1/files/$V2_FILE_ID'" \
        "200"
fi

# 7. V2 파일 다운로드
if [ -n "$V2_FILE_ID" ] && [ "$V2_FILE_ID" != "null" ]; then
    run_test "v2_file_download" \
        "curl -s -w 'HTTP/%{http_code}' -o '$TEST_RESULTS_DIR/v2_downloaded.txt' '$API_BASE_URL/api/v1/files/$V2_FILE_ID/download'" \
        "200"
    
    # 다운로드된 파일 내용 확인
    if [ -f "$TEST_RESULTS_DIR/v2_downloaded.txt" ]; then
        if diff "$TEST_FILE" "$TEST_RESULTS_DIR/v2_downloaded.txt" > /dev/null; then
            log_success "V2 다운로드 파일 내용 일치"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_error "V2 다운로드 파일 내용 불일치"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi
fi

# 8. 파일 목록 조회
run_test "files_list" \
    "curl -s -w 'HTTP/%{http_code}' '$API_BASE_URL/api/v1/files/list'" \
    "200"

# 9. 파일 미리보기 (V1)
if [ -n "$V1_FILE_ID" ] && [ "$V1_FILE_ID" != "null" ]; then
    run_test "v1_file_preview" \
        "curl -s -w 'HTTP/%{http_code}' '$API_BASE_URL/view/$V1_FILE_ID'" \
        "200"
fi

# 10. 파일 미리보기 (V2)
if [ -n "$V2_FILE_ID" ] && [ "$V2_FILE_ID" != "null" ]; then
    run_test "v2_file_preview" \
        "curl -s -w 'HTTP/%{http_code}' '$API_BASE_URL/api/v1/files/$V2_FILE_ID/preview'" \
        "200"
fi

# 11. 파일 삭제 (V1)
if [ -n "$V1_FILE_ID" ] && [ "$V1_FILE_ID" != "null" ]; then
    run_test "v1_file_delete" \
        "curl -s -w 'HTTP/%{http_code}' -X DELETE '$API_BASE_URL/files/$V1_FILE_ID'" \
        "200"
fi

# 12. 파일 삭제 (V2)
if [ -n "$V2_FILE_ID" ] && [ "$V2_FILE_ID" != "null" ]; then
    run_test "v2_file_delete" \
        "curl -s -w 'HTTP/%{http_code}' -X DELETE '$API_BASE_URL/api/v1/files/$V2_FILE_ID'" \
        "200"
fi

# 13. 삭제된 파일 접근 시도 (404 확인)
if [ -n "$V1_FILE_ID" ] && [ "$V1_FILE_ID" != "null" ]; then
    run_test "v1_deleted_file_access" \
        "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/files/$V1_FILE_ID'" \
        "404"
fi

if [ -n "$V2_FILE_ID" ] && [ "$V2_FILE_ID" != "null" ]; then
    run_test "v2_deleted_file_access" \
        "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/api/v1/files/$V2_FILE_ID'" \
        "404"
fi

# 14. 메트릭스 확인
run_test "workflow_metrics" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/metrics'" \
    "200"

# 15. 상세 메트릭스 확인
run_test "workflow_detailed_metrics" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/api/v1/metrics/detailed'" \
    "200"

# 테스트 결과 요약
log_step "워크플로우 테스트 결과 요약..."

echo ""
echo "📊 전체 워크플로우 테스트 결과:"
echo "============================="
echo "총 테스트 수: $TOTAL_TESTS"
echo "통과: $PASSED_TESTS"
echo "실패: $FAILED_TESTS"
echo "성공률: $((PASSED_TESTS * 100 / TOTAL_TESTS))%"
echo ""

# 결과를 파일로 저장
cat > "$TEST_RESULTS_DIR/workflow_test_summary.txt" << EOF
전체 워크플로우 테스트 결과 요약
================================
실행 시간: $(date)
API 베이스 URL: $API_BASE_URL
테스트 파일: $TEST_FILE
V1 파일 ID: $V1_FILE_ID
V2 파일 ID: $V2_FILE_ID
총 테스트 수: $TOTAL_TESTS
통과: $PASSED_TESTS
실패: $FAILED_TESTS
성공률: $((PASSED_TESTS * 100 / TOTAL_TESTS))%

테스트 세부사항:
$(ls -la "$TEST_RESULTS_DIR"/*.log 2>/dev/null | wc -l) 개의 상세 로그 파일이 생성되었습니다.

워크플로우 테스트 내용:
1. API 헬스체크
2. V1 업로드 API 테스트
3. V1 파일 정보 조회
4. V1 파일 다운로드 및 내용 검증
5. V2 업로드 API 테스트
6. V2 파일 정보 조회
7. V2 파일 다운로드 및 내용 검증
8. 파일 목록 조회
9. 파일 미리보기 (V1/V2)
10. 파일 삭제 (V1/V2)
11. 삭제된 파일 접근 시도 (404 확인)
12. 메트릭스 확인
13. 상세 메트릭스 확인
EOF

# 정리
rm -f "$TEST_FILE" "$TEST_RESULTS_DIR/v1_downloaded.txt" "$TEST_RESULTS_DIR/v2_downloaded.txt" 2>/dev/null || true

# 실패한 테스트가 있으면 종료 코드 1 반환
if [ $FAILED_TESTS -gt 0 ]; then
    log_error "일부 워크플로우 테스트가 실패했습니다!"
    echo ""
    echo "실패한 테스트 로그:"
    for log_file in "$TEST_RESULTS_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            echo "--- $(basename "$log_file") ---"
            cat "$log_file"
            echo ""
        fi
    done
    exit 1
else
    log_success "모든 워크플로우 테스트가 통과했습니다!"
    exit 0
fi 