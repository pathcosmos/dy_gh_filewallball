"""
감사 로그 서비스
Task 10: 감사 로그 및 백그라운드 작업 시스템
"""

import asyncio
import json
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.async_redis_client import get_async_redis_client
from app.database import get_db
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class AuditAction(str, Enum):
    """감사 로그 액션 타입"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    LOGIN = "login"
    LOGOUT = "logout"
    AUTH_FAILED = "auth_failed"
    PERMISSION_DENIED = "permission_denied"
    SYSTEM_ERROR = "system_error"


class AuditResult(str, Enum):
    """감사 로그 결과 타입"""

    SUCCESS = "success"
    FAILED = "failed"
    DENIED = "denied"
    ERROR = "error"


class AuditLogService:
    """구조화된 감사 로그 서비스"""

    def __init__(self):
        self.struct_logger = structlog.get_logger()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # 감사 로그 파일 설정
        self.audit_log_file = self.log_dir / "audit.log"
        self.audit_logger = self._setup_audit_logger()

    def _setup_audit_logger(self):
        """감사 로그 전용 로거 설정"""
        import logging
        from logging.handlers import TimedRotatingFileHandler

        # 감사 로그 로거 생성
        audit_logger = logging.getLogger("audit")
        audit_logger.setLevel(logging.INFO)

        # 기존 핸들러 제거
        for handler in audit_logger.handlers[:]:
            audit_logger.removeHandler(handler)

        try:
            # 로그 디렉토리 생성
            self.log_dir.mkdir(exist_ok=True)

            # 파일 핸들러 추가 (일별 로테이션, 90일 보관)
            file_handler = TimedRotatingFileHandler(
                str(self.audit_log_file),
                when="midnight",
                interval=1,
                backupCount=90,
                encoding="utf-8",
            )
        except PermissionError:
            # 권한 문제가 있는 경우 임시 디렉토리 사용
            import tempfile
            temp_log_file = os.path.join(tempfile.gettempdir(), "audit.log")
            logger.warning(f"Using temporary directory for audit logs: {temp_log_file}")
            
            file_handler = TimedRotatingFileHandler(
                temp_log_file,
                when="midnight",
                interval=1,
                backupCount=90,
                encoding="utf-8",
            )

        # JSON 포맷터 설정
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        file_handler.setFormatter(formatter)
        audit_logger.addHandler(file_handler)

        return audit_logger

    async def log_audit_event(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,
        result: AuditResult = AuditResult.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """감사 이벤트 로깅"""
        try:
            # 감사 로그 데이터 구성
            audit_data = {
                "timestamp": datetime.now().isoformat(),
                "action": action.value,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "user_id": user_id,
                "user_ip": user_ip,
                "result": result.value,
                "duration_ms": duration_ms,
                "request_id": request_id,
                "details": details or {},
            }

            if error_message:
                audit_data["error_message"] = error_message

            # 구조화된 로그 출력
            log_message = json.dumps(audit_data, ensure_ascii=False)

            # 로그 레벨 결정
            if result == AuditResult.SUCCESS:
                self.audit_logger.info(log_message)
            elif result == AuditResult.DENIED:
                self.audit_logger.warning(log_message)
            else:
                self.audit_logger.error(log_message)

            # Redis에 최근 감사 로그 캐시 (최근 1000개)
            await self._cache_audit_log(audit_data)

            # 메트릭 업데이트
            await self._update_audit_metrics(action, result)

        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

    async def _cache_audit_log(self, audit_data: Dict[str, Any]):
        """감사 로그를 Redis에 캐시"""
        try:
            redis_client = await get_async_redis_client()

            # 최근 감사 로그 리스트에 추가
            log_key = "audit_logs:recent"
            log_data = json.dumps(audit_data, ensure_ascii=False)

            # 리스트의 왼쪽에 추가 (최신이 맨 앞)
            await redis_client.lpush(log_key, log_data)

            # 리스트 크기 제한 (최근 1000개만 유지)
            await redis_client.ltrim(log_key, 0, 999)

            # TTL 설정 (7일)
            await redis_client.expire(log_key, 7 * 24 * 3600)

        except Exception as e:
            logger.error(f"감사 로그 캐시 실패: {e}")

    async def _update_audit_metrics(self, action: AuditAction, result: AuditResult):
        """감사 메트릭 업데이트"""
        try:
            from app.middleware.metrics_middleware import record_file_upload_metric

            # 액션별 메트릭 업데이트
            if action == AuditAction.UPLOAD:
                record_file_upload_metric(
                    file_type="audit", status=result.value, user_id="system"
                )
            elif action == AuditAction.DOWNLOAD:
                from app.middleware.metrics_middleware import (
                    record_file_download_metric,
                )

                record_file_download_metric(
                    file_type="audit", status=result.value, user_id="system"
                )

        except Exception as e:
            logger.error(f"감사 메트릭 업데이트 실패: {e}")

    async def get_audit_logs(
        self,
        page: int = 1,
        size: int = 50,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        result: Optional[AuditResult] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        user_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """감사 로그 조회"""
        try:
            # Redis에서 최근 로그 조회
            redis_client = await get_async_redis_client()
            log_key = "audit_logs:recent"

            # 전체 로그 가져오기
            all_logs = await redis_client.lrange(log_key, 0, -1)

            # JSON 파싱
            parsed_logs = []
            for log_str in all_logs:
                try:
                    log_data = json.loads(log_str)
                    parsed_logs.append(log_data)
                except json.JSONDecodeError:
                    continue

            # 필터링
            filtered_logs = self._filter_audit_logs(
                parsed_logs,
                user_id,
                action,
                resource_type,
                result,
                date_from,
                date_to,
                user_ip,
            )

            # 정렬 (최신순)
            filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # 페이지네이션
            total_count = len(filtered_logs)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_logs = filtered_logs[start_idx:end_idx]

            return {
                "logs": paginated_logs,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_count": total_count,
                    "total_pages": (total_count + size - 1) // size,
                },
            }

        except Exception as e:
            logger.error(f"감사 로그 조회 실패: {e}")
            return {
                "logs": [],
                "pagination": {
                    "page": 1,
                    "size": size,
                    "total_count": 0,
                    "total_pages": 0,
                },
            }

    def _filter_audit_logs(
        self,
        logs: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        result: Optional[AuditResult] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        user_ip: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """감사 로그 필터링"""
        filtered_logs = []

        for log in logs:
            # 사용자 ID 필터
            if user_id and log.get("user_id") != user_id:
                continue

            # 액션 필터
            if action and log.get("action") != action.value:
                continue

            # 리소스 타입 필터
            if resource_type and log.get("resource_type") != resource_type:
                continue

            # 결과 필터
            if result and log.get("result") != result.value:
                continue

            # 날짜 범위 필터
            if date_from or date_to:
                log_timestamp = log.get("timestamp")
                if log_timestamp:
                    try:
                        log_date = datetime.fromisoformat(
                            log_timestamp.replace("Z", "+00:00")
                        )

                        if date_from and log_date < date_from:
                            continue
                        if date_to and log_date > date_to:
                            continue
                    except ValueError:
                        continue

            # IP 주소 필터
            if user_ip and log.get("user_ip") != user_ip:
                continue

            filtered_logs.append(log)

        return filtered_logs

    async def get_audit_statistics(
        self, days: int = 30, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """감사 로그 통계 조회"""
        try:
            # Redis에서 최근 로그 조회
            redis_client = await get_async_redis_client()
            log_key = "audit_logs:recent"
            all_logs = await redis_client.lrange(log_key, 0, -1)

            # 날짜 범위 계산
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=days)

            # 통계 데이터 초기화
            stats = {
                "total_events": 0,
                "success_count": 0,
                "failed_count": 0,
                "denied_count": 0,
                "action_breakdown": {},
                "resource_type_breakdown": {},
                "daily_breakdown": {},
                "top_users": {},
                "top_ips": {},
            }

            # 로그 분석
            for log_str in all_logs:
                try:
                    log_data = json.loads(log_str)
                    log_timestamp = log_data.get("timestamp")

                    if log_timestamp:
                        log_date = datetime.fromisoformat(
                            log_timestamp.replace("Z", "+00:00")
                        )

                        # 날짜 범위 체크
                        if log_date < cutoff_date:
                            continue

                        # 사용자 필터
                        if user_id and log_data.get("user_id") != user_id:
                            continue

                        # 기본 통계
                        stats["total_events"] += 1

                        # 결과별 통계
                        result = log_data.get("result", "unknown")
                        if result == "success":
                            stats["success_count"] += 1
                        elif result == "failed":
                            stats["failed_count"] += 1
                        elif result == "denied":
                            stats["denied_count"] += 1

                        # 액션별 통계
                        action = log_data.get("action", "unknown")
                        stats["action_breakdown"][action] = (
                            stats["action_breakdown"].get(action, 0) + 1
                        )

                        # 리소스 타입별 통계
                        resource_type = log_data.get("resource_type", "unknown")
                        stats["resource_type_breakdown"][resource_type] = (
                            stats["resource_type_breakdown"].get(resource_type, 0) + 1
                        )

                        # 일별 통계
                        date_key = log_date.strftime("%Y-%m-%d")
                        stats["daily_breakdown"][date_key] = (
                            stats["daily_breakdown"].get(date_key, 0) + 1
                        )

                        # 사용자별 통계
                        user_id_log = log_data.get("user_id", "anonymous")
                        stats["top_users"][user_id_log] = (
                            stats["top_users"].get(user_id_log, 0) + 1
                        )

                        # IP별 통계
                        user_ip = log_data.get("user_ip", "unknown")
                        stats["top_ips"][user_ip] = stats["top_ips"].get(user_ip, 0) + 1

                except (json.JSONDecodeError, ValueError):
                    continue

            # 상위 사용자/IP 정렬
            stats["top_users"] = dict(
                sorted(stats["top_users"].items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
            )
            stats["top_ips"] = dict(
                sorted(stats["top_ips"].items(), key=lambda x: x[1], reverse=True)[:10]
            )

            return stats

        except Exception as e:
            logger.error(f"감사 로그 통계 조회 실패: {e}")
            return {
                "total_events": 0,
                "success_count": 0,
                "failed_count": 0,
                "denied_count": 0,
                "action_breakdown": {},
                "resource_type_breakdown": {},
                "daily_breakdown": {},
                "top_users": {},
                "top_ips": {},
            }

    async def cleanup_old_audit_logs(self, days: int = 90):
        """오래된 감사 로그 정리"""
        try:
            # Redis에서 오래된 로그 제거
            redis_client = await get_async_redis_client()
            log_key = "audit_logs:recent"

            # 전체 로그 가져오기
            all_logs = await redis_client.lrange(log_key, 0, -1)

            # 날짜 범위 계산
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=days)

            # 유지할 로그만 필터링
            logs_to_keep = []
            for log_str in all_logs:
                try:
                    log_data = json.loads(log_str)
                    log_timestamp = log_data.get("timestamp")

                    if log_timestamp:
                        log_date = datetime.fromisoformat(
                            log_timestamp.replace("Z", "+00:00")
                        )
                        if log_date >= cutoff_date:
                            logs_to_keep.append(log_str)
                except (json.JSONDecodeError, ValueError):
                    continue

            # Redis 업데이트
            await redis_client.delete(log_key)
            if logs_to_keep:
                await redis_client.lpush(log_key, *logs_to_keep)
                await redis_client.expire(log_key, 7 * 24 * 3600)

            return len(all_logs) - len(logs_to_keep)

        except Exception as e:
            logger.error(f"오래된 감사 로그 정리 실패: {e}")
            return 0


# 전역 인스턴스
audit_log_service = AuditLogService()
