#!/usr/bin/env python3
"""
Dependency injection system test script.
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.dependencies.database import get_db
from app.dependencies.redis import get_redis_client, get_redis_sync
from app.dependencies.settings import get_app_settings
from app.config import Settings


def test_settings_dependency():
    """설정 의존성 테스트"""
    print("=== Testing Settings Dependency ===")
    
    try:
        settings = get_app_settings()
        
        print(f"App Name: {settings.app_name}")
        print(f"App Version: {settings.app_version}")
        print(f"Debug Mode: {settings.debug}")
        print(f"Database URL: {settings.database_url}")
        print(f"Redis URL: {settings.redis_url}")
        
        print("✅ Settings dependency test passed")
        return True
        
    except Exception as e:
        print(f"❌ Settings dependency test failed: {e}")
        return False


def test_database_dependency():
    """데이터베이스 의존성 테스트"""
    print("\n=== Testing Database Dependency ===")
    
    try:
        # 데이터베이스 세션 생성
        db_gen = get_db()
        db = next(db_gen)
        
        # 연결 테스트
        result = db.execute("SELECT 1 as test")
        row = result.fetchone()
        
        if row and row.test == 1:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
        
        # 세션 정리
        db.close()
        
        print("✅ Database dependency test passed")
        return True
        
    except Exception as e:
        print(f"❌ Database dependency test failed: {e}")
        return False


async def test_redis_dependency():
    """Redis 의존성 테스트"""
    print("\n=== Testing Redis Dependency ===")
    
    try:
        # 비동기 Redis 클라이언트 테스트
        redis_gen = get_redis_client()
        redis_client = await anext(redis_gen)
        
        # 연결 테스트
        await redis_client.ping()
        print("✅ Redis async connection successful")
        
        # 데이터 쓰기/읽기 테스트
        test_key = "test_dependency"
        test_value = "test_value"
        
        await redis_client.set(test_key, test_value)
        result = await redis_client.get(test_key)
        
        if result == test_value:
            print("✅ Redis read/write test successful")
        else:
            print("❌ Redis read/write test failed")
            return False
        
        # 정리
        await redis_client.delete(test_key)
        
        print("✅ Redis dependency test passed")
        return True
        
    except Exception as e:
        print(f"❌ Redis dependency test failed: {e}")
        return False


def test_redis_sync_dependency():
    """동기 Redis 의존성 테스트"""
    print("\n=== Testing Redis Sync Dependency ===")
    
    try:
        # 동기 Redis 클라이언트 테스트
        redis_client = get_redis_sync()
        
        # 연결 테스트
        redis_client.ping()
        print("✅ Redis sync connection successful")
        
        # 데이터 쓰기/읽기 테스트
        test_key = "test_sync_dependency"
        test_value = "test_sync_value"
        
        redis_client.set(test_key, test_value)
        result = redis_client.get(test_key)
        
        if result == test_value:
            print("✅ Redis sync read/write test successful")
        else:
            print("❌ Redis sync read/write test failed")
            return False
        
        # 정리
        redis_client.delete(test_key)
        redis_client.close()
        
        print("✅ Redis sync dependency test passed")
        return True
        
    except Exception as e:
        print(f"❌ Redis sync dependency test failed: {e}")
        return False


async def main():
    """메인 테스트 함수"""
    print("🚀 Starting Dependency Tests...\n")
    
    results = []
    
    # 설정 의존성 테스트
    results.append(test_settings_dependency())
    
    # 데이터베이스 의존성 테스트
    results.append(test_database_dependency())
    
    # Redis 의존성 테스트
    results.append(await test_redis_dependency())
    
    # 동기 Redis 의존성 테스트
    results.append(test_redis_sync_dependency())
    
    # 결과 요약
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All dependency tests passed!")
        return 0
    else:
        print("❌ Some dependency tests failed!")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main())) 