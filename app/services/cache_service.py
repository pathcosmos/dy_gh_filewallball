"""
캐시 서비스 모듈
Redis 연결 관리자와 통합된 고급 캐싱 기능을 제공합니다.
Task 7.2: 캐싱 전략 및 TTL 정책 구현
"""

import json
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime
from app.services.redis_connection_manager import get_redis_manager

logger = logging.getLogger(__name__)


class CacheService:
    """Redis 캐시 서비스 클래스 - Task 7.2 캐싱 전략 및 TTL 정책 구현"""
    
    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.client = self.redis_manager.get_client()
        
        # Task 7.2: 동적 TTL 정책 설정
        self.ttl_policies = {
            'file_info': {
                'base_ttl': 3600,  # 기본 1시간
                'size_multiplier': 0.1,  # 파일 크기당 TTL 증가 (MB당 0.1초)
                'access_boost': 300,  # 접근 시 TTL 증가 (5분)
                'max_ttl': 86400  # 최대 24시간
            },
            'file_meta': {
                'base_ttl': 1800,  # 기본 30분
                'size_multiplier': 0.05,
                'access_boost': 150,
                'max_ttl': 7200
            },
            'file_stats': {
                'base_ttl': 600,  # 기본 10분
                'size_multiplier': 0.02,
                'access_boost': 60,
                'max_ttl': 3600
            }
        }
        
        # Task 7.2: 캐시 워밍 설정
        self.cache_warming = {
            'enabled': True,
            'popular_files_threshold': 10,  # 인기 파일 판단 기준 (접근 횟수)
            'warming_ttl': 7200,  # 캐시 워밍 TTL (2시간)
            'max_warming_files': 100  # 최대 워밍 파일 수
        }
        
        # Task 7.2: LRU 정책 설정
        self.lru_config = {
            'maxmemory_policy': 'allkeys-lru',
            'maxmemory': '2gb',  # 최대 메모리 사용량
            'maxmemory_samples': 5  # LRU 샘플링 수
        }
    
    def _calculate_dynamic_ttl(self, cache_type: str, file_size_mb: float = 0, 
                              access_count: int = 0) -> int:
        """
        Task 7.2: 파일 크기와 접근 빈도에 따른 동적 TTL 계산
        
        Args:
            cache_type: 캐시 타입 (file_info, file_meta, file_stats)
            file_size_mb: 파일 크기 (MB)
            access_count: 접근 횟수
            
        Returns:
            계산된 TTL (초)
        """
        policy = self.ttl_policies.get(cache_type, self.ttl_policies['file_info'])
        
        # 기본 TTL
        ttl = policy['base_ttl']
        
        # 파일 크기에 따른 TTL 증가
        size_boost = file_size_mb * policy['size_multiplier']
        ttl += int(size_boost)
        
        # 접근 빈도에 따른 TTL 증가
        access_boost = min(access_count * policy['access_boost'], 
                          policy['max_ttl'] // 2)
        ttl += access_boost
        
        # 최대 TTL 제한
        ttl = min(ttl, policy['max_ttl'])
        
        return max(ttl, 60)  # 최소 1분
    
    async def _get_access_count(self, file_uuid: str) -> int:
        """
        파일 접근 횟수 조회
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            접근 횟수
        """
        try:
            access_key = f"file:access:{file_uuid}"
            count = await self.redis_manager.execute_with_retry(
                self.client.get, access_key
            )
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"접근 횟수 조회 실패: {e}")
            return 0
    
    async def _increment_access_count(self, file_uuid: str) -> int:
        """
        파일 접근 횟수 증가
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            증가된 접근 횟수
        """
        try:
            access_key = f"file:access:{file_uuid}"
            count = await self.redis_manager.execute_with_retry(
                self.client.incr, access_key
            )
            # 접근 횟수는 24시간 동안 유지
            await self.redis_manager.execute_with_retry(
                self.client.expire, access_key, 86400
            )
            return count
        except Exception as e:
            logger.error(f"접근 횟수 증가 실패: {e}")
            return 0
    
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
    
    # Task 7.2: 동적 TTL을 적용한 파일 정보 캐싱
    async def get_file_info(self, file_uuid: str) -> Optional[Dict[str, Any]]:
        """
        파일 정보 캐시 조회 (접근 횟수 증가 포함)
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            파일 정보 (캐시된 경우)
        """
        cache_key = f"file:info:{file_uuid}"
        file_info = await self.get(cache_key)
        
        if file_info:
            # 접근 횟수 증가
            await self._increment_access_count(file_uuid)
            
            # 캐시 히트 시 TTL 연장 (접근 부스트 적용)
            access_count = await self._get_access_count(file_uuid)
            file_size_mb = file_info.get('file_size', 0) / (1024 * 1024)  # MB로 변환
            new_ttl = self._calculate_dynamic_ttl('file_info', file_size_mb, 
                                                access_count)
            await self.expire(cache_key, new_ttl)
            
            logger.info(f"파일 정보 캐시 히트: {file_uuid}, TTL 연장: {new_ttl}초")
        
        return file_info
    
    async def set_file_info(self, file_uuid: str, file_info: Dict[str, Any], 
                           ttl: int = None) -> bool:
        """
        파일 정보 캐시 저장 (동적 TTL 적용)
        
        Args:
            file_uuid: 파일 UUID
            file_info: 파일 정보
            ttl: 만료 시간 (초, None이면 동적 계산)
            
        Returns:
            저장 성공 여부
        """
        cache_key = f"file:info:{file_uuid}"
        
        # Task 7.2: 동적 TTL 계산
        if ttl is None:
            file_size_mb = file_info.get('file_size', 0) / (1024 * 1024)  # MB로 변환
            access_count = await self._get_access_count(file_uuid)
            ttl = self._calculate_dynamic_ttl('file_info', file_size_mb, 
                                            access_count)
        
        success = await self.set(cache_key, file_info, ttl)
        if success:
            logger.info(f"파일 정보 캐시 저장: {file_uuid}, TTL: {ttl}초")
        
        return success
    
    # Task 7.2: 캐시 워밍 기능
    async def warm_popular_files(self, file_list: List[Dict[str, Any]]) -> int:
        """
        인기 파일 사전 캐싱 (캐시 워밍)
        
        Args:
            file_list: 파일 정보 목록
            
        Returns:
            워밍된 파일 수
        """
        if not self.cache_warming['enabled']:
            return 0
        
        warmed_count = 0
        warming_ttl = self.cache_warming['warming_ttl']
        
        for file_info in file_list[:self.cache_warming['max_warming_files']]:
            file_uuid = file_info.get('uuid')
            access_count = await self._get_access_count(file_uuid)
            
            # 인기 파일 판단 (접근 횟수 기준)
            if access_count >= self.cache_warming['popular_files_threshold']:
                success = await self.set_file_info(file_uuid, file_info, warming_ttl)
                if success:
                    warmed_count += 1
                    logger.info(f"캐시 워밍 완료: {file_uuid}")
        
        logger.info(f"캐시 워밍 완료: {warmed_count}개 파일")
        return warmed_count
    
    # Task 7.2: LRU 정책 설정
    async def configure_lru_policy(self) -> bool:
        """
        Redis LRU 정책 설정
        
        Returns:
            설정 성공 여부
        """
        try:
            # maxmemory-policy 설정
            await self.redis_manager.execute_with_retry(
                self.client.config_set, 'maxmemory-policy', 
                self.lru_config['maxmemory_policy']
            )
            
            # maxmemory 설정 (바이트 단위)
            maxmemory_bytes = self._parse_memory_size(self.lru_config['maxmemory'])
            await self.redis_manager.execute_with_retry(
                self.client.config_set, 'maxmemory', str(maxmemory_bytes)
            )
            
            # maxmemory-samples 설정
            await self.redis_manager.execute_with_retry(
                self.client.config_set, 'maxmemory-samples', 
                str(self.lru_config['maxmemory_samples'])
            )
            
            logger.info(f"LRU 정책 설정 완료: {self.lru_config['maxmemory_policy']}")
            return True
            
        except Exception as e:
            logger.error(f"LRU 정책 설정 실패: {e}")
            return False
    
    def _parse_memory_size(self, size_str: str) -> int:
        """
        메모리 크기 문자열을 바이트로 변환
        
        Args:
            size_str: 메모리 크기 문자열 (예: "2gb", "512mb")
            
        Returns:
            바이트 단위 크기
        """
        size_str = size_str.lower()
        if size_str.endswith('gb'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        elif size_str.endswith('mb'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('kb'):
            return int(float(size_str[:-2]) * 1024)
        else:
            return int(size_str)
    
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
    
    async def set_upload_stats(self, client_ip: str, stats: Dict[str, Any], 
                              ttl: int = 300) -> bool:
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
    
    async def increment_counter(self, key: str, amount: int = 1, 
                               expire: int = 3600) -> Optional[int]:
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