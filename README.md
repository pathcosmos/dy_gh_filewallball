# FileWallBall API System

FastAPI 기반의 안전한 파일 업로드/조회/다운로드 API 시스템입니다. 
Docker Compose 환경에서 구동되며, 모듈화된 라우터 구조와 종합적인 문서화를 지원합니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 주요 기능

- **파일 업로드**: POST `/upload` - 파일 업로드 후 조회 URL 반환
- **파일 조회**: GET `/files/{file_id}` - 파일 정보 조회
- **파일 다운로드**: GET `/download/{file_id}` - 파일 다운로드
- **파일 미리보기**: GET `/view/{file_id}` - 텍스트 파일 미리보기
- **파일 목록**: GET `/files` - 업로드된 파일 목록 조회
- **파일 삭제**: DELETE `/files/{file_id}` - 파일 삭제
- **프로젝트 키 생성**: POST `/keygen` - 프로젝트별 API 키 생성
- **시스템 상태 확인**: GET `/health` - 시스템 헬스체크
- **모듈화된 API 구조**: 파일, 다운로드, 시스템 관리 라우터로 구성
- **MariaDB + Redis**: 안정적인 데이터 저장 및 캐싱
- **Docker Compose**: 간편한 개발 및 배포 환경

## ⚡ 빠른 시작 (5분)

### 🐳 Docker Compose로 즉시 실행

```bash
# 1. 저장소 클론
git clone https://github.com/pathcosmos/dy_gh_filewallball.git
cd dy_gh_filewallball

# 2. 개발 환경 시작
docker-compose --env-file .env.dev up -d

# 3. 서비스 상태 확인
docker-compose --env-file .env.dev ps

# 4. API 테스트
curl http://localhost:18000/health
curl http://localhost:18000/files

# 5. API 문서 확인
open http://localhost:18000/docs
```

### 🔄 환경 전환

```bash
# 개발 → 프로덕션
docker-compose --env-file .env.dev down
docker-compose --env-file .env.prod up -d

# 프로덕션 → 개발
docker-compose --env-file .env.prod down
docker-compose --env-file .env.dev up -d
```

### 📊 모니터링

```bash
# 실시간 로그
docker-compose --env-file .env.prod logs -f

# 리소스 사용량
docker stats

# 서비스 상태
docker-compose --env-file .env.prod ps
```

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client        │    │   Nginx         │    │   FastAPI       │
│   (Browser/App) │───▶│   Reverse Proxy │───▶│   Application   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   MariaDB       │
                                              │   (Database)    │
                                              └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Persistent    │
                                              │   Volume        │
                                              └─────────────────┘
```

### 🔧 모듈화된 라우터 구조

```
app/
├── main.py              # FastAPI 애플리케이션 메인
├── routers/             # 모듈화된 API 라우터
│   ├── __init__.py
│   ├── files.py         # 파일 관리 엔드포인트
│   ├── download.py      # 파일 다운로드 및 뷰어
│   └── system.py        # 시스템 관리 엔드포인트
├── config.py            # 설정 관리
├── models/              # 데이터 모델
├── services/            # 비즈니스 로직
└── utils/               # 유틸리티 함수
```

## 📋 요구사항

- **Docker**: 20.10 이상
- **Docker Compose**: 2.0 이상
- **메모리**: 최소 2GB RAM
- **디스크 공간**: 최소 1GB 여유 공간

## 🚀 실제 기동 방법

### 🐳 Docker Compose를 사용한 빠른 시작 (권장)

#### 1. 환경별 실행 방법

**개발 환경 실행:**
```bash
# 개발 환경 시작
docker-compose --env-file .env.dev up -d

# 서비스 상태 확인
docker-compose --env-file .env.dev ps

# 로그 확인
docker-compose --env-file .env.dev logs -f app

# 개발 환경 중지
docker-compose --env-file .env.dev down
```

**프로덕션 환경 실행:**
```bash
# 프로덕션 환경 시작
docker-compose --env-file .env.prod up -d

# 서비스 상태 확인
docker-compose --env-file .env.prod ps

# 로그 확인
docker-compose --env-file .env.prod logs -f app

# 프로덕션 환경 중지
docker-compose --env-file .env.prod down
```

#### 2. 환경 전환

```bash
# 개발 환경에서 프로덕션 환경으로 전환
docker-compose --env-file .env.dev down
docker-compose --env-file .env.prod up -d

