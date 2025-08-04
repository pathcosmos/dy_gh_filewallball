#!/bin/bash

# FileWallBall 테스트 실행 스크립트

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

# 도움말 함수
show_help() {
    echo "FileWallBall 테스트 실행 스크립트"
    echo ""
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  quick     - 빠른 테스트 실행 (기본값)"
    echo "  full      - 전체 워크플로우 테스트 실행"
    echo "  build     - 테스트 컨테이너만 빌드"
    echo "  clean     - 테스트 환경 정리"
    echo "  dev       - 개발 환경 전체 시작"
    echo "  stop      - 모든 서비스 중지"
    echo "  help      - 이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 quick    # 빠른 테스트"
    echo "  $0 full     # 전체 테스트"
    echo "  $0 dev      # 개발 환경 시작"
}

# Docker 및 Docker Compose 확인
check_dependencies() {
    log_info "의존성 확인 중..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되지 않았습니다."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose가 설치되지 않았습니다."
        exit 1
    fi

    log_success "의존성 확인 완료"
}

# Docker Compose 명령어 결정
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

# 테스트 컨테이너 빌드
build_test() {
    log_info "테스트 컨테이너 빌드 중..."
    $(get_docker_compose_cmd) build filewallball-test
    log_success "테스트 컨테이너 빌드 완료"
}

# API 서버 시작 및 대기
start_api() {
    log_info "FileWallBall API 서버 시작 중..."
    $(get_docker_compose_cmd) up -d filewallball mariadb redis

    log_info "API 서버 준비 대기 중..."
    local max_attempts=60
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
            log_success "API 서버 준비 완료"
            return 0
        fi

        log_info "시도 $attempt/$max_attempts - API 서버 대기 중..."
        sleep 5
        attempt=$((attempt + 1))
    done

    log_error "API 서버 시작 실패 (타임아웃)"
    return 1
}

# 빠른 테스트 실행
run_quick_test() {
    log_info "빠른 테스트 실행 중..."
    $(get_docker_compose_cmd) --profile test run --rm filewallball-test /app/quick_test.sh
}

# 전체 테스트 실행
run_full_test() {
    log_info "전체 워크플로우 테스트 실행 중..."
    $(get_docker_compose_cmd) --profile test run --rm filewallball-test /app/test_full_workflow.sh
}

# 테스트 환경 정리
clean_test() {
    log_info "테스트 환경 정리 중..."
    $(get_docker_compose_cmd) --profile test down filewallball-test 2>/dev/null || true
    $(get_docker_compose_cmd) --profile test rm -f filewallball-test 2>/dev/null || true
    rm -rf test_results 2>/dev/null || true
    log_success "테스트 환경 정리 완료"
}

# 개발 환경 시작
start_dev() {
    log_info "개발 환경 시작 중..."
    $(get_docker_compose_cmd) up -d

    log_info "서비스 준비 대기 중..."
    local max_attempts=60
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
            log_success "개발 환경 준비 완료"
            echo ""
            echo "📊 Grafana: http://localhost:3000 (admin/admin)"
            echo "📈 Prometheus: http://localhost:9090"
            echo "🔍 API: http://localhost:8001"
            echo "📚 API 문서: http://localhost:8001/docs"
            return 0
        fi

        log_info "시도 $attempt/$max_attempts - 서비스 대기 중..."
        sleep 5
        attempt=$((attempt + 1))
    done

    log_error "개발 환경 시작 실패 (타임아웃)"
    return 1
}

# 모든 서비스 중지
stop_all() {
    log_info "모든 서비스 중지 중..."
    $(get_docker_compose_cmd) down
    log_success "모든 서비스 중지 완료"
}

# 메인 실행 로직
main() {
    local action=${1:-quick}

    case $action in
        "quick")
            check_dependencies
            build_test
            start_api
            run_quick_test
            ;;
        "full")
            check_dependencies
            build_test
            start_api
            run_full_test
            ;;
        "build")
            check_dependencies
            build_test
            ;;
        "clean")
            clean_test
            ;;
        "dev")
            check_dependencies
            start_dev
            ;;
        "stop")
            stop_all
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "알 수 없는 옵션: $action"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
