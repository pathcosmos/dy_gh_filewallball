# FileWallBall Docker Compose 아키텍처 가이드

## 🐳 **개요**

FileWallBall 애플리케이션을 Docker Compose를 사용하여 컨테이너화된 환경에서 실행하는 방법을 설명합니다.

## 🏗️ **아키텍처 구성**

### **서비스 구성**
- **MariaDB**: 데이터베이스 서버 (포트: 3306)
- **FastAPI App**: 메인 애플리케이션 (포트: 8000)
- **Nginx**: 리버스 프록시 (포트: 80/443)
- **Redis**: 캐시 서버 (포트: 6379, 개발 환경)
- **Adminer**: 데이터베이스 관리 도구 (포트: 8080, 개발 환경)
- **Backup Service**: 백업 및 복구 서비스

### **볼륨 구성**
- `uploads_data`: 파일 업로드 저장소
- `logs_data`: 애플리케이션 로그
- `mariadb_data`: 데이터베이스 데이터
- `mariadb_backups`: 데이터베이스 백업
- `backups_data`: 전체 시스템 백업
- `redis_data`: Redis 캐시 데이터

## 🚀 **빠른 시작**

### **1. 환경 설정**
```bash
# 환경변수 파일 복사
cp .env.example .env

# 환경변수 수정 (필요시)
DB_ROOT_PASSWORD=your_secure_password
DB_NAME=filewallball_db
DB_USER=filewallball_user
DB_PASSWORD=your_user_password
```

### **2. 개발 환경 시작**
```bash
# 개발 환경 시작 (FastAPI + MariaDB + Redis + Adminer)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 백업 서비스 포함 시작
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile backup up -d
```

### **3. 프로덕션 환경 시작**
```bash
# 프로덕션 환경 시작
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 백업 서비스 포함 시작
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d
```

## 📋 **환경별 설정**

### **개발 환경 (docker-compose.dev.yml)**
- **Hot Reload**: FastAPI 애플리케이션 코드 변경 시 자동 재시작
- **Adminer**: 웹 기반 데이터베이스 관리 도구
- **Redis**: 개발용 캐시 서버
- **포트 노출**: 모든 서비스 포트를 호스트에 노출

### **프로덕션 환경 (docker-compose.prod.yml)**
- **리소스 제한**: CPU 및 메모리 사용량 제한
- **보안 강화**: 불필요한 포트 노출 제거
- **백업 스케줄링**: 자동 백업 스케줄 설정
- **Nginx SSL**: HTTPS 지원 (설정 필요)

## 🛠️ **관리 명령어**

### **서비스 관리**
```bash
# 서비스 상태 확인
docker-compose ps

# 서비스 로그 확인
docker-compose logs [service_name]

# 서비스 재시작
docker-compose restart [service_name]

# 전체 스택 중지
docker-compose down

# 전체 스택 중지 (볼륨 포함)
docker-compose down -v
```

### **백업 및 복구**
```bash
# 백업 서비스 시작
docker-compose --profile backup up -d backup

# 향상된 백업 실행
docker exec filewallball-backup scripts/backup-enhanced.sh

# 백업 목록 조회
docker exec filewallball-backup scripts/restore-enhanced.sh --list

# 특정 백업 복구
docker exec filewallball-backup scripts/restore-enhanced.sh --type database db_backup_full_20250824_225057.sql.gz
```

### **볼륨 관리**
```bash
# 볼륨 백업
./scripts/backup-volumes.sh

# 볼륨 복구
./scripts/restore-volumes.sh

# 사용 가능한 백업 목록
./scripts/restore-volumes.sh --list
```

## 🔍 **모니터링 및 헬스체크**

### **헬스체크 스크립트**
```bash
# 전체 서비스 헬스체크
./scripts/health-check.sh

# 특정 서비스 헬스체크
./scripts/health-check.sh mariadb
./scripts/health-check.sh app
./scripts/health-check.sh nginx
./scripts/health-check.sh redis
```

### **로그 모니터링**
```bash
# 실시간 로그 모니터링
./scripts/log-monitor.sh monitor

# 로그 통계 확인
./scripts/log-monitor.sh stats

# 로그 분석
./scripts/log-monitor.sh analyze
```

### **서비스 매니저**
```bash
# 서비스 순차적 시작
./scripts/service-manager.sh start dev

# 서비스 순차적 중지
./scripts/service-manager.sh stop dev

# 서비스 상태 확인
./scripts/service-manager.sh status dev
```

## 🔒 **보안 설정**

### **컨테이너 보안**
- `no-new-privileges`: 권한 상승 방지
- `read_only`: 읽기 전용 파일시스템 (Nginx, Adminer)
- `tmpfs`: 임시 디렉토리를 메모리 기반으로 설정

### **네트워크 보안**
- 커스텀 브리지 네트워크 (172.20.0.0/16)
- 서비스 간 내부 통신만 허용
- 외부 포트는 환경별로 제한적 노출

## 📊 **성능 최적화**

### **리소스 제한**
```yaml
# 프로덕션 환경 예시
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

### **볼륨 최적화**
- Named Volume 사용으로 데이터 영속성 보장
- 볼륨 백업 자동화
- 로그 로테이션 및 정리

## 🚨 **문제 해결**

### **일반적인 문제들**

#### **1. 포트 충돌**
```bash
# 사용 중인 포트 확인
sudo netstat -tlnp | grep :8000

# 기존 프로세스 종료
pkill -f "uvicorn app.main:app"
```

#### **2. 볼륨 마운트 오류**
```bash
# 볼륨 상태 확인
docker volume ls | grep filewallball

# 볼륨 상세 정보 확인
docker volume inspect dy_gh_filewallball_uploads_dev_data
```

#### **3. 데이터베이스 연결 실패**
```bash
# MariaDB 컨테이너 상태 확인
docker-compose ps mariadb

# MariaDB 로그 확인
docker-compose logs mariadb

# 데이터베이스 초기화 스크립트 재실행
docker-compose down -v
docker-compose up -d
```

#### **4. 백업 서비스 오류**
```bash
# 백업 컨테이너 상태 확인
docker-compose ps backup

# 백업 컨테이너 로그 확인
docker-compose logs backup

# 백업 디렉토리 권한 확인
docker exec filewallball-backup ls -la /backup/
```

### **로그 분석**
```bash
# 에러 로그 필터링
docker-compose logs | grep -i error

# 특정 서비스의 최근 로그
docker-compose logs --tail=100 app

# 실시간 로그 모니터링
docker-compose logs -f
```

## 📚 **추가 리소스**

### **Docker Compose 명령어 참조**
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [Docker Compose 파일 참조](https://docs.docker.com/compose/compose-file/)

### **MariaDB Docker 가이드**
- [MariaDB 공식 Docker 이미지](https://hub.docker.com/_/mariadb)
- [MariaDB Docker 문서](https://mariadb.com/kb/en/docker/)

### **FastAPI Docker 배포**
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/deployment/docker/)
- [Uvicorn 설정 가이드](https://www.uvicorn.org/settings/)

## 🤝 **지원 및 피드백**

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해 주세요.

---

**마지막 업데이트**: 2025-08-24
**버전**: 1.0.0
