# FileWallBall API System

FastAPI 기반의 안전한 파일 업로드/조회/다운로드 API 시스템입니다. MicroK8s 환경에서 구동되며, 실시간 요청에 따른 자동 스케일링을 지원합니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 주요 기능

- **파일 업로드**: POST `/upload` - 파일 업로드 후 조회 URL 반환
- **파일 조회**: GET `/files/{file_id}` - 파일 정보 조회
- **파일 다운로드**: GET `/download/{file_id}` - 파일 다운로드
- **파일 미리보기**: GET `/view/{file_id}` - 텍스트 파일 미리보기
- **파일 목록**: GET `/files` - 업로드된 파일 목록 조회
- **파일 삭제**: DELETE `/files/{file_id}` - 파일 삭제
- **고급 파일 저장소**: 호스트 OS와 컨테이너 경로 유연한 매핑, 다중 저장소 지원 (Local, S3, Azure, GCS)
- **파일 저장 구조**: 날짜 기반, UUID 기반, 평면 구조 등 다양한 저장 방식 지원
- **자동 스케일링**: HPA를 통한 실시간 스케일링
- **모니터링**: Prometheus 메트릭 제공
- **보안**: IP 기반 인증, RBAC 권한 관리, 레이트 리미팅
- **캐싱**: Redis 기반 고성능 캐싱 시스템
- **백그라운드 작업**: 비동기 파일 처리, 썸네일 생성

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client        │    │   Ingress       │    │   FastAPI       │
│   (Browser/App) │───▶│   Controller    │───▶│   Application   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Redis         │
                                              │   (Cache)       │
                                              └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Persistent    │
                                              │   Volume        │
                                              └─────────────────┘
```

## 📋 요구사항

- MicroK8s
- Docker
- kubectl
- curl, jq (테스트용)
- **Python 3.11+**
- **uv** (Python 패키지 관리자)

## 🛠️ 설치 및 배포

### 📋 시스템 요구사항

- **운영체제**: Linux, macOS, Windows (Windows는 WSL2 권장)
- **Python**: 3.11 이상
- **메모리**: 최소 4GB RAM
- **디스크 공간**: 최소 2GB 여유 공간

### 🚀 빠른 설치

#### 방법 1: 자동 설치 스크립트 (권장)
```bash
# 저장소 클론
git clone <repository-url>
cd fileWallBall

# 자동 설치 (uv 사용)
./install.sh uv

# 또는 pip 사용
./install.sh pip

# 또는 Docker 사용
./install.sh docker
```

#### 방법 2: 수동 설치

##### 2.1 uv를 사용한 설치 (권장)
```bash
# 1. uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # 또는 터미널 재시작

# 2. 저장소 클론
git clone <repository-url>
cd fileWallBall

# 3. 의존성 설치
uv sync --dev

# 4. 환경 설정
cp env.example .env
# .env 파일 편집

# 5. 개발 서버 실행
./scripts/dev.sh run
```

##### 2.2 pip를 사용한 설치
```bash
# 1. Python 3.11+ 설치 확인
python --version

# 2. 저장소 클론
git clone <repository-url>
cd fileWallBall

# 3. 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 환경 설정
cp env.example .env
# .env 파일 편집

# 5. 개발 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

##### 2.3 setup.py를 사용한 설치
```bash
# 1. 저장소 클론
git clone <repository-url>
cd fileWallBall

# 2. 개발 모드로 설치
pip install -e .[dev]

# 3. 환경 설정
cp env.example .env
# .env 파일 편집

# 4. 개발 서버 실행
filewallball  # 콘솔 스크립트로 실행
```

### 🔧 상세 설정

#### 환경 변수 설정

1. **환경 변수 템플릿 복사**
   ```bash
   cp env.example .env
   ```

