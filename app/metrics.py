"""
Prometheus 메트릭 정의
Task 9: Prometheus 메트릭 및 모니터링 시스템
Task 3.5: 캐시 모니터링 및 메트릭 구현
"""

import time
from functools import wraps
from typing import Any, Callable, Dict

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# HTTP 요청 메트릭
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status", "status_class"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_class"],
)

# 파일 업로드 관련 메트릭
file_upload_counter = Counter(
    "file_upload_total",
    "Total number of file uploads",
    ["status", "file_type", "user_id"],
)

file_download_counter = Counter(
    "file_download_total",
    "Total number of file downloads",
    ["status", "file_type", "user_id"],
)

file_upload_duration = Histogram(
    "file_upload_duration_seconds",
    "Time spent on file uploads",
    ["file_type", "status"],
)

file_upload_error_counter = Counter(
    "file_upload_errors_total",
    "Total number of file upload errors",
    ["error_type", "file_type"],
)

# 시스템 성능 메트릭
active_connections_gauge = Gauge("active_connections", "Number of active connections")

error_rate_counter = Counter(
    "error_rate_total", "Total number of errors", ["error_type", "endpoint"]
)

file_processing_duration = Histogram(
    "file_processing_duration_seconds",
    "Time spent processing files",
    ["operation", "file_type"],
)

# Redis 캐시 성능 메트릭 (상세)
cache_hit_counter = Counter(
    "cache_hits_total", "Total number of cache hits", ["cache_type", "key_pattern"]
)

cache_miss_counter = Counter(
    "cache_misses_total", "Total number of cache misses", ["cache_type", "key_pattern"]
)

cache_operation_duration = Histogram(
    "cache_operation_duration_seconds",
    "Time spent on cache operations",
    ["operation", "cache_type", "status"],
)

cache_set_counter = Counter(
    "cache_set_total",
    "Total number of cache set operations",
    ["cache_type", "key_pattern"],
)

cache_delete_counter = Counter(
    "cache_delete_total",
    "Total number of cache delete operations",
    ["cache_type", "key_pattern"],
)

cache_invalidation_counter = Counter(
    "cache_invalidation_total",
    "Total number of cache invalidations",
    ["cache_type", "invalidation_type"],
)

# Redis 메모리 및 연결 메트릭
redis_memory_usage_gauge = Gauge(
    "redis_memory_usage_bytes", "Redis memory usage in bytes", ["redis_instance"]
)

redis_connected_clients_gauge = Gauge(
    "redis_connected_clients", "Number of connected Redis clients", ["redis_instance"]
)

redis_used_memory_peak_gauge = Gauge(
    "redis_used_memory_peak_bytes", "Peak memory usage in Redis", ["redis_instance"]
)

redis_keyspace_hits_gauge = Gauge(
    "redis_keyspace_hits",
    "Number of successful key lookups in Redis",
    ["redis_instance"],
)

redis_keyspace_misses_gauge = Gauge(
    "redis_keyspace_misses", "Number of failed key lookups in Redis", ["redis_instance"]
)

redis_evicted_keys_gauge = Gauge(
    "redis_evicted_keys", "Number of evicted keys in Redis", ["redis_instance"]
)

redis_expired_keys_gauge = Gauge(
    "redis_expired_keys", "Number of expired keys in Redis", ["redis_instance"]
)

# 캐시 키별 상세 메트릭
cache_key_operations = Counter(
    "cache_key_operations_total",
    "Cache operations by key pattern",
    ["operation", "key_pattern", "status"],
)

cache_ttl_distribution = Histogram(
    "cache_ttl_seconds",
    "Distribution of cache TTL values",
    ["cache_type", "key_pattern"],
)

# 데이터베이스 성능 메트릭
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Time spent on database queries",
    ["operation", "table"],
)

# API 성능 메트릭
api_request_duration = Histogram(
    "api_request_duration_seconds",
    "Time spent on API requests",
    ["method", "endpoint", "status_code"],
)

api_request_counter = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
)

# 시스템 리소스 메트릭
memory_usage_gauge = Gauge("memory_usage_bytes", "Current memory usage in bytes")

disk_usage_gauge = Gauge("disk_usage_bytes", "Current disk usage in bytes")

# 사용자 활동 메트릭
user_login_counter = Counter(
    "user_logins_total", "Total number of user logins", ["status"]
)

user_registration_counter = Counter(
    "user_registrations_total", "Total number of user registrations", ["status"]
)


