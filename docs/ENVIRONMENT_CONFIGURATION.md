# FileWallBall API 환경별 설정 가이드

## 📋 개요

이 문서는 FileWallBall API의 다양한 환경(개발, 테스트, 프로덕션)에 대한 설정 방법과 차이점을 설명합니다.

## 🏗️ 환경 아키텍처

### 환경별 구성 요소

| 구성 요소 | 개발 환경 | 테스트 환경 | 프로덕션 환경 |
|-----------|-----------|-------------|---------------|
| 데이터베이스 | 로컬 MariaDB 컨테이너 | 로컬 MariaDB 컨테이너 | 외부 MariaDB 서버 |
| Redis | 로컬 Redis 컨테이너 | 로컬 Redis 컨테이너 | 선택사항 |
| 로그 레벨 | DEBUG | INFO | WARNING |
| 디버그 모드 | 활성화 | 비활성화 | 비활성화 |
| 리소스 제한 | 없음 | 기본값 | 엄격한 제한 |

## 🔧 환경 변수 파일

### 1. 개발 환경 (.env.dev)

```bash
# Application Settings
ENVIRONMENT="development"
DEBUG=true
LOG_LEVEL="DEBUG"

# Database Configuration - Local Docker Container
DB_HOST="mariadb"
DB_PORT=3306
DB_NAME="filewallball_dev"
DB_USER="filewallball_dev_user"
DB_PASSWORD="dev_password"

# Redis Configuration - Local Docker Container
REDIS_HOST="redis"
REDIS_PORT=6379
REDIS_PASSWORD=""

# Security Settings
SECRET_KEY="dev-secret-key-change-in-production"
CORS_ORIGINS="*"

# Cache Settings
CACHE_TTL_FILE_METADATA=1800  # 30 minutes for development
CACHE_TTL_TEMP=300           # 5 minutes for development
```

### 2. 프로덕션 환경 (.env.prod)

```bash
# Application Settings
ENVIRONMENT="production"
DEBUG=false
LOG_LEVEL="WARNING"

# Database Configuration - External Server
DB_HOST="pathcosmos.iptime.org"
DB_PORT=33377
DB_NAME="filewallball"
DB_USER="filewallball"
DB_PASSWORD="jK9#zQ$p&2@f!L7^xY*"

# Redis Configuration - Optional
# REDIS_HOST="redis"
# REDIS_PORT=6379
# REDIS_PASSWORD=""

# Security Settings
SECRET_KEY="your-super-secret-production-key"
CORS_ORIGINS="*"

# Cache Settings
CACHE_TTL_FILE_METADATA=7200  # 2 hours for production
CACHE_TTL_TEMP=600           # 10 minutes for production

# Performance Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

## 🐳 Docker Compose 환경별 실행

### 개발 환경 실행

```bash
# 개발 환경 시작
docker-compose --env-file .env.dev up -d

# 개발 환경 중지
docker-compose --env-file .env.dev down

# 개발 환경 로그 확인
docker-compose --env-file .env.dev logs -f app
```

### 프로덕션 환경 실행

```bash
# 프로덕션 환경 시작
docker-compose --env-file .env.prod up -d

# 프로덕션 환경 중지
docker-compose --env-file .env.prod down

# 프로덕션 환경 로그 확인
docker-compose --env-file .env.prod logs -f app
```

### 환경 전환

```bash
# 개발 환경에서 프로덕션 환경으로 전환
docker-compose --env-file .env.dev down
docker-compose --env-file .env.prod up -d

# 프로덕션 환경에서 개발 환경으로 전환
docker-compose --env-file .env.prod down
docker-compose --env-file .env.dev up -d
```

## 📊 환경별 성능 설정

### 개발 환경 성능 설정

```yaml
# docker-compose.yml (기본)
services:
  app:
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    # 리소스 제한 없음
    # 핫 리로드 활성화
```

### 프로덕션 환경 성능 설정

```yaml
# docker-compose.prod.yml
services:
  app:
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    restart: always
```

## 🔒 환경별 보안 설정

### 개발 환경 보안

```yaml
# 기본 보안 설정
services:
  app:
    security_opt:
      - no-new-privileges:true
    read_only: false
    tmpfs:
      - /tmp
      - /var/tmp
```

### 프로덕션 환경 보안

```yaml
# 강화된 보안 설정
services:
  app:
    security_opt:
      - no-new-privileges:true
    read_only: false
    tmpfs:
      - /tmp
      - /var/tmp
    user: "app:app"  # 비루트 사용자
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 📝 환경별 설정 검증

### 개발 환경 검증

```bash
# 환경 변수 확인
docker-compose --env-file .env.dev exec app env | grep -E "ENVIRONMENT|DEBUG|LOG_LEVEL"

# 데이터베이스 연결 확인
docker-compose --env-file .env.dev exec app python -c "
from app.core.config import settings
print(f'Environment: {settings.environment}')
print(f'Debug: {settings.debug}')
print(f'Log Level: {settings.log_level}')
print(f'DB Host: {settings.db_host}')
"
```

### 프로덕션 환경 검증

```bash
# 환경 변수 확인
docker-compose --env-file .env.prod exec app env | grep -E "ENVIRONMENT|DEBUG|LOG_LEVEL"

# 데이터베이스 연결 확인
docker-compose --env-file .env.prod exec app python -c "
from app.core.config import settings
print(f'Environment: {settings.environment}')
print(f'Debug: {settings.debug}')
print(f'Log Level: {settings.log_level}')
print(f'DB Host: {settings.db_host}')
"

# 헬스체크 확인
curl http://localhost:8000/health
```

## 🚨 환경별 문제 해결

### 개발 환경 문제

1. **핫 리로드가 작동하지 않음**
   - `--reload` 플래그 확인
   - 볼륨 마운트 확인

2. **데이터베이스 연결 실패**
   - MariaDB 컨테이너 상태 확인
   - 환경 변수 설정 확인

### 프로덕션 환경 문제

1. **환경 변수 로드 실패**
   - `.env.prod` 파일 존재 확인
   - 필수 환경 변수 설정 확인

2. **리소스 부족**
   - 컨테이너 리소스 제한 확인
   - 호스트 시스템 리소스 확인

3. **보안 문제**
   - 컨테이너 보안 설정 확인
   - 환경 변수 보안 확인

## 📋 환경 설정 체크리스트

### 개발 환경 설정

- [ ] `.env.dev` 파일 생성 및 설정
- [ ] 로컬 Docker 컨테이너 설정
- [ ] 디버그 모드 활성화
- [ ] 개발용 데이터베이스 설정

### 프로덕션 환경 설정

- [ ] `.env.prod` 파일 생성 및 설정
- [ ] 외부 데이터베이스 연결 설정
- [ ] 보안 환경 변수 설정
- [ ] 리소스 제한 설정
- [ ] 헬스체크 설정

### 공통 설정

- [ ] 환경 변수 격리 확인
- [ ] Docker Compose 설정 검증
- [ ] 서비스 의존성 확인
- [ ] 로그 설정 확인

## 🔄 환경 마이그레이션

### 개발에서 프로덕션으로

1. 환경 변수 파일 생성
2. 데이터베이스 연결 정보 업데이트
3. 보안 설정 강화
4. 성능 최적화 적용
5. 테스트 및 검증

### 프로덕션에서 개발으로

1. 환경 변수 파일 변경
2. 로컬 리소스 사용
3. 디버그 모드 활성화
4. 개발 도구 설정

---

**마지막 업데이트**: 2025년 8월 24일
**버전**: 1.0.0
