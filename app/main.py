import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiofiles
import redis
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse, Response
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.async_redis_client import get_async_redis_client
from app.database import get_db
from app.dependencies.auth import (
    get_current_user,
    require_admin,
    require_audit_read,
    require_authenticated_user,
    require_file_create,
    require_file_delete,
    require_file_read,
    require_file_update,
    require_system_read,
)
from app.dependencies.auth_schema import (
    get_admin_error_responses,
    get_common_error_responses,
    get_file_error_responses,
)
from app.metrics import (
    error_rate_counter,
    file_download_counter,
    file_upload_counter,
    file_upload_duration,
    file_upload_error_counter,
    get_metrics,
    get_metrics_content_type,
    update_redis_metrics,
)
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.security_headers import (
    CORSValidationMiddleware,
    SecurityHeadersMiddleware,
)
from app.models.api_models import (
    ErrorStatisticsResponse,
    FileDuplicateResponse,
    UploadStatisticsResponse,
)
from app.models.orm_models import FileInfo
from app.models.swagger_models import (
    DetailedHealthCheckResponse,
    ErrorResponse,
    FileInfoResponse,
    FileUploadResponse,
    HealthCheckResponse,
    MetricsResponse,
    UploadResponse,
)
from app.routers.health import router as health_router
from app.routers.ip_auth_router import router as ip_auth_router
from app.services.advanced_rate_limiter import rate_limit_middleware
from app.services.audit_log_service import AuditAction, AuditResult, audit_log_service
from app.services.background_task_service import (
    TaskStatus,
    TaskType,
    background_task_service,
)
from app.services.error_handler_service import ErrorHandlerService
from app.services.file_deletion_service import DeletionType, file_deletion_service
from app.services.file_list_service import SortBy, SortOrder, file_list_service
from app.services.file_storage_service import FileStorageService
from app.services.file_validation_service import file_validation_service
from app.services.health_check_service import health_check_service
from app.services.metadata_service import MetadataService
from app.services.rate_limiter_service import RateLimiterService
from app.services.rbac_service import rbac_service
from app.services.scheduler_service import scheduler_service
from app.utils.swagger_customization import custom_openapi
from app.services.project_key_service import ProjectKeyService

# Redis 연결
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", "filewallball2024"),
    decode_responses=True,
)

# OpenAPI 태그 정의
openapi_tags = [
    {
        "name": "파일 업로드",
        "description": "파일 업로드 관련 엔드포인트. 다양한 형식의 파일을 안전하게 업로드할 수 있습니다.",
    },
    {
        "name": "파일 관리",
        "description": "파일 조회, 다운로드, 미리보기, 삭제 등 파일 관리 기능을 제공합니다.",
    },
    {
        "name": "파일 검색",
        "description": "파일 목록 조회, 검색, 필터링 기능을 제공합니다.",
    },
    {
        "name": "썸네일",
        "description": "이미지 파일의 썸네일 생성 및 조회 기능을 제공합니다.",
    },
    {
        "name": "인증 및 권한",
        "description": "IP 기반 인증, RBAC 권한 관리, 사용자 권한 조회 기능을 제공합니다.",
    },
    {
        "name": "IP 관리",
        "description": "IP 화이트리스트/블랙리스트 관리 및 IP 상태 확인 기능을 제공합니다.",
    },
    {
        "name": "레이트 리미팅",
        "description": "요청 제한 관리, IP 차단/해제 기능을 제공합니다.",
    },
    {
        "name": "감사 로그",
        "description": "시스템 활동에 대한 감사 로그 조회 및 통계 기능을 제공합니다.",
    },
    {
        "name": "백그라운드 작업",
        "description": "백그라운드 작업 제출, 상태 조회, 취소 기능을 제공합니다.",
    },
    {
        "name": "모니터링",
        "description": "시스템 메트릭, 헬스체크, 성능 모니터링 기능을 제공합니다.",
    },
    {
        "name": "관리자",
        "description": "관리자 전용 기능으로 시스템 관리 및 정리 작업을 제공합니다.",
    },
]

app = FastAPI(
    title="FileWallBall API",
    description="""
    # FileWallBall - 안전한 파일 공유 플랫폼 API

    FileWallBall은 안전하고 효율적인 파일 업로드, 저장, 공유를 위한 RESTful API 서비스입니다.

    ## 주요 기능

    * **파일 업로드**: 최대 100MB 파일 업로드 지원, 다양한 파일 형식 검증
    * **파일 관리**: 파일 조회, 다운로드, 미리보기, 삭제 기능
    * **보안**: IP 기반 인증, RBAC 권한 관리, 레이트 리미팅
    * **캐싱**: Redis 기반 고성능 캐싱 시스템
    * **모니터링**: Prometheus 메트릭, 감사 로그, 성능 모니터링
    * **백그라운드 작업**: 비동기 파일 처리, 썸네일 생성

    ## 인증

    대부분의 엔드포인트는 JWT Bearer 토큰 인증이 필요합니다.
    IP 기반 인증을 사용하는 엔드포인트는 별도로 표시됩니다.

    ## 사용 예제

    ```bash
    # 파일 업로드
    curl -X POST "http://localhost:8000/upload" \\
         -H "Authorization: Bearer YOUR_TOKEN" \\
         -F "file=@document.pdf"

    # 파일 다운로드
    curl -X GET "http://localhost:8000/download/{file_id}" \\
         -H "Authorization: Bearer YOUR_TOKEN"

    # 파일 목록 조회
    curl -X GET "http://localhost:8000/api/v1/files?page=1&size=20" \\
         -H "Authorization: Bearer YOUR_TOKEN"
    ```

    ## 에러 코드

    * `400` - 잘못된 요청
    * `401` - 인증 실패
    * `403` - 권한 없음
    * `404` - 리소스 없음
    * `413` - 파일 크기 초과
    * `429` - 요청 한도 초과
    * `500` - 서버 내부 오류
    """,
    version="1.0.0",
    contact={
        "name": "FileWallBall Team",
        "email": "support@filewallball.com",
        "url": "https://github.com/filewallball/api",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=openapi_tags,
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "개발 환경",
        },
        {
            "url": "https://api.filewallball.com",
            "description": "프로덕션 환경",
        },
    ],
)

# 커스터마이징된 OpenAPI 스키마 적용
app.openapi = lambda: custom_openapi(app)

# 메트릭 수집 미들웨어 추가
app.add_middleware(MetricsMiddleware)

# 보안 헤더 및 CORS 정책 설정
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CORSValidationMiddleware)


# 레이트 리미팅 미들웨어 추가
@app.middleware("http")
async def rate_limit_middleware_wrapper(request: Request, call_next):
    """레이트 리미팅 미들웨어 래퍼"""
    return await rate_limit_middleware()(request, call_next)


# 라우터 등록
app.include_router(ip_auth_router)
app.include_router(health_router)

# Redis 메트릭 업데이트 태스크
redis_metrics_task: Optional[asyncio.Task] = None


async def update_redis_metrics_periodically():
    """주기적으로 Redis 메트릭 업데이트"""
    while True:
        try:
            redis_client_async = await get_async_redis_client()
            await update_redis_metrics(redis_client_async)
            await asyncio.sleep(30)  # 30초마다 업데이트
        except Exception as e:
            print(f"Redis 메트릭 업데이트 실패: {e}")
            await asyncio.sleep(60)  # 실패 시 1분 대기


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
    error_rate_counter.labels(error_type=error_type, endpoint="unknown").inc()

    # 기본 에러 응답
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_type": error_type},
    )


# Prometheus Instrumentator 설정
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# 커스텀 메트릭 설정
# 메트릭은 app.metrics 모듈에서 정의됨