# 프로덕션 환경에서 개발 환경으로 전환
docker-compose --env-file .env.prod down
docker-compose --env-file .env.dev up -d
```

#### 3. 서비스 모니터링

```bash
# 실시간 서비스 상태 확인
docker-compose --env-file .env.prod ps

# 리소스 사용량 확인
docker stats

# 특정 서비스 로그 확인
docker-compose --env-file .env.prod logs -f app      # 애플리케이션 로그
docker-compose --env-file .env.prod logs -f mariadb  # 데이터베이스 로그
```

#### 4. 헬스체크 및 API 테스트

```bash
# 헬스체크 확인
curl http://localhost:18000/health

# API 문서 확인
curl http://localhost:18000/docs

# 파일 목록 확인
curl http://localhost:18000/files

# 전체 서비스 상태 확인
docker-compose --env-file .env.prod exec app curl -f http://localhost:18000/health
```

#### 5. 문제 해결

```bash
# 서비스 재시작
docker-compose --env-file .env.prod restart app

# 특정 서비스만 재시작
docker-compose --env-file .env.prod restart mariadb

# 컨테이너 내부 접속
docker-compose --env-file .env.prod exec app bash
docker-compose --env-file .env.prod exec mariadb mysql -u root -p

# 환경 변수 확인
docker-compose --env-file .env.prod exec app env | grep -E "ENVIRONMENT|DEBUG|LOG_LEVEL"
```

### 🔧 환경별 설정 파일

#### 개발 환경 (.env.dev)
- `DEBUG=true`
- `LOG_LEVEL=DEBUG`
- `ENVIRONMENT=development`
- 로컬 Docker 컨테이너 사용
- `DB_HOST=mariadb`, `DB_PORT=13306`
- `DB_NAME=filewallball_db`, `DB_USER=filewallball_user`

#### 프로덕션 환경 (.env.prod)
- `DEBUG=false`
- `LOG_LEVEL=WARNING`
- `ENVIRONMENT=production`
- Docker 컨테이너 사용
- `DB_HOST=mariadb`, `DB_PORT=13306`
- `DB_NAME=filewallball_db`, `DB_USER=filewallball_user`

#### 기본 환경 (.env)
- `DEBUG=true`
- `LOG_LEVEL=INFO`
- `ENVIRONMENT=testing`
- Docker 컨테이너 사용
- `DB_HOST=mariadb`, `DB_PORT=13306`
- `DB_NAME=filewallball_db`, `DB_USER=filewallball_user`

### 📁 **환경별 설정 파일 구조**

```
dy_gh_filewallball/
├── .env.dev          # 개발 환경 설정
├── .env.prod         # 프로덕션 환경 설정
├── .env              # 기본 환경 설정 (기본값)
├── docker-compose.yml           # 기본 Docker Compose 설정
├── docker-compose.dev.yml       # 개발 환경 오버라이드
└── docker-compose.prod.yml      # 프로덕션 환경 오버라이드
```

### 🔄 **환경별 주요 차이점**

| 설정 항목 | 개발 환경 | 프로덕션 환경 | 기본 환경 |
|-----------|-----------|---------------|-----------|
| **DEBUG** | `true` | `false` | `true` |
| **LOG_LEVEL** | `DEBUG` | `WARNING` | `INFO` |
| **ENVIRONMENT** | `development` | `production` | `testing` |
| **핫 리로드** | ✅ 활성화 | ❌ 비활성화 | ❌ 비활성화 |
| **워커 프로세스** | 1개 | 4개 | 1개 |
| **리소스 제한** | ❌ 없음 | ✅ 메모리 1GB, CPU 1.0 | ❌ 없음 |
| **포트 노출** | ✅ 18000, 13306 | ✅ 18000, 13306 | ✅ 18000, 13306 |

### ✅ **빠른 시작 체크리스트**

#### **🔧 초기 설정 (5분)**
- [ ] Docker 및 Docker Compose 설치 확인
- [ ] 프로젝트 클론 완료
- [ ] 환경 변수 파일 확인 (`.env.dev`, `.env.prod`, `.env`)

#### **🚀 개발 환경 시작 (3분)**
- [ ] `docker-compose --env-file .env.dev up -d` 실행
- [ ] 서비스 상태 확인 (`docker-compose --env-file .env.dev ps`)
- [ ] 헬스체크 통과 (`curl http://localhost:18000/health`)
- [ ] API 문서 접속 (`http://localhost:18000/docs`)

