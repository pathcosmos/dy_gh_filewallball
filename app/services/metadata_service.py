"""
메타데이터 저장 및 관계 설정 서비스
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.orm_models import (
    FileCategory,
    FileInfo,
    FileTag,
    FileTagRelation,
    FileUpload,
    SystemSetting,
)
from app.utils.security_utils import generate_uuid


class MetadataService:
    """메타데이터 저장 및 관계 설정 서비스"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    async def save_file_metadata(
        self,
        file_uuid: str,
        original_filename: str,
        stored_filename: str,
        file_extension: str,
        mime_type: str,
        file_size: int,
        file_hash: str,
        storage_path: str,
        request: Request,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        파일 메타데이터 저장

        Args:
            file_uuid: 파일 UUID
            original_filename: 원본 파일명
            stored_filename: 저장 파일명
            file_extension: 파일 확장자
            mime_type: MIME 타입
            file_size: 파일 크기
            file_hash: 파일 해시
            storage_path: 저장 경로
            request: FastAPI 요청 객체
            metadata: 추가 메타데이터

        Returns:
            저장된 메타데이터 정보
        """
        try:
            # 트랜잭션 시작
            self.db_session.begin()

            # 1. files 테이블에 파일 정보 저장
            file_info = FileInfo(
                file_uuid=file_uuid,
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_extension=file_extension,
                mime_type=mime_type,
                file_size=file_size,
                file_hash=file_hash,
                storage_path=storage_path,
                category_id=metadata.get("category_id") if metadata else None,
                is_public=metadata.get("is_public", True) if metadata else True,
                is_deleted=False,
                description=metadata.get("description") if metadata else None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            self.db_session.add(file_info)
            self.db_session.flush()  # ID 생성

            # 2. file_uploads 테이블에 업로드 기록 저장
            upload_record = FileUpload(
                file_uuid=file_uuid,
                upload_status="success",
                upload_ip=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                upload_time=datetime.now(),
                created_at=datetime.now(),
            )

            self.db_session.add(upload_record)

            # 3. 태그 처리
            tags = metadata.get("tags", []) if metadata else []
            if tags:
                await self._process_tags(file_uuid, tags)

            # 4. 카테고리 처리
            category_id = metadata.get("category_id") if metadata else None
            if category_id:
                await self._validate_category(category_id)

            # 트랜잭션 커밋
            self.db_session.commit()

            return {
                "file_uuid": file_uuid,
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "file_hash": file_hash,
                "category_id": category_id,
                "tags": tags,
                "is_public": file_info.is_public,
                "description": file_info.description,
                "upload_ip": upload_record.upload_ip,
                "upload_time": upload_record.upload_time.isoformat(),
            }

        except IntegrityError as e:
            # 외래키 제약조건 위반 등
            self.db_session.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"메타데이터 저장 실패: 제약조건 위반 - {str(e)}",
            )
        except Exception as e:
            # 기타 오류
            self.db_session.rollback()
            raise HTTPException(
                status_code=500, detail=f"메타데이터 저장 실패: {str(e)}"
            )

    async def _process_tags(self, file_uuid: str, tags: List[str]) -> None:
        """
        태그 처리 (생성 및 관계 설정)

        Args:
            file_uuid: 파일 UUID
            tags: 태그 목록
        """
        for tag_name in tags:
            # 태그 정규화 (소문자, 공백 제거)
            normalized_tag = tag_name.lower().strip()
            if not normalized_tag:
                continue

            # 기존 태그 조회 또는 생성
            tag = (
                self.db_session.query(FileTag)
                .filter(FileTag.name == normalized_tag)
                .first()
            )

            if not tag:
                tag = FileTag(
                    name=normalized_tag,
                    display_name=tag_name,
                    created_at=datetime.now(),
                )
                self.db_session.add(tag)
                self.db_session.flush()  # ID 생성

            # 태그 관계 생성 (중복 방지)
            existing_relation = (
                self.db_session.query(FileTagRelation)
                .filter(
                    FileTagRelation.file_uuid == file_uuid,
                    FileTagRelation.tag_id == tag.id,
                )
                .first()
            )

            if not existing_relation:
                tag_relation = FileTagRelation(
                    file_uuid=file_uuid, tag_id=tag.id, created_at=datetime.now()
                )
                self.db_session.add(tag_relation)

    async def _validate_category(self, category_id: int) -> None:
        """
        카테고리 유효성 검증

        Args:
            category_id: 카테고리 ID

        Raises:
            HTTPException: 카테고리가 존재하지 않는 경우
        """
        category = (
            self.db_session.query(FileCategory)
            .filter(FileCategory.id == category_id, FileCategory.is_active == True)
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=400, detail=f"존재하지 않는 카테고리입니다: {category_id}"
            )

    def _get_client_ip(self, request: Request) -> str:
        """
        클라이언트 IP 주소 추출

        Args:
            request: FastAPI 요청 객체

        Returns:
            클라이언트 IP 주소
        """
        # X-Forwarded-For 헤더 확인 (프록시 환경)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 기본 클라이언트 IP
        return request.client.host if request.client else "unknown"

    def get_file_metadata(self, file_uuid: str) -> Optional[Dict[str, Any]]:
        """
        파일 메타데이터 조회

        Args:
            file_uuid: 파일 UUID

        Returns:
            파일 메타데이터
        """
        try:
            # 파일 정보 조회
            file_info = (
                self.db_session.query(FileInfo)
                .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
                .first()
            )

            if not file_info:
                return None

            # 업로드 기록 조회
            upload_record = (
                self.db_session.query(FileUpload)
                .join(FileInfo)
                .filter(FileInfo.file_uuid == file_uuid)
                .order_by(FileUpload.upload_started_at.desc())
                .first()
            )

            # 태그 조회
            tags = (
                self.db_session.query(FileTag)
                .join(FileTagRelation)
                .join(FileInfo)
                .filter(FileInfo.file_uuid == file_uuid)
                .all()
            )

            # 카테고리 조회
            category = None
            if file_info.category_id:
                category = (
                    self.db_session.query(FileCategory)
                    .filter(FileCategory.id == file_info.category_id)
                    .first()
                )

            return {
                "file_uuid": file_info.file_uuid,
                "original_filename": file_info.original_filename,
                "stored_filename": file_info.stored_filename,
                "file_extension": file_info.file_extension,
                "mime_type": file_info.mime_type,
                "file_size": file_info.file_size,
                "file_hash": file_info.file_hash,
                "storage_path": file_info.storage_path,
                "category": (
                    {
                        "id": category.id,
                        "name": category.name,
                        "description": category.description,
                    }
                    if category
                    else None
                ),
                "tags": [{"id": tag.id, "name": tag.name} for tag in tags],
                "is_public": file_info.is_public,
                "description": file_info.description,
                "upload_ip": upload_record.client_ip if upload_record else None,
                "upload_time": (
                    upload_record.upload_started_at.isoformat()
                    if upload_record
                    else None
                ),
                "created_at": file_info.created_at.isoformat(),
                "updated_at": file_info.updated_at.isoformat(),
            }

        except Exception as e:
            print(f"메타데이터 조회 중 오류: {e}")
            return None

    def update_file_metadata(self, file_uuid: str, updates: Dict[str, Any]) -> bool:
        """
        파일 메타데이터 업데이트

        Args:
            file_uuid: 파일 UUID
            updates: 업데이트할 필드들

        Returns:
            업데이트 성공 여부
        """
        try:
            # 파일 정보 조회
            file_info = (
                self.db_session.query(FileInfo)
                .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
                .first()
            )

            if not file_info:
                return False

            # 업데이트 가능한 필드들
            allowed_fields = {"description", "is_public", "category_id"}

            for field, value in updates.items():
                if field in allowed_fields and hasattr(file_info, field):
                    setattr(file_info, field, value)

            file_info.updated_at = datetime.now()

            # 태그 업데이트
            if "tags" in updates:
                # 기존 태그 관계 삭제
                self.db_session.query(FileTagRelation).filter(
                    FileTagRelation.file_uuid == file_uuid
                ).delete()

                # 새 태그 처리
                if updates["tags"]:
                    asyncio.create_task(self._process_tags(file_uuid, updates["tags"]))

            self.db_session.commit()
            return True

        except Exception as e:
            self.db_session.rollback()
            print(f"메타데이터 업데이트 중 오류: {e}")
            return False

    def get_upload_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        업로드 통계 조회

        Args:
            days: 조회할 일수

        Returns:
            업로드 통계
        """
        try:
            from datetime import timedelta

            start_date = datetime.now() - timedelta(days=days)

            # 총 업로드 수
            total_uploads = (
                self.db_session.query(FileUpload)
                .filter(
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_status == "success",
                )
                .count()
            )

            # 성공한 업로드 수
            successful_uploads = (
                self.db_session.query(FileUpload)
                .filter(
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_status == "success",
                )
                .count()
            )

            # 실패한 업로드 수
            failed_uploads = (
                self.db_session.query(FileUpload)
                .filter(
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_status == "failed",
                )
                .count()
            )

            # 총 파일 크기
            total_size = (
                self.db_session.query(FileInfo)
                .filter(FileInfo.created_at >= start_date, FileInfo.is_deleted == False)
                .with_entities(func.sum(FileInfo.file_size))
                .scalar()
                or 0
            )

            return {
                "period_days": days,
                "total_uploads": total_uploads,
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "success_rate": (
                    (successful_uploads / total_uploads * 100)
                    if total_uploads > 0
                    else 0
                ),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
            }

        except Exception as e:
            print(f"업로드 통계 조회 중 오류: {e}")
            return {}