# 추가 커스텀 메트릭
from app.metrics import (
    active_connections_gauge,
    cache_hit_counter,
    cache_miss_counter,
    file_processing_duration,
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
        async with aiofiles.open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()
        # Redis에 해시 저장
        redis_client.setex(f"hash:{file_id}", 86400, file_hash)
    except Exception as e:
        print(f"해시 계산 실패: {e}")


@app.post(
    "/upload",
    response_model=UploadResponse,
    summary="파일 업로드 (프로젝트 키 검증)",
    description="""
    프로젝트 키를 검증하여 파일을 업로드하고 시스템에 저장합니다.

    ## 기능
    - 프로젝트 키 유효성 검증
    - 최대 100MB 파일 업로드 지원
    - 파일 형식 검증 및 바이러스 스캔
    - 자동 썸네일 생성 (이미지 파일)
    - 파일 해시 계산 (백그라운드)
    - 업로드 통계 기록
    - 프로젝트별 파일 분류

    ## 지원 파일 형식
    - 이미지: jpg, jpeg, png, gif, webp, bmp, tiff
    - 문서: pdf, doc, docx, xls, xlsx, ppt, pptx, txt
    - 비디오: mp4, avi, mov, wmv, flv, webm
    - 오디오: mp3, wav, flac, aac, ogg
    - 압축: zip, rar, 7z, tar, gz

    ## 파라미터
    - `file`: 업로드할 파일 (필수)
    - `project_key`: 프로젝트 키 (필수)

    ## 응답
    - `file_id`: 업로드된 파일의 고유 식별자
    - `filename`: 원본 파일명
    - `download_url`: 파일 다운로드 URL
    - `view_url`: 파일 미리보기 URL (지원되는 경우)
    - `message`: 성공 메시지
    - `project_name`: 프로젝트명
    """,
    tags=["파일 업로드"],
    responses=get_file_error_responses(),
)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="업로드할 파일", example="document.pdf"),
    project_key: str = Form(..., description="프로젝트 키"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """파일 업로드 API - 프로젝트 키 검증 및 강화된 검증"""
    start_time = datetime.now()
    file_uuid = None
    error_handler = ErrorHandlerService(db, str(UPLOAD_DIR))

    # 메트릭 업데이트
    file_upload_counter.labels(
        status="started", file_type="unknown", user_id="anonymous"
    ).inc()

    try:
        # 1. 프로젝트 키 검증
        project_key_service = ProjectKeyService(db)
        project_info = project_key_service.validate_project_key(project_key)
        
        if not project_info:
            raise HTTPException(
                status_code=401,
                detail="유효하지 않은 프로젝트 키입니다"
            )
        
        # 2. 파일 검증
        validation_result = await file_validation_service.validate_upload_file(file)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"파일 검증 실패: {validation_result['error_message']}",
            )

        # 2. 파일 ID 생성
        file_uuid = str(uuid.uuid4())

        # 3. 파일 확장자 추출
        file_extension = Path(file.filename).suffix if file.filename else ""

        # 4. 저장할 파일명 생성
        saved_filename = f"{file_uuid}{file_extension}"

        # 5. 계층적 디렉토리 구조 생성 (YYYY/MM/DD)
        current_date = datetime.now()
        date_path = current_date.strftime("%Y/%m/%d")
        upload_path = UPLOAD_DIR / date_path
        upload_path.mkdir(parents=True, exist_ok=True)

        file_path = upload_path / saved_filename

        # 6. 파일 저장
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # 7. 파일 정보 구성
        file_info = {
            "file_id": file_uuid,
            "filename": file.filename,
            "size": len(content),
            "upload_time": datetime.now().isoformat(),
            "content_type": file.content_type,
            "saved_filename": saved_filename,
            "storage_path": str(file_path),
            "mime_type": validation_result.get("detected_mime_type", file.content_type),
            "file_extension": file_extension,
            "uploader_ip": request.client.host if request else "unknown",
        }

        # 8. 데이터베이스에 파일 정보 저장
        from app.models.orm_models import FileInfo
        
        db_file_info = FileInfo(
            file_uuid=file_uuid,
            original_filename=file.filename,
            stored_filename=saved_filename,
            file_extension=file_extension,
            mime_type=validation_result.get("detected_mime_type", file.content_type),
            file_size=len(content),
            storage_path=str(file_path),
            project_key_id=project_info.id,  # 프로젝트 키 ID 연결
            is_public=True,
            is_deleted=False
        )
        
        db.add(db_file_info)
        db.commit()
        db.refresh(db_file_info)

        # 9. Redis에 파일 정보 저장 (24시간 만료)
        redis_client.setex(f"file:{file_uuid}", 86400, str(file_info))

        # 10. URL 생성
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        download_url = f"{base_url}/download/{file_uuid}"
        view_url = f"{base_url}/view/{file_uuid}"

        # 10. 성공 메트릭 업데이트
        upload_duration = (datetime.now() - start_time).total_seconds()
        file_upload_counter.labels(
            status="success",
            file_type=validation_result.get("detected_mime_type", "unknown"),
            user_id="anonymous",
        ).inc()
        file_upload_duration.labels(
            file_type=validation_result.get("detected_mime_type", "unknown"),
            status="success",
        ).observe(upload_duration)

        # 11. 백그라운드 작업: 파일 해시 계산
        background_tasks.add_task(calculate_file_hash, file_uuid, file_path)

        # 12. 백그라운드 작업: 이미지 파일인 경우 썸네일 생성
        from app.services.file_preview_service import file_preview_service

        if file_preview_service.is_image_file(file.filename):

            async def generate_thumbnail_background():
                try:
                    thumbnail_path = await file_preview_service.generate_thumbnail(
                        file_path, "medium", "webp"
                    )
                    if thumbnail_path:
                        await file_preview_service.cache_thumbnail(
                            file_uuid, thumbnail_path, "medium"
                        )
                        logger.info(f"업로드 후 썸네일 생성 완료: {file_uuid}")
                except Exception as e:
                    logger.error(f"업로드 후 썸네일 생성 실패: {e}")

            background_tasks.add_task(generate_thumbnail_background)

        # 13. 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.UPLOAD,
                resource_type="file",
                resource_id=file_uuid,
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.SUCCESS,
                details={
                    "filename": file.filename,
                    "file_size": file_size,
                    "content_type": content_type,
                    "saved_filename": saved_filename,
                },
                duration_ms=upload_duration,
            )
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

        return UploadResponse(
            file_id=file_uuid,
            filename=file.filename,
            download_url=download_url,
            view_url=view_url,
            message=f"File uploaded successfully to project: {project_info.project_name}",
        )

    except HTTPException:
        # HTTP 예외는 그대로 전파
        raise
    except Exception as e:
        # 에러 처리 시스템을 통한 에러 처리
        error_result = await error_handler.handle_upload_error(
            error=e,
            file_uuid=file_uuid or "unknown",
            request=request,
            context={
                "upload_start_time": start_time.isoformat(),
                "file_size": getattr(file, "size", 0),
                "content_type": getattr(file, "content_type", "unknown"),
                "filename": getattr(file, "filename", "unknown"),
            },
        )

        # 에러 메트릭 업데이트
        file_upload_error_counter.labels(
            error_type=error_result["error_type"], file_type="unknown"
        ).inc()

        file_upload_counter.labels(
            status="error", file_type="unknown", user_id="anonymous"
        ).inc()

        # 에러 응답 반환
        return JSONResponse(
            status_code=error_result["status_code"],
            content=ErrorResponse(**error_result).dict(),
        )


