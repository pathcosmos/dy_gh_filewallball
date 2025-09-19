"""
File Management API Router

This module contains all file-related endpoints including upload, listing, 
information retrieval, and deletion operations.
"""

import os
import mimetypes
from pathlib import Path
from typing import List, Optional
import uuid
from datetime import datetime

import aiofiles
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_async_session
from app.config import get_settings
from app.models.orm_models import FileInfo
from app.services.file_storage_service import FileStorageService
from app.services.file_validation_service import FileValidationService
from app.utils.logging_config import get_logger

# Initialize router
router = APIRouter(
    tags=["파일 관리 (File Management)"],
    responses={
        200: {"description": "성공적으로 처리되었습니다"},
        400: {"description": "잘못된 요청입니다"},
        401: {"description": "인증이 필요합니다"},
        404: {"description": "요청한 리소스를 찾을 수 없습니다"},
        413: {"description": "파일 크기가 너무 큽니다"},
        500: {"description": "서버 내부 오류가 발생했습니다"}
    }
)

# Initialize logger
logger = get_logger(__name__)

# Get configuration
config = get_settings()

# Response models
class FileUploadResponse(BaseModel):
    """파일 업로드 응답 모델"""
    file_id: str = Field(..., description="생성된 고유 파일 ID (UUID)")
    filename: str = Field(..., description="원본 파일명")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    upload_time: datetime = Field(..., description="업로드 완료 시간")
    download_url: str = Field(..., description="파일 다운로드 URL")
    view_url: str = Field(..., description="파일 뷰어 URL")
    message: str = Field(..., description="처리 결과 메시지")

    class Config:
        schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "example.txt",
                "file_size": 1024,
                "upload_time": "2025-08-25T01:00:00",
                "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
                "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
                "message": "파일이 성공적으로 업로드되었습니다"
            }
        }


class FileInfoResponse(BaseModel):
    """파일 정보 응답 모델"""
    file_id: str = Field(..., description="파일 고유 ID")
    filename: str = Field(..., description="원본 파일명")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    mime_type: Optional[str] = Field(None, description="파일 MIME 타입")
    upload_time: datetime = Field(..., description="업로드 시간")
    file_hash: Optional[str] = Field(None, description="파일 해시값")
    download_count: int = Field(0, description="다운로드 횟수")
    download_url: str = Field(..., description="파일 다운로드 URL")
    view_url: str = Field(..., description="파일 뷰어 URL (이미지는 여기서 확인 가능)")
    preview_url: Optional[str] = Field(None, description="파일 미리보기 URL (이미지 썸네일)")

    class Config:
        schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "example.png",
                "file_size": 1024,
                "mime_type": "image/png",
                "upload_time": "2025-08-25T01:00:00",
                "file_hash": "a1b2c3d4e5f6",
                "download_count": 5,
                "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
                "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
                "preview_url": "/preview/550e8400-e29b-41d4-a716-446655440000"
            }
        }


