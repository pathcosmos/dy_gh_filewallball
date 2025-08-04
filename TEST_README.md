# FileWallBall 테스트 가이드

이 문서는 FileWallBall 프로젝트의 테스트 실행 방법을 설명합니다. CLAUDE.md의 권장사항을 반영하여 작성되었습니다.

## 🚀 빠른 시작

### 컨테이너 기반 테스트 (권장)

```bash
# 전체 테스트 실행
./scripts/run-container-tests.sh

# 특정 테스트 타입만 실행
./scripts/run-container-tests.sh unit        # Unit 테스트만
./scripts/run-container-tests.sh integration # Integration 테스트만
./scripts/run-container-tests.sh api         # API 테스트만
./scripts/run-container-tests.sh pytest      # 전체 pytest 실행
```

### 로컬 테스트

```bash
# 빠른 테스트 (기본 기능만)
./scripts/test-quick.sh

# 전체 워크플로우 테스트
./scripts/test-full-workflow.sh

# API 테스트
./scripts/test-api.sh
```

## 📋 테스트 종류

### 1. 컨테이너 기반 테스트 (권장)

**장점:**
- 전체 서비스 의존성 포함 (MariaDB, Redis)
- 격리된 테스트 환경
- 프로덕션과 유사한 환경
- 자동 정리 및 결과 수집

**사용법:**
```bash
# 전체 테스트 스위트
./scripts/run-container-tests.sh

# 도움말 보기
./scripts/run-container-tests.sh --help
```

**테스트 타입:**
- `unit`: Unit 테스트만 실행 (pytest tests/unit/)
- `integration`: Integration 테스트만 실행 (pytest tests/integration/)
- `api`: API 테스트만 실행 (scripts/test-api.sh)
- `pytest`: 전체 pytest 실행 (pytest tests/)
- `all`: 전체 테스트 스위트 실행 (기본값)

### 2. 로컬 테스트

#### 빠른 테스트
```bash
./scripts/test-quick.sh
```
- 기본적인 API 기능만 빠르게 확인
- 8개의 핵심 테스트
- 약 1-2분 소요

#### 전체 워크플로우 테스트
```bash
./scripts/test-full-workflow.sh
```
- 파일 업로드부터 삭제까지 전체 과정 테스트
- V1/V2 API 모두 테스트
- 파일 내용 검증 포함
- 약 3-5분 소요

#### API 테스트
```bash
./scripts/test-api.sh
```
- 15개의 API 엔드포인트 테스트
- 보안, 메트릭스, RBAC 등 포함
- 약 2-3분 소요

## 🧪 테스트 환경

### 컨테이너 환경 구성

```yaml
# docker-compose.test.yml
services:
  mariadb-test:    # 테스트용 MariaDB
  redis-test:      # 테스트용 Redis
  filewallball-test-app:  # 테스트용 API 서버
  pytest-runner:   # Python 테스트 실행기
  api-test-runner: # API 테스트 실행기
```

### 환경 변수

```bash
# API 설정
API_BASE_URL=http://localhost:8000
TEST_RESULTS_DIR=test_results
UPLOAD_DIR=test_uploads

# 데이터베이스 설정
DB_HOST=mariadb-test
DB_NAME=filewallball_test_db
DB_USER=filewallball_test_user
DB_PASSWORD=filewallball_test_password

# Redis 설정
REDIS_HOST=redis-test
REDIS_PASSWORD=filewallball_test_2024
```

## 📊 테스트 결과

### 결과 파일 위치

```
test_results/
├── htmlcov/                    # HTML 커버리지 리포트
│   └── index.html
├── junit.xml                   # JUnit XML 리포트
├── service_logs.txt            # 서비스 로그
├── api_test_summary.txt        # API 테스트 요약
├── workflow_test_summary.txt   # 워크플로우 테스트 요약
├── quick_test_summary.txt      # 빠른 테스트 요약
└── *.log                       # 개별 테스트 로그
```

### 결과 확인

```bash
# HTML 커버리지 리포트 보기
open test_results/htmlcov/index.html

# 테스트 요약 확인
cat test_results/api_test_summary.txt
cat test_results/workflow_test_summary.txt
cat test_results/quick_test_summary.txt

# 서비스 로그 확인
tail -f test_results/service_logs.txt
```

## 🔧 Makefile 사용법

