"""
백그라운드 작업 서비스
Task 10: 감사 로그 및 백그라운드 작업 시스템
"""

import asyncio
import hashlib
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.async_redis_client import get_async_redis_client
from app.database import get_db
from app.services.audit_log_service import AuditAction, AuditResult, audit_log_service
from app.services.file_preview_service import file_preview_service
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """백그라운드 작업 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """백그라운드 작업 타입"""

    FILE_HASH = "file_hash"
    THUMBNAIL_GENERATION = "thumbnail_generation"
    LOG_AGGREGATION = "log_aggregation"
    CACHE_CLEANUP = "cache_cleanup"
    AUDIT_LOG_CLEANUP = "audit_log_cleanup"
    FILE_CLEANUP = "file_cleanup"


class BackgroundTaskService:
    """백그라운드 작업 관리 서비스"""

    def __init__(self):
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.max_concurrent_tasks = 10
        self.task_timeout = 300  # 5분

    async def submit_task(
        self,
        task_type: TaskType,
        task_data: Dict[str, Any],
        background_tasks: BackgroundTasks,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,
    ) -> str:
        """백그라운드 작업 제출"""
        try:
            # 작업 ID 생성
            task_id = (
                f"{task_type.value}_{int(time.time())}_{hash(str(task_data)) % 10000}"
            )

            # 작업 정보 구성
            task_info = {
                "task_id": task_id,
                "task_type": task_type.value,
                "task_data": task_data,
                "status": TaskStatus.PENDING.value,
                "created_at": datetime.now().isoformat(),
                "user_id": user_id,
                "user_ip": user_ip,
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
                "duration_ms": None,
            }

            # 활성 작업에 추가
            self.active_tasks[task_id] = task_info

            # Redis에 작업 정보 저장
            await self._save_task_info(task_info)

            # 백그라운드 작업 실행
            if task_type == TaskType.FILE_HASH:
                background_tasks.add_task(
                    self._calculate_file_hash_task, task_id, task_data
                )
            elif task_type == TaskType.THUMBNAIL_GENERATION:
                background_tasks.add_task(
                    self._generate_thumbnail_task, task_id, task_data
                )
            elif task_type == TaskType.LOG_AGGREGATION:
                background_tasks.add_task(self._aggregate_logs_task, task_id, task_data)
            elif task_type == TaskType.CACHE_CLEANUP:
                background_tasks.add_task(self._cleanup_cache_task, task_id, task_data)
            elif task_type == TaskType.AUDIT_LOG_CLEANUP:
                background_tasks.add_task(
                    self._cleanup_audit_logs_task, task_id, task_data
                )
            elif task_type == TaskType.FILE_CLEANUP:
                background_tasks.add_task(self._cleanup_files_task, task_id, task_data)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.CREATE,
                resource_type="background_task",
                resource_id=task_id,
                user_id=user_id,
                user_ip=user_ip,
                result=AuditResult.SUCCESS,
                details={"task_type": task_type.value, "task_data": task_data},
            )

            logger.info(f"백그라운드 작업 제출됨: {task_id} ({task_type.value})")
            return task_id

        except Exception as e:
            logger.error(f"백그라운드 작업 제출 실패: {e}")

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.CREATE,
                resource_type="background_task",
                user_id=user_id,
                user_ip=user_ip,
                result=AuditResult.FAILED,
                error_message=str(e),
                details={"task_type": task_type.value, "task_data": task_data},
            )

            raise

    async def _calculate_file_hash_task(self, task_id: str, task_data: Dict[str, Any]):
        """파일 해시 계산 작업"""
        start_time = time.time()

        try:
            # 작업 상태 업데이트
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            file_path = Path(task_data.get("file_path"))
            file_id = task_data.get("file_id")

            if not file_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

            # SHA-256 해시 계산
            hash_sha256 = hashlib.sha256()
            chunk_size = 8192

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_sha256.update(chunk)

            file_hash = hash_sha256.hexdigest()

            # Redis에 해시 저장
            redis_client = await get_async_redis_client()
            await redis_client.set_with_ttl(
                f"file_hash:{file_id}", file_hash, 86400 * 7  # 7일
            )

            duration = (time.time() - start_time) * 1000

            # 작업 완료
            await self._complete_task(
                task_id,
                {"file_hash": file_hash, "file_size": file_path.stat().st_size},
                duration,
            )

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.UPDATE,
                resource_type="file",
                resource_id=file_id,
                result=AuditResult.SUCCESS,
                details={"operation": "hash_calculation", "file_hash": file_hash},
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            await self._fail_task(task_id, str(e), duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.UPDATE,
                resource_type="file",
                resource_id=task_data.get("file_id"),
                result=AuditResult.FAILED,
                error_message=str(e),
                duration_ms=duration,
            )

    async def _generate_thumbnail_task(self, task_id: str, task_data: Dict[str, Any]):
        """썸네일 생성 작업"""
        start_time = time.time()

        try:
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            file_path = Path(task_data.get("file_path"))
            file_id = task_data.get("file_id")
            size = task_data.get("size", "medium")
            format = task_data.get("format", "webp")

            if not file_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

            # 썸네일 생성
            thumbnail_path = await file_preview_service.generate_thumbnail(
                file_path, size, format
            )

            if thumbnail_path:
                # 썸네일 캐시에 저장
                await file_preview_service.cache_thumbnail(
                    file_id, thumbnail_path, size
                )

                duration = (time.time() - start_time) * 1000

                await self._complete_task(
                    task_id,
                    {
                        "thumbnail_path": str(thumbnail_path),
                        "size": size,
                        "format": format,
                    },
                    duration,
                )

                # 감사 로그 기록
                await audit_log_service.log_audit_event(
                    action=AuditAction.UPDATE,
                    resource_type="file",
                    resource_id=file_id,
                    result=AuditResult.SUCCESS,
                    details={
                        "operation": "thumbnail_generation",
                        "thumbnail_path": str(thumbnail_path),
                    },
                    duration_ms=duration,
                )
            else:
                raise Exception("썸네일 생성에 실패했습니다")

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            await self._fail_task(task_id, str(e), duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.UPDATE,
                resource_type="file",
                resource_id=task_data.get("file_id"),
                result=AuditResult.FAILED,
                error_message=str(e),
                duration_ms=duration,
            )

    async def _aggregate_logs_task(self, task_id: str, task_data: Dict[str, Any]):
        """로그 집계 작업"""
        start_time = time.time()

        try:
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            days = task_data.get("days", 30)

            # 감사 로그 통계 조회
            stats = await audit_log_service.get_audit_statistics(days)

            duration = (time.time() - start_time) * 1000

            await self._complete_task(task_id, stats, duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="audit_log",
                result=AuditResult.SUCCESS,
                details={"operation": "log_aggregation", "days": days, "stats": stats},
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            await self._fail_task(task_id, str(e), duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="audit_log",
                result=AuditResult.FAILED,
                error_message=str(e),
                duration_ms=duration,
            )

    async def _cleanup_cache_task(self, task_id: str, task_data: Dict[str, Any]):
        """캐시 정리 작업"""
        start_time = time.time()

        try:
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            # Redis 캐시 정리
            redis_client = await get_async_redis_client()

            # 만료된 키들 조회 및 삭제
            pattern = task_data.get("pattern", "*")
            keys = await redis_client.keys(pattern)

            deleted_count = 0
            for key in keys:
                ttl = await redis_client.ttl(key)
                if ttl == -1:  # TTL이 설정되지 않은 키
                    await redis_client.delete(key)
                    deleted_count += 1

            duration = (time.time() - start_time) * 1000

            await self._complete_task(
                task_id, {"deleted_keys": deleted_count, "pattern": pattern}, duration
            )

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="cache",
                result=AuditResult.SUCCESS,
                details={"operation": "cache_cleanup", "deleted_keys": deleted_count},
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            await self._fail_task(task_id, str(e), duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="cache",
                result=AuditResult.FAILED,
                error_message=str(e),
                duration_ms=duration,
            )

    async def _cleanup_audit_logs_task(self, task_id: str, task_data: Dict[str, Any]):
        """감사 로그 정리 작업"""
        start_time = time.time()

        try:
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            days = task_data.get("days", 90)

            # 오래된 감사 로그 정리
            cleaned_count = await audit_log_service.cleanup_old_audit_logs(days)

            duration = (time.time() - start_time) * 1000

            await self._complete_task(
                task_id, {"cleaned_logs": cleaned_count, "days": days}, duration
            )

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="audit_log",
                result=AuditResult.SUCCESS,
                details={
                    "operation": "audit_log_cleanup",
                    "cleaned_logs": cleaned_count,
                },
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            await self._fail_task(task_id, str(e), duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="audit_log",
                result=AuditResult.FAILED,
                error_message=str(e),
                duration_ms=duration,
            )

    async def _cleanup_files_task(self, task_id: str, task_data: Dict[str, Any]):
        """파일 정리 작업"""
        start_time = time.time()

        try:
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            days = task_data.get("days", 30)

            # 파일 삭제 서비스에서 정리 작업 수행
            from app.services.file_deletion_service import file_deletion_service

            result = await file_deletion_service.cleanup_old_deleted_files(days)

            duration = (time.time() - start_time) * 1000

            await self._complete_task(task_id, result, duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file",
                result=AuditResult.SUCCESS,
                details={
                    "operation": "file_cleanup",
                    "cleaned_files": result["cleaned_count"],
                },
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            await self._fail_task(task_id, str(e), duration)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file",
                result=AuditResult.FAILED,
                error_message=str(e),
                duration_ms=duration,
            )

    async def _save_task_info(self, task_info: Dict[str, Any]):
        """작업 정보를 Redis에 저장"""
        try:
            redis_client = await get_async_redis_client()
            task_key = f"background_task:{task_info['task_id']}"

            # JSON으로 직렬화하여 저장
            import json

            await redis_client.set_with_ttl(
                task_key, json.dumps(task_info), 86400 * 7  # 7일
            )

        except Exception as e:
            logger.error(f"작업 정보 저장 실패: {e}")

    async def _update_task_status(self, task_id: str, status: TaskStatus):
        """작업 상태 업데이트"""
        try:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = status.value
                self.active_tasks[task_id]["started_at"] = datetime.now().isoformat()

                await self._save_task_info(self.active_tasks[task_id])

        except Exception as e:
            logger.error(f"작업 상태 업데이트 실패: {e}")

    async def _complete_task(
        self, task_id: str, result: Dict[str, Any], duration_ms: float
    ):
        """작업 완료 처리"""
        try:
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                task_info["status"] = TaskStatus.COMPLETED.value
                task_info["completed_at"] = datetime.now().isoformat()
                task_info["result"] = result
                task_info["duration_ms"] = duration_ms

                # 작업 히스토리에 추가
                self.task_history.append(task_info.copy())

                # 활성 작업에서 제거
                del self.active_tasks[task_id]

                await self._save_task_info(task_info)

        except Exception as e:
            logger.error(f"작업 완료 처리 실패: {e}")

    async def _fail_task(self, task_id: str, error: str, duration_ms: float):
        """작업 실패 처리"""
        try:
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                task_info["status"] = TaskStatus.FAILED.value
                task_info["completed_at"] = datetime.now().isoformat()
                task_info["error"] = error
                task_info["duration_ms"] = duration_ms

                # 작업 히스토리에 추가
                self.task_history.append(task_info.copy())

                # 활성 작업에서 제거
                del self.active_tasks[task_id]

                await self._save_task_info(task_info)

        except Exception as e:
            logger.error(f"작업 실패 처리 실패: {e}")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        try:
            # 활성 작업에서 조회
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]

            # Redis에서 조회
            redis_client = await get_async_redis_client()
            task_key = f"background_task:{task_id}"
            task_data = await redis_client.get(task_key)

            if task_data:
                import json

                return json.loads(task_data)

            return None

        except Exception as e:
            logger.error(f"작업 상태 조회 실패: {e}")
            return None

    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """활성 작업 목록 조회"""
        return list(self.active_tasks.values())

    async def get_task_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """작업 히스토리 조회"""
        return self.task_history[-limit:] if self.task_history else []

    async def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""
        try:
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                task_info["status"] = TaskStatus.CANCELLED.value
                task_info["completed_at"] = datetime.now().isoformat()

                # 작업 히스토리에 추가
                self.task_history.append(task_info.copy())

                # 활성 작업에서 제거
                del self.active_tasks[task_id]

                await self._save_task_info(task_info)

                # 감사 로그 기록
                await audit_log_service.log_audit_event(
                    action=AuditAction.DELETE,
                    resource_type="background_task",
                    resource_id=task_id,
                    result=AuditResult.SUCCESS,
                    details={"operation": "task_cancellation"},
                )

                return True

            return False

        except Exception as e:
            logger.error(f"작업 취소 실패: {e}")
            return False


# 전역 인스턴스
background_task_service = BackgroundTaskService()
