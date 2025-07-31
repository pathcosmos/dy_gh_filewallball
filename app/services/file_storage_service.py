"""
파일 저장 및 중복 관리 서비스
"""

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models.orm_models import FileInfo
from app.utils.security_utils import generate_uuid


class FileStorageService:
    """파일 저장 및 중복 관리 서비스"""

    def __init__(self, db_session: Session, base_storage_path: Optional[str] = None):
        self.db_session = db_session
        # 설정에서 실제 사용할 경로 가져오기
        if base_storage_path is None:
            self.base_storage_path = Path(settings.effective_upload_dir)
        else:
            self.base_storage_path = Path(base_storage_path)

        # 디렉토리 생성
        self.base_storage_path.mkdir(parents=True, exist_ok=True)

    async def save_file(
        self, file: UploadFile, original_filename: str
    ) -> Dict[str, Any]:
        """
        파일 저장 및 중복 검사

        Args:
            file: 업로드된 파일
            original_filename: 원본 파일명

        Returns:
            파일 저장 결과 정보
        """
        try:
            # 1. 파일 내용 읽기 및 MD5 해시 계산
            content = await file.read()
            file_hash = hashlib.md5(content).hexdigest()

            # 2. 중복 파일 검사
            existing_file = self._check_duplicate_file(file_hash)
            if existing_file:
                return {
                    "is_duplicate": True,
                    "file_uuid": existing_file.file_uuid,
                    "message": "동일한 파일이 이미 존재합니다",
                    "existing_file": existing_file,
                }

            # 3. UUID 생성
            file_uuid = generate_uuid()

            # 4. 저장 파일명 생성
            file_extension = Path(original_filename).suffix.lower()
            stored_filename = f"{file_uuid}{file_extension}"

            # 5. 저장 경로 생성 (설정에 따른 구조)
            storage_path = self._create_storage_path(file_uuid, stored_filename)

            # 6. 디스크 용량 체크
            self._check_disk_space(len(content))

            # 7. 디렉토리 생성
            storage_path.parent.mkdir(parents=True, exist_ok=True)

            # 8. 파일 저장
            await self._write_file(storage_path, content)

            # 9. 파일 정보 반환
            return {
                "is_duplicate": False,
                "file_uuid": file_uuid,
                "stored_filename": stored_filename,
                "storage_path": str(storage_path),
                "file_hash": file_hash,
                "file_size": len(content),
                "file_extension": file_extension,
            }

        except Exception as e:
            # 저장 실패 시 임시 파일 정리
            await self._cleanup_failed_upload(file_uuid)
            raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")

    def _check_duplicate_file(self, file_hash: str) -> Optional[FileInfo]:
        """
        중복 파일 검사

        Args:
            file_hash: 파일 MD5 해시

        Returns:
            기존 파일 정보 (중복인 경우)
        """
        try:
            # 데이터베이스에서 동일한 해시를 가진 파일 검색
            existing_file = (
                self.db_session.query(FileInfo)
                .filter(FileInfo.file_hash == file_hash)
                .first()
            )
            return existing_file
        except Exception as e:
            # 데이터베이스 오류 시 로그만 남기고 None 반환
            print(f"중복 파일 검사 중 오류: {e}")
            return None

    def _create_storage_path(self, file_uuid: str, stored_filename: str) -> Path:
        """
        설정에 따른 저장 경로 생성

        Args:
            file_uuid: 파일 UUID
            stored_filename: 저장 파일명

        Returns:
            저장 경로
        """
        storage_structure = settings.storage_structure

        if storage_structure == "date":
            # 날짜 기반 구조 (YYYY/MM/DD)
            current_date = datetime.now()
            date_path = current_date.strftime(settings.storage_date_format)
            storage_path = self.base_storage_path / date_path / stored_filename

        elif storage_structure == "uuid":
            # UUID 기반 계층 구조
            uuid_depth = settings.storage_uuid_depth
            uuid_parts = []

            for i in range(uuid_depth):
                start_idx = i * 2
                end_idx = start_idx + 2
                if end_idx <= len(file_uuid):
                    uuid_parts.append(file_uuid[start_idx:end_idx])
                else:
                    break

            storage_path = self.base_storage_path
            for part in uuid_parts:
                storage_path = storage_path / part
            storage_path = storage_path / stored_filename

        elif storage_structure == "flat":
            # 평면 구조 (모든 파일을 하나의 디렉토리에)
            storage_path = self.base_storage_path / stored_filename

        else:
            # 기본값: UUID 기반 구조
            uuid_prefix = file_uuid[:2]
            uuid_subprefix = file_uuid[2:4]
            storage_path = (
                self.base_storage_path / uuid_prefix / uuid_subprefix / stored_filename
            )

        return storage_path

    def _check_disk_space(self, required_bytes: int) -> None:
        """
        디스크 용량 체크

        Args:
            required_bytes: 필요한 바이트 수

        Raises:
            HTTPException: 용량 부족 시
        """
        try:
            # 현재 디스크 사용량 확인
            total, used, free = shutil.disk_usage(self.base_storage_path)

            # 여유 공간이 필요한 용량보다 작으면 오류
            if free < required_bytes:
                free_mb = free / (1024 * 1024)
                required_mb = required_bytes / (1024 * 1024)
                raise HTTPException(
                    status_code=507,  # Insufficient Storage
                    detail=(
                        f"디스크 용량 부족. 필요: {required_mb:.1f}MB, "
                        f"여유: {free_mb:.1f}MB"
                    ),
                )

        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=500, detail=f"디스크 용량 확인 실패: {str(e)}"
            )

    async def _write_file(self, file_path: Path, content: bytes) -> None:
        """
        파일 쓰기

        Args:
            file_path: 저장할 파일 경로
            content: 파일 내용
        """
        try:
            # 파일 쓰기
            with open(file_path, "wb") as f:
                f.write(content)

            # 파일 쓰기 권한 확인
            if not os.access(file_path, os.W_OK):
                raise Exception("파일 쓰기 권한이 없습니다")

        except Exception as e:
            # 파일 쓰기 실패 시 파일 삭제
            if file_path.exists():
                file_path.unlink()
            raise Exception(f"파일 쓰기 실패: {str(e)}")

    async def _cleanup_failed_upload(self, file_uuid: str) -> None:
        """
        실패한 업로드 정리

        Args:
            file_uuid: 파일 UUID
        """
        try:
            # 저장 구조에 따라 정리 경로 결정
            storage_structure = settings.storage_structure

            if storage_structure == "date":
                # 날짜 구조에서는 전체 업로드 디렉토리에서 검색
                cleanup_path = self.base_storage_path
            elif storage_structure == "uuid":
                # UUID 구조
                uuid_depth = settings.storage_uuid_depth
                uuid_parts = []

                for i in range(uuid_depth):
                    start_idx = i * 2
                    end_idx = start_idx + 2
                    if end_idx <= len(file_uuid):
                        uuid_parts.append(file_uuid[start_idx:end_idx])
                    else:
                        break

                cleanup_path = self.base_storage_path
                for part in uuid_parts:
                    cleanup_path = cleanup_path / part
            elif storage_structure == "flat":
                # 평면 구조
                cleanup_path = self.base_storage_path
            else:
                # 기본 UUID 구조
                uuid_prefix = file_uuid[:2]
                uuid_subprefix = file_uuid[2:4]
                cleanup_path = self.base_storage_path / uuid_prefix / uuid_subprefix

            if cleanup_path.exists():
                # 해당 디렉토리의 모든 파일 삭제
                for file_path in cleanup_path.glob(f"{file_uuid}*"):
                    file_path.unlink()

                # 빈 디렉토리 삭제 (날짜 구조가 아닌 경우)
                if storage_structure != "date" and not any(cleanup_path.iterdir()):
                    cleanup_path.rmdir()

        except Exception as e:
            # 정리 실패는 로그만 남기고 예외를 발생시키지 않음
            print(f"업로드 실패 정리 중 오류: {e}")

    def get_file_path(self, file_uuid: str) -> Optional[Path]:
        """
        파일 UUID로 파일 경로 조회

        Args:
            file_uuid: 파일 UUID

        Returns:
            파일 경로 (존재하지 않으면 None)
        """
        try:
            # 데이터베이스에서 파일 정보 조회
            file_info = (
                self.db_session.query(FileInfo)
                .filter(FileInfo.file_uuid == file_uuid)
                .first()
            )

            if file_info and file_info.storage_path:
                file_path = Path(file_info.storage_path)
                if file_path.exists():
                    return file_path

            # 데이터베이스에 없거나 경로가 다른 경우, 저장 구조에 따라 검색
            return self._find_file_by_uuid(file_uuid)

        except Exception as e:
            print(f"파일 경로 조회 중 오류: {e}")
            return None

    def _find_file_by_uuid(self, file_uuid: str) -> Optional[Path]:
        """
        UUID로 파일 검색 (저장 구조에 따라)

        Args:
            file_uuid: 파일 UUID

        Returns:
            파일 경로 (찾지 못하면 None)
        """
        storage_structure = settings.storage_structure

        if storage_structure == "date":
            # 날짜 구조: 전체 디렉토리에서 검색
            for date_dir in self.base_storage_path.iterdir():
                if date_dir.is_dir():
                    for file_path in date_dir.rglob(f"{file_uuid}*"):
                        if file_path.is_file():
                            return file_path

        elif storage_structure == "uuid":
            # UUID 구조
            uuid_depth = settings.storage_uuid_depth
            uuid_parts = []

            for i in range(uuid_depth):
                start_idx = i * 2
                end_idx = start_idx + 2
                if end_idx <= len(file_uuid):
                    uuid_parts.append(file_uuid[start_idx:end_idx])
                else:
                    break

            search_path = self.base_storage_path
            for part in uuid_parts:
                search_path = search_path / part

            if search_path.exists():
                for file_path in search_path.glob(f"{file_uuid}*"):
                    if file_path.is_file():
                        return file_path

        elif storage_structure == "flat":
            # 평면 구조
            for file_path in self.base_storage_path.glob(f"{file_uuid}*"):
                if file_path.is_file():
                    return file_path
        else:
            # 기본 UUID 구조
            uuid_prefix = file_uuid[:2]
            uuid_subprefix = file_uuid[2:4]
            search_path = self.base_storage_path / uuid_prefix / uuid_subprefix

            if search_path.exists():
                for file_path in search_path.glob(f"{file_uuid}*"):
                    if file_path.is_file():
                        return file_path

        return None

    def delete_file(self, file_uuid: str) -> bool:
        """
        파일 삭제

        Args:
            file_uuid: 파일 UUID

        Returns:
            삭제 성공 여부
        """
        try:
            # 파일 경로 조회
            file_path = self.get_file_path(file_uuid)
            if not file_path or not file_path.exists():
                return False

            # 파일 삭제
            file_path.unlink()

            # 빈 디렉토리 정리
            self._cleanup_empty_directories(file_path.parent)

            return True

        except Exception as e:
            print(f"파일 삭제 중 오류: {e}")
            return False

    def _cleanup_empty_directories(self, directory: Path) -> None:
        """
        빈 디렉토리 정리

        Args:
            directory: 정리할 디렉토리
        """
        try:
            # 날짜 구조가 아닌 경우에만 빈 디렉토리 삭제
            if settings.storage_structure != "date":
                current_dir = directory
                while current_dir != self.base_storage_path and current_dir.exists():
                    if not any(current_dir.iterdir()):
                        current_dir.rmdir()
                        current_dir = current_dir.parent
                    else:
                        break
        except Exception as e:
            print(f"빈 디렉토리 정리 중 오류: {e}")

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        저장소 통계 정보 반환

        Returns:
            저장소 통계 정보
        """
        try:
            total_files = 0
            total_size = 0
            file_types = {}

            # 저장 구조에 따라 파일 검색
            if settings.storage_structure == "date":
                # 날짜 구조: 모든 하위 디렉토리 검색
                for file_path in self.base_storage_path.rglob("*"):
                    if file_path.is_file():
                        total_files += 1
                        total_size += file_path.stat().st_size
                        ext = file_path.suffix.lower()
                        file_types[ext] = file_types.get(ext, 0) + 1
            else:
                # 다른 구조: 전체 디렉토리 검색
                for file_path in self.base_storage_path.rglob("*"):
                    if file_path.is_file():
                        total_files += 1
                        total_size += file_path.stat().st_size
                        ext = file_path.suffix.lower()
                        file_types[ext] = file_types.get(ext, 0) + 1

            # 디스크 사용량
            total, used, free = shutil.disk_usage(self.base_storage_path)

            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "file_types": file_types,
                "disk_total_gb": total / (1024 * 1024 * 1024),
                "disk_used_gb": used / (1024 * 1024 * 1024),
                "disk_free_gb": free / (1024 * 1024 * 1024),
                "storage_structure": settings.storage_structure,
                "base_path": str(self.base_storage_path),
            }

        except Exception as e:
            print(f"저장소 통계 조회 중 오류: {e}")
            return {
                "error": str(e),
                "storage_structure": settings.storage_structure,
                "base_path": str(self.base_storage_path),
            }
