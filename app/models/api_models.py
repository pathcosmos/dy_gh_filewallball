"""
API 응답 모델
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """성공 응답 기본 모델"""
    status: str = Field(default="success", description="응답 상태")
    message: str = Field(description="응답 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")
    data: Optional[Dict[str, Any]] = Field(default=None, description="응답 데이터")


class ErrorResponse(BaseModel):
    """에러 응답 기본 모델"""
    status: str = Field(default="error", description="응답 상태")
    error_type: str = Field(description="에러 타입")
    error_message: str = Field(description="에러 메시지")
    status_code: int = Field(description="HTTP 상태 코드")
    is_retryable: bool = Field(description="재시도 가능 여부")
    file_uuid: Optional[str] = Field(default=None, description="파일 UUID")
    error_id: Optional[str] = Field(default=None, description="에러 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="에러 발생 시간")


class FileUploadResponse(BaseModel):
    """파일 업로드 성공 응답"""
    status: str = Field(default="success", description="응답 상태")
    file_uuid: str = Field(description="파일 UUID")
    original_filename: str = Field(description="원본 파일명")
    stored_filename: str = Field(description="저장된 파일명")
    file_size: int = Field(description="파일 크기 (바이트)")
    mime_type: str = Field(description="MIME 타입")
    file_hash: str = Field(description="파일 해시 (MD5)")
    category_id: Optional[int] = Field(default=None, description="카테고리 ID")
    tags: List[str] = Field(default=[], description="태그 목록")
    is_public: bool = Field(description="공개 여부")
    description: Optional[str] = Field(default=None, description="파일 설명")
    upload_time: str = Field(description="업로드 시간")
    upload_ip: str = Field(description="업로드 IP 주소")
    processing_time_ms: int = Field(description="처리 시간 (밀리초)")
    download_url: str = Field(description="다운로드 URL")
    view_url: str = Field(description="미리보기 URL")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")


class FileDuplicateResponse(BaseModel):
    """중복 파일 응답"""
    status: str = Field(default="duplicate", description="응답 상태")
    file_uuid: str = Field(description="기존 파일 UUID")
    message: str = Field(description="중복 파일 메시지")
    duplicate: bool = Field(default=True, description="중복 여부")
    existing_file_info: Optional[Dict[str, Any]] = Field(default=None, description="기존 파일 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")


class FileInfoResponse(BaseModel):
    """파일 정보 응답"""
    file_id: str = Field(description="파일 ID")
    filename: str = Field(description="파일명")
    size: int = Field(description="파일 크기")
    upload_time: datetime = Field(description="업로드 시간")
    download_url: str = Field(description="다운로드 URL")
    view_url: str = Field(description="미리보기 URL")
    content_type: Optional[str] = Field(default=None, description="MIME 타입")
    file_hash: Optional[str] = Field(default=None, description="파일 해시")


class UploadStatisticsResponse(BaseModel):
    """업로드 통계 응답"""
    client_ip: str = Field(description="클라이언트 IP")
    period_days: int = Field(description="통계 기간 (일)")
    total_uploads: int = Field(description="총 업로드 수")
    total_size: int = Field(description="총 파일 크기 (바이트)")
    average_file_size: float = Field(description="평균 파일 크기 (바이트)")
    daily_stats: List[Dict[str, Any]] = Field(description="일별 통계")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")


class RateLimitInfo(BaseModel):
    """Rate Limit 정보"""
    limit: int = Field(description="제한 수")
    remaining: int = Field(description="남은 요청 수")
    reset_time: int = Field(description="리셋 시간 (Unix timestamp)")
    current_count: int = Field(description="현재 요청 수")


class HealthCheckResponse(BaseModel):
    """헬스체크 응답"""
    status: str = Field(description="서비스 상태")
    timestamp: datetime = Field(default_factory=datetime.now, description="체크 시간")
    services: Dict[str, str] = Field(description="서비스별 상태")
    version: str = Field(description="API 버전")
    uptime: Optional[float] = Field(default=None, description="업타임 (초)")


class MetricsResponse(BaseModel):
    """메트릭 응답"""
    file_uploads_total: int = Field(description="총 업로드 수")
    file_downloads_total: int = Field(description="총 다운로드 수")
    file_upload_errors_total: Dict[str, int] = Field(description="에러별 업로드 실패 수")
    average_upload_duration: float = Field(description="평균 업로드 시간 (초)")
    active_uploads: int = Field(description="현재 활성 업로드 수")
    storage_usage: Dict[str, Any] = Field(description="저장소 사용량")
    timestamp: datetime = Field(default_factory=datetime.now, description="메트릭 수집 시간")


class ErrorStatisticsResponse(BaseModel):
    """에러 통계 응답"""
    period_days: int = Field(description="통계 기간 (일)")
    total_errors: int = Field(description="총 에러 수")
    error_types: Dict[str, int] = Field(description="에러 타입별 발생 수")
    retryable_errors: int = Field(description="재시도 가능한 에러 수")
    non_retryable_errors: int = Field(description="재시도 불가능한 에러 수")
    daily_error_stats: List[Dict[str, Any]] = Field(description="일별 에러 통계")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")


class PaginatedResponse(BaseModel):
    """페이지네이션 응답"""
    items: List[Any] = Field(description="아이템 목록")
    total: int = Field(description="총 아이템 수")
    page: int = Field(description="현재 페이지")
    per_page: int = Field(description="페이지당 아이템 수")
    total_pages: int = Field(description="총 페이지 수")
    has_next: bool = Field(description="다음 페이지 존재 여부")
    has_prev: bool = Field(description="이전 페이지 존재 여부")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")


class IPAuthResponse(BaseModel):
    """IP 인증 응답"""
    success: bool = Field(description="성공 여부")
    file_uuid: str = Field(description="파일 UUID")
    original_filename: str = Field(description="원본 파일명")
    file_size: int = Field(description="파일 크기")
    message: str = Field(description="응답 메시지")
    upload_time: str = Field(description="업로드 시간")
    processing_time_ms: int = Field(description="처리 시간 (밀리초)")
    auth_method: str = Field(default="ip_based", description="인증 방법")
    client_ip: str = Field(description="클라이언트 IP")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간") 