```bash
# 테스트 관련 명령어
make -f Makefile.test help          # 도움말
make -f Makefile.test build-test    # 테스트 컨테이너 빌드
make -f Makefile.test run-test      # 전체 테스트 실행
make -f Makefile.test run-quick-test # 빠른 테스트 실행
make -f Makefile.test run-full-test # 전체 워크플로우 테스트
make -f Makefile.test clean-test    # 테스트 정리
make -f Makefile.test logs-test     # 테스트 로그 확인
```

## 🐍 Python 테스트

### 로컬 Python 테스트

```bash
# uv 사용 (권장)
uv run pytest tests/ -v
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# pip 사용
pip install -r requirements.txt
pytest tests/ -v

# 커버리지와 함께
pytest tests/ --cov=app --cov-report=html
```

### 특정 테스트 실행

```bash
# 특정 테스트 파일
pytest tests/unit/test_file_service.py -v

# 특정 테스트 함수
pytest tests/unit/test_file_service.py::test_upload_file -v

# 마커 사용
pytest -m "slow" -v
pytest -m "not slow" -v
```

## 🚨 문제 해결

### 일반적인 문제

1. **API 서비스 연결 실패**
   ```bash
   # 서비스 상태 확인
   docker-compose -f docker-compose.test.yml ps
   
   # 로그 확인
   docker-compose -f docker-compose.test.yml logs filewallball-test-app
   ```

2. **데이터베이스 연결 실패**
   ```bash
   # 데이터베이스 상태 확인
   docker-compose -f docker-compose.test.yml logs mariadb-test
   
   # 수동 연결 테스트
   docker-compose -f docker-compose.test.yml exec mariadb-test mysql -u root -p
   ```

3. **Redis 연결 실패**
   ```bash
   # Redis 상태 확인
   docker-compose -f docker-compose.test.yml logs redis-test
   
   # 수동 연결 테스트
   docker-compose -f docker-compose.test.yml exec redis-test redis-cli ping
   ```

### 테스트 환경 정리

```bash
# 완전 정리
docker-compose -f docker-compose.test.yml down -v --remove-orphans
docker system prune -f
rm -rf test_results test_uploads

# 부분 정리
make -f Makefile.test clean-test
```

## 📈 성능 테스트

```bash
# 성능 테스트 실행
python scripts/performance_test.py

# Redis 성능 테스트
python scripts/redis-performance-test.py

# 데이터베이스 성능 테스트
python scripts/test_database_performance.py
```

## 🔍 모니터링

### 테스트 중 모니터링

```bash
# 실시간 로그 확인
docker-compose -f docker-compose.test.yml logs -f

# 메트릭스 확인
curl http://localhost:8000/metrics

# 상세 메트릭스
curl http://localhost:8000/api/v1/metrics/detailed
```

### 테스트 후 분석

```bash
# 커버리지 분석
open test_results/htmlcov/index.html

# 성능 분석
python scripts/performance_analyzer.py

# 로그 분석
grep "ERROR" test_results/service_logs.txt
grep "WARNING" test_results/service_logs.txt
```

## 📝 테스트 작성 가이드

### 새로운 테스트 추가

1. **Unit 테스트**: `tests/unit/`
2. **Integration 테스트**: `tests/integration/`
3. **E2E 테스트**: `tests/e2e/`

### 테스트 구조

```python
import pytest
from app.services.file_service import FileService

class TestFileService:
    @pytest.fixture
    def file_service(self):
        return FileService()
    
    def test_upload_file(self, file_service):
        # 테스트 로직
        pass
    
    @pytest.mark.integration
    def test_file_workflow(self, file_service):
        # 통합 테스트 로직
        pass
```

### 테스트 마커

```python
@pytest.mark.slow      # 느린 테스트
@pytest.mark.integration  # 통합 테스트
@pytest.mark.api       # API 테스트
@pytest.mark.unit      # 단위 테스트
```

## 🎯 CI/CD 통합

### GitHub Actions 예시

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run container tests
        run: ./scripts/run-container-tests.sh
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test_results/
```

## 📚 추가 리소스

- [CLAUDE.md](./CLAUDE.md) - 개발 가이드
- [docs/testing-framework-guide.md](./docs/testing-framework-guide.md) - 테스트 프레임워크 상세 가이드
- [docs/api-endpoints-guide.md](./docs/api-endpoints-guide.md) - API 엔드포인트 가이드
- [pytest.ini](./pytest.ini) - pytest 설정
- [docker-compose.test.yml](./docker-compose.test.yml) - 테스트 환경 설정 