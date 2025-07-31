"""
Swagger 문서화를 위한 상세한 Pydantic 모델들
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """파일 업로드 응답 모델"""

    file_id: str = Field(
        ...,
        description="업로드된 파일의 고유 식별자 (UUID)",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    filename: str = Field(..., description="원본 파일명", example="document.pdf")
    download_url: str = Field(
        ...,
        description="파일 다운로드 URL",
        example="/download/550e8400-e29b-41d4-a716-446655440000",
    )
    view_url: str = Field(
        ...,
        description="파일 미리보기 URL",
        example="/view/550e8400-e29b-41d4-a716-446655440000",
    )
    message: str = Field(
        ...,
        description="업로드 결과 메시지",
        example="파일이 성공적으로 업로드되었습니다.",
    )

    class Config:
        schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "document.pdf",
                "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
                "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
                "message": "파일이 성공적으로 업로드되었습니다.",
            }
        }


class FileInfoResponse(BaseModel):
    """파일 정보 응답 모델"""

    file_uuid: str = Field(
        ...,
        description="파일 고유 식별자 (UUID)",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    filename: str = Field(..., description="원본 파일명", example="document.pdf")
    file_size: int = Field(..., description="파일 크기 (바이트)", example=1048576, ge=0)
    content_type: str = Field(..., description="MIME 타입", example="application/pdf")
    upload_time: datetime = Field(
        ..., description="업로드 시간", example="2024-01-15T10:30:00Z"
    )
    last_accessed: Optional[datetime] = Field(
        None, description="마지막 접근 시간", example="2024-01-16T14:20:00Z"
    )
    download_count: int = Field(..., description="다운로드 횟수", example=5, ge=0)
    is_public: bool = Field(..., description="공개 여부", example=True)
    tags: List[str] = Field(
        default_factory=list, description="파일 태그 목록", example=["document", "pdf"]
    )
    description: Optional[str] = Field(
        None, description="파일 설명", example="중요한 문서"
    )
    download_url: str = Field(
        ...,
        description="다운로드 URL",
        example="/download/550e8400-e29b-41d4-a716-446655440000",
    )
    preview_url: str = Field(
        ...,
        description="미리보기 URL",
        example="/view/550e8400-e29b-41d4-a716-446655440000",
    )

    class Config:
        schema_extra = {
            "example": {
                "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "document.pdf",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "upload_time": "2024-01-15T10:30:00Z",
                "last_accessed": "2024-01-16T14:20:00Z",
                "download_count": 5,
                "is_public": True,
                "tags": ["document", "pdf"],
                "description": "중요한 문서",
                "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
                "preview_url": "/view/550e8400-e29b-41d4-a716-446655440000",
            }
        }


class FileUploadResponse(BaseModel):
    """고급 파일 업로드 응답 모델"""

    file_uuid: str = Field(
        ...,
        description="파일 고유 식별자 (UUID)",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    filename: str = Field(..., description="원본 파일명", example="presentation.pptx")
    file_size: int = Field(..., description="파일 크기 (바이트)", example=2048576, ge=0)
    content_type: str = Field(
        ...,
        description="MIME 타입",
        example="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    upload_time: datetime = Field(
        ..., description="업로드 시간", example="2024-01-15T10:30:00Z"
    )
    category_id: Optional[int] = Field(None, description="파일 카테고리 ID", example=1)
    tags: List[str] = Field(
        default_factory=list,
        description="파일 태그 목록",
        example=["presentation", "business"],
    )
    is_public: bool = Field(..., description="공개 여부", example=True)
    description: Optional[str] = Field(
        None, description="파일 설명", example="분기별 실적 보고서"
    )
    download_url: str = Field(
        ...,
        description="다운로드 URL",
        example="/api/v1/files/550e8400-e29b-41d4-a716-446655440000/download",
    )
    preview_url: str = Field(
        ...,
        description="미리보기 URL",
        example="/api/v1/files/550e8400-e29b-41d4-a716-446655440000/preview",
    )

    class Config:
        schema_extra = {
            "example": {
                "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "presentation.pptx",
                "file_size": 2048576,
                "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "upload_time": "2024-01-15T10:30:00Z",
                "category_id": 1,
                "tags": ["presentation", "business"],
                "is_public": True,
                "description": "분기별 실적 보고서",
                "download_url": "/api/v1/files/550e8400-e29b-41d4-a716-446655440000/download",
                "preview_url": "/api/v1/files/550e8400-e29b-41d4-a716-446655440000/preview",
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답 모델"""

    detail: str = Field(
        ..., description="에러 상세 메시지", example="파일을 찾을 수 없습니다."
    )
    error_type: Optional[str] = Field(
        None, description="에러 타입", example="not_found"
    )
    error_code: Optional[int] = Field(
        None, description="에러 코드", example=404, ge=400, le=599
    )
    timestamp: Optional[datetime] = Field(
        None, description="에러 발생 시간", example="2024-01-15T10:30:00Z"
    )

    class Config:
        schema_extra = {
            "example": {
                "detail": "파일을 찾을 수 없습니다.",
                "error_type": "not_found",
                "error_code": 404,
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class HealthCheckResponse(BaseModel):
    """헬스체크 응답 모델"""

    status: str = Field(
        ..., description="시스템 상태", example="healthy", regex="^(healthy|unhealthy)$"
    )
    timestamp: datetime = Field(
        ..., description="응답 시간", example="2024-01-15T10:30:00Z"
    )
    service: str = Field(..., description="서비스 이름", example="FileWallBall API")
    version: str = Field(..., description="API 버전", example="1.0.0")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "service": "FileWallBall API",
                "version": "1.0.0",
            }
        }


