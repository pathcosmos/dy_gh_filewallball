"""
Environment-specific configuration classes.

This module provides configuration classes for different environments:
- DevelopmentConfig: Development environment settings
- TestingConfig: Testing environment settings
- ProductionConfig: Production environment settings
"""

from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    """Base configuration class with common settings."""

    model_config = {"extra": "ignore"}

    # Application settings
    app_name: str = "FileWallBall API"
    app_version: str = "1.0.0"
    environment: str = "development"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Database settings - External MariaDB
    db_host: str = Field(default="pathcosmos.iptime.org", env="DB_HOST")
    db_port: int = Field(default=33377, env="DB_PORT")
    db_name: str = Field(default="filewallball", env="DB_NAME")
    db_user: str = Field(default="filewallball", env="DB_USER")
    db_password: str = Field(default="jK9#zQ$p&2@f!L7^xY*", env="DB_PASSWORD")
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis settings - DISABLED
    # redis_host: str = "localhost"
    # redis_port: int = 6379
    # redis_password: str = ""
    # redis_db: int = 0
    # redis_pool_size: int = 20

    # File storage settings
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")
    allowed_extensions: List[str] = Field(
        default=[
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".mp4",
            ".mp3",
            ".zip",
            ".rar",
            ".7z",
        ],
        env="ALLOWED_EXTENSIONS",
    )

    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    # CORS settings
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")

    # Security settings
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Cache settings
    cache_ttl_file_metadata: int = Field(default=3600, env="CACHE_TTL_FILE_METADATA")
    cache_ttl_session: int = Field(default=86400, env="CACHE_TTL_SESSION")
    cache_ttl_temp: int = Field(default=600, env="CACHE_TTL_TEMP")

    # Performance settings
    upload_chunk_size: int = Field(default=8192, env="UPLOAD_CHUNK_SIZE")
    download_chunk_size: int = Field(default=8192, env="DOWNLOAD_CHUNK_SIZE")

    @validator("allowed_extensions", pre=True)
    def parse_allowed_extensions(cls, v):
        """Parse allowed_extensions string to list."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse cors_origins string to list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def database_url(self) -> str:
        """Generate MariaDB database URL from settings."""
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.db_password)
        return f"mysql+pymysql://{self.db_user}:{encoded_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    debug: bool = True
    environment: str = "development"

    # Development-specific settings
    log_level: str = "DEBUG"
    cors_origins: List[str] = ["*"]

    # Development secret key (change in production)
    secret_key: str = "dev-secret-key-change-in-production"


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    debug: bool = False
    environment: str = "testing"

    # Testing-specific settings
    log_level: str = "WARNING"

    # Test secret key
    secret_key: str = "test-secret-key"

    # Disable CORS for testing
    cors_origins: List[str] = []


class ProductionConfig(BaseConfig):
    """Production environment configuration."""

    debug: bool = False
    environment: str = "production"

    # Production-specific settings
    log_level: str = "WARNING"
    log_file: str = "/var/log/filewallball/app.log"

    # Production database settings (can be overridden by environment)
    # Uses default values from BaseConfig if not set

    # Production secret key (with fallback)
    secret_key: str = Field(default="prod-secret-key-change-in-production", env="SECRET_KEY")

    # Production CORS settings (with fallback)
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = True


def get_config() -> BaseConfig:
    """Get configuration based on environment."""
    environment = BaseConfig().environment

    if environment == "testing":
        return TestingConfig()
    elif environment == "production":
        return ProductionConfig()
    else:
        return DevelopmentConfig()


# Global settings instance
settings = get_config()
