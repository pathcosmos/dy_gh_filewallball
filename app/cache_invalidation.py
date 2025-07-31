#!/usr/bin/env python3
"""
FileWallBall 캐시 무효화 및 TTL 관리 시스템
Task 3.3: TTL 관리 및 캐시 무효화 전략 구현
Task 3.5: 캐시 모니터링 및 메트릭 구현

주요 기능:
- 캐시 무효화 데코레이터 (@invalidate_cache)
- 파일 CRUD 작업 시 관련 캐시 자동 삭제
- 패턴 매칭을 통한 벌크 삭제 (SCAN + DEL)
- 캐시 무효화 이벤트 로깅
- 캐시 무효화 메트릭 수집
"""

import asyncio
import functools
import inspect
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.async_redis_client import AsyncRedisClient, get_async_redis_client
from app.cache_models import CacheKeyManager, CacheTTL, get_cache_key_manager
from app.metrics import cache_metrics

# 로깅 설정
logger = logging.getLogger(__name__)


class InvalidationEvent(str, Enum):
    """캐시 무효화 이벤트 타입"""

    FILE_CREATED = "file_created"
    FILE_UPDATED = "file_updated"
    FILE_DELETED = "file_deleted"
    FILE_ACCESSED = "file_accessed"
    USER_SESSION_EXPIRED = "user_session_expired"
    STATS_UPDATED = "stats_updated"
    SYSTEM_SETTINGS_CHANGED = "system_settings_changed"
    BULK_INVALIDATION = "bulk_invalidation"
    TTL_EXPIRED = "ttl_expired"


class CacheInvalidationStrategy(str, Enum):
    """캐시 무효화 전략"""

    IMMEDIATE = "immediate"  # 즉시 삭제
    LAZY = "lazy"  # 지연 삭제 (TTL 기반)
    PATTERN_BASED = "pattern_based"  # 패턴 기반 삭제
    SELECTIVE = "selective"  # 선택적 삭제


