#!/usr/bin/env python3
"""
FileWallBall 캐시 키 전략 및 데이터 모델
Task 3.2: 캐시 키 전략 및 데이터 모델 구현
"""

import hashlib
import json
import logging
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 로깅 설정
logger = logging.getLogger(__name__)


class CacheKeyPrefix(str, Enum):
    """캐시 키 프리픽스 열거형"""

    # 파일 관련
    FILE_META = "file:meta"
    FILE_CONTENT = "file:content"
    FILE_STATS = "file:stats"
    FILE_ACCESS = "file:access"

    # 사용자 관련
    USER_SESSION = "user:session"
    USER_ACTIVITY = "user:activity"
    USER_PREFERENCES = "user:preferences"

    # 통계 관련
    STATS_DAILY = "stats:daily"
    STATS_HOURLY = "stats:hourly"
    STATS_MONTHLY = "stats:monthly"

    # 시스템 관련
    SYSTEM_SETTINGS = "system:settings"
    API_RATE_LIMIT = "rate_limit"
    TEMP_UPLOAD = "temp:upload"
    TEMP_DOWNLOAD = "temp:download"

    # 검색 관련
    SEARCH_INDEX = "search:index"
    SEARCH_RESULTS = "search:results"


class CacheTTL(int, Enum):
    """캐시 TTL 상수 (초 단위)"""

    # 파일 관련
    FILE_META = 3600  # 1시간
    FILE_CONTENT = 1800  # 30분
    FILE_STATS = 86400  # 24시간
    FILE_ACCESS = 300  # 5분

    # 사용자 관련
    USER_SESSION = 86400  # 24시간
    USER_ACTIVITY = 7200  # 2시간
    USER_PREFERENCES = 604800  # 7일

    # 통계 관련
    STATS_DAILY = 86400  # 24시간
    STATS_HOURLY = 3600  # 1시간
    STATS_MONTHLY = 2592000  # 30일

    # 시스템 관련
    SYSTEM_SETTINGS = 3600  # 1시간
    API_RATE_LIMIT = 60  # 1분
    TEMP_DATA = 600  # 10분

    # 검색 관련
    SEARCH_INDEX = 1800  # 30분
    SEARCH_RESULTS = 300  # 5분


class FileMetadata(BaseModel):
    """파일 메타데이터 모델"""

    file_id: UUID = Field(..., description="파일 고유 ID")
    filename: str = Field(..., description="파일명")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    mime_type: str = Field(..., description="MIME 타입")
    upload_time: datetime = Field(..., description="업로드 시간")
    uploader_ip: str = Field(..., description="업로드자 IP")
    checksum: str = Field(..., description="파일 체크섬")
    is_public: bool = Field(default=False, description="공개 여부")
    download_count: int = Field(default=0, description="다운로드 횟수")
    last_accessed: Optional[datetime] = Field(None, description="마지막 접근 시간")

    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
    )

    @field_validator("checksum")
    @classmethod
    def validate_checksum(cls, v):
        """체크섬 유효성 검사"""
        if len(v) != 64:  # SHA-256
            raise ValueError("체크섬은 SHA-256 형식이어야 합니다")
        return v


class UserSession(BaseModel):
    """사용자 세션 모델"""

    user_id: str = Field(..., description="사용자 ID (IP 또는 세션 ID)")
    session_id: str = Field(..., description="세션 ID")
    created_at: datetime = Field(..., description="세션 생성 시간")
    last_activity: datetime = Field(..., description="마지막 활동 시간")
    ip_address: str = Field(..., description="IP 주소")
    user_agent: Optional[str] = Field(None, description="User Agent")
    upload_count: int = Field(default=0, description="업로드 횟수")
    download_count: int = Field(default=0, description="다운로드 횟수")
    is_active: bool = Field(default=True, description="활성 상태")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class FileStats(BaseModel):
    """파일 통계 모델"""

    file_id: UUID = Field(..., description="파일 ID")
    stats_date: date = Field(..., description="통계 날짜")
    download_count: int = Field(default=0, description="다운로드 횟수")
    upload_count: int = Field(default=0, description="업로드 횟수")
    total_size: int = Field(default=0, description="총 파일 크기")
    unique_visitors: int = Field(default=0, description="고유 방문자 수")
    peak_hour: Optional[int] = Field(None, description="피크 시간 (0-23)")

    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            date: lambda v: v.isoformat(),
        }
    )


