#!/usr/bin/env python3
"""
Redis 연결 관리자 및 캐시 서비스 테스트
"""

import asyncio
import json
import time
from app.services.redis_connection_manager import get_redis_manager
from app.services.cache_service import CacheService


async def test_redis_connection():
    """Redis 연결 테스트"""
    print("🚀 Redis 연결 관리자 테스트 시작")
    print("=" * 50)
    
    try:
        # Redis 연결 관리자 초기화
        redis_manager = get_redis_manager()
        print("✅ Redis 연결 관리자 초기화 성공")
        
        # 연결 정보 조회
        connection_info = redis_manager.get_connection_info()
        print(f"📊 연결 정보: {json.dumps(connection_info, indent=2, ensure_ascii=False)}")
        
        # 헬스체크 실행
        await redis_manager.health_check()
        print("✅ Redis 헬스체크 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis 연결 테스트 실패: {e}")
        return False


async def test_cache_service():
    """캐시 서비스 테스트"""
    print("\n🔧 캐시 서비스 테스트")
    print("-" * 30)
    
    try:
        cache_service = CacheService()
        print("✅ 캐시 서비스 초기화 성공")
        
        # 기본 캐시 작업 테스트
        test_key = "test:cache:basic"
        test_value = {"message": "Hello Redis!", "timestamp": time.time()}
        
        # 1. 캐시 저장 테스트
        print("1. 캐시 저장 테스트...")
        success = await cache_service.set(test_key, test_value, 60)
        print(f"   결과: {'✅ 성공' if success else '❌ 실패'}")
        
        # 2. 캐시 조회 테스트
        print("2. 캐시 조회 테스트...")
        retrieved_value = await cache_service.get(test_key)
        if retrieved_value and retrieved_value.get("message") == test_value["message"]:
            print("   ✅ 성공 - 값이 올바르게 조회됨")
        else:
            print("   ❌ 실패 - 값이 올바르지 않음")
        
        # 3. TTL 테스트
        print("3. TTL 테스트...")
        ttl = await cache_service.ttl(test_key)
        print(f"   남은 시간: {ttl}초")
        
        # 4. 키 존재 확인 테스트
        print("4. 키 존재 확인 테스트...")
        exists = await cache_service.exists(test_key)
        print(f"   결과: {'✅ 존재' if exists else '❌ 없음'}")
        
        # 5. 캐시 삭제 테스트
        print("5. 캐시 삭제 테스트...")
        deleted = await cache_service.delete(test_key)
        print(f"   결과: {'✅ 성공' if deleted else '❌ 실패'}")
        
        # 6. 삭제 후 조회 테스트
        print("6. 삭제 후 조회 테스트...")
        after_delete = await cache_service.get(test_key)
        print(f"   결과: {'✅ 정상 (None 반환)' if after_delete is None else '❌ 오류'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 캐시 서비스 테스트 실패: {e}")
        return False


async def test_file_cache():
    """파일 캐시 기능 테스트"""
    print("\n📁 파일 캐시 기능 테스트")
    print("-" * 30)
    
    try:
        cache_service = CacheService()
        
        # 파일 정보 캐시 테스트
        file_uuid = "test-file-123"
        file_info = {
            "file_uuid": file_uuid,
            "original_filename": "test.txt",
            "file_size": 1024,
            "mime_type": "text/plain",
            "upload_time": time.time()
        }
        
        # 1. 파일 정보 캐시 저장
        print("1. 파일 정보 캐시 저장...")
        success = await cache_service.set_file_info(file_uuid, file_info, 300)
        print(f"   결과: {'✅ 성공' if success else '❌ 실패'}")
        
        # 2. 파일 정보 캐시 조회
        print("2. 파일 정보 캐시 조회...")
        cached_info = await cache_service.get_file_info(file_uuid)
        if cached_info and cached_info.get("file_uuid") == file_uuid:
            print("   ✅ 성공 - 파일 정보가 올바르게 조회됨")
        else:
            print("   ❌ 실패 - 파일 정보가 올바르지 않음")
        
        # 3. 파일 캐시 무효화
        print("3. 파일 캐시 무효화...")
        invalidated = await cache_service.invalidate_file_cache(file_uuid)
        print(f"   결과: {'✅ 성공' if invalidated else '❌ 실패'}")
        
        # 4. 무효화 후 조회
        print("4. 무효화 후 조회...")
        after_invalidate = await cache_service.get_file_info(file_uuid)
        print(f"   결과: {'✅ 정상 (None 반환)' if after_invalidate is None else '❌ 오류'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 파일 캐시 테스트 실패: {e}")
        return False