#### **🏭 프로덕션 환경 시작 (3분)**
- [ ] `docker-compose --env-file .env.prod up -d` 실행
- [ ] 프로덕션 설정 검증 (환경 변수, 성능 설정)
- [ ] 헬스체크 통과 및 성능 확인
- [ ] 보안 설정 검증

#### **📊 기능 테스트 (5분)**
- [ ] 파일 업로드 테스트
- [ ] 파일 목록 조회 테스트
- [ ] 파일 다운로드 테스트
- [ ] 파일 미리보기 테스트

#### **🔄 환경 전환 테스트 (2분)**
- [ ] 개발 → 프로덕션 전환
- [ ] 프로덕션 → 개발 전환
- [ ] 데이터 일관성 확인

---

## 🛠️ 설치 및 배포

### 📋 시스템 요구사항

- **운영체제**: Linux, macOS, Windows (Windows는 WSL2 권장)
- **Docker**: 20.10 이상
- **Docker Compose**: 2.0 이상
- **메모리**: 최소 2GB RAM
- **디스크 공간**: 최소 1GB 여유 공간

### 🚀 빠른 설치

#### 방법 1: 자동 설치 스크립트 (권장)
```bash
# Ubuntu 환경에서 Production 환경 자동 설치
curl -fsSL https://raw.githubusercontent.com/pathcosmos/dy_gh_filewallball/main/scripts/ubuntu-production-installer.sh | bash
```

#### 방법 2: 수동 설치

##### 2.1 Docker를 사용한 설치 (권장)
```bash
# 1. Docker 및 Docker Compose 설치 확인
docker --version
docker-compose --version

# 2. 저장소 클론
git clone https://github.com/pathcosmos/dy_gh_filewallball.git
cd dy_gh_filewallball

# 3. 환경 설정
cp .env.example .env
# .env 파일 편집

# 4. 개발 서버 실행
docker-compose --env-file .env.dev up -d
```

### 🔧 상세 설정

#### 환경 변수 설정

1. **환경 변수 템플릿 복사**
   ```bash
   cp .env.example .env
   ```

2. **환경 변수 구성**
   `.env` 파일을 편집하여 설정:
   ```bash
   # 애플리케이션 설정
   APP_NAME="FileWallBall API"
   APP_VERSION="2.0.0"
   DEBUG=true
   ENVIRONMENT="development"

   # 서버 설정
   HOST="0.0.0.0"
   APP_PORT=18000

   # 데이터베이스 설정
   DB_HOST="mariadb"
   DB_PORT=13306
   DB_NAME="filewallball_db"
   DB_USER="filewallball_user"
   DB_PASSWORD="your_password"

   # 파일 저장소 설정
   UPLOAD_DIR="./uploads"
   MAX_FILE_SIZE=104857600  # 100MB
   ALLOWED_EXTENSIONS=".txt,.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.mp4,.mp3,.zip,.rar,.7z"

   # 보안 설정
   SECRET_KEY="your-super-secret-key-change-this-in-production"
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

#### 데이터베이스 설정

##### MariaDB 설정
프로젝트는 Docker 컨테이너 내부의 MariaDB를 사용합니다.

```bash
# 환경 변수 설정
DB_HOST="mariadb"  # Docker 컨테이너 이름
DB_PORT=13306      # 호스트 포트
DB_NAME="filewallball_db"
DB_USER="filewallball_user"
DB_PASSWORD="your_password"
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
# 호스트 OS 경로 (Docker에서 볼륨 마운트용)
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

자세한 설정 방법은 [환경 설정 가이드](docs/ENVIRONMENT_CONFIGURATION.md)를 참조하세요.

---

## 📖 API 사용법

### 파일 업로드
```bash
curl -X POST "http://localhost:18000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_file.txt"
```

응답 예시:
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "your_file.txt",
  "download_url": "http://localhost:18000/download/550e8400-e29b-41d4-a716-446655440000",
  "view_url": "http://localhost:18000/view/550e8400-e29b-41d4-a716-446655440000",
  "message": "File uploaded successfully"
}
```

### 파일 정보 조회
```bash
curl "http://localhost:18000/files/{file_id}"
```

### 파일 다운로드
```bash
curl "http://localhost:18000/download/{file_id}" -o downloaded_file
```

### 파일 미리보기
```bash
curl "http://localhost:18000/view/{file_id}"
```

### 파일 목록 조회
```bash
curl "http://localhost:18000/files?limit=10&offset=0"
```

### 파일 삭제
```bash
curl -X DELETE "http://localhost:18000/files/{file_id}"
```

### 프로젝트 키 생성
```bash
curl -X POST "http://localhost:18000/keygen" \
  -H "Content-Type: application/json" \
  -d '{"project_name": "my_project"}'