2. **환경 변수 구성**
   `.env` 파일을 편집하여 설정:
   ```bash
   # 애플리케이션 설정
   APP_NAME="FileWallBall API"
   APP_VERSION="1.0.0"
   DEBUG=true
   ENVIRONMENT="development"

   # 서버 설정
   HOST="0.0.0.0"
   PORT=8000

   # 데이터베이스 설정 (개발용)
   DB_HOST="localhost"
   DB_PORT=3306
   DB_NAME="filewallball_dev"
   DB_USER=""
   DB_PASSWORD=""

   # Redis 설정 (개발용)
   REDIS_HOST="localhost"
   REDIS_PORT=6379
   REDIS_PASSWORD=""
   REDIS_DB=0

   # 파일 저장소 설정
   UPLOAD_DIR="./uploads"
   MAX_FILE_SIZE=104857600  # 100MB
   ALLOWED_EXTENSIONS=".txt,.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.mp4,.mp3,.zip,.rar,.7z"

   # 보안 설정
   SECRET_KEY="your-super-secret-key-change-this-in-production"
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

#### 데이터베이스 설정

##### 옵션 1: SQLite (개발용 권장)
개발 시 기본적으로 SQLite를 사용합니다. 추가 설정이 필요하지 않습니다.

##### 옵션 2: MySQL/MariaDB
```bash
# 1. MySQL/MariaDB 설치
# Ubuntu/Debian
sudo apt install mysql-server

# macOS
brew install mysql

# 2. 데이터베이스 생성
mysql -u root -p
CREATE DATABASE filewallball_dev;
CREATE USER 'filewallball_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON filewallball_dev.* TO 'filewallball_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 3. 환경 변수 업데이트
DB_HOST="localhost"
DB_PORT=3306
DB_NAME="filewallball_dev"
DB_USER="filewallball_user"
DB_PASSWORD="your_password"
```

#### Redis 설정

##### 옵션 1: 로컬 Redis 설치
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis
```

##### 옵션 2: Docker Redis
```bash
# Docker로 Redis 시작
docker run -d --name redis-filewallball -p 6379:6379 redis:7-alpine

# 또는 Makefile 명령어 사용
make redis-start
```

#### 파일 저장소 설정

##### 기본 설정
```bash
# 업로드 디렉토리 생성
mkdir -p uploads

# 권한 설정
chmod 755 uploads
```

##### 고급 경로 매핑 설정
FileWallBall은 호스트 OS 경로와 컨테이너 내부 경로를 유연하게 매핑할 수 있습니다.

```bash
# 호스트 OS 경로 (Docker/K8s에서 볼륨 마운트용)
HOST_UPLOAD_DIR=./uploads

# 컨테이너 내부 경로
CONTAINER_UPLOAD_DIR=/app/uploads

# 저장소 타입 (local, s3, azure, gcs)
STORAGE_TYPE=local

# 파일 저장 구조 설정
# date: 날짜 기반 (YYYY/MM/DD)
# uuid: UUID 기반 계층 구조
# flat: 평면 구조 (모든 파일을 하나의 디렉토리에)
STORAGE_STRUCTURE=date

# 날짜 형식 (STORAGE_STRUCTURE=date일 때 사용)
STORAGE_DATE_FORMAT=%Y/%m/%d

# UUID 계층 깊이 (STORAGE_STRUCTURE=uuid일 때 사용)
STORAGE_UUID_DEPTH=2
```

**환경별 권장 설정:**

- **개발 환경**: `STORAGE_STRUCTURE=uuid` (파일 분산 저장)
- **프로덕션 환경**: `STORAGE_STRUCTURE=date` (날짜별 정리)

자세한 설정 방법은 [파일 저장소 경로 매핑 가이드](docs/file-storage-path-mapping-guide.md)를 참조하세요.

### 🐳 Docker 설치

#### 단일 컨테이너 실행
```bash
# 1. Docker 이미지 빌드
docker build -t filewallball:latest .

# 2. 환경 변수 설정
cp env.example .env
# .env 파일 편집

# 3. 컨테이너 실행
docker run -p 8000:8000 --env-file .env filewallball:latest
```

#### Docker Compose를 사용한 전체 스택 실행
```bash
# 1. 전체 스택 실행 (개발 환경)
docker-compose up -d

# 2. 로그 확인
docker-compose logs -f filewallball

# 3. 서비스 중지
docker-compose down
```

### ☸️ Kubernetes 배포

#### MicroK8s 환경
```bash
# 1. MicroK8s 배포 스크립트 실행
./scripts/deploy.sh

# 2. 배포 상태 확인
kubectl get pods -n filewallball
kubectl get svc -n filewallball
```