class SystemSettings(BaseModel):
    """시스템 설정 모델"""

    key: str = Field(..., description="설정 키")
    value: Any = Field(..., description="설정 값")
    description: Optional[str] = Field(None, description="설정 설명")
    updated_at: datetime = Field(..., description="업데이트 시간")
    updated_by: Optional[str] = Field(None, description="업데이트자")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class RateLimitInfo(BaseModel):
    """레이트 리미트 정보 모델"""

    ip_address: str = Field(..., description="IP 주소")
    endpoint: str = Field(..., description="엔드포인트")
    request_count: int = Field(default=0, description="요청 횟수")
    window_start: datetime = Field(..., description="윈도우 시작 시간")
    limit: int = Field(..., description="제한 횟수")
    window_size: int = Field(..., description="윈도우 크기 (초)")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class SearchResult(BaseModel):
    """검색 결과 모델"""

    query: str = Field(..., description="검색 쿼리")
    results: List[Dict[str, Any]] = Field(..., description="검색 결과")
    total_count: int = Field(..., description="총 결과 수")
    search_time: float = Field(..., description="검색 소요 시간")
    cached_at: datetime = Field(..., description="캐시 시간")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class CacheKeyManager:
    """캐시 키 관리 클래스"""

    def __init__(self, namespace: str = "filewallball"):
        """
        캐시 키 관리자 초기화

        Args:
            namespace: 캐시 네임스페이스
        """
        self.namespace = namespace

    def _build_key(self, prefix: str, *parts: Any) -> str:
        """
        캐시 키 생성

        Args:
            prefix: 키 프리픽스
            *parts: 키 구성 요소들

        Returns:
            str: 생성된 캐시 키
        """
        # 모든 부분을 문자열로 변환
        key_parts = [str(part) for part in parts]

        # 키 생성
        key = f"{self.namespace}:{prefix}:{':'.join(key_parts)}"

        # 키 길이 제한 (Redis 키는 512바이트 제한)
        if len(key.encode("utf-8")) > 500:
            # 긴 키는 해시로 축약
            key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
            key = f"{self.namespace}:{prefix}:hash:{key_hash}"

        return key

    def file_meta_key(self, file_id: Union[str, UUID]) -> str:
        """파일 메타데이터 키 생성"""
        return self._build_key(CacheKeyPrefix.FILE_META, file_id)

    def file_content_key(self, file_id: Union[str, UUID]) -> str:
        """파일 내용 키 생성"""
        return self._build_key(CacheKeyPrefix.FILE_CONTENT, file_id)

    def file_stats_key(self, file_id: Union[str, UUID], date: Union[str, date]) -> str:
        """파일 통계 키 생성"""
        if hasattr(date, "isoformat"):
            date = date.isoformat()
        return self._build_key(CacheKeyPrefix.FILE_STATS, file_id, date)

    def file_access_key(self, file_id: Union[str, UUID]) -> str:
        """파일 접근 키 생성"""
        return self._build_key(CacheKeyPrefix.FILE_ACCESS, file_id)

    def user_session_key(self, user_id: str) -> str:
        """사용자 세션 키 생성"""
        return self._build_key(CacheKeyPrefix.USER_SESSION, user_id)

    def user_activity_key(self, user_id: str, date: Union[str, date]) -> str:
        """사용자 활동 키 생성"""
        if hasattr(date, "isoformat"):
            date = date.isoformat()
        return self._build_key(CacheKeyPrefix.USER_ACTIVITY, user_id, date)

    def user_preferences_key(self, user_id: str) -> str:
        """사용자 설정 키 생성"""
        return self._build_key(CacheKeyPrefix.USER_PREFERENCES, user_id)

    def stats_daily_key(self, date: Union[str, date]) -> str:
        """일별 통계 키 생성"""
        if hasattr(date, "isoformat"):
            date = date.isoformat()
        return self._build_key(CacheKeyPrefix.STATS_DAILY, date)

    def stats_hourly_key(self, date: Union[str, date], hour: int) -> str:
        """시간별 통계 키 생성"""
        if hasattr(date, "isoformat"):
            date = date.isoformat()
        return self._build_key(CacheKeyPrefix.STATS_HOURLY, date, hour)

    def stats_monthly_key(self, year: int, month: int) -> str:
        """월별 통계 키 생성"""
        return self._build_key(CacheKeyPrefix.STATS_MONTHLY, year, month)

    def system_settings_key(self, key: str) -> str:
        """시스템 설정 키 생성"""
        return self._build_key(CacheKeyPrefix.SYSTEM_SETTINGS, key)

    def rate_limit_key(self, ip: str, endpoint: str) -> str:
        """레이트 리미트 키 생성"""
        return self._build_key(CacheKeyPrefix.API_RATE_LIMIT, ip, endpoint)

    def temp_upload_key(self, upload_id: str) -> str:
        """임시 업로드 키 생성"""
        return self._build_key(CacheKeyPrefix.TEMP_UPLOAD, upload_id)

    def temp_download_key(self, token: str) -> str:
        """임시 다운로드 키 생성"""
        return self._build_key(CacheKeyPrefix.TEMP_DOWNLOAD, token)

    def search_index_key(self, query: str) -> str:
        """검색 인덱스 키 생성"""
        # 쿼리를 해시로 변환하여 키 길이 제한
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
        return self._build_key("search:index", query_hash)

    def search_results_key(self, query: str) -> str:
        """검색 결과 키 생성"""
        # 쿼리를 해시로 변환하여 키 길이 제한
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
        return self._build_key("search:results", query_hash)

    def get_pattern(self, prefix: str, *parts: Any) -> str:
        """
        패턴 매칭용 키 생성

        Args:
            prefix: 키 프리픽스
            *parts: 키 구성 요소들

        Returns:
            str: 패턴 매칭용 키
        """
        key_parts = [str(part) for part in parts]
        pattern = f"{self.namespace}:{prefix}:{':'.join(key_parts)}:*"
        return pattern


