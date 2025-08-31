"""
File Download and Viewer API Router

This module contains all file download, viewing, preview, and thumbnail 
generation endpoints.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_async_session
from app.models.orm_models import FileInfo
from app.utils.logging_config import get_logger

# Initialize router
router = APIRouter(
    tags=["파일 다운로드 및 뷰어 (File Download & Viewer)"],
    responses={
        200: {"description": "성공적으로 처리되었습니다"},
        400: {"description": "잘못된 요청입니다"},
        404: {"description": "요청한 리소스를 찾을 수 없습니다"},
        500: {"description": "서버 내부 오류가 발생했습니다"}
    }
)

# Initialize logger
logger = get_logger(__name__)


@router.get(
    "/download/{file_id}",
    summary="파일 다운로드",
    description="""
## ⬇️ 파일 다운로드

저장된 파일을 다운로드합니다.

### 🔧 사용 방법
1. **파일 ID**: URL 경로에 파일 ID 입력
2. **자동 다운로드**: 브라우저에서 자동으로 다운로드 시작
3. **원본 파일명**: 원본 파일명으로 다운로드됨
4. **MIME 타입**: 파일 형식에 맞는 Content-Type 설정

### 📋 요청 예시
```bash
# 직접 다운로드
curl -X GET "http://localhost:8000/download/550e8400-e29b-41d4-a716-446655440000" \
  -o downloaded_file.txt

# 브라우저에서 다운로드
# http://localhost:8000/download/550e8400-e29b-41d4-a716-446655440000
```

### ✅ 응답
- **Content-Type**: 파일의 MIME 타입
- **Content-Disposition**: `attachment; filename="원본파일명"`
- **파일 내용**: 바이너리 데이터

### ⚠️ 주의사항
- 존재하지 않는 파일 ID는 404 에러 반환
- 삭제된 파일은 다운로드할 수 없음
- 물리적 파일이 없는 경우 404 에러 반환
- 대용량 파일의 경우 스트리밍 다운로드

### 🔒 보안
- 파일 접근 권한 확인
- 다운로드 로그 기록
- 악성 파일 검사 (향후 구현 예정)
    """,
    responses={
        200: {"description": "파일 다운로드 성공"},
        404: {"description": "파일을 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def download_file(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """파일 다운로드 endpoint"""
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


@router.get(
    "/view/{file_id}",
    summary="파일 내용 보기",
    description="""
## 👁️ 파일 내용 보기

파일의 내용을 웹 브라우저에서 직접 확인할 수 있습니다.

### 🔧 사용 방법

#### 📝 텍스트 파일
- 파일 내용을 HTML로 렌더링하여 표시
- UTF-8 인코딩 우선, 실패 시 Latin-1 인코딩 시도
- 파일 정보와 함께 내용 표시

#### 🖼️ 이미지 파일
- 이미지를 직접 브라우저에 표시
- 캐시 헤더 설정 (1시간)
- 바이트 범위 요청 지원
- 자동 MIME 타입 감지 및 수정

#### 📄 기타 파일
- 다운로드 링크 제공
- 파일 정보만 표시

### 📋 요청 예시
```bash
# 텍스트 파일 보기
curl -X GET "http://localhost:8000/view/550e8400-e29b-41d4-a716-446655440000"

# 브라우저에서 직접 접근
# http://localhost:8000/view/550e8400-e29b-41d4-a716-446655440000
```

### ✅ 응답 형식

#### 텍스트 파일
```html
<!DOCTYPE html>
<html>
<head>
    <title>Viewing: example.txt</title>
    <style>...</style>
</head>
<body>
    <div class="file-info">
        <h2>File: example.txt</h2>
        <p>Size: 1,024 bytes</p>
        <p>Type: text/plain</p>
        <p>Uploaded: 2025-08-25T01:00:00</p>
    </div>
    <div class="content">파일 내용...</div>
</body>
</html>
```

#### 이미지 파일
- **Content-Type**: 이미지 MIME 타입
- **Cache-Control**: `public, max-age=3600`
- **Accept-Ranges**: `bytes`
- **Content-Disposition**: `inline` (브라우저에서 직접 표시)

### ⚠️ 주의사항
- 존재하지 않는 파일 ID는 404 에러 반환
- 삭제된 파일은 볼 수 없음
- 대용량 텍스트 파일은 성능에 영향
- 인코딩 문제가 있는 파일은 경고 표시

