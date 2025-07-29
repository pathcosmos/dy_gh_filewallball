"""
파일 통계 관리 서비스 모듈
Task 8.5: 조회/다운로드 통계 집계 뷰 생성 및 연동
FileStatistics 뷰를 활용한 효율적인 통계 데이터 관리
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.models.orm_models import FileStatistics, FileView, FileDownload, FileInfo
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class StatisticsService:
    """파일 통계 관리 서비스 클래스 - Task 8.5"""

    def __init__(self):
        self.cache_service = CacheService()
        
        # Task 8.5: 통계 캐시 설정
        self.cache_config = {
            'file_stats_ttl': 1800,  # 30분
            'popular_files_ttl': 3600,  # 1시간
            'trending_files_ttl': 900,  # 15분
            'cache_key_prefix': 'stats:'
        }

    async def get_file_statistics(self, db: Session, file_uuid: str) -> Optional[Dict[str, Any]]:
        """
        파일별 상세 통계 조회 (캐시 우선)
        
        Args:
            db: 데이터베이스 세션
            file_uuid: 파일 UUID
            
        Returns:
            파일 통계 정보
        """
        cache_key = f"{self.cache_config['cache_key_prefix']}file:{file_uuid}"
        
        # Task 8.5: 캐시에서 통계 정보 확인
        cached_stats = await self.cache_service.get(cache_key)
        if cached_stats:
            logger.info(f"파일 통계 캐시 히트: {file_uuid}")
            return cached_stats
        
        # Task 8.5: FileStatistics 뷰에서 통계 조회
        logger.info(f"파일 통계 캐시 미스: {file_uuid}")
        
        stats_result = db.query(FileStatistics).filter(
            FileStatistics.file_uuid == file_uuid
        ).first()
        
        if not stats_result:
            return None
        
        # Task 8.5: 통계 데이터 구성
        stats_data = {
            "file_uuid": stats_result.file_uuid,
            "total_views": stats_result.total_views,
            "unique_viewers": stats_result.unique_viewers,
            "total_downloads": stats_result.total_downloads,
            "unique_downloaders": stats_result.unique_downloaders,
            "total_interactions": stats_result.total_interactions,
            "popularity_score": float(stats_result.popularity_score),
            "avg_daily_views": float(stats_result.avg_daily_views),
            "engagement_rate": float(stats_result.engagement_rate),
            "recent_views": stats_result.recent_views,
            "recent_downloads": stats_result.recent_downloads,
            "view_breakdown": {
                "info_views": stats_result.info_views,
                "preview_views": stats_result.preview_views,
                "thumbnail_views": stats_result.thumbnail_views
            },
            "last_viewed": stats_result.last_viewed.isoformat() if stats_result.last_viewed else None,
            "first_viewed": stats_result.first_viewed.isoformat() if stats_result.first_viewed else None,
            "last_downloaded": stats_result.last_downloaded.isoformat() if stats_result.last_downloaded else None,
            "first_downloaded": stats_result.first_downloaded.isoformat() if stats_result.first_downloaded else None,
            "total_bytes_downloaded": stats_result.total_bytes_downloaded,
            "statistics_updated_at": stats_result.statistics_updated_at.isoformat(),
            "cached_at": datetime.utcnow().isoformat()
        }
        
        # Task 8.5: 통계 데이터 캐시 저장
        try:
            await self.cache_service.set(
                cache_key, 
                stats_data, 
                self.cache_config['file_stats_ttl']
            )
            logger.info(f"파일 통계 캐시 저장 완료: {file_uuid}")
        except Exception as cache_error:
            logger.warning(f"통계 캐시 저장 실패 (무시됨): {file_uuid}, 오류: {cache_error}")
        
        return stats_data

    async def get_popular_files(self, db: Session, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """
        인기 파일 목록 조회 (최근 N일 기준)
        
        Args:
            db: 데이터베이스 세션
            limit: 조회할 파일 수
            days: 기준일 수
            
        Returns:
            인기 파일 목록
        """
        cache_key = f"{self.cache_config['cache_key_prefix']}popular:{days}d:{limit}"
        
        # Task 8.5: 캐시에서 인기 파일 목록 확인
        cached_popular = await self.cache_service.get(cache_key)
        if cached_popular:
            logger.info(f"인기 파일 목록 캐시 히트: {days}일, {limit}개")
            return cached_popular
        
        # Task 8.5: FileStatistics 뷰에서 인기 파일 조회
        logger.info(f"인기 파일 목록 캐시 미스: {days}일, {limit}개")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        popular_files = db.query(FileStatistics).filter(
            and_(
                FileStatistics.last_viewed >= cutoff_date,
                FileStatistics.is_public == True
            )
        ).order_by(
            desc(FileStatistics.popularity_score)
        ).limit(limit).all()
        
        # Task 8.5: 인기 파일 데이터 구성
        popular_data = []
        for file_stats in popular_files:
            file_data = {
                "file_uuid": file_stats.file_uuid,
                "original_filename": file_stats.original_filename,
                "file_extension": file_stats.file_extension,
                "file_size": file_stats.file_size,
                "total_views": file_stats.total_views,
                "total_downloads": file_stats.total_downloads,
                "popularity_score": float(file_stats.popularity_score),
                "recent_views": file_stats.recent_views,
                "recent_downloads": file_stats.recent_downloads,
                "last_viewed": file_stats.last_viewed.isoformat() if file_stats.last_viewed else None,
                "created_at": file_stats.created_at.isoformat()
            }
            popular_data.append(file_data)
        
        # Task 8.5: 인기 파일 목록 캐시 저장
        try:
            await self.cache_service.set(
                cache_key, 
                popular_data, 
                self.cache_config['popular_files_ttl']
            )
            logger.info(f"인기 파일 목록 캐시 저장 완료: {days}일, {limit}개")
        except Exception as cache_error:
            logger.warning(f"인기 파일 캐시 저장 실패 (무시됨): {cache_error}")
        
        return popular_data

    async def get_trending_files(self, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """
        트렌딩 파일 목록 조회 (최근 24시간 기준)
        
        Args:
            db: 데이터베이스 세션
            limit: 조회할 파일 수
            
        Returns:
            트렌딩 파일 목록
        """
        cache_key = f"{self.cache_config['cache_key_prefix']}trending:{limit}"
        
        # Task 8.5: 캐시에서 트렌딩 파일 목록 확인
        cached_trending = await self.cache_service.get(cache_key)
        if cached_trending:
            logger.info(f"트렌딩 파일 목록 캐시 히트: {limit}개")
            return cached_trending
        
        # Task 8.5: FileStatistics 뷰에서 트렌딩 파일 조회
        logger.info(f"트렌딩 파일 목록 캐시 미스: {limit}개")
        
        cutoff_date = datetime.utcnow() - timedelta(hours=24)
        
        trending_files = db.query(FileStatistics).filter(
            and_(
                FileStatistics.last_viewed >= cutoff_date,
                FileStatistics.is_public == True
            )
        ).order_by(
            desc(FileStatistics.recent_views)
        ).limit(limit).all()
        
        # Task 8.5: 트렌딩 파일 데이터 구성
        trending_data = []
        for file_stats in trending_files:
            file_data = {
                "file_uuid": file_stats.file_uuid,
                "original_filename": file_stats.original_filename,
                "file_extension": file_stats.file_extension,
                "recent_views": file_stats.recent_views,
                "recent_downloads": file_stats.recent_downloads,
                "total_views": file_stats.total_views,
                "total_downloads": file_stats.total_downloads,
                "popularity_score": float(file_stats.popularity_score),
                "last_viewed": file_stats.last_viewed.isoformat() if file_stats.last_viewed else None,
                "created_at": file_stats.created_at.isoformat()
            }
            trending_data.append(file_data)
        
        # Task 8.5: 트렌딩 파일 목록 캐시 저장
        try:
            await self.cache_service.set(
                cache_key, 
                trending_data, 
                self.cache_config['trending_files_ttl']
            )
            logger.info(f"트렌딩 파일 목록 캐시 저장 완료: {limit}개")
        except Exception as cache_error:
            logger.warning(f"트렌딩 파일 캐시 저장 실패 (무시됨): {cache_error}")
        
        return trending_data

    async def invalidate_file_statistics_cache(self, file_uuid: str) -> bool:
        """
        파일 통계 캐시 무효화
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            무효화 성공 여부
        """
        try:
            cache_key = f"{self.cache_config['cache_key_prefix']}file:{file_uuid}"
            await self.cache_service.delete(cache_key)
            
            # Task 8.5: 관련 캐시도 함께 무효화
            await self.cache_service.clear_pattern(f"{self.cache_config['cache_key_prefix']}popular:*")
            await self.cache_service.clear_pattern(f"{self.cache_config['cache_key_prefix']}trending:*")
            
            logger.info(f"파일 통계 캐시 무효화 완료: {file_uuid}")
            return True
        except Exception as e:
            logger.error(f"파일 통계 캐시 무효화 실패: {file_uuid}, 오류: {e}")
            return False

    async def get_system_statistics(self, db: Session) -> Dict[str, Any]:
        """
        시스템 전체 통계 조회
        
        Args:
            db: 데이터베이스 세션
            
        Returns:
            시스템 통계 정보
        """
        cache_key = f"{self.cache_config['cache_key_prefix']}system:overview"
        
        # Task 8.5: 캐시에서 시스템 통계 확인
        cached_system_stats = await self.cache_service.get(cache_key)
        if cached_system_stats:
            return cached_system_stats
        
        # Task 8.5: 시스템 통계 계산
        total_files = db.query(func.count(FileInfo.id)).filter(
            FileInfo.is_deleted == False
        ).scalar()
        
        total_views = db.query(func.count(FileView.id)).scalar()
        total_downloads = db.query(func.count(FileDownload.id)).scalar()
        
        total_size = db.query(func.sum(FileInfo.file_size)).filter(
            FileInfo.is_public == True,
            FileInfo.is_deleted == False
        ).scalar() or 0
        
        # Task 8.5: 최근 24시간 활동
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_views = db.query(func.count(FileView.id)).filter(
            FileView.created_at >= yesterday
        ).scalar()
        
        recent_downloads = db.query(func.count(FileDownload.id)).filter(
            FileDownload.created_at >= yesterday
        ).scalar()
        
        # Task 8.5: 시스템 통계 데이터 구성
        system_stats = {
            "total_files": total_files,
            "total_views": total_views,
            "total_downloads": total_downloads,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "recent_24h_views": recent_views,
            "recent_24h_downloads": recent_downloads,
            "avg_views_per_file": round(total_views / total_files, 2) if total_files > 0 else 0,
            "avg_downloads_per_file": round(total_downloads / total_files, 2) if total_files > 0 else 0,
            "engagement_rate": round(total_downloads / total_views * 100, 2) if total_views > 0 else 0,
            "statistics_updated_at": datetime.utcnow().isoformat(),
            "cached_at": datetime.utcnow().isoformat()
        }
        
        # Task 8.5: 시스템 통계 캐시 저장
        try:
            await self.cache_service.set(
                cache_key, 
                system_stats, 
                self.cache_config['file_stats_ttl']
            )
        except Exception as cache_error:
            logger.warning(f"시스템 통계 캐시 저장 실패 (무시됨): {cache_error}")
        
        return system_stats


# Task 8.5: 전역 통계 서비스 인스턴스
statistics_service = StatisticsService() 