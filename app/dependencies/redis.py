"""
Redis dependencies for FastAPI.
"""

from typing import Generator
import redis.asyncio as redis

from app.config import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Redis 연결 풀
_redis_pool = None


async def get_redis_client() -> Generator[redis.Redis, None, None]:
    """
    Redis 클라이언트 의존성
    
    Yields:
        redis.Redis: Redis 클라이언트 인스턴스
        
    Example:
        @app.get("/cache/{key}")
        async def get_cache(key: str, redis_client: redis.Redis = Depends(get_redis_client)):
            return await redis_client.get(key)
    """
    global _redis_pool
    
    settings = get_settings()
    
    try:
        if _redis_pool is None:
            # Redis 연결 풀 생성
            _redis_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=True
            )
            logger.info("Redis connection pool created")
        
        # Redis 클라이언트 생성
        redis_client = redis.Redis(connection_pool=_redis_pool)
        
        # 연결 테스트
        await redis_client.ping()
        
        yield redis_client
        
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        raise
    finally:
        if redis_client:
            await redis_client.close()


def get_redis_sync() -> redis.Redis:
    """
    동기 Redis 클라이언트 의존성 (비동기 컨텍스트 외부에서 사용)
    
    Returns:
        redis.Redis: Redis 클라이언트 인스턴스
    """
    settings = get_settings()
    
    try:
        redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
        
        # 연결 테스트
        redis_client.ping()
        
        return redis_client
        
    except Exception as e:
        logger.error(f"Redis sync connection error: {e}")
        raise 