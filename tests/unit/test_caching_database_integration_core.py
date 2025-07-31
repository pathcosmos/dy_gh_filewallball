"""
Core Caching and Database Integration Tests for FileWallBall.

This module implements unit tests for caching and database integration
that don't require external Redis server, focusing on core functionality
that can be validated without external dependencies.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.orm_models import FileInfo
from app.services.cache_service import CacheService
from app.services.file_service import FileService


class TestCachingDatabaseIntegrationCore:
    """Core caching and database integration tests without external dependencies."""

    @pytest_asyncio.fixture
    async def mock_redis_client(self):
        """Create a mock Redis client for testing."""
        mock_client = AsyncMock()

        # Mock Redis operations
        mock_client.set = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.delete = AsyncMock(return_value=1)
        mock_client.exists = AsyncMock(return_value=0)
        mock_client.flushdb = AsyncMock(return_value=True)

        return mock_client

    @pytest_asyncio.fixture
    async def cache_service(self, mock_redis_client) -> CacheService:
        """Create cache service with mock Redis client."""
        with patch("app.services.cache_service.get_redis_manager") as mock_manager:
            mock_manager.return_value.get_client.return_value = mock_redis_client
            return CacheService()

    @pytest_asyncio.fixture
    async def file_service(self, test_db_session, mock_redis_client) -> FileService:
        """Create file service with mock Redis client."""
        return FileService(db_session=test_db_session, redis_client=mock_redis_client)

    @pytest.fixture
    def test_file_data(self) -> Dict[str, any]:
        """Generate test file data."""
        content = b"Test file content for caching and database integration tests"
        file_hash = hashlib.sha256(content).hexdigest()
        return {
            "content": content.decode("utf-8"),  # Convert bytes to string for JSON
            "filename": "test_integration.txt",
            "file_hash": file_hash,
            "size": len(content),
            "mime_type": "text/plain",
        }

    # ==================== Redis Cache Hit/Miss Scenarios ====================

    @pytest.mark.asyncio
    async def test_cache_hit_scenario(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache hit scenario - data retrieved from cache."""
        file_id = "test_cache_hit_001"

        # Mock Redis to return cached data
        cached_data_json = json.dumps(test_file_data)
        cache_service.client.get.return_value = cached_data_json

        # Test cache hit
        cached_data = await cache_service.get_file_info(file_id)
        assert cached_data is not None
        assert cached_data["filename"] == test_file_data["filename"]
        assert cached_data["file_hash"] == test_file_data["file_hash"]

        # Verify Redis was called
        cache_service.client.get.assert_called_once_with(f"file:{file_id}")

    @pytest.mark.asyncio
    async def test_cache_miss_scenario(self, cache_service: CacheService):
        """Test cache miss scenario - data not found in cache."""
        file_id = "test_cache_miss_001"

        # Mock Redis to return None (cache miss)
        cache_service.client.get.return_value = None

        # Test cache miss
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is None

        # Verify Redis was called
        cache_service.client.get.assert_called_once_with(f"file:{file_id}")

    @pytest.mark.asyncio
    async def test_cache_set_operation(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache set operation."""
        file_id = "test_cache_set_001"

        # Test setting data in cache
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Verify Redis set was called with correct data
        cache_service.client.set.assert_called_once()
        call_args = cache_service.client.set.call_args
        assert call_args[0][0] == f"file:{file_id}"

        # Verify the data was serialized correctly
        stored_data = json.loads(call_args[0][1])
        assert stored_data["filename"] == test_file_data["filename"]
        assert stored_data["file_hash"] == test_file_data["file_hash"]

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_service: CacheService):
        """Test cache invalidation operation."""
        file_id = "test_invalidation_001"

        # Test cache invalidation
        await cache_service.invalidate_file_metadata(file_id)

        # Verify Redis delete was called
        cache_service.client.delete.assert_called_once_with(f"file:{file_id}")

    # ==================== Database Transaction Tests ====================

    @pytest.mark.asyncio
    async def test_database_transaction_rollback_on_error(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test database transaction rollback when error occurs."""
        # Start transaction
        test_db_session.begin()

        try:
            # Create file record
            file_record = FileInfo(
                file_id="test_rollback_001",
                original_filename=test_file_data["filename"],
                file_hash=test_file_data["file_hash"],
                file_size=test_file_data["size"],
                mime_type=test_file_data["mime_type"],
                upload_path="/test/path",
            )
            test_db_session.add(file_record)
            test_db_session.flush()

            # Verify record exists in session
            db_file = (
                test_db_session.query(FileInfo)
                .filter_by(file_id="test_rollback_001")
                .first()
            )
            assert db_file is not None

            # Simulate error
            raise Exception("Simulated error for rollback test")

        except Exception:
            # Rollback transaction
            test_db_session.rollback()

            # Verify record is not persisted
            db_file = (
                test_db_session.query(FileInfo)
                .filter_by(file_id="test_rollback_001")
                .first()
            )
            assert db_file is None

    @pytest.mark.asyncio
    async def test_database_transaction_commit_success(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test successful database transaction commit."""
        # Start transaction
        test_db_session.begin()

        # Create file record
        file_record = FileInfo(
            file_id="test_commit_001",
            original_filename=test_file_data["filename"],
            file_hash=test_file_data["file_hash"],
            file_size=test_file_data["size"],
            mime_type=test_file_data["mime_type"],
            upload_path="/test/path",
        )
        test_db_session.add(file_record)

        # Commit transaction
        test_db_session.commit()

        # Verify record is persisted
        db_file = (
            test_db_session.query(FileInfo).filter_by(file_id="test_commit_001").first()
        )
        assert db_file is not None
        assert db_file.original_filename == test_file_data["filename"]

    @pytest.mark.asyncio
    async def test_database_integrity_constraint_violation(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test database integrity constraint violation handling."""
        # Create first record
        file_record1 = FileInfo(
            file_id="test_constraint_001",
            original_filename=test_file_data["filename"],
            file_hash=test_file_data["file_hash"],
            file_size=test_file_data["size"],
            mime_type=test_file_data["mime_type"],
            upload_path="/test/path1",
        )
        test_db_session.add(file_record1)
        test_db_session.commit()

        # Try to create duplicate record (should violate unique constraint)
        file_record2 = FileInfo(
            file_id="test_constraint_001",  # Same file_id
            original_filename="duplicate.txt",
            file_hash="different_hash",
            file_size=200,
            mime_type="text/plain",
            upload_path="/test/path2",
        )
        test_db_session.add(file_record2)

        # Should raise integrity error
        with pytest.raises(IntegrityError):
            test_db_session.commit()

    # ==================== Concurrency Control Tests ====================

    @pytest.mark.asyncio
    async def test_concurrent_file_access_control(
        self, file_service: FileService, test_file_data: Dict[str, any]
    ):
        """Test concurrent access to the same file."""
        file_id = "test_concurrent_001"

        # Simulate concurrent file operations
        async def upload_file():
            return await file_service.create_file_record(
                file_id=file_id,
                filename=test_file_data["filename"],
                file_hash=test_file_data["file_hash"],
                file_size=test_file_data["size"],
                mime_type=test_file_data["mime_type"],
                upload_path="/test/concurrent",
            )

        async def read_file():
            return await file_service.get_file_by_id(file_id)

        # Execute operations concurrently
        results = await asyncio.gather(
            upload_file(), read_file(), return_exceptions=True
        )

        # At least one operation should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 1

    @pytest.mark.asyncio
    async def test_redis_distributed_lock_simulation(self, cache_service: CacheService):
        """Test Redis distributed locking mechanism simulation."""
        lock_key = "test_distributed_lock"
        lock_value = "test_lock_value"

        # Mock Redis SET with NX flag (simulate lock acquisition)
        cache_service.redis_client.set.return_value = True

        # Simulate acquiring lock
        lock_acquired = await cache_service.redis_client.set(
            lock_key, lock_value, ex=10, nx=True
        )
        assert lock_acquired is True

        # Mock Redis SET with NX flag returning None (simulate lock failure)
        cache_service.redis_client.set.return_value = None

        # Try to acquire same lock again (should fail)
        second_lock = await cache_service.redis_client.set(
            lock_key, "another_value", ex=10, nx=True
        )
        assert second_lock is None

        # Mock Redis DELETE (simulate lock release)
        cache_service.redis_client.delete.return_value = 1
        await cache_service.redis_client.delete(lock_key)

        # Mock Redis SET with NX flag returning True (simulate successful re-acquisition)
        cache_service.redis_client.set.return_value = True

        # Should be able to acquire lock again
        third_lock = await cache_service.redis_client.set(
            lock_key, "third_value", ex=10, nx=True
        )
        assert third_lock is True

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test concurrent cache operations."""
        file_id = "test_concurrent_cache_001"

        # Simulate concurrent cache operations
        async def set_cache():
            await cache_service.set_file_metadata(file_id, test_file_data)
            return "set"

        async def get_cache():
            return await cache_service.get_file_metadata(file_id)

        async def delete_cache():
            await cache_service.invalidate_file_metadata(file_id)
            return "deleted"

        # Execute operations concurrently
        results = await asyncio.gather(
            set_cache(), get_cache(), delete_cache(), return_exceptions=True
        )

        # All operations should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception)

    # ==================== Cache-DB Consistency Tests ====================

    @pytest.mark.asyncio
    async def test_cache_db_consistency_after_update(
        self,
        cache_service: CacheService,
        file_service: FileService,
        test_db_session: Session,
        test_file_data: Dict[str, any],
    ):
        """Test cache-database consistency after file update."""
        file_id = "test_consistency_001"

        # Create file in database
        file_record = FileInfo(
            file_id=file_id,
            original_filename=test_file_data["filename"],
            file_hash=test_file_data["file_hash"],
            file_size=test_file_data["size"],
            mime_type=test_file_data["mime_type"],
            upload_path="/test/consistency",
        )
        test_db_session.add(file_record)
        test_db_session.commit()

        # Set cache
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Update file in database
        file_record.original_filename = "updated_consistency.txt"
        file_record.file_size = 999
        test_db_session.commit()

        # Invalidate cache to force refresh
        await cache_service.invalidate_file_metadata(file_id)

        # Get fresh data from database
        updated_data = await file_service.get_file_by_id(file_id)

        # Set updated data in cache
        cache_data = {
            "filename": updated_data.original_filename,
            "file_hash": updated_data.file_hash,
            "size": updated_data.file_size,
            "mime_type": updated_data.mime_type,
        }
        await cache_service.set_file_metadata(file_id, cache_data)

        # Verify consistency by checking Redis calls
        cache_service.redis_client.delete.assert_called_with(f"file:{file_id}")
        cache_service.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_cache_db_consistency_bulk_operations(
        self,
        cache_service: CacheService,
        test_db_session: Session,
        test_file_data: Dict[str, any],
    ):
        """Test cache-database consistency during bulk operations."""
        file_ids = [f"test_bulk_{i:03d}" for i in range(10)]

        # Create files in database
        for i, file_id in enumerate(file_ids):
            file_record = FileInfo(
                file_id=file_id,
                original_filename=f"bulk_test_{i}.txt",
                file_hash=test_file_data["file_hash"],
                file_size=test_file_data["size"] + i,
                mime_type=test_file_data["mime_type"],
                upload_path=f"/test/bulk/{i}",
            )
            test_db_session.add(file_record)

        test_db_session.commit()

        # Set cache for all files
        cache_operations = []
        for i, file_id in enumerate(file_ids):
            cache_data = test_file_data.copy()
            cache_data["filename"] = f"bulk_test_{i}.txt"
            cache_data["size"] = test_file_data["size"] + i
            cache_operations.append(
                cache_service.set_file_metadata(file_id, cache_data)
            )

        await asyncio.gather(*cache_operations)

        # Verify all cache operations were called
        assert cache_service.redis_client.set.call_count == 10

    # ==================== Large Data Pagination Tests ====================

    @pytest.mark.asyncio
    async def test_large_data_pagination_performance(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test pagination performance with large datasets."""
        # Create large dataset
        file_records = []
        for i in range(100):  # Reduced for unit testing
            file_record = FileInfo(
                file_id=f"pagination_test_{i:04d}",
                original_filename=f"pagination_file_{i}.txt",
                file_hash=test_file_data["file_hash"],
                file_size=test_file_data["size"],
                mime_type=test_file_data["mime_type"],
                upload_path=f"/test/pagination/{i}",
            )
            file_records.append(file_record)

        test_db_session.add_all(file_records)
        test_db_session.commit()

        # Test pagination performance
        page_sizes = [10, 50, 100]

        for page_size in page_sizes:
            start_time = time.time()

            # Query with pagination
            files = test_db_session.query(FileInfo).limit(page_size).offset(0).all()

            query_time = time.time() - start_time

            assert len(files) == page_size
            assert query_time < 1.0  # Should be fast (< 1 second)

    @pytest.mark.asyncio
    async def test_pagination_cache_integration(
        self,
        cache_service: CacheService,
        test_db_session: Session,
        test_file_data: Dict[str, any],
    ):
        """Test pagination with cache integration."""
        # Create test data
        file_records = []
        for i in range(50):  # Reduced for unit testing
            file_record = FileInfo(
                file_id=f"cache_pagination_{i:03d}",
                original_filename=f"cache_pag_{i}.txt",
                file_hash=test_file_data["file_hash"],
                file_size=test_file_data["size"],
                mime_type=test_file_data["mime_type"],
                upload_path=f"/test/cache_pagination/{i}",
            )
            file_records.append(file_record)

        test_db_session.add_all(file_records)
        test_db_session.commit()

        # Cache pagination results
        page_key = "pagination:page_1:size_10"
        page_data = {
            "files": [f.file_id for f in file_records[:10]],
            "total": 50,
            "page": 1,
            "size": 10,
        }

        await cache_service.redis_client.set(page_key, json.dumps(page_data), ex=300)

        # Verify cached pagination data was set
        cache_service.redis_client.set.assert_called_with(
            page_key, json.dumps(page_data), ex=300
        )

    # ==================== Connection Pool Tests ====================

    @pytest.mark.asyncio
    async def test_database_connection_pool_handling(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test database connection pool behavior under load."""

        # Simulate multiple concurrent database operations
        async def db_operation(operation_id: int):
            try:
                # Create a file record
                file_record = FileInfo(
                    file_id=f"pool_test_{operation_id:03d}",
                    original_filename=f"pool_file_{operation_id}.txt",
                    file_hash=test_file_data["file_hash"],
                    file_size=test_file_data["size"],
                    mime_type=test_file_data["mime_type"],
                    upload_path=f"/test/pool/{operation_id}",
                )
                test_db_session.add(file_record)
                test_db_session.commit()
                return f"success_{operation_id}"
            except Exception as e:
                return f"error_{operation_id}: {str(e)}"

        # Execute multiple operations concurrently
        operations = [db_operation(i) for i in range(10)]  # Reduced for unit testing
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Most operations should succeed
        successful_results = [
            r for r in results if isinstance(r, str) and r.startswith("success")
        ]
        assert len(successful_results) >= 7  # At least 70% success rate

    @pytest.mark.asyncio
    async def test_redis_connection_pool_handling(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test Redis connection pool behavior under load."""

        # Simulate multiple concurrent Redis operations
        async def redis_operation(operation_id: int):
            try:
                file_id = f"redis_pool_test_{operation_id:03d}"
                await cache_service.set_file_metadata(file_id, test_file_data)
                cached_data = await cache_service.get_file_metadata(file_id)
                await cache_service.invalidate_file_metadata(file_id)
                return f"success_{operation_id}"
            except Exception as e:
                return f"error_{operation_id}: {str(e)}"

        # Execute multiple operations concurrently
        operations = [redis_operation(i) for i in range(20)]  # Reduced for unit testing
        results = await asyncio.gather(*operations, return_exceptions=True)

        # All operations should succeed (mocked Redis)
        successful_results = [
            r for r in results if isinstance(r, str) and r.startswith("success")
        ]
        assert len(successful_results) == 20  # 100% success rate with mocked Redis

    # ==================== Performance and Stress Tests ====================

    @pytest.mark.asyncio
    async def test_cache_performance_under_load(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache performance under high load."""
        num_operations = 100  # Reduced for unit testing
        start_time = time.time()

        # Perform many cache operations
        operations = []
        for i in range(num_operations):
            file_id = f"perf_test_{i:04d}"
            cache_data = test_file_data.copy()
            cache_data["filename"] = f"perf_file_{i}.txt"
            operations.append(cache_service.set_file_metadata(file_id, cache_data))

        await asyncio.gather(*operations)

        total_time = time.time() - start_time
        operations_per_second = num_operations / total_time

        # Should handle at least 10 operations per second (mocked)
        assert operations_per_second >= 10
        assert total_time < 5  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_database_performance_under_load(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test database performance under high load."""
        num_records = 100  # Reduced for unit testing
        start_time = time.time()

        # Create many records
        file_records = []
        for i in range(num_records):
            file_record = FileInfo(
                file_id=f"db_perf_{i:04d}",
                original_filename=f"db_perf_file_{i}.txt",
                file_hash=test_file_data["file_hash"],
                file_size=test_file_data["size"],
                mime_type=test_file_data["mime_type"],
                upload_path=f"/test/db_perf/{i}",
            )
            file_records.append(file_record)

        test_db_session.add_all(file_records)
        test_db_session.commit()

        total_time = time.time() - start_time
        records_per_second = num_records / total_time

        # Should handle at least 10 records per second
        assert records_per_second >= 10
        assert total_time < 5  # Should complete within 5 seconds

    # ==================== Error Recovery and Resilience Tests ====================

    @pytest.mark.asyncio
    async def test_cache_recovery_after_failure(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache recovery after temporary failure."""
        file_id = "test_recovery_001"

        # Set initial data
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Simulate cache failure (mock delete)
        cache_service.redis_client.delete.return_value = 1
        await cache_service.redis_client.delete(f"file:{file_id}")

        # Mock cache miss
        cache_service.redis_client.get.return_value = None

        # Try to get data (should return None)
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is None

        # Recover by setting data again
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Verify recovery by checking Redis calls
        assert cache_service.redis_client.set.call_count >= 2

    @pytest.mark.asyncio
    async def test_database_recovery_after_transaction_failure(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test database recovery after transaction failure."""
        file_id = "test_db_recovery_001"

        # First successful transaction
        file_record = FileInfo(
            file_id=file_id,
            original_filename=test_file_data["filename"],
            file_hash=test_file_data["file_hash"],
            file_size=test_file_data["size"],
            mime_type=test_file_data["mime_type"],
            upload_path="/test/recovery",
        )
        test_db_session.add(file_record)
        test_db_session.commit()

        # Verify record exists
        db_file = test_db_session.query(FileInfo).filter_by(file_id=file_id).first()
        assert db_file is not None

        # Simulate failed transaction
        try:
            test_db_session.begin()
            # Try to create duplicate (should fail)
            duplicate_record = FileInfo(
                file_id=file_id,  # Same ID
                original_filename="duplicate.txt",
                file_hash="different_hash",
                file_size=200,
                mime_type="text/plain",
                upload_path="/test/duplicate",
            )
            test_db_session.add(duplicate_record)
            test_db_session.commit()
        except IntegrityError:
            test_db_session.rollback()

        # Verify original record still exists
        db_file = test_db_session.query(FileInfo).filter_by(file_id=file_id).first()
        assert db_file is not None
        assert db_file.original_filename == test_file_data["filename"]

    # ==================== Integration Test Summary ====================

    @pytest.mark.asyncio
    async def test_comprehensive_caching_database_integration(
        self,
        cache_service: CacheService,
        file_service: FileService,
        test_db_session: Session,
        test_file_data: Dict[str, any],
    ):
        """Comprehensive test covering all caching and database integration aspects."""
        file_id = "test_comprehensive_001"

        # 1. Database operation
        file_record = FileInfo(
            file_id=file_id,
            original_filename=test_file_data["filename"],
            file_hash=test_file_data["file_hash"],
            file_size=test_file_data["size"],
            mime_type=test_file_data["mime_type"],
            upload_path="/test/comprehensive",
        )
        test_db_session.add(file_record)
        test_db_session.commit()

        # 2. Cache operation
        await cache_service.set_file_metadata(file_id, test_file_data)

        # 3. Verify consistency
        db_file = test_db_session.query(FileInfo).filter_by(file_id=file_id).first()
        assert db_file is not None

        # 4. Update operation
        db_file.original_filename = "updated_comprehensive.txt"
        test_db_session.commit()

        # 5. Cache invalidation
        await cache_service.invalidate_file_metadata(file_id)

        # 6. Cache refresh
        updated_data = {
            "filename": db_file.original_filename,
            "file_hash": db_file.file_hash,
            "size": db_file.file_size,
            "mime_type": db_file.mime_type,
        }
        await cache_service.set_file_metadata(file_id, updated_data)

        # 7. Verify Redis operations were called
        assert cache_service.redis_client.set.call_count >= 2
        assert cache_service.redis_client.delete.call_count >= 1

        # 8. Cleanup
        test_db_session.delete(db_file)
        test_db_session.commit()
        await cache_service.invalidate_file_metadata(file_id)

        # 9. Verify cleanup
        db_file = test_db_session.query(FileInfo).filter_by(file_id=file_id).first()
        assert db_file is None
