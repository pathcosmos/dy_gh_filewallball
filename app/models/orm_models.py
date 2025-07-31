"""
SQLAlchemy ORM Models for FileWallBall application.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class FileInfo(Base):
    """파일 정보 모델"""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_category_id: Mapped[Optional[int]] = mapped_column(
        SmallInteger, ForeignKey("file_categories.id")
    )
    owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )  # Task 12.5: 파일 소유자
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 관계 정의
    category: Mapped[Optional["FileCategory"]] = relationship(
        "FileCategory", back_populates="files"
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User", back_populates="owned_files"
    )  # Task 12.5: 소유자 관계
    uploads: Mapped[List["FileUpload"]] = relationship(
        "FileUpload", back_populates="file"
    )
    tags: Mapped[List["FileTag"]] = relationship(
        "FileTag", secondary="file_tag_relations", back_populates="files"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.file_uuid:
            self.file_uuid = str(uuid.uuid4())

    def __repr__(self):
        return f"<FileInfo(id={self.id}, uuid={self.file_uuid}, filename='{self.original_filename}')>"


class FileCategory(Base):
    """파일 카테고리 모델"""

    __tablename__ = "file_categories"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 관계 정의
    files: Mapped[List["FileInfo"]] = relationship(
        "FileInfo", back_populates="category"
    )

    def __repr__(self):
        return f"<FileCategory(id={self.id}, name='{self.name}')>"


class FileExtension(Base):
    """파일 확장자 관리 모델"""

    __tablename__ = "file_extensions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    extension: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    max_file_size: Mapped[int] = mapped_column(BigInteger, default=10485760)  # 10MB
    description: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FileExtension(id={self.id}, extension='{self.extension}')>"


class FileUpload(Base):
    """파일 업로드 추적 모델"""

    __tablename__ = "file_uploads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False
    )
    upload_session_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    upload_status: Mapped[str] = mapped_column(String(20), default="completed")
    upload_started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    upload_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 관계 정의
    file: Mapped["FileInfo"] = relationship("FileInfo", back_populates="uploads")

    def __repr__(self):
        return f"<FileUpload(id={self.id}, file_id={self.file_id}, status='{self.upload_status}')>"


class FileTag(Base):
    """파일 태그 모델"""

    __tablename__ = "file_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tag_name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    tag_color: Mapped[str] = mapped_column(String(7), default="#007bff")
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 관계 정의
    files: Mapped[List["FileInfo"]] = relationship(
        "FileInfo", secondary="file_tag_relations", back_populates="tags"
    )

    def __repr__(self):
        return f"<FileTag(id={self.id}, name='{self.tag_name}')>"


class FileTagRelation(Base):
    """파일-태그 관계 모델 (다대다)"""

    __tablename__ = "file_tag_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("file_tags.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("file_id", "tag_id"),)

    def __repr__(self):
        return f"<FileTagRelation(file_id={self.file_id}, tag_id={self.tag_id})>"


class FileView(Base):
    """파일 조회 로그 모델"""

    __tablename__ = "file_views"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False
    )
    viewer_ip: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    referer: Mapped[Optional[str]] = mapped_column(String(500))
    view_type: Mapped[str] = mapped_column(
        Enum("info", "preview", "download"), nullable=False
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<FileView(id={self.id}, file_id={self.file_id}, type='{self.view_type}')>"
        )


class FileDownload(Base):
    """파일 다운로드 로그 모델"""

    __tablename__ = "file_downloads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False
    )
    downloader_ip: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    download_method: Mapped[str] = mapped_column(
        Enum("direct", "api", "web"), nullable=False
    )
    bytes_downloaded: Mapped[Optional[int]] = mapped_column(BigInteger)
    download_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FileDownload(id={self.id}, file_id={self.file_id}, method='{self.download_method}')>"


class SystemSetting(Base):
    """시스템 설정 모델"""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    setting_value: Mapped[Optional[str]] = mapped_column(Text)
    setting_type: Mapped[str] = mapped_column(
        String(20), default="string"
    )  # string, integer, boolean, json
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<SystemSetting(id={self.id}, key='{self.setting_key}')>"


class FileStatistics(Base):
    """파일별 상세 통계 뷰 모델 (Task 8.5)"""

    __tablename__ = "file_statistics"
    __table_args__ = {"info": {"is_view": True}}

    # 기본 파일 정보
    file_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    file_id: Mapped[int] = mapped_column(BigInteger)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_extension: Mapped[str] = mapped_column(String(20))
    file_size: Mapped[int] = mapped_column(BigInteger)
    is_public: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    # 조회 통계
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    unique_viewers: Mapped[int] = mapped_column(Integer, default=0)
    last_viewed: Mapped[Optional[datetime]] = mapped_column(DateTime)
    first_viewed: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 다운로드 통계
    total_downloads: Mapped[int] = mapped_column(Integer, default=0)
    unique_downloaders: Mapped[int] = mapped_column(Integer, default=0)
    last_downloaded: Mapped[Optional[datetime]] = mapped_column(DateTime)
    first_downloaded: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_bytes_downloaded: Mapped[int] = mapped_column(BigInteger, default=0)

    # 계산된 통계
    total_interactions: Mapped[int] = mapped_column(Integer, default=0)
    popularity_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_daily_views: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # 최근 활동
    recent_views: Mapped[int] = mapped_column(Integer, default=0)
    recent_downloads: Mapped[int] = mapped_column(Integer, default=0)

    # 조회 타입별 통계
    info_views: Mapped[int] = mapped_column(Integer, default=0)
    preview_views: Mapped[int] = mapped_column(Integer, default=0)
    thumbnail_views: Mapped[int] = mapped_column(Integer, default=0)

    # 메타데이터
    statistics_updated_at: Mapped[datetime] = mapped_column(DateTime)

    def __repr__(self):
        return f"<FileStatistics(file_uuid={self.file_uuid}, views={self.total_views}, downloads={self.total_downloads})>"


# 헬퍼 함수들
def generate_file_uuid() -> str:
    """UUID v4 생성 함수"""
    return str(uuid.uuid4())


def add_tags_to_file(db_session, file_id: int, tag_names: List[str]) -> bool:
    """파일에 태그 일괄 추가"""
    try:
        for tag_name in tag_names:
            # 태그가 존재하는지 확인
            tag = db_session.query(FileTag).filter(FileTag.tag_name == tag_name).first()
            if not tag:
                tag = FileTag(tag_name=tag_name)
                db_session.add(tag)
                db_session.flush()

            # 관계가 이미 존재하는지 확인
            existing_relation = (
                db_session.query(FileTagRelation)
                .filter(
                    FileTagRelation.file_id == file_id, FileTagRelation.tag_id == tag.id
                )
                .first()
            )

            if not existing_relation:
                relation = FileTagRelation(file_id=file_id, tag_id=tag.id)
                db_session.add(relation)

        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        raise e


def remove_tags_from_file(db_session, file_id: int, tag_names: List[str]) -> bool:
    """파일에서 태그 제거"""
    try:
        for tag_name in tag_names:
            tag = db_session.query(FileTag).filter(FileTag.tag_name == tag_name).first()
            if tag:
                relation = (
                    db_session.query(FileTagRelation)
                    .filter(
                        FileTagRelation.file_id == file_id,
                        FileTagRelation.tag_id == tag.id,
                    )
                    .first()
                )
                if relation:
                    db_session.delete(relation)

        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        raise e


def get_file_statistics(db_session) -> List[FileStatistics]:
    """카테고리별 파일 통계 조회"""
    try:
        return db_session.query(FileStatistics).all()
    except Exception as e:
        return []


def bulk_insert_files(db_session, files_data: List[dict]) -> bool:
    """대량 파일 정보 삽입"""
    try:
        for file_data in files_data:
            file_info = FileInfo(**file_data)
            db_session.add(file_info)

        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        raise e


def soft_delete_file(db_session, file_uuid: str) -> bool:
    """파일 소프트 삭제"""
    try:
        file_info = (
            db_session.query(FileInfo).filter(FileInfo.file_uuid == file_uuid).first()
        )

        if file_info:
            file_info.is_deleted = True
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        raise e


def restore_file(db_session, file_uuid: str) -> bool:
    """삭제된 파일 복구"""
    try:
        file_info = (
            db_session.query(FileInfo).filter(FileInfo.file_uuid == file_uuid).first()
        )

        if file_info:
            file_info.is_deleted = False
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        raise e


class AllowedIP(Base):
    """IP 기반 인증 허용 목록 모델"""

    __tablename__ = "allowed_ips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(
        String(45), nullable=False, index=True
    )  # IPv6 지원
    ip_range: Mapped[Optional[str]] = mapped_column(String(18))  # CIDR 표기법
    encryption_key: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # 키 해시 저장
    permissions: Mapped[Optional[str]] = mapped_column(JSON)  # 권한 설정
    max_uploads_per_hour: Mapped[int] = mapped_column(Integer, default=100)
    max_file_size: Mapped[int] = mapped_column(BigInteger, default=104857600)  # 100MB
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 관계 정의
    auth_logs: Mapped[List["IPAuthLog"]] = relationship(
        "IPAuthLog", back_populates="allowed_ip"
    )

    __table_args__ = (
        UniqueConstraint("ip_address", "encryption_key", name="unique_ip_key"),
    )

    def __repr__(self):
        return f"<AllowedIP(id={self.id}, ip='{self.ip_address}', active={self.is_active})>"


class IPAuthLog(Base):
    """IP 인증 로그 모델"""

    __tablename__ = "ip_auth_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    allowed_ip_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("allowed_ips.id")
    )
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # upload, auth_failed, rate_limited
    file_uuid: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    request_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    response_code: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    request_size: Mapped[Optional[int]] = mapped_column(BigInteger)  # 요청 크기
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)  # 처리 시간

    # 관계 정의
    allowed_ip: Mapped[Optional["AllowedIP"]] = relationship(
        "AllowedIP", back_populates="auth_logs"
    )

    def __repr__(self):
        return (
            f"<IPAuthLog(id={self.id}, ip='{self.ip_address}', action='{self.action}')>"
        )


class IPRateLimit(Base):
    """IP별 Rate Limiting 모델"""

    __tablename__ = "ip_rate_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    last_request_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "ip_address", "api_key_hash", "window_start", name="unique_rate_limit"
        ),
    )

    def __repr__(self):
        return f"<IPRateLimit(id={self.id}, ip='{self.ip_address}', count={self.request_count})>"


class User(Base):
    """사용자 모델 (Task 12.5: RBAC 구현)"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "user", "moderator"), default="user", nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 관계 정의
    owned_files: Mapped[List["FileInfo"]] = relationship(
        "FileInfo", back_populates="owner"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class AuditLog(Base):
    """감사 로그 모델 (Task 12.5: 보안 추적성)"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # create, read, update, delete, login, logout
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # file, user, system
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(100), index=True
    )  # file_uuid, user_id 등
    resource_name: Mapped[Optional[str]] = mapped_column(
        String(255)
    )  # 파일명, 사용자명 등
    details: Mapped[Optional[str]] = mapped_column(Text)  # 상세 정보 (JSON 형태)
    status: Mapped[str] = mapped_column(
        Enum("success", "failed", "denied"), default="success", index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    request_path: Mapped[str] = mapped_column(String(500), nullable=False)
    request_method: Mapped[str] = mapped_column(String(10), nullable=False)
    response_code: Mapped[Optional[int]] = mapped_column(Integer)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # 관계 정의
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', resource='{self.resource_type}')>"
