# FileWallBall Redis 클라이언트 가이드

## 🎯 개요

FileWallBall Redis 클라이언트는 Redis 연결 풀과 캐싱 기능을 제공하는 Python 모듈입니다. 연결 관리, TTL 설정, 성능 최적화가 포함되어 있습니다.

## 📁 파일 구조

### 1. **Redis 클라이언트 모듈**
- `app/redis_client.py`: 메인 Redis 클라이언트 클래스
- `app/redis_pool_config.py`: 연결 풀 설정 및 환경별 설정

### 2. **테스트 스크립트**
- `scripts/test_redis_client.py`: Redis 클라이언트 기능 테스트

## 🔧 주요 기능

### 1. **Redis 연결 풀 관리**
```python
from app.redis_client import RedisClient

# 기본 연결 (localhost)
redis_client = RedisClient()

# 커스텀 설정
redis_client = RedisClient(
    host='redis',
    port=6379,
    password='filewallball2024',
    max_connections=30,
    socket_timeout=5
)
```

### 2. **TTL 기반 캐싱**
```python
from app.redis_client import CacheKeys, CacheTTL

# 파일 메타데이터 캐싱 (1시간)
file_meta = {"name": "document.pdf", "size": 1024000}
redis_client.set_with_ttl(
    CacheKeys.FILE_META.format(file_uuid="test-123"),
    file_meta,
    CacheTTL.FILE_META
)

# 세션 데이터 캐싱 (24시간)
session_data = {"user_id": 123, "permissions": ["read", "write"]}
redis_client.set_with_ttl(
    CacheKeys.SESSION.format(user_id=123),
    session_data,
    CacheTTL.SESSION
)
```

### 3. **데이터 조회 및 관리**
```python
# 데이터 조회
file_data = redis_client.get("file:meta:test-123")
session_data = redis_client.get("session:user:123")

# 키 존재 확인
exists = redis_client.exists("file:meta:test-123")

# TTL 확인
ttl = redis_client.ttl("file:meta:test-123")

# 키 삭제
redis_client.delete("file:meta:test-123")
```

## ⚙️ 환경별 설정

### 1. **개발 환경**
```python
from app.redis_pool_config import get_redis_config

config = get_redis_config('development')
# host: localhost
# max_connections: 10
# socket_timeout: 3초
```

### 2. **Kubernetes 환경**
```python
config = get_redis_config('kubernetes')
# host: redis
# max_connections: 30
# socket_timeout: 5초
```

### 3. **프로덕션 환경**
```python
config = get_redis_config('production')
# host: redis
# max_connections: 50
# socket_timeout: 10초
```

## 📊 모니터링 및 통계

### 1. **서버 정보 조회**
```python
info = redis_client.get_info()
print(f"Redis 버전: {info.get('version')}")
print(f"사용 메모리: {info.get('used_memory')}")
print(f"연결된 클라이언트: {info.get('connected_clients')}")
```

### 2. **캐시 통계 조회**
```python
stats = redis_client.get_stats()
print(f"캐시 히트율: {stats.get('hit_rate')}%")
print(f"총 요청: {stats.get('total_requests')}")
print(f"히트: {stats.get('hits')}")
print(f"미스: {stats.get('misses')}")
```

## 🔄 재시도 메커니즘

### 1. **재시도 데코레이터**
```python
from app.redis_client import retry_on_failure

@retry_on_failure(max_retries=3, delay=1.0)
def cache_operation():
    # Redis 작업 수행
    pass
```

### 2. **연결 오류 처리**
```python
try:
    with redis_client.get_connection() as conn:
        result = conn.get("key")
except redis.ConnectionError as e:
    logger.error(f"Redis 연결 오류: {e}")
    # 재시도 로직 또는 대체 처리
```

## 🎯 캐시 키 패턴

### 1. **파일 메타데이터**
```python
# 패턴: file:meta:{uuid}
cache_key = CacheKeys.FILE_META.format(file_uuid="test-123")
# TTL: 1시간 (3600초)
```

### 2. **세션 데이터**
```python
# 패턴: session:user:{user_id}
session_key = CacheKeys.SESSION.format(user_id=123)
# TTL: 24시간 (86400초)
```

### 3. **임시 데이터**
```python
# 패턴: temp:upload:progress:{upload_id}
temp_key = CacheKeys.TEMP_UPLOAD_PROGRESS.format(upload_id="upload-456")
# TTL: 10분 (600초)
```

## ⚡ 성능 최적화

### 1. **연결 풀 설정**
```python
# 성능 최적화된 설정
redis_client = RedisClient(
    max_connections=30,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30
)
```

### 2. **파이프라인 사용**
```python
with redis_client.get_connection() as conn:
    pipe = conn.pipeline()
    for i in range(100):
        pipe.set(f"key:{i}", f"value:{i}")
    pipe.execute()
```

### 3. **배치 작업**
```python
# 대량 데이터 처리
keys_to_delete = ["key1", "key2", "key3"]
with redis_client.get_connection() as conn:
    conn.delete(*keys_to_delete)
```

## 🧪 테스트 및 검증

