"""
Redis 연결 관리자 모듈
고급 연결 풀, 클러스터 모드, 장애 복구 기능을 제공합니다.
"""

import redis
import redis.cluster
import redis.sentinel
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RedisMode(Enum):
    """Redis 운영 모드"""
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


@dataclass
class RedisNode:
    """Redis 노드 정보"""
    host: str
    port: int
    password: Optional[str] = None
    db: int = 0
    weight: int = 1


@dataclass
class ConnectionConfig:
    """Redis 연결 설정"""
    mode: RedisMode = RedisMode.STANDALONE
    nodes: List[RedisNode] = None
    pool_size: int = 20
    max_connections: int = 50
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 2.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = None
    retry_on_timeout: bool = True
    retry_on_error: List[type] = None
    health_check_interval: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


class CircuitBreaker:
    """서킷 브레이커 패턴 구현"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_failure(self):
        """실패 기록"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def record_success(self):
        """성공 기록"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def can_execute(self) -> bool:
        """실행 가능 여부 확인"""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        return True  # HALF_OPEN 상태


class RedisConnectionManager:
    """Redis 연결 관리자"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker()
        self.connection_pool = None
        self.client = None
        self.health_check_task = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Redis 연결 초기화"""
        try:
            if self.config.mode == RedisMode.STANDALONE:
                self._setup_standalone()
            elif self.config.mode == RedisMode.CLUSTER:
                self._setup_cluster()
            elif self.config.mode == RedisMode.SENTINEL:
                self._setup_sentinel()
            
            # 연결 테스트
            self._test_connection()
            logger.info(f"Redis connection initialized successfully in {self.config.mode.value} mode")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    def _setup_standalone(self):
        """단일 Redis 서버 설정"""
        if not self.config.nodes:
            raise ValueError("At least one Redis node is required")
        
        node = self.config.nodes[0]
        self.connection_pool = redis.ConnectionPool(
            host=node.host,
            port=node.port,
            password=node.password,
            db=node.db,
            max_connections=self.config.max_connections,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_keepalive=self.config.socket_keepalive,
            socket_keepalive_options=self.config.socket_keepalive_options,
            retry_on_timeout=self.config.retry_on_timeout,
            retry_on_error=self.config.retry_on_error or [redis.ConnectionError],
            decode_responses=True
        )
        
        self.client = redis.Redis(connection_pool=self.connection_pool)
    
    def _setup_cluster(self):
        """Redis 클러스터 설정"""
        if not self.config.nodes:
            raise ValueError("At least one Redis cluster node is required")
        
        startup_nodes = [
            {"host": node.host, "port": node.port, "password": node.password}
            for node in self.config.nodes
        ]
        
        self.client = redis.cluster.RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_keepalive=self.config.socket_keepalive,
            retry_on_timeout=self.config.retry_on_timeout,
            retry_on_error=self.config.retry_on_error or [redis.ConnectionError],
            max_connections_per_node=self.config.pool_size
        )
    
    def _setup_sentinel(self):
        """Redis Sentinel 설정"""
        if not self.config.nodes:
            raise ValueError("At least one Redis sentinel node is required")
        
        sentinel_hosts = [(node.host, node.port) for node in self.config.nodes]
        
        self.client = redis.sentinel.Sentinel(
            sentinel_hosts,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_keepalive=self.config.socket_keepalive,
            retry_on_timeout=self.config.retry_on_timeout,
            retry_on_error=self.config.retry_on_error or [redis.ConnectionError],
            decode_responses=True
        )
    
    def _test_connection(self):
        """연결 테스트"""
        try:
            self.client.ping()
            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise ConnectionError(f"Redis connection test failed: {e}")
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """재시도 로직과 함께 Redis 작업 실행"""
        if not self.circuit_breaker.can_execute():
            raise ConnectionError("Circuit breaker is open")
        
        for attempt in range(self.config.max_retries):
            try:
                result = operation(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result
            except (redis.ConnectionError, redis.TimeoutError) as e:
                self.circuit_breaker.record_failure()
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    logger.warning(f"Redis operation failed, retrying... (attempt {attempt + 1})")
                else:
                    raise ConnectionError(f"Redis operation failed after {self.config.max_retries} attempts: {e}")
            except Exception as e:
                logger.error(f"Unexpected Redis error: {e}")
                raise
    
    def get_client(self) -> Union[redis.Redis, redis.cluster.RedisCluster]:
        """Redis 클라이언트 반환"""
        return self.client
    
    def get_connection_info(self) -> Dict[str, Any]:
        """연결 정보 반환"""
        try:
            info = self.client.info()
            return {
                "mode": self.config.mode.value,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                "circuit_breaker_state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count
            }
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {
                "mode": self.config.mode.value,
                "error": str(e),
                "circuit_breaker_state": self.circuit_breaker.state
            }
    
    async def health_check(self):
        """헬스체크 실행"""
        try:
            self._test_connection()
            logger.debug("Redis health check passed")
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
    
    async def start_health_check(self):
        """헬스체크 태스크 시작"""
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop_health_check(self):
        """헬스체크 태스크 중지"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None
    
    async def _health_check_loop(self):
        """헬스체크 루프"""
        while True:
            try:
                await self.health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    def close(self):
        """연결 종료"""
        if self.client:
            self.client.close()
        if self.connection_pool:
            self.connection_pool.disconnect()


# 전역 Redis 연결 관리자 인스턴스
_redis_manager: Optional[RedisConnectionManager] = None


def get_redis_manager() -> RedisConnectionManager:
    """Redis 연결 관리자 인스턴스 반환 (싱글톤 패턴)"""
    global _redis_manager
    if _redis_manager is None:
        from app.config import get_settings
        
        settings = get_settings()
        
        # 설정에서 Redis 노드 정보 생성
        nodes = [
            RedisNode(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password if settings.redis_password else None,
                db=settings.redis_db
            )
        ]
        
        config = ConnectionConfig(
            mode=RedisMode.STANDALONE,  # 기본값, 환경변수로 변경 가능
            nodes=nodes,
            pool_size=settings.redis_pool_size,
            max_connections=settings.redis_pool_size * 2,
            socket_timeout=5.0,
            socket_connect_timeout=2.0,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        _redis_manager = RedisConnectionManager(config)
    
    return _redis_manager


@asynccontextmanager
async def redis_context():
    """Redis 컨텍스트 매니저"""
    manager = get_redis_manager()
    try:
        await manager.start_health_check()
        yield manager
    finally:
        await manager.stop_health_check()
        manager.close() 