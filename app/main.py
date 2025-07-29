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
from app.middleware.security_headers import SecurityHeadersMiddleware, CORSValidationMiddleware
from pydantic import BaseModel
import redis
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.error_handler_service import ErrorHandlerService
from app.services.file_storage_service import FileStorageService
from app.services.metadata_service import MetadataService
from app.services.rate_limiter_service import RateLimiterService
from app.models.orm_models import FileInfo
from app.models.api_models import (
    FileUploadResponse, FileDuplicateResponse, FileInfoResponse,
    UploadStatisticsResponse, ErrorResponse,
    MetricsResponse, ErrorStatisticsResponse
)
from app.routers.ip_auth_router import router as ip_auth_router
from app.routers.health import router as health_router
from app.services.scheduler_service import scheduler_service
from app.services.file_validation_service import file_validation_service
from app.services.rbac_service import rbac_service
from app.middleware.audit_middleware import AuditMiddleware

# Redis 연결
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', 'filewallball2024'),
    decode_responses=True
)

app = FastAPI(title="File Management API", version="1.0.0")

# 보안 헤더 및 CORS 정책 설정
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CORSValidationMiddleware)

# 라우터 등록
app.include_router(ip_auth_router)
app.include_router(health_router)

# 전역 예외 처리 미들웨어
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리 미들웨어 - 에러 메트릭 업데이트"""
    # 에러 타입 분류
    if isinstance(exc, HTTPException):
        error_type = f"http_{exc.status_code}"
    elif isinstance(exc, ValueError):
        error_type = "validation_error"
    elif isinstance(exc, ConnectionError):
        error_type = "connection_error"
    else:
        error_type = "internal_error"
    
    # 에러 메트릭 업데이트
    error_rate_counter.labels(error_type=error_type).inc()
    
    # 기본 에러 응답
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

# Prometheus Instrumentator 설정
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# 커스텀 메트릭 설정
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

# 추가 커스텀 메트릭
active_connections_gauge = Counter(
    'active_connections_total', 'Total number of active connections'
)
error_rate_counter = Counter(
    'error_rate_total', 'Total number of errors', ['error_type']
)
file_processing_duration = Histogram(
    'file_processing_duration_seconds', 'File processing duration'
)
cache_hit_counter = Counter(
    'cache_hits_total', 'Total number of cache hits'
)
cache_miss_counter = Counter(
    'cache_misses_total', 'Total number of cache misses'
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
        
        # 4. 파일 유효성 검사 (Task 12.4: 강화된 검증)
        validation_result = await file_validation_service.validate_upload_file(file)
        
        if not validation_result['is_valid']:
            # 검증 실패 시 에러 메트릭 업데이트
            file_upload_error_counter.labels(error_type='validation_error').inc()
            error_rate_counter.labels(error_type='validation_error').inc()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "파일 검증에 실패했습니다",
                    "errors": validation_result['errors'],
                    "file_info": {
                        "filename": file.filename,
                        "detected_mime_type": validation_result.get('mime_type'),
                        "file_size": validation_result.get('file_size')
                    }
                }
            )
        
        # 5. 파일 크기 제한 확인 (Rate Limiter)
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


@app.get("/api/v1/security/headers-test")
async def test_security_headers():
    """
    보안 헤더 테스트 API
    Task 12.3: 보안 헤더 검증
    
    Returns:
        보안 헤더가 적용된 응답
    """
    return {
        "message": "Security headers test endpoint",
        "status": "success",
        "headers_applied": [
            "X-Content-Type-Options: nosniff",
            "X-Frame-Options: DENY", 
            "X-XSS-Protection: 1; mode=block",
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "Referrer-Policy: strict-origin-when-cross-origin",
            "Permissions-Policy",
            "Cross-Origin-Embedder-Policy: require-corp",
            "Cross-Origin-Opener-Policy: same-origin",
            "Cross-Origin-Resource-Policy: same-origin"
        ],
        "cors_policy": {
            "description": "Strict CORS policy applied",
            "allowed_origins": [
                "http://localhost:3000",
                "http://localhost:8080", 
                "https://filewallball.com",
                "https://www.filewallball.com"
            ],
            "environment_origins": "Configurable via ALLOWED_ORIGINS env var"
        }
    }


@app.get("/api/v1/validation/policy")
async def get_validation_policy():
    """
    파일 업로드 검증 정책 조회 API
    Task 12.4: 파일 유효성 검사 정책 정보
    
    Returns:
        파일 업로드 검증 정책 정보
    """
    return {
        "message": "File upload validation policy",
        "status": "success",
        "validation_policy": {
            "file_size_limits": {
                "min_size_bytes": file_validation_service.min_file_size,
                "max_size_bytes": file_validation_service.max_file_size,
                "min_size_mb": file_validation_service.min_file_size // (1024 * 1024),
                "max_size_mb": file_validation_service.max_file_size // (1024 * 1024)
            },
            "allowed_extensions": file_validation_service.get_allowed_extensions(),
            "blocked_extensions": file_validation_service.get_blocked_extensions(),
            "allowed_mime_types": list(file_validation_service.allowed_mime_types.keys()),
            "blocked_mime_types": list(file_validation_service.blocked_mime_types),
            "filename_restrictions": {
                "max_length": 255,
                "forbidden_patterns": file_validation_service.forbidden_filename_patterns,
                "forbidden_characters": ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
            },
            "security_features": [
                "Magic Number 기반 MIME 타입 검증",
                "악성 코드 패턴 검사",
                "실행 파일 차단",
                "스크립트 파일 차단",
                "파일명 보안 검증"
            ]
        }
    }


@app.get("/api/v1/audit/logs")
async def get_audit_logs(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=200, description="페이지당 로그 수"),
    user_id: Optional[int] = Query(None, description="사용자 ID로 필터링"),
    action: Optional[str] = Query(None, description="액션으로 필터링 (create, read, update, delete)"),
    resource_type: Optional[str] = Query(None, description="리소스 타입으로 필터링 (file, user, system)"),
    status: Optional[str] = Query(None, description="상태로 필터링 (success, failed, denied)"),
    date_from: Optional[datetime] = Query(None, description="시작 날짜"),
    date_to: Optional[datetime] = Query(None, description="종료 날짜"),
    ip_address: Optional[str] = Query(None, description="IP 주소로 필터링"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    감사 로그 조회 API
    Task 12.5: RBAC 기반 감사 로그 조회
    
    Returns:
        감사 로그 목록 및 페이지네이션 정보
    """
    try:
        # 필터 구성
        filters = {}
        if user_id:
            filters['user_id'] = user_id
        if action:
            filters['action'] = action
        if resource_type:
            filters['resource_type'] = resource_type
        if status:
            filters['status'] = status
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if ip_address:
            filters['ip_address'] = ip_address
        
        # RBAC 서비스를 통한 로그 조회
        logs, total = rbac_service.get_audit_logs(
            db=db,
            user=current_user,
            filters=filters,
            page=page,
            size=size
        )
        
        # 로그 데이터 변환
        log_data = []
        for log in logs:
            log_data.append({
                "id": log.id,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "resource_name": log.resource_name,
                "details": json.loads(log.details) if log.details else None,
                "status": log.status,
                "error_message": log.error_message,
                "request_path": log.request_path,
                "request_method": log.request_method,
                "response_code": log.response_code,
                "processing_time_ms": log.processing_time_ms,
                "created_at": log.created_at.isoformat()
            })
        
        return {
            "message": "Audit logs retrieved successfully",
            "status": "success",
            "data": {
                "logs": log_data,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "pages": (total + size - 1) // size
                },
                "filters": filters
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="감사 로그 조회 중 오류가 발생했습니다"
        )


@app.get("/api/v1/rbac/permissions")
async def get_user_permissions(
    current_user = Depends(get_current_user)
):
    """
    사용자 권한 조회 API
    Task 12.5: RBAC 권한 정보 조회
    
    Returns:
        현재 사용자의 권한 정보
    """
    try:
        permissions = rbac_service.get_user_permissions(current_user)
        
        return {
            "message": "User permissions retrieved successfully",
            "status": "success",
            "data": {
                "user_id": current_user.id,
                "username": current_user.username,
                "role": current_user.role,
                "permissions": permissions,
                "file_access_rules": rbac_service.file_access_rules
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="권한 정보 조회 중 오류가 발생했습니다"
        )


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    try:
        # 스케줄러 시작
        await scheduler_service.start_scheduler()
        print("✅ File cleanup scheduler started successfully")
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트"""
    try:
        # 스케줄러 중지
        await scheduler_service.stop_scheduler()
        print("✅ File cleanup scheduler stopped successfully")
    except Exception as e:
        print(f"❌ Failed to stop scheduler: {e}")