@app.post(
    "/api/v1/files/upload",
    response_model=FileUploadResponse,
    summary="고급 파일 업로드 (v2)",
    description="""
    고급 기능을 포함한 파일 업로드 엔드포인트입니다.

    ## 추가 기능
    - 카테고리 분류
    - 태그 시스템
    - 공개/비공개 설정
    - 파일 설명 추가
    - 메타데이터 자동 추출

    ## 파라미터
    - `file`: 업로드할 파일 (필수)
    - `category_id`: 파일 카테고리 ID (선택)
    - `tags`: 파일 태그 목록 (선택)
    - `is_public`: 공개 여부 (기본값: true)
    - `description`: 파일 설명 (선택)

    ## 응답
    - `file_uuid`: 파일 고유 식별자
    - `filename`: 원본 파일명
    - `file_size`: 파일 크기 (바이트)
    - `content_type`: MIME 타입
    - `upload_time`: 업로드 시간
    - `category_id`: 카테고리 ID
    - `tags`: 태그 목록
    - `is_public`: 공개 여부
    - `description`: 파일 설명
    - `download_url`: 다운로드 URL
    - `preview_url`: 미리보기 URL
    """,
    tags=["파일 업로드"],
    responses=get_file_error_responses(),
)
async def upload_file_v2(
    file: UploadFile = File(..., description="업로드할 파일"),
    request: Request = None,
    background_tasks: BackgroundTasks = None,
    category_id: Optional[int] = Query(None, description="파일 카테고리 ID"),
    tags: Optional[List[str]] = Query(None, description="파일 태그 목록"),
    is_public: bool = Query(True, description="공개 여부"),
    description: Optional[str] = Query(None, description="파일 설명"),
    db: Session = Depends(get_db),
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
        is_hour_limited, hour_info = rate_limiter.is_rate_limited(
            client_ip, "uploads_per_hour"
        )
        is_day_limited, day_info = rate_limiter.is_rate_limited(
            client_ip, "uploads_per_day"
        )

        if is_hour_limited:
            raise HTTPException(
                status_code=429,
                detail=f"시간당 업로드 제한 초과. {hour_info.get('reset_time', 0)}초 후 재시도 가능",
            )

        if is_day_limited:
            raise HTTPException(
                status_code=429,
                detail=f"일일 업로드 제한 초과. {day_info.get('reset_time', 0)}초 후 재시도 가능",
            )

        # 2. 동시 업로드 제한 확인
        if not rate_limiter.check_concurrent_uploads(client_ip):
            raise HTTPException(
                status_code=429,
                detail="동시 업로드 제한 초과. 다른 업로드가 완료될 때까지 대기하세요",
            )

        # 3. 업로드 세션 시작
        rate_limiter.start_upload_session(client_ip)

        # 4. 파일 유효성 검사 (Task 12.4: 강화된 검증)
        validation_result = await file_validation_service.validate_upload_file(file)

        if not validation_result["is_valid"]:
            # 검증 실패 시 에러 메트릭 업데이트
            file_upload_error_counter.labels(
                error_type="validation_error", file_type="unknown"
            ).inc()
            error_rate_counter.labels(
                error_type="validation_error", endpoint="upload"
            ).inc()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "파일 검증에 실패했습니다",
                    "errors": validation_result["errors"],
                    "file_info": {
                        "filename": file.filename,
                        "detected_mime_type": validation_result.get("mime_type"),
                        "file_size": validation_result.get("file_size"),
                    },
                },
            )

        # 5. 파일 크기 제한 확인 (Rate Limiter)
        if not rate_limiter.check_file_size_limit(getattr(file, "size", 0), client_ip):
            raise HTTPException(status_code=413, detail="파일 크기가 제한을 초과합니다")

        # 6. 파일 저장
        storage_result = await storage_service.save_file(file, file.filename)

        if storage_result["is_duplicate"]:
            # 중복 파일 응답
            return FileDuplicateResponse(
                file_uuid=storage_result["file_uuid"],
                message=storage_result["message"],
                existing_file_info=storage_result.get("existing_file"),
            )

        file_uuid = storage_result["file_uuid"]

        # 7. 메타데이터 저장
        metadata = {
            "category_id": category_id,
            "tags": tags,
            "is_public": is_public,
            "description": description,
        }

        metadata_result = await metadata_service.save_file_metadata(
            file_uuid=file_uuid,
            original_filename=file.filename,
            stored_filename=storage_result["stored_filename"],
            file_extension=storage_result["file_extension"],
            mime_type=file.content_type,
            file_size=storage_result["file_size"],
            file_hash=storage_result["file_hash"],
            storage_path=storage_result["storage_path"],
            request=request,
            metadata=metadata,
        )

        # 8. Rate Limiting 카운트 증가
        rate_limiter.increment_request_count(client_ip, "uploads_per_hour")
        rate_limiter.increment_request_count(client_ip, "uploads_per_day")

        # 9. 성공 메트릭 업데이트
        file_upload_counter.inc()
        file_upload_duration.observe((datetime.now() - start_time).total_seconds())

        # 10. 백그라운드 작업: 추가 처리
        background_tasks.add_task(
            calculate_file_hash, file_uuid, Path(storage_result["storage_path"])
        )

        # 11. URL 생성
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        download_url = f"{base_url}/download/{file_uuid}"
        view_url = f"{base_url}/view/{file_uuid}"

        # 12. 표준화된 응답 반환
        return FileUploadResponse(
            file_uuid=file_uuid,
            original_filename=file.filename,
            stored_filename=storage_result["stored_filename"],
            file_size=storage_result["file_size"],
            mime_type=file.content_type,
            file_hash=storage_result["file_hash"],
            category_id=category_id,
            tags=tags or [],
            is_public=is_public,
            description=description,
            upload_time=metadata_result["upload_time"],
            upload_ip=metadata_result["upload_ip"],
            processing_time_ms=int(
                (datetime.now() - start_time).total_seconds() * 1000
            ),
            download_url=download_url,
            view_url=view_url,
        )

    except Exception as e:
        # 에러 처리 시스템을 통한 에러 처리
        error_result = await error_handler.handle_upload_error(
            error=e,
            file_uuid=file_uuid or "unknown",
            request=request,
            context={
                "upload_start_time": start_time.isoformat(),
                "file_size": getattr(file, "size", 0),
                "content_type": getattr(file, "content_type", "unknown"),
                "filename": getattr(file, "filename", "unknown"),
                "category_id": category_id,
                "tags": tags,
                "is_public": is_public,
            },
        )

        # 에러 메트릭 업데이트
        file_upload_error_counter.labels(
            error_type=error_result["error_type"], file_type="unknown"
        ).inc()

        # 에러 응답 반환
        return JSONResponse(
            status_code=error_result["status_code"],
            content=ErrorResponse(**error_result).dict(),
        )

    finally:
        # 업로드 세션 종료
        rate_limiter.end_upload_session(client_ip)


@app.get(
    "/files/{file_id}",
    response_model=FileInfoResponse,
    summary="파일 정보 조회",
    description="""
    특정 파일의 상세 정보를 조회합니다.

    ## 기능
    - 파일 메타데이터 조회
    - 접근 권한 확인
    - 다운로드 통계 기록
    - 캐시된 정보 반환 (성능 최적화)

    ## 파라미터
    - `file_id`: 조회할 파일의 고유 식별자 (UUID)

    ## 응답
    - `file_uuid`: 파일 고유 식별자
    - `filename`: 원본 파일명
    - `file_size`: 파일 크기 (바이트)
    - `content_type`: MIME 타입
    - `upload_time`: 업로드 시간
    - `last_accessed`: 마지막 접근 시간
    - `download_count`: 다운로드 횟수
    - `is_public`: 공개 여부
    - `tags`: 태그 목록
    - `description`: 파일 설명
    - `download_url`: 다운로드 URL
    - `preview_url`: 미리보기 URL
    """,
    tags=["파일 관리"],
    responses=get_common_error_responses(),
)
async def get_file_info(
    file_id: str = Path(
        description="조회할 파일의 고유 식별자",
        example="550e8400-e29b-41d4-a716-446655440000",
    ),
    request: Request = None,
    current_user=Depends(require_file_read),
):
    """파일 정보 조회 API - 캐시 우선 조회"""
    start_time = datetime.now()

    try:
        # 1. Redis 캐시에서 파일 정보 조회
        file_info_str = redis_client.get(f"file:{file_id}")

        if not file_info_str:
            # 2. 캐시에 없으면 DB에서 조회 (향후 구현)
            raise HTTPException(status_code=404, detail="File not found")

        # 3. 파일 정보 파싱
        import ast

        file_info = ast.literal_eval(file_info_str)

        # 4. URL 생성
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        download_url = f"{base_url}/download/{file_id}"
        view_url = f"{base_url}/view/{file_id}"

        # 5. 응답 구성
        response = FileInfo(
            file_id=file_info["file_id"],
            filename=file_info["filename"],
            size=file_info["size"],
            upload_time=datetime.fromisoformat(file_info["upload_time"]),
            download_url=download_url,
            view_url=view_url,
        )

        # 6. 성공 메트릭 업데이트
        processing_time = (datetime.now() - start_time).total_seconds()
        api_request_duration.labels(
            method="GET", endpoint="/files/{file_id}", status_code=200
        ).observe(processing_time)

        api_request_counter.labels(
            method="GET", endpoint="/files/{file_id}", status_code=200
        ).inc()

        # 7. 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="file",
                resource_id=file_id,
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.SUCCESS,
                details={"filename": file_info["filename"]},
                duration_ms=processing_time * 1000,
            )
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

        return response

    except HTTPException:
        # HTTP 예외는 그대로 전파
        raise
    except Exception as e:
        # 에러 메트릭 업데이트
        api_request_counter.labels(
            method="GET", endpoint="/files/{file_id}", status_code=500
        ).inc()

        raise HTTPException(
            status_code=500, detail=f"Error retrieving file info: {str(e)}"
        )