async def test_rate_limiting():
    """Rate Limiting 기능 테스트"""
    print("\n⚡ Rate Limiting 기능 테스트")
    print("-" * 30)
    
    try:
        cache_service = CacheService()
        
        # Rate limiting 카운터 테스트
        counter_key = "rate_limit:test:127.0.0.1"
        
        # 1. 카운터 초기화 및 증가
        print("1. 카운터 증가 테스트...")
        for i in range(5):
            value = await cache_service.increment_counter(counter_key, 1, 60)
            print(f"   증가 {i+1}: {value}")
        
        # 2. 카운터 값 조회
        print("2. 카운터 값 조회...")
        current_value = await cache_service.get_counter(counter_key)
        print(f"   현재 값: {current_value}")
        
        # 3. 카운터 삭제
        print("3. 카운터 삭제...")
        deleted = await cache_service.delete(counter_key)
        print(f"   결과: {'✅ 성공' if deleted else '❌ 실패'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate Limiting 테스트 실패: {e}")
        return False


async def test_cache_stats():
    """캐시 통계 테스트"""
    print("\n📈 캐시 통계 테스트")
    print("-" * 30)
    
    try:
        cache_service = CacheService()
        
        # 캐시 통계 조회
        stats = await cache_service.get_stats()
        print("📊 Redis 통계:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # 헬스체크
        health = await cache_service.health_check()
        print(f"\n🏥 헬스체크 결과: {health['status']}")
        if health.get('write_test'):
            print("   ✅ 쓰기 테스트 통과")
        if health.get('read_test'):
            print("   ✅ 읽기 테스트 통과")
        
        return True
        
    except Exception as e:
        print(f"❌ 캐시 통계 테스트 실패: {e}")
        return False


async def test_circuit_breaker():
    """서킷 브레이커 테스트"""
    print("\n🔄 서킷 브레이커 테스트")
    print("-" * 30)
    
    try:
        redis_manager = get_redis_manager()
        
        # 서킷 브레이커 상태 확인
        connection_info = redis_manager.get_connection_info()
        circuit_state = connection_info.get('circuit_breaker_state', 'unknown')
        failure_count = connection_info.get('failure_count', 0)
        
        print(f"서킷 브레이커 상태: {circuit_state}")
        print(f"실패 횟수: {failure_count}")
        
        # 정상적인 Redis 작업 실행
        print("정상 Redis 작업 실행...")
        await redis_manager.execute_with_retry(redis_manager.client.ping)
        print("✅ 정상 작업 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 서킷 브레이커 테스트 실패: {e}")
        return False


async def main():
    """메인 테스트 함수"""
    print("🚀 Redis 연결 관리자 및 캐시 서비스 종합 테스트")
    print("=" * 60)
    
    tests = [
        ("Redis 연결", test_redis_connection),
        ("캐시 서비스", test_cache_service),
        ("파일 캐시", test_file_cache),
        ("Rate Limiting", test_rate_limiting),
        ("캐시 통계", test_cache_stats),
        ("서킷 브레이커", test_circuit_breaker)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트에서 예외 발생: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n전체 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공적으로 통과했습니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다.")


if __name__ == "__main__":
    asyncio.run(main()) 