# MIME type validation function
def _is_valid_mime_type(mime_type: str) -> bool:
    """Validate MIME type format."""
    import re
    # MIME type format: type/subtype
    # type and subtype should contain only alphanumeric characters, hyphens, and dots
    pattern = r'^[a-zA-Z0-9\-\.]+\/[a-zA-Z0-9\-\.]+$'
    return bool(re.match(pattern, mime_type))


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    summary="파일 업로드 (API 키 필요)",
    description="""
## 📤 파일 업로드 (인증 필요)

파일을 시스템에 업로드하고 저장합니다.

### 🔒 인증
- **X-API-Key** 헤더에 유효한 API 키가 필요합니다

### 🔧 사용 방법
1. **multipart/form-data** 형식으로 파일을 전송
2. **X-API-Key** 헤더에 API 키 포함
3. **파일 크기 제한**: 최대 100MB
4. **지원 형식**: 모든 파일 형식 지원
5. **자동 생성**: 고유 파일 ID, 저장 경로, 해시값

### 📋 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "accept: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@example.txt"
```

### ✅ 응답 예시
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.txt",
  "file_size": 1024,
  "upload_time": "2025-08-25T01:00:00",
  "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
  "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
  "message": "파일이 성공적으로 업로드되었습니다"
}
```

### ⚠️ 주의사항
- 빈 파일은 업로드할 수 없습니다
- 파일명이 없는 경우 오류가 발생합니다
- 파일 크기 제한을 초과하면 413 에러가 반환됩니다
    """,
    responses={
        200: {
            "description": "파일 업로드 성공",
            "content": {
                "application/json": {
                    "example": {
                        "file_id": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "example.txt",
                        "file_size": 1024,
                        "upload_time": "2025-08-25T01:00:00",
                        "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
                        "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
                        "message": "파일이 성공적으로 업로드되었습니다"
                    }
                }
            }
        },
        400: {"description": "잘못된 요청 (파일명 없음, 빈 파일)"},
        401: {"description": "인증 실패 (API 키가 없거나 유효하지 않음)"},
        413: {"description": "파일 크기 초과 (100MB 제한)"},
        500: {"description": "서버 내부 오류"}
    }
)
async def upload_file(
    file: UploadFile = File(..., description="업로드할 파일"),
    db: AsyncSession = Depends(get_async_session),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """파일 업로드 endpoint"""
    # API 키 검증
    VALID_API_KEY = "dkpia_sdpALcQuO3lDmTy8hY_zwltJpYBRFRTmnRbKrSCMc_wML4Rq"

    if x_api_key != VALID_API_KEY:
        logger.warning(f"Invalid API key attempt for upload: {x_api_key}")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    try:
        logger.info(f"Starting file upload for: {file.filename}")
        
        # Basic file validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if file.size and file.size > config.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File size exceeds maximum allowed size of {config.max_file_size} bytes"
            )
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Determine file extension
        file_extension = Path(file.filename).suffix.lower() if file.filename else ""
        
        # Generate stored filename
        stored_filename = f"{file_id}{file_extension}"
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(config.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Full storage path
        storage_path = upload_dir / stored_filename
        
        # Save file to disk
        try:
            async with aiofiles.open(storage_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save file")
        
        # Get file size
        file_size = len(content)
        
        # Enhanced MIME type detection
        mime_type = file.content_type
        
        # If no MIME type from client, try to detect from filename
        if not mime_type or mime_type == 'application/octet-stream':
            mime_type = mimetypes.guess_type(file.filename)[0]
        
        # If still no MIME type, use extension-based detection
        if not mime_type:
            # Common image MIME type mapping
            extension_mime_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
                '.pdf': 'application/pdf',
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.json': 'application/json',
                '.xml': 'application/xml',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.zip': 'application/zip',
                '.rar': 'application/vnd.rar',
                '.7z': 'application/x-7z-compressed',
                '.tar': 'application/x-tar',
                '.gz': 'application/gzip',
                '.mp3': 'audio/mpeg',
                '.mp4': 'video/mp4',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.wav': 'audio/wav',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.xls': 'application/vnd.ms-excel',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.ppt': 'application/vnd.ms-powerpoint',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            }
            
            detected_mime = extension_mime_map.get(file_extension.lower())
            if detected_mime:
                mime_type = detected_mime
                logger.info(f"Auto-detected MIME type for {file_id}: {detected_mime}")
            else:
                mime_type = 'application/octet-stream'
        
        # Validate MIME type format
        if not _is_valid_mime_type(mime_type):
            logger.warning(f"Invalid MIME type format: {mime_type}")
            mime_type = 'application/octet-stream'
        
        # Log MIME type detection result
        logger.info(f"Final MIME type for {file_id}: {mime_type} (original: {file.content_type})")
        
        # Calculate file hash (simple implementation)
        file_hash = str(hash(content))[:16]
        
        # Create file info record
        file_info = FileInfo(
            file_uuid=file_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_size=file_size,
            mime_type=mime_type,
            file_extension=file_extension,
            storage_path=str(storage_path),
            file_hash=file_hash,
            created_at=datetime.now()
        )
        
        # Save to database
        db.add(file_info)
        await db.commit()
        
        logger.info(f"File uploaded successfully: {file_id}, size: {file_size} bytes")
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=file_size,
            upload_time=file_info.created_at,
            download_url=f"/download/{file_id}",
            view_url=f"/view/{file_id}",
            message="파일이 성공적으로 업로드되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post(
    "/test-upload", 
    response_model=dict,
    summary="테스트 파일 업로드",
    description="""
## 🧪 테스트 파일 업로드

개발 및 테스트 목적으로 파일 업로드를 시뮬레이션합니다.

### 🔧 사용 방법
- 실제 파일 저장 없이 업로드 과정만 테스트
- 데이터베이스에 저장되지 않음
- 파일 정보만 반환

### 📋 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/test-upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.txt"
```

### ✅ 응답 예시
```json
{
  "message": "테스트 업로드 성공",
  "filename": "test.txt",
  "file_size": 1024,
  "content_type": "text/plain",
  "timestamp": "2025-08-25T01:00:00"
}
    """,
    responses={
        200: {"description": "테스트 업로드 성공"},
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 내부 오류"}
    }
)
async def test_upload(
    file: UploadFile = File(..., description="테스트용 파일"),
    db: AsyncSession = Depends(get_async_session)
):
    """테스트 업로드 endpoint"""
    try:
        logger.info(f"Test upload for: {file.filename}")
        
        # Basic validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Simple response for testing
        return {
            "message": "테스트 업로드 성공",
            "filename": file.filename,
            "file_size": file_size,
            "content_type": file.content_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test upload failed: {str(e)}")


@router.get(
    "/files/{file_id}", 
    response_model=FileInfoResponse,
    summary="파일 정보 조회",
    description="""
## 📄 파일 정보 조회

특정 파일의 상세 정보를 조회합니다.

### 🔧 사용 방법
1. **파일 ID**: URL 경로에 파일 ID 입력
2. **응답**: 파일 메타데이터 및 통계 정보
3. **상태 확인**: 삭제된 파일은 404 에러 반환

### 📋 요청 예시
```bash
curl -X GET "http://localhost:8000/api/v1/files/550e8400-e29b-41d4-a716-446655440000" \
  -H "accept: application/json"
```

### ✅ 응답 예시
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.txt",
  "file_size": 1024,
  "mime_type": "text/plain",
  "upload_time": "2025-08-25T01:00:00",
  "file_hash": "a1b2c3d4e5f6",
  "download_count": 5
}
```

### ⚠️ 주의사항
- 존재하지 않는 파일 ID는 404 에러 반환
- 삭제된 파일은 조회할 수 없음
    """,
    responses={
        200: {"description": "파일 정보 조회 성공"},
        404: {"description": "파일을 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def get_file_info(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """파일 정보 조회 endpoint"""
    try:
        from sqlalchemy import select
        stmt = select(FileInfo).where(FileInfo.file_uuid == file_id)
        result = await db.execute(stmt)
        file_info = result.scalar_one_or_none()
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_info.is_deleted:
            raise HTTPException(status_code=404, detail="File has been deactivated")
        
        # 다운로드 횟수 조회 (향후 구현)
        download_count = 0  # TODO: Redis나 별도 테이블에서 조회
        
        # 이미지 파일 여부 확인
        is_image = (
            file_info.mime_type and 
            file_info.mime_type.startswith('image/')
        )
        
        return FileInfoResponse(
            file_id=file_info.file_uuid,
            filename=file_info.original_filename,
            file_size=file_info.file_size,
            mime_type=file_info.mime_type,
            upload_time=file_info.created_at,
            file_hash=file_info.file_hash,
            download_count=download_count,
            download_url=f"/download/{file_info.file_uuid}",
            view_url=f"/view/{file_info.file_uuid}",
            preview_url=f"/preview/{file_info.file_uuid}" if is_image else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get file info error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/files",
    summary="파일 목록 조회",
    description="""
## 📋 파일 목록 조회

업로드된 파일들의 목록을 페이지네이션과 정렬 옵션으로 조회합니다.

### 🔧 사용 방법

#### 📄 페이지네이션
- **page**: 페이지 번호 (기본값: 1)
- **limit**: 페이지당 파일 수 (기본값: 20, 최대: 100)

#### 🔄 정렬 옵션
- **sort_by**: 정렬 기준
  - `uploaded_at`: 업로드 시간 (기본값)
  - `filename`: 파일명
  - `size`: 파일 크기
- **order**: 정렬 순서
  - `asc`: 오름차순
  - `desc`: 내림차순 (기본값)

### 📋 요청 예시
```bash
# 기본 조회
curl -X GET "http://localhost:8000/api/v1/files"

# 페이지네이션
curl -X GET "http://localhost:8000/api/v1/files?page=2&limit=10"

# 정렬
curl -X GET "http://localhost:8000/api/v1/files?sort_by=filename&order=asc"

# 복합 옵션
curl -X GET "http://localhost:8000/api/v1/files?page=1&limit=50&sort_by=size&order=desc"
```

### ✅ 응답 예시
```json
{
  "files": [
    {
      "file_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "example.txt",
      "stored_filename": "550e8400-e29b-41d4-a716-446655440000.txt",
      "file_size": 1024,
      "file_size_human": "1,024 bytes",
      "mime_type": "text/plain",
      "file_extension": ".txt",
      "upload_time": "2025-08-25T01:00:00",
      "upload_time_iso": "2025-08-25T01:00:00",
      "file_hash": "a1b2c3d4e5f6",
      "storage_path": "uploads/550e8400-e29b-41d4-a716-446655440000.txt",
      "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
      "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
      "is_public": true,
      "is_deleted": false
    }
  ],
  "pagination": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  },
  "sorting": {
    "sort_by": "uploaded_at",
    "order": "desc"
  }
}
```

### 📊 응답 구조
- **files**: 파일 정보 배열
- **pagination**: 페이지네이션 정보
- **sorting**: 정렬 옵션 정보

### ⚠️ 주의사항
- 삭제된 파일은 목록에 포함되지 않음
- 페이지당 최대 100개 파일 조회 가능
- 정렬 기준이 잘못된 경우 기본값 사용
    """,
    responses={
        200: {"description": "파일 목록 조회 성공"},
        500: {"description": "서버 내부 오류"}
    }
)
async def list_files(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 파일 수 (최대 100)"),
    sort_by: str = Query("uploaded_at", description="정렬 기준: uploaded_at, filename, size"),
    order: str = Query("desc", description="정렬 순서: asc, desc"),
    db: AsyncSession = Depends(get_async_session)
):
    """파일 목록 조회 endpoint"""
    try:
        from sqlalchemy import select, desc, asc, func
        
        # 기본 쿼리 생성 (비활성화되지 않은 파일만)
        stmt = select(FileInfo).where(FileInfo.is_deleted == False)
        
        # 정렬 옵션 적용
        if sort_by == "filename":
            order_clause = asc(FileInfo.original_filename) if order == "asc" else desc(FileInfo.original_filename)
        elif sort_by == "size":
            order_clause = asc(FileInfo.file_size) if order == "asc" else desc(FileInfo.file_size)
        else:  # uploaded_at (기본값)
            order_clause = asc(FileInfo.created_at) if order == "asc" else desc(FileInfo.created_at)
        
        stmt = stmt.order_by(order_clause)
        
        # 전체 파일 수 조회 (비활성화되지 않은 파일만)
        count_stmt = select(func.count(FileInfo.id)).where(FileInfo.is_deleted == False)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()
        
        # 페이지네이션 계산
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)
        
        # 파일 조회
        result = await db.execute(stmt)
        files = result.scalars().all()
        
        # 총 페이지 수 계산
        total_pages = (total + limit - 1) // limit
        
        return {
            "files": [
                {
                    "file_id": f.file_uuid,
                    "filename": f.original_filename,
                    "stored_filename": f.stored_filename,
                    "file_size": f.file_size,
                    "file_size_human": f"{f.file_size:,} bytes",
                    "mime_type": f.mime_type,
                    "file_extension": f.file_extension,
                    "upload_time": f.created_at,
                    "upload_time_iso": f.created_at.isoformat() if f.created_at else None,
                    "file_hash": f.file_hash,
                    "storage_path": f.storage_path,
                    "download_url": f"/download/{f.file_uuid}",
                    "view_url": f"/view/{f.file_uuid}",
                    "is_public": getattr(f, 'is_public', None),
                    "is_deleted": getattr(f, 'is_deleted', False)
                }
                for f in files
            ],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "prev_page": page - 1 if page > 1 else None
            },
            "sorting": {
                "sort_by": sort_by,
                "order": order
            }
        }
        
    except Exception as e:
        logger.error(f"List files error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/files/{file_id}",
    summary="파일 비활성화 (소프트 삭제)",
    description="""
## 🗑️ 파일 비활성화 (소프트 삭제)

파일을 시스템에서 비활성화합니다. 실제 파일은 삭제되지 않고 접근만 차단됩니다.

### 🔧 사용 방법
1. **파일 ID**: URL 경로에 파일 ID 입력
2. **소프트 삭제**: 물리적 파일은 유지, 접근만 차단
3. **복구 가능**: 필요시 데이터베이스에서 복구 가능

### 📋 요청 예시
```bash
curl -X DELETE "http://localhost:8000/api/v1/files/550e8400-e29b-41d4-a716-446655440000" \
  -H "accept: application/json"
```

### ✅ 응답 예시
```json
{
  "message": "파일 550e8400-e29b-41d4-a716-446655440000이 성공적으로 비활성화되었습니다",
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.txt",
  "deactivated_at": "2025-08-25T01:00:00",
  "note": "파일은 삭제 표시되었지만 물리적 파일은 그대로 유지됩니다"
}
```

### ⚠️ 주의사항
- 존재하지 않는 파일 ID는 404 에러 반환
- 이미 비활성화된 파일은 400 에러 반환
- 물리적 파일은 삭제되지 않음
- 다운로드, 뷰어 등 모든 접근이 차단됨

### 🔄 복구 방법
필요시 데이터베이스에서 `is_deleted` 필드를 `false`로 변경하여 복구 가능
    """,
    responses={
        200: {"description": "파일 비활성화 성공"},
        400: {"description": "이미 비활성화된 파일"},
        404: {"description": "파일을 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def deactivate_file(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """파일 비활성화 endpoint"""
    try:
        from sqlalchemy import select, update
        
        # 파일 정보 조회
        stmt = select(FileInfo).where(FileInfo.file_uuid == file_id)
        result = await db.execute(stmt)
        file_info = result.scalar_one_or_none()
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_info.is_deleted:
            raise HTTPException(status_code=400, detail="File is already deactivated")
        
        # 파일 비활성화 로그 기록
        logger.info(f"File deactivation requested - ID: {file_id}, Filename: {file_info.original_filename}, Size: {file_info.file_size} bytes")
        
        # 파일을 비활성화 상태로 변경 (soft delete)
        update_stmt = update(FileInfo).where(FileInfo.file_uuid == file_id).values(
            is_deleted=True,
            updated_at=datetime.now()
        )
        await db.execute(update_stmt)
        await db.commit()
        
        logger.info(f"File {file_id} deactivated successfully")
        
        return {
            "message": f"파일 {file_id}이 성공적으로 비활성화되었습니다",
            "file_id": file_id,
            "filename": file_info.original_filename,
            "deactivated_at": datetime.now().isoformat(),
            "note": "파일은 삭제 표시되었지만 물리적 파일은 그대로 유지됩니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