@app.get(
    "/download/{file_id}",
    summary="파일 다운로드",
    description="""
    파일을 다운로드합니다.

    ## 기능
    - 파일 스트리밍 다운로드
    - Range 요청 지원 (부분 다운로드)
    - 다운로드 통계 기록
    - 접근 권한 확인
    - 캐시 헤더 설정

    ## 파라미터
    - `file_id`: 다운로드할 파일의 고유 식별자 (UUID)

    ## 헤더
    - `Range`: 부분 다운로드를 위한 범위 지정 (선택)
    - `Authorization`: Bearer 토큰 (필수)

    ## 응답
    - 파일 바이너리 데이터
    - 적절한 Content-Type 헤더
    - Content-Length 헤더
    - Accept-Ranges 헤더 (Range 요청 지원)
    - Cache-Control 헤더

    ## 사용 예제
    ```bash
    # 전체 파일 다운로드
    curl -X GET "http://localhost:8000/download/{file_id}" \\
         -H "Authorization: Bearer YOUR_TOKEN" \\
         -o "downloaded_file.pdf"

    # 부분 다운로드 (첫 1MB)
    curl -X GET "http://localhost:8000/download/{file_id}" \\
         -H "Authorization: Bearer YOUR_TOKEN" \\
         -H "Range: bytes=0-1048575" \\
         -o "file_part.pdf"
    ```
    """,
    tags=["파일 관리"],
    responses=get_file_error_responses(),
)
async def download_file(
    file_id: str = Path(
        description="다운로드할 파일의 고유 식별자",
        example="550e8400-e29b-41d4-a716-446655440000",
    ),
    request: Request = None,
    background_tasks: BackgroundTasks = None,
    current_user=Depends(require_file_read),
):
    """파일 다운로드 API - Range 헤더 지원 및 스트리밍"""
    start_time = datetime.now()

    try:
        # 1. Redis에서 파일 정보 조회
        file_info_str = redis_client.get(f"file:{file_id}")
        if not file_info_str:
            raise HTTPException(status_code=404, detail="File not found")

        import ast

        file_info = ast.literal_eval(file_info_str)

        # 2. 파일 경로 구성 (계층적 구조 고려)
        saved_filename = file_info["saved_filename"]
        upload_time = datetime.fromisoformat(file_info["upload_time"])
        date_path = upload_time.strftime("%Y/%m/%d")
        file_path = UPLOAD_DIR / date_path / saved_filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # 3. Range 헤더 처리
        range_header = request.headers.get("range")
        file_size = file_info["size"]

        if range_header:
            # Range 요청 처리
            try:
                range_start, range_end = parse_range_header(range_header, file_size)
                return await stream_file_range(
                    file_path,
                    file_info["filename"],
                    file_info["content_type"],
                    range_start,
                    range_end,
                    file_size,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid range: {str(e)}")

        # 4. 전체 파일 다운로드
        # 다운로드 메트릭 업데이트
        file_download_counter.labels(
            status="success",
            file_type=file_info.get("content_type", "unknown"),
            user_id="anonymous",
        ).inc()

        # 5. 백그라운드 작업: 다운로드 통계 수집
        if background_tasks:
            background_tasks.add_task(
                record_download_statistics,
                file_id,
                request.client.host if request else "unknown",
            )

        # 6. 성공 메트릭 업데이트
        processing_time = (datetime.now() - start_time).total_seconds()
        api_request_duration.labels(
            method="GET", endpoint="/download/{file_id}", status_code=200
        ).observe(processing_time)

        api_request_counter.labels(
            method="GET", endpoint="/download/{file_id}", status_code=200
        ).inc()

        return FileResponse(
            path=file_path,
            filename=file_info["filename"],
            media_type=file_info["content_type"],
        )

    except HTTPException:
        # HTTP 예외는 그대로 전파
        raise
    except Exception as e:
        # 에러 메트릭 업데이트
        file_download_counter.labels(
            status="error", file_type="unknown", user_id="anonymous"
        ).inc()

        api_request_counter.labels(
            method="GET", endpoint="/download/{file_id}", status_code=500
        ).inc()

        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


def parse_range_header(range_header: str, file_size: int) -> tuple:
    """Range 헤더 파싱"""
    if not range_header.startswith("bytes="):
        raise ValueError("Invalid range format")

    range_spec = range_header[6:]  # "bytes=" 제거
    parts = range_spec.split("-")

    if len(parts) != 2:
        raise ValueError("Invalid range format")

    start_str, end_str = parts

    if not start_str and not end_str:
        raise ValueError("Invalid range: both start and end are empty")

    if start_str:
        start = int(start_str)
        if start < 0 or start >= file_size:
            raise ValueError("Range start out of bounds")
    else:
        start = file_size - int(end_str) - 1
        if start < 0:
            start = 0

    if end_str:
        end = int(end_str)
        if end < start or end >= file_size:
            end = file_size - 1
    else:
        end = file_size - 1

    return start, end


async def stream_file_range(
    file_path: Path,
    filename: str,
    content_type: str,
    start: int,
    end: int,
    file_size: int,
):
    """Range 요청에 대한 스트리밍 응답"""
    from fastapi.responses import StreamingResponse

    async def file_stream():
        chunk_size = 8192  # 8KB 청크
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1

            while remaining > 0:
                chunk_size = min(chunk_size, remaining)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    return StreamingResponse(
        file_stream(),
        media_type=content_type,
        headers=headers,
        status_code=206,  # Partial Content
    )


async def record_download_statistics(file_id: str, client_ip: str):
    """다운로드 통계 기록 (백그라운드 작업)"""
    try:
        # Redis에 다운로드 통계 저장
        download_key = f"download_stats:{file_id}"
        download_count = redis_client.get(download_key)

        if download_count:
            redis_client.incr(download_key)
        else:
            redis_client.setex(download_key, 86400, 1)  # 24시간 만료

        # IP별 다운로드 통계
        ip_key = f"download_ip:{client_ip}"
        redis_client.incr(ip_key)
        redis_client.expire(ip_key, 3600)  # 1시간 만료

    except Exception as e:
        print(f"다운로드 통계 기록 실패: {e}")


@app.get(
    "/view/{file_id}",
    summary="파일 미리보기",
    description="""
    파일을 브라우저에서 직접 미리보기할 수 있습니다.

    ## 기능
    - 이미지 파일: 브라우저에서 직접 표시
    - PDF 파일: PDF 뷰어로 표시
    - 텍스트 파일: 텍스트로 표시
    - 기타 파일: 다운로드 링크 제공

    ## 지원 파일 형식
    - **이미지**: jpg, jpeg, png, gif, webp, bmp, tiff
    - **PDF**: pdf
    - **텍스트**: txt, md, json, xml, csv, log
    - **기타**: 다운로드 링크로 안내

    ## 파라미터
    - `file_id`: 미리보기할 파일의 고유 식별자 (UUID)

    ## 응답
    - 지원되는 파일: 적절한 Content-Type으로 파일 내용 반환
    - 지원되지 않는 파일: HTML 페이지로 다운로드 링크 제공

    ## 사용 예제
    ```bash
    # 이미지 미리보기
    curl -X GET "http://localhost:8000/view/{file_id}" \\
         -H "Authorization: Bearer YOUR_TOKEN"

    # 브라우저에서 직접 접근
    # http://localhost:8000/view/{file_id}
    ```
    """,
    tags=["파일 관리"],
    responses=get_common_error_responses(),
)
async def view_file(
    file_id: str = Path(
        description="미리보기할 파일의 고유 식별자",
        example="550e8400-e29b-41d4-a716-446655440000",
    ),
    current_user=Depends(require_file_read),
):
    """파일 미리보기 API - 고급 텍스트/이미지 미리보기"""
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

        # 고급 파일 미리보기 서비스 사용
        from app.services.file_preview_service import file_preview_service

        preview_info = await file_preview_service.get_file_preview(
            file_path, file_info["filename"]
        )

        if preview_info["type"] == "text" and preview_info["preview_available"]:
            # 텍스트 파일 미리보기
            return {
                "file_id": file_id,
                "filename": file_info["filename"],
                "preview_type": "text",
                "content": preview_info["content"],
                "encoding": preview_info["encoding"],
                "file_size": preview_info["file_size"],
                "total_lines": preview_info["total_lines"],
                "preview_lines": preview_info["preview_lines"],
                "truncated": preview_info["truncated"],
                "message": "텍스트 파일 미리보기",
            }

        elif preview_info["type"] == "image" and preview_info["preview_available"]:
            # 이미지 파일 정보 반환
            return {
                "file_id": file_id,
                "filename": file_info["filename"],
                "preview_type": "image",
                "width": preview_info["width"],
                "height": preview_info["height"],
                "format": preview_info["format"],
                "file_size": preview_info["file_size"],
                "message": "이미지 파일 정보",
            }

        else:
            # 미리보기 불가능한 파일
            return {
                "file_id": file_id,
                "filename": file_info["filename"],
                "preview_type": "unsupported",
                "reason": preview_info.get("reason", "지원하지 않는 파일 타입"),
                "file_size": preview_info.get("file_size", 0),
                "message": "미리보기를 지원하지 않는 파일입니다",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"View failed: {str(e)}")


@app.get("/metrics")
async def metrics():
    """
    Prometheus 메트릭 엔드포인트
    Task 9: Prometheus 메트릭 및 모니터링 시스템
    """
    from app.metrics import CONTENT_TYPE_LATEST, generate_latest

    # Redis 메트릭 업데이트
    try:
        redis_client = await get_async_redis_client()
        await update_redis_metrics(redis_client)
    except Exception as e:
        logger.error(f"Redis metrics update failed: {e}")

    # 활성 연결 수 업데이트
    try:
        import psutil

        process = psutil.Process()
        connections = len(process.connections())
        from app.middleware.metrics_middleware import record_active_connections

        record_active_connections(connections)
    except Exception as e:
        logger.error(f"Active connections update failed: {e}")

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/upload/errors", response_model=ErrorStatisticsResponse)
async def get_upload_errors(days: int = 30, db: Session = Depends(get_db)):
    """업로드 에러 통계 조회"""
    error_handler = ErrorHandlerService(db, str(UPLOAD_DIR))
    stats = await error_handler.get_error_statistics(days)
    return ErrorStatisticsResponse(**stats)


@app.delete("/api/v1/upload/errors/cleanup")
async def cleanup_error_logs(days: int = 90, db: Session = Depends(get_db)):
    """오래된 에러 로그 정리"""
    error_handler = ErrorHandlerService(db, str(UPLOAD_DIR))
    cleaned_count = await error_handler.cleanup_old_error_logs(days)
    return {"cleaned_count": cleaned_count, "days": days}


@app.get(
    "/api/v1/upload/statistics/{client_ip}", response_model=UploadStatisticsResponse
)
async def get_upload_statistics(
    client_ip: str, days: int = 7, db: Session = Depends(get_db)
):
    """IP별 업로드 통계 조회"""
    rate_limiter = RateLimiterService(db, redis_client)
    stats = rate_limiter.get_upload_statistics(client_ip, days)

    # 평균 파일 크기 계산
    if stats["total_uploads"] > 0:
        average_file_size = stats["total_size"] / stats["total_uploads"]
    else:
        average_file_size = 0.0

    return UploadStatisticsResponse(
        client_ip=stats["client_ip"],
        period_days=stats["period_days"],
        total_uploads=stats["total_uploads"],
        total_size=stats["total_size"],
        average_file_size=average_file_size,
        daily_stats=stats["daily_stats"],
    )


@app.get("/api/v1/metrics/detailed", response_model=MetricsResponse)
async def get_detailed_metrics(db: Session = Depends(get_db)):
    """상세 메트릭 조회"""
    try:
        # 기본 메트릭 수집
        from prometheus_client import REGISTRY

        # 업로드 통계
        upload_counter = REGISTRY.get_sample_value("file_uploads_total")
        download_counter = REGISTRY.get_sample_value("file_downloads_total")

        # 에러 통계
        error_counters = {}
        for sample in REGISTRY.get_sample_value("file_upload_errors_total"):
            error_counters[sample.labels["error_type"]] = sample.value

        # 평균 업로드 시간
        upload_duration = REGISTRY.get_sample_value("file_upload_duration_seconds_sum")
        upload_count = REGISTRY.get_sample_value("file_upload_duration_seconds_count")
        avg_duration = upload_duration / upload_count if upload_count > 0 else 0

        # 활성 업로드 수 (Redis에서 조회)
        active_uploads = len(redis_client.keys("concurrent_uploads:*"))

        # 저장소 사용량
        import shutil

        total, used, free = shutil.disk_usage(str(UPLOAD_DIR))
        storage_usage = {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "usage_percent": (used / total) * 100 if total > 0 else 0,
        }

        return MetricsResponse(
            file_uploads_total=int(upload_counter or 0),
            file_downloads_total=int(download_counter or 0),
            file_upload_errors_total=error_counters,
            average_upload_duration=float(avg_duration or 0),
            active_uploads=active_uploads,
            storage_usage=storage_usage,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메트릭 수집 실패: {str(e)}")


@app.get("/api/v1/security/headers-test")
async def test_security_headers():
    """
    보안 헤더 테스트 API
    Task 8: 레이트 리미팅 및 보안 헤더 구현

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
            "Content-Security-Policy (강화된 정책)",
            "Strict-Transport-Security (강화된 HSTS)",
            "Referrer-Policy: strict-origin-when-cross-origin",
            "Permissions-Policy",
            "Cross-Origin-Embedder-Policy: require-corp",
            "Cross-Origin-Opener-Policy: same-origin",
            "Cross-Origin-Resource-Policy: same-origin",
            "X-RateLimit-Limit: [레이트 리미트 정보]",
            "X-RateLimit-Remaining: [남은 요청 수]",
            "X-RateLimit-Reset: [리셋 시간]",
        ],
        "cors_policy": {
            "description": "Strict CORS policy applied",
            "allowed_origins": [
                "http://localhost:3000",
                "http://localhost:8080",
                "https://filewallball.com",
                "https://www.filewallball.com",
            ],
            "environment_origins": "Configurable via ALLOWED_ORIGINS env var",
        },
        "rate_limit_policy": {
            "description": "Advanced rate limiting applied to all endpoints",
            "limits": {
                "upload": "10/minute",
                "download": "100/minute",
                "read": "1000/minute",
                "api": "500/minute",
                "auth": "5/minute",
                "admin": "1000/minute",
            },
            "features": [
                "IP별 동적 제한",
                "의심스러운 IP 자동 감지",
                "차단된 IP 관리",
                "Retry-After 헤더 포함",
                "Redis 기반 카운터 저장",
            ],
        },
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
                "max_size_mb": file_validation_service.max_file_size // (1024 * 1024),
            },
            "allowed_extensions": file_validation_service.get_allowed_extensions(),
            "blocked_extensions": file_validation_service.get_blocked_extensions(),
            "allowed_mime_types": list(
                file_validation_service.allowed_mime_types.keys()
            ),
            "blocked_mime_types": list(file_validation_service.blocked_mime_types),
            "filename_restrictions": {
                "max_length": 255,
                "forbidden_patterns": file_validation_service.forbidden_filename_patterns,
                "forbidden_characters": ["<", ">", ":", '"', "|", "?", "*", "\\", "/"],
            },
            "security_features": [
                "Magic Number 기반 MIME 타입 검증",
                "악성 코드 패턴 검사",
                "실행 파일 차단",
                "스크립트 파일 차단",
                "파일명 보안 검증",
            ],
        },
    }


@app.get("/api/v1/audit/logs")
async def get_audit_logs(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=200, description="페이지당 로그 수"),
    user_id: Optional[int] = Query(None, description="사용자 ID로 필터링"),
    action: Optional[str] = Query(
        None, description="액션으로 필터링 (create, read, update, delete)"
    ),
    resource_type: Optional[str] = Query(
        None, description="리소스 타입으로 필터링 (file, user, system)"
    ),
    status: Optional[str] = Query(
        None, description="상태로 필터링 (success, failed, denied)"
    ),
    date_from: Optional[datetime] = Query(None, description="시작 날짜"),
    date_to: Optional[datetime] = Query(None, description="종료 날짜"),
    ip_address: Optional[str] = Query(None, description="IP 주소로 필터링"),
    db: Session = Depends(get_db),
    current_user=Depends(require_audit_read),
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
            filters["user_id"] = user_id
        if action:
            filters["action"] = action
        if resource_type:
            filters["resource_type"] = resource_type
        if status:
            filters["status"] = status
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        if ip_address:
            filters["ip_address"] = ip_address

        # RBAC 서비스를 통한 로그 조회
        logs, total = rbac_service.get_audit_logs(
            db=db, user=current_user, filters=filters, page=page, size=size
        )

        # 로그 데이터 변환
        log_data = []
        for log in logs:
            log_data.append(
                {
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
                    "created_at": log.created_at.isoformat(),
                }
            )

        return {
            "message": "Audit logs retrieved successfully",
            "status": "success",
            "data": {
                "logs": log_data,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "pages": (total + size - 1) // size,
                },
                "filters": filters,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="감사 로그 조회 중 오류가 발생했습니다",
        )


@app.get("/api/v1/rbac/permissions")
async def get_user_permissions(current_user=Depends(require_authenticated_user)):
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
                "file_access_rules": rbac_service.file_access_rules,
            },
        }

    except Exception as e:
        logger.error(f"Failed to retrieve user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="권한 정보 조회 중 오류가 발생했습니다",
        )


@app.post("/api/v1/ip-management/whitelist")
async def add_ip_to_whitelist(ip_address: str, current_user=Depends(require_admin)):
    """
    IP 화이트리스트 추가 API
    Task 7: IP 기반 인증 및 RBAC 시스템 구현
    """
    try:
        from app.dependencies.auth import add_ip_to_whitelist as add_whitelist

        add_whitelist(ip_address)
        return {
            "message": f"IP {ip_address}가 화이트리스트에 추가되었습니다",
            "ip_address": ip_address,
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"IP 화이트리스트 추가 중 오류가 발생했습니다: {str(e)}",
        )


@app.post("/api/v1/ip-management/blacklist")
async def add_ip_to_blacklist(ip_address: str, current_user=Depends(require_admin)):
    """
    IP 블랙리스트 추가 API
    Task 7: IP 기반 인증 및 RBAC 시스템 구현
    """
    try:
        from app.dependencies.auth import add_ip_to_blacklist as add_blacklist

        add_blacklist(ip_address)
        return {
            "message": f"IP {ip_address}가 블랙리스트에 추가되었습니다",
            "ip_address": ip_address,
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"IP 블랙리스트 추가 중 오류가 발생했습니다: {str(e)}",
        )


@app.get("/api/v1/ip-management/check/{ip_address}")
async def check_ip_status(ip_address: str, current_user=Depends(require_admin)):
    """
    IP 상태 확인 API
    Task 7: IP 기반 인증 및 RBAC 시스템 구현
    """
    try:
        from app.dependencies.auth import is_ip_allowed

        is_allowed = is_ip_allowed(ip_address)
        return {
            "ip_address": ip_address,
            "is_allowed": is_allowed,
            "message": f"IP {ip_address}는 {'허용' if is_allowed else '차단'} 상태입니다",
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"IP 상태 확인 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/api/v1/rate-limit/status")
async def get_rate_limit_status(
    request: Request, current_user=Depends(require_authenticated_user)
):
    """
    레이트 리미트 상태 확인 API
    Task 8: 레이트 리미팅 및 보안 헤더 구현
    """
    try:
        from app.services.advanced_rate_limiter import advanced_rate_limiter

        client_ip = advanced_rate_limiter.get_client_ip(request)
        endpoint = request.url.path

        # 현재 레이트 리미트 정보 확인
        is_limited, limit_info = await advanced_rate_limiter.check_rate_limit(
            request, endpoint
        )

        return {
            "client_ip": client_ip,
            "endpoint": endpoint,
            "is_limited": is_limited,
            "limit_info": limit_info,
            "message": "레이트 리미트 상태를 성공적으로 조회했습니다",
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"레이트 리미트 상태 확인 중 오류가 발생했습니다: {str(e)}",
        )


@app.post("/api/v1/rate-limit/block-ip")
async def block_ip_address(
    ip_address: str, reason: str = "Manual block", current_user=Depends(require_admin)
):
    """
    IP 주소 차단 API
    Task 8: 레이트 리미팅 및 보안 헤더 구현
    """
    try:
        from app.dependencies.auth import add_ip_to_blacklist

        add_ip_to_blacklist(ip_address)

        return {
            "ip_address": ip_address,
            "reason": reason,
            "message": f"IP {ip_address}가 차단되었습니다",
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"IP 차단 중 오류가 발생했습니다: {str(e)}"
        )


@app.post("/api/v1/rate-limit/unblock-ip")
async def unblock_ip_address(ip_address: str, current_user=Depends(require_admin)):
    """
    IP 주소 차단 해제 API
    Task 8: 레이트 리미팅 및 보안 헤더 구현
    """
    try:
        # 실제 구현에서는 Redis에서 차단 목록 제거
        return {
            "ip_address": ip_address,
            "message": f"IP {ip_address}의 차단이 해제되었습니다",
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"IP 차단 해제 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/api/v1/thumbnails/{file_id}")
async def get_thumbnail(
    file_id: str, size: str = "medium", current_user=Depends(require_file_read)
):
    """
    이미지 썸네일 조회 API
    Task 6: 파일 미리보기 및 썸네일 생성 시스템
    """
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

        # 이미지 파일인지 확인
        from app.services.file_preview_service import file_preview_service

        if not file_preview_service.is_image_file(file_info["filename"]):
            raise HTTPException(status_code=400, detail="이미지 파일이 아닙니다")

        # 캐시된 썸네일 확인
        cached_thumbnail = await file_preview_service.get_cached_thumbnail(
            file_id, size
        )
        if cached_thumbnail and cached_thumbnail.exists():
            return FileResponse(
                path=cached_thumbnail,
                media_type="image/webp",
                headers={"Cache-Control": "public, max-age=3600"},
            )

        # 썸네일 생성
        thumbnail_path = await file_preview_service.generate_thumbnail(
            file_path, size, "webp"
        )
        if thumbnail_path:
            # 썸네일 캐시에 저장
            await file_preview_service.cache_thumbnail(file_id, thumbnail_path, size)

            return FileResponse(
                path=thumbnail_path,
                media_type="image/webp",
                headers={"Cache-Control": "public, max-age=3600"},
            )
        else:
            raise HTTPException(status_code=500, detail="썸네일 생성에 실패했습니다")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Thumbnail generation failed: {str(e)}"
        )


@app.post("/api/v1/thumbnails/{file_id}/generate")
async def generate_thumbnail(
    file_id: str,
    size: str = "medium",
    format: str = "webp",
    background_tasks: BackgroundTasks = None,
    current_user=Depends(require_file_read),
):
    """
    썸네일 생성 API (백그라운드 작업)
    Task 6: 파일 미리보기 및 썸네일 생성 시스템
    """
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

        # 이미지 파일인지 확인
        from app.services.file_preview_service import file_preview_service

        if not file_preview_service.is_image_file(file_info["filename"]):
            raise HTTPException(status_code=400, detail="이미지 파일이 아닙니다")

        # 백그라운드에서 썸네일 생성
        async def generate_thumbnail_task():
            try:
                thumbnail_path = await file_preview_service.generate_thumbnail(
                    file_path, size, format
                )
                if thumbnail_path:
                    await file_preview_service.cache_thumbnail(
                        file_id, thumbnail_path, size
                    )
                    logger.info(f"썸네일 생성 완료: {file_id} - {size}")
                else:
                    logger.error(f"썸네일 생성 실패: {file_id} - {size}")
            except Exception as e:
                logger.error(f"썸네일 생성 작업 실패: {e}")

        if background_tasks:
            background_tasks.add_task(generate_thumbnail_task)
        else:
            asyncio.create_task(generate_thumbnail_task())

        return {
            "file_id": file_id,
            "size": size,
            "format": format,
            "message": "썸네일 생성이 시작되었습니다",
            "status": "processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Thumbnail generation failed: {str(e)}"
        )


@app.get("/api/v1/preview/supported-formats")
async def get_supported_preview_formats():
    """
    지원하는 미리보기 형식 조회 API
    Task 6: 파일 미리보기 및 썸네일 생성 시스템
    """
    from app.services.file_preview_service import file_preview_service

    return {
        "text_formats": sorted(list(file_preview_service.text_extensions)),
        "image_formats": sorted(list(file_preview_service.image_extensions)),
        "thumbnail_sizes": file_preview_service.thumbnail_sizes,
        "max_preview_size_mb": file_preview_service.max_preview_size / (1024 * 1024),
        "max_preview_lines": file_preview_service.max_preview_lines,
        "message": "지원하는 미리보기 형식 정보",
    }


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="기본 헬스체크",
    description="""
    애플리케이션의 기본 상태를 확인합니다.

    ## 기능
    - 애플리케이션 실행 상태 확인
    - 간단한 응답 시간 측정
    - Kubernetes liveness probe용

    ## 응답
    - `status`: 애플리케이션 상태 (healthy/unhealthy)
    - `timestamp`: 응답 시간 (ISO 8601 형식)
    - `service`: 서비스 이름
    - `version`: API 버전

    ## 사용 예제
    ```bash
    curl -X GET "http://localhost:8000/health"
    ```

    ## Kubernetes 연동
    이 엔드포인트는 Kubernetes liveness probe에서 사용됩니다.
    """,
    tags=["모니터링"],
    responses={
        200: {"description": "애플리케이션 정상 동작"},
        503: {"description": "애플리케이션 비정상 상태", "model": ErrorResponse},
    },
)
async def health_check():
    """
    헬스체크 API
    Task 9: Prometheus 메트릭 및 모니터링 시스템
    """
    return await health_check_service.get_health_status(detailed=False)


@app.get(
    "/health/detailed",
    response_model=DetailedHealthCheckResponse,
    summary="상세 헬스체크",
    description="""
    애플리케이션의 상세한 상태를 확인합니다.

    ## 기능
    - 데이터베이스 연결 상태 확인
    - Redis 연결 상태 확인
    - 각 컴포넌트별 응답 시간 측정
    - 시스템 리소스 상태 확인

    ## 응답
    - `status`: 전체 시스템 상태
    - `timestamp`: 응답 시간
    - `service`: 서비스 정보
    - `version`: API 버전
    - `checks`: 각 컴포넌트별 상태
      - `database`: 데이터베이스 상태 및 응답 시간
      - `redis`: Redis 상태 및 응답 시간
      - `application`: 애플리케이션 상태

    ## 사용 예제
    ```bash
    curl -X GET "http://localhost:8000/health/detailed"
    ```

    ## 모니터링 연동
    이 엔드포인트는 Prometheus와 Grafana에서 시스템 상태 모니터링에 사용됩니다.
    """,
    tags=["모니터링"],
    responses={
        200: {"description": "시스템 정상 동작"},
        503: {
            "description": "시스템 비정상 상태 - 하나 이상의 컴포넌트에 문제가 있음",
            "model": ErrorResponse,
        },
    },
)
async def detailed_health_check():
    """
    상세 헬스체크 API
    Task 9: Prometheus 메트릭 및 모니터링 시스템
    """
    return await health_check_service.get_health_status(detailed=True)


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness 체크 API (Kubernetes용)
    Task 9: Prometheus 메트릭 및 모니터링 시스템
    """
    health_status = await health_check_service.get_health_status(detailed=False)

    if health_status["status"] == "healthy":
        return {"status": "ready", "timestamp": health_status["timestamp"]}
    else:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service not ready"
        )


@app.get("/health/live")
async def liveness_check():
    """
    Liveness 체크 API (Kubernetes용)
    Task 9: Prometheus 메트릭 및 모니터링 시스템
    """
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@app.get("/api/v1/audit/logs")
async def get_audit_logs(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=200, description="페이지당 로그 수"),
    user_id: Optional[str] = Query(None, description="사용자 ID로 필터링"),
    action: Optional[str] = Query(None, description="액션으로 필터링"),
    resource_type: Optional[str] = Query(None, description="리소스 타입으로 필터링"),
    result: Optional[str] = Query(None, description="결과로 필터링"),
    date_from: Optional[datetime] = Query(None, description="시작 날짜"),
    date_to: Optional[datetime] = Query(None, description="종료 날짜"),
    user_ip: Optional[str] = Query(None, description="IP 주소로 필터링"),
    current_user=Depends(require_audit_read),
):
    """
    감사 로그 조회 API
    Task 10: 감사 로그 및 백그라운드 작업 시스템
    """
    try:
        # 액션 및 결과 변환
        audit_action = None
        if action:
            try:
                audit_action = AuditAction(action)
            except ValueError:
                raise HTTPException(status_code=400, detail="유효하지 않은 액션입니다")

        audit_result = None
        if result:
            try:
                audit_result = AuditResult(result)
            except ValueError:
                raise HTTPException(status_code=400, detail="유효하지 않은 결과입니다")

        # 감사 로그 조회
        logs_data = await audit_log_service.get_audit_logs(
            page=page,
            size=size,
            user_id=user_id,
            action=audit_action,
            resource_type=resource_type,
            result=audit_result,
            date_from=date_from,
            date_to=date_to,
            user_ip=user_ip,
        )

        return {
            "logs": logs_data["logs"],
            "pagination": logs_data["pagination"],
            "message": "감사 로그를 성공적으로 조회했습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"감사 로그 조회 실패: {str(e)}")


@app.get("/api/v1/audit/statistics")
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365, description="통계 기간 (일)"),
    user_id: Optional[str] = Query(None, description="사용자 ID로 필터링"),
    current_user=Depends(require_audit_read),
):
    """
    감사 로그 통계 조회 API
    Task 10: 감사 로그 및 백그라운드 작업 시스템
    """
    try:
        stats = await audit_log_service.get_audit_statistics(days, user_id)

        return {
            "statistics": stats,
            "period_days": days,
            "message": "감사 로그 통계를 성공적으로 조회했습니다",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"감사 로그 통계 조회 실패: {str(e)}"
        )


