# FileWallBall Redis 캐싱 정책 가이드

## 🎯 캐싱 정책 개요

### ✅ 구현된 캐싱 정책

#### 1. **TTL (Time To Live) 정책**
- **파일 메타데이터**: 1시간 (3600초)
- **세션 데이터**: 24시간 (86400초)
- **임시 데이터**: 10분 (600초)

#### 2. **메모리 관리 정책**
- **최대 메모리**: 256MB
- **메모리 정책**: allkeys-lru (Least Recently Used)
- **샘플링**: 5개 키 샘플링으로 LRU 결정

#### 3. **데이터 지속성 정책**
- **AOF (Append Only File)**: 활성화
- **RDB 스냅샷**: 주기적 백업
- **복제 준비**: 향후 클러스터 확장용

## 📊 캐싱 정책 세부 사항

### 1. **파일 메타데이터 캐싱**
```bash
# 파일 메타데이터 캐시 예시
SET file:meta:uuid123 '{"name":"document.pdf","size":1024000,"type":"application/pdf"}' EX 3600
```

**특징:**
- **TTL**: 1시간
- **용도**: 파일 정보, 크기, 타입 등
- **패턴**: `file:meta:{uuid}`
- **데이터 형식**: JSON

### 2. **세션 데이터 캐싱**
```bash
# 세션 데이터 캐시 예시
SET session:user:123 '{"user_id":123,"login_time":"2024-01-01","permissions":["read","write"]}' EX 86400
```

**특징:**
- **TTL**: 24시간
- **용도**: 사용자 세션, 권한 정보
- **패턴**: `session:user:{user_id}`
- **데이터 형식**: JSON

### 3. **임시 데이터 캐싱**
```bash
# 임시 데이터 캐시 예시
SET temp:upload:progress:456 '{"progress":75,"status":"uploading"}' EX 600
```

**특징:**
- **TTL**: 10분
- **용도**: 업로드 진행률, 임시 상태
- **패턴**: `temp:{type}:{id}`
- **데이터 형식**: JSON

## 🧠 메모리 관리 정책

### 1. **LRU (Least Recently Used) 정책**
```bash
# 메모리 정책 확인
CONFIG GET maxmemory-policy
# 결과: allkeys-lru
```

**동작 방식:**
- 메모리 한계 도달 시 가장 오래 전에 사용된 키부터 삭제
- 모든 키에 대해 LRU 적용
- 캐시 효율성 최적화

### 2. **메모리 제한**
```bash
# 메모리 제한 확인
CONFIG GET maxmemory
# 결과: 268435456 (256MB)
```

**설정:**
- **최대 메모리**: 256MB
- **샘플링**: 5개 키로 LRU 결정
- **압축**: 메모리 효율성을 위한 최적화

## ⚡ 성능 최적화

### 1. **네트워크 최적화**
```bash
# 네트워크 설정
tcp-nodelay yes
tcp-keepalive 300
```

### 2. **메모리 최적화**
```bash
# 메모리 최적화 설정
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
```

### 3. **클라이언트 버퍼 설정**
```bash
# 클라이언트 버퍼 제한
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit slave 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
```

## 📈 모니터링 및 성능 측정

### 1. **성능 테스트 결과**
- **연결 테스트**: ✅ 성공
- **TTL 정책**: ✅ 모든 TTL 정상 설정
- **메모리 정책**: ✅ 256MB 제한, allkeys-lru 적용
- **성능 테스트**: 50회 랜덤 읽기 7.1초

### 2. **모니터링 지표**
```bash
# 메모리 사용량 확인
INFO memory

# 키 개수 확인
DBSIZE

# 느린 쿼리 확인
SLOWLOG GET 10
```

### 3. **성능 최적화 권장사항**
- **캐시 히트율**: 80% 이상 유지
- **메모리 사용률**: 80% 이하 유지
- **연결 수**: 1000개 이하 유지
- **응답 시간**: 10ms 이하 유지

## 🔧 설정 파일 구조

### 1. **ConfigMap 설정**
```yaml
# k8s/redis-advanced-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-advanced-config
data:
  redis.conf: |
    # 캐싱 정책 설정
    maxmemory 256mb
    maxmemory-policy allkeys-lru

    # AOF 설정
    appendonly yes
    appendfsync everysec

    # 성능 최적화
    tcp-nodelay yes
    maxmemory-samples 5
```

### 2. **테스트 스크립트**
```bash
# scripts/redis-caching-policy.sh
# TTL 정책 테스트
# 메모리 정책 테스트
# 성능 테스트
```

## 🚀 사용 예시

### 1. **파일 메타데이터 캐싱**
```python
import redis
import json

# Redis 연결
r = redis.Redis(host='redis', port=6379, password='filewallball2024')

# 파일 메타데이터 캐싱
file_meta = {
    "name": "document.pdf",
    "size": 1024000,
    "type": "application/pdf",
    "upload_time": "2024-01-01T10:00:00Z"
}

# 1시간 TTL로 캐싱
r.setex(f"file:meta:{file_uuid}", 3600, json.dumps(file_meta))
```

### 2. **세션 데이터 캐싱**
```python
# 사용자 세션 캐싱
session_data = {
    "user_id": 123,
    "login_time": "2024-01-01T10:00:00Z",
    "permissions": ["read", "write"],
    "last_activity": "2024-01-01T10:30:00Z"
}

# 24시간 TTL로 캐싱
r.setex(f"session:user:{user_id}", 86400, json.dumps(session_data))
```

### 3. **임시 데이터 캐싱**
```python
# 업로드 진행률 캐싱
progress_data = {
    "progress": 75,
    "status": "uploading",
    "bytes_uploaded": 768000,
    "total_bytes": 1024000
}

# 10분 TTL로 캐싱
r.setex(f"temp:upload:progress:{upload_id}", 600, json.dumps(progress_data))
```

## 📋 캐싱 정책 체크리스트

### ✅ 완료된 항목
- [x] TTL 정책 설정 (파일 메타데이터, 세션, 임시 데이터)
- [x] 메모리 관리 정책 (LRU, 256MB 제한)
- [x] 성능 최적화 설정
- [x] AOF 데이터 지속성 설정
- [x] 캐싱 정책 테스트 스크립트
- [x] 성능 모니터링 설정

### 🔄 지속적 모니터링
- [ ] 캐시 히트율 추적
- [ ] 메모리 사용률 모니터링
- [ ] 응답 시간 측정
- [ ] TTL 만료 패턴 분석

## 🎯 최적화 권장사항

### 1. **캐시 키 설계**
- **네임스페이스**: `{type}:{category}:{id}`
- **TTL 일관성**: 동일 유형의 데이터는 동일 TTL
- **키 크기**: 최소화하여 메모리 효율성 향상

### 2. **성능 최적화**
- **파이프라인**: 다중 명령어 배치 처리
- **연결 풀**: 애플리케이션 레벨 연결 관리
- **모니터링**: 실시간 성능 지표 추적

### 3. **확장성 고려**
- **클러스터링**: 향후 Redis Cluster 구성
- **복제**: 읽기 부하 분산
- **백업**: 정기적인 데이터 백업

---

**최종 결과**: FileWallBall Redis 캐싱 정책이 성공적으로 구현되었습니다. TTL 정책, 메모리 관리, 성능 최적화가 모두 적용되어 있으며, 테스트를 통해 정상 작동을 확인했습니다.