```

---

## 🚀 프로덕션 환경 운영 가이드

### 📋 프로덕션 배포 체크리스트

#### 배포 전 확인사항
- [ ] `.env.prod` 파일 설정 완료
- [ ] 데이터베이스 연결 확인
- [ ] 보안 환경 변수 설정
- [ ] 리소스 제한 설정 확인

#### 배포 후 확인사항
- [ ] 모든 서비스 정상 시작
- [ ] 헬스체크 통과
- [ ] API 엔드포인트 동작 확인
- [ ] 로그 모니터링 설정

### 🔧 프로덕션 환경 관리

#### 서비스 상태 모니터링
```bash
# 전체 서비스 상태 확인
docker-compose --env-file .env.prod ps

# 실시간 로그 모니터링
docker-compose --env-file .env.prod logs -f

# 특정 서비스 로그 확인
docker-compose --env-file .env.prod logs -f app
docker-compose --env-file .env.prod logs -f mariadb
```

#### 성능 모니터링
```bash
# 리소스 사용량 확인
docker stats --no-stream

# 컨테이너별 상세 정보
docker-compose --env-file .env.prod top

# 네트워크 상태 확인
docker network ls
docker network inspect dy_gh_filewallball_app-network
```

#### 백업 및 복구
```bash
# 데이터베이스 백업
docker-compose --env-file .env.prod exec mariadb mysqldump -u root -p filewallball_db > backup.sql

# 볼륨 백업
docker run --rm -v filewallball_uploads_prod_data:/data -v $(pwd):/backup alpine tar czf /backup/uploads_backup.tar.gz -C /data .

# 백업 복구
docker-compose --env-file .env.prod exec -T mariadb mysql -u root -p filewallball_db < backup.sql
```

### 🚨 문제 해결

#### 일반적인 프로덕션 문제

**1. 서비스 재시작 문제**
```bash
# 서비스 강제 재시작
docker-compose --env-file .env.prod restart app

# 컨테이너 상태 확인
docker-compose --env-file .env.prod ps app

# 로그 분석
docker-compose --env-file .env.prod logs app --tail=100
```

**2. 데이터베이스 연결 문제**
```bash
# 데이터베이스 상태 확인
docker-compose --env-file .env.prod exec mariadb mysqladmin ping -h localhost -u root -p

# 연결 테스트
docker-compose --env-file .env.prod exec app python -c "
from app.core.config import settings
print(f'DB Host: {settings.db_host}')
print(f'DB Port: {settings.db_port}')
print(f'DB Name: {settings.db_name}')
"
```

**3. 리소스 부족 문제**
```bash
# 리소스 사용량 확인
docker stats --no-stream

# 컨테이너 리소스 제한 확인
docker-compose --env-file .env.prod config | grep -A 10 "deploy:"
```

### 📈 성능 최적화

#### 워커 프로세스 조정
```bash
# 프로덕션 환경에서 워커 수 조정
# docker-compose.prod.yml 수정
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]

# 설정 적용
docker-compose --env-file .env.prod up -d --force-recreate app
```

---

## 🚨 문제 해결

### 일반적인 문제들

#### 1. Docker 버전 문제
**문제**: 잘못된 Docker 버전
```bash
# Docker 버전 확인
docker --version

# 잘못된 버전인 경우 올바른 버전 설치
sudo apt install docker.io docker-compose  # Ubuntu/Debian
```

#### 2. 포트 이미 사용 중
**문제**: 포트 18000이 이미 사용 중
```bash
# 포트 18000을 사용하는 프로세스 찾기
lsof -i :18000

# 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용 (.env 파일에서 APP_PORT 수정)
```

#### 3. 권한 문제
**문제**: 권한 거부 오류
```bash
# 업로드 디렉토리 권한 수정
chmod 755 uploads