#### 수동 Kubernetes 배포
```bash
# 1. 네임스페이스 생성
kubectl apply -f k8s/namespace.yaml

# 2. ConfigMap 및 Secret 배포
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/02-configmap-secret.yaml

# 3. 데이터베이스 배포
kubectl apply -f k8s/mariadb-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml

# 4. 애플리케이션 배포
kubectl apply -f k8s/03-deployment-service.yaml

# 5. Ingress 배포
kubectl apply -f k8s/ingress.yaml
```

## 🧪 개발 도구

### 개발 스크립트 사용법
```bash
# 의존성 설치
./scripts/dev.sh install

# 개발 의존성 설치
./scripts/dev.sh install-dev

# 애플리케이션 실행
./scripts/dev.sh run

# 테스트 실행
./scripts/dev.sh test

# 테스트 (커버리지 포함)
./scripts/dev.sh test-cov

# 코드 포맷팅
./scripts/dev.sh format

# 린팅
./scripts/dev.sh lint

# 캐시 정리
./scripts/dev.sh clean

# 도움말
./scripts/dev.sh help
```

### uv 명령어 직접 사용
```bash
# 의존성 설치
uv sync

# 개발 의존성 포함 설치
uv sync --dev

# 애플리케이션 실행
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 테스트 실행
uv run pytest tests/ -v

# 코드 포맷팅
uv run black app/ tests/
uv run isort app/ tests/

# 린팅
uv run flake8 app/ tests/
uv run mypy app/
```

## 📖 API 사용법

### 파일 업로드
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_file.txt"
```

응답 예시:
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "your_file.txt",
  "download_url": "http://localhost:8000/download/550e8400-e29b-41d4-a716-446655440000",
  "view_url": "http://localhost:8000/view/550e8400-e29b-41d4-a716-446655440000",
  "message": "File uploaded successfully"
}
```

### 파일 정보 조회
```bash
curl "http://localhost:8000/files/{file_id}"
```

### 파일 다운로드
```bash
curl "http://localhost:8000/download/{file_id}" -o downloaded_file
```

### 파일 미리보기
```bash
curl "http://localhost:8000/view/{file_id}"
```

### 파일 목록 조회
```bash
curl "http://localhost:8000/files?limit=10&offset=0"
```

### 파일 삭제
```bash
curl -X DELETE "http://localhost:8000/files/{file_id}"
```

## 🧪 테스트 및 개발

### 테스트 실행

```bash
# 전체 테스트 실행
./scripts/dev.sh test

# 커버리지 포함 테스트
./scripts/dev.sh test-cov

# 또는 Makefile 사용
make test
make test-cov

# 특정 테스트 카테고리 실행
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run pytest tests/e2e/ -v

# 특정 마커로 테스트 실행
uv run pytest -m "unit"
uv run pytest -m "integration"
uv run pytest -m "slow"
```

### 테스트 데이터베이스
테스트는 기본적으로 인메모리 SQLite 데이터베이스를 사용합니다. 추가 설정이 필요하지 않습니다.

### 테스트 커버리지
커버리지 리포트는 `htmlcov/` 디렉토리에 생성됩니다:
```bash
# 브라우저에서 커버리지 리포트 열기
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### API 테스트 실행
```bash
chmod +x scripts/test-api.sh
./scripts/test-api.sh
```

### 시스템 모니터링
```bash
chmod +x scripts/monitor.sh
./scripts/monitor.sh
```

### 코드 품질 도구

#### Pre-commit Hooks
```bash
# pre-commit 훅 설치
uv run pre-commit install

# 모든 파일에 수동 실행
uv run pre-commit run --all-files

# 특정 훅 실행
uv run pre-commit run black --all-files
```

#### 수동 코드 품질 검사
```bash
# 코드 포맷팅
./scripts/dev.sh format
make format

# 린팅
./scripts/dev.sh lint
make lint

# 타입 체킹
uv run mypy app/

# 보안 검사
uv run bandit -r app/
```

### 개발 워크플로우

#### 일일 개발 명령어
```bash
# 개발 서버 시작
./scripts/dev.sh run
make run

# 커밋 전 테스트 실행
./scripts/dev.sh test
make test

# 커밋 전 코드 포맷팅
./scripts/dev.sh format
make format

