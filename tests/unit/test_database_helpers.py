"""
Database Helpers Unit Tests
데이터베이스 헬퍼 함수들의 단위 테스트
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.orm_models import FileInfo, FileTag, FileTagRelation
from app.utils.database_helpers import (
    DatabaseHelpers,
    calculate_file_hash,
    format_file_size,
    generate_file_uuid,
)


class TestDatabaseHelpers:
    """DatabaseHelpers 클래스 테스트"""

    @pytest.fixture
    def db_session(self):
        """테스트용 데이터베이스 세션 모킹"""
        return Mock(spec=Session)

    @pytest.fixture
    def helpers(self, db_session):
        """DatabaseHelpers 인스턴스"""
        return DatabaseHelpers(db_session)

    def test_generate_file_uuid(self):
        """UUID 생성 테스트"""
        uuid1 = generate_file_uuid()
        uuid2 = generate_file_uuid()

        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # UUID v4 길이

    def test_calculate_file_hash(self):
        """파일 해시 계산 테스트"""
        content = b"test file content"
        hash1 = calculate_file_hash(content)
        hash2 = calculate_file_hash(content)

        assert isinstance(hash1, str)
        assert hash1 == hash2  # 같은 내용은 같은 해시
        assert len(hash1) == 64  # SHA-256 길이

    def test_format_file_size(self):
        """파일 크기 포맷팅 테스트"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1048576) == "1.0 MB"
        assert format_file_size(1073741824) == "1.0 GB"
        assert format_file_size(512) == "512.0 B"

    def test_create_file_with_metadata_success(self, helpers, db_session):
        """파일 생성 성공 테스트"""
        file_data = {
            "original_filename": "test.txt",
            "stored_filename": "test_uuid.txt",
            "file_extension": "txt",
            "mime_type": "text/plain",
            "file_size": 1024,
            "storage_path": "/storage/test.txt",
        }
        tags = ["test", "document"]

        # 모킹 설정
        mock_file = Mock(spec=FileInfo)
        mock_file.id = 1
        db_session.add.return_value = None
        db_session.flush.return_value = None
        db_session.commit.return_value = None

        with patch.object(helpers, "add_tags_to_file", return_value=True):
            result = helpers.create_file_with_metadata(file_data, tags)

        assert result is not None
        assert "file_uuid" in file_data
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()

    def test_create_file_with_metadata_failure(self, helpers, db_session):
        """파일 생성 실패 테스트"""
        file_data = {"invalid": "data"}

        db_session.add.side_effect = Exception("Database error")
        db_session.rollback.return_value = None

        result = helpers.create_file_with_metadata(file_data)

        assert result is None
        db_session.rollback.assert_called_once()

    def test_find_file_by_hash_success(self, helpers, db_session):
        """해시로 파일 검색 성공 테스트"""
        file_hash = "test_hash"
        mock_file = Mock(spec=FileInfo)

        db_session.query.return_value.filter.return_value.first.return_value = mock_file

        result = helpers.find_file_by_hash(file_hash)

        assert result == mock_file
        db_session.query.assert_called_once_with(FileInfo)

    def test_find_file_by_hash_not_found(self, helpers, db_session):
        """해시로 파일 검색 실패 테스트"""
        file_hash = "nonexistent_hash"

        db_session.query.return_value.filter.return_value.first.return_value = None

        result = helpers.find_file_by_hash(file_hash)

        assert result is None

    def test_search_files_basic(self, helpers, db_session):
        """기본 파일 검색 테스트"""
        mock_files = [Mock(spec=FileInfo), Mock(spec=FileInfo)]

        db_session.query.return_value.filter.return_value.count.return_value = 2
        db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_files
        )

        files, total = helpers.search_files(query="test")

        assert len(files) == 2
        assert total == 2

    def test_add_tags_to_file_success(self, helpers, db_session):
        """태그 추가 성공 테스트"""
        file_id = 1
        tag_names = ["tag1", "tag2"]

        # 모킹 설정
        mock_tag = Mock(spec=FileTag)
        mock_tag.id = 1
        db_session.query.return_value.filter.return_value.first.return_value = mock_tag
        db_session.flush.return_value = None
        db_session.commit.return_value = None

        result = helpers.add_tags_to_file(file_id, tag_names)

        assert result is True
        db_session.commit.assert_called_once()

    def test_remove_tags_from_file_success(self, helpers, db_session):
        """태그 제거 성공 테스트"""
        file_id = 1
        tag_names = ["tag1"]

        # 모킹 설정
        mock_tag = Mock(spec=FileTag)
        mock_tag.id = 1
        mock_relation = Mock(spec=FileTagRelation)

        db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_tag,
            mock_relation,
        ]
        db_session.delete.return_value = None
        db_session.commit.return_value = None

        result = helpers.remove_tags_from_file(file_id, tag_names)

        assert result is True
        db_session.delete.assert_called_once_with(mock_relation)
        db_session.commit.assert_called_once()

    def test_get_file_statistics(self, helpers, db_session):
        """파일 통계 조회 테스트"""
        # 모킹 설정
        db_session.query.return_value.filter.return_value.scalar.side_effect = [
            10,
            1024000,
        ]  # 파일 수, 총 크기
        db_session.query.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.all.return_value = (
            []
        )
        db_session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )
        db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        stats = helpers.get_file_statistics()

        assert "total_files" in stats
        assert "total_size" in stats
        assert "category_stats" in stats
        assert "extension_stats" in stats
        assert "recent_uploads" in stats

    def test_get_upload_trends(self, helpers, db_session):
        """업로드 트렌드 조회 테스트"""
        # 모킹 설정
        mock_result = [(datetime.now().date(), 5, 1024000)]
        db_session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = (
            mock_result
        )

        trends = helpers.get_upload_trends(days=7)

        assert len(trends) == 1
        assert "date" in trends[0]
        assert "upload_count" in trends[0]
        assert "total_size" in trends[0]

    def test_bulk_insert_files_success(self, helpers, db_session):
        """대량 파일 삽입 성공 테스트"""
        files_data = [
            {
                "original_filename": "test1.txt",
                "stored_filename": "test1_uuid.txt",
                "file_extension": "txt",
                "mime_type": "text/plain",
                "file_size": 1024,
                "storage_path": "/storage/test1.txt",
            },
            {
                "original_filename": "test2.txt",
                "stored_filename": "test2_uuid.txt",
                "file_extension": "txt",
                "mime_type": "text/plain",
                "file_size": 2048,
                "storage_path": "/storage/test2.txt",
            },
        ]

        db_session.add.return_value = None
        db_session.commit.return_value = None

        success_count, error_count = helpers.bulk_insert_files(files_data)

        assert success_count == 2
        assert error_count == 0
        assert db_session.add.call_count == 2
        db_session.commit.assert_called_once()

    def test_get_system_setting(self, helpers, db_session):
        """시스템 설정 조회 테스트"""
        key = "test_setting"
        default_value = "default"

        # 설정이 없는 경우
        db_session.query.return_value.filter.return_value.first.return_value = None

        result = helpers.get_system_setting(key, default_value)

        assert result == default_value

    def test_set_system_setting_new(self, helpers, db_session):
        """새 시스템 설정 저장 테스트"""
        key = "new_setting"
        value = "test_value"

        # 기존 설정이 없는 경우
        db_session.query.return_value.filter.return_value.first.return_value = None
        db_session.add.return_value = None
        db_session.commit.return_value = None

        result = helpers.set_system_setting(key, value)

        assert result is True
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()

    def test_cleanup_old_logs(self, helpers, db_session):
        """오래된 로그 정리 테스트"""
        db_session.query.return_value.filter.return_value.delete.return_value = 5
        db_session.commit.return_value = None

        deleted_count = helpers.cleanup_old_logs(days=90)

        assert deleted_count == 15  # 3개 테이블 * 5개씩
        assert db_session.query.call_count == 3
        db_session.commit.assert_called_once()

    def test_transaction_context_manager(self, helpers, db_session):
        """트랜잭션 컨텍스트 매니저 테스트"""
        db_session.commit.return_value = None

        with helpers.transaction() as session:
            assert session == db_session

        db_session.commit.assert_called_once()

    def test_transaction_context_manager_with_exception(self, helpers, db_session):
        """트랜잭션 컨텍스트 매니저 예외 처리 테스트"""
        db_session.rollback.return_value = None

        with pytest.raises(Exception):
            with helpers.transaction() as session:
                raise Exception("Test error")

        db_session.rollback.assert_called_once()


class TestDatabaseHelpersIntegration:
    """통합 테스트 (실제 데이터베이스 연결 필요)"""

    @pytest.mark.integration
    def test_file_lifecycle(self):
        """파일 생명주기 통합 테스트"""
        # 이 테스트는 실제 데이터베이스 연결이 필요합니다
        # CI/CD 환경에서만 실행됩니다
        pass

    @pytest.mark.integration
    def test_concurrent_tag_operations(self):
        """동시 태그 작업 테스트"""
        # 동시성 테스트는 실제 데이터베이스에서만 가능합니다
        pass
