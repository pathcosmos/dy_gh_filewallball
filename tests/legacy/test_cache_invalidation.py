#!/usr/bin/env python3
"""
FileWallBall 캐시 무효화 및 TTL 관리 시스템 테스트
Task 3.3: TTL 관리 및 캐시 무효화 전략 구현 테스트
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.async_redis_client import AsyncRedisClient
from app.cache_invalidation import (
    CacheInvalidationEvent,
    CacheInvalidationManager,
    CacheInvalidationStrategy,
    InvalidationEvent,
    TTLManager,
    invalidate_cache,
    invalidate_file_cache,
    invalidate_stats_cache,
    invalidate_user_cache,
)
from app.cache_models import CacheKeyManager, CacheTTL


class TestCacheInvalidationEvent:
    """캐시 무효화 이벤트 테스트"""

    def test_event_creation(self):
        """이벤트 생성 테스트"""

        event = CacheInvalidationEvent(
            InvalidationEvent.FILE_CREATED,
            ["key1", "key2"],
            CacheInvalidationStrategy.IMMEDIATE,
            metadata={"file_id": "test123"},
        )

        assert event.event_type == InvalidationEvent.FILE_CREATED
        assert event.keys == ["key1", "key2"]
        assert event.strategy == CacheInvalidationStrategy.IMMEDIATE
        assert event.metadata["file_id"] == "test123"
        assert isinstance(event.timestamp, datetime)

    def test_event_to_dict(self):
        """이벤트 딕셔너리 변환 테스트"""

        event = CacheInvalidationEvent(
            InvalidationEvent.FILE_DELETED,
            ["key1"],
            CacheInvalidationStrategy.PATTERN_BASED,
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "file_deleted"
        assert event_dict["keys"] == ["key1"]
        assert event_dict["strategy"] == "pattern_based"
        assert "timestamp" in event_dict


class TestTTLManager:
    """TTL 관리자 테스트"""

    @pytest.fixture
    def mock_redis_client(self):
        """Redis 클라이언트 모킹"""
        client = AsyncMock(spec=AsyncRedisClient)
        client.set_with_ttl.return_value = True
        client.exists.return_value = True
        client.ttl.return_value = 1800
        return client

    @pytest.fixture
    def mock_key_manager(self):
        """키 관리자 모킹"""
        return MagicMock(spec=CacheKeyManager)

    @pytest.fixture
    def ttl_manager(self, mock_redis_client, mock_key_manager):
        """TTL 관리자 인스턴스"""
        return TTLManager(mock_redis_client, mock_key_manager)

    def test_get_ttl(self, ttl_manager):
        """TTL 값 반환 테스트"""
        assert ttl_manager.get_ttl(CacheTTL.FILE_META) == 3600
        assert ttl_manager.get_ttl(CacheTTL.USER_SESSION) == 86400
        assert ttl_manager.get_ttl(CacheTTL.STATS_DAILY) == 86400
        assert ttl_manager.get_ttl(CacheTTL.API_RATE_LIMIT) == 60

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, ttl_manager, mock_redis_client):
        """TTL과 함께 캐시 설정 테스트"""
        result = await ttl_manager.set_with_ttl(
            "test_key", {"data": "value"}, CacheTTL.FILE_META
        )

        assert result is True
        mock_redis_client.set_with_ttl.assert_called_once_with(
            "test_key", {"data": "value"}, 3600
        )

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, ttl_manager, mock_redis_client):
        """커스텀 TTL과 함께 캐시 설정 테스트"""
        result = await ttl_manager.set_with_ttl(
            "test_key", {"data": "value"}, CacheTTL.FILE_META, custom_ttl=7200
        )

        assert result is True
        mock_redis_client.set_with_ttl.assert_called_once_with(
            "test_key", {"data": "value"}, 7200
        )

    @pytest.mark.asyncio
    async def test_extend_ttl(self, ttl_manager, mock_redis_client):
        """TTL 연장 테스트"""
        mock_redis_client.get.return_value = {"data": "value"}

        result = await ttl_manager.extend_ttl("test_key", CacheTTL.FILE_META)

        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")
        mock_redis_client.get.assert_called_once_with("test_key")
        mock_redis_client.set_with_ttl.assert_called_once_with(
            "test_key", {"data": "value"}, 3600
        )

    @pytest.mark.asyncio
    async def test_extend_ttl_key_not_exists(self, ttl_manager, mock_redis_client):
        """존재하지 않는 키의 TTL 연장 테스트"""
        mock_redis_client.exists.return_value = False

        result = await ttl_manager.extend_ttl("nonexistent_key", CacheTTL.FILE_META)

        assert result is False
        mock_redis_client.exists.assert_called_once_with("nonexistent_key")

    @pytest.mark.asyncio
    async def test_get_remaining_ttl(self, ttl_manager, mock_redis_client):
        """남은 TTL 조회 테스트"""
        result = await ttl_manager.get_remaining_ttl("test_key")

        assert result == 1800
        mock_redis_client.ttl.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_refresh_ttl(self, ttl_manager, mock_redis_client):
        """TTL 새로고침 테스트"""
        mock_redis_client.get.return_value = {"data": "value"}

        result = await ttl_manager.refresh_ttl("test_key", CacheTTL.FILE_META)

        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")
        mock_redis_client.get.assert_called_once_with("test_key")
        mock_redis_client.set_with_ttl.assert_called_once_with(
            "test_key", {"data": "value"}, 3600
        )


class TestCacheInvalidationManager:
    """캐시 무효화 관리자 테스트"""

    @pytest.fixture
    def mock_redis_client(self):
        """Redis 클라이언트 모킹"""
        client = AsyncMock(spec=AsyncRedisClient)
        client.delete.return_value = True
        client.delete_pattern.return_value = 5
        client.scan_iter.return_value = ["key1", "key2", "key3", "key4", "key5"]
        return client

    @pytest.fixture
    def mock_key_manager(self):
        """키 관리자 모킹"""
        return MagicMock(spec=CacheKeyManager)

    @pytest.fixture
    def invalidation_manager(self, mock_redis_client, mock_key_manager):
        """무효화 관리자 인스턴스"""
        return CacheInvalidationManager(mock_redis_client, mock_key_manager)

    def test_add_invalidation_event(self, invalidation_manager):
        """무효화 이벤트 추가 테스트"""
        event = invalidation_manager.add_invalidation_event(
            InvalidationEvent.FILE_CREATED,
            ["key1", "key2"],
            CacheInvalidationStrategy.IMMEDIATE,
        )

        assert event.event_type == InvalidationEvent.FILE_CREATED
        assert event.keys == ["key1", "key2"]
        assert event.strategy == CacheInvalidationStrategy.IMMEDIATE
        assert len(invalidation_manager.invalidation_queue) == 1

    def test_add_invalidation_event_queue_limit(self, invalidation_manager):
        """큐 크기 제한 테스트"""
        # 큐를 가득 채움
        for i in range(1001):
            invalidation_manager.add_invalidation_event(
                InvalidationEvent.FILE_CREATED,
                [f"key{i}"],
                CacheInvalidationStrategy.IMMEDIATE,
            )

        # 최대 크기를 초과하면 오래된 이벤트가 제거됨
        assert len(invalidation_manager.invalidation_queue) == 1000

    @pytest.mark.asyncio
    async def test_invalidate_keys_immediate(
        self, invalidation_manager, mock_redis_client
    ):
        """즉시 키 삭제 테스트"""
        keys = ["key1", "key2", "key3"]
        result = await invalidation_manager._invalidate_keys_immediate(keys)

        assert result == 3
        assert mock_redis_client.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_invalidate_keys_by_pattern(
        self, invalidation_manager, mock_redis_client
    ):
        """패턴 기반 키 삭제 테스트"""
        patterns = ["file:meta:*", "user:session:*"]

        # scan_iter가 각 패턴에 대해 키 목록을 반환하도록 설정
        mock_redis_client.scan_iter.side_effect = [
            ["file:meta:1", "file:meta:2", "file:meta:3", "file:meta:4", "file:meta:5"],
            [
                "user:session:1",
                "user:session:2",
                "user:session:3",
                "user:session:4",
                "user:session:5",
            ],
        ]

        result = await invalidation_manager._invalidate_keys_by_pattern(patterns)

        assert result == 10  # 5개 키 * 2개 패턴
        assert mock_redis_client.delete_pattern.call_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_keys_selective(
        self, invalidation_manager, mock_redis_client
    ):
        """선택적 키 삭제 테스트"""
        keys = ["key1", "key2", "key3"]
        result = await invalidation_manager._invalidate_keys_selective(keys)

        assert result == 3
        assert mock_redis_client.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_process_invalidation_event(
        self, invalidation_manager, mock_redis_client
    ):
        """무효화 이벤트 처리 테스트"""
        event = CacheInvalidationEvent(
            InvalidationEvent.FILE_CREATED,
            ["key1", "key2"],
            CacheInvalidationStrategy.IMMEDIATE,
        )

        result = await invalidation_manager._process_invalidation_event(event)

        assert result is True
        assert mock_redis_client.delete.call_count == 2


class TestCacheInvalidationDecorators:
    """캐시 무효화 데코레이터 테스트"""

    @pytest.fixture
    def mock_redis_client(self):
        """Redis 클라이언트 모킹"""
        client = AsyncMock(spec=AsyncRedisClient)
        client.delete_pattern.return_value = 5
        return client

    @pytest.fixture
    def mock_key_manager(self):
        """키 관리자 모킹"""
        return MagicMock(spec=CacheKeyManager)

    @patch("app.cache_invalidation.get_async_redis_client")
    @patch("app.cache_invalidation.get_cache_key_manager")
    @pytest.mark.asyncio
    async def test_invalidate_cache_decorator_async(
        self, mock_get_key_manager, mock_get_redis, mock_redis_client, mock_key_manager
    ):
        """캐시 무효화 데코레이터 테스트 (비동기)"""
        mock_get_redis.return_value = mock_redis_client
        mock_get_key_manager.return_value = mock_key_manager

        @invalidate_cache(
            InvalidationEvent.FILE_CREATED,
            ["file:meta:{file_id}"],
            CacheInvalidationStrategy.IMMEDIATE,
        )
        async def test_function(file_id: str):
            return f"processed_{file_id}"

        result = await test_function("test123")

        assert result == "processed_test123"

    @patch("app.cache_invalidation.get_async_redis_client")
    @patch("app.cache_invalidation.get_cache_key_manager")
    @pytest.mark.asyncio
    async def test_invalidate_file_cache_decorator(
        self, mock_get_key_manager, mock_get_redis, mock_redis_client, mock_key_manager
    ):
        """파일 캐시 무효화 데코레이터 테스트"""
        mock_get_redis.return_value = mock_redis_client
        mock_get_key_manager.return_value = mock_key_manager

        @invalidate_file_cache()
        async def test_function(file_id: str):
            return f"processed_{file_id}"

        result = await test_function("test123")

        assert result == "processed_test123"
        # 파일 관련 캐시가 무효화되었는지 확인
        assert mock_redis_client.delete_pattern.call_count >= 1

    @patch("app.cache_invalidation.get_async_redis_client")
    @patch("app.cache_invalidation.get_cache_key_manager")
    @pytest.mark.asyncio
    async def test_invalidate_user_cache_decorator(
        self, mock_get_key_manager, mock_get_redis, mock_redis_client, mock_key_manager
    ):
        """사용자 캐시 무효화 데코레이터 테스트"""
        mock_get_redis.return_value = mock_redis_client
        mock_get_key_manager.return_value = mock_key_manager

        @invalidate_user_cache()
        async def test_function(user_id: str):
            return f"processed_{user_id}"

        result = await test_function("user123")

        assert result == "processed_user123"
        # 사용자 관련 캐시가 무효화되었는지 확인
        assert mock_redis_client.delete_pattern.call_count >= 1

    @patch("app.cache_invalidation.get_async_redis_client")
    @patch("app.cache_invalidation.get_cache_key_manager")
    @pytest.mark.asyncio
    async def test_invalidate_stats_cache_decorator(
        self, mock_get_key_manager, mock_get_redis, mock_redis_client, mock_key_manager
    ):
        """통계 캐시 무효화 데코레이터 테스트"""
        mock_get_redis.return_value = mock_redis_client
        mock_get_key_manager.return_value = mock_key_manager

        @invalidate_stats_cache()
        async def test_function():
            return "processed_stats"

        result = await test_function()

        assert result == "processed_stats"
        # 통계 관련 캐시가 무효화되었는지 확인
        assert mock_redis_client.delete_pattern.call_count >= 1


class TestCacheInvalidationIntegration:
    """캐시 무효화 통합 테스트"""

    @pytest.fixture
    def mock_redis_client(self):
        """Redis 클라이언트 모킹"""
        client = AsyncMock(spec=AsyncRedisClient)
        client.set_with_ttl.return_value = True
        client.delete_pattern.return_value = 3
        client.scan_iter.return_value = ["file:meta:1", "file:meta:2", "file:meta:3"]
        return client

    @pytest.fixture
    def mock_key_manager(self):
        """키 관리자 모킹"""
        return MagicMock(spec=CacheKeyManager)

    @pytest.mark.asyncio
    async def test_file_upload_invalidation_flow(
        self, mock_redis_client, mock_key_manager
    ):
        """파일 업로드 무효화 플로우 테스트"""
        # TTL 관리자 생성
        ttl_manager = TTLManager(mock_redis_client, mock_key_manager)

        # 파일 메타데이터 캐시 설정
        file_data = {
            "file_id": "file123",
            "filename": "test.txt",
            "size": 1024,
            "upload_time": datetime.utcnow().isoformat(),
        }

        success = await ttl_manager.set_with_ttl(
            "file:meta:file123", file_data, CacheTTL.FILE_META
        )

        assert success is True
        mock_redis_client.set_with_ttl.assert_called_once_with(
            "file:meta:file123", file_data, 3600
        )

        # 무효화 관리자 생성
        invalidation_manager = CacheInvalidationManager(
            mock_redis_client, mock_key_manager
        )

        # 파일 관련 캐시 무효화
        result = await invalidation_manager._invalidate_keys_by_pattern(["file:meta:*"])

        assert result == 3
        mock_redis_client.delete_pattern.assert_called_once_with("file:meta:*")

    @pytest.mark.asyncio
    async def test_user_session_invalidation_flow(
        self, mock_redis_client, mock_key_manager
    ):
        """사용자 세션 캐시 무효화 플로우 테스트"""
        # TTL 관리자 생성
        ttl_manager = TTLManager(mock_redis_client, mock_key_manager)

        # 사용자 세션 캐시 설정
        session_data = {
            "user_id": "user123",
            "session_id": "session456",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }

        success = await ttl_manager.set_with_ttl(
            "user:session:user123", session_data, CacheTTL.USER_SESSION
        )

        assert success is True
        mock_redis_client.set_with_ttl.assert_called_once_with(
            "user:session:user123", session_data, 86400
        )


class TestCacheInvalidationPerformance:
    """캐시 무효화 성능 테스트"""

    @pytest.fixture
    def mock_redis_client(self):
        """Redis 클라이언트 모킹"""
        client = AsyncMock(spec=AsyncRedisClient)
        client.delete.return_value = True
        client.delete_pattern.return_value = 100
        client.scan_iter.return_value = [f"key{i}" for i in range(100)]
        return client

    @pytest.fixture
    def mock_key_manager(self):
        """키 관리자 모킹"""
        return MagicMock(spec=CacheKeyManager)

    @pytest.mark.asyncio
    async def test_bulk_invalidation_performance(
        self, mock_redis_client, mock_key_manager
    ):
        """벌크 무효화 성능 테스트"""
        invalidation_manager = CacheInvalidationManager(
            mock_redis_client, mock_key_manager
        )

        # 대량의 키 무효화 테스트
        keys = [f"key{i}" for i in range(1000)]

        start_time = time.time()

        result = await invalidation_manager._invalidate_keys_immediate(keys)

        process_time = time.time() - start_time

        assert result == 1000
        assert process_time < 1.0  # 1초 이내에 처리되어야 함
        assert mock_redis_client.delete.call_count == 1000

    @pytest.mark.asyncio
    async def test_pattern_based_invalidation_performance(
        self, mock_redis_client, mock_key_manager
    ):
        """패턴 기반 무효화 성능 테스트"""
        invalidation_manager = CacheInvalidationManager(
            mock_redis_client, mock_key_manager
        )

        # 패턴 기반 무효화 테스트
        patterns = ["file:meta:*", "user:session:*", "stats:*"]

        # scan_iter가 각 패턴에 대해 키 목록을 반환하도록 설정
        mock_redis_client.scan_iter.side_effect = [
            [f"file:meta:{i}" for i in range(100)],
            [f"user:session:{i}" for i in range(100)],
            [f"stats:{i}" for i in range(100)],
        ]

        start_time = time.time()

        result = await invalidation_manager._invalidate_keys_by_pattern(patterns)

        process_time = time.time() - start_time

        assert result == 300  # 100개 키 * 3개 패턴
        assert process_time < 2.0  # 2초 이내에 처리되어야 함
        assert mock_redis_client.delete_pattern.call_count == 3


class TestCacheInvalidationErrorHandling:
    """캐시 무효화 오류 처리 테스트"""

    @pytest.fixture
    def mock_redis_client_error(self):
        """오류를 발생시키는 Redis 클라이언트 모킹"""
        client = AsyncMock(spec=AsyncRedisClient)
        client.delete.side_effect = Exception("Redis connection error")
        client.delete_pattern.side_effect = Exception("Redis connection error")
        client.scan_iter.side_effect = Exception("Redis connection error")
        return client

    @pytest.fixture
    def mock_key_manager(self):
        """키 관리자 모킹"""
        return MagicMock(spec=CacheKeyManager)

    @pytest.mark.asyncio
    async def test_invalidation_error_handling(
        self, mock_redis_client_error, mock_key_manager
    ):
        """무효화 오류 처리 테스트"""
        invalidation_manager = CacheInvalidationManager(
            mock_redis_client_error, mock_key_manager
        )

        # 오류가 발생해도 시스템이 중단되지 않아야 함
        try:
            result = await invalidation_manager._invalidate_keys_immediate(
                ["key1", "key2"]
            )
            # 오류가 발생했지만 예외가 전파되지 않아야 함
            assert result == 0  # 오류로 인해 삭제된 키가 없음
        except Exception as e:
            pytest.fail(f"무효화 오류가 예외로 전파됨: {e}")

    @pytest.mark.asyncio
    async def test_pattern_invalidation_error_handling(
        self, mock_redis_client_error, mock_key_manager
    ):
        """패턴 무효화 오류 처리 테스트"""
        invalidation_manager = CacheInvalidationManager(
            mock_redis_client_error, mock_key_manager
        )

        # 패턴 기반 무효화에서 오류가 발생해도 시스템이 중단되지 않아야 함
        try:
            result = await invalidation_manager._invalidate_keys_by_pattern(
                ["file:meta:*"]
            )
            # 오류가 발생했지만 예외가 전파되지 않아야 함
            assert result == 0  # 오류로 인해 삭제된 키가 없음
        except Exception as e:
            pytest.fail(f"패턴 무효화 오류가 예외로 전파됨: {e}")
