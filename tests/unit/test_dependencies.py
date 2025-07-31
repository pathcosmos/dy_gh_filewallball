#!/usr/bin/env python3
"""
Dependency injection system tests.

This module tests the dependency injection system including:
- Settings dependency
- Database dependency
- Redis dependency (async and sync)
"""

from unittest.mock import MagicMock, patch

import pytest

from app.dependencies.database import get_db
from app.dependencies.redis import get_redis_client, get_redis_sync
from app.dependencies.settings import get_app_settings


class TestSettingsDependency:
    """Test settings dependency injection."""

    def test_get_app_settings(self):
        """Test that app settings are properly loaded."""
        settings = get_app_settings()

        assert settings is not None
        assert hasattr(settings, "app_name")
        assert hasattr(settings, "app_version")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")


class TestDatabaseDependency:
    """Test database dependency injection."""

    @patch("app.dependencies.database.SessionLocal")
    def test_get_db(self, mock_session_local):
        """Test database session creation."""
        # Mock the session
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        # Get database session
        db_gen = get_db()
        db = next(db_gen)

        assert db == mock_session

        # Test session cleanup
        db.close()
        mock_session.close.assert_called_once()


class TestRedisDependency:
    """Test Redis dependency injection."""

    @pytest.mark.asyncio
    @patch("app.dependencies.redis.get_async_redis_client")
    async def test_get_redis_client(self, mock_get_redis):
        """Test async Redis client dependency."""
        # Mock the Redis client
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Get Redis client
        redis_gen = get_redis_client()
        redis_client = await anext(redis_gen)

        assert redis_client == mock_redis

    @patch("app.dependencies.redis.get_sync_redis_client")
    def test_get_redis_sync(self, mock_get_redis):
        """Test sync Redis client dependency."""
        # Mock the Redis client
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Get Redis client
        redis_client = get_redis_sync()

        assert redis_client == mock_redis


class TestDependencyIntegration:
    """Test dependency integration scenarios."""

    @patch("app.dependencies.database.SessionLocal")
    @patch("app.dependencies.redis.get_async_redis_client")
    @pytest.mark.asyncio
    async def test_dependencies_work_together(self, mock_get_redis, mock_session_local):
        """Test that all dependencies can be used together."""
        # Mock dependencies
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Test all dependencies
        settings = get_app_settings()
        assert settings is not None

        db_gen = get_db()
        db = next(db_gen)
        assert db == mock_session

        redis_gen = get_redis_client()
        redis_client = await anext(redis_gen)
        assert redis_client == mock_redis

        # Cleanup
        db.close()
        mock_session.close.assert_called_once()


class TestDependencyErrorHandling:
    """Test dependency error handling."""

    @patch("app.dependencies.settings.Settings")
    def test_settings_dependency_error(self, mock_settings):
        """Test settings dependency error handling."""
        mock_settings.side_effect = Exception("Settings error")

        with pytest.raises(Exception):
            get_app_settings()

    @patch("app.dependencies.database.SessionLocal")
    def test_database_dependency_error(self, mock_session_local):
        """Test database dependency error handling."""
        mock_session_local.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            db_gen = get_db()
            next(db_gen)

    @patch("app.dependencies.redis.get_async_redis_client")
    @pytest.mark.asyncio
    async def test_redis_dependency_error(self, mock_get_redis):
        """Test Redis dependency error handling."""
        mock_get_redis.side_effect = Exception("Redis error")

        with pytest.raises(Exception):
            redis_gen = get_redis_client()
            await anext(redis_gen)


if __name__ == "__main__":
    pytest.main([__file__])
