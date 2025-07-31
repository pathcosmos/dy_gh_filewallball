"""
Database connection and configuration.
"""

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

# 데이터베이스 설정
DB_HOST = os.getenv("DB_HOST", "mariadb-service")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "filewallball_db")
DB_USER = os.getenv("DB_USER", "filewallball_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "filewallball_user_password")

# 데이터베이스 URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 설정
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,  # SQL 로그 출력 여부
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
    Column("name", String(100), nullable=False, unique=True),
    Column("description", String(255)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

file_extensions = Table(
    "file_extensions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("extension", String(10), nullable=False, unique=True),
    Column("mime_type", String(100), nullable=False),
    Column("is_allowed", Boolean, default=True),
    Column("max_file_size", BigInteger, default=10485760),  # 10MB
    Column("description", String(255)),
    Column("created_at", DateTime, default=datetime.utcnow),
)

file_tags = Table(
    "file_tags",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tag_name", String(50), nullable=False, unique=True),
    Column("tag_color", String(7), default="#007bff"),
    Column("description", String(255)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

file_tag_relations = Table(
    "file_tag_relations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("file_id", BigInteger, nullable=False),
    Column("tag_id", Integer, nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

system_settings = Table(
    "system_settings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("setting_key", String(100), nullable=False, unique=True),
    Column("setting_value", Text),
    Column("setting_type", String(20), default="string"),
    Column("description", String(255)),
    Column("is_public", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)


# 데이터베이스 매니저
class DatabaseManager:
    """데이터베이스 연결 및 관리 클래스"""

    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal

    def get_db(self) -> Session:
        """데이터베이스 세션 반환"""
        return self.SessionLocal()

    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def create_tables(self):
        """테이블 생성"""
        try:
            metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


def get_db():
    """FastAPI 의존성 주입용 데이터베이스 세션"""
    db = db_manager.get_db()
    try:
        yield db
    finally:
        db.close()


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