@app.delete("/api/v1/audit/logs/cleanup")
async def cleanup_audit_logs(
    days: int = Query(90, ge=30, le=365, description="보관 기간 (일)"),
    current_user=Depends(require_admin),
):
    """
    오래된 감사 로그 정리 API
    Task 10: 감사 로그 및 백그라운드 작업 시스템
    """
    try:
        cleaned_count = await audit_log_service.cleanup_old_audit_logs(days)

        return {
            "cleaned_count": cleaned_count,
            "retention_days": days,
            "message": f"{cleaned_count}개의 오래된 감사 로그를 정리했습니다",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"감사 로그 정리 실패: {str(e)}")


@app.post("/api/v1/background-tasks")
async def submit_background_task(
    task_type: str = Form(..., description="작업 타입"),
    task_data: str = Form(..., description="작업 데이터 (JSON)"),
    background_tasks: BackgroundTasks = None,
    current_user=Depends(require_admin),
):
    """
    백그라운드 작업 제출 API
    Task 10: 감사 로그 및 백그라운드 작업 시스템
    """
    try:
        # 작업 타입 검증
        try:
            task_type_enum = TaskType(task_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 작업 타입입니다")

        # 작업 데이터 파싱
        try:
            import json

            parsed_task_data = json.loads(task_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="유효하지 않은 JSON 형식입니다")

        # 백그라운드 작업 제출
        task_id = await background_task_service.submit_task(
            task_type=task_type_enum,
            task_data=parsed_task_data,
            background_tasks=background_tasks,
            user_id=current_user.get("user_id") if current_user else None,
            user_ip=current_user.get("user_ip") if current_user else None,
        )

        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "submitted",
            "message": "백그라운드 작업이 성공적으로 제출되었습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"백그라운드 작업 제출 실패: {str(e)}"
        )


