"""
Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import TestingConfig
from app.main import app
from app.models.database import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> TestingConfig:
    """Get testing configuration."""
    return TestingConfig()


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db_session(test_db_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create test client for FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Create temporary upload directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        upload_dir = Path(temp_dir) / "uploads"
        upload_dir.mkdir()
        yield upload_dir


@pytest.fixture
def mock_redis():
    """Mock Redis client for tests."""

    # This would be replaced with actual Redis mock implementation
    # For now, return a simple mock object
    class MockRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, ex=None):
            self.data[key] = value
            return True

        def delete(self, key):
            if key in self.data:
                del self.data[key]
                return 1
            return 0

        def exists(self, key):
            return key in self.data

        def flushdb(self):
            self.data.clear()
            return True

    return MockRedis()


@pytest.fixture
def sample_file_content() -> bytes:
    """Sample file content for testing."""
    return b"This is a test file content for testing file upload functionality."


@pytest.fixture
def sample_file_metadata() -> dict:
    """Sample file metadata for testing."""
    return {
        "filename": "test_file.txt",
        "content_type": "text/plain",
        "size": 47,
        "checksum": "test_checksum_123",
        "uploaded_by": "test_user",
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Set test environment
    os.environ["ENVIRONMENT"] = "testing"

    # Clear any existing environment variables that might interfere
    for var in ["DATABASE_URL", "REDIS_URL", "SECRET_KEY"]:
        if var in os.environ:
            del os.environ[var]

    yield

    # Cleanup after test
    pass


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from unittest.mock import Mock

    settings = Mock()
    settings.upload_dir = "/tmp/test_uploads"
    settings.max_file_size = 1024 * 1024  # 1MB
    settings.allowed_extensions = [".txt", ".pdf", ".jpg"]
    settings.secret_key = "test-secret-key"
    settings.debug = True

    return settings
