#!/usr/bin/env python3
"""
FileWallBall Redis 클라이언트 테스트 스크립트
Redis 연결 풀 및 클라이언트 기능 테스트
"""

import sys
import os
import time
import json
from typing import Dict, Any

# app 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from redis_client import RedisClient, CacheKeys, CacheTTL, get_redis_client
    from redis_pool_config import get_redis_config, TTL_SETTINGS
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    sys.exit(1)

def test_connection():
    """Redis 연결 테스트"""
    print("🔗 Redis 연결 테스트 중...")
    
    try:
        redis_client = get_redis_client()
        if redis_client.is_connected():
            print("✅ Redis 연결 성공")
            return True
        else:
            print("❌ Redis 연결 실패")
            return False
    except Exception as e:
        print(f"❌ Redis 연결 오류: {e}")
        return False

def test_basic_operations():
    """기본 Redis 작업 테스트"""
    print("\n📝 기본 Redis 작업 테스트 중...")
    
    redis_client = get_redis_client()
    
    # SET/GET 테스트
    test_key = "test:basic:key"
    test_value = {"message": "Hello Redis!", "timestamp": time.time()}
    
    # 값 설정
    success = redis_client.set_with_ttl(test_key, test_value, 60)
    if success:
        print("✅ SET 작업 성공")
    else:
        print("❌ SET 작업 실패")
        return False
    
    # 값 조회
    retrieved_value = redis_client.get(test_key)
    if retrieved_value:
        print("✅ GET 작업 성공")
        print(f"   조회된 값: {retrieved_value}")
    else:
        print("❌ GET 작업 실패")
        return False
    
    # TTL 확인
    ttl = redis_client.ttl(test_key)
    print(f"   TTL: {ttl}초")
    
    # 키 존재 확인
    exists = redis_client.exists(test_key)
    print(f"   키 존재: {exists}")
    
    # 키 삭제
    deleted = redis_client.delete(test_key)
    if deleted:
        print("✅ DELETE 작업 성공")
    else:
        print("❌ DELETE 작업 실패")
    
    return True

def test_cache_patterns():
    """캐시 패턴 테스트"""
    print("\n🎯 캐시 패턴 테스트 중...")
    
    redis_client = get_redis_client()
    
    # 파일 메타데이터 캐시 테스트
    file_uuid = "test-file-123"
    file_meta = {
        "name": "test-document.pdf",
        "size": 1024000,
        "type": "application/pdf",
        "upload_time": "2024-01-01T10:00:00Z"
    }
    
    cache_key = CacheKeys.FILE_META.format(file_uuid=file_uuid)
    success = redis_client.set_with_ttl(cache_key, file_meta, CacheTTL.FILE_META)
    if success:
        print("✅ 파일 메타데이터 캐시 설정 성공")
    else:
        print("❌ 파일 메타데이터 캐시 설정 실패")
        return False
    
    # 세션 데이터 캐시 테스트
    user_id = 123
    session_data = {
        "user_id": user_id,
        "login_time": "2024-01-01T10:00:00Z",
        "permissions": ["read", "write"],
        "last_activity": "2024-01-01T10:30:00Z"
    }
    
    session_key = CacheKeys.SESSION.format(user_id=user_id)
    success = redis_client.set_with_ttl(session_key, session_data, CacheTTL.SESSION)
    if success:
        print("✅ 세션 데이터 캐시 설정 성공")
    else:
        print("❌ 세션 데이터 캐시 설정 실패")
        return False
    
    # 임시 데이터 캐시 테스트
    upload_id = "upload-456"
    progress_data = {
        "progress": 75,
        "status": "uploading",
        "bytes_uploaded": 768000,
        "total_bytes": 1024000
    }
    
    temp_key = CacheKeys.TEMP_UPLOAD_PROGRESS.format(upload_id=upload_id)
    success = redis_client.set_with_ttl(temp_key, progress_data, CacheTTL.TEMP_DATA)
    if success:
        print("✅ 임시 데이터 캐시 설정 성공")
    else:
        print("❌ 임시 데이터 캐시 설정 실패")
        return False
    
    # 캐시된 데이터 조회 테스트
    retrieved_file_meta = redis_client.get(cache_key)
    retrieved_session = redis_client.get(session_key)
    retrieved_progress = redis_client.get(temp_key)
    
    if all([retrieved_file_meta, retrieved_session, retrieved_progress]):
        print("✅ 모든 캐시 데이터 조회 성공")
    else:
        print("❌ 캐시 데이터 조회 실패")
        return False
    
    # 테스트 데이터 정리
    redis_client.delete(cache_key)
    redis_client.delete(session_key)
    redis_client.delete(temp_key)
    print("✅ 테스트 데이터 정리 완료")
    
    return True

