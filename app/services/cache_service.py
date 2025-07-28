"""
캐시 서비스 모듈
"""

import redis
import json
from typing import Optional, Any, Dict
from datetime import datetime, timedelta


class CacheService:
    """Redis 캐시 서비스 클래스"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        캐시에 값 저장
        
        Args:
            key: 캐시 키
            value: 저장할 값
            expire: 만료 시간 (초)
            
        Returns:
            저장 성공 여부
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.redis.setex(key, expire, value)
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            저장된 값 (없으면 None)
        """
        try:
            value = self.redis.get(key)
            if value is None:
                return None
            
            # JSON 파싱 시도
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.decode('utf-8')
                
        except Exception as e:
            print(f"캐시 조회 실패: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제
        
        Args:
            key: 캐시 키
            
        Returns:
            삭제 성공 여부
        """
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            print(f"캐시 삭제 실패: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        캐시 키 존재 여부 확인
        
        Args:
            key: 캐시 키
            
        Returns:
            키 존재 여부
        """
        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            print(f"캐시 키 확인 실패: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        캐시 키 만료 시간 설정
        
        Args:
            key: 캐시 키
            seconds: 만료 시간 (초)
            
        Returns:
            설정 성공 여부
        """
        try:
            return bool(self.redis.expire(key, seconds))
        except Exception as e:
            print(f"캐시 만료 시간 설정 실패: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        캐시 키의 남은 만료 시간 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            남은 만료 시간 (초, -1은 만료 없음, -2는 키 없음)
        """
        try:
            return self.redis.ttl(key)
        except Exception as e:
            print(f"캐시 TTL 조회 실패: {e}")
            return -2
    
    def clear_pattern(self, pattern: str) -> int:
        """
        패턴에 맞는 캐시 키들 삭제
        
        Args:
            pattern: 키 패턴 (예: "file:*")
            
        Returns:
            삭제된 키 개수
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"캐시 패턴 삭제 실패: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회
        
        Returns:
            캐시 통계 정보
        """
        try:
            info = self.redis.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0)
            }
        except Exception as e:
            print(f"캐시 통계 조회 실패: {e}")
            return {} 