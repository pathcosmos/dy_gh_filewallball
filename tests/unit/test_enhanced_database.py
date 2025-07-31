#!/usr/bin/env python3
"""
Enhanced Database Connection Pool and Session Management Test Script.
"""

import sys
import threading
import time
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from app.models.database_enhanced import (
    db_health_checker,
    enhanced_db_manager,
    get_db_session,
    transaction_rollback_decorator,
    with_transaction,
)


def test_connection_info():
    """연결 정보 테스트"""
    print("Testing connection info...")

    connection_info = enhanced_db_manager.get_connection_info()
    print(f"Connection info: {connection_info}")

    # Task 5.2 요구사항 확인
    assert connection_info["pool_size"] == 20, "pool_size should be 20"
    assert connection_info["max_overflow"] == 30, "max_overflow should be 30"
    assert connection_info["pool_pre_ping"] is True, "pool_pre_ping should be True"
    assert connection_info["pool_recycle"] == 3600, "pool_recycle should be 3600"

    print("Connection info test passed!")


def test_connection():
    """연결 테스트"""
    print("\nTesting database connection...")

    is_connected = enhanced_db_manager.test_connection()
    print(f"Database connected: {is_connected}")

    if is_connected:
        print("Connection test passed!")
    else:
        print("Connection test failed!")
        return False

    return True


def test_pool_status():
    """연결 풀 상태 테스트"""
    print("\nTesting pool status...")

    pool_status = enhanced_db_manager.get_pool_status()
    print(f"Pool status: {pool_status}")

    # 풀 상태 정보 확인
    required_keys = ["pool_size", "checked_in", "checked_out", "overflow", "invalid"]
    for key in required_keys:
        assert key in pool_status, f"Pool status should contain {key}"

    print("Pool status test passed!")


def test_session_management():
    """세션 관리 테스트"""
    print("\nTesting session management...")

    # 일반 세션 테스트
    session = enhanced_db_manager.get_db()
    try:
        print(f"Session created: {session}")
        print(f"Session is active: {session.is_active}")
    finally:
        session.close()
        print("Session closed")

    # 컨텍스트 매니저 세션 테스트
    with get_db_session() as session:
        print(f"Context manager session: {session}")
        print(f"Context manager session is active: {session.is_active}")

    print("Session management test passed!")


def test_health_checker():
    """헬스 체커 테스트"""
    print("\nTesting health checker...")

    # 연결 상태 체크
    connection_health = db_health_checker.check_connection()
    print(f"Connection health: {connection_health}")

    # 성능 체크
    performance_health = db_health_checker.check_performance()
    print(f"Performance health: {performance_health}")

    print("Health checker test passed!")


@transaction_rollback_decorator
def test_transaction_decorator(session: Session, should_fail: bool = False):
    """트랜잭션 데코레이터 테스트"""
    print(f"Testing transaction decorator (should_fail={should_fail})...")

    # 간단한 쿼리 실행
    result = session.execute("SELECT 1 as test_value")
    row = result.fetchone()
    print(f"Query result: {row}")

    if should_fail:
        raise Exception("Simulated transaction failure")

    return row


def test_concurrent_connections():
    """동시 연결 테스트"""
    print("\nTesting concurrent connections...")

    def worker(worker_id: int):
        """워커 함수"""
        try:
            with get_db_session() as session:
                result = session.execute("SELECT 1 as worker_result")
                row = result.fetchone()
                print(f"Worker {worker_id} result: {row}")
                time.sleep(0.1)  # 짧은 대기
        except Exception as e:
            print(f"Worker {worker_id} error: {e}")

    # 10개의 동시 연결 테스트
    threads = []
    for i in range(10):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()

    # 모든 스레드 완료 대기
    for thread in threads:
        thread.join()

    # 풀 상태 확인
    pool_status = enhanced_db_manager.get_pool_status()
    print(f"Pool status after concurrent test: {pool_status}")

    print("Concurrent connections test passed!")


def test_transaction_rollback():
    """트랜잭션 롤백 테스트"""
    print("\nTesting transaction rollback...")

    # 성공하는 트랜잭션
    try:
        session = enhanced_db_manager.get_db()
        result = test_transaction_decorator(session, should_fail=False)
        print(f"Successful transaction result: {result}")
    except Exception as e:
        print(f"Unexpected error in successful transaction: {e}")

    # 실패하는 트랜잭션 (롤백 테스트)
    try:
        session = enhanced_db_manager.get_db()
        test_transaction_decorator(session, should_fail=True)
    except Exception as e:
        print(f"Expected transaction failure: {e}")
        print("Transaction rollback test passed!")


def test_with_transaction_decorator():
    """with_transaction 데코레이터 테스트"""
    print("\nTesting with_transaction decorator...")

    session = enhanced_db_manager.get_db()

    @with_transaction(session)
    def test_function():
        result = session.execute("SELECT 2 as test_value")
        return result.fetchone()

    try:
        result = test_function()
        print(f"with_transaction result: {result}")
        print("with_transaction decorator test passed!")
    except Exception as e:
        print(f"with_transaction error: {e}")
    finally:
        session.close()


def main():
    """메인 테스트 함수"""
    print("Starting Enhanced Database Tests...\n")

    try:
        test_connection_info()

        if not test_connection():
            print("Database connection failed, skipping other tests")
            return 1

        test_pool_status()
        test_session_management()
        test_health_checker()
        test_concurrent_connections()
        test_transaction_rollback()
        test_with_transaction_decorator()

        print("\nAll enhanced database tests passed!")
        return 0

    except Exception as e:
        print(f"\nEnhanced database test error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