@app.get("/api/v1/background-tasks/{task_id}")
async def get_background_task_status(task_id: str, current_user=Depends(require_admin)):
    """
    백그라운드 작업 상태 조회 API
    Task 10: 감사 로그 및 백그라운드 작업 시스템
    """
    try:
        task_info = await background_task_service.get_task_status(task_id)

        if not task_info:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        return {
            "task_info": task_info,
            "message": "작업 상태를 성공적으로 조회했습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 상태 조회 실패: {str(e)}")


@app.get("/api/v1/background-tasks")
async def get_background_tasks(current_user=Depends(require_admin)):
    """
    백그라운드 작업 목록 조회 API
    Task 10: 감사 로그 및 백그라운드 작업 시스템
    """
    try:
        active_tasks = await background_task_service.get_active_tasks()
        task_history = await background_task_service.get_task_history(limit=50)

        return {
            "active_tasks": active_tasks,
            "task_history": task_history,
            "message": "백그라운드 작업 목록을 성공적으로 조회했습니다",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 목록 조회 실패: {str(e)}")


@app.delete("/api/v1/background-tasks/{task_id}")
async def cancel_background_task(task_id: str, current_user=Depends(require_admin)):
    """
    백그라운드 작업 취소 API
    Task 10: 감사 로그 및 백그라운드 작업 시스템
    """
    try:
        cancelled = await background_task_service.cancel_task(task_id)

        if not cancelled:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "백그라운드 작업이 성공적으로 취소되었습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 취소 실패: {str(e)}")