def test_performance():
    """성능 테스트"""
    print("\n⚡ 성능 테스트 중...")
    
    redis_client = get_redis_client()
    
    # 대량 데이터 삽입 테스트
    start_time = time.time()
    success_count = 0
    
    for i in range(100):
        key = f"perf:test:{i}"
        value = {"index": i, "data": f"test_data_{i}", "timestamp": time.time()}
        if redis_client.set_with_ttl(key, value, 300):
            success_count += 1
    
    insert_time = time.time() - start_time
    print(f"📥 대량 삽입: {success_count}/100 성공 ({insert_time:.2f}초)")
    
    # 대량 데이터 조회 테스트
    start_time = time.time()
    retrieve_count = 0
    
    for i in range(100):
        key = f"perf:test:{i}"
        if redis_client.get(key):
            retrieve_count += 1
    
    retrieve_time = time.time() - start_time
    print(f"📖 대량 조회: {retrieve_count}/100 성공 ({retrieve_time:.2f}초)")
    
    # 테스트 데이터 정리
    for i in range(100):
        key = f"perf:test:{i}"
        redis_client.delete(key)
    
    print("✅ 성능 테스트 데이터 정리 완료")
    return True

def test_server_info():
    """서버 정보 조회 테스트"""
    print("\n📊 서버 정보 조회 테스트 중...")
    
    redis_client = get_redis_client()
    
    # 서버 정보 조회
    info = redis_client.get_info()
    if info:
        print("✅ 서버 정보 조회 성공")
        print(f"   Redis 버전: {info.get('version', 'N/A')}")
        print(f"   사용 메모리: {info.get('used_memory', 'N/A')}")
        print(f"   연결된 클라이언트: {info.get('connected_clients', 'N/A')}")
        print(f"   총 명령어 처리: {info.get('total_commands_processed', 'N/A')}")
        print(f"   업타임: {info.get('uptime_in_seconds', 'N/A')}초")
    else:
        print("❌ 서버 정보 조회 실패")
        return False
    
    # 캐시 통계 조회
    stats = redis_client.get_stats()
    if stats:
        print("✅ 캐시 통계 조회 성공")
        print(f"   총 요청: {stats.get('total_requests', 0)}")
        print(f"   히트: {stats.get('hits', 0)}")
        print(f"   미스: {stats.get('misses', 0)}")
        print(f"   히트율: {stats.get('hit_rate', 0)}%")
    else:
        print("❌ 캐시 통계 조회 실패")
        return False
    
    return True

def test_configuration():
    """설정 테스트"""
    print("\n⚙️ 설정 테스트 중...")
    
    # Redis 설정 조회
    config = get_redis_config('kubernetes')
    print("✅ Kubernetes 환경 설정 로드 성공")
    print(f"   호스트: {config.get('host')}")
    print(f"   포트: {config.get('port')}")
    print(f"   최대 연결: {config.get('max_connections')}")
    print(f"   소켓 타임아웃: {config.get('socket_timeout')}초")
    
    # TTL 설정 확인
    print("✅ TTL 설정 확인")
    for key, ttl in TTL_SETTINGS.items():
        print(f"   {key}: {ttl}초")
    
    return True

def main():
    """메인 테스트 함수"""
    print("=== FileWallBall Redis 클라이언트 테스트 시작 ===")
    
    tests = [
        ("연결 테스트", test_connection),
        ("기본 작업 테스트", test_basic_operations),
        ("캐시 패턴 테스트", test_cache_patterns),
        ("성능 테스트", test_performance),
        ("서버 정보 테스트", test_server_info),
        ("설정 테스트", test_configuration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} 통과")
                passed += 1
            else:
                print(f"❌ {test_name} 실패")
        except Exception as e:
            print(f"❌ {test_name} 오류: {e}")
    
    print(f"\n=== 테스트 결과 ===")
    print(f"통과: {passed}/{total}")
    print(f"성공률: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 모든 테스트 통과!")
        return True
    else:
        print("⚠️ 일부 테스트 실패")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 