class CacheInvalidationEvent:
    """캐시 무효화 이벤트 모델"""

    def __init__(
        self,
        event_type: InvalidationEvent,
        keys: List[str],
        strategy: CacheInvalidationStrategy,
        timestamp: datetime = None,
        metadata: Dict[str, Any] = None,
    ):
        self.event_type = event_type
        self.keys = keys
        self.strategy = strategy
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """이벤트를 딕셔너리로 변환"""
        return {
            "event_type": self.event_type.value,
            "keys": self.keys,
            "strategy": self.strategy.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class CacheInvalidationManager:
    """캐시 무효화 관리자"""

    def __init__(self, redis_client: AsyncRedisClient, key_manager: CacheKeyManager):
        self.redis_client = redis_client
        self.key_manager = key_manager
        self.invalidation_queue: List[CacheInvalidationEvent] = []
        self.max_queue_size = 1000
        self.batch_size = 50
        self.processing_interval = 5.0  # 초
        self._processing_task: Optional[asyncio.Task] = None

    async def start_background_processing(self):
        """백그라운드 처리 시작"""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(
                self._process_invalidation_queue()
            )
            logger.info("캐시 무효화 백그라운드 처리 시작")

    async def stop_background_processing(self):
        """백그라운드 처리 중지"""
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            logger.info("캐시 무효화 백그라운드 처리 중지")

    async def _process_invalidation_queue(self):
        """무효화 큐 처리"""
        while True:
            try:
                if self.invalidation_queue:
                    # 배치 처리
                    batch = self.invalidation_queue[: self.batch_size]
                    self.invalidation_queue = self.invalidation_queue[self.batch_size :]

                    await self._process_batch(batch)

                await asyncio.sleep(self.processing_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"무효화 큐 처리 오류: {e}")
                await asyncio.sleep(self.processing_interval)

    async def _process_batch(self, events: List[CacheInvalidationEvent]):
        """배치 무효화 처리"""
        for event in events:
            try:
                await self._process_invalidation_event(event)
            except Exception as e:
                logger.error(f"무효화 이벤트 처리 실패: {event.event_type}, 오류: {e}")

    async def _process_invalidation_event(self, event: CacheInvalidationEvent) -> bool:
        """무효화 이벤트 처리"""
        start_time = time.time()

        try:
            if event.strategy == CacheInvalidationStrategy.IMMEDIATE:
                deleted_count = await self._invalidate_keys_immediate(event.keys)
            elif event.strategy == CacheInvalidationStrategy.PATTERN_BASED:
                deleted_count = await self._invalidate_keys_by_pattern(event.keys)
            elif event.strategy == CacheInvalidationStrategy.SELECTIVE:
                deleted_count = await self._invalidate_keys_selective(event.keys)
            else:
                # LAZY 전략은 TTL 기반이므로 즉시 삭제하지 않음
                deleted_count = 0

            # 메트릭 기록
            duration = time.time() - start_time
            cache_metrics.record_cache_invalidation(
                cache_type="redis", invalidation_type=event.strategy.value
            )
            cache_metrics.record_cache_operation(
                operation="invalidation",
                cache_type="redis",
                status="success",
                duration=duration,
            )

            logger.info(
                f"캐시 무효화 완료: {event.event_type.value}, "
                f"삭제된 키: {deleted_count}개, "
                f"소요시간: {duration:.3f}초"
            )

            return True

        except Exception as e:
            # 실패 시 메트릭 기록
            duration = time.time() - start_time
            cache_metrics.record_cache_operation(
                operation="invalidation",
                cache_type="redis",
                status="error",
                duration=duration,
            )

            logger.error(f"캐시 무효화 실패: {event.event_type.value}, 오류: {e}")
            return False

    async def _invalidate_keys_immediate(self, keys: List[str]) -> int:
        """즉시 키 무효화"""
        if not keys:
            return 0

        try:
            deleted_count = 0
            for key in keys:
                if await self.redis_client.delete(key):
                    deleted_count += 1

            return deleted_count
        except Exception as e:
            logger.error(f"즉시 무효화 실패: {e}")
            return 0

    async def _invalidate_keys_by_pattern(self, patterns: List[str]) -> int:
        """패턴 기반 키 무효화"""
        if not patterns:
            return 0

        try:
            total_deleted = 0
            for pattern in patterns:
                keys = await self.redis_client.scan_iter(match=pattern)
                if keys:
                    deleted_count = await self.redis_client.delete_pattern(pattern)
                    total_deleted += deleted_count

            return total_deleted
        except Exception as e:
            logger.error(f"패턴 기반 무효화 실패: {e}")
            return 0

    async def _invalidate_keys_selective(self, keys: List[str]) -> int:
        """선택적 키 무효화"""
        if not keys:
            return 0

        try:
            # 존재하는 키만 필터링
            existing_keys = []
            for key in keys:
                if await self.redis_client.exists(key):
                    existing_keys.append(key)

            # 존재하는 키만 삭제
            deleted_count = 0
            for key in existing_keys:
                if await self.redis_client.delete(key):
                    deleted_count += 1

            return deleted_count
        except Exception as e:
            logger.error(f"선택적 무효화 실패: {e}")
            return 0

    def add_invalidation_event(
        self,
        event_type: InvalidationEvent,
        keys: List[str],
        strategy: CacheInvalidationStrategy = CacheInvalidationStrategy.IMMEDIATE,
        metadata: Dict[str, Any] = None,
    ) -> CacheInvalidationEvent:
        """무효화 이벤트 추가"""
        event = CacheInvalidationEvent(
            event_type=event_type, keys=keys, strategy=strategy, metadata=metadata
        )

        # 큐 크기 제한
        if len(self.invalidation_queue) >= self.max_queue_size:
            # 가장 오래된 이벤트 제거
            self.invalidation_queue.pop(0)

        self.invalidation_queue.append(event)
        logger.debug(f"무효화 이벤트 추가: {event_type.value}, 키 수: {len(keys)}")

        return event


class TTLManager:
    """TTL 관리자"""

    def __init__(self, redis_client: AsyncRedisClient, key_manager: CacheKeyManager):
        self.redis_client = redis_client
        self.key_manager = key_manager

    def get_ttl(self, cache_type: CacheTTL) -> int:
        """캐시 타입별 TTL 반환"""
        return cache_type.value

    async def set_with_ttl(
        self,
        key: str,
        value: Any,
        cache_type: CacheTTL,
        custom_ttl: Optional[int] = None,
    ) -> bool:
        """TTL과 함께 값 설정"""
        ttl = custom_ttl or self.get_ttl(cache_type)

        # 메트릭 기록
        cache_metrics.record_ttl(cache_type="redis", key_pattern="file_meta", ttl=ttl)

        return await self.redis_client.set_with_ttl(key, value, ttl)

    async def extend_ttl(self, key: str, cache_type: CacheTTL) -> bool:
        """TTL 연장"""
        try:
            current_ttl = await self.redis_client.ttl(key)
            if current_ttl > 0:
                new_ttl = self.get_ttl(cache_type)
                # TTL 연장을 위해 값을 다시 설정
                value = await self.redis_client.get(key)
                if value is not None:
                    return await self.redis_client.set_with_ttl(key, value, new_ttl)
            return False
        except Exception as e:
            logger.error(f"TTL 연장 실패: {key}, 오류: {e}")
            return False

    async def get_remaining_ttl(self, key: str) -> int:
        """남은 TTL 조회"""
        return await self.redis_client.ttl(key)

    async def refresh_ttl(self, key: str, cache_type: CacheTTL) -> bool:
        """TTL 새로고침 (연장과 동일)"""
        return await self.extend_ttl(key, cache_type)


def invalidate_cache(
    event_type: InvalidationEvent,
    key_patterns: List[str] = None,
    strategy: CacheInvalidationStrategy = CacheInvalidationStrategy.IMMEDIATE,
    metadata: Dict[str, Any] = None,
):
    """캐시 무효화 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 함수 실행
            result = await func(*args, **kwargs)

            # 캐시 무효화 실행
            await _execute_cache_invalidation(
                event_type, key_patterns or [], strategy, metadata, args, kwargs
            )

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 함수 실행
            result = func(*args, **kwargs)

            # 비동기 무효화 실행 (이벤트 루프에서)
            asyncio.create_task(
                _execute_cache_invalidation(
                    event_type, key_patterns or [], strategy, metadata, args, kwargs
                )
            )

            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


async def _execute_cache_invalidation(
    event_type: InvalidationEvent,
    key_patterns: List[str],
    strategy: CacheInvalidationStrategy,
    metadata: Dict[str, Any],
    args: tuple,
    kwargs: dict,
):
    """캐시 무효화 실행"""
    try:
        # 키 패턴 해석
        resolved_keys = _resolve_key_patterns(key_patterns, args, kwargs)

        if resolved_keys:
            # 무효화 매니저 가져오기
            redis_client = await get_async_redis_client()
            key_manager = get_cache_key_manager()
            invalidation_manager = CacheInvalidationManager(redis_client, key_manager)

            # 무효화 이벤트 추가
            invalidation_manager.add_invalidation_event(
                event_type=event_type,
                keys=resolved_keys,
                strategy=strategy,
                metadata=metadata,
            )

            # 즉시 처리 (IMMEDIATE 전략인 경우)
            if strategy == CacheInvalidationStrategy.IMMEDIATE:
                await invalidation_manager._process_invalidation_event(
                    CacheInvalidationEvent(
                        event_type=event_type,
                        keys=resolved_keys,
                        strategy=strategy,
                        metadata=metadata,
                    )
                )

    except Exception as e:
        logger.error(f"캐시 무효화 실행 실패: {event_type.value}, 오류: {e}")


def _resolve_key_patterns(patterns: List[str], args: tuple, kwargs: dict) -> List[str]:
    """키 패턴 해석"""
    resolved_keys = []

    for pattern in patterns:
        if "{file_id}" in pattern:
            file_id = _extract_file_id(args, kwargs)
            if file_id:
                resolved_keys.append(pattern.replace("{file_id}", file_id))

        elif "{user_id}" in pattern:
            user_id = _extract_user_id(args, kwargs)
            if user_id:
                resolved_keys.append(pattern.replace("{user_id}", user_id))

        else:
            # 정적 패턴
            resolved_keys.append(pattern)

    return resolved_keys


def _extract_file_id(args, kwargs, param_name: str = "file_id") -> Optional[str]:
    """함수 인자에서 file_id 추출"""
    # kwargs에서 먼저 찾기
    if param_name in kwargs:
        return str(kwargs[param_name])

    # 함수 시그니처 분석
    try:
        import inspect

        sig = inspect.signature(
            args[0].__self__.__class__.__dict__.get(args[0].__name__)
        )
        param_names = list(sig.parameters.keys())

        for i, param in enumerate(param_names):
            if param == param_name and i < len(args):
                return str(args[i])
    except:
        pass

    return None


def _extract_user_id(args, kwargs, param_name: str = "user_id") -> Optional[str]:
    """함수 인자에서 user_id 추출"""
    # kwargs에서 먼저 찾기
    if param_name in kwargs:
        return str(kwargs[param_name])

    # 함수 시그니처 분석
    try:
        import inspect

        sig = inspect.signature(
            args[0].__self__.__class__.__dict__.get(args[0].__name__)
        )
        param_names = list(sig.parameters.keys())

        for i, param in enumerate(param_names):
            if param == param_name and i < len(args):
                return str(args[i])
    except:
        pass

    return None


def invalidate_file_cache(file_id_param: str = "file_id"):
    """파일 관련 캐시 무효화 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            file_id = _extract_file_id(args, kwargs, file_id_param)
            if file_id:
                await _invalidate_file_related_cache(file_id)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            file_id = _extract_file_id(args, kwargs, file_id_param)
            if file_id:
                asyncio.create_task(_invalidate_file_related_cache(file_id))
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


async def _invalidate_file_related_cache(file_id: str):
    """파일 관련 캐시 무효화"""
    try:
        redis_client = await get_async_redis_client()
        key_manager = get_cache_key_manager()

        # 파일 관련 캐시 키 패턴들
        patterns = [
            key_manager.file_meta_key(file_id),
            key_manager.file_content_key(file_id),
            key_manager.file_stats_key(file_id, "*"),
            key_manager.file_access_key(file_id),
        ]

        # 패턴 기반 삭제
        total_deleted = 0
        for pattern in patterns:
            deleted_count = await redis_client.delete_pattern(pattern)
            total_deleted += deleted_count

        # 메트릭 기록
        cache_metrics.record_cache_invalidation(
            cache_type="redis", invalidation_type="file_related"
        )

        logger.info(
            f"파일 관련 캐시 무효화 완료: {file_id}, 삭제된 키: {total_deleted}개"
        )

    except Exception as e:
        logger.error(f"파일 관련 캐시 무효화 실패: {file_id}, 오류: {e}")


def invalidate_user_cache(user_id_param: str = "user_id"):
    """사용자 관련 캐시 무효화 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            user_id = _extract_user_id(args, kwargs, user_id_param)
            if user_id:
                await _invalidate_user_related_cache(user_id)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            user_id = _extract_user_id(args, kwargs, user_id_param)
            if user_id:
                asyncio.create_task(_invalidate_user_related_cache(user_id))
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


async def _invalidate_user_related_cache(user_id: str):
    """사용자 관련 캐시 무효화"""
    try:
        redis_client = await get_async_redis_client()
        key_manager = get_cache_key_manager()

        # 사용자 관련 캐시 키 패턴들
        patterns = [
            key_manager.user_session_key(user_id),
            key_manager.user_activity_key(user_id, "*"),
            key_manager.user_preferences_key(user_id),
        ]

        # 패턴 기반 삭제
        total_deleted = 0
        for pattern in patterns:
            deleted_count = await redis_client.delete_pattern(pattern)
            total_deleted += deleted_count

        # 메트릭 기록
        cache_metrics.record_cache_invalidation(
            cache_type="redis", invalidation_type="user_related"
        )

        logger.info(
            f"사용자 관련 캐시 무효화 완료: {user_id}, 삭제된 키: {total_deleted}개"
        )

    except Exception as e:
        logger.error(f"사용자 관련 캐시 무효화 실패: {user_id}, 오류: {e}")


def invalidate_stats_cache():
    """통계 캐시 무효화 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await _invalidate_stats_cache()
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            asyncio.create_task(_invalidate_stats_cache())
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


async def _invalidate_stats_cache():
    """통계 캐시 무효화"""
    try:
        redis_client = await get_async_redis_client()
        key_manager = get_cache_key_manager()

        # 통계 관련 캐시 키 패턴들
        patterns = [
            key_manager.get_pattern("stats:daily", "*"),
            key_manager.get_pattern("stats:hourly", "*"),
            key_manager.get_pattern("stats:monthly", "*"),
        ]

        # 패턴 기반 삭제
        total_deleted = 0
        for pattern in patterns:
            deleted_count = await redis_client.delete_pattern(pattern)
            total_deleted += deleted_count

        # 메트릭 기록
        cache_metrics.record_cache_invalidation(
            cache_type="redis", invalidation_type="stats_related"
        )

        logger.info(f"통계 캐시 무효화 완료, 삭제된 키: {total_deleted}개")

    except Exception as e:
        logger.error(f"통계 캐시 무효화 실패: {e}")


def get_cache_invalidation_manager() -> CacheInvalidationManager:
    """캐시 무효화 매니저 인스턴스 반환"""
    redis_client = asyncio.run(get_async_redis_client())
    key_manager = get_cache_key_manager()
    return CacheInvalidationManager(redis_client, key_manager)


def get_ttl_manager() -> TTLManager:
    """TTL 매니저 인스턴스 반환"""
    redis_client = asyncio.run(get_async_redis_client())
    key_manager = get_cache_key_manager()
    return TTLManager(redis_client, key_manager)
