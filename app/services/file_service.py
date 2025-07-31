"""
파일 서비스 모듈
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.orm_models import FileInfo
from app.services.file_storage_service import FileStorageService


class FileService:
    """파일 서비스 클래스"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.storage_service = FileStorageService(db_session)

    async def upload_file(
        self, file: UploadFile, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        파일 업로드

        Args:
            file: 업로드된 파일
            metadata: 추가 메타데이터

        Returns:
            업로드 결과
        """
        try:
            # 파일 저장
            storage_result = await self.storage_service.save_file(file, file.filename)

            if storage_result["is_duplicate"]:
                return {
                    "status": "duplicate",
                    "file_uuid": storage_result["file_uuid"],
                    "message": storage_result["message"],
                }

            # 메타데이터 저장
            file_info = FileInfo(
                file_uuid=storage_result["file_uuid"],
                original_filename=file.filename,
                stored_filename=storage_result["stored_filename"],
                file_extension=storage_result["file_extension"],
                mime_type=file.content_type,
                file_size=storage_result["file_size"],
                file_hash=storage_result["file_hash"],
                storage_path=storage_result["storage_path"],
                is_public=metadata.get("is_public", True) if metadata else True,
                description=metadata.get("description") if metadata else None,
            )

            self.db_session.add(file_info)
            self.db_session.commit()

            return {
                "status": "success",
                "file_uuid": storage_result["file_uuid"],
                "original_filename": file.filename,
                "stored_filename": storage_result["stored_filename"],
                "file_size": storage_result["file_size"],
                "file_hash": storage_result["file_hash"],
            }

        except Exception as e:
            self.db_session.rollback()
            raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

    def get_file_info(self, file_uuid: str) -> Optional[FileInfo]:
        """
        파일 정보 조회

        Args:
            file_uuid: 파일 UUID

        Returns:
            파일 정보
        """
        return (
            self.db_session.query(FileInfo)
            .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
            .first()
        )

    def list_files(self, limit: int = 100, offset: int = 0) -> List[FileInfo]:
        """
        파일 목록 조회

        Args:
            limit: 조회할 파일 수
            offset: 시작 위치

        Returns:
            파일 목록
        """
        return (
            self.db_session.query(FileInfo)
            .filter(FileInfo.is_deleted == False)
            .limit(limit)
            .offset(offset)
            .all()
        )

    def delete_file(self, file_uuid: str) -> bool:
        """
        파일 삭제

        Args:
            file_uuid: 파일 UUID

        Returns:
            삭제 성공 여부
        """
        return self.storage_service.delete_file(file_uuid)

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        저장소 통계 조회

        Returns:
            저장소 통계
        """
        return self.storage_service.get_storage_stats()