@app.get("/api/v1/files")
async def get_file_list(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=200, description="페이지당 파일 수"),
    sort_by: str = Query(
        "upload_time",
        description="정렬 기준 (upload_time, filename, size, content_type)",
    ),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
    file_type: Optional[str] = Query(
        None, description="파일 타입 필터 (image, video, audio, document 등)"
    ),
    date_from: Optional[datetime] = Query(None, description="업로드 시작 날짜"),
    date_to: Optional[datetime] = Query(None, description="업로드 종료 날짜"),
    min_size: Optional[int] = Query(None, ge=0, description="최소 파일 크기 (바이트)"),
    max_size: Optional[int] = Query(None, ge=0, description="최대 파일 크기 (바이트)"),
    filename_search: Optional[str] = Query(None, description="파일명 검색"),
    user_id: Optional[str] = Query(None, description="사용자 ID 필터"),
    include_deleted: bool = Query(False, description="삭제된 파일 포함 여부"),
    current_user=Depends(require_file_read),
):
    """
    파일 목록 조회 API
    Task 11: 파일 목록 조회 및 검색 API
    """
    try:
        # 정렬 기준 검증
        try:
            sort_by_enum = SortBy(sort_by)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 정렬 기준입니다")

        # 정렬 순서 검증
        try:
            sort_order_enum = SortOrder(sort_order)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 정렬 순서입니다")

        # 파일 목록 조회
        result = await file_list_service.get_file_list(
            page=page,
            size=size,
            sort_by=sort_by_enum,
            sort_order=sort_order_enum,
            file_type=file_type,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            filename_search=filename_search,
            user_id=user_id,
            include_deleted=include_deleted,
        )

        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="file_list",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.SUCCESS,
                details={
                    "page": page,
                    "size": size,
                    "total_count": result["pagination"]["total_count"],
                    "filters": result["filters"],
                },
            )
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

        return {
            "files": result["items"],
            "pagination": result["pagination"],
            "filters": result["filters"],
            "sorting": result["sorting"],
            "message": "파일 목록을 성공적으로 조회했습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="file_list",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.FAILED,
                error_message=str(e),
            )
        except Exception as log_error:
            logger.error(f"감사 로그 기록 실패: {log_error}")

        raise HTTPException(status_code=500, detail=f"파일 목록 조회 실패: {str(e)}")


@app.get("/api/v1/files/statistics")
async def get_file_statistics(
    user_id: Optional[str] = Query(None, description="사용자 ID 필터"),
    days: int = Query(30, ge=1, le=365, description="통계 기간 (일)"),
    current_user=Depends(require_file_read),
):
    """
    파일 통계 조회 API
    Task 11: 파일 목록 조회 및 검색 API
    """
    try:
        stats = await file_list_service.get_file_statistics(user_id, days)

        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="file_statistics",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.SUCCESS,
                details={"period_days": days, "user_id": user_id},
            )
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

        return {
            "statistics": stats,
            "period_days": days,
            "message": "파일 통계를 성공적으로 조회했습니다",
        }

    except Exception as e:
        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="file_statistics",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.FAILED,
                error_message=str(e),
            )
        except Exception as log_error:
            logger.error(f"감사 로그 기록 실패: {log_error}")

        raise HTTPException(status_code=500, detail=f"파일 통계 조회 실패: {str(e)}")


@app.get("/api/v1/files/search")
async def search_files(
    query: str = Query(..., description="검색 쿼리"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=200, description="페이지당 결과 수"),
    search_fields: Optional[str] = Query(
        "filename,content_type", description="검색 필드 (쉼표로 구분)"
    ),
    current_user=Depends(require_file_read),
):
    """
    파일 검색 API
    Task 11: 파일 목록 조회 및 검색 API
    """
    try:
        # 검색 필드 파싱
        fields = (
            [field.strip() for field in search_fields.split(",")]
            if search_fields
            else ["filename", "content_type"]
        )

        # 파일 검색
        result = await file_list_service.search_files(
            query=query, page=page, size=size, search_fields=fields
        )

        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="file_search",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.SUCCESS,
                details={
                    "query": query,
                    "search_fields": fields,
                    "results_count": result["search"]["results_count"],
                },
            )
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

        return {
            "files": result["items"],
            "pagination": result["pagination"],
            "search": result["search"],
            "message": "파일 검색을 성공적으로 완료했습니다",
        }

    except Exception as e:
        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.READ,
                resource_type="file_search",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.FAILED,
                error_message=str(e),
            )
        except Exception as log_error:
            logger.error(f"감사 로그 기록 실패: {log_error}")

        raise HTTPException(status_code=500, detail=f"파일 검색 실패: {str(e)}")


