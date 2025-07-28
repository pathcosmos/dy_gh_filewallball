"""
Environment configuration management using Pydantic BaseSettings.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""
    
    model_config = {
        "extra": "ignore"
    }
    
    # 애플리케이션 기본 설정
    app_name: str = Field(default="FileWallBall API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # 데이터베이스 설정 (MariaDB)
    db_host: str = Field(default="mariadb-service", env="DB_HOST")
    db_port: int = Field(default=3306, env="DB_PORT")
    db_name: str = Field(default="filewallball_db", env="DB_NAME")
    db_user: str = Field(default="filewallball_user", env="DB_USER")
    db_password: str = Field(default="filewallball_user_password", env="DB_PASSWORD")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Redis 설정
    redis_host: str = Field(default="redis-service", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_pool_size: int = Field(default=20, env="REDIS_POOL_SIZE")
    
    # 파일 저장 설정
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    allowed_extensions: List[str] = Field(
        default=[
            ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", 
            ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3",
            ".zip", ".rar", ".7z"
        ],
        env="ALLOWED_EXTENSIONS"
    )
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # CORS 설정
    cors_origins: List[str] = Field(
        default=["*"], 
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # 보안 설정
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 캐시 설정
    cache_ttl_file_metadata: int = Field(default=3600, env="CACHE_TTL_FILE_METADATA")  # 1시간
    cache_ttl_session: int = Field(default=86400, env="CACHE_TTL_SESSION")  # 24시간
    cache_ttl_temp: int = Field(default=600, env="CACHE_TTL_TEMP")  # 10분
    
    # 성능 설정
    upload_chunk_size: int = Field(default=8192, env="UPLOAD_CHUNK_SIZE")
    download_chunk_size: int = Field(default=8192, env="DOWNLOAD_CHUNK_SIZE")
    
    @validator("allowed_extensions", pre=True)
    def parse_allowed_extensions(cls, v):
        """allowed_extensions 문자열을 리스트로 파싱"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """cors_origins 문자열을 리스트로 파싱"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("upload_dir")
    def validate_upload_dir(cls, v):
        """업로드 디렉토리 유효성 검사 및 생성"""
        upload_path = Path(v)
        upload_path.mkdir(parents=True, exist_ok=True)
        return str(upload_path)
    
    @property
    def database_url(self) -> str:
        """데이터베이스 URL 생성"""
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Redis URL 생성"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}" 