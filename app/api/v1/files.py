"""
File management endpoints.
Task 8.1: 파일 정보 조회 및 다운로드 API 리팩토링
"""

import mimetypes
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, text
from sqlalchemy.orm import Session, joinedload

from app.dependencies.auth import get_current_user, get_optional_user
from app.dependencies.database import get_db
from app.services.project_key_service import ProjectKeyService

# Prometheus 메트릭은 별도 모듈에서 import
# from app.metrics import (
#     active_connections_gauge,
#     cache_hit_counter,
#     cache_miss_counter,
#     error_rate_counter,
#     file_download_counter,
#     file_processing_duration,
#     file_upload_counter,
#     file_upload_duration,
#     file_upload_error_counter,
# )
from app.models.orm_models import (
    FileDownload,
    FileInfo,
    FileTag,
    FileTagRelation,
    FileView,
    ProjectKey,
)
# from app.services.cache_service import CacheService
# from app.services.rbac_service import rbac_service
# from app.services.scheduler_service import scheduler_service
# from app.services.statistics_service import statistics_service
# from app.services.thumbnail_service import thumbnail_service
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    파일 업로드 API
    Task 15: 파일 업로드 API 구현

    Args:
        file: 업로드할 파일
        authorization: Bearer 토큰 (프로젝트 키)
        db: 데이터베이스 세션

    Returns:
        Dict[str, Any]: 업로드 결과 (file_id, download_url 등)
    """
    try:
        # 프로젝트 키 인증
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header with Bearer token required"
            )
        
        project_key = authorization.replace("Bearer ", "")
        
        # 프로젝트 키 검증
        project_service = ProjectKeyService(db)
        project_info = project_service.validate_project_key(project_key)
        
        if not project_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid project key"
            )
        
        # 파일 크기 제한 (100MB)
        max_file_size = 100 * 1024 * 1024  # 100MB
        if file.size and file.size > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds maximum limit of 100MB"
            )
        
        # 파일 확장자 및 MIME 타입 확인
        file_extension = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
        
        # 파일 ID 생성 (UUID4)
        file_id = str(uuid.uuid4())
        
        # 저장 경로 생성 (권한 문제 해결을 위해 임시 디렉토리 사용)
        try:
            project_upload_dir = os.path.join("/app/uploads", str(project_info.id))
            os.makedirs(project_upload_dir, exist_ok=True)
        except (PermissionError, OSError):
            # 권한 문제 시 임시 디렉토리 사용
            project_upload_dir = os.path.join("/tmp/uploads", str(project_info.id))
            os.makedirs(project_upload_dir, exist_ok=True)
        
        # 파일 저장 경로
        stored_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(project_upload_dir, stored_filename)
        
        # 파일 저장
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file"
            )
        
        # 파일 크기 확인
        file_size = os.path.getsize(file_path)
        
        # 파일 해시 계산 (간단한 구현)
        import hashlib
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # 데이터베이스에 파일 정보 저장
        file_info = FileInfo(
            file_uuid=file_id,
            original_filename=file.filename or "unknown",
            stored_filename=stored_filename,
            file_extension=file_extension,
            mime_type=mime_type,
            file_size=file_size,
            file_hash=file_hash,
            storage_path=os.path.join(str(project_info.id), stored_filename),
            is_public=False,  # 기본적으로 비공개
            project_id=project_info.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        db.add(file_info)
        db.commit()
        db.refresh(file_info)
        
        # 다운로드 URL 생성
        download_url = f"/api/v1/files/{file_id}/download"
        
        # 메트릭 업데이트
        file_upload_counter.inc()
        
        logger.info(f"File uploaded successfully: {file_id}, size: {file_size}, project: {project_info.project_name}")
        
        return {
            "file_id": file_id,
            "download_url": download_url,
            "original_filename": file.filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "message": "File uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        file_upload_error_counter.inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.get("/")
async def list_files(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    size: int = Query(20, ge=1, le=100, description="페이지당 파일 수"),
    sort_by: str = Query(
        "created_at",
        description="정렬 기준 (filename, file_size, created_at, updated_at)",
    ),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
    category_id: Optional[int] = Query(None, description="카테고리 ID로 필터링"),
    tags: Optional[str] = Query(
        None, description="태그로 필터링 (쉼표로 구분된 문자열)"
    ),
    file_type: Optional[str] = Query(
        None, description="파일 확장자로 필터링 (예: jpg, pdf)"
    ),
    min_size: Optional[int] = Query(None, ge=0, description="최소 파일 크기 (bytes)"),
    max_size: Optional[int] = Query(None, ge=0, description="최대 파일 크기 (bytes)"),
    date_from: Optional[datetime] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    date_to: Optional[datetime] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    is_public: bool = Query(True, description="공개 여부로 필터링"),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> Dict[str, Any]:
    """
    파일 목록 조회 및 고도화된 필터링 (Task 12.1)

    Args:
        page: 페이지 번호 (1부터 시작)
        size: 페이지당 파일 수 (최대 100)
        sort_by: 정렬 기준 (filename, file_size, created_at, updated_at)
        sort_order: 정렬 순서 (asc, desc)
        category_id: 카테고리 ID로 필터링
        tags: 태그로 필터링 (쉼표로 구분된 문자열)
        file_type: 파일 확장자로 필터링
        min_size: 최소 파일 크기 (bytes)
        max_size: 최대 파일 크기 (bytes)
        date_from: 시작 날짜
        date_to: 종료 날짜
        is_public: 공개 여부로 필터링
        db: 데이터베이스 세션
        current_user: 현재 사용자 (선택적)

    Returns:
        Dict[str, Any]: 파일 목록 및 페이지네이션 정보
    """
    try:
        # 페이지네이션 계산
        offset = (page - 1) * size

        # 기본 쿼리 구성
        query = (
            db.query(FileInfo)
            .filter(FileInfo.is_deleted == False, FileInfo.is_public == is_public)
            .options(joinedload(FileInfo.category), joinedload(FileInfo.tags))
        )

        # 카테고리 필터링
        if category_id is not None:
            query = query.filter(FileInfo.file_category_id == category_id)

        # 태그 필터링
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            if tag_list:
                # 태그 관계를 통한 필터링
                query = (
                    query.join(FileTagRelation)
                    .join(FileTag)
                    .filter(FileTag.tag_name.in_(tag_list))
                    .distinct()
                )

        # 파일 타입 필터링
        if file_type:
            file_type = file_type.lower().strip()
            if not file_type.startswith("."):
                file_type = f".{file_type}"
            query = query.filter(FileInfo.file_extension.ilike(f"%{file_type}"))

        # 파일 크기 필터링
        if min_size is not None:
            query = query.filter(FileInfo.file_size >= min_size)
        if max_size is not None:
            query = query.filter(FileInfo.file_size <= max_size)

        # 날짜 범위 필터링
        if date_from:
            query = query.filter(FileInfo.created_at >= date_from)
        if date_to:
            query = query.filter(FileInfo.created_at <= date_to)

        # 총 개수 조회
        total_count = query.count()

        # 동적 정렬 적용
        sort_column = None
        if sort_by == "filename":
            sort_column = FileInfo.original_filename
        elif sort_by == "file_size":
            sort_column = FileInfo.file_size
        elif sort_by == "created_at":
            sort_column = FileInfo.created_at
        elif sort_by == "updated_at":
            sort_column = FileInfo.updated_at
        else:
            # 기본값: 생성일
            sort_column = FileInfo.created_at

        # 정렬 순서 적용
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 페이지네이션 적용
        files = query.offset(offset).limit(size).all()

        # 응답 데이터 구성
        file_list = []
        for file_info in files:
            file_data = {
                "file_uuid": file_info.file_uuid,
                "original_filename": file_info.original_filename,
                "file_extension": file_info.file_extension,
                "mime_type": file_info.mime_type,
                "file_size": file_info.file_size,
                "is_public": file_info.is_public,
                "created_at": file_info.created_at.isoformat(),
                "updated_at": file_info.updated_at.isoformat(),
                "category": (
                    {
                        "id": file_info.category.id,
                        "name": file_info.category.name,
                        "description": file_info.category.description,
                    }
                    if file_info.category
                    else None
                ),
                "tags": [
                    {
                        "id": tag.id,
                        "name": tag.tag_name,
                        "color": tag.tag_color,
                        "description": tag.description,
                    }
                    for tag in file_info.tags
                ],
            }
            file_list.append(file_data)

        # 페이지네이션 메타데이터 계산
        total_pages = (total_count + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        response_data = {
            "files": file_list,
            "pagination": {
                "page": page,
                "size": size,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": page + 1 if has_next else None,
                "prev_page": page - 1 if has_prev else None,
            },
            "sorting": {"sort_by": sort_by, "sort_order": sort_order},
            "filters": {
                "category_id": category_id,
                "tags": tags,
                "file_type": file_type,
                "min_size": min_size,
                "max_size": max_size,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "is_public": is_public,
            },
        }

        logger.info(
            f"File list retrieved: page={page}, size={size}, total={total_count}, "
            f"sort_by={sort_by}, sort_order={sort_order}"
        )
        return response_data

    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file list",
        )


@router.get("/search")
async def search_files(
    query: str = Query(..., description="검색어"),
    file_type: Optional[str] = Query(None, description="파일 확장자 (예: jpg, pdf)"),
    date_from: Optional[datetime] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    date_to: Optional[datetime] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 파일 수"),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> Dict[str, Any]:
    """
    파일 검색 API (Task 8.3)

    Args:
        query: 검색어 (파일명, 설명에서 검색)
        file_type: 파일 확장자로 필터링
        date_from: 시작 날짜
        date_to: 종료 날짜
        page: 페이지 번호
        size: 페이지당 파일 수
        db: 데이터베이스 세션
        current_user: 현재 사용자 (선택적)

    Returns:
        Dict[str, Any]: 검색 결과 및 페이지네이션 정보
    """
    try:
        # 페이지네이션 계산
        offset = (page - 1) * size

        # 기본 쿼리 구성
        search_query = (
            db.query(FileInfo)
            .filter(FileInfo.is_deleted == False)
            .options(joinedload(FileInfo.category), joinedload(FileInfo.tags))
        )

        # 검색어 필터링 (파일명, 설명에서 contains 검색)
        if query:
            search_query = search_query.filter(
                or_(
                    FileInfo.original_filename.contains(query),
                    FileInfo.description.contains(query),
                )
            )

        # 파일 타입 필터링
        if file_type:
            search_query = search_query.filter(
                FileInfo.file_extension.ilike(f"%{file_type}%")
            )

        # 날짜 범위 필터링
        if date_from:
            search_query = search_query.filter(FileInfo.created_at >= date_from)
        if date_to:
            search_query = search_query.filter(FileInfo.created_at <= date_to)

        # 총 개수 조회
        total_count = search_query.count()

        # 정렬 및 페이지네이션 적용
        files = (
            search_query.order_by(FileInfo.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # 응답 데이터 구성
        file_list = []
        for file_info in files:
            file_data = {
                "file_uuid": file_info.file_uuid,
                "original_filename": file_info.original_filename,
                "file_extension": file_info.file_extension,
                "mime_type": file_info.mime_type,
                "file_size": file_info.file_size,
                "is_public": file_info.is_public,
                "created_at": file_info.created_at.isoformat(),
                "updated_at": file_info.updated_at.isoformat(),
                "category": (
                    {
                        "id": file_info.category.id,
                        "name": file_info.category.name,
                        "description": file_info.category.description,
                    }
                    if file_info.category
                    else None
                ),
                "tags": [
                    {
                        "id": tag.id,
                        "name": tag.tag_name,
                        "color": tag.tag_color,
                        "description": tag.description,
                    }
                    for tag in file_info.tags
                ],
            }
            file_list.append(file_data)

        # 페이지네이션 메타데이터 계산
        total_pages = (total_count + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        response_data = {
            "query": query,
            "filters": {
                "file_type": file_type,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
            "files": file_list,
            "pagination": {
                "page": page,
                "size": size,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": page + 1 if has_next else None,
                "prev_page": page - 1 if has_prev else None,
            },
        }

        logger.info(f"File search completed: query='{query}', total={total_count}")
        return response_data

    except Exception as e:
        logger.error(f"Failed to search files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search files",
        )


@router.get("/{file_uuid}")
async def get_file_info(
    file_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> Dict[str, Any]:
    """
    파일 정보 조회 (Task 8.1 + Task 8.4 Redis 캐싱)

    Args:
        file_uuid: 파일 UUID
        request: FastAPI Request 객체
        db: 데이터베이스 세션
        current_user: 현재 사용자 (선택적)

    Returns:
        Dict[str, Any]: 파일 정보 및 통계
    """
    try:
        # Task 8.4: Redis 캐시 서비스 초기화
        cache_service = CacheService()

        # Task 8.4: Redis에서 캐시된 파일 정보 확인
        cached_file_info = await cache_service.get_file_info(file_uuid)

        if cached_file_info:
            logger.info(f"파일 정보 캐시 히트: {file_uuid}")

            # 캐시 히트 메트릭 업데이트
            cache_hit_counter.inc()

            # FileView 기록 저장 (캐시 히트 시에도 기록)
            view_record = FileView(
                file_uuid=file_uuid,
                user_id=current_user.id if current_user else None,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", ""),
                view_type="info",
                viewed_at=datetime.utcnow(),
            )
            db.add(view_record)
            db.commit()

            return cached_file_info

        # Task 8.4: 캐시 미스 - DB에서 파일 정보 조회
        logger.info(f"파일 정보 캐시 미스: {file_uuid}")

        # 캐시 미스 메트릭 업데이트
        cache_miss_counter.inc()

        file_info = (
            db.query(FileInfo)
            .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
            .options(joinedload(FileInfo.category), joinedload(FileInfo.tags))
            .first()
        )

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # Task 8.5: 통계 서비스를 통한 통계 정보 조회
        stats_data = await statistics_service.get_file_statistics(db, file_uuid)

        # FileView 기록 저장
        view_record = FileView(
            file_uuid=file_uuid,
            user_id=current_user.id if current_user else None,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", ""),
            view_type="info",
            viewed_at=datetime.utcnow(),
        )
        db.add(view_record)
        db.commit()

        # Task 8.4: 응답 데이터 구성
        response_data = {
            "file_uuid": file_info.file_uuid,
            "original_filename": file_info.original_filename,
            "stored_filename": file_info.stored_filename,
            "file_extension": file_info.file_extension,
            "mime_type": file_info.mime_type,
            "file_size": file_info.file_size,
            "file_hash": file_info.file_hash,
            "storage_path": file_info.storage_path,
            "is_public": file_info.is_public,
            "created_at": file_info.created_at.isoformat(),
            "updated_at": file_info.updated_at.isoformat(),
            "category": (
                {
                    "id": file_info.category.id,
                    "name": file_info.category.name,
                    "description": file_info.category.description,
                }
                if file_info.category
                else None
            ),
            "tags": [
                {
                    "id": tag.id,
                    "name": tag.tag_name,
                    "color": tag.tag_color,
                    "description": tag.description,
                }
                for tag in file_info.tags
            ],
            "statistics": (
                stats_data
                if stats_data
                else {
                    "total_views": 0,
                    "unique_viewers": 0,
                    "total_downloads": 0,
                    "unique_downloaders": 0,
                    "total_interactions": 0,
                    "popularity_score": 0.0,
                    "avg_daily_views": 0.0,
                    "engagement_rate": 0.0,
                    "recent_views": 0,
                    "recent_downloads": 0,
                    "view_breakdown": {
                        "info_views": 0,
                        "preview_views": 0,
                        "thumbnail_views": 0,
                    },
                    "last_viewed": None,
                    "first_viewed": None,
                    "last_downloaded": None,
                    "first_downloaded": None,
                    "total_bytes_downloaded": 0,
                    "statistics_updated_at": None,
                }
            ),
        }

        # Task 8.4: Redis에 파일 정보 캐시 저장
        try:
            await cache_service.set_file_info(file_uuid, response_data)
            logger.info(f"파일 정보 캐시 저장 완료: {file_uuid}")
        except Exception as cache_error:
            logger.warning(f"캐시 저장 실패 (무시됨): {file_uuid}, 오류: {cache_error}")

        logger.info(f"File info retrieved for UUID: {file_uuid}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file info for UUID {file_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file information",
        )


@router.get("/{file_uuid}/download")
async def download_file(
    file_uuid: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    """
    파일 다운로드 (Task 8.1)

    Args:
        file_uuid: 파일 UUID
        request: FastAPI Request 객체
        response: FastAPI Response 객체
        db: 데이터베이스 세션
        current_user: 현재 사용자 (선택적)

    Returns:
        StreamingResponse: 파일 스트리밍 응답
    """
    try:
        # 파일 정보 조회
        file_info = (
            db.query(FileInfo)
            .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
            .first()
        )

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # 파일 존재 여부 확인
        # storage_path는 상대 경로이므로 uploads 디렉토리와 결합
        if file_info.storage_path.startswith('/'):
            file_path = os.path.join(file_info.storage_path, file_info.stored_filename)
        else:
            # 상대 경로인 경우 uploads 디렉토리와 결합
            file_path = os.path.join("/app/uploads", file_info.storage_path, file_info.stored_filename)
            
        if not os.path.exists(file_path):
            # 첫 번째 경로가 없으면 임시 디렉토리에서 시도
            temp_file_path = os.path.join("/tmp/uploads", file_info.storage_path, file_info.stored_filename)
            if os.path.exists(temp_file_path):
                file_path = temp_file_path
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found on storage",
                )

        # 다운로드 시작 시간 기록
        download_start_time = time.time()

        # FileView 기록 저장 (다운로드 조회)
        view_record = FileView(
            file_id=file_info.id,
            viewer_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer"),
            view_type="download",
            session_id=request.headers.get("x-session-id"),
        )
        db.add(view_record)

        # FileDownload 기록 저장
        download_record = FileDownload(
            file_id=file_info.id,
            downloader_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            download_method="api",
            bytes_downloaded=file_info.file_size,
            session_id=request.headers.get("x-session-id"),
        )
        db.add(download_record)
        db.commit()

        # 다운로드 완료 시간 계산
        download_duration_ms = int((time.time() - download_start_time) * 1000)
        download_record.download_duration_ms = download_duration_ms
        db.commit()

        # 스트리밍 응답 생성
        def file_stream():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):  # 8KB 청크
                    yield chunk

        # Content-Disposition 헤더 설정
        filename = file_info.original_filename
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.headers["Content-Type"] = file_info.mime_type
        response.headers["Content-Length"] = str(file_info.file_size)

        # 메트릭 업데이트
        file_download_counter.inc()
        file_processing_duration.observe(time.time() - download_start_time)

        logger.info(
            f"File download started for UUID: {file_uuid}, size: {file_info.file_size}"
        )

        return StreamingResponse(
            file_stream(),
            media_type=file_info.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(file_info.file_size),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file for UUID {file_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file",
        )


# Task 8.6: 이미지 파일 지원 확장자 및 MIME 타입 매핑
SUPPORTED_IMAGE_EXTENSIONS = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "svg": "image/svg+xml",
    "ico": "image/x-icon",
    "tiff": "image/tiff",
    "tif": "image/tiff",
}


@router.get("/{file_uuid}/preview")
async def preview_image(
    file_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> StreamingResponse:
    """
    이미지 파일 웹 스트리밍 API
    Task 8.6: 이미지 파일 웹 스트리밍 API 구현

    Args:
        file_uuid: 파일 UUID
        request: HTTP 요청 객체
        db: 데이터베이스 세션
        current_user: 현재 사용자 (선택적)

    Returns:
        StreamingResponse: 이미지 스트리밍 응답
    """
    try:
        # 파일 정보 조회
        file_info = (
            db.query(FileInfo)
            .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
            .first()
        )

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # 파일 확장자 확인
        file_extension = file_info.file_extension.lower()
        if file_extension not in SUPPORTED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format: {file_extension}",
            )

        # 파일 경로 확인
        if file_info.storage_path.startswith('/'):
            file_path = os.path.join(file_info.storage_path, file_info.stored_filename)
        else:
            # 상대 경로인 경우 uploads 디렉토리와 결합
            file_path = os.path.join("/app/uploads", file_info.storage_path, file_info.stored_filename)
            
        if not os.path.exists(file_path):
            # 첫 번째 경로가 없으면 임시 디렉토리에서 시도
            temp_file_path = os.path.join("/tmp/uploads", file_info.storage_path, file_info.stored_filename)
            if os.path.exists(temp_file_path):
                file_path = temp_file_path
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk"
                )

        # MIME 타입 설정
        content_type = SUPPORTED_IMAGE_EXTENSIONS[file_extension]

        # FileView 기록 저장 (view_type: 'preview')
        view_record = FileView(
            file_uuid=file_uuid,
            user_id=current_user.id if current_user else None,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", ""),
            view_type="preview",
            viewed_at=datetime.utcnow(),
        )
        db.add(view_record)
        db.commit()

        # 스트리밍 응답 생성
        def generate_image_stream():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):  # 8KB 청크
                    yield chunk

        logger.info(f"Image preview streamed: {file_uuid}, type: {content_type}")

        return StreamingResponse(
            generate_image_stream(),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # 1시간 캐시
                "Accept-Ranges": "bytes",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview image {file_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview image",
        )


@router.get("/{file_uuid}/thumbnail")
async def get_thumbnail(
    file_uuid: str,
    size: str = Query("medium", description="썸네일 크기 (small, medium, large)"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> StreamingResponse:
    """
    이미지 썸네일 생성 및 제공 API
    Task 8.7: 이미지 썸네일 생성 및 제공 API 구현

    Args:
        file_uuid: 파일 UUID
        size: 썸네일 크기 (small, medium, large)
        request: HTTP 요청 객체
        db: 데이터베이스 세션
        current_user: 현재 사용자 (선택적)

    Returns:
        StreamingResponse: 썸네일 스트리밍 응답
    """
    try:
        # 파일 정보 조회
        file_info = (
            db.query(FileInfo)
            .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
            .first()
        )

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # 이미지 파일인지 확인
        file_extension = file_info.file_extension.lower()
        if file_extension not in SUPPORTED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format: {file_extension}",
            )

        # 원본 파일 경로 확인
        if file_info.storage_path.startswith('/'):
            original_path = os.path.join(file_info.storage_path, file_info.stored_filename)
        else:
            # 상대 경로인 경우 uploads 디렉토리와 결합
            original_path = os.path.join("/app/uploads", file_info.storage_path, file_info.stored_filename)
            
        if not os.path.exists(original_path):
            # 첫 번째 경로가 없으면 임시 디렉토리에서 시도
            temp_original_path = os.path.join("/tmp/uploads", file_info.storage_path, file_info.stored_filename)
            if os.path.exists(temp_original_path):
                original_path = temp_original_path
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Original file not found on disk",
                )

        # 썸네일 가져오기 (캐시 확인 후 필요시 생성)
        thumbnail_path = thumbnail_service.get_thumbnail(original_path, file_uuid, size)

        if not thumbnail_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate thumbnail",
            )

        # FileView 기록 저장 (view_type: 'thumbnail')
        if request:
            view_record = FileView(
                file_uuid=file_uuid,
                user_id=current_user.id if current_user else None,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", ""),
                view_type="thumbnail",
                viewed_at=datetime.utcnow(),
            )
            db.add(view_record)
            db.commit()

        # 썸네일 스트리밍 응답 생성
        def generate_thumbnail_stream():
            with open(thumbnail_path, "rb") as f:
                while chunk := f.read(8192):  # 8KB 청크
                    yield chunk

        logger.info(f"Thumbnail streamed: {file_uuid}, size: {size}")

        return StreamingResponse(
            generate_thumbnail_stream(),
            media_type="image/jpeg",  # 썸네일은 항상 JPEG
            headers={
                "Cache-Control": "public, max-age=86400",  # 24시간 캐시
                "Accept-Ranges": "bytes",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thumbnail for {file_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get thumbnail",
        )


@router.put("/{file_uuid}")
async def update_file_info(
    file_uuid: str,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    파일 정보 업데이트 (Task 8.4 캐시 무효화 포함)

    Args:
        file_uuid: 파일 UUID
        update_data: 업데이트할 데이터
        db: 데이터베이스 세션
        current_user: 현재 사용자 (필수)

    Returns:
        Dict[str, Any]: 업데이트된 파일 정보
    """
    try:
        # 파일 정보 조회
        file_info = (
            db.query(FileInfo)
            .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
            .first()
        )

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # 업데이트 가능한 필드들
        allowed_fields = {
            "original_filename",
            "description",
            "is_public",
            "file_category_id",
            "tags",
        }

        # 필드 업데이트
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(file_info, field):
                setattr(file_info, field, value)

        # 업데이트 시간 설정
        file_info.updated_at = datetime.utcnow()

        # Task 8.4: Redis 캐시 무효화
        try:
            cache_service = CacheService()
            await cache_service.invalidate_file_cache(file_uuid)
            logger.info(f"파일 정보 캐시 무효화 완료: {file_uuid}")
        except Exception as cache_error:
            logger.warning(
                f"캐시 무효화 실패 (무시됨): {file_uuid}, 오류: {cache_error}"
            )

        db.commit()

        logger.info(f"File info updated for UUID: {file_uuid}")

        return {
            "file_uuid": file_uuid,
            "updated": True,
            "message": "File information updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file info for UUID {file_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file information",
        )


