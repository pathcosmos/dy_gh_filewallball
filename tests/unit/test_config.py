"""
Unit tests for configuration management.

Tests for environment-specific configuration loading and validation.
"""

import os
from unittest.mock import patch

import pytest

from app.core.config import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_config,
)


class TestBaseConfig:
    """Test base configuration functionality."""

    def test_base_config_defaults(self):
        """Test base configuration default values."""
        config = BaseConfig()

        assert config.app_name == "FileWallBall API"
        assert config.app_version == "1.0.0"
        assert config.environment == "development"
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False

    def test_database_url_generation_mariadb(self):
        """Test MariaDB database URL generation."""
        config = BaseConfig()
        config.db_host = "localhost"
        config.db_port = 3306
        config.db_name = "test_db"
        config.db_user = "test_user"
        config.db_password = "test_pass"

        url = config.database_url
        assert "mysql+pymysql://test_user:test_pass@localhost:3306/test_db" == url

    def test_database_url_generation_mysql(self):
        """Test MySQL database URL generation."""
        config = BaseConfig()
        config.db_host = "localhost"
        config.db_port = 3306
        config.db_name = "test_db"
        config.db_user = "test_user"
        config.db_password = "test_pass"

        url = config.database_url
        expected = "mysql+pymysql://test_user:test_pass@localhost:3306/test_db"
        assert url == expected

    def test_redis_url_generation(self):
        """Test Redis URL generation."""
        config = BaseConfig()
        config.redis_host = "localhost"
        config.redis_port = 6379
        config.redis_db = 0

        url = config.redis_url
        assert url == "redis://localhost:6379/0"

    def test_redis_url_generation_with_password(self):
        """Test Redis URL generation with password."""
        config = BaseConfig()
        config.redis_host = "localhost"
        config.redis_port = 6379
        config.redis_db = 0
        config.redis_password = "redis_pass"

        url = config.redis_url
        assert url == "redis://:redis_pass@localhost:6379/0"

    def test_allowed_extensions_parsing(self):
        """Test allowed extensions string parsing."""
        config = BaseConfig()
        config.allowed_extensions = ".txt,.pdf,.jpg"

        assert ".txt" in config.allowed_extensions
        assert ".pdf" in config.allowed_extensions
        assert ".jpg" in config.allowed_extensions

    def test_cors_origins_parsing(self):
        """Test CORS origins string parsing."""
        config = BaseConfig()
        config.cors_origins = "http://localhost:3000,https://example.com"

        assert "http://localhost:3000" in config.cors_origins
        assert "https://example.com" in config.cors_origins


class TestDevelopmentConfig:
    """Test development configuration."""

    def test_development_config_defaults(self):
        """Test development configuration default values."""
        config = DevelopmentConfig()

        assert config.environment == "development"
        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.db_name == "filewallball_dev.db"
        assert config.secret_key == "dev-secret-key-change-in-production"

    def test_development_config_database_url(self):
        """Test development configuration database URL."""
        config = DevelopmentConfig()

        url = config.database_url
        assert "mysql+pymysql://" in url
        assert "filewallball_dev" in url


class TestTestingConfig:
    """Test testing configuration."""

    def test_testing_config_defaults(self):
        """Test testing configuration default values."""
        config = TestingConfig()

        assert config.environment == "testing"
        assert config.debug is False
        assert config.log_level == "WARNING"
        assert config.db_name == ":memory:"
        assert config.redis_db == 1
        assert config.secret_key == "test-secret-key"
        assert config.cors_origins == []

    def test_testing_config_database_url(self):
        """Test testing configuration database URL."""
        config = TestingConfig()

        url = config.database_url
        assert "mysql+pymysql://" in url
        assert "test_filewallball" in url


class TestProductionConfig:
    """Test production configuration."""

    @patch.dict(
        os.environ,
        {
            "DB_HOST": "prod-db.example.com",
            "DB_NAME": "filewallball_prod",
            "DB_USER": "prod_user",
            "DB_PASSWORD": "prod_password",
            "REDIS_HOST": "prod-redis.example.com",
            "REDIS_PASSWORD": "redis_password",
            "SECRET_KEY": "prod-secret-key",
            "CORS_ORIGINS": "https://example.com,https://api.example.com",
        },
    )
    def test_production_config_required_vars(self):
        """Test production configuration with required environment variables."""
        config = ProductionConfig()

        assert config.environment == "production"
        assert config.debug is False
        assert config.log_level == "WARNING"
        assert config.db_host == "prod-db.example.com"
        assert config.db_name == "filewallball_prod"
        assert config.db_user == "prod_user"
        assert config.db_password == "prod_password"
        assert config.redis_host == "prod-redis.example.com"
        assert config.redis_password == "redis_password"
        assert config.secret_key == "prod-secret-key"
        assert "https://example.com" in config.cors_origins
        assert "https://api.example.com" in config.cors_origins

    def test_production_config_missing_required_vars(self):
        """Test production configuration with missing required variables."""
        # Clear environment variables
        for var in [
            "DB_HOST",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "REDIS_HOST",
            "REDIS_PASSWORD",
            "SECRET_KEY",
            "CORS_ORIGINS",
        ]:
            if var in os.environ:
                del os.environ[var]

        with pytest.raises(Exception):
            ProductionConfig()


class TestGetConfig:
    """Test configuration factory function."""

    def test_get_config_development(self):
        """Test get_config returns development config by default."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = get_config()
            assert isinstance(config, DevelopmentConfig)

    def test_get_config_testing(self):
        """Test get_config returns testing config."""
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            config = get_config()
            assert isinstance(config, TestingConfig)

    def test_get_config_production(self):
        """Test get_config returns production config."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "DB_HOST": "prod-db.example.com",
                "DB_NAME": "filewallball_prod",
                "DB_USER": "prod_user",
                "DB_PASSWORD": "prod_password",
                "REDIS_HOST": "prod-redis.example.com",
                "REDIS_PASSWORD": "redis_password",
                "SECRET_KEY": "prod-secret-key",
                "CORS_ORIGINS": "https://example.com",
            },
        ):
            config = get_config()
            assert isinstance(config, ProductionConfig)
