"""
파일 삭제 및 정리 서비스
Task 12: 파일 삭제 및 정리 시스템
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.async_redis_client import get_async_redis_client
from app.database import get_db
from app.services.audit_log_service import AuditAction, AuditResult, audit_log_service
from app.services.file_preview_service import file_preview_service
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DeletionType(str, Enum):
    """삭제 타입"""

    SOFT = "soft"  # 소프트 삭제 (deleted_at만 설정)
    HARD = "hard"  # 하드 삭제 (실제 파일 삭제)
    PERMANENT = "permanent"  # 영구 삭제 (백업 없이 완전 삭제)


class FileDeletionService:
    """파일 삭제 및 정리 서비스"""

    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.soft_deleted_retention_days = 30  # 소프트 삭제된 파일 보관 기간

    async def delete_file(
        self,
        file_id: str,
        deletion_type: DeletionType = DeletionType.SOFT,
        backup_before_delete: bool = True,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """파일 삭제"""
        try:
            # Redis에서 파일 정보 조회
            redis_client = await get_async_redis_client()
            file_info_str = await redis_client.get(f"file:{file_id}")

            if not file_info_str:
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_id}")

            file_info = eval(file_info_str)

            # 파일 경로 구성
            saved_filename = file_info["saved_filename"]
            upload_time = datetime.fromisoformat(file_info["upload_time"])
            date_path = upload_time.strftime("%Y/%m/%d")
            file_path = Path("uploads") / date_path / saved_filename

            # 삭제 전 백업 (필요한 경우)
            backup_path = None
            if backup_before_delete and deletion_type != DeletionType.SOFT:
                backup_path = await self._create_backup(file_id, file_path, file_info)

            # 삭제 타입에 따른 처리
            if deletion_type == DeletionType.SOFT:
                result = await self._soft_delete_file(file_id, file_info, reason)
            elif deletion_type == DeletionType.HARD:
                result = await self._hard_delete_file(
                    file_id, file_path, file_info, backup_path
                )
            elif deletion_type == DeletionType.PERMANENT:
                result = await self._permanent_delete_file(
                    file_id, file_path, file_info
                )
            else:
                raise ValueError(f"지원하지 않는 삭제 타입입니다: {deletion_type}")

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file",
                resource_id=file_id,
                user_id=user_id,
                user_ip=user_ip,
                result=AuditResult.SUCCESS,
                details={
                    "deletion_type": deletion_type.value,
                    "filename": file_info["filename"],
                    "backup_created": backup_path is not None,
                    "backup_path": str(backup_path) if backup_path else None,
                    "reason": reason,
                },
            )

            return result

        except Exception as e:
            logger.error(f"파일 삭제 실패: {e}")

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file",
                resource_id=file_id,
                user_id=user_id,
                user_ip=user_ip,
                result=AuditResult.FAILED,
                error_message=str(e),
                details={"deletion_type": deletion_type.value, "reason": reason},
            )

            raise

    async def _soft_delete_file(
        self, file_id: str, file_info: Dict[str, Any], reason: Optional[str]
    ) -> Dict[str, Any]:
        """소프트 삭제 (deleted_at 필드만 설정)"""
        try:
            # 파일 정보에 삭제 정보 추가
            file_info["deleted"] = True
            file_info["deleted_at"] = datetime.now().isoformat()
            file_info["deletion_reason"] = reason

            # Redis에 업데이트된 정보 저장
            redis_client = await get_async_redis_client()
            await redis_client.set_with_ttl(
                f"file:{file_id}", str(file_info), 86400 * 7  # 7일
            )

            # 관련 캐시 무효화
            await self._invalidate_related_caches(file_id)

            return {
                "file_id": file_id,
                "deletion_type": "soft",
                "deleted_at": file_info["deleted_at"],
                "message": "파일이 소프트 삭제되었습니다",
            }

        except Exception as e:
            logger.error(f"소프트 삭제 실패: {e}")
            raise

    async def _hard_delete_file(
        self,
        file_id: str,
        file_path: Path,
        file_info: Dict[str, Any],
        backup_path: Optional[Path],
    ) -> Dict[str, Any]:
        """하드 삭제 (실제 파일 삭제, 백업 유지)"""
        try:
            # 실제 파일 삭제
            if file_path.exists():
                file_path.unlink()
                logger.info(f"파일 삭제됨: {file_path}")

            # 썸네일 삭제
            await self._delete_thumbnails(file_id)

            # Redis에서 파일 정보 삭제
            redis_client = await get_async_redis_client()
            await redis_client.delete(f"file:{file_id}")

            # 관련 캐시 무효화
            await self._invalidate_related_caches(file_id)

            return {
                "file_id": file_id,
                "deletion_type": "hard",
                "file_deleted": file_path.exists() is False,
                "backup_path": str(backup_path) if backup_path else None,
                "message": "파일이 하드 삭제되었습니다",
            }

        except Exception as e:
            logger.error(f"하드 삭제 실패: {e}")
            raise

    async def _permanent_delete_file(
        self, file_id: str, file_path: Path, file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """영구 삭제 (백업 없이 완전 삭제)"""
        try:
            # 실제 파일 삭제
            if file_path.exists():
                file_path.unlink()
                logger.info(f"파일 영구 삭제됨: {file_path}")

            # 썸네일 삭제
            await self._delete_thumbnails(file_id)

            # Redis에서 파일 정보 삭제
            redis_client = await get_async_redis_client()
            await redis_client.delete(f"file:{file_id}")

            # 관련 캐시 무효화
            await self._invalidate_related_caches(file_id)

            return {
                "file_id": file_id,
                "deletion_type": "permanent",
                "file_deleted": file_path.exists() is False,
                "message": "파일이 영구 삭제되었습니다",
            }

        except Exception as e:
            logger.error(f"영구 삭제 실패: {e}")
            raise

    async def _create_backup(
        self, file_id: str, file_path: Path, file_info: Dict[str, Any]
    ) -> Optional[Path]:
        """삭제 전 백업 생성"""
        try:
            if not file_path.exists():
                return None

            # 백업 디렉토리 생성
            backup_date = datetime.now().strftime("%Y/%m/%d")
            backup_dir = self.backup_dir / backup_date
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 백업 파일명 생성
            backup_filename = f"{file_id}_{int(time.time())}_{file_info['filename']}"
            backup_path = backup_dir / backup_filename

            # 파일 복사
            import shutil

            shutil.copy2(file_path, backup_path)

            # 백업 정보 저장
            backup_info = {
                "original_file_id": file_id,
                "original_filename": file_info["filename"],
                "backup_path": str(backup_path),
                "backup_created_at": datetime.now().isoformat(),
                "original_file_info": file_info,
            }

            redis_client = await get_async_redis_client()
            await redis_client.set_with_ttl(
                f"backup:{file_id}", str(backup_info), 86400 * 365  # 1년
            )

            logger.info(f"백업 생성됨: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"백업 생성 실패: {e}")
            return None

    async def _delete_thumbnails(self, file_id: str):
        """썸네일 삭제"""
        try:
            # 썸네일 디렉토리에서 해당 파일의 썸네일 삭제
            thumbnail_dir = Path("thumbnails")
            if thumbnail_dir.exists():
                for thumbnail_file in thumbnail_dir.rglob(f"*{file_id}*"):
                    try:
                        thumbnail_file.unlink()
                        logger.info(f"썸네일 삭제됨: {thumbnail_file}")
                    except Exception as e:
                        logger.warning(f"썸네일 삭제 실패: {e}")

            # 썸네일 캐시 삭제
            redis_client = await get_async_redis_client()
            thumbnail_keys = await redis_client.keys(f"thumbnail:{file_id}:*")
            if thumbnail_keys:
                await redis_client.delete(*thumbnail_keys)

        except Exception as e:
            logger.error(f"썸네일 삭제 실패: {e}")

    async def _invalidate_related_caches(self, file_id: str):
        """관련 캐시 무효화"""
        try:
            redis_client = await get_async_redis_client()

            # 파일 목록 캐시 무효화
            file_list_keys = await redis_client.keys("file_list:*")
            if file_list_keys:
                await redis_client.delete(*file_list_keys)

            # 파일 해시 캐시 삭제
            await redis_client.delete(f"file_hash:{file_id}")

            # 파일 미리보기 캐시 삭제
            preview_keys = await redis_client.keys(f"preview:{file_id}:*")
            if preview_keys:
                await redis_client.delete(*preview_keys)

        except Exception as e:
            logger.error(f"캐시 무효화 실패: {e}")

    async def restore_file(
        self, file_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """소프트 삭제된 파일 복원"""
        try:
            # Redis에서 파일 정보 조회
            redis_client = await get_async_redis_client()
            file_info_str = await redis_client.get(f"file:{file_id}")

            if not file_info_str:
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_id}")

            file_info = eval(file_info_str)

            # 소프트 삭제된 파일인지 확인
            if not file_info.get("deleted", False):
                raise ValueError("삭제되지 않은 파일입니다")

            # 삭제 정보 제거
            file_info.pop("deleted", None)
            file_info.pop("deleted_at", None)
            file_info.pop("deletion_reason", None)

            # Redis에 업데이트된 정보 저장
            await redis_client.set_with_ttl(
                f"file:{file_id}", str(file_info), 86400 * 7  # 7일
            )

            # 관련 캐시 무효화
            await self._invalidate_related_caches(file_id)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.UPDATE,
                resource_type="file",
                resource_id=file_id,
                user_id=user_id,
                result=AuditResult.SUCCESS,
                details={
                    "operation": "file_restore",
                    "filename": file_info["filename"],
                },
            )

            return {
                "file_id": file_id,
                "restored": True,
                "message": "파일이 성공적으로 복원되었습니다",
            }

        except Exception as e:
            logger.error(f"파일 복원 실패: {e}")

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.UPDATE,
                resource_type="file",
                resource_id=file_id,
                user_id=user_id,
                result=AuditResult.FAILED,
                error_message=str(e),
                details={"operation": "file_restore"},
            )

            raise

    async def get_deleted_files(
        self, page: int = 1, size: int = 50, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """삭제된 파일 목록 조회"""
        try:
            # Redis에서 모든 파일 키 조회
            redis_client = await get_async_redis_client()
            file_keys = await redis_client.keys("file:*")

            # 삭제된 파일만 필터링
            deleted_files = []
            for key in file_keys:
                try:
                    file_data = await redis_client.get(key)
                    if file_data:
                        file_info = eval(file_data)

                        # 삭제된 파일인지 확인
                        if file_info.get("deleted", False):
                            # 사용자 필터 적용
                            if user_id and file_info.get("user_id") != user_id:
                                continue

                            deleted_files.append(file_info)

                except Exception as e:
                    logger.warning(f"파일 정보 파싱 실패: {e}")
                    continue

            # 삭제 시간 기준으로 정렬 (최신순)
            deleted_files.sort(
                key=lambda x: datetime.fromisoformat(x.get("deleted_at", "")),
                reverse=True,
            )

            # 페이지네이션 적용
            total_count = len(deleted_files)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_files = deleted_files[start_idx:end_idx]

            return {
                "files": paginated_files,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_count": total_count,
                    "total_pages": (total_count + size - 1) // size,
                    "has_next": page * size < total_count,
                    "has_prev": page > 1,
                },
            }

        except Exception as e:
            logger.error(f"삭제된 파일 목록 조회 실패: {e}")
            return {
                "files": [],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False,
                },
            }

    async def cleanup_old_deleted_files(self, days: int = None) -> Dict[str, Any]:
        """오래된 소프트 삭제 파일 정리"""
        try:
            if days is None:
                days = self.soft_deleted_retention_days

            cutoff_date = datetime.now() - timedelta(days=days)

            # Redis에서 모든 파일 키 조회
            redis_client = await get_async_redis_client()
            file_keys = await redis_client.keys("file:*")

            cleaned_files = []
            for key in file_keys:
                try:
                    file_data = await redis_client.get(key)
                    if file_data:
                        file_info = eval(file_data)

                        # 소프트 삭제된 파일인지 확인
                        if file_info.get("deleted", False):
                            deleted_at = datetime.fromisoformat(
                                file_info.get("deleted_at", "")
                            )

                            # 보관 기간이 지난 파일 처리
                            if deleted_at < cutoff_date:
                                file_id = file_info["file_id"]

                                # 하드 삭제 수행
                                result = await self._hard_delete_file(
                                    file_id,
                                    Path("uploads") / file_info["saved_filename"],
                                    file_info,
                                    None,  # 백업 없이 삭제
                                )

                                cleaned_files.append(
                                    {
                                        "file_id": file_id,
                                        "filename": file_info["filename"],
                                        "deleted_at": file_info["deleted_at"],
                                    }
                                )

                except Exception as e:
                    logger.warning(f"파일 정리 실패: {e}")
                    continue

            return {
                "cleaned_count": len(cleaned_files),
                "cleaned_files": cleaned_files,
                "retention_days": days,
                "message": f"{len(cleaned_files)}개의 오래된 삭제 파일을 정리했습니다",
            }

        except Exception as e:
            logger.error(f"오래된 삭제 파일 정리 실패: {e}")
            return {
                "cleaned_count": 0,
                "cleaned_files": [],
                "retention_days": days,
                "message": "파일 정리에 실패했습니다",
            }

    async def get_backup_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """백업 정보 조회"""
        try:
            redis_client = await get_async_redis_client()
            backup_info_str = await redis_client.get(f"backup:{file_id}")

            if backup_info_str:
                return eval(backup_info_str)

            return None

        except Exception as e:
            logger.error(f"백업 정보 조회 실패: {e}")
            return None

    async def restore_from_backup(
        self, file_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """백업에서 파일 복원"""
        try:
            backup_info = await self.get_backup_info(file_id)

            if not backup_info:
                raise FileNotFoundError(f"백업을 찾을 수 없습니다: {file_id}")

            backup_path = Path(backup_info["backup_path"])
            if not backup_path.exists():
                raise FileNotFoundError(f"백업 파일이 존재하지 않습니다: {backup_path}")

            # 원본 파일 경로 복원
            original_file_info = backup_info["original_file_info"]
            upload_time = datetime.fromisoformat(original_file_info["upload_time"])
            date_path = upload_time.strftime("%Y/%m/%d")
            original_path = (
                Path("uploads") / date_path / original_file_info["saved_filename"]
            )

            # 디렉토리 생성
            original_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일 복원
            import shutil

            shutil.copy2(backup_path, original_path)

            # Redis에 파일 정보 복원
            redis_client = await get_async_redis_client()
            await redis_client.set_with_ttl(
                f"file:{file_id}", str(original_file_info), 86400 * 7  # 7일
            )

            # 관련 캐시 무효화
            await self._invalidate_related_caches(file_id)

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.UPDATE,
                resource_type="file",
                resource_id=file_id,
                user_id=user_id,
                result=AuditResult.SUCCESS,
                details={
                    "operation": "restore_from_backup",
                    "filename": original_file_info["filename"],
                    "backup_path": str(backup_path),
                },
            )

            return {
                "file_id": file_id,
                "restored": True,
                "backup_path": str(backup_path),
                "message": "백업에서 파일이 성공적으로 복원되었습니다",
            }

        except Exception as e:
            logger.error(f"백업에서 파일 복원 실패: {e}")

            # 감사 로그 기록
            await audit_log_service.log_audit_event(
                action=AuditAction.UPDATE,
                resource_type="file",
                resource_id=file_id,
                user_id=user_id,
                result=AuditResult.FAILED,
                error_message=str(e),
                details={"operation": "restore_from_backup"},
            )

            raise


# 전역 인스턴스
file_deletion_service = FileDeletionService()
