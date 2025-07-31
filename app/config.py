"""
Environment configuration management using Pydantic BaseSettings.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""

    model_config = {"extra": "ignore"}

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

    # 파일 저장 설정 - 기본값
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")

    # 파일 저장 설정 - 고급 옵션
    # 호스트 OS 경로 (Docker/K8s에서 볼륨 마운트용)
    host_upload_dir: str = Field(default="./uploads", env="HOST_UPLOAD_DIR")

    # 컨테이너 내부 경로
    container_upload_dir: str = Field(
        default="/app/uploads", env="CONTAINER_UPLOAD_DIR"
    )

    # 저장소 타입 (local, s3, azure, gcs)
    storage_type: str = Field(default="local", env="STORAGE_TYPE")

    # 로컬 저장소 설정
    local_storage_path: str = Field(default="./uploads", env="LOCAL_STORAGE_PATH")

    # S3 저장소 설정 (storage_type이 s3일 때 사용)
    s3_bucket: str = Field(default="", env="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", env="S3_REGION")
    s3_access_key: str = Field(default="", env="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", env="S3_SECRET_KEY")
    s3_endpoint_url: str = Field(default="", env="S3_ENDPOINT_URL")

    # Azure Blob Storage 설정 (storage_type이 azure일 때 사용)
    azure_connection_string: str = Field(default="", env="AZURE_CONNECTION_STRING")
    azure_container_name: str = Field(default="", env="AZURE_CONTAINER_NAME")

    # Google Cloud Storage 설정 (storage_type이 gcs일 때 사용)
    gcs_bucket: str = Field(default="", env="GCS_BUCKET")
    gcs_credentials_file: str = Field(default="", env="GCS_CREDENTIALS_FILE")

    # 파일 저장 구조 설정
    storage_structure: str = Field(
        default="date", env="STORAGE_STRUCTURE"
    )  # date, uuid, flat
    storage_date_format: str = Field(default="%Y/%m/%d", env="STORAGE_DATE_FORMAT")
    storage_uuid_depth: int = Field(
        default=2, env="STORAGE_UUID_DEPTH"
    )  # UUID 기반 계층 깊이

    # 파일 크기 및 형식 설정
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
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

    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    # CORS 설정
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")

    # 보안 설정
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # 캐시 설정
    cache_ttl_file_metadata: int = Field(
        default=3600, env="CACHE_TTL_FILE_METADATA"
    )  # 1시간
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

    @validator("host_upload_dir")
    def validate_host_upload_dir(cls, v):
        """호스트 업로드 디렉토리 유효성 검사"""
        host_path = Path(v)
        if not host_path.exists():
            host_path.mkdir(parents=True, exist_ok=True)
        return str(host_path)

    @property
    def effective_upload_dir(self) -> str:
        """실제 사용할 업로드 디렉토리 경로 반환"""
        if self.environment == "production" and self.storage_type == "local":
            # 프로덕션 환경에서는 컨테이너 내부 경로 사용
            return self.container_upload_dir
        elif self.environment == "development":
            # 개발 환경에서는 호스트 경로 사용
            return self.host_upload_dir
        else:
            # 기본값
            return self.upload_dir

    @property
    def storage_config(self) -> Dict[str, Any]:
        """저장소 타입별 설정 반환"""
        config = {
            "type": self.storage_type,
            "local": {
                "path": self.local_storage_path,
                "effective_path": self.effective_upload_dir,
            },
        }

        if self.storage_type == "s3":
            config["s3"] = {
                "bucket": self.s3_bucket,
                "region": self.s3_region,
                "access_key": self.s3_access_key,
                "secret_key": self.s3_secret_key,
                "endpoint_url": self.s3_endpoint_url,
            }
        elif self.storage_type == "azure":
            config["azure"] = {
                "connection_string": self.azure_connection_string,
                "container_name": self.azure_container_name,
            }
        elif self.storage_type == "gcs":
            config["gcs"] = {
                "bucket": self.gcs_bucket,
                "credentials_file": self.gcs_credentials_file,
            }

        return config

    # SQLite URL 생성
    @property
    def database_url(self) -> str:
        if self.environment == "development" and self.db_host == "localhost":
            return f"sqlite:///./{self.db_name}"
        else:
            return (
                f"mysql+pymysql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )

    @property
    def redis_url(self) -> str:
        """Redis URL 생성"""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:"
                f"{self.redis_port}/{self.redis_db}"
            )
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/" f"{self.redis_db}"


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """설정 인스턴스를 반환하는 함수"""
    return settings