### 1. **기능 테스트 실행**
```bash
# Redis 클라이언트 테스트
python scripts/test_redis_client.py
```

### 2. **연결 테스트**
```python
# 연결 상태 확인
if redis_client.is_connected():
    print("✅ Redis 연결 성공")
else:
    print("❌ Redis 연결 실패")
```

### 3. **성능 벤치마크**
```python
import time

# 성능 측정
start_time = time.time()
for i in range(1000):
    redis_client.set_with_ttl(f"benchmark:{i}", {"data": i}, 60)
end_time = time.time()

print(f"1000개 키 설정 시간: {end_time - start_time:.2f}초")
```

## 🔧 설정 파일 관리

### 1. **환경 변수 설정**
```bash
# .env 파일
ENVIRONMENT=kubernetes
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=filewallball2024
```

### 2. **Kubernetes ConfigMap**
```yaml
# k8s/redis-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
data:
  REDIS_HOST: redis
  REDIS_PORT: "6379"
  REDIS_PASSWORD: filewallball2024
```

## 📋 사용 체크리스트

### ✅ 기본 설정
- [x] Redis 클라이언트 초기화
- [x] 연결 풀 설정
- [x] 환경별 설정 분리
- [x] TTL 정책 적용

### ✅ 캐싱 전략
- [x] 파일 메타데이터 캐싱 (1시간)
- [x] 세션 데이터 캐싱 (24시간)
- [x] 임시 데이터 캐싱 (10분)
- [x] 캐시 키 패턴 정의

### ✅ 모니터링
- [x] 서버 정보 조회
- [x] 캐시 통계 수집
- [x] 성능 메트릭 수집
- [x] 오류 로깅

### ✅ 성능 최적화
- [x] 연결 풀 최적화
- [x] 파이프라인 사용
- [x] 배치 작업 처리
- [x] 재시도 메커니즘

## 🚀 실제 사용 예시

### 1. **파일 업로드 캐싱**
```python
def cache_file_metadata(file_uuid: str, metadata: dict):
    """파일 메타데이터 캐싱"""
    redis_client = get_redis_client()
    cache_key = CacheKeys.FILE_META.format(file_uuid=file_uuid)
    
    success = redis_client.set_with_ttl(
        cache_key, 
        metadata, 
        CacheTTL.FILE_META
    )
    
    if success:
        logger.info(f"파일 메타데이터 캐싱 성공: {file_uuid}")
    else:
        logger.error(f"파일 메타데이터 캐싱 실패: {file_uuid}")
    
    return success
```

### 2. **사용자 세션 관리**
```python
def cache_user_session(user_id: int, session_data: dict):
    """사용자 세션 캐싱"""
    redis_client = get_redis_client()
    session_key = CacheKeys.SESSION.format(user_id=user_id)
    
    success = redis_client.set_with_ttl(
        session_key,
        session_data,
        CacheTTL.SESSION
    )
    
    return success

def get_user_session(user_id: int):
    """사용자 세션 조회"""
    redis_client = get_redis_client()
    session_key = CacheKeys.SESSION.format(user_id=user_id)
    
    session_data = redis_client.get(session_key)
    return session_data
```

### 3. **업로드 진행률 추적**
```python
def update_upload_progress(upload_id: str, progress: int, status: str):
    """업로드 진행률 업데이트"""
    redis_client = get_redis_client()
    progress_key = CacheKeys.TEMP_UPLOAD_PROGRESS.format(upload_id=upload_id)
    
    progress_data = {
        "progress": progress,
        "status": status,
        "timestamp": time.time()
    }
    
    success = redis_client.set_with_ttl(
        progress_key,
        progress_data,
        CacheTTL.TEMP_DATA
    )
    
    return success
```

## 🎯 모니터링 대시보드

### 1. **캐시 성능 지표**
- 캐시 히트율: 80% 이상 유지
- 응답 시간: 10ms 이하
- 메모리 사용률: 80% 이하
- 연결 수: 1000개 이하

### 2. **알림 설정**
```python
def check_cache_health():
    """캐시 상태 확인"""
    redis_client = get_redis_client()
    stats = redis_client.get_stats()
    
    hit_rate = stats.get('hit_rate', 0)
    if hit_rate < 80:
        logger.warning(f"캐시 히트율 낮음: {hit_rate}%")
    
    info = redis_client.get_info()
    used_memory = info.get('used_memory_human', '0B')
    logger.info(f"Redis 메모리 사용량: {used_memory}")
```

## 📝 추가 권장사항

### 1. **보안 강화**
- Redis 비밀번호 강화
- 네트워크 접근 제한
- SSL/TLS 암호화 (필요시)

### 2. **확장성 고려**
- Redis Cluster 구성
- 읽기 전용 복제본
- 지리적 분산 캐싱

### 3. **백업 및 복구**
- Redis 데이터 백업
- 캐시 복구 전략
- 장애 복구 절차

---

**최종 결과**: FileWallBall Redis 클라이언트가 성공적으로 구현되었습니다. 연결 풀 관리, TTL 기반 캐싱, 성능 최적화, 모니터링 기능이 모두 포함되어 있으며, 다양한 환경에서 안정적으로 작동합니다. 