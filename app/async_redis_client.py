#!/usr/bin/env python3
"""
FileWallBall 비동기 Redis 클라이언트 설정
redis.asyncio 모듈을 사용한 비동기 Redis 연결 풀 및 클라이언트 관리 모듈
Task 3.1: Redis 비동기 클라이언트 구현
Task 3.5: 캐시 모니터링 및 메트릭 구현
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis

# 메트릭 import
from .metrics import cache_metrics, cache_metrics_decorator

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncRedisClient:
    """비동기 Redis 클라이언트 관리 클래스"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        password: str = None,
        db: int = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
        cluster_mode: bool = False,
        cluster_nodes: List[str] = None,
        redis_url: str = None,
    ):
        """
        비동기 Redis 클라이언트 초기화

        Args:
            host: Redis 서버 호스트
            port: Redis 서버 포트
            password: Redis 비밀번호
            db: Redis 데이터베이스 번호
            max_connections: 최대 연결 수 (기본값: 50)
            socket_timeout: 소켓 타임아웃 (초)
            socket_connect_timeout: 연결 타임아웃 (초)
            retry_on_timeout: 타임아웃 시 재시도 여부
            health_check_interval: 헬스체크 간격 (초)
            cluster_mode: Redis Cluster 모드 사용 여부
            cluster_nodes: 클러스터 노드 목록
            redis_url: Redis 연결 URL
        """
        # 환경 변수에서 설정 로드
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.cluster_nodes = cluster_nodes or self._parse_cluster_nodes()
        self.cluster_mode = cluster_mode or bool(self.cluster_nodes)

        # 기본 설정
        self.host = host or os.getenv("REDIS_HOST", "redis")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.password = password or os.getenv("REDIS_PASSWORD", "filewallball2024")
        self.db = db or int(os.getenv("REDIS_DB", "0"))
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval

        # Redis 클라이언트 초기화
        self.client = None
        self.pool = None

    def _parse_cluster_nodes(self) -> List[str]:
        """환경 변수에서 클러스터 노드 목록 파싱"""
        cluster_nodes_str = os.getenv("REDIS_CLUSTER_NODES")
        if cluster_nodes_str:
            return [node.strip() for node in cluster_nodes_str.split(",")]
        return []

    async def _create_client(self):
        """Redis 클라이언트 생성"""
        if self.cluster_mode:
            # Redis Cluster 모드
            if self.redis_url:
                self.client = redis.RedisCluster.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    health_check_interval=self.health_check_interval,
                    decode_responses=True,
                )
            else:
                self.client = redis.RedisCluster(
                    startup_nodes=[
                        {"host": node.split(":")[0], "port": int(node.split(":")[1])}
                        for node in self.cluster_nodes
                    ],
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    health_check_interval=self.health_check_interval,
                    decode_responses=True,
                )
        else:
            # 단일 Redis 모드
            if self.redis_url:
                self.client = redis.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    health_check_interval=self.health_check_interval,
                    decode_responses=True,
                )
            else:
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    health_check_interval=self.health_check_interval,
                    decode_responses=True,
                )

    async def connect(self) -> bool:
        """Redis 연결"""
        try:
            await self._create_client()
            is_connected = await self._test_connection()
            if is_connected:
                logger.info("Redis 연결 성공")
                return True
            else:
                logger.error("Redis 연결 실패")
                return False
        except Exception as e:
            logger.error(f"Redis 연결 오류: {e}")
            return False

    async def _test_connection(self) -> bool:
        """연결 테스트"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 연결 테스트 실패: {e}")
            return False

    async def is_connected(self) -> bool:
        """연결 상태 확인"""
        try:
            await self.client.ping()
            return True
        except Exception:
            return False

    @asynccontextmanager
    async def get_connection(self):
        """Redis 연결 컨텍스트 매니저"""
        try:
            yield self.client
        except Exception as e:
            logger.error(f"Redis 연결 오류: {e}")
            raise

    @cache_metrics_decorator(
        operation="set", cache_type="redis", key_pattern="file_meta"
    )
    async def set_with_ttl(
        self, key: str, value: Union[str, Dict, Any], ttl: int
    ) -> bool:
        """
        TTL과 함께 값 설정

        Args:
            key: Redis 키
            value: 저장할 값
            ttl: TTL (초)

        Returns:
            bool: 성공 여부
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)

            async with self.get_connection() as redis_client:
                result = await redis_client.setex(key, ttl, value)
                logger.debug(f"캐시 설정: {key} (TTL: {ttl}초)")
                return result
        except Exception as e:
            logger.error(f"캐시 설정 실패: {key}, 오류: {e}")
            return False

    @cache_metrics_decorator(
        operation="get", cache_type="redis", key_pattern="file_meta"
    )
    async def get(self, key: str) -> Optional[Union[str, Dict]]:
        """
        키로 값 조회

        Args:
            key: Redis 키

        Returns:
            저장된 값 또는 None
        """
        try:
            async with self.get_connection() as redis_client:
                value = await redis_client.get(key)
                if value:
                    # JSON 형식인지 확인
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        return value
                return None
        except Exception as e:
            logger.error(f"캐시 조회 실패: {key}, 오류: {e}")
            return None

    @cache_metrics_decorator(
        operation="delete", cache_type="redis", key_pattern="file_meta"
    )
    async def delete(self, key: str) -> bool:
        """
        키 삭제

        Args:
            key: 삭제할 Redis 키

        Returns:
            bool: 성공 여부
        """
        try:
            async with self.get_connection() as redis_client:
                result = await redis_client.delete(key)
                logger.debug(f"캐시 삭제: {key}")
                return result > 0
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {key}, 오류: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        키 존재 여부 확인

        Args:
            key: 확인할 Redis 키

        Returns:
            bool: 존재 여부
        """
        try:
            async with self.get_connection() as redis_client:
                result = await redis_client.exists(key)
                return result > 0
        except Exception as e:
            logger.error(f"키 존재 확인 실패: {key}, 오류: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        키의 TTL 조회

        Args:
            key: Redis 키

        Returns:
            int: 남은 TTL (초), -1은 만료 없음, -2는 키 없음
        """
        try:
            async with self.get_connection() as redis_client:
                return await redis_client.ttl(key)
        except Exception as e:
            logger.error(f"TTL 조회 실패: {key}, 오류: {e}")
            return -2

    async def flush_db(self) -> bool:
        """
        현재 데이터베이스 초기화

        Returns:
            bool: 성공 여부
        """
        try:
            async with self.get_connection() as redis_client:
                await redis_client.flushdb()
                logger.info("Redis 데이터베이스 초기화 완료")
                return True
        except Exception as e:
            logger.error(f"Redis 데이터베이스 초기화 실패: {e}")
            return False

    async def get_info(self) -> Dict[str, Any]:
        """
        Redis 서버 정보 조회

        Returns:
            Dict: Redis 서버 정보
        """
        try:
            async with self.get_connection() as redis_client:
                info = await redis_client.info()
                return info
        except Exception as e:
            logger.error(f"Redis 정보 조회 실패: {e}")
            return {}

    async def get_stats(self) -> Dict[str, Any]:
        """
        Redis 통계 정보 조회

        Returns:
            Dict: Redis 통계 정보
        """
        try:
            async with self.get_connection() as redis_client:
                info = await redis_client.info()
                stats = {
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "total_connections_received": info.get(
                        "total_connections_received", 0
                    ),
                    "total_net_input_bytes": info.get("total_net_input_bytes", 0),
                    "total_net_output_bytes": info.get("total_net_output_bytes", 0),
                    "instantaneous_ops_per_sec": info.get(
                        "instantaneous_ops_per_sec", 0
                    ),
                    "instantaneous_input_kbps": info.get("instantaneous_input_kbps", 0),
                    "instantaneous_output_kbps": info.get(
                        "instantaneous_output_kbps", 0
                    ),
                    "rejected_connections": info.get("rejected_connections", 0),
                    "sync_full": info.get("sync_full", 0),
                    "sync_partial_ok": info.get("sync_partial_ok", 0),
                    "sync_partial_err": info.get("sync_partial_err", 0),
                    "expired_keys": info.get("expired_keys", 0),
                    "evicted_keys": info.get("evicted_keys", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "pubsub_channels": info.get("pubsub_channels", 0),
                    "pubsub_patterns": info.get("pubsub_patterns", 0),
                    "latest_fork_usec": info.get("latest_fork_usec", 0),
                    "migrate_cached_sockets": info.get("migrate_cached_sockets", 0),
                    "slave_expires_tracked_keys": info.get(
                        "slave_expires_tracked_keys", 0
                    ),
                    "active_defrag_hits": info.get("active_defrag_hits", 0),
                    "active_defrag_misses": info.get("active_defrag_misses", 0),
                    "active_defrag_key_hits": info.get("active_defrag_key_hits", 0),
                    "active_defrag_key_misses": info.get("active_defrag_key_misses", 0),
                }
                return stats
        except Exception as e:
            logger.error(f"Redis 통계 조회 실패: {e}")
            return {}

    async def mget(self, keys: List[str]) -> List[Optional[Union[str, Dict]]]:
        """
        여러 키의 값 조회

        Args:
            keys: 조회할 키 목록

        Returns:
            List: 값 목록 (없는 키는 None)
        """
        try:
            async with self.get_connection() as redis_client:
                values = await redis_client.mget(keys)
                result = []
                for value in values:
                    if value:
                        try:
                            result.append(json.loads(value))
                        except (json.JSONDecodeError, TypeError):
                            result.append(value)
                    else:
                        result.append(None)
                return result
        except Exception as e:
            logger.error(f"다중 캐시 조회 실패: {keys}, 오류: {e}")
            return [None] * len(keys)

    async def mset(
        self, data: Dict[str, Union[str, Dict, Any]], ttl: int = None
    ) -> bool:
        """
        여러 키-값 설정

        Args:
            data: 키-값 딕셔너리
            ttl: TTL (초, 선택사항)

        Returns:
            bool: 성공 여부
        """
        try:
            # JSON 직렬화
            serialized_data = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    serialized_data[key] = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_data[key] = str(value)

            async with self.get_connection() as redis_client:
                if ttl:
                    # TTL이 있는 경우 파이프라인 사용
                    pipe = redis_client.pipeline()
                    for key, value in serialized_data.items():
                        pipe.setex(key, ttl, value)
                    await pipe.execute()
                else:
                    await redis_client.mset(serialized_data)

                logger.debug(f"다중 캐시 설정: {len(data)}개 키")
                return True
        except Exception as e:
            logger.error(f"다중 캐시 설정 실패: {e}")
            return False

    async def scan_iter(self, match: str = "*", count: int = 100) -> List[str]:
        """
        패턴에 맞는 키 스캔

        Args:
            match: 키 패턴
            count: 한 번에 스캔할 키 수

        Returns:
            List: 키 목록
        """
        try:
            keys = []
            async with self.get_connection() as redis_client:
                async for key in redis_client.scan_iter(match=match, count=count):
                    keys.append(key)
            return keys
        except Exception as e:
            logger.error(f"키 스캔 실패: {match}, 오류: {e}")
            return []

    async def delete_pattern(self, pattern: str) -> int:
        """
        패턴에 맞는 키 삭제

        Args:
            pattern: 삭제할 키 패턴

        Returns:
            int: 삭제된 키 수
        """
        try:
            keys = await self.scan_iter(match=pattern)
            if not keys:
                return 0

            async with self.get_connection() as redis_client:
                result = await redis_client.delete(*keys)
                logger.info(f"패턴 삭제 완료: {pattern}, 삭제된 키: {result}개")
                return result
        except Exception as e:
            logger.error(f"패턴 삭제 실패: {pattern}, 오류: {e}")
            return 0

    async def close(self):
        """Redis 연결 종료"""
        try:
            if self.client:
                await self.client.close()
                logger.info("Redis 연결 종료")
        except Exception as e:
            logger.error(f"Redis 연결 종료 실패: {e}")


def async_retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    비동기 Redis 작업 실패 시 재시도 데코레이터

    Args:
        max_retries: 최대 재시도 횟수
        delay: 재시도 간격 (초)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Redis 작업 실패, {delay}초 후 재시도 ({attempt + 1}/{max_retries}): {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Redis 작업 최종 실패: {e}")
                        raise last_exception
            return None

        return wrapper

    return decorator


# 캐시 키 네임스페이스 상수 (기존과 동일)
class CacheKeys:
    """캐시 키 네임스페이스 정의"""

    # 파일 메타데이터 캐시 (TTL: 1시간)
    FILE_META = "file:meta:{file_uuid}"

    # 세션 데이터 캐시 (TTL: 24시간)
    SESSION = "session:user:{user_id}"

    # 임시 데이터 캐시 (TTL: 10분)
    TEMP_UPLOAD_PROGRESS = "temp:upload:progress:{upload_id}"
    TEMP_DOWNLOAD_TOKEN = "temp:download:token:{token}"

    # 시스템 캐시
    SYSTEM_SETTINGS = "system:settings:{key}"
    API_RATE_LIMIT = "rate_limit:{ip}:{endpoint}"


# TTL 상수 (기존과 동일)
class CacheTTL:
    """캐시 TTL 상수"""

    # 파일 메타데이터: 1시간
    FILE_META = 3600

    # 세션 데이터: 24시간
    SESSION = 86400

    # 임시 데이터: 10분
    TEMP_DATA = 600

    # 시스템 설정: 1시간
    SYSTEM_SETTINGS = 3600

    # API 레이트 리미트: 1분
    RATE_LIMIT = 60


# 전역 비동기 Redis 클라이언트 인스턴스
_async_redis_client: Optional[AsyncRedisClient] = None


async def get_async_redis_client() -> AsyncRedisClient:
    """
    전역 비동기 Redis 클라이언트 인스턴스 반환

    Returns:
        AsyncRedisClient: 비동기 Redis 클라이언트 인스턴스
    """
    global _async_redis_client
    if _async_redis_client is None:
        _async_redis_client = AsyncRedisClient()
        await _async_redis_client.connect()
    return _async_redis_client


async def init_async_redis_client(**kwargs) -> AsyncRedisClient:
    """
    비동기 Redis 클라이언트 초기화

    Args:
        **kwargs: AsyncRedisClient 생성자 매개변수

    Returns:
        AsyncRedisClient: 초기화된 비동기 Redis 클라이언트
    """
    global _async_redis_client
    _async_redis_client = AsyncRedisClient(**kwargs)
    await _async_redis_client.connect()
    return _async_redis_client


async def close_async_redis_client():
    """전역 비동기 Redis 클라이언트 연결 종료"""
    global _async_redis_client
    if _async_redis_client:
        await _async_redis_client.close()
        _async_redis_client = None


# 사용 예시
async def main():
    """비동기 Redis 클라이언트 사용 예시"""
    # Redis 클라이언트 초기화
    redis_client = await get_async_redis_client()

    # 연결 테스트
    if await redis_client.is_connected():
        print("✅ 비동기 Redis 연결 성공")

        # 서버 정보 출력
        info = await redis_client.get_info()
        print(f"Redis 버전: {info.get('redis_version')}")
        print(f"사용 메모리: {info.get('used_memory_human')}")
        print(f"연결된 클라이언트: {info.get('connected_clients')}")

        # 캐시 통계 출력
        stats = await redis_client.get_stats()
        print(f"캐시 히트율: {stats.get('hit_rate')}%")

        # 연결 종료
        await close_async_redis_client()

    else:
        print("❌ 비동기 Redis 연결 실패")


if __name__ == "__main__":
    asyncio.run(main())
