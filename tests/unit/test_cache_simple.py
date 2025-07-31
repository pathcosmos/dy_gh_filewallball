#!/usr/bin/env python3
"""
캐시 무효화 시스템 간단 테스트
Task 3.3 완료 확인용
"""

import asyncio
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.async_redis_client import AsyncRedisClient
from app.cache_invalidation import (
    CacheInvalidationManager,
    CacheInvalidationStrategy,
    InvalidationEvent,
    TTLManager,
    get_cache_invalidation_manager,
    get_ttl_manager,
)
from app.cache_models import CacheTTL, get_cache_key_manager


class MockRedisClient:
    """Redis 클라이언트 모의 객체"""

    def __init__(self):
        self.data = {}
        self.ttl_data = {}
        self.delete_calls = []
        self.set_calls = []
        self.expire_calls = []

    async def set_with_ttl(self, key: str, value, ttl: int) -> bool:
        self.data[key] = value
        self.ttl_data[key] = ttl
        self.set_calls.append((key, value, ttl))
        return True

    async def delete(self, key: str) -> int:
        if key in self.data:
            del self.data[key]
            if key in self.ttl_data:
                del self.ttl_data[key]
        self.delete_calls.append(key)
        return 1

    async def exists(self, key: str) -> bool:
        return key in self.data

    async def expire(self, key: str, ttl: int) -> bool:
        if key in self.data:
            self.ttl_data[key] = ttl
            self.expire_calls.append((key, ttl))
            return True
        return False

    async def ttl(self, key: str) -> int:
        return self.ttl_data.get(key, -1)

    async def scan_iter(self, match: str = None, count: int = None):
        if match:
            # 간단한 패턴 매칭
            pattern = match.replace("*", "")
            keys = [key for key in self.data.keys() if pattern in key]
        else:
            keys = list(self.data.keys())

        # async iterator로 반환
        for key in keys:
            yield key

    async def delete_pattern(self, pattern: str) -> int:
        """패턴에 맞는 키들을 삭제"""
        deleted_count = 0
        if pattern:
            # 간단한 패턴 매칭
            match_pattern = pattern.replace("*", "")
            keys_to_delete = [key for key in self.data.keys() if match_pattern in key]
            for key in keys_to_delete:
                await self.delete(key)
                deleted_count += 1
        return deleted_count


async def test_ttl_manager():
    """TTL 관리자 테스트"""
    print("=== TTL 관리자 테스트 ===")

    redis_client = MockRedisClient()
    key_manager = get_cache_key_manager()
    ttl_manager = TTLManager(redis_client, key_manager)

    # TTL 값 확인
    assert ttl_manager.get_ttl(CacheTTL.FILE_META) == 3600
    assert ttl_manager.get_ttl(CacheTTL.USER_SESSION) == 86400
    print("✓ TTL 값 확인 완료")

    # 캐시 설정 테스트
    result = await ttl_manager.set_with_ttl(
        "test:key", {"data": "test"}, CacheTTL.FILE_META
    )
    assert result is True
    assert "test:key" in redis_client.data
    print("✓ 캐시 설정 완료")

    # TTL 연장 테스트
    result = await ttl_manager.extend_ttl("test:key", CacheTTL.FILE_META)
    assert result is True
    print("✓ TTL 연장 완료")

    print("TTL 관리자 테스트 통과!\n")


async def test_cache_invalidation_manager():
    """캐시 무효화 관리자 테스트"""
    print("=== 캐시 무효화 관리자 테스트 ===")

    redis_client = MockRedisClient()
    key_manager = get_cache_key_manager()
    invalidation_manager = CacheInvalidationManager(redis_client, key_manager)

    # 무효화 이벤트 추가
    invalidation_manager.add_invalidation_event(
        InvalidationEvent.FILE_CREATED,
        ["file:meta:123"],
        CacheInvalidationStrategy.IMMEDIATE,
    )
    assert len(invalidation_manager.invalidation_queue) == 1
    print("✓ 무효화 이벤트 추가 완료")

    # 즉시 키 무효화 테스트
    result = await invalidation_manager._invalidate_keys_immediate(["key1", "key2"])
    assert result == 2
    assert len(redis_client.delete_calls) == 2
    print("✓ 즉시 키 무효화 완료")

    # 패턴 기반 무효화 테스트
    redis_client.data = {"file:meta:123": "data1", "file:meta:456": "data2"}
    result = await invalidation_manager._invalidate_keys_by_pattern(["file:meta:*"])
    assert result == 2
    print("✓ 패턴 기반 무효화 완료")

    print("캐시 무효화 관리자 테스트 통과!\n")


async def test_cache_invalidation_decorator():
    """캐시 무효화 데코레이터 테스트"""
    print("=== 캐시 무효화 데코레이터 테스트 ===")

    from app.cache_invalidation import invalidate_cache

    redis_client = MockRedisClient()

    @invalidate_cache(
        InvalidationEvent.FILE_CREATED,
        ["file:meta:{file_id}"],
        CacheInvalidationStrategy.IMMEDIATE,
    )
    async def create_file(file_id: str):
        return {"file_id": file_id, "status": "created"}

    # 데코레이터가 적용된 함수 실행
    result = await create_file("123")
    assert result == {"file_id": "123", "status": "created"}
    print("✓ 데코레이터 함수 실행 완료")

    print("캐시 무효화 데코레이터 테스트 통과!\n")


async def test_integration():
    """통합 테스트"""
    print("=== 통합 테스트 ===")

    redis_client = MockRedisClient()
    key_manager = get_cache_key_manager()
    ttl_manager = TTLManager(redis_client, key_manager)
    invalidation_manager = CacheInvalidationManager(redis_client, key_manager)

    # 파일 메타데이터 캐시 설정
    file_id = "123"
    meta_key = f"file:meta:{file_id}"
    await ttl_manager.set_with_ttl(meta_key, {"test": "data"}, CacheTTL.FILE_META)
    assert meta_key in redis_client.data
    print("✓ 파일 메타데이터 캐시 설정 완료")

    # 파일 업데이트 시 캐시 무효화
    invalidation_manager.add_invalidation_event(
        InvalidationEvent.FILE_UPDATED, [meta_key], CacheInvalidationStrategy.IMMEDIATE
    )
    print("✓ 무효화 이벤트 추가 완료")

    # 무효화 이벤트 처리
    await invalidation_manager._process_invalidation_queue()
    assert meta_key not in redis_client.data
    print("✓ 캐시 무효화 완료")

    print("통합 테스트 통과!\n")


async def test_factory_functions():
    """팩토리 함수 테스트"""
    print("=== 팩토리 함수 테스트 ===")

    # 싱글톤 동작 확인
    manager1 = get_cache_invalidation_manager()
    manager2 = get_cache_invalidation_manager()
    assert manager1 is manager2
    print("✓ 캐시 무효화 관리자 싱글톤 확인")

    ttl_manager1 = get_ttl_manager()
    ttl_manager2 = get_ttl_manager()
    assert ttl_manager1 is ttl_manager2
    print("✓ TTL 관리자 싱글톤 확인")

    print("팩토리 함수 테스트 통과!\n")


async def main():
    """메인 테스트 함수"""
    print("FileWallBall 캐시 무효화 시스템 테스트 시작\n")

    try:
        await test_ttl_manager()
        await test_cache_invalidation_manager()
        await test_cache_invalidation_decorator()
        await test_integration()
        await test_factory_functions()

        print("🎉 모든 테스트가 성공적으로 통과했습니다!")
        print("Task 3.3: TTL 관리 및 캐시 무효화 전략 구현이 완료되었습니다.")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
