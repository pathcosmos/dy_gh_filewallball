# FileWallBall Scripts Directory

이 디렉토리는 FileWallBall 프로젝트의 다양한 관리 및 유틸리티 스크립트를 포함합니다.

## 📋 스크립트 목록

### 🗄️ 데이터베이스 관리

#### **setup-database.sh** - 데이터베이스 초기 설정
데이터베이스 root 비밀번호 설정 및 filewallball 계정의 원격 접속을 위한 설정 스크립트입니다.

**사용법:**
```bash
# 기본 설정으로 실행
./scripts/setup-database.sh

# 환경 변수 설정 후 실행
export DB_ROOT_PASSWORD="your_secure_password"
export DB_USER="your_filewallball_user"
export DB_PASSWORD="your_secure_user_password"
./scripts/setup-database.sh

# 도움말 보기
./scripts/setup-database.sh --help

# 연결 테스트만 실행
./scripts/setup-database.sh --test-only

# 데이터베이스 설정만 실행
./scripts/setup-database.sh --setup-only
```

**주요 기능:**
- MariaDB 컨테이너 자동 시작
- 데이터베이스 스키마 생성
- 사용자 계정 생성 및 권한 설정
- 원격 접속 허용 설정
- 연결 테스트 및 검증
- 환경 변수 파일 자동 생성

#### **test-db-connection.sh** - 데이터베이스 연결 테스트
다양한 환경에서 데이터베이스 연결을 테스트하는 스크립트입니다.

**사용법:**
```bash
# 모든 테스트 실행
./scripts/test-db-connection.sh

# 특정 테스트만 실행
./scripts/test-db-connection.sh --container-only    # 컨테이너 내부 연결만
./scripts/test-db-connection.sh --host-only         # 호스트 연결만
./scripts/test-db-connection.sh --network-only      # 네트워크 연결만
./scripts/test-db-connection.sh --permissions-only  # 사용자 권한만
./scripts/test-db-connection.sh --examples          # 연결 예제만

# 도움말 보기
./scripts/test-db-connection.sh --help
```

**테스트 항목:**
- 컨테이너 내부 연결 테스트
- 호스트에서의 연결 테스트
- 네트워크 연결성 테스트
- 사용자 권한 테스트
- 연결 예제 제공

### 🔄 서비스 관리

#### **service-manager.sh** - 서비스 관리
Docker 서비스의 시작, 중지, 재시작, 상태 확인을 관리하는 스크립트입니다.

#### **dev.sh** - 개발 환경 관리
개발 환경에서 애플리케이션을 실행하고 관리하는 스크립트입니다.

### 📊 모니터링 및 로깅

#### **health-check.sh** - 서비스 상태 확인
모든 서비스의 상태를 확인하고 헬스체크를 수행하는 스크립트입니다.

#### **log-monitor.sh** - 로그 모니터링
실시간으로 서비스 로그를 모니터링하는 스크립트입니다.

### 💾 백업 및 복구

#### **backup-enhanced.sh** - 향상된 백업
데이터베이스, 파일, 설정 등을 종합적으로 백업하는 스크립트입니다.

#### **restore-enhanced.sh** - 향상된 복구
백업에서 데이터를 복구하는 스크립트입니다.

#### **backup-volumes.sh** - 볼륨 백업
Docker 볼륨을 백업하는 스크립트입니다.

#### **restore-volumes.sh** - 볼륨 복구
백업된 Docker 볼륨을 복구하는 스크립트입니다.

## 🚀 빠른 시작

### **1. 데이터베이스 설정 (권장)**

```bash
# 스크립트 실행 권한 설정
chmod +x scripts/*.sh

# 데이터베이스 설정 실행
./scripts/setup-database.sh
```

### **2. 연결 테스트**

```bash
# 모든 연결 테스트 실행
./scripts/test-db-connection.sh
```

### **3. 서비스 시작**

```bash
# 개발 환경 시작
./scripts/dev.sh run

# 또는 Docker Compose 사용
docker-compose up -d
```

## ⚙️ 환경 변수 설정

### **데이터베이스 설정**

```bash
# 기본 데이터베이스 설정
export DB_ROOT_PASSWORD="FileWallBall_Root_2025!"
export DB_NAME="filewallball_db"
export DB_USER="filewallball_user"
export DB_PASSWORD="FileWallBall_User_2025!"
export DB_PORT="13306"
export DB_HOST="localhost"
```

### **애플리케이션 설정**

```bash
# 애플리케이션 설정
export APP_PORT="18000"
export DEBUG="true"
export LOG_LEVEL="INFO"
export ENVIRONMENT="development"
```

## 🔧 문제 해결

### **스크립트 실행 권한 문제**

```bash
# 모든 스크립트에 실행 권한 부여
chmod +x scripts/*.sh

# 특정 스크립트에만 실행 권한 부여
chmod +x scripts/setup-database.sh
chmod +x scripts/test-db-connection.sh
```

### **데이터베이스 연결 문제**

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs mariadb

# 연결 테스트
./scripts/test-db-connection.sh --container-only
```

### **환경 변수 문제**

```bash
# 환경 변수 확인
env | grep -E "DB_|APP_"

# .env 파일 생성
./scripts/setup-database.sh
```

## 📚 추가 문서

- **[데이터베이스 설정 가이드](../docs/database-setup-guide.md)** - 상세한 데이터베이스 설정 방법
- **[프로젝트 README](../README.md)** - 전체 프로젝트 개요 및 사용법
- **[배포 가이드](../docs/deployment-operations-guide.md)** - 프로덕션 배포 방법

## 🤝 기여하기

새로운 스크립트를 추가하거나 기존 스크립트를 개선하고 싶다면:

1. 스크립트에 적절한 주석 추가
2. 도움말 옵션 (`--help`) 포함
3. 에러 처리 및 로깅 추가
4. 실행 권한 설정 (`chmod +x`)
5. 이 README 파일 업데이트

---

**💡 팁**: 모든 스크립트는 `--help` 옵션을 지원하므로, 사용법을 모를 때는 이 옵션을 사용해보세요!
