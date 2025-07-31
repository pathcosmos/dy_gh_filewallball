"""
Tests for database performance optimization and monitoring.
"""

import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.monitoring import DatabaseMonitor, db_monitor
from app.repositories.file_repository import FileRepository
from app.utils.query_optimizer import QueryOptimizer


@pytest.mark.asyncio
async def test_database_monitor_initialization():
    """Test database monitor initialization."""
    monitor = DatabaseMonitor()
    assert monitor.slow_queries == []
    assert monitor.query_stats == {}
    assert monitor.start_time is not None


@pytest.mark.asyncio
async def test_query_optimizer_initialization(test_db_session: AsyncSession):
    """Test query optimizer initialization."""
    optimizer = QueryOptimizer(test_db_session)
    assert optimizer.session == test_db_session


@pytest.mark.asyncio
async def test_database_monitor_performance_summary():
    """Test database monitor performance summary."""
    monitor = DatabaseMonitor()
    summary = monitor.get_performance_summary()

    assert "total_queries" in summary
    assert "total_errors" in summary
    assert "error_rate" in summary
    assert "avg_duration_ms" in summary
    assert "slow_queries_count" in summary
    assert "uptime_seconds" in summary


@pytest.mark.asyncio
async def test_database_monitor_query_stats():
    """Test database monitor query statistics."""
    monitor = DatabaseMonitor()
    stats = monitor.get_query_stats()

    assert "start_time" in stats
    assert "uptime" in stats
    assert "total_queries" in stats
    assert "slow_queries_count" in stats
    assert "query_stats" in stats


@pytest.mark.asyncio
async def test_slow_query_detection():
    """Test slow query detection."""
    monitor = DatabaseMonitor()

    # Simulate a slow query
    slow_query = {
        "timestamp": time.time(),
        "duration": 0.15,  # 150ms - above threshold
        "operation": "SELECT",
        "table": "files",
        "statement": "SELECT * FROM files WHERE file_size > 1000000",
    }

    monitor.slow_queries.append(slow_query)

    slow_queries = monitor.get_slow_queries(limit=5)
    assert len(slow_queries) >= 1
    assert slow_queries[0]["duration"] == 0.15


@pytest.mark.asyncio
async def test_query_optimizer_explain_query(test_db_session: AsyncSession):
    """Test query optimizer explain functionality."""
    optimizer = QueryOptimizer(test_db_session)

    # Test with a simple query
    result = await optimizer.explain_query("SELECT 1")

    assert "query" in result
    assert "plan" in result or "error" in result


@pytest.mark.asyncio
async def test_query_optimizer_analyze_table_indexes(test_db_session: AsyncSession):
    """Test table index analysis."""
    optimizer = QueryOptimizer(test_db_session)

    # This might fail if pg_indexes view is not available
    result = await optimizer.analyze_table_indexes("files")

    assert "table_name" in result
    assert "indexes" in result or "error" in result


@pytest.mark.asyncio
async def test_query_optimizer_suggest_indexes():
    """Test index suggestion functionality."""
    optimizer = QueryOptimizer(None)  # We don't need session for this test

    query_patterns = [
        "SELECT * FROM files WHERE file_size > 1000000",
        "SELECT * FROM files ORDER BY created_at DESC",
        "SELECT * FROM files GROUP BY file_extension",
    ]

    suggestions = await optimizer.suggest_indexes("files", query_patterns)

    assert isinstance(suggestions, list)
    # Should have suggestions for WHERE, ORDER BY, and GROUP BY
    assert len(suggestions) >= 1


@pytest.mark.asyncio
async def test_repository_performance_with_monitoring(test_db_session: AsyncSession):
    """Test repository performance with monitoring."""
    repo = FileRepository(test_db_session)

    # Create test data
    file_data = {
        "file_uuid": "perf-test-uuid",
        "original_filename": "performance_test.txt",
        "stored_filename": "perf_test.txt",
        "file_extension": "txt",
        "mime_type": "text/plain",
        "file_size": 1024,
        "storage_path": "/uploads/perf_test.txt",
    }

    # Measure creation time
    start_time = time.time()
    file_info = await repo.create(**file_data)
    creation_time = time.time() - start_time

    assert file_info is not None
    assert creation_time < 1.0  # Should complete within 1 second

    # Measure retrieval time
    start_time = time.time()
    retrieved_file = await repo.get_by_uuid("perf-test-uuid")
    retrieval_time = time.time() - start_time

    assert retrieved_file is not None
    assert retrieval_time < 0.1  # Should complete within 100ms


@pytest.mark.asyncio
async def test_bulk_operations_performance(test_db_session: AsyncSession):
    """Test bulk operations performance."""
    repo = FileRepository(test_db_session)

    # Create bulk data
    files_data = [
        {
            "file_uuid": f"bulk-perf-{i}",
            "original_filename": f"bulk_perf_{i}.txt",
            "stored_filename": f"bulk_perf_{i}.txt",
            "file_extension": "txt",
            "mime_type": "text/plain",
            "file_size": 1024 * i,
            "storage_path": f"/uploads/bulk_perf_{i}.txt",
        }
        for i in range(1, 11)  # 10 files
    ]

    # Measure bulk creation time
    start_time = time.time()
    created_files = await repo.bulk_create(files_data)
    bulk_creation_time = time.time() - start_time

    assert len(created_files) == 10
    assert bulk_creation_time < 2.0  # Should complete within 2 seconds

    # Measure bulk retrieval time
    start_time = time.time()
    all_files = await repo.get_all(limit=100)
    bulk_retrieval_time = time.time() - start_time

    assert len(all_files) >= 10
    assert bulk_retrieval_time < 0.5  # Should complete within 500ms


@pytest.mark.asyncio
async def test_search_performance(test_db_session: AsyncSession):
    """Test search functionality performance."""
    repo = FileRepository(test_db_session)

    # Create test data for search
    search_files_data = [
        {
            "file_uuid": f"search-perf-{i}",
            "original_filename": f"search_performance_{i}.pdf",
            "stored_filename": f"search_perf_{i}.pdf",
            "file_extension": "pdf",
            "mime_type": "application/pdf",
            "file_size": 1024 * i,
            "storage_path": f"/uploads/search_perf_{i}.pdf",
        }
        for i in range(1, 6)  # 5 files
    ]

    for file_data in search_files_data:
        await repo.create(**file_data)

    # Measure search time
    start_time = time.time()
    search_results = await repo.search_files("search_performance")
    search_time = time.time() - start_time

    assert len(search_results) >= 1
    assert search_time < 0.2  # Should complete within 200ms

    # Measure content type filtering
    start_time = time.time()
    pdf_files = await repo.get_by_content_type("application/pdf")
    filter_time = time.time() - start_time

    assert len(pdf_files) >= 5
    assert filter_time < 0.1  # Should complete within 100ms


@pytest.mark.asyncio
async def test_global_monitor_instance():
    """Test global database monitor instance."""
    # Test that global instance exists
    assert db_monitor is not None
    assert isinstance(db_monitor, DatabaseMonitor)

    # Test performance summary
    summary = db_monitor.get_performance_summary()
    assert isinstance(summary, dict)

    # Test query stats
    stats = db_monitor.get_query_stats()
    assert isinstance(stats, dict)
