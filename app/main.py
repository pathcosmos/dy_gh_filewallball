"""
Simple FileWallBall API - Streamlined version without Redis/Docker dependencies
"""
import os
import mimetypes
from pathlib import Path
from typing import List, Optional
import uuid
from datetime import datetime

import aiofiles
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, Depends, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_async_session
from app.config import get_settings
from app.models.orm_models import FileInfo
from app.services.file_storage_service import FileStorageService
from app.services.file_validation_service import FileValidationService
from app.services.project_key_service import ProjectKeyService
from app.utils.logging_config import get_logger

# V1 API imports removed - using simplified endpoints only

# Initialize logger
logger = get_logger(__name__)

# Get configuration
config = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="FileWallBall API",
    description="Simple file upload and management system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response models
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    upload_time: datetime
    download_url: str
    view_url: str
    message: str


class FileInfoResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    mime_type: Optional[str]
    upload_time: datetime
    file_hash: Optional[str]
    download_count: int = 0


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str
    version: str


class KeygenRequest(BaseModel):
    project_name: str
    request_date: str  # YYYYMMDD format


class KeygenResponse(BaseModel):
    project_id: int
    project_name: str
    project_key: str
    request_date: str
    message: str


# MIME type validation function
def _is_valid_mime_type(mime_type: str) -> bool:
    """Validate MIME type format."""
    import re
    # MIME type format: type/subtype
    # type and subtype should contain only alphanumeric characters, hyphens, and dots
    pattern = r'^[a-zA-Z0-9\-\.]+\/[a-zA-Z0-9\-\.]+$'
    return bool(re.match(pattern, mime_type))

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        service="FileWallBall API",
        version="2.0.0"
    )


@app.post("/keygen", response_model=KeygenResponse)
async def generate_project_key(
    request_data: KeygenRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    keygen_auth: str = Header(None, alias="X-Keygen-Auth")
):
    """
    Generate project key endpoint.
    Creates a new project and returns the generated project key.
    
    Args:
        request_data: Project name and request date
        request: FastAPI request object for IP extraction
        db: Database session
        keygen_auth: Special keygen authentication header
    
    Returns:
        KeygenResponse: Generated project information and key
    """
    try:
        # Validate keygen authentication header
        KEYGEN_AUTH_VALUE = "dy2025@fileBucket"
        if keygen_auth != KEYGEN_AUTH_VALUE:
            raise HTTPException(
                status_code=401,
                detail="Invalid keygen authentication header"
            )
        
        # Validate date format (YYYYMMDD)
        if len(request_data.request_date) != 8 or not request_data.request_date.isdigit():
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYYMMDD format"
            )
        
        # Validate project name
        if not request_data.project_name or len(request_data.project_name.strip()) < 2:
            raise HTTPException(
                status_code=400,
                detail="Project name must be at least 2 characters long"
            )
        
        # Get client IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Initialize project key service
        project_service = ProjectKeyService(db)
        
        # Create project key
        project = await project_service.create_project_key(
            project_name=request_data.project_name.strip(),
            request_date=request_data.request_date,
            request_ip=client_ip
        )
        
        logger.info(f"Project key generated: {project.id} for {request_data.project_name}")
        
        return KeygenResponse(
            project_id=project.id,
            project_name=project.project_name,
            project_key=project.project_key,
            request_date=project.request_date,
            message="Project key generated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Keygen error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate project key"
        )


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session)
):
    """Simplified file upload endpoint."""
    try:
        logger.info(f"Starting file upload for: {file.filename}")
        
        # Basic file validation
        if not file.filename:
            logger.error("No filename provided")
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file size (100MB limit)
        max_size = 100 * 1024 * 1024  # 100MB
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"File size: {file_size} bytes")
        
        if file_size > max_size:
            logger.error(f"File too large: {file_size} bytes")
            raise HTTPException(status_code=413, detail="File too large (max 100MB)")
        
        if file_size == 0:
            logger.error("Empty file")
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Reset file pointer
        await file.seek(0)
        
        # Generate file UUID
        file_uuid = str(uuid.uuid4())
        logger.info(f"Generated file UUID: {file_uuid}")
        
        # Get file extension and mime type
        file_extension = Path(file.filename).suffix.lower()
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        
        # Validate MIME type format (temporarily disabled for debugging)
        # if mime_type and not _is_valid_mime_type(mime_type):
        #     logger.error(f"Invalid MIME type: {mime_type}")
        #     raise HTTPException(status_code=400, detail=f"Invalid MIME type: {mime_type}")
        
        logger.info(f"File extension: {file_extension}, MIME type: {mime_type}")
        
        # Calculate file hash
        import hashlib
        file_hash = hashlib.sha256(content).hexdigest()
        logger.info(f"File hash: {file_hash}")
        
        # Create storage path
        upload_dir = Path("uploads")  # Simplified for debugging
        logger.info(f"Upload directory: {upload_dir}")
        
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory created/verified: {upload_dir}")
        
        # Save file
        stored_filename = f"{file_uuid}{file_extension}"
        file_path = upload_dir / stored_filename
        logger.info(f"Storing file at: {file_path}")
        
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"File saved successfully to: {file_path}")
        
        # Save to database
        logger.info("Saving file info to database...")
        file_info = FileInfo(
            file_uuid=file_uuid,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_extension=file_extension,
            mime_type=mime_type,
            file_size=file_size,
            file_hash=file_hash,
            storage_path=str(file_path)
        )
        
        db.add(file_info)
        await db.commit()
        logger.info("File info saved to database successfully")
        
        return FileUploadResponse(
            file_id=file_uuid,
            filename=file.filename,
            file_size=file_size,
            upload_time=datetime.now(),
            download_url=f"/download/{file_uuid}",
            view_url=f"/view/{file_uuid}",
            message="File uploaded successfully"
        )
        
    except HTTPException:
        logger.error("HTTPException occurred during upload")
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")


