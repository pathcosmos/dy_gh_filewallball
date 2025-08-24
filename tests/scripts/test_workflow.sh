#!/bin/bash

# FileWallBall API 전체 워크플로우 테스트 스크립트
# 키 생성부터 파일 업로드, 다운로드, 검증까지의 전체 과정을 자동화

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
API_BASE_URL="http://127.0.0.1:8000"
LOG_FILE="workflow_test_$(date +%Y%m%d_%H%M%S).log"
START_TIME=$(date +%s)
TEST_FILE="workflow_test_file.txt"
TEST_CONTENT="This is a test file for FileWallBall API workflow testing.\nGenerated at: $(date)\nRandom data: $RANDOM"

# 로그 함수
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $timestamp: $message" | tee -a "$LOG_FILE"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $timestamp: $message" | tee -a "$LOG_FILE"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $timestamp: $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $timestamp: $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# 에러 처리 함수
handle_error() {
    local exit_code=$?
    local line_number=$1
    log "ERROR" "스크립트 실행 중 오류 발생 (라인: $line_number, 종료 코드: $exit_code)"
    cleanup
    exit $exit_code
}

# 정리 함수
cleanup() {
    log "INFO" "테스트 파일 정리 중..."
    rm -f "$TEST_FILE" "downloaded_$TEST_FILE" 2>/dev/null || true
    log "INFO" "정리 완료"
}

# jq 설치 확인
check_dependencies() {
    log "INFO" "의존성 확인 중..."
    
    if ! command -v jq &> /dev/null; then
        log "ERROR" "jq가 설치되지 않았습니다. jq 1.6+ 버전을 설치해주세요."
        exit 1
    fi
    
    jq_version=$(jq --version | cut -d'-' -f2)
    log "INFO" "jq 버전: $jq_version"
    
    if ! command -v curl &> /dev/null; then
        log "ERROR" "curl이 설치되지 않았습니다."
        exit 1
    fi
    
    log "SUCCESS" "의존성 확인 완료"
}

# API 헬스체크
health_check() {
    log "INFO" "API 헬스체크 시작..."
    
    local max_retries=5
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s "$API_BASE_URL/health" > /dev/null 2>&1; then
            local health_response=$(curl -s "$API_BASE_URL/health")
            local status=$(echo "$health_response" | jq -r '.status')
            
            if [ "$status" = "healthy" ]; then
                local version=$(echo "$health_response" | jq -r '.version')
                log "SUCCESS" "API 헬스체크 성공 - 버전: $version"
                return 0
            fi
        fi
        
        retry_count=$((retry_count + 1))
        log "WARNING" "API 응답 대기 중... (시도 $retry_count/$max_retries)"
        sleep 2
    done
    
    log "ERROR" "API 헬스체크 실패 - 최대 재시도 횟수 초과"
    return 1
}

# 프로젝트 키 생성
generate_project_key() {
    log "INFO" "프로젝트 키 생성 시작..."
    
    local project_name="workflow_test_$(date +%Y%m%d_%H%M%S)"
    local request_date=$(date +%Y%m%d)
    
    local keygen_response=$(curl -s -X POST "$API_BASE_URL/keygen" \
        -H "Content-Type: application/json" \
        -H "X-Keygen-Auth: dy2025@fileBucket" \
        -d "{
            \"project_name\": \"$project_name\",
            \"request_date\": \"$request_date\"
        }")
    
    if [ $? -eq 0 ]; then
        local project_key=$(echo "$keygen_response" | jq -r '.project_key')
        local project_id=$(echo "$keygen_response" | jq -r '.project_id')
        
        if [ "$project_key" != "null" ] && [ "$project_key" != "" ]; then
            log "SUCCESS" "프로젝트 키 생성 성공 - ID: $project_id, 키: ${project_key:0:8}..."
            echo "$project_key"
            return 0
        fi
    fi
    
    log "ERROR" "프로젝트 키 생성 실패"
    return 1
}

