#!/usr/bin/env python3
"""
캐시 모델 및 키 관리 테스트
Task 3.2: 캐시 키 전략 및 데이터 모델 구현 테스트
"""

import json
from datetime import date, datetime
from uuid import uuid4

import pytest

from app.cache_models import (
    CacheHelper,
    CacheKeyManager,
    CacheKeyPrefix,
    CacheSerializer,
    CacheTTL,
    FileMetadata,
    FileStats,
    RateLimitInfo,
    SearchResult,
    SystemSettings,
    UserSession,
    get_cache_helper,
    get_cache_key_manager,
    get_cache_serializer,
)


class TestCacheKeyManager:
    """캐시 키 관리자 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.key_manager = CacheKeyManager("test")

    def test_file_meta_key(self):
        """파일 메타데이터 키 생성 테스트"""
        file_id = str(uuid4())
        key = self.key_manager.file_meta_key(file_id)
        expected = f"test:{CacheKeyPrefix.FILE_META}:{file_id}"
        assert key == expected

    def test_file_content_key(self):
        """파일 내용 키 생성 테스트"""
        file_id = str(uuid4())
        key = self.key_manager.file_content_key(file_id)
        expected = f"test:{CacheKeyPrefix.FILE_CONTENT}:{file_id}"
        assert key == expected

    def test_file_stats_key(self):
        """파일 통계 키 생성 테스트"""
        file_id = str(uuid4())
        test_date = date(2024, 1, 1)
        key = self.key_manager.file_stats_key(file_id, test_date)
        expected = f"test:{CacheKeyPrefix.FILE_STATS}:{file_id}:2024-01-01"
        assert key == expected

    def test_user_session_key(self):
        """사용자 세션 키 생성 테스트"""
        user_id = "192.168.1.1"
        key = self.key_manager.user_session_key(user_id)
        expected = f"test:{CacheKeyPrefix.USER_SESSION}:{user_id}"
        assert key == expected

    def test_user_activity_key(self):
        """사용자 활동 키 생성 테스트"""
        user_id = "192.168.1.1"
        test_date = date(2024, 1, 1)
        key = self.key_manager.user_activity_key(user_id, test_date)
        expected = f"test:{CacheKeyPrefix.USER_ACTIVITY}:{user_id}:2024-01-01"
        assert key == expected

    def test_stats_daily_key(self):
        """일별 통계 키 생성 테스트"""
        test_date = date(2024, 1, 1)
        key = self.key_manager.stats_daily_key(test_date)
        expected = f"test:{CacheKeyPrefix.STATS_DAILY}:2024-01-01"
        assert key == expected

    def test_stats_hourly_key(self):
        """시간별 통계 키 생성 테스트"""
        test_date = date(2024, 1, 1)
        hour = 14
        key = self.key_manager.stats_hourly_key(test_date, hour)
        expected = f"test:{CacheKeyPrefix.STATS_HOURLY}:2024-01-01:14"
        assert key == expected

    def test_stats_monthly_key(self):
        """월별 통계 키 생성 테스트"""
        year = 2024
        month = 1
        key = self.key_manager.stats_monthly_key(year, month)
        expected = f"test:{CacheKeyPrefix.STATS_MONTHLY}:2024:1"
        assert key == expected

    def test_system_settings_key(self):
        """시스템 설정 키 생성 테스트"""
        setting_key = "max_file_size"
        key = self.key_manager.system_settings_key(setting_key)
        expected = f"test:{CacheKeyPrefix.SYSTEM_SETTINGS}:{setting_key}"
        assert key == expected

    def test_rate_limit_key(self):
        """레이트 리미트 키 생성 테스트"""
        ip = "192.168.1.1"
        endpoint = "/upload"
        key = self.key_manager.rate_limit_key(ip, endpoint)
        expected = f"test:{CacheKeyPrefix.API_RATE_LIMIT}:{ip}:{endpoint}"
        assert key == expected

    def test_temp_upload_key(self):
        """임시 업로드 키 생성 테스트"""
        upload_id = "upload_123"
        key = self.key_manager.temp_upload_key(upload_id)
        expected = f"test:{CacheKeyPrefix.TEMP_UPLOAD}:{upload_id}"
        assert key == expected

    def test_temp_download_key(self):
        """임시 다운로드 키 생성 테스트"""
        token = "download_token_123"
        key = self.key_manager.temp_download_key(token)
        expected = f"test:{CacheKeyPrefix.TEMP_DOWNLOAD}:{token}"
        assert key == expected

    def test_search_index_key(self):
        """검색 인덱스 키 생성 테스트"""
        query = "test query"
        key = self.key_manager.search_index_key(query)
        # 해시가 포함되어야 함
        assert "test:search:index:" in key
        assert len(key.split(":")) == 4

    def test_search_results_key(self):
        """검색 결과 키 생성 테스트"""
        query = "test query"
        key = self.key_manager.search_results_key(query)
        # 해시가 포함되어야 함
        assert "test:search:results:" in key
        assert len(key.split(":")) == 4

    def test_get_pattern(self):
        """패턴 매칭 키 생성 테스트"""
        pattern = self.key_manager.get_pattern("file:meta", "user1")
        expected = "test:file:meta:user1:*"
        assert pattern == expected

    def test_long_key_handling(self):
        """긴 키 처리 테스트"""
        # 매우 긴 키 생성
        long_part = "a" * 1000
        key = self.key_manager._build_key("test", long_part)
        # 해시로 축약되어야 함
        assert "hash:" in key
        assert len(key) < 100


class TestCacheSerializer:
    """캐시 직렬화기 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.serializer = CacheSerializer()

    def test_serialize_file_metadata(self):
        """파일 메타데이터 직렬화 테스트"""
        file_meta = FileMetadata(
            file_id=str(uuid4()),
            filename="test.txt",
            file_size=1024,
            mime_type="text/plain",
            upload_time=datetime(2024, 1, 1, 12, 0, 0),
            uploader_ip="192.168.1.1",
            checksum="a" * 64,
        )

        json_str = self.serializer.serialize(file_meta)
        data = json.loads(json_str)

        assert data["filename"] == "test.txt"
        assert data["file_size"] == 1024
        assert data["mime_type"] == "text/plain"
        assert "2024-01-01T12:00:00" in data["upload_time"]

    def test_deserialize_file_metadata(self):
        """파일 메타데이터 역직렬화 테스트"""
        file_id = str(uuid4())
        json_str = json.dumps(
            {
                "file_id": file_id,
                "filename": "test.txt",
                "file_size": 1024,
                "mime_type": "text/plain",
                "upload_time": "2024-01-01T12:00:00",
                "uploader_ip": "192.168.1.1",
                "checksum": "a" * 64,
            }
        )

        file_meta = self.serializer.deserialize(json_str, FileMetadata)

        assert file_meta.file_id == file_id
        assert file_meta.filename == "test.txt"
        assert file_meta.file_size == 1024

    def test_serialize_user_session(self):
        """사용자 세션 직렬화 테스트"""
        session = UserSession(
            user_id="192.168.1.1",
            session_id="session_123",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            last_activity=datetime(2024, 1, 1, 12, 30, 0),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            upload_count=5,
            download_count=10,
        )

        json_str = self.serializer.serialize(session)
        data = json.loads(json_str)

        assert data["user_id"] == "192.168.1.1"
        assert data["session_id"] == "session_123"
        assert data["upload_count"] == 5
        assert data["download_count"] == 10

    def test_serialize_dict(self):
        """딕셔너리 직렬화 테스트"""
        data = {
            "key1": "value1",
            "key2": 123,
            "key3": {"nested": "value"},
            "key4": datetime(2024, 1, 1, 12, 0, 0),
        }

        json_str = self.serializer.serialize_dict(data)
        deserialized = self.serializer.deserialize_dict(json_str)

        assert deserialized["key1"] == "value1"
        assert deserialized["key2"] == 123
        assert deserialized["key3"]["nested"] == "value"

    def test_deserialize_dict(self):
        """딕셔너리 역직렬화 테스트"""
        json_str = '{"key1": "value1", "key2": 123}'
        data = self.serializer.deserialize_dict(json_str)

        assert data["key1"] == "value1"
        assert data["key2"] == 123


