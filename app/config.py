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
    
    # 기본 설정
    app_name: str = "FileWallBall API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 데이터베이스 설정 - 로컬 개발용 SQLite
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "filewallball.db"
    db_user: str = ""
    db_password: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Redis 설정
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_pool_size: int = 20
    
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
    
    # SQLite URL 생성
    @property
    def database_url(self) -> str:
        if self.environment == "development" and self.db_host == "localhost":
            return f"sqlite:///./{self.db_name}"
        else:
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Redis URL 생성"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# 전역 설정 인스턴스
_settings = None


def get_settings() -> Settings:
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 