# 스크립트 권한 수정
chmod +x scripts/*.sh
```

#### 4. 파일 저장소 경로 매핑 문제
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
docker inspect filewallball-app | grep -A 10 "Mounts"
```

#### 5. 데이터베이스 연결 문제
**문제**: 데이터베이스에 연결할 수 없음
```bash
# 데이터베이스 실행 상태 확인
docker-compose --env-file .env.dev ps mariadb

# .env 파일의 연결 설정 확인
cat .env | grep DB_
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
# Docker 로그
docker-compose logs -f app
```

#### 3. 데이터베이스 디버깅
```bash
# 데이터베이스 연결 확인
docker-compose exec app python -c "from app.core.config import get_config; print(get_config().database_url)"

# 데이터베이스 연결 테스트
docker-compose exec mariadb mysql -u root -p -e "SHOW DATABASES;"
```

### 로그 확인

```bash
# 애플리케이션 로그
docker-compose logs -f app

# 데이터베이스 로그
docker-compose logs -f mariadb

# 전체 서비스 로그
docker-compose logs -f
```

---

## 📚 문서 가이드

FileWallBall 프로젝트의 모든 문서를 체계적으로 정리한 가이드입니다. 각 문서는 특정 기능이나 영역에 대한 상세한 설명을 제공합니다.

## 🗂️ 문서 구조

### �� 프로젝트 개요 및 설정
- **[데이터베이스 설정 가이드](docs/database-setup-guide.md)** - MariaDB 설정 및 원격 접속 구성
- **[백업 및 복구 가이드](docs/backup-recovery-guide.md)** - 데이터 백업 및 복구 시스템
- **[프로덕션 배포 가이드](docs/PRODUCTION_DEPLOYMENT_GUIDE.md)** - 프로덕션 환경 배포 방법
- **[환경 설정 가이드](docs/ENVIRONMENT_CONFIGURATION.md)** - 개발/프로덕션 환경 설정
- **[배포 체크리스트](docs/DEPLOYMENT_CHECKLIST.md)** - 배포 전후 확인사항

### 🌍 프로그래밍 언어별 API 사용법 가이드
- **[언어별 가이드 개요](docs/language-guides/README.md)** - 모든 프로그래밍 언어 가이드의 공통 템플릿 및 사용법
- **[Java API 사용법 가이드](docs/language-guides/java.md)** - Java 개발자를 위한 FileWallBall API 상세 사용법
- **[Node.js API 사용법 가이드](docs/language-guides/nodejs.md)** - Node.js 개발자를 위한 FileWallBall API 상세 사용법
- **[Python API 사용법 가이드](docs/language-guides/python.md)** - Python 개발자를 위한 FileWallBall API 상세 사용법
- **[Go API 사용법 가이드](docs/language-guides/go.md)** - Go 개발자를 위한 FileWallBall API 상세 사용법
- **[공통 기능 및 고급 사용법](docs/language-guides/common-features.md)** - 모든 언어에 공통적으로 적용되는 고급 기능 가이드
- **[통합 예제 및 최종 검토](docs/language-guides/integration-examples.md)** - 각 언어별 완전한 예제 프로젝트 구조 및 품질 검증 결과

### 🔧 핵심 기능 문서
- **[테스팅 가이드](docs/TESTING_GUIDE.md)** - pytest 기반 테스팅 시스템 및 테스트 실행 방법
- **[테스트 결과 리포트](docs/TEST_RESULTS_REPORT.md)** - 테스트 실행 결과 및 분석
- **[키 생성 엔드포인트 요약](docs/KEYGEN_ENDPOINT_SUMMARY.md)** - 프로젝트 키 생성 API 상세 설명
- **[키 생성 테스트 리포트](docs/KEYGEN_TEST_REPORT.md)** - 키 생성 기능 테스트 결과

### 🛡️ 보안 및 인증
- **[보안 강화 요약](docs/SECURITY_ENHANCEMENT_SUMMARY.md)** - 보안 기능 및 인증 시스템 개선사항
- **[인프라 체크리스트](docs/INFRASTRUCTURE_CHECKLIST.md)** - 보안 및 인프라 설정 확인사항

### 📊 모니터링 및 성능
- **[MariaDB 설정](docs/MARIADB_SETUP.md)** - MariaDB 데이터베이스 설정 및 관리
- **[데이터베이스 연결 상태](docs/DB_CONNECTION_STATUS.md)** - 데이터베이스 연결 상태 확인 및 문제 해결

### 🔄 백업 및 복구
- **[백업 및 복구 가이드](docs/backup-recovery-guide.md)** - 데이터 백업 및 복구 시스템
- **[SQLite 정리 리포트](docs/SQLITE_CLEANUP_REPORT.md)** - SQLite에서 MariaDB로의 마이그레이션 과정

### 🧪 테스팅
- **[테스팅 가이드](docs/TESTING_GUIDE.md)** - pytest 기반 테스팅 시스템
- **[테스트 결과 리포트](docs/TEST_RESULTS_REPORT.md)** - 테스트 실행 결과 및 분석

### 📝 개발 및 문서화
- **[Claude 개발 가이드](docs/CLAUDE.md)** - Claude AI를 활용한 개발 가이드
- **[문서 업데이트 요약](docs/DOCUMENTATION_UPDATE_SUMMARY.md)** - 문서 업데이트 내역 및 변경사항
- **[V1 정리 요약](docs/V1_CLEANUP_SUMMARY.md)** - V1 버전 정리 및 V2 마이그레이션 과정

## 🎯 문서별 주요 내용

### 프로젝트 개요 및 설정
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [데이터베이스 설정 가이드](docs/database-setup-guide.md) | MariaDB 설정, 원격 접속 구성, 사용자 관리 | 개발자, DevOps |
| [백업 및 복구 가이드](docs/backup-recovery-guide.md) | 데이터 백업, 복구 절차, 자동화 | DevOps, 운영팀 |
| [프로덕션 배포 가이드](docs/PRODUCTION_DEPLOYMENT_GUIDE.md) | 프로덕션 환경 배포, 설정, 검증 | DevOps, 운영팀 |
| [환경 설정 가이드](docs/ENVIRONMENT_CONFIGURATION.md) | 개발/프로덕션 환경 설정, 환경 변수 관리 | 개발자, DevOps |
| [배포 체크리스트](docs/DEPLOYMENT_CHECKLIST.md) | 배포 전후 확인사항, 체크리스트 | DevOps, 운영팀 |

### 핵심 기능
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [테스팅 가이드](docs/TESTING_GUIDE.md) | pytest 테스팅, 테스트 실행, 결과 분석 | QA, 개발자 |
| [키 생성 엔드포인트](docs/KEYGEN_ENDPOINT_SUMMARY.md) | 프로젝트 키 생성 API, 사용법, 응답 형식 | API 사용자, 개발자 |
| [키 생성 테스트](docs/KEYGEN_TEST_REPORT.md) | 키 생성 기능 테스트 결과, 검증 과정 | QA, 개발자 |

### 보안 및 인증
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [보안 강화 요약](docs/SECURITY_ENHANCEMENT_SUMMARY.md) | 보안 기능, 인증 시스템, 권한 관리 | 보안팀, 개발자 |
| [인프라 체크리스트](docs/INFRASTRUCTURE_CHECKLIST.md) | 보안 설정, 인프라 구성 확인사항 | DevOps, 보안팀 |

### 모니터링 및 성능
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [MariaDB 설정](docs/MARIADB_SETUP.md) | MariaDB 설정, 데이터베이스 관리 | 개발자, DBA |
| [데이터베이스 연결 상태](docs/DB_CONNECTION_STATUS.md) | DB 연결 상태, 문제 해결, 모니터링 | 개발자, DevOps |

### 백업 및 복구
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [백업 및 복구 가이드](docs/backup-recovery-guide.md) | 자동 백업, 복구 절차, 시스템 관리 | DevOps, 운영팀 |
| [SQLite 정리 리포트](docs/SQLITE_CLEANUP_REPORT.md) | 마이그레이션 과정, 데이터 이전, 정리 | 개발자, DevOps |

### 개발 및 문서화
| 문서 | 주요 내용 | 대상 독자 |
|------|-----------|-----------|
| [Claude 개발 가이드](docs/CLAUDE.md) | AI 활용 개발, 코드 생성, 문제 해결 | 개발자 |
| [문서 업데이트 요약](docs/DOCUMENTATION_UPDATE_SUMMARY.md) | 문서 변경사항, 업데이트 내역 | 모든 사용자 |
| [V1 정리 요약](docs/V1_CLEANUP_SUMMARY.md) | 버전 마이그레이션, 코드 정리, 개선사항 | 개발자, 운영팀 |

## 🚀 빠른 시작 가이드

### 개발자 시작하기
1. **설치 및 배포 섹션** - 개발 환경 설정 (위 참조)
2. **[데이터베이스 설정 가이드](docs/database-setup-guide.md)** - 데이터베이스 설정 및 관리
3. **[환경 설정 가이드](docs/ENVIRONMENT_CONFIGURATION.md)** - 개발/프로덕션 환경 설정
4. **[프로덕션 배포 가이드](docs/PRODUCTION_DEPLOYMENT_GUIDE.md)** - 배포 및 운영
5. **[프로그래밍 언어별 API 사용법 가이드](docs/language-guides/README.md)** - 선호하는 언어로 API 사용법 학습

### API 사용자 시작하기
1. **[키 생성 엔드포인트](docs/KEYGEN_ENDPOINT_SUMMARY.md)** - API 키 생성 및 인증
2. **[언어별 API 사용법 가이드](docs/language-guides/README.md)** - 선호하는 언어로 상세한 구현 예제 확인
3. **[테스팅 가이드](docs/TESTING_GUIDE.md)** - API 테스트 및 검증

### 운영팀 시작하기
1. **[프로덕션 배포 가이드](docs/PRODUCTION_DEPLOYMENT_GUIDE.md)** - 배포 및 운영
2. **[배포 체크리스트](docs/DEPLOYMENT_CHECKLIST.md)** - 배포 전후 확인사항
3. **[백업 및 복구 가이드](docs/backup-recovery-guide.md)** - 백업 및 복구
4. **[MariaDB 설정](docs/MARIADB_SETUP.md)** - 데이터베이스 관리

### 보안팀 시작하기
1. **[보안 강화 요약](docs/SECURITY_ENHANCEMENT_SUMMARY.md)** - 보안 아키텍처
2. **[인프라 체크리스트](docs/INFRASTRUCTURE_CHECKLIST.md)** - 보안 설정 확인
3. **[데이터베이스 연결 상태](docs/DB_CONNECTION_STATUS.md)** - 보안 연결 상태

## 📊 문서 품질 관리

### 문서 업데이트 체크리스트
- [ ] 코드 변경사항 반영
- [ ] 예제 코드 검증
- [ ] 링크 유효성 확인
- [ ] 문법 및 맞춤법 검토
- [ ] 언어별 가이드 문서 동기화 (API 변경 시)
- [ ] 영문/한글 주석 일관성 확인

### 문서 버전 관리
- **주 버전**: 주요 기능 추가/변경
- **부 버전**: 문서 개선 및 수정
- **패치 버전**: 오타 수정 및 링크 업데이트

## 🔗 관련 링크

### 외부 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Redis 공식 문서](https://redis.io/documentation)
- [MariaDB 공식 문서](https://mariadb.org/documentation/)
- [Docker 공식 문서](https://docs.docker.com/)

### 프로젝트 리소스
- [GitHub 저장소](https://github.com/pathcosmos/dy_gh_filewallball)
- [API 문서 (Swagger UI)](http://localhost:18000/docs)
- [API 문서 (ReDoc)](http://localhost:18000/redoc)

## 📚 추가 리소스

### 외부 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [Redis 문서](https://redis.io/documentation)
- [Docker Compose 문서](https://docs.docker.com/compose/)

### 도구
- [Black 코드 포맷터](https://black.readthedocs.io/)
- [isort 임포트 정렬기](https://pycqa.github.io/isort/)
- [flake8 린터](https://flake8.pycqa.org/)
- [mypy 타입 체커](https://mypy.readthedocs.io/)
- [pytest 테스팅 프레임워크](https://docs.pytest.org/)

## 📞 지원 및 문의

문의사항이 있으시면 GitHub Issues를 통해 문의해주세요.

**🐙 GitHub Issues**: https://github.com/pathcosmos/dy_gh_filewallball/issues

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
3. Install dependencies with Docker Compose
4. Run tests with Docker Compose
5. Format code with development tools
6. Commit your changes
7. Push to the branch
8. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

MIT License - 자유롭게 사용, 수정, 배포할 수 있는 오픈소스 라이선스입니다.

## 📞 지원

문제가 발생하거나 질문이 있으시면 GitHub Issues를 통해 문의해주세요.

**🐙 GitHub Issues**: https://github.com/pathcosmos/dy_gh_filewallball/issues

---

이 문서는 FileWallBall 프로젝트의 모든 문서를 체계적으로 정리한 가이드입니다. 각 문서는 특정 기능이나 영역에 대한 상세한 설명을 제공하며, 프로젝트의 성공적인 개발과 운영을 지원합니다.