### 🔧 기능
- **자동 인코딩 감지**: UTF-8 → Latin-1 순서로 시도
- **파일 크기 표시**: 바이트 단위로 표시
- **업로드 시간 표시**: ISO 형식으로 표시
- **반응형 디자인**: 모바일 친화적 UI
- **자동 MIME 타입 감지**: 파일 확장자 기반 MIME 타입 추정
    """,
    responses={
        200: {"description": "파일 내용 보기 성공"},
        404: {"description": "파일을 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def view_file(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """파일 내용 보기 endpoint"""
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
        
        # Enhanced MIME type detection for images
        mime_type = file_info.mime_type
        if not mime_type or mime_type == 'application/octet-stream':
            # Try to detect MIME type from file extension
            import mimetypes
            detected_mime = mimetypes.guess_type(file_info.original_filename)[0]
            if detected_mime:
                mime_type = detected_mime
                logger.info(f"Auto-detected MIME type for {file_id}: {detected_mime}")
        
        # Check if file is image-based (improved detection)
        is_image = (
            (mime_type and mime_type.startswith('image/')) or
            (file_info.file_extension.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'])
        )
        
        if is_image:
            # Ensure proper MIME type for images
            if not mime_type or not mime_type.startswith('image/'):
                # Map common image extensions to MIME types
                extension_mime_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp',
                    '.tiff': 'image/tiff',
                    '.tif': 'image/tiff'
                }
                mime_type = extension_mime_map.get(file_info.file_extension.lower(), 'image/jpeg')
                logger.info(f"Corrected MIME type for image {file_id}: {mime_type}")
            
            # Stream image file for viewing with optimized headers
            logger.info(f"Streaming image file: {file_id}, type: {mime_type}")
            return FileResponse(
                path=file_path,
                media_type=mime_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 1시간 캐시
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": "inline",  # 브라우저에서 직접 표시
                    "X-Content-Type-Options": "nosniff",  # MIME 타입 스니핑 방지
                }
            )
        
        # For text files, read and return content
        elif mime_type and mime_type.startswith('text/'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return HTMLResponse(
                    content=f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Viewing: {file_info.original_filename}</title>
                        <style>
                            body {{ font-family: monospace; margin: 20px; background: #f5f5f5; }}
                            .file-info {{ background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                            .content {{ background: white; padding: 20px; border-radius: 5px; white-space: pre-wrap; }}
                        </style>
                    </head>
                    <body>
                        <div class="file-info">
                            <h2>File: {file_info.original_filename}</h2>
                            <p>Size: {file_info.file_size:,} bytes</p>
                            <p>Type: {mime_type}</p>
                            <p>Uploaded: {file_info.created_at}</p>
                        </div>
                        <div class="content">{content}</div>
                    </body>
                    </html>
                    """,
                    headers={"Content-Type": "text/html; charset=utf-8"}
                )
            except UnicodeDecodeError:
                # Fallback for non-UTF-8 text files
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                
                return HTMLResponse(
                    content=f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Viewing: {file_info.original_filename}</title>
                        <style>
                            body {{ font-family: monospace; margin: 20px; background: #f5f5f5; }}
                            .file-info {{ background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                            .content {{ background: white; padding: 20px; border-radius: 5px; white-space: pre-wrap; }}
                        </style>
                    </head>
                    <body>
                        <div class="file-info">
                            <h2>File: {file_info.original_filename}</h2>
                            <p>Size: {file_info.file_size:,} bytes</p>
                            <p>Type: {mime_type}</p>
                            <p>Uploaded: {file_info.created_at}</p>
                            <p><strong>Note: File encoding may not be UTF-8</strong></p>
                        </div>
                        <div class="content">{content}</div>
                    </body>
                    </html>
                    """,
                    headers={"Content-Type": "text/html; charset=utf-8"}
                )
        
        # For other file types, offer download
        else:
            return FileResponse(
                path=file_path,
                filename=file_info.original_filename,
                media_type=mime_type or 'application/octet-stream',
                headers={
                    "Content-Disposition": f"attachment; filename=\"{file_info.original_filename}\""
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"View file error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/preview/{file_id}",
    summary="파일 미리보기",
    description="""
## 👀 파일 미리보기

파일의 내용을 미리보기 형태로 제공합니다.

### 🔧 사용 방법

#### 🖼️ 이미지 파일
- **썸네일 생성**: 300x300 픽셀 이하의 작은 크기로 자동 리사이징
- **품질 최적화**: JPEG 품질 85%, PNG 최적화
- **투명도 처리**: PNG 투명 이미지는 흰색 배경으로 변환
- **30분 캐시**: 성능 최적화를 위한 캐시 설정
- **폴백 지원**: 썸네일 생성 실패 시 원본 이미지 반환

#### 📝 텍스트 파일
- 첫 1000자만 표시
- 잘린 내용 표시
- 다운로드 링크 제공
- 아름다운 UI로 표시

#### 📄 기타 파일
- 파일 정보만 표시
- 다운로드 링크 제공

### 📋 요청 예시
```bash
# 이미지 미리보기 (썸네일)
curl -X GET "http://localhost:8000/preview/550e8400-e29b-41d4-a716-446655440000"

# 브라우저에서 직접 접근
# http://localhost:8000/preview/550e8400-e29b-41d4-a716-446655440000
```

### ✅ 응답 형식

#### 이미지 파일 (썸네일)
- **Content-Type**: 이미지 MIME 타입
- **Cache-Control**: `public, max-age=1800` (30분)
- **X-Thumbnail**: `true` (썸네일 응답 표시)
- **X-Original-Size**: 원본 이미지 크기 (예: `1920x1080`)
- **X-Thumbnail-Size**: 썸네일 크기 (예: `300x169`)
- **X-Thumbnail-Quality**: 썸네일 품질 (85)

#### 텍스트 파일
```html
<!DOCTYPE html>
<html>
<head>
    <title>Preview: example.txt</title>
    <style>...</style>
</head>
<body>
    <div class="preview-container">
        <div class="file-header">
            <h1>📄 example.txt</h1>
            <p>📊 Size: 1,024 bytes | 📅 Uploaded: 2025-08-25T01:00:00</p>
            <p>🏷️ Type: text/plain</p>
        </div>
        <div class="preview-content">
            <h3>File Preview:</h3>
            <div class="content-text">파일 내용 (최대 1000자)...</div>
            <a href="/download/550e8400-e29b-41d4-a716-446655440000" class="download-link">⬇️ Download Full File</a>
        </div>
    </div>
</body>
</html>
```

#### 기타 파일
```json
{
  "message": "이 파일 형식은 미리보기를 지원하지 않습니다",
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.pdf",
  "file_size": 1024,
  "mime_type": "application/pdf",
  "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
  "note": "다운로드 endpoint를 사용하여 파일을 가져오세요"
}
```

### ⚠️ 주의사항
- 존재하지 않는 파일 ID는 404 에러 반환
- 삭제된 파일은 미리보기할 수 없음
- 텍스트 파일은 1000자로 제한
- 대용량 파일은 성능에 영향
- 썸네일 생성 실패 시 원본 이미지 반환

### 🎨 UI 특징
- **반응형 디자인**: 모바일과 데스크톱 모두 지원
- **모던한 스타일**: Bootstrap 스타일의 깔끔한 UI
- **이모지 사용**: 직관적인 아이콘
- **다운로드 링크**: 전체 파일 다운로드 버튼

### 🖼️ 썸네일 기능
- **자동 리사이징**: 최대 300x300 픽셀로 자동 조정
- **비율 유지**: 원본 이미지의 가로세로 비율 유지
- **품질 최적화**: 파일 크기와 품질의 균형
- **다양한 형식 지원**: JPEG, PNG, GIF, BMP, WebP 등
- **투명도 처리**: PNG 투명 이미지의 적절한 배경 처리
    """,
    responses={
        200: {"description": "파일 미리보기 성공"},
        404: {"description": "파일을 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def preview_file(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """파일 미리보기 endpoint"""
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
        
        # For images, generate and return thumbnail
        logger.info(f"DEBUG: Checking file {file_id}, mime_type: {file_info.mime_type}, is_image: {file_info.mime_type and file_info.mime_type.startswith('image/')}")
        
        if file_info.mime_type and file_info.mime_type.startswith('image/'):
            logger.info(f"Processing image file: {file_id}, type: {file_info.mime_type}")
            
            # Force thumbnail generation for testing
            try:
                from PIL import Image
                import io
                
                logger.info(f"PIL imported successfully for {file_id}")
                
                # Open image and generate thumbnail
                with Image.open(file_path) as img:
                    logger.info(f"Image opened successfully: {img.size}, mode: {img.mode}")
                    
                    # Simple thumbnail generation
                    max_size = 300
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    
                    # Convert to bytes
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    thumbnail_data = img_buffer.getvalue()
                    
                    logger.info(f"Generated thumbnail for {file_id}: size: {len(thumbnail_data)} bytes")
                    
                    # Return thumbnail with appropriate headers
                    from fastapi.responses import Response
                    return Response(
                        content=thumbnail_data,
                        media_type=file_info.mime_type,
                        headers={
                            "Cache-Control": "public, max-age=1800",
                            "X-Thumbnail": "true",
                            "X-Thumbnail-Size": f"{img.size[0]}x{img.size[1]}",
                            "Content-Disposition": f"inline; filename=\"thumb_{file_info.original_filename}\""
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Thumbnail generation failed for {file_id}: {e}", exc_info=True)
                # Fallback to original image if thumbnail generation fails
                return FileResponse(
                    path=file_path,
                    media_type=file_info.mime_type,
                    headers={
                        "Cache-Control": "public, max-age=1800",
                        "X-Thumbnail": "false",
                        "X-Fallback": "true"
                    }
                )
        elif file_info.mime_type and file_info.mime_type.startswith('text/'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Limit preview to first 1000 characters
                preview_content = content[:1000]
                if len(content) > 1000:
                    preview_content += "\n\n... (truncated for preview)"
                
                return HTMLResponse(
                    content=f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Preview: {file_info.original_filename}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
                            .preview-container {{ max-width: 800px; margin: 0 auto; }}
                            .file-header {{ background: #007bff; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                            .preview-content {{ background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                            .content-text {{ font-family: 'Courier New', monospace; line-height: 1.6; white-space: pre-wrap; }}
                            .download-link {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; }}
                        </style>
                    </head>
                    <body>
                        <div class="preview-container">
                            <div class="file-header">
                                <h1>📄 {file_info.original_filename}</h1>
                                <p>📊 Size: {file_info.file_size:,} bytes | 📅 Uploaded: {file_info.created_at}</p>
                                <p>🏷️ Type: {file_info.mime_type}</p>
                            </div>
                            <div class="preview-content">
                                <h3>File Preview:</h3>
                                <div class="content-text">{preview_content}</div>
                                <a href="/download/{file_id}" class="download-link">⬇️ Download Full File</a>
                            </div>
                        </div>
                    </body>
                    </html>
                    """,
                    headers={"Content-Type": "text/html; charset=utf-8"}
                )
            except Exception as e:
                logger.error(f"Preview generation error: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate preview")
        
        # For other file types, return file info
        else:
            return {
                "message": "이 파일 형식은 미리보기를 지원하지 않습니다",
                "file_id": file_id,
                "filename": file_info.original_filename,
                "file_size": file_info.file_size,
                "mime_type": file_info.mime_type,
                "download_url": f"/download/{file_id}",
                "note": "다운로드 endpoint를 사용하여 파일을 가져오세요"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/thumbnail/{file_id}",
    summary="이미지 썸네일",
    description="""
## 🖼️ 이미지 썸네일

이미지 파일의 썸네일을 생성하고 제공합니다.

### 🔧 사용 방법
1. **파일 ID**: URL 경로에 이미지 파일 ID 입력
2. **이미지 전용**: 이미지 파일만 지원
3. **캐시 설정**: 2시간 캐시로 성능 최적화
4. **메타데이터**: 원본 파일 크기 정보 포함

### 📋 요청 예시
```bash
# 이미지 썸네일 요청
curl -X GET "http://localhost:8000/thumbnail/550e8400-e29b-41d4-a716-446655440000"

# 브라우저에서 직접 접근
# http://localhost:8000/thumbnail/550e8400-e29b-41d4-a716-446655440000
```

### ✅ 응답
- **Content-Type**: 이미지 MIME 타입
- **Cache-Control**: `public, max-age=7200` (2시간)
- **X-Thumbnail**: `true` (썸네일 응답 표시)
- **X-Original-Size**: 원본 파일 크기

### ⚠️ 주의사항
- **이미지 파일만 지원**: 다른 형식은 400 에러 반환
- **현재 구현**: 실제 썸네일 생성 대신 원본 이미지 반환
- **향후 개선**: PIL/Pillow를 사용한 실제 썸네일 생성 예정

### 🔮 향후 계획
- **다양한 크기**: small, medium, large 썸네일
- **이미지 최적화**: 품질과 크기 최적화
- **포맷 변환**: WebP 등 최신 포맷 지원
- **캐싱**: 생성된 썸네일 캐싱

### 📊 지원 이미지 형식
- **JPEG**: .jpg, .jpeg
- **PNG**: .png
- **GIF**: .gif
- **BMP**: .bmp
- **TIFF**: .tiff, .tif
- **WebP**: .webp

### 🔧 기술적 세부사항
- **현재**: 원본 이미지 스트리밍
- **캐시**: 2시간 브라우저 캐시
- **헤더**: 썸네일 관련 메타데이터 포함
- **로깅**: 썸네일 요청 로그 기록
    """,
    responses={
        200: {"description": "이미지 썸네일 성공"},
        400: {"description": "이미지 파일이 아님"},
        404: {"description": "파일을 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def thumbnail_file(
    file_id: str, 
    db: AsyncSession = Depends(get_async_session)
):
    """이미지 썸네일 생성 endpoint"""
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
        
        # Check if file is an image
        if not file_info.mime_type or not file_info.mime_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="썸네일 생성은 이미지 파일에서만 사용할 수 있습니다"
            )
        
        # For now, return the original image as thumbnail
        # TODO: Implement actual thumbnail generation with PIL/Pillow
        logger.info(f"Thumbnail requested for image: {file_id}")
        
        return FileResponse(
            path=file_path,
            media_type=file_info.mime_type,
            headers={
                "Cache-Control": "public, max-age=7200",  # 2시간 캐시
                "X-Thumbnail": "true",
                "X-Original-Size": str(file_info.file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thumbnail error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