@app.delete("/api/v1/files/cache/invalidate")
async def invalidate_file_cache(
    pattern: str = Query("file_list:*", description="캐시 패턴"),
    current_user=Depends(require_admin),
):
    """
    파일 목록 캐시 무효화 API
    Task 11: 파일 목록 조회 및 검색 API
    """
    try:
        invalidated_count = await file_list_service.invalidate_cache(pattern)

        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file_cache",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.SUCCESS,
                details={"pattern": pattern, "invalidated_count": invalidated_count},
            )
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

        return {
            "invalidated_count": invalidated_count,
            "pattern": pattern,
            "message": f"{invalidated_count}개의 캐시를 성공적으로 무효화했습니다",
        }

    except Exception as e:
        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file_cache",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.FAILED,
                error_message=str(e),
            )
        except Exception as log_error:
            logger.error(f"감사 로그 기록 실패: {log_error}")

        raise HTTPException(status_code=500, detail=f"캐시 무효화 실패: {str(e)}")


@app.delete("/api/v1/files/{file_id}")
async def delete_file(
    file_id: str,
    deletion_type: str = Query("soft", description="삭제 타입 (soft, hard, permanent)"),
    backup_before_delete: bool = Query(True, description="삭제 전 백업 생성 여부"),
    reason: Optional[str] = Query(None, description="삭제 사유"),
    current_user=Depends(require_file_delete),
):
    """
    파일 삭제 API
    Task 12: 파일 삭제 및 정리 시스템
    """
    try:
        # 삭제 타입 검증
        try:
            deletion_type_enum = DeletionType(deletion_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 삭제 타입입니다")

        # 파일 삭제 수행
        result = await file_deletion_service.delete_file(
            file_id=file_id,
            deletion_type=deletion_type_enum,
            backup_before_delete=backup_before_delete,
            user_id=current_user.get("user_id") if current_user else None,
            user_ip=current_user.get("user_ip") if current_user else None,
            reason=reason,
        )

        return {
            "file_id": file_id,
            "deletion_result": result,
            "message": "파일이 성공적으로 삭제되었습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 삭제 실패: {str(e)}")


@app.post("/api/v1/files/{file_id}/restore")
async def restore_file(file_id: str, current_user=Depends(require_file_update)):
    """
    소프트 삭제된 파일 복원 API
    Task 12: 파일 삭제 및 정리 시스템
    """
    try:
        result = await file_deletion_service.restore_file(
            file_id=file_id,
            user_id=current_user.get("user_id") if current_user else None,
        )

        return {
            "file_id": file_id,
            "restore_result": result,
            "message": "파일이 성공적으로 복원되었습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 복원 실패: {str(e)}")


@app.get("/api/v1/files/deleted")
async def get_deleted_files(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=200, description="페이지당 파일 수"),
    user_id: Optional[str] = Query(None, description="사용자 ID 필터"),
    current_user=Depends(require_admin),
):
    """
    삭제된 파일 목록 조회 API
    Task 12: 파일 삭제 및 정리 시스템
    """
    try:
        result = await file_deletion_service.get_deleted_files(
            page=page, size=size, user_id=user_id
        )

        return {
            "deleted_files": result["files"],
            "pagination": result["pagination"],
            "message": "삭제된 파일 목록을 성공적으로 조회했습니다",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"삭제된 파일 목록 조회 실패: {str(e)}"
        )


@app.delete("/api/v1/files/cleanup")
async def cleanup_old_deleted_files(
    days: int = Query(30, ge=1, le=365, description="보관 기간 (일)"),
    current_user=Depends(require_admin),
):
    """
    오래된 삭제 파일 정리 API
    Task 12: 파일 삭제 및 정리 시스템
    """
    try:
        result = await file_deletion_service.cleanup_old_deleted_files(days)

        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file_cleanup",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.SUCCESS,
                details={
                    "cleaned_count": result["cleaned_count"],
                    "retention_days": days,
                },
            )
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")

        return {
            "cleanup_result": result,
            "message": "오래된 삭제 파일 정리를 완료했습니다",
        }

    except Exception as e:
        # 감사 로그 기록
        try:
            await audit_log_service.log_audit_event(
                action=AuditAction.DELETE,
                resource_type="file_cleanup",
                user_id=current_user.get("user_id") if current_user else None,
                user_ip=current_user.get("user_ip") if current_user else None,
                result=AuditResult.FAILED,
                error_message=str(e),
            )
        except Exception as log_error:
            logger.error(f"감사 로그 기록 실패: {log_error}")

        raise HTTPException(status_code=500, detail=f"파일 정리 실패: {str(e)}")


@app.get("/api/v1/files/{file_id}/backup")
async def get_backup_info(file_id: str, current_user=Depends(require_admin)):
    """
    파일 백업 정보 조회 API
    Task 12: 파일 삭제 및 정리 시스템
    """
    try:
        backup_info = await file_deletion_service.get_backup_info(file_id)

        if not backup_info:
            raise HTTPException(status_code=404, detail="백업 정보를 찾을 수 없습니다")

        return {
            "file_id": file_id,
            "backup_info": backup_info,
            "message": "백업 정보를 성공적으로 조회했습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"백업 정보 조회 실패: {str(e)}")


@app.post("/api/v1/files/{file_id}/restore-from-backup")
async def restore_from_backup(file_id: str, current_user=Depends(require_admin)):
    """
    백업에서 파일 복원 API
    Task 12: 파일 삭제 및 정리 시스템
    """
    try:
        result = await file_deletion_service.restore_from_backup(
            file_id=file_id,
            user_id=current_user.get("user_id") if current_user else None,
        )

        return {
            "file_id": file_id,
            "restore_result": result,
            "message": "백업에서 파일이 성공적으로 복원되었습니다",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"백업에서 파일 복원 실패: {str(e)}"
        )


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    global redis_metrics_task

    try:
        # 스케줄러 시작
        await scheduler_service.start_scheduler()
        print("✅ File cleanup scheduler started successfully")

        # Redis 메트릭 업데이트 태스크 시작
        redis_metrics_task = asyncio.create_task(update_redis_metrics_periodically())
        print("✅ Redis metrics update task started successfully")

    except Exception as e:
        print(f"❌ Failed to start services: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트"""
    global redis_metrics_task

    try:
        # 스케줄러 중지
        await scheduler_service.stop_scheduler()
        print("✅ File cleanup scheduler stopped successfully")

        # Redis 메트릭 업데이트 태스크 중지
        if redis_metrics_task and not redis_metrics_task.done():
            redis_metrics_task.cancel()
            try:
                await redis_metrics_task
            except asyncio.CancelledError:
                pass
        print("✅ Redis metrics update task stopped successfully")

    except Exception as e:
        print(f"❌ Failed to stop services: {e}")


@app.post("/keygen")
async def generate_project_key(
    project_name: str = Form(..., description="프로젝트명"),
    request_date: str = Form(..., description="요청 날짜 (YYYYMMDD)"),
    master_key: str = Form(..., description="마스터 키"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    프로젝트 고유 키 생성 API
    
    ## 기능
    - 프로젝트명, 요청 날짜, IP 주소를 기반으로 고유 키 생성
    - 마스터 키 검증
    - 생성된 키를 데이터베이스에 저장
    
    ## 파라미터
    - `project_name`: 프로젝트명 (필수)
    - `request_date`: 요청 날짜 YYYYMMDD 형식 (필수)
    - `master_key`: 마스터 키 (필수)
    
    ## 응답
    - `project_key`: 생성된 프로젝트 키
    - `project_name`: 프로젝트명
    - `request_date`: 요청 날짜
    - `request_ip`: 요청 IP 주소
    - `message`: 성공 메시지
    """
    try:
        # 마스터 키 검증
        expected_master_key = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
        if master_key != expected_master_key:
            raise HTTPException(
                status_code=401, 
                detail="마스터 키가 유효하지 않습니다"
            )
        
        # 요청 날짜 형식 검증
        try:
            datetime.strptime(request_date, "%Y%m%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="요청 날짜는 YYYYMMDD 형식이어야 합니다"
            )
        
        # 클라이언트 IP 추출
        client_ip = request.client.host if request else "unknown"
        
        # 프로젝트 키 서비스 초기화
        project_key_service = ProjectKeyService(db)
        
        # 프로젝트 키 생성
        project_key_obj = project_key_service.create_project_key(
            project_name=project_name,
            request_date=request_date,
            request_ip=client_ip
        )
        
        return {
            "project_key": project_key_obj.project_key,
            "project_name": project_key_obj.project_name,
            "request_date": project_key_obj.request_date,
            "request_ip": project_key_obj.request_ip,
            "message": "프로젝트 키가 성공적으로 생성되었습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"프로젝트 키 생성 실패: {str(e)}"
        )
