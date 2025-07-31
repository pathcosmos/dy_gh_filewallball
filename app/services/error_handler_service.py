"""
업로드 에러 처리 및 복구 시스템
"""

import asyncio
import os
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import DisconnectionError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.orm_models import FileInfo, FileUpload
from app.utils.security_utils import generate_uuid


class ErrorType(Enum):
    """에러 타입 정의"""

    VALIDATION_ERROR = "validation_error"
    STORAGE_ERROR = "storage_error"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    DISK_FULL_ERROR = "disk_full_error"
    UNKNOWN_ERROR = "unknown_error"


class RetryableError(Enum):
    """재시도 가능한 에러"""

    NETWORK_ERROR = "network_error"
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    STORAGE_TEMPORARY_ERROR = "storage_temporary_error"


class ErrorHandlerService:
    """업로드 에러 처리 및 복구 서비스"""

    def __init__(self, db_session: Session, base_storage_path: str = "./uploads"):
        self.db_session = db_session
        self.base_storage_path = Path(base_storage_path)
        self.temp_dir = self.base_storage_path / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def handle_upload_error(
        self,
        error: Exception,
        file_uuid: str,
        request: Request,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        업로드 에러 처리

        Args:
            error: 발생한 예외
            file_uuid: 파일 UUID
            request: FastAPI 요청 객체
            context: 추가 컨텍스트 정보

        Returns:
            에러 처리 결과
        """
        try:
            # 1. 에러 타입 분류
            error_type = self._classify_error(error)

            # 2. 에러 로그 기록
            error_info = await self._log_error(
                error, error_type, file_uuid, request, context
            )

            # 3. 임시 파일 정리
            await self._cleanup_temp_files(file_uuid)

            # 4. 데이터베이스 롤백
            await self._rollback_database_changes(file_uuid)

            # 5. 재시도 가능 여부 확인
            is_retryable = self._is_retryable_error(error_type)

            # 6. 적절한 HTTP 상태 코드 및 메시지 생성
            status_code, error_message = self._generate_error_response(
                error_type, error
            )

            return {
                "error_type": error_type.value,
                "error_message": error_message,
                "status_code": status_code,
                "is_retryable": is_retryable,
                "file_uuid": file_uuid,
                "error_id": error_info.get("error_id"),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            # 에러 처리 중 발생한 예외
            print(f"에러 처리 중 추가 예외 발생: {e}")
            return {
                "error_type": ErrorType.UNKNOWN_ERROR.value,
                "error_message": "내부 서버 오류가 발생했습니다.",
                "status_code": 500,
                "is_retryable": False,
                "file_uuid": file_uuid,
                "timestamp": datetime.now().isoformat(),
            }

    def _classify_error(self, error: Exception) -> ErrorType:
        """
        에러 타입 분류

        Args:
            error: 발생한 예외

        Returns:
            에러 타입
        """
        if isinstance(error, HTTPException):
            if error.status_code == 400:
                return ErrorType.VALIDATION_ERROR
            elif error.status_code == 413:
                return ErrorType.STORAGE_ERROR
            elif error.status_code == 507:
                return ErrorType.DISK_FULL_ERROR
            else:
                return ErrorType.UNKNOWN_ERROR

        elif isinstance(error, IntegrityError):
            return ErrorType.DATABASE_ERROR

        elif isinstance(error, (OperationalError, DisconnectionError)):
            return ErrorType.DATABASE_ERROR

        elif isinstance(error, (OSError, IOError)):
            if "No space left on device" in str(error):
                return ErrorType.DISK_FULL_ERROR
            elif "Permission denied" in str(error):
                return ErrorType.PERMISSION_ERROR
            else:
                return ErrorType.STORAGE_ERROR

        elif isinstance(error, ConnectionError):
            return ErrorType.NETWORK_ERROR

        else:
            return ErrorType.UNKNOWN_ERROR

    async def _log_error(
        self,
        error: Exception,
        error_type: ErrorType,
        file_uuid: str,
        request: Request,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        에러 로그 기록

        Args:
            error: 발생한 예외
            error_type: 에러 타입
            file_uuid: 파일 UUID
            request: FastAPI 요청 객체
            context: 추가 컨텍스트 정보

        Returns:
            에러 로그 정보
        """
        try:
            error_id = generate_uuid()

            # 파일 정보 조회
            file_info = (
                self.db_session.query(FileInfo)
                .filter(FileInfo.file_uuid == file_uuid)
                .first()
            )

            if file_info:
                # 업로드 실패 기록
                upload_record = FileUpload(
                    file_id=file_info.id,
                    upload_status="failed",
                    client_ip=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    upload_started_at=datetime.now(),
                )

                self.db_session.add(upload_record)
                self.db_session.commit()
            else:
                # 파일 정보가 없는 경우 로그만 기록
                print(f"파일 정보를 찾을 수 없음: {file_uuid}")
                return {"error_id": generate_uuid()}

            # 에러 상세 정보 로깅
            error_info = {
                "error_id": error_id,
                "file_uuid": file_uuid,
                "error_type": error_type.value,
                "error_message": str(error),
                "error_class": error.__class__.__name__,
                "upload_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
                "timestamp": datetime.now().isoformat(),
                "context": context or {},
            }

            # 로그 파일에 기록
            await self._write_error_log(error_info)

            return error_info

        except Exception as e:
            print(f"에러 로그 기록 실패: {e}")
            return {"error_id": generate_uuid()}

    async def _write_error_log(self, error_info: Dict[str, Any]) -> None:
        """
        에러 로그 파일에 기록

        Args:
            error_info: 에러 정보
        """
        try:
            log_file = self.base_storage_path / "logs" / "upload_errors.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            log_entry = (
                f"[{error_info['timestamp']}] "
                f"ERROR_ID={error_info['error_id']} "
                f"FILE_UUID={error_info['file_uuid']} "
                f"TYPE={error_info['error_type']} "
                f"IP={error_info['upload_ip']} "
                f"MESSAGE={error_info['error_message']}\n"
            )

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)

        except Exception as e:
            print(f"에러 로그 파일 기록 실패: {e}")

    async def _cleanup_temp_files(self, file_uuid: str) -> None:
        """
        임시 파일 정리

        Args:
            file_uuid: 파일 UUID
        """
        try:
            # 임시 디렉토리에서 파일 UUID 관련 파일들 삭제
            for temp_file in self.temp_dir.glob(f"*{file_uuid}*"):
                if temp_file.is_file():
                    temp_file.unlink()
                    print(f"임시 파일 삭제: {temp_file}")

            # 저장 디렉토리에서 부분적으로 저장된 파일 삭제
            uuid_prefix = file_uuid[:2]
            uuid_subprefix = file_uuid[2:4]
            storage_dir = self.base_storage_path / uuid_prefix / uuid_subprefix

            if storage_dir.exists():
                for file_path in storage_dir.glob(f"{file_uuid}*"):
                    if file_path.is_file():
                        file_path.unlink()
                        print(f"부분 저장 파일 삭제: {file_path}")

                # 빈 디렉토리 삭제
                if not any(storage_dir.iterdir()):
                    storage_dir.rmdir()

        except Exception as e:
            print(f"임시 파일 정리 실패: {e}")

    async def _rollback_database_changes(self, file_uuid: str) -> None:
        """
        데이터베이스 변경사항 롤백

        Args:
            file_uuid: 파일 UUID
        """
        try:
            # 파일 정보 삭제
            file_info = (
                self.db_session.query(FileInfo)
                .filter(FileInfo.file_uuid == file_uuid)
                .first()
            )

            if file_info:
                self.db_session.delete(file_info)
                print(f"파일 정보 롤백: {file_uuid}")

            # 트랜잭션 커밋
            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            print(f"데이터베이스 롤백 실패: {e}")

    def _is_retryable_error(self, error_type: ErrorType) -> bool:
        """
        재시도 가능한 에러인지 확인

        Args:
            error_type: 에러 타입

        Returns:
            재시도 가능 여부
        """
        retryable_types = [
            ErrorType.NETWORK_ERROR,
            ErrorType.DATABASE_ERROR,  # 연결 오류의 경우
            ErrorType.STORAGE_ERROR,  # 임시 오류의 경우
        ]

        return error_type in retryable_types

    def _generate_error_response(
        self, error_type: ErrorType, error: Exception
    ) -> tuple:
        """
        에러 응답 생성

        Args:
            error_type: 에러 타입
            error: 발생한 예외

        Returns:
            (상태 코드, 에러 메시지) 튜플
        """
        if error_type == ErrorType.VALIDATION_ERROR:
            return 400, "파일 검증에 실패했습니다. 파일 형식과 크기를 확인해주세요."

        elif error_type == ErrorType.STORAGE_ERROR:
            return 500, "파일 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        elif error_type == ErrorType.DATABASE_ERROR:
            return 500, "데이터베이스 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        elif error_type == ErrorType.NETWORK_ERROR:
            return 503, "네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        elif error_type == ErrorType.PERMISSION_ERROR:
            return 500, "파일 시스템 권한 오류가 발생했습니다."

        elif error_type == ErrorType.DISK_FULL_ERROR:
            return 507, "저장소 용량이 부족합니다. 관리자에게 문의해주세요."

        else:
            return 500, "알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

    def _get_client_ip(self, request: Request) -> str:
        """
        클라이언트 IP 주소 추출

        Args:
            request: FastAPI 요청 객체

        Returns:
            클라이언트 IP 주소
        """
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def get_error_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        에러 통계 조회

        Args:
            days: 조회할 일수

        Returns:
            에러 통계 정보
        """
        try:
            from datetime import timedelta

            start_date = datetime.now() - timedelta(days=days)

            # 실패한 업로드 수
            failed_uploads = (
                self.db_session.query(FileUpload)
                .filter(
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_status == "failed",
                )
                .count()
            )

            # 에러 타입별 통계
            error_types = (
                self.db_session.query(FileUpload.error_type, func.count(FileUpload.id))
                .filter(
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_status == "failed",
                )
                .group_by(FileUpload.error_type)
                .all()
            )

            # 재시도 가능한 에러 수
            retryable_errors = sum(
                count
                for error_type, count in error_types
                if error_type in [e.value for e in RetryableError]
            )

            return {
                "period_days": days,
                "total_failed_uploads": failed_uploads,
                "error_types": dict(error_types),
                "retryable_errors": retryable_errors,
                "non_retryable_errors": failed_uploads - retryable_errors,
            }

        except Exception as e:
            print(f"에러 통계 조회 실패: {e}")
            return {}

    async def cleanup_old_error_logs(self, days: int = 90) -> int:
        """
        오래된 에러 로그 정리

        Args:
            days: 보관할 일수

        Returns:
            삭제된 로그 파일 수
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0

            # 오래된 업로드 실패 기록 삭제
            old_records = (
                self.db_session.query(FileUpload)
                .filter(
                    FileUpload.upload_time < cutoff_date,
                    FileUpload.upload_status == "failed",
                )
                .all()
            )

            for record in old_records:
                self.db_session.delete(record)
                deleted_count += 1

            self.db_session.commit()

            return deleted_count

        except Exception as e:
            self.db_session.rollback()
            print(f"오래된 에러 로그 정리 실패: {e}")
            return 0
