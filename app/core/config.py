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

    # Database settings - MariaDB Container
    db_host: str = "mariadb-service"
    db_port: int = 3306
    db_name: str = "filewallball_db"
    db_user: str = "filewallball_user"
    db_password: str = "filewallball_user_password"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_pool_size: int = 20

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
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        """Generate Redis URL from settings."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    debug: bool = True
    environment: str = "development"

    # Development-specific settings
    log_level: str = "DEBUG"
    cors_origins: List[str] = ["*"]

    # Development MariaDB
    db_host: str = "localhost"  # For local development
    db_name: str = "filewallball_dev"

    # Development secret key (change in production)
    secret_key: str = "dev-secret-key-change-in-production"


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    debug: bool = False
    environment: str = "testing"

    # Testing-specific settings
    log_level: str = "WARNING"

    # Use separate test database
    db_name: str = "filewallball_test"

    # Use separate Redis database for testing
    redis_db: int = 1

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

    # Production database settings (should be set via environment)
    db_host: str = Field(..., env="DB_HOST")
    db_name: str = Field(..., env="DB_NAME")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")

    # Production Redis settings
    redis_host: str = Field(..., env="REDIS_HOST")
    redis_password: str = Field(..., env="REDIS_PASSWORD")

    # Production secret key (must be set via environment)
    secret_key: str = Field(..., env="SECRET_KEY")

    # Production CORS settings
    cors_origins: List[str] = Field(..., env="CORS_ORIGINS")
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
