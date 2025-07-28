import os
import uuid
import aiofiles
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import (
    FastAPI, File, UploadFile, HTTPException, BackgroundTasks, 
    Request, Depends
)
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.error_handler_service import ErrorHandlerService
from app.services.file_storage_service import FileStorageService
from app.services.metadata_service import MetadataService
from app.services.rate_limiter_service import RateLimiterService
from app.models.orm_models import FileInfo
from app.models.api_models import (
    FileUploadResponse, FileDuplicateResponse, FileInfoResponse,
    UploadStatisticsResponse, ErrorResponse, HealthCheckResponse,
    MetricsResponse, ErrorStatisticsResponse
)
from app.routers.ip_auth_router import router as ip_auth_router

# Redis 연결
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', 'filewallball2024'),
    decode_responses=True
)

app = FastAPI(title="File Management API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(ip_auth_router)

# 메트릭 설정
file_upload_counter = Counter(
    'file_uploads_total', 'Total number of file uploads'
)
file_download_counter = Counter(
    'file_downloads_total', 'Total number of file downloads'
)
file_upload_duration = Histogram(
    'file_upload_duration_seconds', 'File upload duration'
)
file_upload_error_counter = Counter(
    'file_upload_errors_total', 
    'Total number of file upload errors', 
    ['error_type']
)

# 파일 저장 디렉토리
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    download_url: str
    view_url: str
    message: str

async def calculate_file_hash(file_id: str, file_path: Path):
    """백그라운드에서 파일 해시 계산"""
    try:
        import hashlib
        hash_md5 = hashlib.md5()
        async with aiofiles.open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()
        # Redis에 해시 저장
        redis_client.setex(f"hash:{file_id}", 86400, file_hash)
    except Exception as e:
        print(f"해시 계산 실패: {e}")

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """파일 업로드 API - 에러 처리 시스템 통합"""
    start_time = datetime.now()
    file_uuid = None
    error_handler = ErrorHandlerService(db, str(UPLOAD_DIR))
    
    try:
        # 파일 ID 생성
        file_uuid = str(uuid.uuid4())
        
        # 파일 확장자 추출
        file_extension = Path(file.filename).suffix if file.filename else ""
        
        # 저장할 파일명 생성
        saved_filename = f"{file_uuid}{file_extension}"
        file_path = UPLOAD_DIR / saved_filename
        
        # 파일 저장
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 파일 정보 저장
        file_info = {
            "file_id": file_uuid,
            "filename": file.filename,
            "size": len(content),
            "upload_time": datetime.now().isoformat(),
            "content_type": file.content_type,
            "saved_filename": saved_filename
        }
        
        # Redis에 파일 정보 저장 (24시간 만료)
        redis_client.setex(f"file:{file_uuid}", 86400, str(file_info))
        
        # URL 생성
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        download_url = f"{base_url}/download/{file_uuid}"
        view_url = f"{base_url}/view/{file_uuid}"
        
        # 메트릭 업데이트
        file_upload_counter.inc()
        file_upload_duration.observe((datetime.now() - start_time).total_seconds())
        
        # 백그라운드 작업: 파일 해시 계산
        background_tasks.add_task(calculate_file_hash, file_uuid, file_path)
        
        return UploadResponse(
            file_id=file_uuid,
            filename=file.filename,
            download_url=download_url,
            view_url=view_url,
            message="File uploaded successfully"
        )
        
    except Exception as e:
        # 에러 처리 시스템을 통한 에러 처리
        error_result = await error_handler.handle_upload_error(
            error=e,
            file_uuid=file_uuid or "unknown",
            request=request,
            context={
                "upload_start_time": start_time.isoformat(),
                "file_size": getattr(file, 'size', 0),
                "content_type": getattr(file, 'content_type', 'unknown'),
                "filename": getattr(file, 'filename', 'unknown')
            }
        )
        
        # 에러 메트릭 업데이트
        file_upload_error_counter.labels(error_type=error_result['error_type']).inc()
        
        # 에러 응답 반환
        return JSONResponse(
            status_code=error_result['status_code'],
            content=ErrorResponse(**error_result).dict()
        )

@app.post("/api/v1/files/upload", response_model=FileUploadResponse)
async def upload_file_v2(
    file: UploadFile,
    request: Request,
    background_tasks: BackgroundTasks,
    category_id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    is_public: bool = True,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """향상된 파일 업로드 API - Rate Limiting 및 표준화된 응답"""
    start_time = datetime.now()
    file_uuid = None
    
    # 서비스 초기화
    error_handler = ErrorHandlerService(db, str(UPLOAD_DIR))
    storage_service = FileStorageService(db, str(UPLOAD_DIR))
    metadata_service = MetadataService(db)
    rate_limiter = RateLimiterService(db, redis_client)
    
    # 클라이언트 IP 추출
    client_ip = rate_limiter.get_client_ip(request)
    
    try:
        # 1. Rate Limiting 확인
        is_hour_limited, hour_info = rate_limiter.is_rate_limited(client_ip, 'uploads_per_hour')
        is_day_limited, day_info = rate_limiter.is_rate_limited(client_ip, 'uploads_per_day')
        
        if is_hour_limited:
            raise HTTPException(
                status_code=429, 
                detail=f"시간당 업로드 제한 초과. {hour_info.get('reset_time', 0)}초 후 재시도 가능"
            )
        
        if is_day_limited:
            raise HTTPException(
                status_code=429, 
                detail=f"일일 업로드 제한 초과. {day_info.get('reset_time', 0)}초 후 재시도 가능"
            )
        
        # 2. 동시 업로드 제한 확인
        if not rate_limiter.check_concurrent_uploads(client_ip):
            raise HTTPException(
                status_code=429, 
                detail="동시 업로드 제한 초과. 다른 업로드가 완료될 때까지 대기하세요"
            )
        
        # 3. 업로드 세션 시작
        rate_limiter.start_upload_session(client_ip)
        
        # 4. 파일 검증
        if not file.filename:
            raise ValueError("파일명이 제공되지 않았습니다")
        
        # 5. 파일 크기 제한 확인
        if not rate_limiter.check_file_size_limit(getattr(file, 'size', 0), client_ip):
            raise HTTPException(
                status_code=413, 
                detail="파일 크기가 제한을 초과합니다"
            )
        
        # 6. 파일 저장
        storage_result = await storage_service.save_file(file, file.filename)
        
        if storage_result['is_duplicate']:
            # 중복 파일 응답
            return FileDuplicateResponse(
                file_uuid=storage_result['file_uuid'],
                message=storage_result['message'],
                existing_file_info=storage_result.get('existing_file')
            )
        
        file_uuid = storage_result['file_uuid']
        
        # 7. 메타데이터 저장
        metadata = {
            'category_id': category_id,
            'tags': tags,
            'is_public': is_public,
            'description': description
        }
        
        metadata_result = await metadata_service.save_file_metadata(
            file_uuid=file_uuid,
            original_filename=file.filename,
            stored_filename=storage_result['stored_filename'],
            file_extension=storage_result['file_extension'],
            mime_type=file.content_type,
            file_size=storage_result['file_size'],
            file_hash=storage_result['file_hash'],
            storage_path=storage_result['storage_path'],
            request=request,
            metadata=metadata
        )
        
        # 8. Rate Limiting 카운트 증가
        rate_limiter.increment_request_count(client_ip, 'uploads_per_hour')
        rate_limiter.increment_request_count(client_ip, 'uploads_per_day')
        
        # 9. 성공 메트릭 업데이트
        file_upload_counter.inc()
        file_upload_duration.observe((datetime.now() - start_time).total_seconds())
        
        # 10. 백그라운드 작업: 추가 처리
        background_tasks.add_task(calculate_file_hash, file_uuid, Path(storage_result['storage_path']))
        
        # 11. URL 생성
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        download_url = f"{base_url}/download/{file_uuid}"
        view_url = f"{base_url}/view/{file_uuid}"
        
        # 12. 표준화된 응답 반환
        return FileUploadResponse(
            file_uuid=file_uuid,
            original_filename=file.filename,
            stored_filename=storage_result['stored_filename'],
            file_size=storage_result['file_size'],
            mime_type=file.content_type,
            file_hash=storage_result['file_hash'],
            category_id=category_id,
            tags=tags or [],
            is_public=is_public,
            description=description,
            upload_time=metadata_result['upload_time'],
            upload_ip=metadata_result['upload_ip'],
            processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            download_url=download_url,
            view_url=view_url
        )
        
    except Exception as e:
        # 에러 처리 시스템을 통한 에러 처리
        error_result = await error_handler.handle_upload_error(
            error=e,
            file_uuid=file_uuid or "unknown",
            request=request,
            context={
                "upload_start_time": start_time.isoformat(),
                "file_size": getattr(file, 'size', 0),
                "content_type": getattr(file, 'content_type', 'unknown'),
                "filename": getattr(file, 'filename', 'unknown'),
                "category_id": category_id,
                "tags": tags,
                "is_public": is_public
            }
        )
        
        # 에러 메트릭 업데이트
        file_upload_error_counter.labels(error_type=error_result['error_type']).inc()
        
        # 에러 응답 반환
        return JSONResponse(
            status_code=error_result['status_code'],
            content=ErrorResponse(**error_result).dict()
        )
    
    finally:
        # 업로드 세션 종료
        rate_limiter.end_upload_session(client_ip)

@app.get("/files/{file_id}", response_model=FileInfoResponse)
async def get_file_info(file_id: str):
    """파일 정보 조회 API"""
    file_info_str = redis_client.get(f"file:{file_id}")
    if not file_info_str:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        import ast
        file_info = ast.literal_eval(file_info_str)
        
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        download_url = f"{base_url}/download/{file_id}"
        view_url = f"{base_url}/view/{file_id}"
        
        return FileInfo(
            file_id=file_info["file_id"],
            filename=file_info["filename"],
            size=file_info["size"],
            upload_time=datetime.fromisoformat(file_info["upload_time"]),
            download_url=download_url,
            view_url=view_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file info: {str(e)}")

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """파일 다운로드 API"""
    try:
        # Redis에서 파일 정보 조회
        file_info_str = redis_client.get(f"file:{file_id}")
        if not file_info_str:
            raise HTTPException(status_code=404, detail="File not found")
        
        import ast
        file_info = ast.literal_eval(file_info_str)
        saved_filename = file_info["saved_filename"]
        file_path = UPLOAD_DIR / saved_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # 다운로드 카운터 증가
        file_download_counter.inc()
        
        return FileResponse(
            path=file_path,
            filename=file_info["filename"],
            media_type=file_info["content_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/view/{file_id}")
async def view_file(file_id: str):
    """파일 미리보기 API"""
    try:
        # Redis에서 파일 정보 조회
        file_info_str = redis_client.get(f"file:{file_id}")
        if not file_info_str:
            raise HTTPException(status_code=404, detail="File not found")
        
        import ast
        file_info = ast.literal_eval(file_info_str)
        saved_filename = file_info["saved_filename"]
        file_path = UPLOAD_DIR / saved_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # 텍스트 파일인 경우 내용 반환
        content_type = file_info["content_type"]
        if content_type and content_type.startswith('text/'):
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return Response(content=content, media_type=content_type)
        
        # 이미지 파일인 경우 직접 반환
        elif content_type and content_type.startswith('image/'):
            return FileResponse(path=file_path, media_type=content_type)
        
        # 기타 파일은 다운로드로 처리
        else:
            return FileResponse(
                path=file_path,
                filename=file_info["filename"],
                media_type=content_type
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"View failed: {str(e)}")

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    try:
        # Redis 연결 확인
        redis_client.ping()
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}
        )

@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/api/v1/upload/errors", response_model=ErrorStatisticsResponse)
async def get_upload_errors(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """업로드 에러 통계 조회"""
    error_handler = ErrorHandlerService(db, str(UPLOAD_DIR))
    stats = await error_handler.get_error_statistics(days)
    return ErrorStatisticsResponse(**stats)


@app.delete("/api/v1/upload/errors/cleanup")
async def cleanup_error_logs(
    days: int = 90,
    db: Session = Depends(get_db)
):
    """오래된 에러 로그 정리"""
    error_handler = ErrorHandlerService(db, str(UPLOAD_DIR))
    cleaned_count = await error_handler.cleanup_old_error_logs(days)
    return {"cleaned_count": cleaned_count, "days": days}


@app.get("/api/v1/upload/statistics/{client_ip}", response_model=UploadStatisticsResponse)
async def get_upload_statistics(
    client_ip: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """IP별 업로드 통계 조회"""
    rate_limiter = RateLimiterService(db, redis_client)
    stats = rate_limiter.get_upload_statistics(client_ip, days)
    
    # 평균 파일 크기 계산
    if stats['total_uploads'] > 0:
        average_file_size = stats['total_size'] / stats['total_uploads']
    else:
        average_file_size = 0.0
    
    return UploadStatisticsResponse(
        client_ip=stats['client_ip'],
        period_days=stats['period_days'],
        total_uploads=stats['total_uploads'],
        total_size=stats['total_size'],
        average_file_size=average_file_size,
        daily_stats=stats['daily_stats']
    )


@app.get("/api/v1/metrics/detailed", response_model=MetricsResponse)
async def get_detailed_metrics(db: Session = Depends(get_db)):
    """상세 메트릭 조회"""
    try:
        # 기본 메트릭 수집
        from prometheus_client import REGISTRY
        
        # 업로드 통계
        upload_counter = REGISTRY.get_sample_value('file_uploads_total')
        download_counter = REGISTRY.get_sample_value('file_downloads_total')
        
        # 에러 통계
        error_counters = {}
        for sample in REGISTRY.get_sample_value('file_upload_errors_total'):
            error_counters[sample.labels['error_type']] = sample.value
        
        # 평균 업로드 시간
        upload_duration = REGISTRY.get_sample_value('file_upload_duration_seconds_sum')
        upload_count = REGISTRY.get_sample_value('file_upload_duration_seconds_count')
        avg_duration = upload_duration / upload_count if upload_count > 0 else 0
        
        # 활성 업로드 수 (Redis에서 조회)
        active_uploads = len(redis_client.keys("concurrent_uploads:*"))
        
        # 저장소 사용량
        import shutil
        total, used, free = shutil.disk_usage(str(UPLOAD_DIR))
        storage_usage = {
            'total_bytes': total,
            'used_bytes': used,
            'free_bytes': free,
            'usage_percent': (used / total) * 100 if total > 0 else 0
        }
        
        return MetricsResponse(
            file_uploads_total=int(upload_counter or 0),
            file_downloads_total=int(download_counter or 0),
            file_upload_errors_total=error_counters,
            average_upload_duration=float(avg_duration or 0),
            active_uploads=active_uploads,
            storage_usage=storage_usage
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메트릭 수집 실패: {str(e)}")


@app.get("/health/detailed", response_model=HealthCheckResponse)
async def detailed_health_check():
    """상세 헬스체크"""
    services = {}
    
    # Redis 연결 확인
    try:
        redis_client.ping()
        services['redis'] = 'healthy'
    except Exception as e:
        services['redis'] = f'unhealthy: {str(e)}'
    
    # 파일 시스템 확인
    try:
        if UPLOAD_DIR.exists() and os.access(UPLOAD_DIR, os.W_OK):
            services['file_system'] = 'healthy'
        else:
            services['file_system'] = 'unhealthy: 권한 없음'
    except Exception as e:
        services['file_system'] = f'unhealthy: {str(e)}'
    
    # 전체 상태 결정
    overall_status = 'healthy' if all(
        status == 'healthy' for status in services.values()
    ) else 'unhealthy'
    
    return HealthCheckResponse(
        status=overall_status,
        services=services,
        version="1.0.0"
    )