class CacheSerializer:
    """캐시 데이터 직렬화/역직렬화 클래스"""

    @staticmethod
    def serialize(data: BaseModel) -> str:
        """
        Pydantic 모델을 JSON 문자열로 직렬화

        Args:
            data: 직렬화할 Pydantic 모델

        Returns:
            str: JSON 문자열
        """
        try:
            return data.json(ensure_ascii=False)
        except Exception as e:
            logger.error(f"데이터 직렬화 실패: {e}")
            raise

    @staticmethod
    def deserialize(json_str: str, model_class: type) -> BaseModel:
        """
        JSON 문자열을 Pydantic 모델로 역직렬화

        Args:
            json_str: JSON 문자열
            model_class: 역직렬화할 모델 클래스

        Returns:
            BaseModel: 역직렬화된 모델 인스턴스
        """
        try:
            return model_class.parse_raw(json_str)
        except Exception as e:
            logger.error(f"데이터 역직렬화 실패: {e}")
            raise

    @staticmethod
    def serialize_dict(data: Dict[str, Any]) -> str:
        """
        딕셔너리를 JSON 문자열로 직렬화

        Args:
            data: 직렬화할 딕셔너리

        Returns:
            str: JSON 문자열
        """
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"딕셔너리 직렬화 실패: {e}")
            raise

    @staticmethod
    def deserialize_dict(json_str: str) -> Dict[str, Any]:
        """
        JSON 문자열을 딕셔너리로 역직렬화

        Args:
            json_str: JSON 문자열

        Returns:
            Dict[str, Any]: 역직렬화된 딕셔너리
        """
        try:
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"딕셔너리 역직렬화 실패: {e}")
            raise