class DetailedHealthCheckResponse(BaseModel):
    """상세 헬스체크 응답 모델"""

    status: str = Field(
        ...,
        description="전체 시스템 상태",
        example="healthy",
        regex="^(healthy|unhealthy)$",
    )
    timestamp: datetime = Field(
        ..., description="응답 시간", example="2024-01-15T10:30:00Z"
    )
    service: str = Field(..., description="서비스 이름", example="FileWallBall API")
    version: str = Field(..., description="API 버전", example="1.0.0")
    checks: dict = Field(
        ...,
        description="각 컴포넌트별 상태",
        example={
            "database": {"status": "healthy", "response_time": 2.5},
            "redis": {"status": "healthy", "response_time": 1.2},
            "application": {"status": "healthy", "response_time": 0.5},
        },
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "service": "FileWallBall API",
                "version": "1.0.0",
                "checks": {
                    "database": {"status": "healthy", "response_time": 2.5},
                    "redis": {"status": "healthy", "response_time": 1.2},
                    "application": {"status": "healthy", "response_time": 0.5},
                },
            }
        }


class FileListResponse(BaseModel):
    """파일 목록 응답 모델"""

    files: List[FileInfoResponse] = Field(..., description="파일 목록")
    total: int = Field(..., description="전체 파일 수", example=150, ge=0)
    page: int = Field(..., description="현재 페이지 번호", example=1, ge=1)
    size: int = Field(..., description="페이지당 파일 수", example=20, ge=1, le=200)
    total_pages: int = Field(..., description="전체 페이지 수", example=8, ge=0)

    class Config:
        schema_extra = {
            "example": {
                "files": [
                    {
                        "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "document.pdf",
                        "file_size": 1048576,
                        "content_type": "application/pdf",
                        "upload_time": "2024-01-15T10:30:00Z",
                        "download_count": 5,
                        "is_public": True,
                        "tags": ["document", "pdf"],
                        "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
                        "preview_url": "/view/550e8400-e29b-41d4-a716-446655440000",
                    }
                ],
                "total": 150,
                "page": 1,
                "size": 20,
                "total_pages": 8,
            }
        }


