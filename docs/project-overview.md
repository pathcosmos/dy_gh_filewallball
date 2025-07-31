# FileWallBall 프로젝트 개요

## 🎯 프로젝트 개요

FileWallBall은 Kubernetes 기반의 파일 관리 시스템으로, MariaDB를 데이터베이스로 사용하고 Redis를 캐싱 레이어로 활용합니다. 자동 백업 시스템과 고성능 캐싱 정책이 구현되어 있습니다.

## 🏗️ 아키텍처 구성요소

### 1. **데이터베이스 레이어 (MariaDB)**
- **목적**: 파일 메타데이터, 사용자 정보, 시스템 설정 저장
- **구성**: Kubernetes Deployment, PersistentVolume, Service
- **백업**: 자동 CronJob + 수동 스크립트
- **복구**: 자동화된 복구 스크립트

### 2. **캐싱 레이어 (Redis)**
- **목적**: 성능 최적화를 위한 캐싱
- **구성**: Kubernetes Deployment, ConfigMap, Secret
- **정책**: TTL 기반 캐싱 (파일 메타데이터, 세션, 임시 데이터)
- **클라이언트**: Python Redis 클라이언트 모듈

### 3. **애플리케이션 레이어**
- **언어**: Python
- **프레임워크**: FastAPI (예상)
- **배포**: Kubernetes Deployment
- **모니터링**: 헬스체크, 로깅, 메트릭

## 📁 프로젝트 구조

```
fileWallBall/
├── app/                          # 애플리케이션 코드
│   ├── redis_client.py          # Redis 클라이언트
│   └── redis_pool_config.py     # Redis 설정
├── k8s/                         # Kubernetes 매니페스트
│   ├── mariadb-deployment.yaml  # MariaDB 배포
│   ├── redis-deployment.yaml    # Redis 배포
│   ├── backup-cronjob.yaml      # 백업 CronJob
│   └── backup-serviceaccount.yaml # 백업 권한
├── scripts/                     # 유틸리티 스크립트
│   ├── backup-database.sh       # 수동 백업
│   ├── restore-database.sh      # 복구 스크립트
│   ├── redis-caching-policy.sh  # Redis 정책 테스트
│   └── test_redis_client.py     # Redis 클라이언트 테스트
├── docs/                        # 문서
│   ├── backup-recovery.md       # 백업/복구 가이드
│   ├── redis-caching-policy.md  # Redis 캐싱 정책
│   ├── redis-client-guide.md    # Redis 클라이언트 가이드
│   └── project-overview.md      # 프로젝트 개요
└── backups/                     # 백업 파일 저장소
```

## 🔄 백업 및 복구 시스템

### 1. **자동 백업 (CronJob)**
```yaml
# k8s/backup-cronjob.yaml
schedule: "0 2 * * *"  # 매일 오전 2시
retention: 7일
compression: gzip
integrity_check: 자동 검증
```

### 2. **수동 백업 스크립트**
```bash
# scripts/backup-database.sh
./scripts/backup-database.sh
```

### 3. **복구 시스템**
```bash
# 백업 목록 확인
./scripts/restore-database.sh --list

# 특정 백업으로 복구
./scripts/restore-database.sh -f filewallball_backup_20240725_170206.sql.gz
```

### 4. **백업 정책**
- **빈도**: 매일 1회 자동 + 수동
- **보관**: 7일간 보관
- **압축**: gzip으로 저장 공간 절약
- **검증**: 백업 후 자동 무결성 검증
- **안전장치**: 복구 전 기존 데이터 자동 백업

## 🧠 Redis 캐싱 시스템

### 1. **TTL 정책**
```python
# 파일 메타데이터: 1시간
CacheTTL.FILE_META = 3600

# 세션 데이터: 24시간
CacheTTL.SESSION = 86400

# 임시 데이터: 10분
CacheTTL.TEMP_DATA = 600
```

### 2. **메모리 관리**
```yaml
# k8s/redis-advanced-configmap.yaml
maxmemory: 256mb
maxmemory-policy: allkeys-lru
```

### 3. **캐시 키 패턴**
```python
# 파일 메타데이터
CacheKeys.FILE_META = "file:meta:{file_uuid}"

# 세션 데이터
CacheKeys.SESSION = "session:user:{user_id}"

# 임시 데이터
CacheKeys.TEMP_UPLOAD_PROGRESS = "temp:upload:progress:{upload_id}"
```

### 4. **Redis 클라이언트**
```python
from app.redis_client import RedisClient, CacheKeys, CacheTTL

# 클라이언트 초기화
redis_client = RedisClient()

# 캐싱
redis_client.set_with_ttl(key, value, ttl)

# 조회
data = redis_client.get(key)
```

## 🚀 Kubernetes 배포

### 1. **MariaDB 배포**
```yaml
# k8s/mariadb-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mariadb
  namespace: filewallball
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mariadb
```

### 2. **Redis 배포**
```yaml
# k8s/redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: filewallball
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
```

### 3. **백업 시스템**
```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: filewallball-backup-cronjob
spec:
  schedule: "0 2 * * *"
```

## 📊 모니터링 및 관리

