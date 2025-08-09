"""
Cache service - 단순화된 버전
"""

from typing import Any, Optional
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CacheService:
    """캐시 서비스 (단순화된 버전)"""
    
    def __init__(self):
        self.cache = {}  # 메모리 기반 단순 캐시
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        return self.cache.get(key)
    
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """캐시에 값 저장"""
        self.cache[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    async def clear(self) -> bool:
        """캐시 전체 삭제"""
        self.cache.clear()
        return True


# 싱글톤 인스턴스
cache_service = CacheService()