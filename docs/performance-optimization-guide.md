# FileWallBall 성능 최적화 가이드

## 🚀 개요

FileWallBall의 성능 최적화 가이드는 시스템의 응답 시간, 처리량, 리소스 효율성을 향상시키기 위한 전략과 기법을 설명합니다.

## 📊 성능 지표

### 핵심 성능 지표 (KPI)

```python
PERFORMANCE_TARGETS = {
    "response_time": {
        "upload": "< 5초",
        "download": "< 1초",
        "api": "< 100ms"
    },
    "throughput": {
        "concurrent_users": "1000명",
        "requests_per_second": "1000 RPS",
        "file_uploads_per_minute": "100개"
    },
    "resource_utilization": {
        "cpu": "< 80%",
        "memory": "< 80%",
        "disk": "< 90%"
    },
    "availability": {
        "uptime": "99.9%",
        "error_rate": "< 0.1%"
    }
}
```

## 🔄 캐싱 최적화

### Redis 캐싱 전략

```python
# 캐시 TTL 설정
CACHE_TTL = {
    "file_metadata": 3600,      # 1시간
    "user_permissions": 1800,   # 30분
    "file_content": 300,        # 5분
    "search_results": 600,      # 10분
    "statistics": 3600          # 1시간
}

# 캐시 키 패턴
CACHE_KEYS = {
    "file_meta": "file:meta:{file_id}",
    "user_perm": "user:perm:{user_id}",
    "file_content": "file:content:{file_id}",
    "search": "search:{query_hash}",
    "stats": "stats:{date}"
}
```

### 캐시 무효화 전략

```python
class CacheInvalidationService:
    def invalidate_file_cache(self, file_id: str):
        """파일 관련 캐시 무효화"""
        keys_to_delete = [
            f"file:meta:{file_id}",
            f"file:content:{file_id}",
            f"file:thumbnail:{file_id}"
        ]
        redis_client.delete(*keys_to_delete)

    def invalidate_user_cache(self, user_id: str):
        """사용자 관련 캐시 무효화"""
        pattern = f"user:*:{user_id}"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
```

## 🗄️ 데이터베이스 최적화

### 인덱스 최적화

```sql
-- 파일 정보 테이블 인덱스
CREATE INDEX idx_file_info_user_id ON file_info(user_id);
CREATE INDEX idx_file_info_upload_time ON file_info(upload_time);
CREATE INDEX idx_file_info_file_type ON file_info(mime_type);
CREATE INDEX idx_file_info_file_size ON file_info(file_size);

-- 복합 인덱스
CREATE INDEX idx_file_info_user_upload ON file_info(user_id, upload_time);
CREATE INDEX idx_file_info_type_size ON file_info(mime_type, file_size);

-- 감사 로그 테이블 인덱스
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action);
CREATE INDEX idx_audit_logs_ip_address ON audit_logs(ip_address);
```

### 쿼리 최적화

```python
# 페이지네이션 최적화
def get_files_with_pagination(user_id: int, page: int, size: int):
    offset = (page - 1) * size
    return db.query(FileInfo).filter(
        FileInfo.user_id == user_id
    ).order_by(
        FileInfo.upload_time.desc()
    ).offset(offset).limit(size).all()

# 배치 처리
def batch_insert_files(files_data: List[Dict]):
    db.bulk_insert_mappings(FileInfo, files_data)
    db.commit()
```

## 📁 파일 처리 최적화

### 비동기 파일 처리

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncFileProcessor:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def process_file_async(self, file_content: bytes, filename: str):
        """비동기 파일 처리"""
        # 파일 검증 (동기 작업을 비동기로 실행)
        validation_task = asyncio.get_event_loop().run_in_executor(
            self.executor, self._validate_file, file_content, filename
        )

        # 썸네일 생성 (병렬 처리)
        thumbnail_task = asyncio.get_event_loop().run_in_executor(
            self.executor, self._generate_thumbnail, file_content
        )

        # 메타데이터 추출 (병렬 처리)
        metadata_task = asyncio.get_event_loop().run_in_executor(
            self.executor, self._extract_metadata, file_content
        )

        # 모든 작업 완료 대기
        validation_result, thumbnail_data, metadata = await asyncio.gather(
            validation_task, thumbnail_task, metadata_task
        )

        return {
            "validation": validation_result,
            "thumbnail": thumbnail_data,
            "metadata": metadata
        }
```

### 스트리밍 업로드

```python
async def stream_upload_file(file: UploadFile):
    """스트리밍 파일 업로드"""
    chunk_size = 1024 * 1024  # 1MB 청크

    file_path = f"uploads/{uuid.uuid4()}_{file.filename}"

    with open(file_path, "wb") as f:
        while chunk := await file.read(chunk_size):
            f.write(chunk)

    return file_path
```

## 🔧 애플리케이션 최적화

### 연결 풀 최적화

```python
# 데이터베이스 연결 풀 설정
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}

# Redis 연결 풀 설정
REDIS_CONFIG = {
    "max_connections": 50,
    "retry_on_timeout": True,
    "socket_keepalive": True,
    "socket_keepalive_options": {}
}
```

### 비동기 처리

```python
# 백그라운드 작업
@app.post("/upload")
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    # 즉시 응답
    file_id = str(uuid.uuid4())

    # 백그라운드에서 처리
    background_tasks.add_task(process_file_background, file_id, file)

    return {"file_id": file_id, "status": "processing"}
```

## 📊 모니터링 및 프로파일링

### 성능 메트릭 수집

```python
from prometheus_client import Histogram, Counter

# 성능 메트릭
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

file_upload_duration = Histogram(
    'file_upload_duration_seconds',
    'File upload duration',
    ['file_type', 'file_size']
)

cache_hit_ratio = Counter(
    'cache_hit_ratio',
    'Cache hit ratio',
    ['cache_type']
)
```

### 성능 프로파일링

```python
import cProfile
import pstats
from functools import wraps

def profile_function(func):
    """함수 성능 프로파일링 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()

        # 프로파일 결과 저장
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)  # 상위 10개 함수

        return result
    return wrapper
```

## 🚀 배포 최적화

### Docker 최적화

```dockerfile
# 멀티스테이지 빌드
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .

# 성능 최적화 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=2

# 워커 프로세스 설정
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Kubernetes 최적화

```yaml
# 리소스 제한 및 요청
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

# 헬스체크 최적화
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
```

## 📋 성능 최적화 체크리스트

### 배포 전 성능 확인

- [ ] 응답 시간이 목표치 이하
- [ ] 처리량이 목표치 이상
- [ ] 리소스 사용률이 적정 수준
- [ ] 캐시 히트율이 80% 이상
- [ ] 데이터베이스 쿼리가 최적화됨
- [ ] 파일 업로드/다운로드가 최적화됨

### 정기 성능 점검

- [ ] 성능 메트릭 모니터링
- [ ] 병목 지점 분석
- [ ] 캐시 효율성 검토
- [ ] 데이터베이스 성능 분석
- [ ] 리소스 사용량 최적화

---

이 문서는 FileWallBall의 성능 최적화 전략을 설명합니다. 성능 관련 질문이나 개선 제안이 있으시면 개발팀에 문의해 주세요.