# 코드 품질 확인
./scripts/dev.sh lint
make lint

# 캐시 파일 정리
./scripts/dev.sh clean
make clean
```

#### Git 워크플로우
```bash
# 기능 브랜치 생성
git checkout -b feature/your-feature-name

# 변경사항 커밋
git add .
git commit -m "feat: add new feature"

# 원격 저장소에 푸시
git push origin feature/your-feature-name

# Pull Request 생성
# GitHub에서 PR 생성
```

## 📊 모니터링

### 메트릭 확인
```bash
curl "http://localhost:8000/metrics"
```

### 헬스체크
```bash
curl "http://localhost:8000/health"
```

### HPA 상태 확인
```bash
kubectl get hpa -n filewallball
```

## 🔧 설정

### 환경 변수
- `BASE_URL`: API 기본 URL
- `REDIS_HOST`: Redis 서버 호스트
- `REDIS_PORT`: Redis 서버 포트

### Kubernetes 설정
- **네임스페이스**: `filewallball`
- **Replicas**: 2-10 (HPA)
- **Storage**: 10Gi PersistentVolume
- **CPU Limit**: 200m
- **Memory Limit**: 256Mi

## 🚨 문제 해결

### 일반적인 문제들

#### 1. Python 버전 문제
**문제**: 잘못된 Python 버전
```bash
# Python 버전 확인
python3 --version

# 잘못된 버전인 경우 올바른 버전 설치
sudo apt install python3.11  # Ubuntu/Debian
brew install python@3.11     # macOS
```

#### 2. uv 설치 문제
**문제**: uv 명령어를 찾을 수 없음
```bash
# uv 재설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 또는 PATH에 수동 추가
export PATH="$HOME/.cargo/bin:$PATH"
```

#### 3. 의존성 설치 문제
**문제**: 패키지 설치 실패
```bash
# uv 캐시 정리
uv cache clean

# 의존성 재설치
uv sync --reinstall
```

#### 4. 데이터베이스 연결 문제
**문제**: 데이터베이스에 연결할 수 없음
```bash
# 데이터베이스 실행 상태 확인
sudo systemctl status mysql  # MySQL
sudo systemctl status redis  # Redis

# .env 파일의 연결 설정 확인
cat .env | grep DB_
```

#### 5. 포트 이미 사용 중
**문제**: 포트 8000이 이미 사용 중
```bash
# 포트 8000을 사용하는 프로세스 찾기
lsof -i :8000

# 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용
uv run uvicorn app.main:app --port 8001
```

#### 6. 권한 문제
**문제**: 권한 거부 오류
```bash
# 업로드 디렉토리 권한 수정
chmod 755 uploads