class CacheMetricsCollector:
    """캐시 메트릭 수집기"""

    def __init__(self):
        self.start_time = time.time()

    def record_cache_hit(self, cache_type: str = "redis", key_pattern: str = "unknown"):
        """캐시 히트 기록"""
        cache_hit_counter.labels(cache_type=cache_type, key_pattern=key_pattern).inc()

    def record_cache_miss(
        self, cache_type: str = "redis", key_pattern: str = "unknown"
    ):
        """캐시 미스 기록"""
        cache_miss_counter.labels(cache_type=cache_type, key_pattern=key_pattern).inc()

    def record_cache_operation(
        self,
        operation: str,
        cache_type: str = "redis",
        status: str = "success",
        duration: float = None,
    ):
        """캐시 작업 기록"""
        if duration is not None:
            cache_operation_duration.labels(
                operation=operation, cache_type=cache_type, status=status
            ).observe(duration)

    def record_cache_set(self, cache_type: str = "redis", key_pattern: str = "unknown"):
        """캐시 설정 작업 기록"""
        cache_set_counter.labels(cache_type=cache_type, key_pattern=key_pattern).inc()

    def record_cache_delete(
        self, cache_type: str = "redis", key_pattern: str = "unknown"
    ):
        """캐시 삭제 작업 기록"""
        cache_delete_counter.labels(
            cache_type=cache_type, key_pattern=key_pattern
        ).inc()

    def record_cache_invalidation(
        self, cache_type: str = "redis", invalidation_type: str = "manual"
    ):
        """캐시 무효화 기록"""
        cache_invalidation_counter.labels(
            cache_type=cache_type, invalidation_type=invalidation_type
        ).inc()

    def record_key_operation(
        self, operation: str, key_pattern: str, status: str = "success"
    ):
        """키별 작업 기록"""
        cache_key_operations.labels(
            operation=operation, key_pattern=key_pattern, status=status
        ).inc()

    def record_ttl(
        self, cache_type: str = "redis", key_pattern: str = "unknown", ttl: float = 0
    ):
        """TTL 분포 기록"""
        cache_ttl_distribution.labels(
            cache_type=cache_type, key_pattern=key_pattern
        ).observe(ttl)

    def get_cache_hit_rate(self) -> float:
        """캐시 히트율 계산"""
        total_hits = cache_hit_counter._value.sum()
        total_misses = cache_miss_counter._value.sum()
        total_requests = total_hits + total_misses

        if total_requests == 0:
            return 0.0

        return (total_hits / total_requests) * 100


def cache_metrics_decorator(
    operation: str, cache_type: str = "redis", key_pattern: str = "unknown"
):
    """캐시 메트릭 수집 데코레이터"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics_collector = CacheMetricsCollector()

            try:
                result = await func(*args, **kwargs)

                # 성공 시 메트릭 기록
                duration = time.time() - start_time
                metrics_collector.record_cache_operation(
                    operation=operation,
                    cache_type=cache_type,
                    status="success",
                    duration=duration,
                )

                # 작업별 특정 메트릭
                if operation == "get":
                    if result is not None:
                        metrics_collector.record_cache_hit(cache_type, key_pattern)
                    else:
                        metrics_collector.record_cache_miss(cache_type, key_pattern)
                elif operation == "set":
                    metrics_collector.record_cache_set(cache_type, key_pattern)
                elif operation == "delete":
                    metrics_collector.record_cache_delete(cache_type, key_pattern)

                metrics_collector.record_key_operation(
                    operation, key_pattern, "success"
                )

                return result

            except Exception as e:
                # 실패 시 메트릭 기록
                duration = time.time() - start_time
                metrics_collector.record_cache_operation(
                    operation=operation,
                    cache_type=cache_type,
                    status="error",
                    duration=duration,
                )
                metrics_collector.record_key_operation(operation, key_pattern, "error")
                raise

        return wrapper

    return decorator


async def update_redis_metrics(redis_client) -> Dict[str, Any]:
    """Redis 메트릭 업데이트"""
    try:
        info = await redis_client.get_info()
        stats = await redis_client.get_stats()

        # Redis 메모리 메트릭 업데이트
        redis_memory_usage_gauge.labels(redis_instance="main").set(
            info.get("used_memory", 0)
        )
        redis_used_memory_peak_gauge.labels(redis_instance="main").set(
            info.get("used_memory_peak", 0)
        )
        redis_connected_clients_gauge.labels(redis_instance="main").set(
            info.get("connected_clients", 0)
        )

        # Redis 키스페이스 메트릭 업데이트
        redis_keyspace_hits_gauge.labels(redis_instance="main").set(
            info.get("keyspace_hits", 0)
        )
        redis_keyspace_misses_gauge.labels(redis_instance="main").set(
            info.get("keyspace_misses", 0)
        )
        redis_evicted_keys_gauge.labels(redis_instance="main").set(
            info.get("evicted_keys", 0)
        )
        redis_expired_keys_gauge.labels(redis_instance="main").set(
            info.get("expired_keys", 0)
        )

        return {
            "memory_usage": info.get("used_memory", 0),
            "connected_clients": info.get("connected_clients", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": calculate_redis_hit_rate(info),
            "stats": stats,
        }

    except Exception as e:
        # Redis 연결 실패 시 메트릭 초기화
        redis_memory_usage_gauge.labels(redis_instance="main").set(0)
        redis_connected_clients_gauge.labels(redis_instance="main").set(0)
        return {"error": str(e)}


def calculate_redis_hit_rate(info: Dict[str, Any]) -> float:
    """Redis 히트율 계산"""
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    total = hits + misses

    if total == 0:
        return 0.0

    return (hits / total) * 100


def get_metrics() -> str:
    """Prometheus 메트릭 데이터 반환"""
    return generate_latest()


def get_metrics_content_type() -> str:
    """Prometheus 메트릭 Content-Type 반환"""
    return CONTENT_TYPE_LATEST


# 전역 메트릭 수집기 인스턴스
cache_metrics = CacheMetricsCollector()