@app.post("/test-upload", response_model=dict)
async def test_upload_file(
    file: UploadFile = File(...)
):
    """Test file upload without database."""
    try:
        logger.info(f"Starting test file upload for: {file.filename}")
        
        # Basic file validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"File size: {file_size} bytes")
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Get MIME type
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        logger.info(f"MIME type: {mime_type}")
        
        return {
            "filename": file.filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "message": "Test upload successful"
        }
        
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory created/verified: {upload_dir}")
        
        # Save file
        stored_filename = f"{file_uuid}{file_extension}"
        file_path = upload_dir / stored_filename
        logger.info(f"Storing file at: {file_path}")
        
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"File saved successfully to: {file_path}")
        
        return {
            "file_id": file_uuid,
            "filename": file.filename,
            "file_size": file_size,
            "upload_time": datetime.now().isoformat(),
            "file_path": str(file_path),
            "message": "File uploaded successfully (test mode)"
        }
        
    except HTTPException:
        logger.error("HTTPException occurred during test upload")
        raise
    except Exception as e:
        logger.error(f"Test upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test upload failed: {str(e)}")


@app.get("/files/{file_id}", response_model=FileInfoResponse)
async def get_file_info(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """Get file information."""
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
        
        return FileInfoResponse(
            file_id=file_info.file_uuid,
            filename=file_info.original_filename,
            file_size=file_info.file_size,
            mime_type=file_info.mime_type,
            upload_time=file_info.created_at,
            file_hash=file_info.file_hash,
            download_count=download_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get file info error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/download/{file_id}")
async def download_file(file_id: str, db: AsyncSession = Depends(get_async_session)):
    """Download a file."""
    try:
        from sqlalchemy import select
        stmt = select(FileInfo).where(FileInfo.file_uuid == file_id)
        result = await db.execute(stmt)
        file_info = result.scalar_one_or_none()
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_info.is_deleted:
            raise HTTPException(status_code=404, detail="File has been deactivated")
        
        file_path = Path(file_info.storage_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Physical file not found")
        
        return FileResponse(
            path=file_path,
            filename=file_info.original_filename,
            media_type=file_info.mime_type or 'application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/view/{file_id}")
async def view_file(file_id: str, db: AsyncSession = Depends(get_async_session)):
    """View file content (for text files) or stream image files."""
    try:
        from sqlalchemy import select
        stmt = select(FileInfo).where(FileInfo.file_uuid == file_id)
        result = await db.execute(stmt)
        file_info = result.scalar_one_or_none()
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_info.storage_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Physical file not found")
        
        # Check if file is image-based
        if file_info.mime_type and file_info.mime_type.startswith('image/'):
            # Stream image file for viewing
            logger.info(f"Streaming image file: {file_id}, type: {file_info.mime_type}")
            return FileResponse(
                path=file_path,
                media_type=file_info.mime_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 1시간 캐시
                    "Accept-Ranges": "bytes",
                }
            )
        
        # Check if file is text-based
        if not file_info.mime_type or not file_info.mime_type.startswith('text/'):
            # Return file info instead of content for non-text files
            return {
                "file_id": file_info.id,
                "filename": file_info.original_filename,
                "mime_type": file_info.mime_type,
                "message": "File is not text-based or image. Use /download endpoint instead."
            }
        
        # Read and return text content
        async with aiofiles.open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
            return {
                "file_id": file_info.id,
                "filename": file_info.original_filename,
                "content": content[:1000],  # Limit to first 1000 chars
                "truncated": len(content) > 1000
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"View error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/preview/{file_id}")
async def preview_image(
    file_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Preview image files with optimized streaming."""
    try:
        from sqlalchemy import select
        
        # 파일 정보 조회
        stmt = select(FileInfo).where(FileInfo.file_uuid == file_id)
        result = await db.execute(stmt)
        file_info = result.scalar_one_or_none()
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 이미지 파일인지 확인
        if not file_info.mime_type or not file_info.mime_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail=f"File is not an image. MIME type: {file_info.mime_type}"
            )
        
        file_path = Path(file_info.storage_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Physical file not found")
        
        logger.info(f"Image preview requested: {file_id}, type: {file_info.mime_type}")
        
        # 이미지 프리뷰를 위한 스트리밍 응답
        return FileResponse(
            path=file_path,
            media_type=file_info.mime_type,
            headers={
                "Cache-Control": "public, max-age=1800",  # 30분 캐시 (프리뷰용)
                "Accept-Ranges": "bytes",
                "X-Image-Preview": "true",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image preview error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/thumbnail/{file_id}")
async def get_image_thumbnail(
    file_id: str, 
    size: str = Query("medium", description="썸네일 크기 (small, medium, large)"),
    db: AsyncSession = Depends(get_async_session)
):
    """Get image thumbnail for image files."""
    try:
        from sqlalchemy import select
        
        # 파일 정보 조회
        stmt = select(FileInfo).where(FileInfo.file_uuid == file_id)
        result = await db.execute(stmt)
        file_info = result.scalar_one_or_none()
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 이미지 파일인지 확인
        if not file_info.mime_type or not file_info.mime_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail=f"File is not an image. MIME type: {file_info.mime_type}"
            )
        
        file_path = Path(file_info.storage_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Physical file not found")
        
        # 썸네일 크기 설정 (실제로는 이미지 리사이징 로직이 필요하지만, 여기서는 원본 반환)
        logger.info(f"Thumbnail requested for image: {file_id}, size: {size}")
        
        # TODO: 실제 썸네일 생성 로직 구현
        # 현재는 원본 이미지를 반환 (Pillow 등을 사용하여 리사이징 구현 필요)
        
        return FileResponse(
            path=file_path,
            media_type=file_info.mime_type,
            headers={
                "Cache-Control": "public, max-age=7200",  # 2시간 캐시
                "Accept-Ranges": "bytes",
                "X-Thumbnail-Size": size,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thumbnail error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/files")
async def list_files(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of files per page"),
    sort_by: str = Query("uploaded_at", description="Sort by: uploaded_at, filename, size"),
    order: str = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_async_session)
):
    """List uploaded files with sorting and pagination."""
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


@app.delete("/files/{file_id}")
async def deactivate_file(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """Deactivate a file (soft delete)."""
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
            "message": f"File {file_id} deactivated successfully",
            "file_id": file_id,
            "filename": file_info.original_filename,
            "deactivated_at": datetime.now().isoformat(),
            "note": "File is marked as deleted but physical file remains intact"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


# V1 API routers removed - using simplified endpoints only


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logger.info("FileWallBall API starting up...")
    
    # Ensure upload directory exists
    upload_dir = Path(config.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Upload directory: {upload_dir}")
    logger.info("FileWallBall API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    logger.info("FileWallBall API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)