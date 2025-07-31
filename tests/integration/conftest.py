"""
Integration test configuration and fixtures.

This module provides comprehensive fixtures for testing the entire FileWallBall
system including database, Redis, file operations, authentication, and API
workflows.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import TestingConfig
from app.database import get_db
from app.main import app
from app.models.database import Base
from app.services.cache_service import CacheService
from app.services.file_service import FileService
from app.services.ip_auth_service import IPAuthService
from app.services.rbac_service import RBACService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> TestingConfig:
    """Get testing configuration with integration test settings."""
    config = TestingConfig()
    # Override database settings for testing
    config.db_name = ":memory:"
    config.redis_db = 1
    config.upload_dir = "/tmp/filewallball_test_uploads"
    config.max_file_size = 100 * 1024 * 1024  # 100MB for testing
    return config


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine with proper isolation."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db_session(test_db_engine):
    """Create test database session with transaction rollback."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest_asyncio.fixture
async def test_redis_client() -> AsyncGenerator[Redis, None]:
    """Create test Redis client with proper cleanup."""
    redis_client = Redis.from_url(
        "redis://localhost:6379/1", encoding="utf-8", decode_responses=True
    )

    try:
        # Clear test database
        await redis_client.flushdb()
        yield redis_client
    finally:
        # Clean up after tests
        await redis_client.flushdb()
        await redis_client.close()


@pytest.fixture
def test_client(
    test_db_session, test_redis_client
) -> Generator[TestClient, None, None]:
    """Create test client with dependency overrides."""

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_redis():
        return test_redis_client

    app.dependency_overrides[get_db] = override_get_db
    # Add Redis dependency override when implemented

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Create temporary upload directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        upload_dir = Path(temp_dir) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        yield upload_dir


