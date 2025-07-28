"""
Database models and ORM definitions.
"""

from .database import Base, get_db, DatabaseManager
from .file_models import (
    FileModel, FileViewModel, FileDownloadModel, 
    FileUploadModel, SystemSettingsModel
)
from .orm_models import (
    FileInfo, FileCategory, FileExtension, FileUpload, FileTag, 
    FileTagRelation, FileView, FileDownload, SystemSetting, 
    FileStatistics, generate_file_uuid, add_tags_to_file, 
    remove_tags_from_file, get_file_statistics, bulk_insert_files,
    soft_delete_file, restore_file
)

__all__ = [
    # 기존 모델들
    "Base",
    "get_db", 
    "DatabaseManager",
    "FileModel",
    "FileViewModel", 
    "FileDownloadModel",
    "FileUploadModel",
    "SystemSettingsModel",
    
    # 새로운 ORM 모델들
    "FileInfo",
    "FileCategory", 
    "FileExtension",
    "FileUpload",
    "FileTag",
    "FileTagRelation",
    "FileView",
    "FileDownload",
    "SystemSetting",
    "FileStatistics",
    
    # 헬퍼 함수들
    "generate_file_uuid",
    "add_tags_to_file",
    "remove_tags_from_file", 
    "get_file_statistics",
    "bulk_insert_files",
    "soft_delete_file",
    "restore_file"
] 