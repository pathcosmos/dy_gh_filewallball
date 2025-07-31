#!/usr/bin/env python3
"""
비동기 Redis 클라이언트 테스트
Task 3.1: Redis 비동기 클라이언트 구현 테스트
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.async_redis_client import (
    AsyncRedisClient,
    CacheKeys,
    CacheTTL,
    async_retry_on_failure,
    close_async_redis_client,
    get_async_redis_client,
    init_async_redis_client,
)


class TestAsyncRedisClient:
    """비동기 Redis 클라이언트 테스트 클래스"""

    @pytest.fixture
    async def redis_client(self):
        """테스트용 Redis 클라이언트 픽스처"""
        client = AsyncRedisClient(
            host="localhost",
            port=6379,
            password="test_password",
            db=0,
            max_connections=10,
        )
        yield client
        await client.close()

    @pytest.fixture
    async def mock_redis_client(self):
        """모킹된 Redis 클라이언트 픽스처"""
        with patch("app.async_redis_client.redis") as mock_redis:
            # Redis 클라이언트 모킹
            mock_client = AsyncMock()
            mock_redis.Redis.return_value = mock_client
            mock_redis.ConnectionPool.return_value = AsyncMock()

            # 연결 테스트 성공
            mock_client.ping.return_value = True

            client = AsyncRedisClient(
                host="localhost",
                port=6379,
                password="test_password",
                db=0,
            )
            await client.connect()
            yield client, mock_client
            await client.close()

    @pytest.mark.asyncio
    async def test_redis_client_initialization(self, redis_client):
        """Redis 클라이언트 초기화 테스트"""
        assert redis_client.host == "localhost"
        assert redis_client.port == 6379
        assert redis_client.password == "test_password"
        assert redis_client.db == 0
        assert redis_client.max_connections == 10
        assert redis_client.retry_on_timeout is True

    @pytest.mark.asyncio
    async def test_redis_client_connection(self, mock_redis_client):
        """Redis 연결 테스트"""
        client, mock_client = mock_redis_client

        # 연결 상태 확인
        is_connected = await client.is_connected()
        assert is_connected is True
        mock_client.ping.assert_called()

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, mock_redis_client):
        """TTL과 함께 키-값 설정 테스트"""
        client, mock_client = mock_redis_client

        # 문자열 값 설정
        mock_client.setex.return_value = True
        result = await client.set_with_ttl("test_key", "test_value", 3600)
        assert result is True
        mock_client.setex.assert_called_with("test_key", 3600, "test_value")

        # 딕셔너리 값 설정
        test_data = {"name": "test", "value": 123}
        result = await client.set_with_ttl("test_dict", test_data, 1800)
        assert result is True
        expected_json = json.dumps(test_data, ensure_ascii=False)
        mock_client.setex.assert_called_with("test_dict", 1800, expected_json)

    @pytest.mark.asyncio
    async def test_get_string_value(self, mock_redis_client):
        """문자열 값 조회 테스트"""
        client, mock_client = mock_redis_client

        # 문자열 값 반환
        mock_client.get.return_value = "test_value"
        result = await client.get("test_key")
        assert result == "test_value"
        mock_client.get.assert_called_with("test_key")

    @pytest.mark.asyncio
    async def test_get_json_value(self, mock_redis_client):
        """JSON 값 조회 테스트"""
        client, mock_client = mock_redis_client

        # JSON 값 반환
        test_data = {"name": "test", "value": 123}
        mock_client.get.return_value = json.dumps(test_data)
        result = await client.get("test_key")
        assert result == test_data

    @pytest.mark.asyncio
    async def test_get_none_value(self, mock_redis_client):
        """None 값 조회 테스트"""
        client, mock_client = mock_redis_client

        # None 값 반환
        mock_client.get.return_value = None
        result = await client.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_key(self, mock_redis_client):
        """키 삭제 테스트"""
        client, mock_client = mock_redis_client

        # 삭제 성공
        mock_client.delete.return_value = 1
        result = await client.delete("test_key")
        assert result is True
        mock_client.delete.assert_called_with("test_key")

        # 삭제 실패 (키가 없는 경우)
        mock_client.delete.return_value = 0
        result = await client.delete("nonexistent_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_key(self, mock_redis_client):
        """키 존재 여부 확인 테스트"""
        client, mock_client = mock_redis_client

        # 키 존재
        mock_client.exists.return_value = 1
        result = await client.exists("test_key")
        assert result is True

        # 키 없음
        mock_client.exists.return_value = 0
        result = await client.exists("nonexistent_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_ttl_key(self, mock_redis_client):
        """TTL 조회 테스트"""
        client, mock_client = mock_redis_client

        # TTL 값 반환
        mock_client.ttl.return_value = 1800
        result = await client.ttl("test_key")
        assert result == 1800

    @pytest.mark.asyncio
    async def test_mget_multiple_keys(self, mock_redis_client):
        """다중 키 조회 테스트"""
        client, mock_client = mock_redis_client

        # 여러 값 반환
        values = ["value1", json.dumps({"name": "test"}), None, "value4"]
        mock_client.mget.return_value = values

        result = await client.mget(["key1", "key2", "key3", "key4"])
        assert result == ["value1", {"name": "test"}, None, "value4"]
        mock_client.mget.assert_called_with(["key1", "key2", "key3", "key4"])

    @pytest.mark.asyncio
    async def test_mset_multiple_keys(self, mock_redis_client):
        """다중 키 설정 테스트"""
        client, mock_client = mock_redis_client

        # 파이프라인 모킹
        mock_pipeline = AsyncMock()
        mock_client.pipeline.return_value.__aenter__.return_value = mock_pipeline
        mock_client.pipeline.return_value.__aexit__.return_value = None

        data = {"key1": "value1", "key2": {"name": "test"}, "key3": 123}

        result = await client.mset(data, ttl=3600)
        assert result is True

        # 파이프라인 호출 확인
        assert mock_pipeline.setex.call_count == 3

    @pytest.mark.asyncio
    async def test_scan_iter_keys(self, mock_redis_client):
        """키 스캔 테스트"""
        client, mock_client = mock_redis_client

        # 스캔 결과 모킹
        keys = ["key1", "key2", "key3"]
        mock_client.scan_iter.return_value = keys

        result = await client.scan_iter(match="test:*", count=100)
        assert result == keys

    @pytest.mark.asyncio
    async def test_delete_pattern(self, mock_redis_client):
        """패턴 삭제 테스트"""
        client, mock_client = mock_redis_client

        # 스캔 결과 모킹
        keys = ["test:key1", "test:key2", "test:key3"]
        mock_client.scan_iter.return_value = keys
        mock_client.delete.return_value = 3

        result = await client.delete_pattern("test:*")
        assert result == 3
        mock_client.delete.assert_called_with("test:key1", "test:key2", "test:key3")

    @pytest.mark.asyncio
    async def test_get_info(self, mock_redis_client):
        """Redis 정보 조회 테스트"""
        client, mock_client = mock_redis_client

        # Redis INFO 결과 모킹
        info_data = {
            "redis_version": "6.2.0",
            "used_memory_human": "1.2M",
            "connected_clients": "5",
            "total_commands_processed": "1000",
            "keyspace_hits": "800",
            "keyspace_misses": "200",
            "uptime_in_seconds": "3600",
        }
        mock_client.info.return_value = info_data

        result = await client.get_info()
        assert result["version"] == "6.2.0"
        assert result["used_memory"] == "1.2M"
        assert result["connected_clients"] == "5"

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_redis_client):
        """캐시 통계 조회 테스트"""
        client, mock_client = mock_redis_client

        # Redis INFO 결과 모킹
        info_data = {"keyspace_hits": "800", "keyspace_misses": "200"}
        mock_client.info.return_value = info_data

        result = await client.get_stats()
        assert result["hits"] == "800"
        assert result["misses"] == "200"
        assert result["hit_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_redis_client):
        """연결 오류 처리 테스트"""
        client, mock_client = mock_redis_client

        # 연결 오류 시뮬레이션
        mock_client.get.side_effect = Exception("Connection error")

        result = await client.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cluster_mode_initialization(self):
        """클러스터 모드 초기화 테스트"""
        with patch("app.async_redis_client.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.RedisCluster.return_value = mock_client
            mock_client.ping.return_value = True

            client = AsyncRedisClient(host="localhost", port=6379, cluster_mode=True)
            await client.connect()

            assert client.cluster_mode is True
            mock_redis.RedisCluster.assert_called()
            await client.close()

    @pytest.mark.asyncio
    async def test_redis_url_initialization(self):
        """Redis URL 초기화 테스트"""
        with patch("app.async_redis_client.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.Redis.from_url.return_value = mock_client
            mock_client.ping.return_value = True

            client = AsyncRedisClient(redis_url="redis://localhost:6379/0")
            await client.connect()

            assert client.redis_url == "redis://localhost:6379/0"
            mock_redis.Redis.from_url.assert_called()
            await client.close()


class TestAsyncRetryDecorator:
    """비동기 재시도 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_retry_on_failure_success(self):
        """재시도 성공 테스트"""
        call_count = 0

        @async_retry_on_failure(max_retries=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_failure_max_retries(self):
        """최대 재시도 횟수 초과 테스트"""
        call_count = 0

        @async_retry_on_failure(max_retries=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent error")

        with pytest.raises(Exception, match="Persistent error"):
            await test_function()

        assert call_count == 3


class TestCacheConstants:
    """캐시 상수 테스트"""

    def test_cache_keys(self):
        """캐시 키 상수 테스트"""
        assert CacheKeys.FILE_META == "file:meta:{file_uuid}"
        assert CacheKeys.SESSION == "session:user:{user_id}"
        assert CacheKeys.TEMP_UPLOAD_PROGRESS == "temp:upload:progress:{upload_id}"
        assert CacheKeys.TEMP_DOWNLOAD_TOKEN == "temp:download:token:{token}"
        assert CacheKeys.SYSTEM_SETTINGS == "system:settings:{key}"
        assert CacheKeys.API_RATE_LIMIT == "rate_limit:{ip}:{endpoint}"

    def test_cache_ttl(self):
        """캐시 TTL 상수 테스트"""
        assert CacheTTL.FILE_META == 3600
        assert CacheTTL.SESSION == 86400
        assert CacheTTL.TEMP_DATA == 600
        assert CacheTTL.SYSTEM_SETTINGS == 3600
        assert CacheTTL.RATE_LIMIT == 60


class TestGlobalClient:
    """전역 클라이언트 테스트"""

    @pytest.mark.asyncio
    async def test_get_async_redis_client(self):
        """전역 클라이언트 반환 테스트"""
        with patch("app.async_redis_client.AsyncRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True

            client = await get_async_redis_client()
            assert client == mock_client
            mock_client.connect.assert_called()

    @pytest.mark.asyncio
    async def test_init_async_redis_client(self):
        """전역 클라이언트 초기화 테스트"""
        with patch("app.async_redis_client.AsyncRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True

            client = await init_async_redis_client(host="test")
            assert client == mock_client
            mock_client_class.assert_called_with(host="test")
            mock_client.connect.assert_called()

    @pytest.mark.asyncio
    async def test_close_async_redis_client(self):
        """전역 클라이언트 종료 테스트"""
        with patch("app.async_redis_client._async_redis_client") as mock_global_client:
            mock_client = AsyncMock()
            mock_global_client.__class__ = AsyncRedisClient
            mock_global_client.close = AsyncMock()

            await close_async_redis_client()
            mock_client.close.assert_called()


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v"])
