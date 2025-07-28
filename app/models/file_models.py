"""
File-related database models and business logic.
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from .database import (
    files, file_views, file_downloads, file_uploads, system_settings
)

logger = logging.getLogger(__name__)


class FileModel:
    """파일 정보 관리 모델"""
    
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
                files.c.file_uuid == file_uuid, 
                files.c.is_deleted.is_(False)
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
            query = files.select().where(
                files.c.is_deleted.is_(False)
            ).order_by(
                files.c.created_at.desc()
            ).limit(limit).offset(offset)
            result = self.db.execute(query)
            return [dict(row) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get files: {e}")
            return []
    
    def delete_file(self, file_uuid: str) -> bool:
        """파일 삭제 (소프트 삭제)"""
        try:
            query = files.update().where(
                files.c.file_uuid == file_uuid
            ).values(is_deleted=True)
            result = self.db.execute(query)
            self.db.commit()
            return result.rowcount > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete file: {e}")
            return False


class FileViewModel:
    """파일 조회 로그 모델"""
    
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
    """파일 다운로드 로그 모델"""
    
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
    """파일 업로드 로그 모델"""
    
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
    """시스템 설정 모델"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_setting(self, key: str) -> Optional[str]:
        """시스템 설정 조회"""
        try:
            query = system_settings.select().where(
                system_settings.c.setting_key == key
            )
            result = self.db.execute(query)
            row = result.fetchone()
            return row.setting_value if row else None
        except Exception as e:
            logger.error(f"Failed to get setting: {e}")
            return None
    
    def set_setting(
        self, key: str, value: str, setting_type: str = 'string'
    ) -> bool:
        """시스템 설정 저장/업데이트"""
        try:
            query = system_settings.insert().values(
                setting_key=key,
                setting_value=value,
                setting_type=setting_type
            ).on_duplicate_key_update(
                setting_value=value,
                setting_type=setting_type
            )
            self.db.execute(query)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to set setting: {e}")
            return False 