#!/usr/bin/env python3
"""
FileWallBall 캐시 서비스 레이어 테스트
Task 3.4: 캐시 서비스 레이어 구현 테스트
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.cache_service import CacheService, cache_result


class TestCacheServiceGetOrSet:
    """get_or_set 메서드 테스트"""

    @pytest.fixture
    def cache_service(self):
        return CacheService()

    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self, cache_service):
        """캐시 히트 시나리오 테스트"""
        with (
            patch.object(cache_service, "get") as mock_get,
            patch.object(cache_service, "set") as mock_set,
        ):

            mock_get.return_value = {"data": "cached_value"}

            async def data_fetcher():
                return {"data": "new_value"}

            result = await cache_service.get_or_set("test_key", data_fetcher, 3600)

            assert result == {"data": "cached_value"}
            mock_get.assert_called_once_with("test_key")
            # data_fetcher는 호출되지 않아야 함
            mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss(self, cache_service):
        """캐시 미스 시나리오 테스트"""
        with (
            patch.object(cache_service, "get") as mock_get,
            patch.object(cache_service, "set") as mock_set,
        ):

            mock_get.return_value = None
            mock_set.return_value = True

            async def data_fetcher():
                return {"data": "new_value"}

            result = await cache_service.get_or_set("test_key", data_fetcher, 3600)

            assert result == {"data": "new_value"}
            mock_get.assert_called_once_with("test_key")
            mock_set.assert_called_once_with("test_key", {"data": "new_value"}, 3600)

    @pytest.mark.asyncio
    async def test_get_or_set_with_args(self, cache_service):
        """인수가 있는 data_fetcher 테스트"""
        with (
            patch.object(cache_service, "get") as mock_get,
            patch.object(cache_service, "set") as mock_set,
        ):

            mock_get.return_value = None
            mock_set.return_value = True

            async def data_fetcher(user_id: str, include_meta: bool = False):
                return {"user_id": user_id, "meta": include_meta}

            result = await cache_service.get_or_set(
                "test_key", data_fetcher, 3600, "user123", include_meta=True
            )

            assert result == {"user_id": "user123", "meta": True}


class TestCacheServiceBatchOperations:
    """배치 작업 테스트"""

    @pytest.fixture
    def cache_service(self):
        return CacheService()

    @pytest.fixture
    def mock_pipeline(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_mget_success(self, cache_service, mock_pipeline):
        """mget 성공 테스트"""
        with patch.object(cache_service, "client") as mock_client:
            mock_client.pipeline.return_value = mock_pipeline
            mock_pipeline.execute.return_value = [
                '{"data": "value1"}',
                None,
                '{"data": "value3"}',
            ]

            keys = ["key1", "key2", "key3"]
            results = await cache_service.mget(keys)

            assert results == [{"data": "value1"}, None, {"data": "value3"}]
            assert mock_pipeline.get.call_count == 3

    @pytest.mark.asyncio
    async def test_mget_empty_keys(self, cache_service):
        """빈 키 리스트로 mget 테스트"""
        results = await cache_service.mget([])
        assert results == []

    @pytest.mark.asyncio
    async def test_mset_success(self, cache_service, mock_pipeline):
        """mset 성공 테스트"""
        with patch.object(cache_service, "client") as mock_client:
            mock_client.pipeline.return_value = mock_pipeline

            data = {"key1": {"data": "value1"}, "key2": {"data": "value2"}}

            result = await cache_service.mset(data, 3600)

            assert result is True
            assert mock_pipeline.setex.call_count == 2

    @pytest.mark.asyncio
    async def test_mset_empty_data(self, cache_service):
        """빈 데이터로 mset 테스트"""
        result = await cache_service.mset({})
        assert result is True


class TestCacheServiceTransaction:
    """트랜잭션 테스트"""

    @pytest.fixture
    def cache_service(self):
        return CacheService()

    @pytest.fixture
    def mock_pipeline(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_transaction_success(self, cache_service, mock_pipeline):
        """트랜잭션 성공 테스트"""
        with patch.object(cache_service, "client") as mock_client:
            mock_client.pipeline.return_value = mock_pipeline
            mock_pipeline.execute.return_value = ["result1", "result2"]

            def op1(pipeline):
                pipeline.set("key1", "value1")

            def op2(pipeline):
                pipeline.set("key2", "value2")

            operations = [op1, op2]
            results = await cache_service.transaction(operations)

            assert results == ["result1", "result2"]
            assert mock_pipeline.set.call_count == 2


class TestCacheResultDecorator:
    """@cache_result 데코레이터 테스트"""

    @patch("app.services.cache_service.CacheService")
    @pytest.mark.asyncio
    async def test_cache_result_hit(self, mock_cache_class):
        """캐시 히트 시나리오 테스트"""
        mock_cache_service = AsyncMock()
        mock_cache_class.return_value = mock_cache_service
        mock_cache_service.get.return_value = {"data": "cached_value"}

        @cache_result(ttl=3600)
        async def test_function(user_id: str):
            return {"data": "new_value"}

        result = await test_function("user123")

        assert result == {"data": "cached_value"}
        mock_cache_service.get.assert_called_once()
        # 원본 함수는 호출되지 않아야 함

    @patch("app.services.cache_service.CacheService")
    @pytest.mark.asyncio
    async def test_cache_result_miss(self, mock_cache_class):
        """캐시 미스 시나리오 테스트"""
        mock_cache_service = AsyncMock()
        mock_cache_class.return_value = mock_cache_service
        mock_cache_service.get.return_value = None
        mock_cache_service.set.return_value = True

        @cache_result(ttl=3600)
        async def test_function(user_id: str):
            return {"data": "new_value"}

        result = await test_function("user123")

        assert result == {"data": "new_value"}
        mock_cache_service.get.assert_called_once()
        mock_cache_service.set.assert_called_once()

    @patch("app.services.cache_service.CacheService")
    @pytest.mark.asyncio
    async def test_cache_result_with_key_prefix(self, mock_cache_class):
        """키 접두사가 있는 데코레이터 테스트"""
        mock_cache_service = AsyncMock()
        mock_cache_class.return_value = mock_cache_service
        mock_cache_service.get.return_value = None
        mock_cache_service.set.return_value = True

        @cache_result(ttl=3600, key_prefix="user")
        async def test_function(user_id: str):
            return {"data": "value"}

        await test_function("user123")

        # 키에 접두사가 포함되었는지 확인
        call_args = mock_cache_service.get.call_args[0][0]
        assert "user" in call_args

    @patch("app.services.cache_service.CacheService")
    @pytest.mark.asyncio
    async def test_cache_result_fallback_on_error(self, mock_cache_class):
        """에러 시 캐시 폴백 테스트"""
        mock_cache_service = AsyncMock()
        mock_cache_class.return_value = mock_cache_service
        mock_cache_service.get.side_effect = [
            None,  # 첫 번째 호출 (캐시 미스)
            {"data": "cached_value"},  # 에러 후 폴백
        ]
        mock_cache_service.set.side_effect = Exception("Redis error")

        @cache_result(ttl=3600, fallback_on_error=True)
        async def test_function(user_id: str):
            return {"data": "new_value"}

        result = await test_function("user123")

        assert result == {"data": "cached_value"}


class TestCacheServiceErrorHandling:
    """에러 핸들링 테스트"""

    @pytest.fixture
    def cache_service(self):
        return CacheService()

    @pytest.fixture
    def mock_pipeline(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_or_set_redis_error(self, cache_service):
        """Redis 에러 시 폴백 테스트"""
        with (
            patch.object(cache_service, "get") as mock_get,
            patch.object(cache_service, "set") as mock_set,
        ):

            mock_get.side_effect = [
                None,  # 첫 번째 호출
                {"data": "cached_value"},  # 에러 후 폴백
            ]
            mock_set.side_effect = Exception("Redis connection error")

            async def data_fetcher():
                return {"data": "new_value"}

            result = await cache_service.get_or_set("test_key", data_fetcher, 3600)

            assert result == {"data": "cached_value"}

    @pytest.mark.asyncio
    async def test_mget_redis_error(self, cache_service, mock_pipeline):
        """mget Redis 에러 테스트"""
        with patch.object(cache_service, "client") as mock_client:
            mock_client.pipeline.side_effect = Exception("Redis error")

            keys = ["key1", "key2"]
            results = await cache_service.mget(keys)

            assert results == [None, None]

    @pytest.mark.asyncio
    async def test_mset_redis_error(self, cache_service, mock_pipeline):
        """mset Redis 에러 테스트"""
        with patch.object(cache_service, "client") as mock_client:
            mock_client.pipeline.side_effect = Exception("Redis error")

            data = {"key1": "value1"}
            result = await cache_service.mset(data, 3600)

            assert result is False


class TestCacheServiceIntegration:
    """통합 테스트"""

    @pytest.fixture
    def cache_service(self):
        return CacheService()

    @pytest.fixture
    def mock_pipeline(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_file_metadata_caching_flow(self, cache_service):
        """파일 메타데이터 캐싱 플로우 테스트"""
        with (
            patch.object(cache_service, "get") as mock_get,
            patch.object(cache_service, "set") as mock_set,
        ):

            mock_get.side_effect = [
                None,  # 첫 번째 호출 (캐시 미스)
                {
                    "file_id": "file123",
                    "name": "test_file.txt",
                },  # 두 번째 호출 (캐시 히트)
            ]
            mock_set.return_value = True

            # 파일 메타데이터 가져오기 시뮬레이션
            async def fetch_file_metadata(file_id: str):
                return {
                    "file_id": file_id,
                    "name": "test_file.txt",
                    "size": 1024,
                    "created_at": "2024-01-01T00:00:00Z",
                }

            # 첫 번째 호출 (캐시 미스)
            result1 = await cache_service.get_or_set(
                "file:meta:file123", fetch_file_metadata, 1800, "file123"
            )

            # 두 번째 호출 (캐시 히트)
            result2 = await cache_service.get_or_set(
                "file:meta:file123", fetch_file_metadata, 1800, "file123"
            )

            assert result1["file_id"] == "file123"
            assert result2["file_id"] == "file123"
            assert mock_set.call_count == 1  # 한 번만 저장됨

    @pytest.mark.asyncio
    async def test_batch_user_sessions(self, cache_service, mock_pipeline):
        """배치 사용자 세션 처리 테스트"""
        with patch.object(cache_service, "client") as mock_client:
            mock_client.pipeline.return_value = mock_pipeline
            mock_pipeline.execute.return_value = [
                '{"user_id": "user1", "session": "active"}',
                '{"user_id": "user2", "session": "active"}',
                None,  # user3는 세션이 없음
            ]

            user_keys = [
                "user:session:user1",
                "user:session:user2",
                "user:session:user3",
            ]
            sessions = await cache_service.mget(user_keys)

            assert len(sessions) == 3
            assert sessions[0]["user_id"] == "user1"
            assert sessions[1]["user_id"] == "user2"
            assert sessions[2] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