@router.delete("/{file_uuid}")
async def delete_file(
    file_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    파일 삭제

    Args:
        file_uuid: 파일 UUID
        db: 데이터베이스 세션
        current_user: 현재 사용자 (필수)

    Returns:
        Dict[str, Any]: 삭제 결과
    """
    try:
        # 파일 정보 조회
        file_info = (
            db.query(FileInfo)
            .filter(FileInfo.file_uuid == file_uuid, FileInfo.is_deleted == False)
            .first()
        )

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # Task 12.5: RBAC 권한 검증
        can_delete, reason = rbac_service.can_access_file(
            current_user, file_info, "delete"
        )
        if not can_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"파일 삭제 권한이 없습니다: {reason}",
            )

        # 소프트 삭제 (is_deleted = True)
        file_info.is_deleted = True

        # Task 8.4: Redis 캐시 무효화
        try:
            cache_service = CacheService()
            await cache_service.invalidate_file_cache(file_uuid)
            logger.info(f"삭제된 파일 캐시 무효화 완료: {file_uuid}")
        except Exception as cache_error:
            logger.warning(
                f"캐시 무효화 실패 (무시됨): {file_uuid}, 오류: {cache_error}"
            )

        db.commit()

        logger.info(f"File soft deleted for UUID: {file_uuid}")

        return {
            "file_uuid": file_uuid,
            "deleted": True,
            "message": "File deleted successfully",
        }

    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )


@router.delete("/{file_uuid}/permanent")
async def permanent_delete_file(
    file_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    파일 영구 삭제 (관리자 전용)

    Args:
        file_uuid: 파일 UUID
        db: 데이터베이스 세션
        current_user: 현재 사용자 (관리자 권한 필요)

    Returns:
        Dict[str, Any]: 영구 삭제 결과
    """
    try:
        # Task 12.5: RBAC 권한 검증 (영구 삭제)
        can_permanent_delete, reason = rbac_service.can_access_file(
            current_user, file_info, "permanent_delete"
        )
        if not can_permanent_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"영구 삭제 권한이 없습니다: {reason}",
            )

        # 파일 정보 조회 (소프트 삭제된 파일도 포함)
        file_info = db.query(FileInfo).filter(FileInfo.file_uuid == file_uuid).first()

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # 실제 파일 시스템에서 파일 삭제
        try:
            file_path = os.path.join("uploads", file_info.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Physical file deleted: {file_path}")

            # 썸네일 파일도 삭제
            thumbnail_dir = os.path.join("uploads", "thumbnails")
            if os.path.exists(thumbnail_dir):
                for size in ["small", "medium", "large"]:
                    thumbnail_path = os.path.join(
                        thumbnail_dir, f"{file_uuid}_{size}.jpg"
                    )
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                        logger.info(f"Thumbnail deleted: {thumbnail_path}")

        except Exception as file_error:
            logger.warning(f"Physical file deletion failed: {file_error}")

        # 데이터베이스에서 레코드 완전 삭제
        db.delete(file_info)

        # Task 8.4: Redis 캐시 무효화
        try:
            cache_service = CacheService()
            await cache_service.invalidate_file_cache(file_uuid)
            logger.info(f"영구 삭제된 파일 캐시 무효화 완료: {file_uuid}")
        except Exception as cache_error:
            logger.warning(
                f"캐시 무효화 실패 (무시됨): {file_uuid}, 오류: {cache_error}"
            )

        db.commit()

        logger.info(f"File permanently deleted for UUID: {file_uuid}")

        return {
            "file_uuid": file_uuid,
            "permanently_deleted": True,
            "message": "File permanently deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to permanently delete file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to permanently delete file",
        )


@router.get("/popular")
async def get_popular_files(
    limit: int = Query(10, ge=1, le=100, description="조회할 파일 수"),
    days: int = Query(7, ge=1, le=365, description="기준일 수"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    인기 파일 목록 조회 API
    Task 8.5: 인기 파일 목록 조회

    Args:
        limit: 조회할 파일 수 (1-100)
        days: 기준일 수 (1-365)
        db: 데이터베이스 세션

    Returns:
        인기 파일 목록
    """
    try:
        popular_files = await statistics_service.get_popular_files(db, limit, days)

        return {
            "popular_files": popular_files,
            "total_count": len(popular_files),
            "days": days,
            "limit": limit,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get popular files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get popular files",
        )


@router.get("/trending")
async def get_trending_files(
    limit: int = Query(10, ge=1, le=100, description="조회할 파일 수"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    트렌딩 파일 목록 조회 API
    Task 8.5: 트렌딩 파일 목록 조회 (최근 24시간)

    Args:
        limit: 조회할 파일 수 (1-100)
        db: 데이터베이스 세션

    Returns:
        트렌딩 파일 목록
    """
    try:
        trending_files = await statistics_service.get_trending_files(db, limit)

        return {
            "trending_files": trending_files,
            "total_count": len(trending_files),
            "limit": limit,
            "period": "24h",
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get trending files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trending files",
        )


@router.get("/statistics/overview")
async def get_system_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    시스템 전체 통계 조회 API
    Task 8.5: 시스템 전체 통계 조회

    Args:
        db: 데이터베이스 세션

    Returns:
        시스템 통계 정보
    """
    try:
        system_stats = await statistics_service.get_system_statistics(db)

        return {
            "system_statistics": system_stats,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get system statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system statistics",
        )


@router.get("/cleanup/stats")
async def get_cleanup_statistics(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    파일 정리 작업 통계 조회 API
    Task 12.2: 스케줄러 통계 조회

    Args:
        db: 데이터베이스 세션
        current_user: 현재 사용자 (관리자 권한 필요)

    Returns:
        정리 작업 통계 정보
    """
    try:
        # 관리자 권한 확인 (임시로 user_id가 1인 경우 관리자로 간주)
        if not hasattr(current_user, "id") or current_user.id != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        stats = await scheduler_service.get_cleanup_stats(db)

        return {
            "cleanup_statistics": stats,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cleanup statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cleanup statistics",
        )


@router.post("/cleanup/trigger")
async def trigger_cleanup(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    수동으로 파일 정리 작업 실행
    Task 12.2: 수동 정리 작업 트리거

    Args:
        db: 데이터베이스 세션
        current_user: 현재 사용자 (관리자 권한 필요)

    Returns:
        정리 작업 실행 결과
    """
    try:
        # 관리자 권한 확인
        if not hasattr(current_user, "id") or current_user.id != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        # 백그라운드에서 정리 작업 실행
        await scheduler_service.cleanup_deleted_files()

        return {
            "triggered": True,
            "message": "Cleanup job triggered successfully",
            "triggered_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger cleanup job",
        )