# 스크립트 권한 수정
chmod +x scripts/*.py
```

#### 7. 파일 저장소 경로 매핑 문제
**문제**: 파일 업로드 경로 매핑 오류
```bash
# 설정 확인
echo $HOST_UPLOAD_DIR
echo $CONTAINER_UPLOAD_DIR
echo $STORAGE_TYPE
echo $STORAGE_STRUCTURE

# 디렉토리 존재 확인
ls -la $HOST_UPLOAD_DIR

# Docker 볼륨 마운트 확인
docker inspect filewallball | grep -A 10 "Mounts"

# Kubernetes PVC 상태 확인
kubectl get pvc -n filewallball
kubectl describe pvc filewallball-storage-pvc -n filewallball
```

#### 8. 저장소 구조 문제
**문제**: 파일 저장 구조 오류
```bash
# 현재 저장소 구조 확인
find uploads/ -type f | head -10

# 저장소 통계 확인
curl -X GET "http://localhost:8000/api/v1/storage/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 설정 재적용
docker-compose down
docker-compose up -d
```

### Kubernetes 문제

#### Pod가 시작되지 않는 경우
```bash
kubectl describe pod -n filewallball <pod-name>
kubectl logs -n filewallball <pod-name>
```

#### Redis 연결 문제
```bash
kubectl logs -n filewallball deployment/redis-deployment
```

#### 스토리지 문제
```bash
kubectl get pvc -n filewallball
kubectl describe pvc -n filewallball filewallball-pvc
```

### 성능 문제

#### 1. 느린 테스트 실행
```bash
# 병렬로 테스트 실행
uv run pytest -n auto

# 단위 테스트만 실행
uv run pytest tests/unit/ -v
```

#### 2. 메모리 문제
```bash
# 캐시 정리
make clean

# uv 캐시 정리
uv cache clean

# 개발 서버 재시작
```

### 디버깅

#### 1. 디버그 모드 활성화
```bash
# .env에서 디버그 모드 설정
DEBUG=true
LOG_LEVEL=DEBUG
```

#### 2. 애플리케이션 로그 확인
```bash
# 개발 서버 로그
uv run uvicorn app.main:app --log-level debug

# Docker 로그
docker-compose logs -f app
```

#### 3. 데이터베이스 디버깅
```bash
# 데이터베이스 연결 확인
uv run python -c "from app.core.config import get_config; print(get_config().database_url)"

# 데이터베이스 연결 테스트
uv run python scripts/test_config.py
```

### 로그 확인

```bash
# 애플리케이션 로그
tail -f logs/app.log

# Docker 로그
docker logs -f filewallball

# Kubernetes 로그
kubectl logs -f deployment/filewallball-deployment -n filewallball
```

## 📈 성능 최적화

### 자동 스케일링 설정
- **CPU 임계값**: 70%
- **메모리 임계값**: 80%
- **최소 Replicas**: 2
- **최대 Replicas**: 10

### 캐시 설정
- Redis TTL: 24시간
- 파일 메타데이터 캐싱
- 해시값 계산 (백그라운드)

## 🔒 보안 고려사항

- 파일 업로드 크기 제한
- 허용된 파일 타입 검증
- CORS 설정
- 적절한 에러 처리
- IP 기반 인증
- RBAC 권한 관리
- 레이트 리미팅

---

# 📚 문서 가이드

FileWallBall 프로젝트의 모든 문서를 체계적으로 정리한 가이드입니다. 각 문서는 특정 기능이나 영역에 대한 상세한 설명을 제공합니다.

## 🗂️ 문서 구조

### 📋 프로젝트 개요 및 설정
- **[프로젝트 개요](docs/project-overview.md)** - FileWallBall 프로젝트의 전체적인 구조와 아키텍처
- **[파일 저장소 경로 매핑 가이드](docs/file-storage-path-mapping-guide.md)** - 호스트 OS와 컨테이너 경로 매핑 설정
- **[배포 및 운영 가이드](docs/deployment-operations-guide.md)** - 프로덕션 배포 및 운영 관리

### 🔧 핵심 기능 문서
- **[API 엔드포인트 가이드](docs/api-endpoints-guide.md)** - 모든 API 엔드포인트의 사용법과 응답 형식
- **[Swagger API 문서화 가이드](docs/swagger-api-documentation-guide.md)** - Swagger UI 및 API 문서화 시스템
- **[서비스 아키텍처 가이드](docs/services-architecture-guide.md)** - 모든 서비스의 구조와 기능 설명

### 🛡️ 보안 및 인증
- **[보안 및 인증 가이드](docs/security-authentication-guide.md)** - 보안 아키텍처, 인증 시스템, 권한 관리
- **[파일 검증 및 처리 가이드](docs/file-validation-processing-guide.md)** - 파일 업로드 검증 및 처리 시스템

### 📊 모니터링 및 성능
- **[모니터링 및 메트릭 가이드](docs/monitoring-metrics-guide.md)** - Prometheus 메트릭, 로깅, 성능 모니터링
- **[성능 최적화 가이드](docs/performance-optimization-guide.md)** - 성능 튜닝 및 최적화 방법
- **[성능 최적화](docs/performance-optimization.md)** - 성능 최적화 전략 및 구현

### 🗄️ 데이터 관리
- **[Redis 캐싱 정책](docs/redis-caching-policy.md)** - Redis 캐싱 시스템 및 정책
- **[Redis 클라이언트 가이드](docs/redis-client-guide.md)** - Redis 클라이언트 사용법
- **[Redis 모니터링 가이드](docs/redis-monitoring-guide.md)** - Redis 모니터링 및 관리
- **[ACID 트랜잭션](docs/acid-transactions.md)** - 데이터베이스 트랜잭션 관리
- **[데이터베이스 헬퍼 사용법](docs/database_helpers_usage.md)** - 데이터베이스 유틸리티 사용법

### 🔄 백업 및 복구
- **[백업 및 복구 가이드](docs/backup-recovery.md)** - 데이터 백업 및 복구 시스템
- **[에러 처리 및 복구 가이드](docs/error-handling-recovery-guide.md)** - 에러 처리 및 장애 복구 시스템

### 🧪 테스팅
- **[테스팅 프레임워크 가이드](docs/testing-framework-guide.md)** - pytest 기반 테스팅 시스템

### 📝 로깅 및 관리
- **[로깅 가이드](docs/logging-guide.md)** - 로깅 시스템 및 설정

## 🎯 문서별 주요 내용

### 프로젝트 개요 및 설정
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [프로젝트 개요](docs/project-overview.md) | 전체 아키텍처, 구성요소, 기술 스택 | 모든 개발자 |
| [파일 저장소 경로 매핑 가이드](docs/file-storage-path-mapping-guide.md) | 호스트 OS와 컨테이너 경로 매핑, 저장소 설정 | 개발자, DevOps |
| [배포 및 운영 가이드](docs/deployment-operations-guide.md) | 프로덕션 배포, 운영 관리 | DevOps, 운영팀 |

### 핵심 기능
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [API 엔드포인트 가이드](docs/api-endpoints-guide.md) | 모든 API 엔드포인트, 사용 예제 | API 사용자, 개발자 |
| [Swagger API 문서화](docs/swagger-api-documentation-guide.md) | Swagger UI, OpenAPI 스키마 | API 개발자 |
| [서비스 아키텍처 가이드](docs/services-architecture-guide.md) | 서비스 구조, 의존성, 확장성 | 백엔드 개발자 |

### 보안 및 인증
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [보안 및 인증 가이드](docs/security-authentication-guide.md) | 보안 아키텍처, RBAC, IP 인증 | 보안팀, 개발자 |
| [파일 검증 및 처리](docs/file-validation-processing-guide.md) | 파일 검증, 바이러스 스캔 | 개발자, 보안팀 |

### 모니터링 및 성능
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [모니터링 및 메트릭](docs/monitoring-metrics-guide.md) | Prometheus, Grafana, 알림 | DevOps, 운영팀 |
| [성능 최적화 가이드](docs/performance-optimization-guide.md) | 성능 튜닝, 벤치마킹 | 개발자, 성능 엔지니어 |
| [성능 최적화](docs/performance-optimization.md) | 최적화 전략, 구현 방법 | 개발자 |

### 데이터 관리
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [Redis 캐싱 정책](docs/redis-caching-policy.md) | 캐싱 전략, TTL 설정 | 개발자, DevOps |
| [Redis 클라이언트 가이드](docs/redis-client-guide.md) | Redis 클라이언트 사용법 | 개발자 |
| [Redis 모니터링 가이드](docs/redis-monitoring-guide.md) | Redis 모니터링, 성능 분석 | DevOps, 운영팀 |
| [ACID 트랜잭션](docs/acid-transactions.md) | 트랜잭션 관리, 일관성 | 개발자, DBA |
| [데이터베이스 헬퍼](docs/database_helpers_usage.md) | DB 유틸리티, 헬퍼 함수 | 개발자 |

### 백업 및 복구
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [백업 및 복구 가이드](docs/backup-recovery.md) | 자동 백업, 복구 절차 | DevOps, 운영팀 |
| [에러 처리 및 복구](docs/error-handling-recovery-guide.md) | 에러 처리, 장애 복구 | 개발자, 운영팀 |

### 테스팅
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [테스팅 프레임워크](docs/testing-framework-guide.md) | pytest, 통합 테스트, 성능 테스트 | QA, 개발자 |

### 로깅 및 관리
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [로깅 가이드](docs/logging-guide.md) | 로깅 설정, 로그 분석 | 개발자, 운영팀 |

## 🚀 빠른 시작 가이드

### 개발자 시작하기
1. **설치 및 배포 섹션** - 개발 환경 설정 (위 참조)
2. **[프로젝트 개요](docs/project-overview.md)** - 전체 구조 이해
3. **[파일 저장소 경로 매핑 가이드](docs/file-storage-path-mapping-guide.md)** - 파일 저장소 설정
4. **[API 엔드포인트 가이드](docs/api-endpoints-guide.md)** - API 사용법 학습
5. **[서비스 아키텍처 가이드](docs/services-architecture-guide.md)** - 서비스 구조 파악

### API 사용자 시작하기
1. **[API 엔드포인트 가이드](docs/api-endpoints-guide.md)** - API 사용법
2. **[Swagger API 문서화](docs/swagger-api-documentation-guide.md)** - 인터랙티브 문서
3. **[보안 및 인증 가이드](docs/security-authentication-guide.md)** - 인증 방법

### 운영팀 시작하기
1. **[배포 및 운영 가이드](docs/deployment-operations-guide.md)** - 배포 및 운영
2. **[모니터링 및 메트릭 가이드](docs/monitoring-metrics-guide.md)** - 모니터링 설정
3. **[백업 및 복구 가이드](docs/backup-recovery.md)** - 백업 및 복구
4. **[Redis 모니터링 가이드](docs/redis-monitoring-guide.md)** - Redis 관리

### 보안팀 시작하기
1. **[보안 및 인증 가이드](docs/security-authentication-guide.md)** - 보안 아키텍처
2. **[파일 검증 및 처리 가이드](docs/file-validation-processing-guide.md)** - 파일 보안
3. **[에러 처리 및 복구 가이드](docs/error-handling-recovery-guide.md)** - 보안 이벤트

## 📊 문서 품질 관리

### 문서 업데이트 체크리스트
- [ ] 코드 변경사항 반영
- [ ] 예제 코드 검증
- [ ] 스크린샷 및 다이어그램 업데이트
- [ ] 링크 유효성 확인
- [ ] 문법 및 맞춤법 검토

### 문서 버전 관리
- **주 버전**: 주요 기능 추가/변경
- **부 버전**: 문서 개선 및 수정
- **패치 버전**: 오타 수정 및 링크 업데이트

## 🔗 관련 링크

### 외부 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Redis 공식 문서](https://redis.io/documentation)
- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Kubernetes 공식 문서](https://kubernetes.io/docs/)

### 프로젝트 리소스
- [GitHub 저장소](https://github.com/filewallball/api)
- [API 문서 (Swagger UI)](http://localhost:8000/docs)
- [API 문서 (ReDoc)](http://localhost:8000/redoc)
- [프로젝트 위키](https://github.com/filewallball/api/wiki)

## 📚 추가 리소스

### 외부 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [Redis 문서](https://redis.io/documentation)
- [uv 문서](https://docs.astral.sh/uv/)

### 도구
- [Black 코드 포맷터](https://black.readthedocs.io/)
- [isort 임포트 정렬기](https://pycqa.github.io/isort/)
- [flake8 린터](https://flake8.pycqa.org/)
- [mypy 타입 체커](https://mypy.readthedocs.io/)
- [pytest 테스팅 프레임워크](https://docs.pytest.org/)

## 📞 지원 및 문의

문의사항이 있으시면 아래 이메일로 메일을 보내주세요.

**📧 이메일**: lanco.gh@gmail.com

## 📝 문서 기여하기

### 기여 방법
1. GitHub 저장소를 포크
2. 문서 수정 또는 추가
3. Pull Request 생성
4. 리뷰 후 병합

### 문서 작성 규칙
- **마크다운 형식** 사용
- **한국어**로 작성 (영어 버전은 별도 관리)
- **이모지**를 활용한 가독성 향상
- **코드 예제** 포함
- **스크린샷** 및 **다이어그램** 활용

---

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Install dependencies with `uv sync --dev`
4. Run tests with `./scripts/dev.sh test`
5. Format code with `./scripts/dev.sh format`
6. Commit your changes
7. Push to the branch
8. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

MIT License - 자유롭게 사용, 수정, 배포할 수 있는 오픈소스 라이선스입니다.

## 📞 지원

문제가 발생하거나 질문이 있으시면 이메일로 문의해주세요.

**📧 이메일**: lanco.gh@gmail.com

---

이 문서는 FileWallBall 프로젝트의 모든 문서를 체계적으로 정리한 가이드입니다. 각 문서는 특정 기능이나 영역에 대한 상세한 설명을 제공하며, 프로젝트의 성공적인 개발과 운영을 지원합니다.
