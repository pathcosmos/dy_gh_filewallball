#!/usr/bin/env python3
"""
Redis 성능 테스트 스크립트
FileWallBall Redis 캐싱 시스템 성능 검증
"""

import json
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import redis


class RedisPerformanceTest:
    def __init__(self, host="localhost", port=6379, password="filewallball2024"):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        self.test_results = {}

    def test_connection(self):
        """Redis 연결 테스트"""
        try:
            self.redis_client.ping()
            print("✓ Redis 연결 성공")
            return True
        except Exception as e:
            print(f"✗ Redis 연결 실패: {e}")
            return False

    def test_basic_operations(self, iterations=1000):
        """기본 작업 성능 테스트"""
        print(f"\n=== 기본 작업 성능 테스트 ({iterations}회) ===")

        start_time = time.time()

        for i in range(iterations):
            key = f"test:basic:{i}"
            value = f"value_{i}_{random.randint(1000, 9999)}"

            # SET 작업
            self.redis_client.set(key, value)

            # GET 작업
            self.redis_client.get(key)

            # EXISTS 작업
            self.redis_client.exists(key)

            # TTL 설정
            self.redis_client.expire(key, 60)

            # DELETE 작업 (50% 확률)
            if i % 2 == 0:
                self.redis_client.delete(key)

        end_time = time.time()
        duration = end_time - start_time
        ops_per_sec = iterations / duration

        self.test_results["basic_operations"] = {
            "iterations": iterations,
            "duration": duration,
            "ops_per_sec": ops_per_sec,
        }

        print(f"완료 시간: {duration:.2f}초")
        print(f"초당 작업: {ops_per_sec:.2f} ops/sec")

        return ops_per_sec

    def test_hash_operations(self, iterations=500):
        """Hash 작업 성능 테스트"""
        print(f"\n=== Hash 작업 성능 테스트 ({iterations}회) ===")

        start_time = time.time()

        for i in range(iterations):
            hash_key = f"test:hash:{i}"

            # Hash 필드 설정
            hash_data = {
                "field1": f"value1_{i}",
                "field2": f"value2_{i}",
                "field3": random.randint(1, 1000),
                "field4": json.dumps({"nested": f"data_{i}"}),
            }

            # HSET 작업
            self.redis_client.hset(hash_key, mapping=hash_data)

            # HGET 작업
            self.redis_client.hget(hash_key, "field1")
            self.redis_client.hget(hash_key, "field3")

            # HGETALL 작업
            self.redis_client.hgetall(hash_key)

            # HEXISTS 작업
            self.redis_client.hexists(hash_key, "field1")

            # TTL 설정
            self.redis_client.expire(hash_key, 60)

        end_time = time.time()
        duration = end_time - start_time
        ops_per_sec = iterations / duration

        self.test_results["hash_operations"] = {
            "iterations": iterations,
            "duration": duration,
            "ops_per_sec": ops_per_sec,
        }

        print(f"완료 시간: {duration:.2f}초")
        print(f"초당 작업: {ops_per_sec:.2f} ops/sec")

        return ops_per_sec

    def test_list_operations(self, iterations=300):
        """List 작업 성능 테스트"""
        print(f"\n=== List 작업 성능 테스트 ({iterations}회) ===")

        start_time = time.time()

        for i in range(iterations):
            list_key = f"test:list:{i}"

            # LPUSH 작업
            for j in range(10):
                self.redis_client.lpush(list_key, f"item_{j}")

            # RPUSH 작업
            for j in range(10):
                self.redis_client.rpush(list_key, f"item_r_{j}")

            # LRANGE 작업
            self.redis_client.lrange(list_key, 0, -1)

            # LLEN 작업
            length = self.redis_client.llen(list_key)

            # LPOP 작업
            if length > 0:
                self.redis_client.lpop(list_key)

            # TTL 설정
            self.redis_client.expire(list_key, 60)

        end_time = time.time()
        duration = end_time - start_time
        ops_per_sec = iterations / duration

        self.test_results["list_operations"] = {
            "iterations": iterations,
            "duration": duration,
            "ops_per_sec": ops_per_sec,
        }

        print(f"완료 시간: {duration:.2f}초")
        print(f"초당 작업: {ops_per_sec:.2f} ops/sec")

        return ops_per_sec

    def test_concurrent_operations(self, num_threads=10, operations_per_thread=100):
        """동시 작업 성능 테스트"""
        print(
            "\n=== 동시 작업 성능 테스트 "
            f"({num_threads} 스레드, {operations_per_thread} 작업/스레드) ==="
        )

        def worker(thread_id):
            results = []
            for i in range(operations_per_thread):
                key = f"test:concurrent:{thread_id}:{i}"
                value = f"value_{thread_id}_{i}_{random.randint(1000, 9999)}"

                start_time = time.time()
                self.redis_client.set(key, value)
                self.redis_client.get(key)
                self.redis_client.expire(key, 30)
                end_time = time.time()

                results.append(end_time - start_time)

            return results

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            all_results = []

            for future in futures:
                all_results.extend(future.result())

        end_time = time.time()
        total_duration = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_sec = total_operations / total_duration

        avg_response_time = sum(all_results) / len(all_results)
        min_response_time = min(all_results)
        max_response_time = max(all_results)

        self.test_results["concurrent_operations"] = {
            "num_threads": num_threads,
            "operations_per_thread": operations_per_thread,
            "total_operations": total_operations,
            "total_duration": total_duration,
            "ops_per_sec": ops_per_sec,
            "avg_response_time": avg_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
        }

        print(f"총 완료 시간: {total_duration:.2f}초")
        print(f"총 작업 수: {total_operations}")
        print(f"초당 작업: {ops_per_sec:.2f} ops/sec")
        print(f"평균 응답 시간: {avg_response_time:.4f}초")
        print(f"최소 응답 시간: {min_response_time:.4f}초")
        print(f"최대 응답 시간: {max_response_time:.4f}초")

        return ops_per_sec

    def test_memory_usage(self):
        """메모리 사용량 테스트"""
        print("\n=== 메모리 사용량 테스트 ===")

        # 초기 메모리 사용량
        info_before = self.redis_client.info("memory")
        used_memory_before = int(info_before["used_memory"])

        print(f"초기 메모리 사용량: {used_memory_before / 1024 / 1024:.2f} MB")

        # 대량 데이터 삽입
        large_data_count = 1000
        for i in range(large_data_count):
            key = f"test:memory:{i}"
            # 1KB 크기의 데이터
            value = "".join(
                random.choices(string.ascii_letters + string.digits, k=1024)
            )
            self.redis_client.set(key, value)
            self.redis_client.expire(key, 300)  # 5분 TTL

        # 메모리 사용량 확인
        info_after = self.redis_client.info("memory")
        used_memory_after = int(info_after["used_memory"])

        memory_increase = used_memory_after - used_memory_before
        memory_increase_mb = memory_increase / 1024 / 1024

        print(f"최종 메모리 사용량: {used_memory_after / 1024 / 1024:.2f} MB")
        print(f"메모리 증가량: {memory_increase_mb:.2f} MB")
        print(f"데이터당 평균 메모리: {memory_increase_mb / large_data_count:.2f} MB")

        self.test_results["memory_usage"] = {
            "initial_memory_mb": used_memory_before / 1024 / 1024,
            "final_memory_mb": used_memory_after / 1024 / 1024,
            "memory_increase_mb": memory_increase_mb,
            "data_count": large_data_count,
            "avg_memory_per_data_mb": memory_increase_mb / large_data_count,
        }

        return memory_increase_mb

    def cleanup_test_data(self):
        """테스트 데이터 정리"""
        print("\n=== 테스트 데이터 정리 ===")

        patterns = [
            "test:basic:*",
            "test:hash:*",
            "test:list:*",
            "test:concurrent:*",
            "test:memory:*",
        ]
        total_deleted = 0

        for pattern in patterns:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                total_deleted += deleted
                print(f"삭제된 키 ({pattern}): {deleted}개")

        print(f"총 삭제된 키: {total_deleted}개")

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "=" * 50)
        print("Redis 성능 테스트 결과 요약")
        print("=" * 50)
        print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if "basic_operations" in self.test_results:
            basic = self.test_results["basic_operations"]
            print(f"기본 작업: {basic['ops_per_sec']:.2f} ops/sec")

        if "hash_operations" in self.test_results:
            hash_ops = self.test_results["hash_operations"]
            print(f"Hash 작업: {hash_ops['ops_per_sec']:.2f} ops/sec")

        if "list_operations" in self.test_results:
            list_ops = self.test_results["list_operations"]
            print(f"List 작업: {list_ops['ops_per_sec']:.2f} ops/sec")

        if "concurrent_operations" in self.test_results:
            concurrent = self.test_results["concurrent_operations"]
            print(f"동시 작업: {concurrent['ops_per_sec']:.2f} ops/sec")
            print(f"평균 응답 시간: {concurrent['avg_response_time']:.4f}초")

        if "memory_usage" in self.test_results:
            memory = self.test_results["memory_usage"]
            print(f"메모리 증가량: {memory['memory_increase_mb']:.2f} MB")

        print("=" * 50)

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("Redis 성능 테스트 시작")
        print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.test_connection():
            return False

        try:
            self.test_basic_operations()
            self.test_hash_operations()
            self.test_list_operations()
            self.test_concurrent_operations()
            self.test_memory_usage()

            self.print_summary()

            # 테스트 데이터 정리
            self.cleanup_test_data()

            return True

        except Exception as e:
            print(f"테스트 중 오류 발생: {e}")
            return False


if __name__ == "__main__":
    # Redis 성능 테스트 실행
    tester = RedisPerformanceTest()
    success = tester.run_all_tests()

    if success:
        print("\n✓ 모든 테스트가 성공적으로 완료되었습니다.")
    else:
        print("\n✗ 테스트 중 오류가 발생했습니다.")
