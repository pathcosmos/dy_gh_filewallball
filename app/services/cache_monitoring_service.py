"""
캐시 성능 모니터링 및 메트릭 수집 서비스 모듈
Task 7.4: 캐시 성능 모니터링 및 메트릭 수집 구현
Prometheus 메트릭 노출 및 Grafana 대시보드 지원
"""

import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.cache_service import CacheService
from app.services.redis_connection_manager import get_redis_manager

logger = logging.getLogger(__name__)


class CacheMonitoringService:
    """캐시 성능 모니터링 및 메트릭 수집 서비스 클래스 - Task 7.4"""

    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.client = self.redis_manager.get_client()
        self.cache_service = CacheService()

        # Task 7.4: 캐시 히트/미스 카운터
        self.cache_hits = defaultdict(int)
        self.cache_misses = defaultdict(int)
        self.cache_operations = defaultdict(int)

        # Task 7.4: 응답 시간 히스토그램
        self.response_times = defaultdict(lambda: deque(maxlen=1000))
        self.slow_queries = deque(maxlen=100)

        # Task 7.4: 메모리 사용량 추적
        self.memory_usage_history = deque(maxlen=1440)  # 24시간 (1분 간격)
        self.key_count_history = deque(maxlen=1440)

        # Task 7.4: 성능 임계값 설정
        self.thresholds = {
            "slow_query_threshold": 100,  # 밀리초
            "cache_hit_rate_minimum": 80.0,  # 퍼센트
            "memory_usage_warning": 80.0,  # 퍼센트
            "key_count_warning": 10000,
        }

        # Task 7.4: 알림 상태
        self.alerts = {
            "low_hit_rate": False,
            "high_memory_usage": False,
            "slow_queries": False,
            "high_key_count": False,
        }

        # Task 7.4: 메트릭 수집 간격
        self.metrics_interval = 60  # 초
        self.last_metrics_collection = time.time()

    async def record_cache_hit(self, cache_type: str = "default"):
        """캐시 히트 기록"""
        self.cache_hits[cache_type] += 1
        self.cache_operations[cache_type] += 1

    async def record_cache_miss(self, cache_type: str = "default"):
        """캐시 미스 기록"""
        self.cache_misses[cache_type] += 1
        self.cache_operations[cache_type] += 1

    async def record_response_time(self, operation: str, response_time_ms: float):
        """응답 시간 기록"""
        self.response_times[operation].append(response_time_ms)

        # 느린 쿼리 기록
        if response_time_ms > self.thresholds["slow_query_threshold"]:
            slow_query = {
                "operation": operation,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.slow_queries.append(slow_query)

            if not self.alerts["slow_queries"]:
                self.alerts["slow_queries"] = True
                logger.warning(f"느린 쿼리 감지: {operation} ({response_time_ms}ms)")

    async def collect_memory_metrics(self):
        """메모리 사용량 메트릭 수집"""
        try:
            # Redis INFO 명령어로 메모리 정보 조회
            info = await self.redis_manager.execute_with_retry(
                self.client.info, "memory"
            )

            # 메모리 사용량 (바이트)
            used_memory = int(info.get("used_memory", 0))
            used_memory_peak = int(info.get("used_memory_peak", 0))
            maxmemory = int(info.get("maxmemory", 0))

            # 키 개수
            db_info = await self.redis_manager.execute_with_retry(
                self.client.info, "keyspace"
            )

            total_keys = 0
            for db_key, db_data in db_info.items():
                if db_key.startswith("db"):
                    keys_match = db_data.split(",")[0]
                    keys_count = int(keys_match.split("=")[1])
                    total_keys += keys_count

            # 메모리 사용률 계산
            memory_usage_percent = 0
            if maxmemory > 0:
                memory_usage_percent = (used_memory / maxmemory) * 100

            # 히스토리 기록
            memory_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "used_memory": used_memory,
                "used_memory_peak": used_memory_peak,
                "maxmemory": maxmemory,
                "memory_usage_percent": memory_usage_percent,
                "total_keys": total_keys,
            }

            self.memory_usage_history.append(memory_record)
            self.key_count_history.append(
                {"timestamp": datetime.utcnow().isoformat(), "total_keys": total_keys}
            )

            # 알림 체크
            await self._check_memory_alerts(memory_usage_percent, total_keys)

            return memory_record

        except Exception as e:
            logger.error(f"메모리 메트릭 수집 실패: {e}")
            return {}

    async def _check_memory_alerts(self, memory_usage_percent: float, total_keys: int):
        """메모리 관련 알림 체크"""
        # 높은 메모리 사용률 알림
        if memory_usage_percent > self.thresholds["memory_usage_warning"]:
            if not self.alerts["high_memory_usage"]:
                self.alerts["high_memory_usage"] = True
                logger.warning(f"높은 메모리 사용률: {memory_usage_percent:.1f}%")
        else:
            self.alerts["high_memory_usage"] = False

        # 높은 키 개수 알림
        if total_keys > self.thresholds["key_count_warning"]:
            if not self.alerts["high_key_count"]:
                self.alerts["high_key_count"] = True
                logger.warning(f"높은 키 개수: {total_keys}")
        else:
            self.alerts["high_key_count"] = False

    async def get_cache_hit_rate(self, cache_type: str = "default") -> float:
        """캐시 히트율 계산"""
        hits = self.cache_hits[cache_type]
        misses = self.cache_misses[cache_type]
        total = hits + misses

        if total == 0:
            return 0.0

        hit_rate = (hits / total) * 100

        # 낮은 히트율 알림
        if hit_rate < self.thresholds["cache_hit_rate_minimum"]:
            if not self.alerts["low_hit_rate"]:
                self.alerts["low_hit_rate"] = True
                logger.warning(f"낮은 캐시 히트율: {hit_rate:.1f}%")
        else:
            self.alerts["low_hit_rate"] = False

        return hit_rate

    async def get_average_response_time(self, operation: str = "default") -> float:
        """평균 응답 시간 계산"""
        times = self.response_times[operation]
        if not times:
            return 0.0

        return sum(times) / len(times)

    async def get_percentile_response_time(
        self, operation: str = "default", percentile: int = 95
    ) -> float:
        """백분위 응답 시간 계산"""
        times = sorted(self.response_times[operation])
        if not times:
            return 0.0

        index = int((percentile / 100) * len(times))
        return times[index] if index < len(times) else times[-1]

    async def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """느린 쿼리 목록 조회"""
        return list(self.slow_queries)[-limit:]

    async def get_memory_usage_trend(self, hours: int = 24) -> List[Dict]:
        """메모리 사용량 트렌드 조회"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        trend_data = []
        for record in self.memory_usage_history:
            record_time = datetime.fromisoformat(record["timestamp"])
            if record_time >= cutoff_time:
                trend_data.append(record)

        return trend_data

    async def get_key_count_trend(self, hours: int = 24) -> List[Dict]:
        """키 개수 트렌드 조회"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        trend_data = []
        for record in self.key_count_history:
            record_time = datetime.fromisoformat(record["timestamp"])
            if record_time >= cutoff_time:
                trend_data.append(record)

        return trend_data

    async def generate_prometheus_metrics(self) -> str:
        """
        Prometheus 형식 메트릭 생성

        Returns:
            Prometheus 메트릭 문자열
        """
        try:
            metrics = []

            # 캐시 히트율 메트릭
            for cache_type in self.cache_hits.keys():
                hit_rate = await self.get_cache_hit_rate(cache_type)
                metrics.append(f'cache_hit_rate{{type="{cache_type}"}} {hit_rate}')

            # 캐시 히트/미스 카운터
            for cache_type, hits in self.cache_hits.items():
                metrics.append(f'cache_hits_total{{type="{cache_type}"}} {hits}')

            for cache_type, misses in self.cache_misses.items():
                metrics.append(f'cache_misses_total{{type="{cache_type}"}} {misses}')

            # 응답 시간 메트릭
            for operation in self.response_times.keys():
                avg_time = await self.get_average_response_time(operation)
                p95_time = await self.get_percentile_response_time(operation, 95)
                p99_time = await self.get_percentile_response_time(operation, 99)

                metrics.append(
                    f'cache_response_time_avg{{operation="{operation}"}} {avg_time}'
                )
                metrics.append(
                    f'cache_response_time_p95{{operation="{operation}"}} {p95_time}'
                )
                metrics.append(
                    f'cache_response_time_p99{{operation="{operation}"}} {p99_time}'
                )

            # 메모리 사용량 메트릭
            memory_record = await self.collect_memory_metrics()
            if memory_record:
                metrics.append(
                    f'cache_memory_used_bytes {memory_record["used_memory"]}'
                )
                metrics.append(
                    f'cache_memory_peak_bytes {memory_record["used_memory_peak"]}'
                )
                metrics.append(f'cache_memory_max_bytes {memory_record["maxmemory"]}')
                metrics.append(
                    f'cache_memory_usage_percent {memory_record["memory_usage_percent"]}'
                )
                metrics.append(f'cache_keys_total {memory_record["total_keys"]}')

            # 알림 상태 메트릭
            for alert_name, is_active in self.alerts.items():
                metrics.append(
                    f'cache_alert_active{{alert="{alert_name}"}} {1 if is_active else 0}'
                )

            # 느린 쿼리 개수
            slow_query_count = len(self.slow_queries)
            metrics.append(f"cache_slow_queries_total {slow_query_count}")

            # Redis 연결 상태
            connection_info = self.redis_manager.get_connection_info()
            circuit_breaker_state = (
                1 if connection_info.get("circuit_breaker_state") == "open" else 0
            )
            metrics.append(f"cache_circuit_breaker_open {circuit_breaker_state}")

            return "\n".join(metrics)

        except Exception as e:
            logger.error(f"Prometheus 메트릭 생성 실패: {e}")
            return f"# Error generating metrics: {e}"

    async def generate_cache_efficiency_report(self) -> Dict[str, Any]:
        """
        캐시 효율성 리포트 생성

        Returns:
            캐시 효율성 리포트
        """
        try:
            # 기본 통계
            total_hits = sum(self.cache_hits.values())
            total_misses = sum(self.cache_misses.values())
            total_operations = total_hits + total_misses
            overall_hit_rate = (
                (total_hits / total_operations * 100) if total_operations > 0 else 0
            )

            # 응답 시간 통계
            response_time_stats = {}
            for operation in self.response_times.keys():
                avg_time = await self.get_average_response_time(operation)
                p95_time = await self.get_percentile_response_time(operation, 95)
                p99_time = await self.get_percentile_response_time(operation, 99)

                response_time_stats[operation] = {
                    "average_ms": avg_time,
                    "p95_ms": p95_time,
                    "p99_ms": p99_time,
                    "sample_count": len(self.response_times[operation]),
                }

            # 메모리 통계
            memory_record = await self.collect_memory_metrics()

            # 알림 상태
            active_alerts = [
                name for name, is_active in self.alerts.items() if is_active
            ]

            # 성능 등급
            performance_grade = "A"
            if overall_hit_rate < 90:
                performance_grade = "B"
            if overall_hit_rate < 80:
                performance_grade = "C"
            if overall_hit_rate < 70:
                performance_grade = "D"

            if active_alerts:
                performance_grade = "F"

            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "performance_grade": performance_grade,
                "overall_hit_rate": overall_hit_rate,
                "total_operations": total_operations,
                "total_hits": total_hits,
                "total_misses": total_misses,
                "response_time_stats": response_time_stats,
                "memory_stats": memory_record,
                "active_alerts": active_alerts,
                "slow_queries_count": len(self.slow_queries),
                "cache_type_stats": {
                    cache_type: {
                        "hits": hits,
                        "misses": self.cache_misses[cache_type],
                        "hit_rate": await self.get_cache_hit_rate(cache_type),
                    }
                    for cache_type, hits in self.cache_hits.items()
                },
            }

            return report

        except Exception as e:
            logger.error(f"캐시 효율성 리포트 생성 실패: {e}")
            return {"error": str(e)}

    async def reset_metrics(self):
        """메트릭 초기화"""
        self.cache_hits.clear()
        self.cache_misses.clear()
        self.cache_operations.clear()
        self.response_times.clear()
        self.slow_queries.clear()
        self.memory_usage_history.clear()
        self.key_count_history.clear()

        for alert in self.alerts:
            self.alerts[alert] = False

        logger.info("캐시 모니터링 메트릭 초기화 완료")

    async def health_check(self) -> Dict[str, Any]:
        """
        캐시 모니터링 서비스 헬스체크

        Returns:
            헬스체크 결과
        """
        try:
            # 메트릭 수집 테스트
            memory_record = await self.collect_memory_metrics()
            hit_rate = await self.get_cache_hit_rate()

            # 알림 상태 확인
            active_alerts = [
                name for name, is_active in self.alerts.items() if is_active
            ]

            return {
                "status": "healthy" if not active_alerts else "warning",
                "memory_metrics_collected": bool(memory_record),
                "hit_rate_calculated": hit_rate >= 0,
                "active_alerts": active_alerts,
                "total_operations": sum(self.cache_operations.values()),
                "slow_queries_count": len(self.slow_queries),
            }

        except Exception as e:
            logger.error(f"캐시 모니터링 서비스 헬스체크 실패: {e}")
            return {"status": "unhealthy", "error": str(e)}