class TestCacheHelper:
    """캐시 헬퍼 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.key_manager = CacheKeyManager("test")
        self.serializer = CacheSerializer()
        self.helper = CacheHelper(self.key_manager, self.serializer)

    def test_get_file_meta_key(self):
        """파일 메타데이터 키 반환 테스트"""
        file_id = str(uuid4())
        key = self.helper.get_file_meta_key(file_id)
        expected = f"test:{CacheKeyPrefix.FILE_META}:{file_id}"
        assert key == expected

    def test_get_user_session_key(self):
        """사용자 세션 키 반환 테스트"""
        user_id = "192.168.1.1"
        key = self.helper.get_user_session_key(user_id)
        expected = f"test:{CacheKeyPrefix.USER_SESSION}:{user_id}"
        assert key == expected

    def test_get_stats_key(self):
        """통계 키 반환 테스트"""
        test_date = date(2024, 1, 1)
        key = self.helper.get_stats_key(test_date)
        expected = f"test:{CacheKeyPrefix.STATS_DAILY}:2024-01-01"
        assert key == expected

    def test_get_rate_limit_key(self):
        """레이트 리미트 키 반환 테스트"""
        ip = "192.168.1.1"
        endpoint = "/upload"
        key = self.helper.get_rate_limit_key(ip, endpoint)
        expected = f"test:{CacheKeyPrefix.API_RATE_LIMIT}:{ip}:{endpoint}"
        assert key == expected

    def test_get_ttl(self):
        """TTL 반환 테스트"""
        # 파일 메타데이터 TTL
        ttl = self.helper.get_ttl("file:meta")
        assert ttl == CacheTTL.FILE_META

        # 사용자 세션 TTL
        ttl = self.helper.get_ttl("user:session")
        assert ttl == CacheTTL.USER_SESSION

        # 알 수 없는 프리픽스
        ttl = self.helper.get_ttl("unknown:prefix")
        assert ttl == CacheTTL.TEMP_DATA

    def test_create_file_metadata(self):
        """파일 메타데이터 생성 테스트"""
        file_id = str(uuid4())
        file_meta = self.helper.create_file_metadata(
            file_id=file_id,
            filename="test.txt",
            file_size=1024,
            mime_type="text/plain",
            upload_time=datetime(2024, 1, 1, 12, 0, 0),
            uploader_ip="192.168.1.1",
            checksum="a" * 64,
        )

        assert isinstance(file_meta, FileMetadata)
        assert file_meta.file_id == file_id
        assert file_meta.filename == "test.txt"

    def test_create_user_session(self):
        """사용자 세션 생성 테스트"""
        session = self.helper.create_user_session(
            user_id="192.168.1.1",
            session_id="session_123",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            last_activity=datetime(2024, 1, 1, 12, 30, 0),
            ip_address="192.168.1.1",
        )

        assert isinstance(session, UserSession)
        assert session.user_id == "192.168.1.1"
        assert session.session_id == "session_123"

    def test_create_file_stats(self):
        """파일 통계 생성 테스트"""
        file_id = str(uuid4())
        stats = self.helper.create_file_stats(
            file_id=file_id, date=date(2024, 1, 1), download_count=10, upload_count=5
        )

        assert isinstance(stats, FileStats)
        assert stats.file_id == file_id
        assert stats.download_count == 10
        assert stats.upload_count == 5

    def test_create_system_settings(self):
        """시스템 설정 생성 테스트"""
        settings = self.helper.create_system_settings(
            key="max_file_size",
            value=10485760,
            description="최대 파일 크기 (바이트)",
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert isinstance(settings, SystemSettings)
        assert settings.key == "max_file_size"
        assert settings.value == 10485760

    def test_create_rate_limit_info(self):
        """레이트 리미트 정보 생성 테스트"""
        rate_limit = self.helper.create_rate_limit_info(
            ip_address="192.168.1.1",
            endpoint="/upload",
            request_count=5,
            window_start=datetime(2024, 1, 1, 12, 0, 0),
            limit=10,
            window_size=60,
        )

        assert isinstance(rate_limit, RateLimitInfo)
        assert rate_limit.ip_address == "192.168.1.1"
        assert rate_limit.endpoint == "/upload"
        assert rate_limit.request_count == 5

    def test_create_search_result(self):
        """검색 결과 생성 테스트"""
        search_result = self.helper.create_search_result(
            query="test query",
            results=[{"id": 1, "name": "test"}],
            total_count=1,
            search_time=0.1,
            cached_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert isinstance(search_result, SearchResult)
        assert search_result.query == "test query"
        assert search_result.total_count == 1
        assert search_result.search_time == 0.1


class TestGlobalFunctions:
    """전역 함수 테스트"""

    def test_get_cache_key_manager(self):
        """전역 키 관리자 반환 테스트"""
        key_manager = get_cache_key_manager()
        assert isinstance(key_manager, CacheKeyManager)

    def test_get_cache_serializer(self):
        """전역 직렬화기 반환 테스트"""
        serializer = get_cache_serializer()
        assert isinstance(serializer, CacheSerializer)

    def test_get_cache_helper(self):
        """전역 캐시 헬퍼 반환 테스트"""
        helper = get_cache_helper()
        assert isinstance(helper, CacheHelper)


class TestDataModels:
    """데이터 모델 테스트"""

    def test_file_metadata_validation(self):
        """파일 메타데이터 유효성 검사 테스트"""
        # 유효한 체크섬
        file_meta = FileMetadata(
            file_id=str(uuid4()),
            filename="test.txt",
            file_size=1024,
            mime_type="text/plain",
            upload_time=datetime(2024, 1, 1, 12, 0, 0),
            uploader_ip="192.168.1.1",
            checksum="a" * 64,
        )
        assert file_meta.checksum == "a" * 64

        # 잘못된 체크섬
        with pytest.raises(ValueError, match="체크섬은 SHA-256 형식이어야 합니다"):
            FileMetadata(
                file_id=str(uuid4()),
                filename="test.txt",
                file_size=1024,
                mime_type="text/plain",
                upload_time=datetime(2024, 1, 1, 12, 0, 0),
                uploader_ip="192.168.1.1",
                checksum="invalid",
            )

    def test_model_json_encoding(self):
        """모델 JSON 인코딩 테스트"""
        file_meta = FileMetadata(
            file_id=str(uuid4()),
            filename="test.txt",
            file_size=1024,
            mime_type="text/plain",
            upload_time=datetime(2024, 1, 1, 12, 0, 0),
            uploader_ip="192.168.1.1",
            checksum="a" * 64,
        )

        json_str = file_meta.json()
        data = json.loads(json_str)

        # UUID가 문자열로 변환되었는지 확인
        assert isinstance(data["file_id"], str)
        # datetime이 ISO 형식으로 변환되었는지 확인
        assert "2024-01-01T12:00:00" in data["upload_time"]


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v"])