@pytest.fixture
def sample_files() -> Dict[str, bytes]:
    """Generate sample files of different sizes and types for testing."""
    return {
        "small_text": b"This is a small text file for testing.\n" * 10,
        "medium_text": b"This is a medium text file for testing.\n" * 1000,
        "large_text": (b"This is a large text file for testing.\n" * 100000),
        "binary_data": (b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09" * 1000),
        "json_data": b'{"test": "data", "number": 42, "array": [1, 2, 3]}',
        "empty_file": b"",
    }


@pytest.fixture
def test_file_metadata() -> Dict[str, any]:
    """Generate test file metadata."""
    return {
        "filename": "test_file.txt",
        "content_type": "text/plain",
        "size": 1024,
        "hash": "sha256:test_hash_value",
        "uploaded_by": "test_user",
        "permissions": ["read", "write"],
        "tags": ["test", "integration"],
        "description": "Test file for integration testing",
    }


@pytest_asyncio.fixture
async def auth_service(test_db_session) -> IPAuthService:
    """Create authentication service for testing."""
    return IPAuthService(db_session=test_db_session)


@pytest_asyncio.fixture
async def file_service(test_db_session, test_redis_client) -> FileService:
    """Create file service for testing."""
    cache_service = CacheService(redis_client=test_redis_client)
    return FileService(
        db_session=test_db_session,
        cache_service=cache_service,
        upload_dir=Path("/tmp/test_uploads"),
    )


@pytest_asyncio.fixture
async def cache_service(test_redis_client) -> CacheService:
    """Create cache service for testing."""
    return CacheService(redis_client=test_redis_client)


@pytest.fixture
def mock_external_services():
    """Mock external services for integration testing."""
    # Mock file system operations
    mock_fs = MagicMock()
    mock_fs.exists.return_value = True
    mock_fs.mkdir.return_value = None
    mock_fs.rmtree.return_value = None

    # Mock network operations
    mock_network = AsyncMock()
    mock_network.get.return_value = MagicMock(status_code=200, content=b"test")

    # Mock system metrics
    mock_metrics = MagicMock()
    mock_metrics.cpu_percent.return_value = 25.0
    mock_metrics.memory_percent.return_value = 50.0
    mock_metrics.disk_usage.return_value = MagicMock(used=1024, total=2048)

    return {
        "filesystem": mock_fs,
        "network": mock_network,
        "metrics": mock_metrics,
    }


@pytest.fixture
def test_users() -> List[Dict[str, any]]:
    """Generate test users with different roles and permissions."""
    return [
        {
            "username": "admin_user",
            "email": "admin@test.com",
            "password": "admin_password_123",
            "role": "admin",
            "permissions": ["read", "write", "delete", "admin"],
            "ip_whitelist": ["127.0.0.1", "192.168.1.0/24"],
        },
        {
            "username": "regular_user",
            "email": "user@test.com",
            "password": "user_password_123",
            "role": "user",
            "permissions": ["read", "write"],
            "ip_whitelist": ["127.0.0.1"],
        },
        {
            "username": "readonly_user",
            "email": "readonly@test.com",
            "password": "readonly_password_123",
            "role": "readonly",
            "permissions": ["read"],
            "ip_whitelist": ["127.0.0.1"],
        },
    ]


@pytest.fixture
def test_tokens(test_users, auth_service) -> Dict[str, str]:
    """Generate test JWT tokens for different users."""
    tokens = {}
    for user in test_users:
        # This would be implemented based on your actual auth service
        token = f"test_token_{user['username']}"
        tokens[user["username"]] = token
    return tokens


@pytest.fixture(autouse=True)
def setup_test_environment(test_config, temp_upload_dir):
    """Setup test environment before each test."""
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["UPLOAD_DIR"] = str(temp_upload_dir)
    os.environ["DB_NAME"] = test_config.db_name
    os.environ["REDIS_DB"] = str(test_config.redis_db)

    # Create test directories
    temp_upload_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Cleanup after test
    if temp_upload_dir.exists():
        import shutil

        shutil.rmtree(temp_upload_dir, ignore_errors=True)


@pytest.fixture
def test_scenarios() -> Dict[str, Dict[str, any]]:
    """Define comprehensive test scenarios for integration testing."""
    return {
        "file_upload_workflow": {
            "description": "Complete file upload workflow",
            "steps": [
                "authenticate_user",
                "upload_file",
                "verify_metadata",
                "check_cache",
                "download_file",
                "verify_integrity",
            ],
            "expected_results": {
                "upload_success": True,
                "cache_hit": True,
                "download_success": True,
                "integrity_check": True,
            },
        },
        "concurrent_uploads": {
            "description": "Multiple concurrent file uploads",
            "concurrency": 10,
            "files_per_user": 5,
            "expected_results": {
                "all_uploads_successful": True,
                "no_data_corruption": True,
                "performance_within_limits": True,
            },
        },
        "error_scenarios": {
            "description": "Error handling and recovery",
            "scenarios": [
                "invalid_file_type",
                "file_too_large",
                "unauthorized_access",
                "database_connection_failure",
                "redis_connection_failure",
                "disk_space_full",
            ],
            "expected_results": {
                "proper_error_response": True,
                "graceful_degradation": True,
                "no_data_loss": True,
            },
        },
        "performance_scenarios": {
            "description": "Performance and load testing",
            "scenarios": [
                "large_file_upload",
                "many_small_files",
                "mixed_file_types",
                "high_concurrency",
                "cache_stress_test",
            ],
            "expected_results": {
                "response_time_acceptable": True,
                "memory_usage_stable": True,
                "throughput_meets_requirements": True,
            },
        },
    }


@pytest.fixture
def test_data_generators():
    """Provide data generators for creating test data."""

    def generate_file_content(size: int, content_type: str = "text/plain") -> bytes:
        """Generate file content of specified size."""
        if content_type.startswith("text/"):
            return b"Test content " * (size // 13 + 1)
        else:
            return bytes([i % 256 for i in range(size)])

    def generate_file_metadata(filename: str, size: int) -> Dict[str, any]:
        """Generate file metadata."""
        return {
            "filename": filename,
            "size": size,
            "content_type": "application/octet-stream",
            "uploaded_at": "2024-01-01T00:00:00Z",
            "uploaded_by": "test_user",
            "hash": f"sha256:test_hash_{filename}_{size}",
        }

    def generate_user_data(username: str, role: str = "user") -> Dict[str, any]:
        """Generate user data."""
        return {
            "username": username,
            "email": f"{username}@test.com",
            "role": role,
            "permissions": ["read", "write"] if role == "user" else ["read"],
            "created_at": "2024-01-01T00:00:00Z",
        }

    return {
        "file_content": generate_file_content,
        "file_metadata": generate_file_metadata,
        "user_data": generate_user_data,
    }


@pytest.fixture
def cleanup_utilities():
    """Provide utilities for cleaning up test data."""

    async def cleanup_files(file_ids: List[str], file_service: FileService):
        """Clean up test files."""
        for file_id in file_ids:
            try:
                await file_service.delete_file(file_id)
            except Exception:
                pass  # Ignore cleanup errors

    async def cleanup_cache(keys: List[str], cache_service: CacheService):
        """Clean up test cache entries."""
        for key in keys:
            try:
                await cache_service.delete(key)
            except Exception:
                pass  # Ignore cleanup errors

    async def cleanup_database(records: List[Dict], db_session):
        """Clean up test database records."""
        for record in records:
            try:
                db_session.delete(record)
                db_session.commit()
            except Exception:
                db_session.rollback()

    return {
        "cleanup_files": cleanup_files,
        "cleanup_cache": cleanup_cache,
        "cleanup_database": cleanup_database,
    }
