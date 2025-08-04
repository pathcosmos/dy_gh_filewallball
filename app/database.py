import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
    create_engine,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 데이터베이스 설정 - MariaDB 컨테이너
DB_HOST = os.getenv("DB_HOST", "mariadb-service")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "filewallball_db")
DB_USER = os.getenv("DB_USER", "filewallball_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "filewallball_user_password")

# MariaDB URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# SQLAlchemy 설정 - MariaDB
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()

# 메타데이터
metadata = MetaData()

# 테이블 정의
files = Table(
    "files",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("file_uuid", String(36), nullable=False, unique=True),
    Column("original_filename", String(255), nullable=False),
    Column("stored_filename", String(255), nullable=False),
    Column("file_extension", String(20), nullable=False),
    Column("mime_type", String(100), nullable=False),
    Column("file_size", BigInteger, nullable=False),
    Column("file_hash", String(64)),
    Column("storage_path", String(500), nullable=False),
    Column("file_category_id", SmallInteger),
    Column("is_public", Boolean, default=True),
    Column("is_deleted", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)

file_views = Table(
    "file_views",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("file_id", BigInteger, nullable=False),
    Column("viewer_ip", String(45)),
    Column("user_agent", Text),
    Column("referer", String(500)),
    Column("view_type", Enum("info", "preview", "download"), nullable=False),
    Column("session_id", String(100)),
    Column("created_at", DateTime, default=datetime.utcnow),
)

file_downloads = Table(
    "file_downloads",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("file_id", BigInteger, nullable=False),
    Column("downloader_ip", String(45)),
    Column("user_agent", Text),
    Column("download_method", Enum("direct", "api", "web"), nullable=False),
    Column("bytes_downloaded", BigInteger),
    Column("download_duration_ms", Integer),
    Column("session_id", String(100)),
    Column("created_at", DateTime, default=datetime.utcnow),
)

file_uploads = Table(
    "file_uploads",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("file_id", BigInteger, nullable=False),
    Column("uploader_ip", String(45)),
    Column("user_agent", Text),
    Column("upload_method", Enum("web", "api", "batch"), nullable=False),
    Column("upload_duration_ms", Integer),
    Column("upload_status", Enum("success", "failed", "partial"), nullable=False),
    Column("error_message", Text),
    Column("session_id", String(100)),
    Column("created_at", DateTime, default=datetime.utcnow),
)

file_categories = Table(
    "file_categories",
    metadata,
    Column("id", SmallInteger, primary_key=True, autoincrement=True),
    Column("name", String(50), nullable=False, unique=True),
    Column("description", Text),
    Column("icon", String(50)),
    Column("color", String(7)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

file_extensions = Table(
    "file_extensions",
    metadata,
    Column("id", SmallInteger, primary_key=True, autoincrement=True),
    Column("extension", String(20), nullable=False, unique=True),
    Column("mime_type", String(100), nullable=False),
    Column("description", String(200)),
    Column("is_text_file", Boolean, default=False),
    Column("is_image_file", Boolean, default=False),
    Column("is_video_file", Boolean, default=False),
    Column("is_audio_file", Boolean, default=False),
    Column("is_document_file", Boolean, default=False),
    Column("is_archive_file", Boolean, default=False),
    Column("max_file_size", BigInteger, default=104857600),
    Column("is_allowed", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

system_settings = Table(
    "system_settings",
    metadata,
    Column("id", SmallInteger, primary_key=True, autoincrement=True),
    Column("setting_key", String(100), nullable=False, unique=True),
    Column("setting_value", Text),
    Column(
        "setting_type", Enum("string", "integer", "boolean", "json"), nullable=False
    ),
    Column("description", Text),
    Column("is_public", Boolean, default=False),
    Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)


class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal

    def get_db(self) -> Session:
        """데이터베이스 세션 반환"""
        db = self.SessionLocal()
        try:
            return db
        except Exception as e:
            logger.error(f"Database session error: {e}")
            db.close()
            raise

    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def create_tables(self):
        """테이블 생성"""
        try:
            metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise


# 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


# 의존성 함수
def get_db():
    """FastAPI 의존성 주입용 데이터베이스 세션"""
    db = db_manager.get_db()
    try:
        yield db
    finally:
        db.close()


# 데이터베이스 모델 클래스들
class FileModel:
    def __init__(self, db: Session):
        self.db = db

    def create_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """파일 정보 생성"""
        try:
            query = files.insert().values(**file_data)
            result = self.db.execute(query)
            self.db.commit()
            return {"id": result.inserted_primary_key[0], **file_data}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create file: {e}")
            raise

    def get_file_by_uuid(self, file_uuid: str) -> Optional[Dict[str, Any]]:
        """UUID로 파일 조회"""
        try:
            query = files.select().where(
                files.c.file_uuid == file_uuid, files.c.is_deleted == False
            )
            result = self.db.execute(query)
            row = result.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get file by UUID: {e}")
            return None

    def get_files(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """파일 목록 조회"""
        try:
            query = (
                files.select()
                .where(files.c.is_deleted == False)
                .order_by(files.c.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = self.db.execute(query)
            return [dict(row) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get files: {e}")
            return []

    def delete_file(self, file_uuid: str) -> bool:
        """파일 삭제 (소프트 삭제)"""
        try:
            query = (
                files.update()
                .where(files.c.file_uuid == file_uuid)
                .values(is_deleted=True)
            )
            result = self.db.execute(query)
            self.db.commit()
            return result.rowcount > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete file: {e}")
            return False


class FileViewModel:
    def __init__(self, db: Session):
        self.db = db

    def log_view(self, view_data: Dict[str, Any]) -> bool:
        """파일 조회 로그 기록"""
        try:
            query = file_views.insert().values(**view_data)
            self.db.execute(query)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log file view: {e}")
            return False


class FileDownloadModel:
    def __init__(self, db: Session):
        self.db = db

    def log_download(self, download_data: Dict[str, Any]) -> bool:
        """파일 다운로드 로그 기록"""
        try:
            query = file_downloads.insert().values(**download_data)
            self.db.execute(query)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log file download: {e}")
            return False


class FileUploadModel:
    def __init__(self, db: Session):
        self.db = db

    def log_upload(self, upload_data: Dict[str, Any]) -> bool:
        """파일 업로드 로그 기록"""
        try:
            query = file_uploads.insert().values(**upload_data)
            self.db.execute(query)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log file upload: {e}")
            return False


class SystemSettingsModel:
    def __init__(self, db: Session):
        self.db = db

    def get_setting(self, key: str) -> Optional[str]:
        """시스템 설정 조회"""
        try:
            query = system_settings.select().where(system_settings.c.setting_key == key)
            result = self.db.execute(query)
            row = result.fetchone()
            return row.setting_value if row else None
        except Exception as e:
            logger.error(f"Failed to get setting: {e}")
            return None

    def set_setting(self, key: str, value: str, setting_type: str = "string") -> bool:
        """시스템 설정 저장/업데이트"""
        try:
            query = (
                system_settings.insert()
                .values(setting_key=key, setting_value=value, setting_type=setting_type)
                .on_duplicate_key_update(setting_value=value, setting_type=setting_type)
            )
            self.db.execute(query)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to set setting: {e}")
            return False


# 초기화 함수
def init_database():
    """데이터베이스 초기화"""
    try:
        # 연결 테스트
        if not db_manager.test_connection():
            logger.error("Database connection failed")
            return False

        # 테이블 생성
        db_manager.create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