### 1. **데이터베이스 모니터링**
```bash
# Pod 상태 확인
microk8s kubectl get pods -n filewallball

# 백업 상태 확인
microk8s kubectl get cronjobs -n filewallball

# 백업 로그 확인
microk8s kubectl logs -n filewallball job/filewallball-backup-cronjob-<timestamp>
```

### 2. **Redis 모니터링**
```python
# 서버 정보 조회
info = redis_client.get_info()
print(f"Redis 버전: {info.get('version')}")
print(f"사용 메모리: {info.get('used_memory')}")

# 캐시 통계 조회
stats = redis_client.get_stats()
print(f"캐시 히트율: {stats.get('hit_rate')}%")
```

### 3. **성능 지표**
- **캐시 히트율**: 80% 이상 유지
- **응답 시간**: 10ms 이하
- **메모리 사용률**: 80% 이하
- **백업 성공률**: 99% 이상

## 🔧 설정 및 환경

### 1. **환경별 Redis 설정**
```python
# 개발 환경
config = get_redis_config('development')
# host: localhost, max_connections: 10

# Kubernetes 환경
config = get_redis_config('kubernetes')
# host: redis, max_connections: 30

# 프로덕션 환경
config = get_redis_config('production')
# host: redis, max_connections: 50
```

### 2. **데이터베이스 설정**
```bash
# MariaDB 설정
DB_NAME=filewallball_db
DB_USER=root
DB_PASSWORD=filewallball2024
BACKUP_DIR=/backup
```

### 3. **Redis 설정**
```bash
# Redis 설정
REDIS_PASSWORD=filewallball2024
REDIS_PORT=6379
MAX_MEMORY=256mb
```

## 🧪 테스트 및 검증

### 1. **Redis 클라이언트 테스트**
```bash
# Redis 클라이언트 기능 테스트
python scripts/test_redis_client.py
```

### 2. **백업 시스템 테스트**
```bash
# 수동 백업 테스트
./scripts/backup-database.sh

# 복구 테스트
./scripts/restore-database.sh -f <backup_file>
```

### 3. **Redis 캐싱 정책 테스트**
```bash
# Redis 캐싱 정책 테스트
./scripts/redis-caching-policy.sh
```

## 📋 구현 완료 항목

### ✅ 데이터베이스 시스템
- [x] MariaDB Kubernetes 배포
- [x] PersistentVolume 설정
- [x] 자동 백업 CronJob
- [x] 수동 백업 스크립트
- [x] 복구 스크립트
- [x] 백업 무결성 검증
- [x] 7일 보관 정책

### ✅ Redis 캐싱 시스템
- [x] Redis Kubernetes 배포
- [x] 고급 ConfigMap 설정
- [x] TTL 기반 캐싱 정책
- [x] Python Redis 클라이언트
- [x] 연결 풀 관리
- [x] 성능 최적화 설정
- [x] 캐싱 정책 테스트

### ✅ 모니터링 및 관리
- [x] 헬스체크 설정
- [x] 로깅 시스템
- [x] 성능 메트릭 수집
- [x] 백업 상태 모니터링
- [x] 캐시 통계 조회

### ✅ 문서화
- [x] 백업/복구 가이드
- [x] Redis 캐싱 정책 문서
- [x] Redis 클라이언트 가이드
- [x] 프로젝트 개요 문서

## 🚀 다음 단계

### 1. **애플리케이션 개발**
- FastAPI 애플리케이션 구현
- 파일 업로드/다운로드 API
- 사용자 인증 시스템
- 파일 메타데이터 관리

### 2. **모니터링 강화**
- Prometheus 메트릭 수집
- Grafana 대시보드
- 알림 시스템 구축
- 로그 집계 시스템

### 3. **보안 강화**
- SSL/TLS 인증서 설정
- 네트워크 정책 구성
- RBAC 권한 세분화
- 보안 스캔 도구

### 4. **확장성 고려**
- Redis Cluster 구성
- MariaDB 복제 설정
- 로드 밸런서 구성
- 자동 스케일링

## 📝 기술 스택

### **인프라**
- **Kubernetes**: microk8s
- **데이터베이스**: MariaDB 10.11
- **캐싱**: Redis 7-alpine
- **스토리지**: PersistentVolume

### **개발 도구**
- **언어**: Python 3.x
- **Redis 클라이언트**: redis-py
- **배포**: Kubernetes YAML
- **스크립팅**: Bash

### **모니터링**
- **로그**: Kubernetes 로그
- **메트릭**: Redis INFO 명령어
- **헬스체크**: Kubernetes Probe
- **백업**: mysqldump + gzip

## 🎯 성능 목표

### **응답 시간**
- API 응답: < 100ms
- 캐시 조회: < 10ms
- 데이터베이스 쿼리: < 50ms

### **가용성**
- 시스템 가용성: 99.9%
- 백업 성공률: 99.5%
- 복구 시간: < 30분

### **확장성**
- 동시 사용자: 1000명
- 파일 저장 용량: 1TB
- 캐시 메모리: 256MB

---

**최종 결과**: FileWallBall 프로젝트의 핵심 인프라가 성공적으로 구현되었습니다. 데이터베이스 백업/복구 시스템, Redis 캐싱 시스템, Kubernetes 배포 구성이 모두 완료되어 안정적이고 확장 가능한 파일 관리 시스템의 기반이 마련되었습니다.
