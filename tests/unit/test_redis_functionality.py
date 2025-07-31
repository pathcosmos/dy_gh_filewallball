#!/usr/bin/env python3
"""
Redis 기능 테스트 스크립트
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.redis_service import RedisService


def test_basic_operations():
    """기본 Redis 작업 테스트"""
    print("=== 기본 Redis 작업 테스트 ===")

    client = RedisService.get_redis_client()

    # 1. 연결 테스트
    print(f"1. 연결 상태: {client.is_connected()}")

    # 2. 서버 정보 조회
    info = client.get_info()
    print(f"2. Redis 버전: {info.get('version')}")
    print(f"   사용 메모리: {info.get('used_memory')}")
    print(f"   연결된 클라이언트: {info.get('connected_clients')}")

    # 3. 기본 SET/GET 테스트
    test_key = "test:basic:key"
    test_value = {"message": "Hello Redis!", "timestamp": datetime.now().isoformat()}

    # SET with TTL
    success = client.set_with_ttl(test_key, test_value, 60)
    print(f"3. SET with TTL: {success}")

    # GET
    retrieved_value = client.get(test_key)
    print(f"4. GET: {retrieved_value}")

    # EXISTS
    exists = client.exists(test_key)
    print(f"5. EXISTS: {exists}")

    # TTL
    ttl = client.ttl(test_key)
    print(f"6. TTL: {ttl}초")

    # DELETE
    deleted = client.delete(test_key)
    print(f"7. DELETE: {deleted}")

    # 삭제 후 존재 확인
    exists_after = client.exists(test_key)
    print(f"8. 삭제 후 EXISTS: {exists_after}")

    print()


def test_cache_patterns():
    """캐시 패턴 테스트"""
    print("=== 캐시 패턴 테스트 ===")

    client = RedisService.get_redis_client()

    # 파일 메타데이터 캐시 테스트
    file_uuid = "test-file-123"
    file_meta_key = CacheKeys.FILE_META.format(file_uuid=file_uuid)
    file_meta = {
        "uuid": file_uuid,
        "filename": "test.txt",
        "size": 1024,
        "mime_type": "text/plain",
        "upload_time": datetime.now().isoformat(),
    }

    success = client.set_with_ttl(file_meta_key, file_meta, CacheTTL.FILE_META)
    print(f"1. 파일 메타데이터 캐시 설정: {success}")

    retrieved_meta = client.get(file_meta_key)
    print(f"2. 파일 메타데이터 조회: {retrieved_meta}")

    # 세션 데이터 캐시 테스트
    user_id = "user-456"
    session_key = CacheKeys.SESSION.format(user_id=user_id)
    session_data = {
        "user_id": user_id,
        "login_time": datetime.now().isoformat(),
        "preferences": {"theme": "dark", "language": "ko"},
    }

    success = client.set_with_ttl(session_key, session_data, CacheTTL.SESSION)
    print(f"3. 세션 데이터 캐시 설정: {success}")

    retrieved_session = client.get(session_key)
    print(f"4. 세션 데이터 조회: {retrieved_session}")

    # 임시 데이터 캐시 테스트
    upload_id = "upload-789"
    temp_key = CacheKeys.TEMP_UPLOAD_PROGRESS.format(upload_id=upload_id)
    temp_data = {"upload_id": upload_id, "progress": 75, "status": "uploading"}

    success = client.set_with_ttl(temp_key, temp_data, CacheTTL.TEMP_DATA)
    print(f"5. 임시 데이터 캐시 설정: {success}")

    retrieved_temp = client.get(temp_key)
    print(f"6. 임시 데이터 조회: {retrieved_temp}")

    print()


def test_performance_and_stats():
    """성능 및 통계 테스트"""
    print("=== 성능 및 통계 테스트 ===")

    client = RedisService.get_redis_client()

    # 초기 통계
    initial_stats = client.get_stats()
    print(f"1. 초기 캐시 통계: {initial_stats}")

    # 대량 데이터 삽입 테스트
    print("2. 대량 데이터 삽입 테스트...")
    start_time = time.time()

    for i in range(100):
        key = f"test:bulk:key:{i}"
        value = {
            "index": i,
            "data": f"test_data_{i}",
            "timestamp": datetime.now().isoformat(),
        }
        client.set_with_ttl(key, value, 300)  # 5분 TTL

    insert_time = time.time() - start_time
    print(f"   100개 키 삽입 시간: {insert_time:.2f}초")

    # 대량 데이터 조회 테스트
    print("3. 대량 데이터 조회 테스트...")
    start_time = time.time()

    hit_count = 0
    for i in range(100):
        key = f"test:bulk:key:{i}"
        value = client.get(key)
        if value:
            hit_count += 1

    read_time = time.time() - start_time
    print(f"   100개 키 조회 시간: {read_time:.2f}초")
    print(f"   히트 수: {hit_count}/100")

    # 최종 통계
    final_stats = client.get_stats()
    print(f"4. 최종 캐시 통계: {final_stats}")

    # 정리
    print("5. 테스트 데이터 정리...")
    for i in range(100):
        key = f"test:bulk:key:{i}"
        client.delete(key)

    print()


def test_error_handling():
    """에러 처리 테스트"""
    print("=== 에러 처리 테스트 ===")

    client = RedisService.get_redis_client()

    # 존재하지 않는 키 조회
    non_existent = client.get("non:existent:key")
    print(f"1. 존재하지 않는 키 조회: {non_existent}")

    # 존재하지 않는 키 TTL
    ttl = client.ttl("non:existent:key")
    print(f"2. 존재하지 않는 키 TTL: {ttl}")

    # 존재하지 않는 키 삭제
    deleted = client.delete("non:existent:key")
    print(f"3. 존재하지 않는 키 삭제: {deleted}")

    # 존재하지 않는 키 존재 확인
    exists = client.exists("non:existent:key")
    print(f"4. 존재하지 않는 키 존재 확인: {exists}")

    print()


def test_connection_pool():
    """연결 풀 테스트"""
    print("=== 연결 풀 테스트 ===")

    # 여러 클라이언트 인스턴스 생성
    clients = []
    for i in range(5):
        client = RedisService.get_redis_client()
        clients.append(client)
        print(f"클라이언트 {i+1} 연결: {client.is_connected()}")

    # 동시 작업 테스트
    import threading

    def worker(client_id, client):
        for i in range(10):
            key = f"pool:test:{client_id}:{i}"
            value = {"worker": client_id, "iteration": i}
            client.set_with_ttl(key, value, 60)
            retrieved = client.get(key)
            print(f"Worker {client_id} - 작업 {i}: {'성공' if retrieved else '실패'}")

    threads = []
    for i, client in enumerate(clients):
        thread = threading.Thread(target=worker, args=(i, client))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("모든 워커 스레드 완료")
    print()


def main():
    """메인 테스트 함수"""
    print("🚀 Redis 클라이언트 기능 테스트 시작")
    print("=" * 50)

    try:
        # 1. 기본 작업 테스트
        test_basic_operations()

        # 2. 캐시 패턴 테스트
        test_cache_patterns()

        # 3. 성능 및 통계 테스트
        test_performance_and_stats()

        # 4. 에러 처리 테스트
        test_error_handling()

        # 5. 연결 풀 테스트
        test_connection_pool()

        print("✅ 모든 테스트 완료!")

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 포트 포워딩 정리
        import subprocess

        try:
            subprocess.run(["pkill", "-f", "kubectl port-forward"], check=False)
        except:
            pass


if __name__ == "__main__":
    main()