class CacheHelper:
    """캐시 헬퍼 클래스"""

    def __init__(self, key_manager: CacheKeyManager, serializer: CacheSerializer):
        """
        캐시 헬퍼 초기화

        Args:
            key_manager: 키 관리자
            serializer: 직렬화기
        """
        self.key_manager = key_manager
        self.serializer = serializer

    def get_file_meta_key(self, file_id: Union[str, UUID]) -> str:
        """파일 메타데이터 키 반환"""
        return self.key_manager.file_meta_key(file_id)

    def get_user_session_key(self, user_id: str) -> str:
        """사용자 세션 키 반환"""
        return self.key_manager.user_session_key(user_id)

    def get_stats_key(self, date: Union[str, date]) -> str:
        """통계 키 반환"""
        return self.key_manager.stats_daily_key(date)

    def get_rate_limit_key(self, ip: str, endpoint: str) -> str:
        """레이트 리미트 키 반환"""
        return self.key_manager.rate_limit_key(ip, endpoint)

    def get_ttl(self, prefix: str) -> int:
        """프리픽스에 따른 TTL 반환"""
        try:
            return getattr(CacheTTL, prefix.upper().replace(":", "_"))
        except AttributeError:
            logger.warning(f"알 수 없는 프리픽스: {prefix}, 기본 TTL 사용")
            return CacheTTL.TEMP_DATA

    def create_file_metadata(self, **kwargs) -> FileMetadata:
        """파일 메타데이터 생성"""
        return FileMetadata(**kwargs)

    def create_user_session(self, **kwargs) -> UserSession:
        """사용자 세션 생성"""
        return UserSession(**kwargs)

    def create_file_stats(self, **kwargs) -> FileStats:
        """파일 통계 생성"""
        return FileStats(**kwargs)

    def create_system_settings(self, **kwargs) -> SystemSettings:
        """시스템 설정 생성"""
        return SystemSettings(**kwargs)

    def create_rate_limit_info(self, **kwargs) -> RateLimitInfo:
        """레이트 리미트 정보 생성"""
        return RateLimitInfo(**kwargs)

    def create_search_result(self, **kwargs) -> SearchResult:
        """검색 결과 생성"""
        return SearchResult(**kwargs)


# 전역 인스턴스
_key_manager = CacheKeyManager()
_serializer = CacheSerializer()
_cache_helper = CacheHelper(_key_manager, _serializer)


def get_cache_key_manager() -> CacheKeyManager:
    """전역 키 관리자 반환"""
    return _key_manager


def get_cache_serializer() -> CacheSerializer:
    """전역 직렬화기 반환"""
    return _serializer


def get_cache_helper() -> CacheHelper:
    """전역 캐시 헬퍼 반환"""
    return _cache_helper


# 사용 예시
if __name__ == "__main__":
    # 키 관리자 테스트
    key_manager = get_cache_key_manager()

    # 파일 메타데이터 키 생성
    file_key = key_manager.file_meta_key("123e4567-e89b-12d3-a456-426614174000")
    print(f"파일 메타데이터 키: {file_key}")

    # 사용자 세션 키 생성
    session_key = key_manager.user_session_key("192.168.1.1")
    print(f"사용자 세션 키: {session_key}")

    # 통계 키 생성
    stats_key = key_manager.stats_daily_key("2024-01-01")
    print(f"통계 키: {stats_key}")

    # 모델 생성 및 직렬화 테스트
    serializer = get_cache_serializer()

    file_meta = FileMetadata(
        file_id="123e4567-e89b-12d3-a456-426614174000",
        filename="test.txt",
        file_size=1024,
        mime_type="text/plain",
        upload_time=datetime.now(),
        uploader_ip="192.168.1.1",
        checksum="a" * 64,
    )

    json_data = serializer.serialize(file_meta)
    print(f"직렬화된 데이터: {json_data}")

    # 역직렬화 테스트
    deserialized = serializer.deserialize(json_data, FileMetadata)
    print(f"역직렬화된 데이터: {deserialized}")
