# FileWallBall 테스트 가이드

이 문서는 Ubuntu 컨테이너에서 FileWallBall API의 전체 워크플로우를 테스트하는 방법을 설명합니다.

## 📋 테스트 개요

### 테스트 대상 기능
- ✅ 프로젝트 키 생성 (`/keygen`)
- ✅ 파일 업로드 (`/upload`)
- ✅ 파일 다운로드 (`/download/{file_id}`)
- ✅ 파일 정보 조회 (`/files/{file_id}`)
- ✅ 파일 미리보기 (`/view/{file_id}`)
- ✅ 고급 업로드 API (`/api/v1/files/upload`)
- ✅ 업로드 통계 (`/api/v1/upload/statistics/{client_ip}`)
- ✅ 시스템 메트릭 (`/metrics`)
- ✅ 파일 목록 조회 (`/api/v1/files`)
- ✅ 파일 검색 기능 (`/api/v1/files/search`)

### 테스트 환경
- **OS**: Ubuntu 22.04 (Docker 컨테이너)
- **API 서버**: FileWallBall API (포트 8001)
- **데이터베이스**: MariaDB
- **캐시**: Redis
- **모니터링**: Prometheus + Grafana

## 🚀 빠른 시작

### 1. 의존성 확인
```bash
# Docker 및 Docker Compose 설치 확인
docker --version
docker-compose --version
```

### 2. 테스트 실행

#### 빠른 테스트 (기본)
```bash
./run_test.sh quick
```

#### 전체 워크플로우 테스트
```bash
./run_test.sh full
```

#### 개발 환경 시작
```bash
./run_test.sh dev
```

## 📖 상세 사용법

### 테스트 스크립트 옵션

```bash
./run_test.sh [옵션]
```

| 옵션 | 설명 |
|------|------|
| `quick` | 빠른 테스트 실행 (기본값) |
| `full` | 전체 워크플로우 테스트 실행 |
| `build` | 테스트 컨테이너만 빌드 |
| `clean` | 테스트 환경 정리 |
| `dev` | 개발 환경 전체 시작 |
| `stop` | 모든 서비스 중지 |
| `help` | 도움말 표시 |

### Makefile 사용

```bash
# Makefile.test 사용
make -f Makefile.test help
make -f Makefile.test run-quick-test
make -f Makefile.test run-full-test
make -f Makefile.test dev-start
```

## 🔧 수동 테스트 실행

### 1. API 서버 시작
```bash
# 모든 서비스 시작
docker-compose up -d

# API 서버만 시작
docker-compose up -d filewallball mariadb redis
```

### 2. 테스트 컨테이너 빌드
```bash
docker-compose build filewallball-test
```

### 3. 테스트 실행
```bash
# 빠른 테스트
docker-compose --profile test run --rm filewallball-test /app/quick_test.sh

# 전체 테스트
docker-compose --profile test run --rm filewallball-test /app/test_full_workflow.sh
```

## 📊 테스트 결과 확인

### API 엔드포인트 접근
- **API 서버**: http://localhost:8001
- **API 문서**: http://localhost:8001/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### 로그 확인
```bash
# API 서버 로그
docker-compose logs filewallball

# 테스트 컨테이너 로그
docker-compose --profile test logs filewallball-test

# 모든 서비스 로그
docker-compose logs
```

## 🧪 테스트 시나리오

### 1. 프로젝트 키 생성
```bash
curl -X POST "http://localhost:8001/keygen" \
  -F "project_name=test-project" \
  -F "request_date=20241201" \
  -F "master_key=dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
```

### 2. 파일 업로드
```bash
curl -X POST "http://localhost:8001/upload" \
  -F "file=@test_file.txt" \
  -F "project_key=YOUR_PROJECT_KEY"
```

### 3. 파일 다운로드
```bash
curl -X GET "http://localhost:8001/download/FILE_ID" \
  -o downloaded_file.txt
```

### 4. 파일 정보 조회
```bash
curl -X GET "http://localhost:8001/files/FILE_ID"
```

## 🔍 문제 해결

### 일반적인 문제

#### 1. API 서버 연결 실패
```bash
# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs filewallball

# 포트 확인
netstat -tlnp | grep 8001
```

#### 2. 데이터베이스 연결 실패
```bash
# MariaDB 상태 확인
docker-compose logs mariadb

# 데이터베이스 연결 테스트
docker-compose exec mariadb mysql -u filewallball_user -p filewallball_db
```

#### 3. Redis 연결 실패
```bash
# Redis 상태 확인
docker-compose logs redis

# Redis 연결 테스트
docker-compose exec redis redis-cli ping
```

### 로그 레벨 조정
```bash
# 환경 변수로 로그 레벨 설정
export LOG_LEVEL=DEBUG
docker-compose up -d
```

## 📁 파일 구조

```
.
├── test_full_workflow.sh      # 전체 워크플로우 테스트 스크립트
├── quick_test.sh             # 빠른 테스트 스크립트
├── wait_for_api.sh           # API 서버 대기 스크립트
├── run_test.sh               # 테스트 실행 메인 스크립트
├── Dockerfile.test           # 테스트 컨테이너 Dockerfile
├── Makefile.test             # 테스트용 Makefile
├── docker-compose.yml        # Docker Compose 설정
├── test_results/             # 테스트 결과 저장 디렉토리
└── TEST_README.md           # 이 파일
```

## 🔐 보안 정보

### 마스터 키
- **마스터 키**: `dysnt2025FileWallersBallKAuEZzTAsBjXiQ==`
- **용도**: 프로젝트 키 생성 시 인증
- **주의**: 프로덕션 환경에서는 변경 필요

### 프로젝트 키 생성 규칙
- 프로젝트명 + 요청날짜 + IP 주소 + 마스터 키로 HMAC-SHA256 생성
- Base64 인코딩으로 변환
- 데이터베이스에 저장 및 검증

## 📈 모니터링

### Prometheus 메트릭
- 파일 업로드 성공/실패 카운터
- 업로드 시간 히스토그램
- 파일 타입별 통계
- 에러 타입별 분류

### Grafana 대시보드
- 실시간 업로드 통계
- 시스템 성능 모니터링
- 에러율 추적
- 사용량 분석

## 🚨 주의사항

1. **포트 충돌**: 8001, 3306, 6379, 3000, 9090 포트가 사용됩니다.
2. **데이터 보존**: 테스트 후 데이터베이스와 업로드 파일이 보존됩니다.
3. **리소스 사용**: 전체 환경 실행 시 충분한 메모리와 디스크 공간이 필요합니다.
4. **네트워크**: Docker 네트워크 설정이 올바르게 되어야 합니다.

## 📞 지원

문제가 발생하거나 추가 도움이 필요한 경우:
1. 로그를 확인하세요
2. 이 문서의 문제 해결 섹션을 참조하세요
3. GitHub Issues에 문제를 보고하세요 