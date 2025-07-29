"""
캐시 서비스 모듈
Redis 연결 관리자와 통합된 고급 캐싱 기능을 제공합니다.
"""

import json
import logging
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta
from app.services.redis_connection_manager import get_redis_manager

logger = logging.getLogger(__name__)


class CacheService:
    """Redis 캐시 서비스 클래스"""
    
    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.client = self.redis_manager.get_client()
    
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        캐시에 값 저장 (비동기 재시도 로직 포함)
        
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
            
            await self.redis_manager.execute_with_retry(
                self.client.setex, key, expire, value
            )
            return True
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회 (비동기 재시도 로직 포함)
        
        Args:
            key: 캐시 키
            
        Returns:
            저장된 값 (없으면 None)
        """
        try:
            value = await self.redis_manager.execute_with_retry(
                self.client.get, key
            )
            
            if value is None:
                return None
            
            # JSON 파싱 시도
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제 (비동기 재시도 로직 포함)
        
        Args:
            key: 캐시 키
            
        Returns:
            삭제 성공 여부
        """
        try:
            result = await self.redis_manager.execute_with_retry(
                self.client.delete, key
            )
            return bool(result)
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        캐시 키 존재 여부 확인 (비동기 재시도 로직 포함)
        
        Args:
            key: 캐시 키
            
        Returns:
            키 존재 여부
        """
        try:
            result = await self.redis_manager.execute_with_retry(
                self.client.exists, key
            )
            return bool(result)
        except Exception as e:
            logger.error(f"캐시 키 확인 실패: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        캐시 키 만료 시간 설정 (비동기 재시도 로직 포함)
        
        Args:
            key: 캐시 키
            seconds: 만료 시간 (초)
            
        Returns:
            설정 성공 여부
        """
        try:
            result = await self.redis_manager.execute_with_retry(
                self.client.expire, key, seconds
            )
            return bool(result)
        except Exception as e:
            logger.error(f"캐시 만료 시간 설정 실패: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        캐시 키의 남은 만료 시간 조회 (비동기 재시도 로직 포함)
        
        Args:
            key: 캐시 키
            
        Returns:
            남은 만료 시간 (초, -1은 만료 없음, -2는 키 없음)
        """
        try:
            return await self.redis_manager.execute_with_retry(
                self.client.ttl, key
            )
        except Exception as e:
            logger.error(f"캐시 TTL 조회 실패: {e}")
            return -2
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        패턴에 맞는 캐시 키들 삭제 (비동기 재시도 로직 포함)
        
        Args:
            pattern: 키 패턴 (예: "file:*")
            
        Returns:
            삭제된 키 개수
        """
        try:
            keys = await self.redis_manager.execute_with_retry(
                self.client.keys, pattern
            )
            if keys:
                return await self.redis_manager.execute_with_retry(
                    self.client.delete, *keys
                )
            return 0
        except Exception as e:
            logger.error(f"캐시 패턴 삭제 실패: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회 (연결 관리자 정보 포함)
        
        Returns:
            캐시 통계 정보
        """
        try:
            # Redis 정보 조회
            info = await self.redis_manager.execute_with_retry(
                self.client.info
            )
            
            # 연결 관리자 정보
            connection_info = self.redis_manager.get_connection_info()
            
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'connection_mode': connection_info.get('mode', 'unknown'),
                'circuit_breaker_state': connection_info.get('circuit_breaker_state', 'unknown'),
                'failure_count': connection_info.get('failure_count', 0)
            }
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {}
    
    async def get_file_info(self, file_uuid: str) -> Optional[Dict[str, Any]]:
        """
        파일 정보 캐시 조회
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            파일 정보 (캐시된 경우)
        """
        cache_key = f"file:info:{file_uuid}"
        return await self.get(cache_key)
    
    async def set_file_info(self, file_uuid: str, file_info: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        파일 정보 캐시 저장
        
        Args:
            file_uuid: 파일 UUID
            file_info: 파일 정보
            ttl: 만료 시간 (초)
            
        Returns:
            저장 성공 여부
        """
        cache_key = f"file:info:{file_uuid}"
        return await self.set(cache_key, file_info, ttl)
    
    async def invalidate_file_cache(self, file_uuid: str) -> bool:
        """
        파일 관련 캐시 무효화
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            무효화 성공 여부
        """
        try:
            # 파일 정보 캐시 삭제
            await self.delete(f"file:info:{file_uuid}")
            # 파일 메타데이터 캐시 삭제
            await self.delete(f"file:meta:{file_uuid}")
            # 파일 통계 캐시 삭제
            await self.delete(f"file:stats:{file_uuid}")
            return True
        except Exception as e:
            logger.error(f"파일 캐시 무효화 실패: {e}")
            return False
    
    async def get_upload_stats(self, client_ip: str) -> Optional[Dict[str, Any]]:
        """
        업로드 통계 캐시 조회
        
        Args:
            client_ip: 클라이언트 IP
            
        Returns:
            업로드 통계 (캐시된 경우)
        """
        cache_key = f"upload:stats:{client_ip}"
        return await self.get(cache_key)
    
    async def set_upload_stats(self, client_ip: str, stats: Dict[str, Any], ttl: int = 300) -> bool:
        """
        업로드 통계 캐시 저장
        
        Args:
            client_ip: 클라이언트 IP
            stats: 업로드 통계
            ttl: 만료 시간 (초)
            
        Returns:
            저장 성공 여부
        """
        cache_key = f"upload:stats:{client_ip}"
        return await self.set(cache_key, stats, ttl)
    
    async def increment_counter(self, key: str, amount: int = 1, expire: int = 3600) -> Optional[int]:
        """
        카운터 증가 (Rate limiting용)
        
        Args:
            key: 카운터 키
            amount: 증가량
            expire: 만료 시간 (초)
            
        Returns:
            증가된 값
        """
        try:
            # INCR 명령어로 증가
            result = await self.redis_manager.execute_with_retry(
                self.client.incr, key
            )
            
            # 첫 번째 증가인 경우 만료 시간 설정
            if result == 1:
                await self.redis_manager.execute_with_retry(
                    self.client.expire, key, expire
                )
            
            return result
        except Exception as e:
            logger.error(f"카운터 증가 실패: {e}")
            return None
    
    async def get_counter(self, key: str) -> int:
        """
        카운터 값 조회
        
        Args:
            key: 카운터 키
            
        Returns:
            카운터 값
        """
        try:
            result = await self.redis_manager.execute_with_retry(
                self.client.get, key
            )
            return int(result) if result else 0
        except Exception as e:
            logger.error(f"카운터 조회 실패: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """
        캐시 서비스 헬스체크
        
        Returns:
            헬스체크 결과
        """
        try:
            # Redis 연결 테스트
            await self.redis_manager.health_check()
            
            # 간단한 캐시 작업 테스트
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            # 쓰기 테스트
            write_success = await self.set(test_key, test_value, 60)
            
            # 읽기 테스트
            read_value = await self.get(test_key)
            read_success = read_value is not None
            
            # 정리
            await self.delete(test_key)
            
            return {
                "status": "healthy" if write_success and read_success else "unhealthy",
                "write_test": write_success,
                "read_test": read_success,
                "connection_info": self.redis_manager.get_connection_info()
            }
        except Exception as e:
            logger.error(f"캐시 헬스체크 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_info": self.redis_manager.get_connection_info()
            } 