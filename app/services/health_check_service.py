"""
헬스체크 서비스
Task 9: Prometheus 메트릭 및 모니터링 시스템
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

# Redis 클라이언트 제거됨
from app.database import get_db
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class HealthCheckService:
    """헬스체크 서비스"""

    def __init__(self):
        self.health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "checks": {},
        }

    async def check_database_health(self) -> Dict[str, Any]:
        """데이터베이스 연결 상태 확인"""
        try:
            start_time = time.time()

            # 데이터베이스 세션 생성
            db = next(get_db())

            # 간단한 쿼리 실행
            result = db.execute(text("SELECT 1"))
            result.fetchone()

            # 연결 종료
            db.close()

            duration = time.time() - start_time

            return {
                "status": "healthy",
                "duration_ms": round(duration * 1000, 2),
                "message": "Database connection successful",
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "duration_ms": 0,
                "message": f"Database connection failed: {str(e)}",
            }

    async def check_redis_health(self) -> Dict[str, Any]:
        """Redis 연결 상태 확인"""
        try:
            start_time = time.time()

            # Redis 클라이언트 가져오기
            redis_client = await get_async_redis_client()

            # PING 명령어로 연결 확인
            pong = await redis_client.ping()

            if not pong:
                raise Exception("Redis PING failed")

            # Redis 정보 가져오기
            info = await redis_client.get_info()

            duration = time.time() - start_time

            return {
                "status": "healthy",
                "duration_ms": round(duration * 1000, 2),
                "message": "Redis connection successful",
                "redis_info": {
                    "version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                },
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "duration_ms": 0,
                "message": f"Redis connection failed: {str(e)}",
            }

    async def check_storage_health(self) -> Dict[str, Any]:
        """스토리지 상태 확인"""
        try:
            start_time = time.time()

            import os
            from pathlib import Path

            # 업로드 디렉토리 확인
            upload_dir = Path("uploads")
            if not upload_dir.exists():
                upload_dir.mkdir(parents=True, exist_ok=True)

            # 디스크 사용량 확인
            total, used, free = self._get_disk_usage(upload_dir)

            # 썸네일 디렉토리 확인
            thumbnail_dir = Path("thumbnails")
            if not thumbnail_dir.exists():
                thumbnail_dir.mkdir(parents=True, exist_ok=True)

            duration = time.time() - start_time

            return {
                "status": "healthy",
                "duration_ms": round(duration * 1000, 2),
                "message": "Storage check successful",
                "storage_info": {
                    "upload_dir_exists": upload_dir.exists(),
                    "thumbnail_dir_exists": thumbnail_dir.exists(),
                    "disk_usage": {
                        "total_gb": round(total / (1024**3), 2),
                        "used_gb": round(used / (1024**3), 2),
                        "free_gb": round(free / (1024**3), 2),
                        "usage_percent": (
                            round((used / total) * 100, 2) if total > 0 else 0
                        ),
                    },
                },
            }

        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                "status": "unhealthy",
                "duration_ms": 0,
                "message": f"Storage check failed: {str(e)}",
            }

    def _get_disk_usage(self, path: Path) -> tuple:
        """디스크 사용량 확인"""
        try:
            import shutil

            total, used, free = shutil.disk_usage(path)
            return total, used, free
        except Exception:
            return 0, 0, 0

    async def check_external_services(self) -> Dict[str, Any]:
        """외부 서비스 상태 확인"""
        try:
            start_time = time.time()

            # 외부 서비스 체크 (예: 외부 API, 서비스 등)
            external_checks = {}

            # 예시: 외부 API 체크
            # try:
            #     import httpx
            #     async with httpx.AsyncClient(timeout=5.0) as client:
            #         response = await client.get("https://httpbin.org/status/200")
            #         external_checks["external_api"] = {
            #             "status": "healthy" if response.status_code == 200 else "unhealthy",
            #             "response_time_ms": response.elapsed.total_seconds() * 1000
            #         }
            # except Exception as e:
            #     external_checks["external_api"] = {
            #         "status": "unhealthy",
            #         "error": str(e)
            #     }

            duration = time.time() - start_time

            return {
                "status": (
                    "healthy"
                    if all(
                        check.get("status") == "healthy"
                        for check in external_checks.values()
                    )
                    else "unhealthy"
                ),
                "duration_ms": round(duration * 1000, 2),
                "message": "External services check completed",
                "services": external_checks,
            }

        except Exception as e:
            logger.error(f"External services health check failed: {e}")
            return {
                "status": "unhealthy",
                "duration_ms": 0,
                "message": f"External services check failed: {str(e)}",
            }

    async def check_application_health(self) -> Dict[str, Any]:
        """애플리케이션 상태 확인"""
        try:
            start_time = time.time()

            # 메모리 사용량 확인
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            # CPU 사용량 확인
            cpu_percent = process.cpu_percent(interval=0.1)

            # 스레드 수 확인
            thread_count = process.num_threads()

            duration = time.time() - start_time

            return {
                "status": "healthy",
                "duration_ms": round(duration * 1000, 2),
                "message": "Application health check successful",
                "application_info": {
                    "memory_usage_mb": round(memory_info.rss / (1024**2), 2),
                    "cpu_percent": round(cpu_percent, 2),
                    "thread_count": thread_count,
                    "process_id": process.pid,
                },
            }

        except Exception as e:
            logger.error(f"Application health check failed: {e}")
            return {
                "status": "unhealthy",
                "duration_ms": 0,
                "message": f"Application health check failed: {str(e)}",
            }

    async def perform_full_health_check(self) -> Dict[str, Any]:
        """전체 헬스체크 수행"""
        try:
            start_time = time.time()

            # 모든 헬스체크 병렬 실행
            checks = await asyncio.gather(
                self.check_database_health(),
                self.check_redis_health(),
                self.check_storage_health(),
                self.check_external_services(),
                self.check_application_health(),
                return_exceptions=True,
            )

            # 결과 정리
            check_results = {
                "database": (
                    checks[0]
                    if not isinstance(checks[0], Exception)
                    else {
                        "status": "unhealthy",
                        "message": f"Database check failed: {str(checks[0])}",
                    }
                ),
                "redis": (
                    checks[1]
                    if not isinstance(checks[1], Exception)
                    else {
                        "status": "unhealthy",
                        "message": f"Redis check failed: {str(checks[1])}",
                    }
                ),
                "storage": (
                    checks[2]
                    if not isinstance(checks[2], Exception)
                    else {
                        "status": "unhealthy",
                        "message": f"Storage check failed: {str(checks[2])}",
                    }
                ),
                "external_services": (
                    checks[3]
                    if not isinstance(checks[3], Exception)
                    else {
                        "status": "unhealthy",
                        "message": f"External services check failed: {str(checks[3])}",
                    }
                ),
                "application": (
                    checks[4]
                    if not isinstance(checks[4], Exception)
                    else {
                        "status": "unhealthy",
                        "message": f"Application check failed: {str(checks[4])}",
                    }
                ),
            }

            # 전체 상태 결정
            all_healthy = all(
                check["status"] == "healthy" for check in check_results.values()
            )

            total_duration = time.time() - start_time

            return {
                "status": "healthy" if all_healthy else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "duration_ms": round(total_duration * 1000, 2),
                "checks": check_results,
                "summary": {
                    "total_checks": len(check_results),
                    "healthy_checks": sum(
                        1
                        for check in check_results.values()
                        if check["status"] == "healthy"
                    ),
                    "unhealthy_checks": sum(
                        1
                        for check in check_results.values()
                        if check["status"] == "unhealthy"
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Full health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "duration_ms": 0,
                "message": f"Health check failed: {str(e)}",
                "checks": {},
                "summary": {
                    "total_checks": 0,
                    "healthy_checks": 0,
                    "unhealthy_checks": 0,
                },
            }

    async def get_health_status(self, detailed: bool = False) -> Dict[str, Any]:
        """헬스체크 상태 조회"""
        if detailed:
            return await self.perform_full_health_check()
        else:
            # 간단한 상태만 확인
            basic_checks = await asyncio.gather(
                self.check_database_health(),
                self.check_redis_health(),
                return_exceptions=True,
            )

            db_healthy = (
                not isinstance(basic_checks[0], Exception)
                and basic_checks[0]["status"] == "healthy"
            )
            redis_healthy = (
                not isinstance(basic_checks[1], Exception)
                and basic_checks[1]["status"] == "healthy"
            )

            return {
                "status": "healthy" if db_healthy and redis_healthy else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
            }


# 전역 인스턴스
health_check_service = HealthCheckService()
