"""
Caching and Database Integration Tests for FileWallBall.

This module implements comprehensive integration tests for:
- Redis cache hit/miss scenarios
- Cache invalidation and synchronization
- Database transaction rollback tests
- Concurrency control and locking mechanisms
- Cache-DB consistency verification
- Large data pagination tests
- Connection pool exhaustion scenarios

These tests validate the data layer integrity and performance characteristics
of the FileWallBall system.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.orm_models import FileInfo
from app.services.cache_service import CacheService
from app.services.file_service import FileService


class TestCachingDatabaseIntegration:
    """Comprehensive caching and database integration tests."""

    @pytest_asyncio.fixture
    async def cache_service(self, test_redis_client) -> CacheService:
        """Create cache service for testing."""
        return CacheService(redis_client=test_redis_client)

    @pytest_asyncio.fixture
    async def file_service(self, test_db_session, test_redis_client) -> FileService:
        """Create file service for testing."""
        return FileService(db_session=test_db_session, redis_client=test_redis_client)

    @pytest.fixture
    def test_file_data(self) -> Dict[str, any]:
        """Generate test file data."""
        content = b"Test file content for caching and database integration tests"
        file_hash = hashlib.sha256(content).hexdigest()
        return {
            "content": content,
            "filename": "test_integration.txt",
            "file_hash": file_hash,
            "size": len(content),
            "mime_type": "text/plain",
        }

    # ==================== Redis Cache Hit/Miss Scenarios ====================

    @pytest.mark.asyncio
    async def test_cache_hit_scenario(
        self,
        cache_service: CacheService,
        file_service: FileService,
        test_file_data: Dict[str, any],
    ):
        """Test cache hit scenario - data retrieved from cache."""
        file_id = "test_cache_hit_001"
        cache_key = f"file:{file_id}"

        # First, set data in cache
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Verify cache hit
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is not None
        assert cached_data["filename"] == test_file_data["filename"]
        assert cached_data["file_hash"] == test_file_data["file_hash"]

        # Verify cache key exists
        exists = await cache_service.redis_client.exists(cache_key)
        assert exists == 1

    @pytest.mark.asyncio
    async def test_cache_miss_scenario(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache miss scenario - data not found in cache."""
        file_id = "test_cache_miss_001"

        # Try to get non-existent data from cache
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is None

        # Verify cache key doesn't exist
        cache_key = f"file:{file_id}"
        exists = await cache_service.redis_client.exists(cache_key)
        assert exists == 0

    @pytest.mark.asyncio
    async def test_cache_hit_miss_performance(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test performance difference between cache hit and miss."""
        file_id = "test_perf_001"

        # Measure cache miss time
        start_time = time.time()
        await cache_service.get_file_metadata(file_id)
        miss_time = time.time() - start_time

        # Set data in cache
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Measure cache hit time
        start_time = time.time()
        await cache_service.get_file_metadata(file_id)
        hit_time = time.time() - start_time

        # Cache hit should be significantly faster
        assert hit_time < miss_time
        assert hit_time < 0.01  # Should be very fast (< 10ms)

    # ==================== Cache Invalidation and Synchronization ====================

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache invalidation when file metadata is updated."""
        file_id = "test_invalidation_001"

        # Set initial data in cache
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Verify initial data exists
        initial_data = await cache_service.get_file_metadata(file_id)
        assert initial_data is not None

        # Update file data
        updated_data = test_file_data.copy()
        updated_data["filename"] = "updated_test_file.txt"
        updated_data["size"] = 999

        # Invalidate cache
        await cache_service.invalidate_file_metadata(file_id)

        # Verify cache is cleared
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is None

        # Set updated data
        await cache_service.set_file_metadata(file_id, updated_data)

        # Verify updated data is cached
        final_data = await cache_service.get_file_metadata(file_id)
        assert final_data["filename"] == "updated_test_file.txt"
        assert final_data["size"] == 999

    @pytest.mark.asyncio
    async def test_cache_synchronization_multiple_operations(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache synchronization across multiple operations."""
        file_id = "test_sync_001"

        # Perform multiple cache operations
        operations = []
        for i in range(5):
            data = test_file_data.copy()
            data["filename"] = f"sync_test_{i}.txt"
            data["size"] = 100 + i

            operations.append(cache_service.set_file_metadata(file_id, data))

        # Execute all operations concurrently
        await asyncio.gather(*operations)

        # Verify final state
        final_data = await cache_service.get_file_metadata(file_id)
        assert final_data["filename"] == "sync_test_4.txt"
        assert final_data["size"] == 104

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache TTL expiration functionality."""
        file_id = "test_ttl_001"

        # Set data with short TTL
        await cache_service.set_file_metadata(file_id, test_file_data, ttl=1)

        # Verify data exists immediately
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is not None

        # Wait for TTL expiration
        await asyncio.sleep(1.5)

        # Verify data is expired
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is None

    # ==================== Database Transaction Rollback Tests ====================

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

    # ==================== Concurrency Control and Locking Mechanisms ====================

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
    async def test_redis_distributed_lock(self, cache_service: CacheService):
        """Test Redis distributed locking mechanism."""
        lock_key = "test_distributed_lock"
        lock_value = "test_lock_value"

        # Acquire lock
        lock_acquired = await cache_service.redis_client.set(
            lock_key, lock_value, ex=10, nx=True
        )
        assert lock_acquired is True

        # Try to acquire same lock again (should fail)
        second_lock = await cache_service.redis_client.set(
            lock_key, "another_value", ex=10, nx=True
        )
        assert second_lock is None

        # Release lock
        await cache_service.redis_client.delete(lock_key)

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

    # ==================== Cache-DB Consistency Verification ====================

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

        # Verify consistency
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data["filename"] == "updated_consistency.txt"
        assert cached_data["size"] == 999

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

        # Verify all files are cached
        for file_id in file_ids:
            cached_data = await cache_service.get_file_metadata(file_id)
            assert cached_data is not None

    # ==================== Large Data Pagination Tests ====================

    @pytest.mark.asyncio
    async def test_large_data_pagination_performance(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test pagination performance with large datasets."""
        # Create large dataset
        file_records = []
        for i in range(1000):
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
        for i in range(100):
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
            "total": 100,
            "page": 1,
            "size": 10,
        }

        await cache_service.redis_client.set(page_key, json.dumps(page_data), ex=300)

        # Verify cached pagination data
        cached_page = await cache_service.redis_client.get(page_key)
        assert cached_page is not None

        page_info = json.loads(cached_page)
        assert page_info["total"] == 100
        assert len(page_info["files"]) == 10

    # ==================== Connection Pool Exhaustion Scenarios ====================

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
        operations = [db_operation(i) for i in range(20)]
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Most operations should succeed
        successful_results = [
            r for r in results if isinstance(r, str) and r.startswith("success")
        ]
        assert len(successful_results) >= 15  # At least 75% success rate

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
        operations = [redis_operation(i) for i in range(50)]
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Most operations should succeed
        successful_results = [
            r for r in results if isinstance(r, str) and r.startswith("success")
        ]
        assert len(successful_results) >= 40  # At least 80% success rate

    # ==================== Performance and Stress Tests ====================

    @pytest.mark.asyncio
    async def test_cache_performance_under_load(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache performance under high load."""
        num_operations = 1000
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

        # Should handle at least 100 operations per second
        assert operations_per_second >= 100
        assert total_time < 10  # Should complete within 10 seconds

    @pytest.mark.asyncio
    async def test_database_performance_under_load(
        self, test_db_session: Session, test_file_data: Dict[str, any]
    ):
        """Test database performance under high load."""
        num_records = 500
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

        # Should handle at least 50 records per second
        assert records_per_second >= 50
        assert total_time < 10  # Should complete within 10 seconds

    # ==================== Error Recovery and Resilience Tests ====================

    @pytest.mark.asyncio
    async def test_cache_recovery_after_failure(
        self, cache_service: CacheService, test_file_data: Dict[str, any]
    ):
        """Test cache recovery after temporary failure."""
        file_id = "test_recovery_001"

        # Set initial data
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Simulate cache failure (delete key)
        await cache_service.redis_client.delete(f"file:{file_id}")

        # Try to get data (should return None)
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is None

        # Recover by setting data again
        await cache_service.set_file_metadata(file_id, test_file_data)

        # Verify recovery
        recovered_data = await cache_service.get_file_metadata(file_id)
        assert recovered_data is not None
        assert recovered_data["filename"] == test_file_data["filename"]

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
        cached_data = await cache_service.get_file_metadata(file_id)

        assert db_file is not None
        assert cached_data is not None
        assert db_file.original_filename == cached_data["filename"]
        assert db_file.file_hash == cached_data["file_hash"]

        # 4. Update operation
        db_file.original_filename = "updated_comprehensive.txt"
        test_db_session.commit()

        # 5. Cache invalidation
        await cache_service.invalidate_file_metadata(file_id)

        # 6. Verify cache miss
        cached_data = await cache_service.get_file_metadata(file_id)
        assert cached_data is None

        # 7. Cache refresh
        updated_data = {
            "filename": db_file.original_filename,
            "file_hash": db_file.file_hash,
            "size": db_file.file_size,
            "mime_type": db_file.mime_type,
        }
        await cache_service.set_file_metadata(file_id, updated_data)

        # 8. Final consistency check
        final_cached_data = await cache_service.get_file_metadata(file_id)
        assert final_cached_data["filename"] == "updated_comprehensive.txt"

        # 9. Cleanup
        test_db_session.delete(db_file)
        test_db_session.commit()
        await cache_service.invalidate_file_metadata(file_id)

        # 10. Verify cleanup
        db_file = test_db_session.query(FileInfo).filter_by(file_id=file_id).first()
        cached_data = await cache_service.get_file_metadata(file_id)
        assert db_file is None
        assert cached_data is None
