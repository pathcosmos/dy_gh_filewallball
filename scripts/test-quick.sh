#!/bin/bash

set -e

# FileWallBall 빠른 테스트 스크립트
echo "⚡ FileWallBall 빠른 테스트 시작..."

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

# 함수: API 헬스체크
check_api_health() {
    log_step "API 서비스 헬스체크..."
    
    local max_attempts=10  # 빠른 테스트는 더 짧은 대기 시간
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$API_BASE_URL/health" > /dev/null 2>&1; then
            log_success "API 서비스가 준비되었습니다!"
            return 0
        fi
        
        log_info "API 서비스 대기 중... (시도 $attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done
    
    log_error "API 서비스 헬스체크 실패!"
    return 1
}

# API 헬스체크
check_api_health

log_step "빠른 테스트 시작..."

# 1. 기본 헬스체크
run_test "quick_health_check" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/health'" \
    "200"

# 2. 메트릭스 엔드포인트 (빠른 확인)
run_test "quick_metrics" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/metrics'" \
    "200"

# 3. API 문서 엔드포인트
run_test "quick_api_docs" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/docs'" \
    "200"

# 4. 빠른 파일 업로드 테스트 (V1)
log_step "빠른 V1 업로드 테스트..."
TEST_FILE="$UPLOAD_DIR/quick_test.txt"
echo "Quick test content" > "$TEST_FILE"

run_test "quick_v1_upload" \
    "curl -s -w 'HTTP/%{http_code}' -X POST -F 'file=@$TEST_FILE' '$API_BASE_URL/upload'" \
    "200"

# 5. 빠른 파일 업로드 테스트 (V2)
log_step "빠른 V2 업로드 테스트..."
TEST_FILE_V2="$UPLOAD_DIR/quick_test_v2.txt"
echo "Quick test content for V2" > "$TEST_FILE_V2"

run_test "quick_v2_upload" \
    "curl -s -w 'HTTP/%{http_code}' -X POST -F 'file=@$TEST_FILE_V2' '$API_BASE_URL/api/v1/files/upload'" \
    "200"

# 6. 파일 목록 조회 (빠른 확인)
run_test "quick_files_list" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/api/v1/files/list'" \
    "200"

# 7. 보안 헤더 테스트 (빠른 확인)
run_test "quick_security_headers" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/api/v1/security/headers-test'" \
    "200"

# 8. 상세 메트릭스 (빠른 확인)
run_test "quick_detailed_metrics" \
    "curl -s -w 'HTTP/%{http_code}' -o /dev/null '$API_BASE_URL/api/v1/metrics/detailed'" \
    "200"

# 테스트 결과 요약
log_step "빠른 테스트 결과 요약..."

echo ""
echo "📊 빠른 테스트 결과:"
echo "=================="
echo "총 테스트 수: $TOTAL_TESTS"
echo "통과: $PASSED_TESTS"
echo "실패: $FAILED_TESTS"
echo "성공률: $((PASSED_TESTS * 100 / TOTAL_TESTS))%"
echo ""

# 결과를 파일로 저장
cat > "$TEST_RESULTS_DIR/quick_test_summary.txt" << EOF
빠른 테스트 결과 요약
====================
실행 시간: $(date)
API 베이스 URL: $API_BASE_URL
총 테스트 수: $TOTAL_TESTS
통과: $PASSED_TESTS
실패: $FAILED_TESTS
성공률: $((PASSED_TESTS * 100 / TOTAL_TESTS))%

빠른 테스트 내용:
1. API 헬스체크
2. 메트릭스 엔드포인트 확인
3. API 문서 엔드포인트 확인
4. V1 업로드 API 테스트
5. V2 업로드 API 테스트
6. 파일 목록 조회
7. 보안 헤더 테스트
8. 상세 메트릭스 확인

이 테스트는 기본적인 API 기능만 빠르게 확인합니다.
전체 기능 테스트를 원한다면 test-full-workflow.sh를 실행하세요.
EOF

# 정리
rm -f "$TEST_FILE" "$TEST_FILE_V2" 2>/dev/null || true

# 실패한 테스트가 있으면 종료 코드 1 반환
if [ $FAILED_TESTS -gt 0 ]; then
    log_error "일부 빠른 테스트가 실패했습니다!"
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
    log_success "모든 빠른 테스트가 통과했습니다!"
    echo ""
    echo "💡 팁: 전체 기능을 테스트하려면 다음 명령어를 실행하세요:"
    echo "   ./scripts/test-full-workflow.sh"
    exit 0
fi 