class MetricsResponse(BaseModel):
    """메트릭 응답 모델"""

    timestamp: datetime = Field(
        ..., description="메트릭 수집 시간", example="2024-01-15T10:30:00Z"
    )
    system_metrics: dict = Field(
        ...,
        description="시스템 메트릭",
        example={"cpu_usage": 45.2, "memory_usage": 67.8, "disk_usage": 23.4},
    )
    application_metrics: dict = Field(
        ...,
        description="애플리케이션 메트릭",
        example={"total_uploads": 1250, "total_downloads": 5670, "active_users": 45},
    )
    performance_metrics: dict = Field(
        ...,
        description="성능 메트릭",
        example={"avg_response_time": 125.5, "error_rate": 0.02, "throughput": 150.3},
    )

    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "system_metrics": {
                    "cpu_usage": 45.2,
                    "memory_usage": 67.8,
                    "disk_usage": 23.4,
                },
                "application_metrics": {
                    "total_uploads": 1250,
                    "total_downloads": 5670,
                    "active_users": 45,
                },
                "performance_metrics": {
                    "avg_response_time": 125.5,
                    "error_rate": 0.02,
                    "throughput": 150.3,
                },
            }
        }


class AuditLogResponse(BaseModel):
    """감사 로그 응답 모델"""

    id: int = Field(..., description="로그 ID", example=12345)
    user_id: Optional[str] = Field(None, description="사용자 ID", example="user123")
    action: str = Field(
        ...,
        description="수행된 액션",
        example="file_upload",
        regex="^(create|read|update|delete|upload|download|view)$",
    )
    resource_type: str = Field(
        ..., description="리소스 타입", example="file", regex="^(file|user|system)$"
    )
    resource_id: Optional[str] = Field(
        None, description="리소스 ID", example="550e8400-e29b-41d4-a716-446655440000"
    )
    result: str = Field(
        ...,
        description="액션 결과",
        example="success",
        regex="^(success|failed|denied)$",
    )
    ip_address: str = Field(..., description="사용자 IP 주소", example="192.168.1.100")
    user_agent: Optional[str] = Field(
        None,
        description="사용자 에이전트",
        example="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )
    timestamp: datetime = Field(
        ..., description="로그 생성 시간", example="2024-01-15T10:30:00Z"
    )
    details: Optional[str] = Field(
        None,
        description="추가 상세 정보",
        example="파일 업로드 성공: document.pdf (1.0MB)",
    )

    class Config:
        schema_extra = {
            "example": {
                "id": 12345,
                "user_id": "user123",
                "action": "file_upload",
                "resource_type": "file",
                "resource_id": "550e8400-e29b-41d4-a716-446655440000",
                "result": "success",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "timestamp": "2024-01-15T10:30:00Z",
                "details": "파일 업로드 성공: document.pdf (1.0MB)",
            }
        }


class BackgroundTaskResponse(BaseModel):
    """백그라운드 작업 응답 모델"""

    task_id: str = Field(
        ..., description="작업 ID", example="task_550e8400-e29b-41d4-a716-446655440000"
    )
    task_type: str = Field(
        ...,
        description="작업 타입",
        example="thumbnail_generation",
        regex="^(thumbnail_generation|file_hash_calculation|file_cleanup|backup_creation)$",
    )
    status: str = Field(
        ...,
        description="작업 상태",
        example="running",
        regex="^(pending|running|completed|failed|cancelled)$",
    )
    progress: int = Field(..., description="진행률 (0-100)", example=75, ge=0, le=100)
    created_at: datetime = Field(
        ..., description="작업 생성 시간", example="2024-01-15T10:30:00Z"
    )
    started_at: Optional[datetime] = Field(
        None, description="작업 시작 시간", example="2024-01-15T10:30:05Z"
    )
    completed_at: Optional[datetime] = Field(
        None, description="작업 완료 시간", example="2024-01-15T10:30:45Z"
    )
    result: Optional[str] = Field(
        None, description="작업 결과", example="썸네일 생성 완료: 3개 파일 처리됨"
    )
    error_message: Optional[str] = Field(
        None, description="에러 메시지 (실패 시)", example="파일을 찾을 수 없습니다."
    )

    class Config:
        schema_extra = {
            "example": {
                "task_id": "task_550e8400-e29b-41d4-a716-446655440000",
                "task_type": "thumbnail_generation",
                "status": "running",
                "progress": 75,
                "created_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:30:05Z",
                "completed_at": None,
                "result": None,
                "error_message": None,
            }
        }
