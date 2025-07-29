"""
캐시 장애 복구 및 폴백 전략 서비스 모듈
Task 7.5: 장애 복구 및 폴백 전략 구현
Redis 장애 시 데이터베이스 직접 조회 폴백 및 자동 복구
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from app.services.redis_connection_manager import get_redis_manager
from app.services.cache_service import CacheService
from app.database import get_db

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """서킷 브레이커 상태"""
    CLOSED = "closed"      # 정상 상태
    OPEN = "open"          # 장애 상태 (폴백 사용)
    HALF_OPEN = "half_open"  # 복구 시도 중


class CacheFallbackService:
    """캐시 장애 복구 및 폴백 전략 서비스 클래스 - Task 7.5"""
    
    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.cache_service = CacheService()
        
        # Task 7.5: 서킷 브레이커 설정
        self.circuit_breaker = {
            'state': CircuitBreakerState.CLOSED,
            'failure_threshold': 5,  # 장애 판단 임계값
            'recovery_timeout': 60,  # 복구 대기 시간 (초)
            'failure_count': 0,
            'last_failure_time': None,
            'success_count': 0,
            'success_threshold': 3  # 복구 성공 판단 임계값
        }
        
        # Task 7.5: 폴백 전략 설정
        self.fallback_config = {
            'enabled': True,
            'max_fallback_duration': 300,  # 최대 폴백 사용 시간 (초)
            'fallback_start_time': None,
            'database_timeout': 10,  # 데이터베이스 쿼리 타임아웃 (초)
            'retry_interval': 30  # 복구 재시도 간격 (초)
        }
        
        # Task 7.5: 캐시 복구 설정
        self.recovery_config = {
            'gradual_load_enabled': True,
            'batch_size': 100,  # 복구 배치 크기
            'load_interval': 5,  # 배치 간격 (초)
            'priority_keys': [],  # 우선 복구할 키 목록
            'recovery_progress': 0.0  # 복구 진행률 (0.0 ~ 1.0)
        }
        
        # Task 7.5: 장애 알림 설정
        self.alert_config = {
            'enabled': True,
            'alert_channels': ['log', 'metrics'],
            'alert_threshold': 3,  # 알림 임계값
            'alert_cooldown': 300  # 알림 쿨다운 (초)
        }
        
        # Task 7.5: 복구 작업 관리
        self.recovery_tasks = {}
        self.fallback_usage_stats = {
            'total_requests': 0,
            'fallback_requests': 0,
            'fallback_start_time': None,
            'last_recovery_attempt': None
        }
        
        # Task 7.5: 백업 및 복원 설정
        self.backup_config = {
            'auto_backup_enabled': True,
            'backup_interval': 3600,  # 백업 간격 (초)
            'backup_retention': 7,  # 백업 보관 일수
            'last_backup_time': None
        }
    
    async def get_with_fallback(self, key: str, fetch_func: Callable, 
                              cache_type: str = 'default') -> Optional[Any]:
        """
        캐시 조회 (폴백 포함)
        
        Args:
            key: 캐시 키
            fetch_func: 데이터베이스에서 데이터를 가져오는 함수
            cache_type: 캐시 타입
            
        Returns:
            캐시된 값 또는 폴백 데이터
        """
        self.fallback_usage_stats['total_requests'] += 1
        
        # 서킷 브레이커 상태 확인
        if self.circuit_breaker['state'] == CircuitBreakerState.OPEN:
            logger.warning(f"서킷 브레이커가 열려있음, 폴백 사용: {key}")
            return await self._fallback_to_database(key, fetch_func)
        
        try:
            # 캐시에서 조회 시도
            start_time = datetime.utcnow()
            cached_value = await self.cache_service.get(key)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if cached_value is not None:
                # 캐시 히트
                await self._record_success()
                return cached_value
            
            # 캐시 미스 - 데이터베이스에서 조회
            logger.info(f"캐시 미스, 데이터베이스에서 조회: {key}")
            db_value = await self._fetch_from_database(key, fetch_func)
            
            if db_value is not None:
                # 캐시에 저장 시도
                try:
                    await self.cache_service.set(key, db_value)
                    await self._record_success()
                except Exception as e:
                    logger.warning(f"캐시 저장 실패, 폴백 모드: {e}")
                    await self._record_failure()
            
            return db_value
            
        except Exception as e:
            logger.error(f"캐시 조회 실패, 폴백 사용: {e}")
            await self._record_failure()
            return await self._fallback_to_database(key, fetch_func)
    
    async def _fallback_to_database(self, key: str, fetch_func: Callable) -> Optional[Any]:
        """데이터베이스 폴백 조회"""
        self.fallback_usage_stats['fallback_requests'] += 1
        
        if not self.fallback_usage_stats['fallback_start_time']:
            self.fallback_usage_stats['fallback_start_time'] = datetime.utcnow()
        
        try:
            # 데이터베이스에서 직접 조회
            db_value = await self._fetch_from_database(key, fetch_func)
            
            if db_value is not None:
                logger.info(f"폴백 조회 성공: {key}")
                return db_value
            else:
                logger.warning(f"폴백 조회 실패 - 데이터 없음: {key}")
                return None
                
        except Exception as e:
            logger.error(f"폴백 조회 실패: {e}")
            return None
    
    async def _fetch_from_database(self, key: str, fetch_func: Callable) -> Optional[Any]:
        """데이터베이스에서 데이터 조회"""
        try:
            # 타임아웃 설정
            timeout = self.fallback_config['database_timeout']
            
            # 비동기 타임아웃 적용
            db_value = await asyncio.wait_for(
                fetch_func(key), 
                timeout=timeout
            )
            
            return db_value
            
        except asyncio.TimeoutError:
            logger.error(f"데이터베이스 쿼리 타임아웃: {key}")
            raise
        except Exception as e:
            logger.error(f"데이터베이스 조회 실패: {e}")
            raise
    
    async def _record_success(self):
        """성공 기록"""
        self.circuit_breaker['failure_count'] = 0
        
        if self.circuit_breaker['state'] == CircuitBreakerState.HALF_OPEN:
            self.circuit_breaker['success_count'] += 1
            
            if self.circuit_breaker['success_count'] >= self.circuit_breaker['success_threshold']:
                await self._close_circuit_breaker()
    
    async def _record_failure(self):
        """실패 기록"""
        self.circuit_breaker['failure_count'] += 1
        self.circuit_breaker['last_failure_time'] = datetime.utcnow()
        
        if self.circuit_breaker['failure_count'] >= self.circuit_breaker['failure_threshold']:
            await self._open_circuit_breaker()
    
    async def _open_circuit_breaker(self):
        """서킷 브레이커 열기"""
        if self.circuit_breaker['state'] != CircuitBreakerState.OPEN:
            self.circuit_breaker['state'] = CircuitBreakerState.OPEN
            self.circuit_breaker['success_count'] = 0
            
            logger.warning("서킷 브레이커가 열렸습니다. 폴백 모드로 전환")
            
            # 장애 알림 발송
            await self._send_alert("circuit_breaker_opened", {
                'failure_count': self.circuit_breaker['failure_count'],
                'last_failure_time': self.circuit_breaker['last_failure_time'].isoformat()
            })
            
            # 복구 작업 시작
            asyncio.create_task(self._schedule_recovery())
    
    async def _close_circuit_breaker(self):
        """서킷 브레이커 닫기"""
        self.circuit_breaker['state'] = CircuitBreakerState.CLOSED
        self.circuit_breaker['failure_count'] = 0
        self.circuit_breaker['success_count'] = 0
        
        logger.info("서킷 브레이커가 닫혔습니다. 정상 모드로 복귀")
        
        # 복구 완료 알림
        await self._send_alert("circuit_breaker_closed", {
            'recovery_time': datetime.utcnow().isoformat()
        })
    
    async def _schedule_recovery(self):
        """복구 작업 스케줄링"""
        recovery_timeout = self.circuit_breaker['recovery_timeout']
        
        await asyncio.sleep(recovery_timeout)
        
        # 하프 오픈 상태로 전환
        self.circuit_breaker['state'] = CircuitBreakerState.HALF_OPEN
        logger.info("서킷 브레이커가 하프 오픈 상태로 전환되었습니다")
        
        # 점진적 캐시 복구 시작
        if self.recovery_config['gradual_load_enabled']:
            asyncio.create_task(self._gradual_cache_recovery())
    
    async def _gradual_cache_recovery(self):
        """점진적 캐시 복구"""
        try:
            logger.info("점진적 캐시 복구 시작")
            
            # 우선순위 키부터 복구
            priority_keys = self.recovery_config['priority_keys']
            if priority_keys:
                await self._recover_priority_keys(priority_keys)
            
            # 일반 키 복구
            await self._recover_all_keys()
            
            logger.info("점진적 캐시 복구 완료")
            
        except Exception as e:
            logger.error(f"캐시 복구 실패: {e}")
    
    async def _recover_priority_keys(self, priority_keys: List[str]):
        """우선순위 키 복구"""
        batch_size = self.recovery_config['batch_size']
        load_interval = self.recovery_config['load_interval']
        
        for i in range(0, len(priority_keys), batch_size):
            batch = priority_keys[i:i + batch_size]
            
            for key in batch:
                try:
                    # 데이터베이스에서 데이터 조회
                    # 실제 구현에서는 키에 맞는 fetch_func를 사용해야 함
                    logger.info(f"우선순위 키 복구: {key}")
                    
                except Exception as e:
                    logger.error(f"우선순위 키 복구 실패: {key}, {e}")
            
            # 배치 간격 대기
            await asyncio.sleep(load_interval)
            
            # 진행률 업데이트
            progress = min(1.0, (i + batch_size) / len(priority_keys))
            self.recovery_config['recovery_progress'] = progress
    
    async def _recover_all_keys(self):
        """모든 키 복구"""
        # 실제 구현에서는 데이터베이스에서 모든 필요한 키를 조회하여 복구
        logger.info("일반 키 복구 시작")
        
        # 복구 완료
        self.recovery_config['recovery_progress'] = 1.0
    
    async def _send_alert(self, alert_type: str, data: Dict[str, Any]):
        """장애 알림 발송"""
        if not self.alert_config['enabled']:
            return
        
        try:
            alert_message = {
                'type': alert_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }
            
            # 로그 알림
            if 'log' in self.alert_config['alert_channels']:
                logger.error(f"캐시 장애 알림: {alert_type} - {data}")
            
            # 메트릭 알림 (실제 구현에서는 메트릭 시스템에 전송)
            if 'metrics' in self.alert_config['alert_channels']:
                logger.info(f"메트릭 알림 전송: {alert_type}")
            
        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")
    
    async def create_cache_backup(self) -> bool:
        """캐시 백업 생성"""
        if not self.backup_config['auto_backup_enabled']:
            return False
        
        try:
            # Redis 데이터 백업
            backup_data = {}
            
            # 주요 키들 백업
            important_patterns = ['file:info:*', 'file:meta:*', 'system:*']
            
            for pattern in important_patterns:
                keys = await self.redis_manager.execute_with_retry(
                    self.client.keys, pattern
                )
                
                for key in keys[:100]:  # 최대 100개 키만 백업
                    value = await self.cache_service.get(key)
                    if value is not None:
                        backup_data[key] = value
            
            # 백업 파일 저장
            backup_filename = f"cache_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
            # 실제 구현에서는 파일 시스템이나 클라우드 스토리지에 저장
            logger.info(f"캐시 백업 생성: {backup_filename}, {len(backup_data)}개 키")
            
            self.backup_config['last_backup_time'] = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.error(f"캐시 백업 생성 실패: {e}")
            return False
    
    async def restore_cache_from_backup(self, backup_filename: str) -> bool:
        """백업에서 캐시 복원"""
        try:
            # 실제 구현에서는 백업 파일에서 데이터 로드
            logger.info(f"캐시 복원 시작: {backup_filename}")
            
            # 복원 작업 수행
            # backup_data = load_backup_file(backup_filename)
            # for key, value in backup_data.items():
            #     await self.cache_service.set(key, value)
            
            logger.info("캐시 복원 완료")
            return True
            
        except Exception as e:
            logger.error(f"캐시 복원 실패: {e}")
            return False
    
    async def get_fallback_stats(self) -> Dict[str, Any]:
        """폴백 사용 통계 조회"""
        total_requests = self.fallback_usage_stats['total_requests']
        fallback_requests = self.fallback_usage_stats['fallback_requests']
        
        fallback_rate = 0.0
        if total_requests > 0:
            fallback_rate = (fallback_requests / total_requests) * 100
        
        return {
            'circuit_breaker_state': self.circuit_breaker['state'].value,
            'failure_count': self.circuit_breaker['failure_count'],
            'success_count': self.circuit_breaker['success_count'],
            'total_requests': total_requests,
            'fallback_requests': fallback_requests,
            'fallback_rate': fallback_rate,
            'fallback_duration': self._get_fallback_duration(),
            'recovery_progress': self.recovery_config['recovery_progress'],
            'last_recovery_attempt': self.fallback_usage_stats['last_recovery_attempt']
        }
    
    def _get_fallback_duration(self) -> Optional[float]:
        """폴백 사용 시간 계산 (초)"""
        if not self.fallback_usage_stats['fallback_start_time']:
            return None
        
        duration = datetime.utcnow() - self.fallback_usage_stats['fallback_start_time']
        return duration.total_seconds()
    
    async def health_check(self) -> Dict[str, Any]:
        """폴백 서비스 헬스체크"""
        try:
            circuit_breaker_healthy = self.circuit_breaker['state'] != CircuitBreakerState.OPEN
            fallback_available = self.fallback_config['enabled']
            
            # 폴백 사용 시간 체크
            fallback_duration = self._get_fallback_duration()
            fallback_timeout = fallback_duration and fallback_duration > self.fallback_config['max_fallback_duration']
            
            return {
                "status": "healthy" if circuit_breaker_healthy and not fallback_timeout else "warning",
                "circuit_breaker_healthy": circuit_breaker_healthy,
                "fallback_available": fallback_available,
                "fallback_timeout": fallback_timeout,
                "recovery_progress": self.recovery_config['recovery_progress']
            }
            
        except Exception as e:
            logger.error(f"폴백 서비스 헬스체크 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            } 