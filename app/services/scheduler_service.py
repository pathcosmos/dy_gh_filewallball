"""
Scheduler service for automated file cleanup tasks.
Task 12.2: 파일 영구 삭제 정책 및 스케줄러 구현
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.dependencies.database import get_db
from app.models.orm_models import FileInfo
from app.services.cache_service import CacheService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class SchedulerService:
    """파일 영구 삭제 스케줄러 서비스"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.cache_service = CacheService()
        self.retention_days = 30  # 소프트 삭제 후 30일 후 영구 삭제
        
    async def start_scheduler(self):
        """스케줄러 시작"""
        try:
            # 매일 새벽 2시에 실행
            self.scheduler.add_job(
                self.cleanup_deleted_files,
                CronTrigger(hour=2, minute=0),
                id='cleanup_deleted_files',
                name='Cleanup deleted files',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("File cleanup scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop_scheduler(self):
        """스케줄러 중지"""
        try:
            self.scheduler.shutdown()
            logger.info("File cleanup scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
    
    async def cleanup_deleted_files(self):
        """소프트 삭제된 파일들을 영구 삭제하는 작업"""
        logger.info("Starting cleanup of deleted files...")
        
        try:
            # 데이터베이스 세션 생성
            db = next(get_db())
            
            # 30일 이상 경과한 소프트 삭제된 파일들 조회
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            deleted_files = db.query(FileInfo).filter(
                and_(
                    FileInfo.is_deleted == True,
                    FileInfo.updated_at <= cutoff_date
                )
            ).all()
            
            logger.info(f"Found {len(deleted_files)} files to permanently delete")
            
            deleted_count = 0
            error_count = 0
            
            for file_info in deleted_files:
                try:
                    await self._permanently_delete_file(file_info, db)
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to delete file {file_info.file_uuid}: {e}")
                    error_count += 1
            
            logger.info(
                f"Cleanup completed: {deleted_count} files deleted, "
                f"{error_count} errors"
            )
            
        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")
        finally:
            db.close()
    
    async def _permanently_delete_file(self, file_info: FileInfo, db: Session):
        """개별 파일을 영구 삭제"""
        try:
            # 실제 파일 시스템에서 파일 삭제
            file_path = os.path.join("uploads", file_info.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Physical file deleted: {file_path}")
            
            # 썸네일 파일들 삭제
            await self._delete_thumbnails(file_info.file_uuid)
            
            # 캐시 무효화
            try:
                await self.cache_service.invalidate_file_cache(file_info.file_uuid)
            except Exception as cache_error:
                logger.warning(f"Cache invalidation failed: {cache_error}")
            
            # 데이터베이스에서 레코드 삭제
            db.delete(file_info)
            db.commit()
            
            logger.info(f"File permanently deleted: {file_info.file_uuid}")
            
        except Exception as e:
            logger.error(f"Failed to permanently delete file {file_info.file_uuid}: {e}")
            raise
    
    async def _delete_thumbnails(self, file_uuid: str):
        """썸네일 파일들 삭제"""
        try:
            thumbnail_dir = os.path.join("uploads", "thumbnails")
            if os.path.exists(thumbnail_dir):
                for size in ["small", "medium", "large"]:
                    thumbnail_path = os.path.join(
                        thumbnail_dir, 
                        f"{file_uuid}_{size}.jpg"
                    )
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                        logger.debug(f"Thumbnail deleted: {thumbnail_path}")
                        
        except Exception as e:
            logger.warning(f"Failed to delete thumbnails for {file_uuid}: {e}")
    
    async def get_cleanup_stats(self, db: Session) -> dict:
        """정리 작업 통계 조회"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            # 삭제 예정 파일 수
            pending_deletion = db.query(FileInfo).filter(
                and_(
                    FileInfo.is_deleted == True,
                    FileInfo.updated_at <= cutoff_date
                )
            ).count()
            
            # 최근 7일간 삭제된 파일 수
            week_ago = datetime.utcnow() - timedelta(days=7)
            recently_deleted = db.query(FileInfo).filter(
                and_(
                    FileInfo.is_deleted == True,
                    FileInfo.updated_at >= week_ago
                )
            ).count()
            
            return {
                "pending_deletion": pending_deletion,
                "recently_deleted": recently_deleted,
                "retention_days": self.retention_days,
                "next_cleanup": self._get_next_cleanup_time(),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get cleanup stats: {e}")
            return {}
    
    def _get_next_cleanup_time(self) -> Optional[str]:
        """다음 정리 작업 시간 조회"""
        try:
            job = self.scheduler.get_job('cleanup_deleted_files')
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception as e:
            logger.warning(f"Failed to get next cleanup time: {e}")
        return None
    
    def update_retention_days(self, days: int):
        """보관 기간 업데이트"""
        if days < 1:
            raise ValueError("Retention days must be at least 1")
        
        self.retention_days = days
        logger.info(f"Retention period updated to {days} days")


# 전역 스케줄러 인스턴스
scheduler_service = SchedulerService() 