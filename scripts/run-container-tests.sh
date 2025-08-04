#!/bin/bash

set -e

# 컨테이너 기반 통합 테스트 실행 스크립트
echo "🚀 FileWallBall 컨테이너 기반 테스트 시작..."

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

# 함수: 사용법 출력
show_usage() {
    echo ""
    echo "📖 FileWallBall 컨테이너 기반 테스트 사용법:"
    echo ""
    echo "기본 사용법:"
    echo "  $0 [테스트 타입]"
    echo ""
    echo "테스트 타입:"
    echo "  unit        - Unit 테스트만 실행 (pytest tests/unit/)"
    echo "  integration - Integration 테스트만 실행 (pytest tests/integration/)"
    echo "  api         - API 테스트만 실행 (scripts/test-api.sh)"
    echo "  pytest      - 전체 pytest 실행 (pytest tests/)"
    echo "  all         - 전체 테스트 스위트 실행 (기본값)"
    echo ""
    echo "예시:"
    echo "  $0 unit        # Unit 테스트만"
    echo "  $0 integration # Integration 테스트만"
    echo "  $0 api         # API 테스트만"
    echo "  $0             # 전체 테스트"
    echo ""
    echo "테스트 결과:"
    echo "  - HTML 커버리지: test_results/htmlcov/index.html"
    echo "  - JUnit XML: test_results/junit.xml"
    echo "  - 서비스 로그: test_results/service_logs.txt"
    echo ""
}

# 도움말 요청 확인
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_usage
    exit 0
fi

# 함수: 컨테이너 정리
cleanup() {
    log_info "테스트 환경 정리 중..."
    docker-compose -f docker-compose.test.yml down -v --remove-orphans || true
    docker system prune -f || true
}

# 종료 시 정리
trap cleanup EXIT

# 테스트 결과 디렉토리 생성
mkdir -p test_results test_uploads test_logs test_backups

log_info "이전 테스트 환경 정리..."
cleanup

log_step "1. 테스트 환경 빌드 및 시작..."
docker-compose -f docker-compose.test.yml build

log_step "2. 데이터베이스 및 캐시 서비스 시작..."
docker-compose -f docker-compose.test.yml up -d mariadb-test redis-test

log_step "3. 서비스 헬스체크 대기..."
timeout=300  # 5분 타임아웃
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.test.yml ps | grep -q "Up (healthy)"; then
        log_success "기본 서비스들이 준비되었습니다!"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    log_info "서비스 준비 대기 중... (${elapsed}/${timeout}초)"
done

if [ $elapsed -ge $timeout ]; then
    log_error "서비스 시작 타임아웃!"
    exit 1
fi

log_step "4. FileWallBall API 애플리케이션 시작..."
docker-compose -f docker-compose.test.yml up -d filewallball-test-app

log_step "5. API 서비스 헬스체크 대기..."
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.test.yml ps filewallball-test-app | grep -q "Up (healthy)"; then
        log_success "FileWallBall API가 준비되었습니다!"
        break
    fi
    sleep 10
    elapsed=$((elapsed + 10))
    log_info "API 서비스 준비 대기 중... (${elapsed}/${timeout}초)"
done

if [ $elapsed -ge $timeout ]; then
    log_error "API 서비스 시작 타임아웃!"
    docker-compose -f docker-compose.test.yml logs filewallball-test-app
    exit 1
fi

# 테스트 타입별 실행
TEST_TYPE="${1:-all}"

log_step "6. 테스트 실행 시작 (타입: $TEST_TYPE)..."

case $TEST_TYPE in
    "unit")
        log_info "Unit 테스트 실행..."
        docker-compose -f docker-compose.test.yml run --rm pytest-runner pytest tests/unit/ -v --cov=app --cov-report=html:test_results/htmlcov --junitxml=test_results/junit.xml
        ;;
    "integration")
        log_info "Integration 테스트 실행..."
        docker-compose -f docker-compose.test.yml run --rm pytest-runner pytest tests/integration/ -v --cov=app --cov-report=html:test_results/htmlcov --junitxml=test_results/junit.xml
        ;;
    "api")
        log_info "API 테스트 실행..."
        docker-compose -f docker-compose.test.yml run --rm api-test-runner /app/scripts/test-api.sh
        ;;
    "pytest")
        log_info "전체 pytest 실행..."
        docker-compose -f docker-compose.test.yml run --rm pytest-runner
        ;;
    "all"|*)
        log_info "전체 테스트 스위트 실행..."
        
        # Python 테스트
        log_step "6.1. Python 테스트 실행..."
        docker-compose -f docker-compose.test.yml run --rm pytest-runner || log_warning "Python 테스트에서 일부 실패"
        
        # API 테스트
        log_step "6.2. API 테스트 실행..."
        docker-compose -f docker-compose.test.yml run --rm api-test-runner /app/scripts/test-api.sh || log_warning "API 테스트에서 일부 실패"
        
        # 통합 워크플로우 테스트
        log_step "6.3. 통합 워크플로우 테스트 실행..."
        docker-compose -f docker-compose.test.yml run --rm api-test-runner /app/test_full_workflow.sh || log_warning "워크플로우 테스트에서 일부 실패"
        ;;
esac

# 테스트 결과 확인
log_step "7. 테스트 결과 수집..."
if [ -d "test_results" ]; then
    log_success "테스트 결과가 test_results/ 디렉토리에 저장되었습니다."
    ls -la test_results/
    
    # HTML 커버리지 파일 확인
    if [ -f "test_results/htmlcov/index.html" ]; then
        log_success "HTML 커버리지 리포트: test_results/htmlcov/index.html"
    fi
    
    # JUnit XML 파일 확인
    if [ -f "test_results/junit.xml" ]; then
        log_success "JUnit XML 리포트: test_results/junit.xml"
    fi
fi

# 서비스 로그 저장
log_info "서비스 로그 저장 중..."
docker-compose -f docker-compose.test.yml logs --no-color > test_results/service_logs.txt 2>&1

log_success "컨테이너 기반 테스트 완료!"

# 최종 사용법 안내
show_usage