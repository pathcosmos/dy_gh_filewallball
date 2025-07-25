#!/usr/bin/env python3
"""
FileWallBall Redis 클라이언트 설정
Redis 연결 풀 및 클라이언트 관리 모듈
"""

import redis
import json
import logging
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager
import time
from functools import wraps

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 클라이언트 관리 클래스"""
    
    def __init__(self, 
                 host: str = 'redis',  # Kubernetes 환경에 맞게 redis로 변경
                 port: int = 6379,
                 password: str = 'filewallball2024',
                 db: int = 0,
                 max_connections: int = 20,
                 socket_timeout: int = 5,
                 socket_connect_timeout: int = 5,
                 retry_on_timeout: bool = True,
                 health_check_interval: int = 30):
        """
        Redis 클라이언트 초기화
        
        Args:
            host: Redis 서버 호스트
            port: Redis 서버 포트
            password: Redis 비밀번호
            db: Redis 데이터베이스 번호
            max_connections: 최대 연결 수
            socket_timeout: 소켓 타임아웃 (초)
            socket_connect_timeout: 연결 타임아웃 (초)
            retry_on_timeout: 타임아웃 시 재시도 여부
            health_check_interval: 헬스체크 간격 (초)
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval
        
        # Redis 연결 풀 생성
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            password=password,
            db=db,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            health_check_interval=health_check_interval,
            decode_responses=True  # 문자열 자동 디코딩
        )
        
        # Redis 클라이언트 생성
        self.client = redis.Redis(connection_pool=self.pool)
        
        # 연결 테스트
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Redis 연결 테스트"""
        try:
            self.client.ping()
            logger.info(f"✅ Redis 연결 성공: {self.host}:{self.port}")
            return True
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis 연결 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Redis 연결 오류: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    @contextmanager
    def get_connection(self):
        """Redis 연결 컨텍스트 매니저"""
        try:
            yield self.client
        except redis.ConnectionError as e:
            logger.error(f"Redis 연결 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"Redis 작업 오류: {e}")
            raise
    
    def set_with_ttl(self, key: str, value: Union[str, Dict, Any], ttl: int) -> bool:
        """
        TTL과 함께 키-값 설정
        
        Args:
            key: Redis 키
            value: 저장할 값 (문자열 또는 JSON 직렬화 가능한 객체)
            ttl: 만료 시간 (초)
        
        Returns:
            bool: 성공 여부
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            with self.get_connection() as redis_client:
                result = redis_client.setex(key, ttl, value)
                logger.debug(f"캐시 설정: {key} (TTL: {ttl}초)")
                return result
        except Exception as e:
            logger.error(f"캐시 설정 실패: {key}, 오류: {e}")
            return False
    
    def get(self, key: str) -> Optional[Union[str, Dict]]:
        """
        키로 값 조회
        
        Args:
            key: Redis 키
        
        Returns:
            저장된 값 또는 None
        """
        try:
            with self.get_connection() as redis_client:
                value = redis_client.get(key)
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
    
    def delete(self, key: str) -> bool:
        """
        키 삭제
        
        Args:
            key: 삭제할 Redis 키
        
        Returns:
            bool: 성공 여부
        """
        try:
            with self.get_connection() as redis_client:
                result = redis_client.delete(key)
                logger.debug(f"캐시 삭제: {key}")
                return result > 0
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {key}, 오류: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        키 존재 여부 확인
        
        Args:
            key: 확인할 Redis 키
        
        Returns:
            bool: 존재 여부
        """
        try:
            with self.get_connection() as redis_client:
                return redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"키 존재 확인 실패: {key}, 오류: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        키의 TTL 조회
        
        Args:
            key: Redis 키
        
        Returns:
            int: 남은 TTL (초), -1은 만료 없음, -2는 키 없음
        """
        try:
            with self.get_connection() as redis_client:
                return redis_client.ttl(key)
        except Exception as e:
            logger.error(f"TTL 조회 실패: {key}, 오류: {e}")
            return -2
    
    def flush_db(self) -> bool:
        """
        현재 데이터베이스 초기화
        
        Returns:
            bool: 성공 여부
        """
        try:
            with self.get_connection() as redis_client:
                redis_client.flushdb()
                logger.info("Redis 데이터베이스 초기화 완료")
                return True
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Redis 서버 정보 조회
        
        Returns:
            Dict: Redis 서버 정보
        """
        try:
            with self.get_connection() as redis_client:
                info = redis_client.info()
                return {
                    'version': info.get('redis_version'),
                    'used_memory': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'total_commands_processed': info.get('total_commands_processed'),
                    'keyspace_hits': info.get('keyspace_hits'),
                    'keyspace_misses': info.get('keyspace_misses'),
                    'uptime_in_seconds': info.get('uptime_in_seconds')
                }
        except Exception as e:
            logger.error(f"Redis 정보 조회 실패: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회
        
        Returns:
            Dict: 캐시 통계 정보
        """
        try:
            with self.get_connection() as redis_client:
                info = redis_client.info()
                hits = info.get('keyspace_hits', 0)
                misses = info.get('keyspace_misses', 0)
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                
                return {
                    'total_requests': total,
                    'hits': hits,
                    'misses': misses,
                    'hit_rate': round(hit_rate, 2),
                    'keyspace_hits': hits,
                    'keyspace_misses': misses
                }
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {}


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Redis 작업 실패 시 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        delay: 재시도 간격 (초)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Redis 작업 실패, {delay}초 후 재시도 ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Redis 작업 최종 실패: {e}")
                        raise last_exception
            return None
        return wrapper
    return decorator


# 캐시 키 네임스페이스 상수
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


# TTL 상수
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


# 전역 Redis 클라이언트 인스턴스
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    전역 Redis 클라이언트 인스턴스 반환
    
    Returns:
        RedisClient: Redis 클라이언트 인스턴스
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


def init_redis_client(**kwargs) -> RedisClient:
    """
    Redis 클라이언트 초기화
    
    Args:
        **kwargs: RedisClient 생성자 매개변수
    
    Returns:
        RedisClient: 초기화된 Redis 클라이언트
    """
    global _redis_client
    _redis_client = RedisClient(**kwargs)
    return _redis_client


# 사용 예시
if __name__ == "__main__":
    # Redis 클라이언트 초기화
    redis_client = get_redis_client()
    
    # 연결 테스트
    if redis_client.is_connected():
        print("✅ Redis 연결 성공")
        
        # 서버 정보 출력
        info = redis_client.get_info()
        print(f"Redis 버전: {info.get('version')}")
        print(f"사용 메모리: {info.get('used_memory')}")
        print(f"연결된 클라이언트: {info.get('connected_clients')}")
        
        # 캐시 통계 출력
        stats = redis_client.get_stats()
        print(f"캐시 히트율: {stats.get('hit_rate')}%")
        
    else:
        print("❌ Redis 연결 실패") 