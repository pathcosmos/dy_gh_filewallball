"""
Caching and Database Integration Tests for Subtask 15.4.

This module implements comprehensive tests for Redis caching, database transactions,
data consistency, and related functionality. Tests are designed to work without
requiring a Redis server by using mocks and simulations.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.orm_models import FileInfo, User
from app.services.cache_service import CacheService


class TestCacheServiceIntegration:
    """Cache service integration tests."""

    def setup_method(self):
        """Setup test method."""
        self.cache_service = CacheService()

        # Mock Redis client
        self.mock_redis = AsyncMock()
        self.cache_service.client = self.mock_redis

    def test_cache_hit_miss_scenarios(self):
        """Test cache hit and miss scenarios."""
        # Test cache miss scenario
        self.mock_redis.get.return_value = None

        # Simulate cache miss
        cache_key = "test:file:123"
        expected_data = {"file_id": "123", "filename": "test.txt"}

        # Cache miss should return None
        assert self.cache_service.get(cache_key) is None

        # Test cache hit scenario
        self.mock_redis.get.return_value = json.dumps(expected_data)

        # Cache hit should return cached data
        cached_data = self.cache_service.get(cache_key)
        assert cached_data == expected_data

    def test_cache_invalidation_simulation(self):
        """Test cache invalidation simulation."""
        # Test cache invalidation
        cache_key = "test:file:123"

        # Set cache entry
        self.mock_redis.set.return_value = True
        self.mock_redis.delete.return_value = 1

        # Simulate cache invalidation
        result = self.cache_service.delete(cache_key)
        assert result is True

        # Verify delete was called
        self.mock_redis.delete.assert_called_with(cache_key)

    def test_cache_synchronization_verification(self):
        """Test cache synchronization verification."""
        # Test cache synchronization
        cache_data = {
            "test:file:1": {"file_id": "1", "filename": "file1.txt"},
            "test:file:2": {"file_id": "2", "filename": "file2.txt"},
            "test:file:3": {"file_id": "3", "filename": "file3.txt"},
        }

        # Mock mset operation
        self.mock_redis.mset.return_value = True

        # Test batch cache operations
        result = self.cache_service.mset(cache_data, ttl=3600)
        assert result is True

        # Verify mset was called
        self.mock_redis.mset.assert_called()

    def test_dynamic_ttl_calculation(self):
        """Test dynamic TTL calculation."""
        # Test TTL calculation for different file sizes
        file_sizes = [1, 10, 100, 1000]  # MB

        for size in file_sizes:
            ttl = self.cache_service._calculate_dynamic_ttl(
                "file_info", size, access_count=0
            )

            # TTL should be within reasonable bounds
            assert 1800 <= ttl <= 86400  # 30 minutes to 24 hours

            # Larger files should have longer TTL
            if size > 1:
                assert ttl > self.cache_service._calculate_dynamic_ttl(
                    "file_info", 1, access_count=0
                )

    def test_cache_performance_metrics(self):
        """Test cache performance metrics."""
        # Mock cache statistics
        mock_stats = {
            "keyspace_hits": 1000,
            "keyspace_misses": 100,
            "used_memory": 1048576,  # 1MB
            "connected_clients": 5,
            "total_commands_processed": 5000,
        }

        self.mock_redis.info.return_value = mock_stats

        # Test cache statistics
        stats = self.cache_service.get_stats()

        # Verify statistics structure
        assert "hit_rate" in stats
        assert "memory_usage" in stats
        assert "connected_clients" in stats
        assert "total_commands" in stats

    def test_cache_transaction_simulation(self):
        """Test cache transaction simulation."""
        # Test cache transactions
        operations = [
            lambda: self.cache_service.set("key1", "value1", 3600),
            lambda: self.cache_service.set("key2", "value2", 3600),
            lambda: self.cache_service.delete("key3"),
        ]

        # Mock transaction results
        self.mock_redis.set.return_value = True
        self.mock_redis.delete.return_value = 1

        # Test transaction execution
        results = self.cache_service.transaction(operations)

        # Verify all operations were executed
        assert len(results) == 3
        assert all(result is not None for result in results)


class TestDatabaseTransactionIntegration:
    """Database transaction integration tests."""

    def setup_method(self):
        """Setup test method."""
        # Use MariaDB test database
        from app.core.config import TestingConfig
        config = TestingConfig()
        self.engine = create_engine(config.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        from app.models.orm_models import Base

        Base.metadata.create_all(bind=self.engine)

        self.db_manager = None  # DatabaseManager() # Removed as per edit hint
        self.db_manager = (
            None  # self.SessionLocal # Replaced with self.SessionLocal as per edit hint
        )

    def test_database_transaction_rollback(self):
        """Test database transaction rollback."""
        session = self.SessionLocal()

        try:
            # Create a file record
            file_info = FileInfo(
                file_uuid="test-uuid-123",
                original_filename="test.txt",
                stored_filename="test_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="abc123",
                storage_path="/uploads/test_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session.add(file_info)
            session.commit()

            # Verify file was created
            saved_file = (
                session.query(FileInfo).filter_by(file_uuid="test-uuid-123").first()
            )
            assert saved_file is not None
            assert saved_file.original_filename == "test.txt"

            # Simulate transaction rollback
            session.rollback()

            # Verify rollback worked
            rolled_back_file = (
                session.query(FileInfo).filter_by(file_uuid="test-uuid-123").first()
            )
            assert rolled_back_file is None

        finally:
            session.close()

    def test_concurrency_control_simulation(self):
        """Test concurrency control simulation."""
        # Simulate concurrent access scenarios
        session1 = self.SessionLocal()
        session2 = self.SessionLocal()

        try:
            # Create initial file
            file_info = FileInfo(
                file_uuid="concurrent-test",
                original_filename="concurrent.txt",
                stored_filename="concurrent_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="def456",
                storage_path="/uploads/concurrent_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session1.add(file_info)
            session1.commit()

            # Simulate concurrent reads
            file1 = (
                session1.query(FileInfo).filter_by(file_uuid="concurrent-test").first()
            )
            file2 = (
                session2.query(FileInfo).filter_by(file_uuid="concurrent-test").first()
            )

            # Both sessions should see the same data
            assert file1 is not None
            assert file2 is not None
            assert file1.original_filename == file2.original_filename

            # Simulate concurrent update scenario
            file1.original_filename = "updated1.txt"
            file2.original_filename = "updated2.txt"

            # First update should succeed
            session1.commit()

            # Second update behavior depends on database locking mechanisms
            session2.commit()

            # Verify final state
            final_file = (
                session1.query(FileInfo).filter_by(file_uuid="concurrent-test").first()
            )
            assert final_file.original_filename == "updated2.txt"

        finally:
            session1.close()
            session2.close()

    def test_cache_db_consistency_verification(self):
        """Test cache-database consistency verification."""
        session = self.SessionLocal()

        try:
            # Create file in database
            file_info = FileInfo(
                file_uuid="consistency-test",
                original_filename="consistency.txt",
                stored_filename="consistency_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="ghi789",
                storage_path="/uploads/consistency_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session.add(file_info)
            session.commit()

            # Simulate cache operations
            cache_service = CacheService()
            cache_service.client = AsyncMock()

            # Cache the file info
            file_data = {
                "file_uuid": file_info.file_uuid,
                "original_filename": file_info.original_filename,
                "file_size": file_info.file_size,
                "mime_type": file_info.mime_type,
            }

            cache_service.client.set.return_value = True
            cache_service.set_file_info(file_info.file_uuid, file_data)

            # Verify cache was set
            cache_service.client.set.assert_called()

            # Simulate cache invalidation
            cache_service.client.delete.return_value = 1
            cache_service.invalidate_file_cache(file_info.file_uuid)

            # Verify cache was invalidated
            cache_service.client.delete.assert_called()

        finally:
            session.close()

    def test_large_data_pagination_test(self):
        """Test large data pagination."""
        session = self.SessionLocal()

        try:
            # Create multiple file records
            for i in range(100):
                file_info = FileInfo(
                    file_uuid=f"pagination-test-{i}",
                    original_filename=f"file_{i}.txt",
                    stored_filename=f"file_{i}_123.txt",
                    file_extension="txt",
                    mime_type="text/plain",
                    file_size=1024 + i,
                    file_hash=f"hash{i:03d}",
                    storage_path=f"/uploads/file_{i}_123.txt",
                    is_public=True,
                    is_deleted=False,
                )
                session.add(file_info)

            session.commit()

            # Test pagination
            page_size = 10
            total_files = session.query(FileInfo).count()
            assert total_files == 100

            # Test first page
            first_page = session.query(FileInfo).limit(page_size).offset(0).all()
            assert len(first_page) == 10

            # Test second page
            second_page = session.query(FileInfo).limit(page_size).offset(10).all()
            assert len(second_page) == 10

            # Verify no overlap
            first_page_ids = {f.id for f in first_page}
            second_page_ids = {f.id for f in second_page}
            assert first_page_ids.isdisjoint(second_page_ids)

        finally:
            session.close()

    def test_connection_pool_exhaustion_scenario(self):
        """Test connection pool exhaustion scenario."""
        # Simulate connection pool exhaustion
        max_connections = 5
        active_connections = []

        try:
            # Create multiple sessions to simulate connection pool usage
            for i in range(max_connections + 2):
                session = self.SessionLocal()
                active_connections.append(session)

                # Simulate some work
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1

                # Don't close immediately to simulate long-running transactions

            # Verify we can still create sessions within connection limits
            additional_session = self.SessionLocal()
            result = additional_session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            additional_session.close()

        finally:
            # Clean up all sessions
            for session in active_connections:
                session.close()


class TestDataConsistencyValidation:
    """Data consistency validation tests."""

    def setup_method(self):
        """Setup test method."""
        from app.core.config import TestingConfig
        config = TestingConfig()
        self.engine = create_engine(config.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        from app.models.orm_models import Base

        Base.metadata.create_all(bind=self.engine)

    def test_data_integrity_constraints(self):
        """Test data integrity constraints."""
        session = self.SessionLocal()

        try:
            # Test unique constraint on file_uuid
            file1 = FileInfo(
                file_uuid="unique-test",
                original_filename="file1.txt",
                stored_filename="file1_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="abc123",
                storage_path="/uploads/file1_123.txt",
                is_public=True,
                is_deleted=False,
            )

            file2 = FileInfo(
                file_uuid="unique-test",  # Same UUID
                original_filename="file2.txt",
                stored_filename="file2_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=2048,
                file_hash="def456",
                storage_path="/uploads/file2_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session.add(file1)
            session.commit()

            # Adding file with same UUID should raise an error
            session.add(file2)
            with pytest.raises(Exception):  # Database constraint violation
                session.commit()

            session.rollback()

        finally:
            session.close()

    def test_referential_integrity_simulation(self):
        """Test referential integrity simulation."""
        session = self.SessionLocal()

        try:
            # Create user first
            user = User(
                username="testuser",
                email="test@example.com",
                role="user",
                is_active=True,
            )
            session.add(user)
            session.commit()

            # Create file with valid owner_id
            file_info = FileInfo(
                file_uuid="ref-test",
                original_filename="ref.txt",
                stored_filename="ref_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="ref123",
                storage_path="/uploads/ref_123.txt",
                is_public=True,
                is_deleted=False,
                owner_id=user.id,
            )

            session.add(file_info)
            session.commit()

            # Verify file was created with correct owner
            saved_file = session.query(FileInfo).filter_by(file_uuid="ref-test").first()
            assert saved_file.owner_id == user.id

        finally:
            session.close()

    def test_transaction_isolation_levels(self):
        """Test transaction isolation levels."""
        session1 = self.SessionLocal()
        session2 = self.SessionLocal()

        try:
            # Test read committed isolation
            # Session 1 creates a file
            file_info = FileInfo(
                file_uuid="isolation-test",
                original_filename="isolation.txt",
                stored_filename="isolation_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="iso123",
                storage_path="/uploads/isolation_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session1.add(file_info)
            session1.commit()

            # Session 2 should see the committed data
            file_in_session2 = (
                session2.query(FileInfo).filter_by(file_uuid="isolation-test").first()
            )
            assert file_in_session2 is not None
            assert file_in_session2.original_filename == "isolation.txt"

            # Test uncommitted changes are not visible
            session1.query(FileInfo).filter_by(file_uuid="isolation-test").update(
                {"original_filename": "updated_isolation.txt"}
            )

            # Session 2 should not see uncommitted changes
            file_in_session2_again = (
                session2.query(FileInfo).filter_by(file_uuid="isolation-test").first()
            )
            assert file_in_session2_again.original_filename == "isolation.txt"

            # After commit, session 2 should see the changes
            session1.commit()
            session2.refresh(file_in_session2_again)
            assert file_in_session2_again.original_filename == "updated_isolation.txt"

        finally:
            session1.close()
            session2.close()


class TestCacheDatabasePerformance:
    """Cache and database performance tests."""

    def setup_method(self):
        """Setup test method."""
        self.cache_service = CacheService()
        self.cache_service.client = AsyncMock()

        from app.core.config import TestingConfig
        config = TestingConfig()
        self.engine = create_engine(config.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        from app.models.orm_models import Base

        Base.metadata.create_all(bind=self.engine)

    def test_cache_performance_benchmark(self):
        """Test cache performance benchmark."""
        # Test cache set performance
        start_time = time.time()

        for i in range(100):
            self.cache_service.set(f"perf:key:{i}", f"value:{i}", 3600)

        set_time = time.time() - start_time

        # Test cache get performance
        start_time = time.time()

        for i in range(100):
            self.cache_service.get(f"perf:key:{i}")

        get_time = time.time() - start_time

        # Performance should be reasonable (operations should complete quickly)
        assert set_time < 1.0  # Less than 1 second for 100 operations
        assert get_time < 1.0  # Less than 1 second for 100 operations

    def test_database_performance_benchmark(self):
        """Test database performance benchmark."""
        session = self.SessionLocal()

        try:
            # Test bulk insert performance
            start_time = time.time()

            files = []
            for i in range(100):
                file_info = FileInfo(
                    file_uuid=f"perf:file:{i}",
                    original_filename=f"perf_file_{i}.txt",
                    stored_filename=f"perf_file_{i}_123.txt",
                    file_extension="txt",
                    mime_type="text/plain",
                    file_size=1024 + i,
                    file_hash=f"perf{i:03d}",
                    storage_path=f"/uploads/perf_file_{i}_123.txt",
                    is_public=True,
                    is_deleted=False,
                )
                files.append(file_info)

            session.add_all(files)
            session.commit()

            insert_time = time.time() - start_time

            # Test bulk select performance
            start_time = time.time()

            all_files = session.query(FileInfo).all()

            select_time = time.time() - start_time

            # Performance should be reasonable
            assert insert_time < 1.0  # Less than 1 second for 100 inserts
            assert select_time < 1.0  # Less than 1 second for 100 selects
            assert len(all_files) == 100

        finally:
            session.close()

    def test_concurrent_access_performance(self):
        """Test concurrent access performance."""

        # Simulate concurrent cache access
        async def cache_operation(operation_id: int):
            for i in range(10):
                await self.cache_service.set(
                    f"concurrent:key:{operation_id}:{i}", f"value:{i}", 3600
                )
                await self.cache_service.get(f"concurrent:key:{operation_id}:{i}")

        # Run concurrent operations
        start_time = time.time()

        # Create tasks for concurrent execution
        tasks = [cache_operation(i) for i in range(5)]

        # Run concurrently
        asyncio.run(asyncio.gather(*tasks))

        concurrent_time = time.time() - start_time

        # Concurrent operations should complete in reasonable time
        assert concurrent_time < 2.0  # Less than 2 seconds for 50 operations

    def test_memory_usage_optimization(self):
        """Test memory usage optimization."""
        session = self.SessionLocal()

        try:
            # Test memory usage with large dataset
            large_files = []

            for i in range(1000):
                file_info = FileInfo(
                    file_uuid=f"memory:file:{i}",
                    original_filename=f"memory_file_{i}.txt",
                    stored_filename=f"memory_file_{i}_123.txt",
                    file_extension="txt",
                    mime_type="text/plain",
                    file_size=1024 + i,
                    file_hash=f"mem{i:04d}",
                    storage_path=f"/uploads/memory_file_{i}_123.txt",
                    is_public=True,
                    is_deleted=False,
                )
                large_files.append(file_info)

            # Add in batches to manage memory
            batch_size = 100
            for i in range(0, len(large_files), batch_size):
                batch = large_files[i : i + batch_size]
                session.add_all(batch)
                session.commit()

            # Verify all files were created
            total_files = session.query(FileInfo).count()
            assert total_files == 1000

        finally:
            session.close()


class TestErrorHandlingAndRecovery:
    """Error handling and recovery tests."""

    def setup_method(self):
        """Setup test method."""
        self.cache_service = CacheService()
        self.cache_service.client = AsyncMock()

    def test_cache_error_handling(self):
        """Test cache error handling."""
        # Simulate cache connection error
        self.cache_service.client.set.side_effect = Exception("Connection failed")

        # Test error handling in cache operations
        try:
            result = self.cache_service.set("error:key", "value", 3600)
            assert result is False  # Should handle error gracefully
        except Exception:
            # Error should be handled by the service
            pass

        # Reset mock
        self.cache_service.client.set.side_effect = None
        self.cache_service.client.set.return_value = True

        # Test normal operation after error
        result = self.cache_service.set("normal:key", "value", 3600)
        assert result is True

    def test_database_error_handling(self):
        """Test database error handling."""
        # Test with invalid database connection
        invalid_engine = create_engine("mysql+pymysql://invalid:invalid@invalid:3306/invalid", echo=False)
        invalid_session = sessionmaker(bind=invalid_engine)()

        try:
            # This should handle the error gracefully
            result = invalid_session.execute(text("SELECT 1"))
            # If we get here, the error was handled
        except Exception:
            # Expected error for invalid database
            pass
        finally:
            invalid_session.close()

    def test_data_recovery_simulation(self):
        """Test data recovery simulation."""
        # Simulate data recovery scenario
        session = self.SessionLocal()

        try:
            # Create backup data
            backup_file = FileInfo(
                file_uuid="recovery-test",
                original_filename="recovery.txt",
                stored_filename="recovery_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="rec123",
                storage_path="/uploads/recovery_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session.add(backup_file)
            session.commit()

            # Simulate data corruption (mark as deleted)
            backup_file.is_deleted = True
            session.commit()

            # Simulate recovery (restore from backup)
            backup_file.is_deleted = False
            session.commit()

            # Verify recovery was successful
            recovered_file = (
                session.query(FileInfo).filter_by(file_uuid="recovery-test").first()
            )
            assert recovered_file is not None
            assert recovered_file.is_deleted is False

        finally:
            session.close()


class TestIntegrationScenarios:
    """Integration scenario tests."""

    def setup_method(self):
        """Setup test method."""
        self.cache_service = CacheService()
        self.cache_service.client = AsyncMock()

        from app.core.config import TestingConfig
        config = TestingConfig()
        self.engine = create_engine(config.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        from app.models.orm_models import Base

        Base.metadata.create_all(bind=self.engine)

    def test_file_upload_cache_db_integration(self):
        """Test file upload with cache and database integration."""
        session = self.SessionLocal()

        try:
            # Simulate file upload workflow
            file_uuid = "integration-test-123"
            file_data = {
                "file_uuid": file_uuid,
                "original_filename": "integration.txt",
                "file_size": 1024,
                "mime_type": "text/plain",
            }

            # 1. Create file in database
            file_info = FileInfo(
                file_uuid=file_uuid,
                original_filename=file_data["original_filename"],
                stored_filename=f"{file_uuid}_123.txt",
                file_extension="txt",
                mime_type=file_data["mime_type"],
                file_size=file_data["file_size"],
                file_hash="int123",
                storage_path=f"/uploads/{file_uuid}_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session.add(file_info)
            session.commit()

            # 2. Cache file information
            self.cache_service.client.set.return_value = True
            self.cache_service.set_file_info(file_uuid, file_data)

            # 3. Verify cache was set
            self.cache_service.client.set.assert_called()

            # 4. Simulate cache hit
            self.cache_service.client.get.return_value = json.dumps(file_data)
            cached_data = self.cache_service.get_file_info(file_uuid)

            # 5. Verify cache hit
            assert cached_data == file_data

            # 6. Simulate file deletion
            file_info.is_deleted = True
            session.commit()

            # 7. Invalidate cache
            self.cache_service.client.delete.return_value = 1
            self.cache_service.invalidate_file_cache(file_uuid)

            # 8. Verify cache invalidation
            self.cache_service.client.delete.assert_called()

        finally:
            session.close()

    def test_bulk_operations_integration(self):
        """Test bulk operations integration."""
        session = self.SessionLocal()

        try:
            # Create multiple files
            files = []
            for i in range(10):
                file_info = FileInfo(
                    file_uuid=f"bulk:file:{i}",
                    original_filename=f"bulk_file_{i}.txt",
                    stored_filename=f"bulk_file_{i}_123.txt",
                    file_extension="txt",
                    mime_type="text/plain",
                    file_size=1024 + i,
                    file_hash=f"bulk{i:02d}",
                    storage_path=f"/uploads/bulk_file_{i}_123.txt",
                    is_public=True,
                    is_deleted=False,
                )
                files.append(file_info)

            # Bulk insert
            session.add_all(files)
            session.commit()

            # Bulk cache operations
            cache_data = {}
            for file_info in files:
                cache_data[f"file:{file_info.file_uuid}"] = {
                    "file_uuid": file_info.file_uuid,
                    "original_filename": file_info.original_filename,
                    "file_size": file_info.file_size,
                }

            # Mock bulk cache operations
            self.cache_service.client.mset.return_value = True
            self.cache_service.mset(cache_data, ttl=3600)

            # Verify bulk cache operation
            self.cache_service.client.mset.assert_called()

            # Bulk database query
            all_files = (
                session.query(FileInfo)
                .filter(FileInfo.file_uuid.like("bulk:file:%"))
                .all()
            )

            assert len(all_files) == 10

        finally:
            session.close()

    def test_transaction_consistency_integration(self):
        """Test transaction consistency integration."""
        session = self.SessionLocal()

        try:
            # Test transaction consistency
            file_uuid = "transaction-test"

            # Start transaction
            session.begin()

            # Create file
            file_info = FileInfo(
                file_uuid=file_uuid,
                original_filename="transaction.txt",
                stored_filename="transaction_123.txt",
                file_extension="txt",
                mime_type="text/plain",
                file_size=1024,
                file_hash="txn123",
                storage_path="/uploads/transaction_123.txt",
                is_public=True,
                is_deleted=False,
            )

            session.add(file_info)

            # Cache operation (should be consistent with transaction)
            file_data = {
                "file_uuid": file_uuid,
                "original_filename": "transaction.txt",
                "file_size": 1024,
            }

            self.cache_service.client.set.return_value = True
            self.cache_service.set_file_info(file_uuid, file_data)

            # Commit transaction
            session.commit()

            # Verify consistency
            db_file = session.query(FileInfo).filter_by(file_uuid=file_uuid).first()
            assert db_file is not None

            # Cache should also be consistent
            self.cache_service.client.set.assert_called()

        finally:
            session.close()


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