# 테스트 파일 생성
create_test_file() {
    log "INFO" "테스트 파일 생성 중..."
    
    echo -e "$TEST_CONTENT" > "$TEST_FILE"
    
    if [ -f "$TEST_FILE" ]; then
        local file_size=$(stat -c%s "$TEST_FILE" 2>/dev/null || stat -f%z "$TEST_FILE" 2>/dev/null)
        local file_hash=$(md5sum "$TEST_FILE" 2>/dev/null | cut -d' ' -f1 || md5 "$TEST_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d ' ')
        
        log "SUCCESS" "테스트 파일 생성 완료 - 크기: $file_size bytes, MD5: $file_hash"
        echo "$file_hash"
        return 0
    else
        log "ERROR" "테스트 파일 생성 실패"
        return 1
    fi
}

# 파일 업로드
upload_file() {
    local project_key=$1
    log "INFO" "파일 업로드 시작..."
    
    local upload_response=$(curl -s -X POST "$API_BASE_URL/upload" \
        -F "file=@$TEST_FILE")
    
    if [ $? -eq 0 ]; then
        local file_id=$(echo "$upload_response" | jq -r '.file_id')
        local filename=$(echo "$upload_response" | jq -r '.filename')
        local file_size=$(echo "$upload_response" | jq -r '.file_size')
        
        if [ "$file_id" != "null" ] && [ "$file_id" != "" ]; then
            log "SUCCESS" "파일 업로드 성공 - ID: $file_id, 파일명: $filename, 크기: $file_size bytes"
            echo "$file_id"
            return 0
        fi
    fi
    
    log "ERROR" "파일 업로드 실패"
    return 1
}

# 파일 정보 조회
get_file_info() {
    local file_id=$1
    log "INFO" "파일 정보 조회 시작 (ID: $file_id)..."
    
    local file_info_response=$(curl -s "$API_BASE_URL/files/$file_id")
    
    if [ $? -eq 0 ]; then
        local filename=$(echo "$file_info_response" | jq -r '.filename')
        local file_size=$(echo "$file_info_response" | jq -r '.file_size')
        local mime_type=$(echo "$file_info_response" | jq -r '.mime_type')
        
        if [ "$filename" != "null" ] && [ "$filename" != "" ]; then
            log "SUCCESS" "파일 정보 조회 성공 - 파일명: $filename, 크기: $file_size bytes, MIME: $mime_type"
            return 0
        fi
    fi
    
    log "ERROR" "파일 정보 조회 실패"
    return 1
}

# 파일 다운로드
download_file() {
    local file_id=$1
    log "INFO" "파일 다운로드 시작 (ID: $file_id)..."
    
    if curl -s -o "downloaded_$TEST_FILE" "$API_BASE_URL/download/$file_id"; then
        if [ -f "downloaded_$TEST_FILE" ]; then
            local downloaded_size=$(stat -c%s "downloaded_$TEST_FILE" 2>/dev/null || stat -f%z "downloaded_$TEST_FILE" 2>/dev/null)
            log "SUCCESS" "파일 다운로드 성공 - 크기: $downloaded_size bytes"
            return 0
        fi
    fi
    
    log "ERROR" "파일 다운로드 실패"
    return 1
}

# 파일 무결성 검증
verify_file_integrity() {
    local original_hash=$1
    log "INFO" "파일 무결성 검증 시작..."
    
    if [ -f "downloaded_$TEST_FILE" ]; then
        local downloaded_hash=$(md5sum "downloaded_$TEST_FILE" 2>/dev/null | cut -d' ' -f1 || md5 "downloaded_$TEST_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d ' ')
        
        if [ "$original_hash" = "$downloaded_hash" ]; then
            log "SUCCESS" "파일 무결성 검증 성공 - MD5 해시 일치: $downloaded_hash"
            return 0
        else
            log "ERROR" "파일 무결성 검증 실패 - 원본: $original_hash, 다운로드: $downloaded_hash"
            return 1
        fi
    else
        log "ERROR" "다운로드된 파일을 찾을 수 없음"
        return 1
    fi
}

# 파일 목록 조회
list_files() {
    log "INFO" "파일 목록 조회 시작..."
    
    local list_response=$(curl -s "$API_BASE_URL/files?limit=5")
    
    if [ $? -eq 0 ]; then
        local total_files=$(echo "$list_response" | jq -r '.total')
        local current_files=$(echo "$list_response" | jq -r '.files | length')
        
        if [ "$total_files" != "null" ] && [ "$total_files" != "" ]; then
            log "SUCCESS" "파일 목록 조회 성공 - 전체: $total_files개, 현재 페이지: $current_files개"
            return 0
        fi
    fi
    
    log "ERROR" "파일 목록 조회 실패"
    return 1
}

# 결과 리포트 생성
generate_report() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    log "INFO" "워크플로우 테스트 완료 - 총 소요 시간: ${duration}초"
    
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "FileWallBall API 워크플로우 테스트 결과" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "테스트 시작 시간: $(date -d @$START_TIME)" | tee -a "$LOG_FILE"
    echo "테스트 완료 시간: $(date -d @$end_time)" | tee -a "$LOG_FILE"
    echo "총 소요 시간: ${duration}초" | tee -a "$LOG_FILE"
    echo "로그 파일: $LOG_FILE" | tee -a "$LOG_FILE"
    
    if [ $duration -le 300 ]; then
        log "SUCCESS" "성능 요구사항 충족: 5분 이내 완료 (${duration}초)"
    else
        log "WARNING" "성능 요구사항 미충족: 5분 초과 (${duration}초)"
    fi
}

# 메인 실행 함수
main() {
    log "INFO" "FileWallBall API 워크플로우 테스트 시작"
    log "INFO" "로그 파일: $LOG_FILE"
    
    # 에러 핸들러 설정
    trap 'handle_error $LINENO' ERR
    
    # 1. 의존성 확인
    check_dependencies
    
    # 2. API 헬스체크
    health_check
    
    # 3. 프로젝트 키 생성
    local project_key=$(generate_project_key)
    
    # 4. 테스트 파일 생성
    local original_hash=$(create_test_file)
    
    # 5. 파일 업로드
    local file_id=$(upload_file "$project_key")
    
    # 변수 확인
    log "INFO" "업로드된 파일 ID: $file_id"
    
    # 6. 파일 정보 조회
    get_file_info "$file_id"
    
    # 7. 파일 다운로드
    download_file "$file_id"
    
    # 8. 파일 무결성 검증
    verify_file_integrity "$original_hash"
    
    # 9. 파일 목록 조회
    list_files
    
    # 10. 결과 리포트 생성
    generate_report
    
    log "SUCCESS" "모든 워크플로우 테스트 통과!"
}

# 스크립트 실행
main "$@"
