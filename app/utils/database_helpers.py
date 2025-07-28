"""
Database Helper Functions and Utilities
고급 데이터베이스 작업을 위한 헬퍼 함수들과 유틸리티
"""

import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text, func, or_, desc, asc
from sqlalchemy.orm import Session, joinedload
from contextlib import contextmanager

from app.models.orm_models import (
    FileInfo, FileCategory, FileTag, FileTagRelation, FileView, 
    FileDownload, FileUpload, SystemSetting
)

logger = logging.getLogger(__name__)


class DatabaseHelpers:
    """데이터베이스 헬퍼 클래스"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    # ==================== 파일 관리 헬퍼 함수들 ====================
    
    def create_file_with_metadata(
        self, file_data: Dict[str, Any], 
        tags: Optional[List[str]] = None
    ) -> Optional[FileInfo]:
        """파일 정보 생성 및 메타데이터 설정"""
        try:
            # UUID 생성
            if 'file_uuid' not in file_data:
                file_data['file_uuid'] = str(uuid.uuid4())
            
            # 파일 해시 생성 (있는 경우)
            if ('file_hash' not in file_data and 
                'file_content' in file_data):
                file_data['file_hash'] = self._generate_file_hash(
                    file_data['file_content']
                )
                del file_data['file_content']  # 메모리에서 제거
            
            # 파일 정보 생성
            file_info = FileInfo(**file_data)
            self.db_session.add(file_info)
            self.db_session.flush()  # ID 생성
            
            # 태그 추가
            if tags:
                self.add_tags_to_file(file_info.id, tags)
            
            self.db_session.commit()
            return file_info
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"파일 생성 실패: {e}")
            return None
    
    def _generate_file_hash(self, content: bytes) -> str:
        """파일 내용으로부터 SHA-256 해시 생성"""
        return hashlib.sha256(content).hexdigest()
    
    def find_file_by_hash(self, file_hash: str) -> Optional[FileInfo]:
        """파일 해시로 중복 파일 검색"""
        try:
            return self.db_session.query(FileInfo).filter(
                FileInfo.file_hash == file_hash,
                not FileInfo.is_deleted
            ).first()
        except Exception as e:
            logger.error(f"해시로 파일 검색 실패: {e}")
            return None
    
    def search_files(
        self, 
        query: Optional[str] = None,
        extension: Optional[str] = None,
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        is_public: Optional[bool] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'created_at',
        order_direction: str = 'desc'
    ) -> Tuple[List[FileInfo], int]:
        """고급 파일 검색"""
        try:
            # 기본 쿼리
            query_obj = self.db_session.query(FileInfo).filter(FileInfo.is_deleted == False)
            
            # 파일명 검색
            if query:
                query_obj = query_obj.filter(
                    or_(
                        FileInfo.original_filename.contains(query),
                        FileInfo.stored_filename.contains(query)
                    )
                )
            
            # 확장자 필터
            if extension:
                query_obj = query_obj.filter(FileInfo.file_extension == extension)
            
            # 카테고리 필터
            if category_id:
                query_obj = query_obj.filter(FileInfo.file_category_id == category_id)
            
            # 태그 필터
            if tags:
                query_obj = query_obj.join(FileTagRelation).join(FileTag).filter(
                    FileTag.tag_name.in_(tags),
                    FileTag.is_active == True
                )
            
            # 공개 상태 필터
            if is_public is not None:
                query_obj = query_obj.filter(FileInfo.is_public == is_public)
            
            # 파일 크기 필터
            if min_size:
                query_obj = query_obj.filter(FileInfo.file_size >= min_size)
            if max_size:
                query_obj = query_obj.filter(FileInfo.file_size <= max_size)
            
            # 날짜 범위 필터
            if date_from:
                query_obj = query_obj.filter(FileInfo.created_at >= date_from)
            if date_to:
                query_obj = query_obj.filter(FileInfo.created_at <= date_to)
            
            # 정렬
            order_column = getattr(FileInfo, order_by, FileInfo.created_at)
            if order_direction.lower() == 'desc':
                query_obj = query_obj.order_by(desc(order_column))
            else:
                query_obj = query_obj.order_by(asc(order_column))
            
            # 전체 개수 조회
            total_count = query_obj.count()
            
            # 페이지네이션
            files = query_obj.offset(offset).limit(limit).all()
            
            return files, total_count
            
        except Exception as e:
            logger.error(f"파일 검색 실패: {e}")
            return [], 0
    
    def get_file_with_relations(self, file_uuid: str) -> Optional[FileInfo]:
        """관계 데이터와 함께 파일 정보 조회"""
        try:
            return self.db_session.query(FileInfo).options(
                joinedload(FileInfo.category),
                joinedload(FileInfo.tags),
                joinedload(FileInfo.uploads)
            ).filter(
                FileInfo.file_uuid == file_uuid,
                FileInfo.is_deleted == False
            ).first()
        except Exception as e:
            logger.error(f"파일 관계 조회 실패: {e}")
            return None
    
    # ==================== 태그 관리 헬퍼 함수들 ====================
    
    def add_tags_to_file(self, file_id: int, tag_names: List[str]) -> bool:
        """파일에 태그 일괄 추가 (개선된 버전)"""
        try:
            for tag_name in tag_names:
                # 태그가 존재하는지 확인
                tag = self.db_session.query(FileTag).filter(
                    FileTag.tag_name == tag_name
                ).first()
                
                if not tag:
                    tag = FileTag(tag_name=tag_name)
                    self.db_session.add(tag)
                    self.db_session.flush()
                
                # 관계가 이미 존재하는지 확인
                existing_relation = self.db_session.query(FileTagRelation).filter(
                    FileTagRelation.file_id == file_id,
                    FileTagRelation.tag_id == tag.id
                ).first()
                
                if not existing_relation:
                    relation = FileTagRelation(file_id=file_id, tag_id=tag.id)
                    self.db_session.add(relation)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"태그 추가 실패: {e}")
            return False
    
    def remove_tags_from_file(self, file_id: int, tag_names: List[str]) -> bool:
        """파일에서 태그 제거 (개선된 버전)"""
        try:
            for tag_name in tag_names:
                tag = self.db_session.query(FileTag).filter(
                    FileTag.tag_name == tag_name
                ).first()
                
                if tag:
                    relation = self.db_session.query(FileTagRelation).filter(
                        FileTagRelation.file_id == file_id,
                        FileTagRelation.tag_id == tag.id
                    ).first()
                    
                    if relation:
                        self.db_session.delete(relation)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"태그 제거 실패: {e}")
            return False
    
    def get_files_by_tags(self, tag_names: List[str], limit: int = 100) -> List[FileInfo]:
        """태그로 파일 검색"""
        try:
            return self.db_session.query(FileInfo).join(FileTagRelation).join(FileTag).filter(
                FileTag.tag_name.in_(tag_names),
                FileTag.is_active == True,
                FileInfo.is_deleted == False
            ).distinct().limit(limit).all()
        except Exception as e:
            logger.error(f"태그로 파일 검색 실패: {e}")
            return []
    
    def get_popular_tags(self, limit: int = 10) -> List[Dict[str, Any]]:
        """인기 태그 조회"""
        try:
            result = self.db_session.query(
                FileTag.tag_name,
                func.count(FileTagRelation.file_id).label('file_count')
            ).join(FileTagRelation).filter(
                FileTag.is_active == True
            ).group_by(FileTag.id).order_by(
                desc('file_count')
            ).limit(limit).all()
            
            return [
                {'tag_name': row[0], 'file_count': row[1]} 
                for row in result
            ]
        except Exception as e:
            logger.error(f"인기 태그 조회 실패: {e}")
            return []
    
    # ==================== 통계 및 분석 헬퍼 함수들 ====================
    
    def get_file_statistics(self) -> Dict[str, Any]:
        """파일 통계 정보 조회"""
        try:
            # 전체 파일 수
            total_files = self.db_session.query(func.count(FileInfo.id)).filter(
                FileInfo.is_deleted == False
            ).scalar()
            
            # 전체 파일 크기
            total_size = self.db_session.query(func.sum(FileInfo.file_size)).filter(
                FileInfo.is_deleted == False
            ).scalar() or 0
            
            # 카테고리별 통계
            category_stats = self.db_session.query(
                FileCategory.name,
                func.count(FileInfo.id).label('file_count'),
                func.sum(FileInfo.file_size).label('total_size')
            ).outerjoin(FileInfo).filter(
                FileInfo.is_deleted == False
            ).group_by(FileCategory.id).all()
            
            # 확장자별 통계
            extension_stats = self.db_session.query(
                FileInfo.file_extension,
                func.count(FileInfo.id).label('file_count'),
                func.sum(FileInfo.file_size).label('total_size')
            ).filter(
                FileInfo.is_deleted == False
            ).group_by(FileInfo.file_extension).order_by(
                desc('file_count')
            ).limit(10).all()
            
            # 최근 업로드
            recent_uploads = self.db_session.query(FileInfo).filter(
                FileInfo.is_deleted == False
            ).order_by(desc(FileInfo.created_at)).limit(5).all()
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'category_stats': [
                    {
                        'name': row[0] or '미분류',
                        'file_count': row[1],
                        'total_size': row[2] or 0
                    } for row in category_stats
                ],
                'extension_stats': [
                    {
                        'extension': row[0],
                        'file_count': row[1],
                        'total_size': row[2] or 0
                    } for row in extension_stats
                ],
                'recent_uploads': recent_uploads
            }
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}
    
    def get_upload_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """업로드 트렌드 조회"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            result = self.db_session.query(
                func.date(FileInfo.created_at).label('date'),
                func.count(FileInfo.id).label('upload_count'),
                func.sum(FileInfo.file_size).label('total_size')
            ).filter(
                FileInfo.created_at >= start_date,
                FileInfo.is_deleted == False
            ).group_by(
                func.date(FileInfo.created_at)
            ).order_by(
                asc('date')
            ).all()
            
            return [
                {
                    'date': row[0].isoformat(),
                    'upload_count': row[1],
                    'total_size': row[2] or 0
                } for row in result
            ]
            
        except Exception as e:
            logger.error(f"업로드 트렌드 조회 실패: {e}")
            return []
    
    def get_file_activity_stats(self, file_uuid: str, days: int = 30) -> Dict[str, Any]:
        """파일 활동 통계"""
        try:
            file_info = self.db_session.query(FileInfo).filter(
                FileInfo.file_uuid == file_uuid
            ).first()
            
            if not file_info:
                return {}
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 조회 통계
            view_count = self.db_session.query(func.count(FileView.id)).filter(
                FileView.file_id == file_info.id,
                FileView.created_at >= start_date
            ).scalar()
            
            # 다운로드 통계
            download_count = self.db_session.query(func.count(FileDownload.id)).filter(
                FileDownload.file_id == file_info.id,
                FileDownload.created_at >= start_date
            ).scalar()
            
            # 최근 활동
            recent_views = self.db_session.query(FileView).filter(
                FileView.file_id == file_info.id
            ).order_by(desc(FileView.created_at)).limit(10).all()
            
            recent_downloads = self.db_session.query(FileDownload).filter(
                FileDownload.file_id == file_info.id
            ).order_by(desc(FileDownload.created_at)).limit(10).all()
            
            return {
                'file_info': file_info,
                'view_count': view_count,
                'download_count': download_count,
                'recent_views': recent_views,
                'recent_downloads': recent_downloads
            }
            
        except Exception as e:
            logger.error(f"파일 활동 통계 조회 실패: {e}")
            return {}
    
    # ==================== 배치 처리 헬퍼 함수들 ====================
    
    def bulk_insert_files(self, files_data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """대량 파일 정보 삽입 (개선된 버전)"""
        success_count = 0
        error_count = 0
        
        try:
            for file_data in files_data:
                try:
                    # UUID 생성
                    if 'file_uuid' not in file_data:
                        file_data['file_uuid'] = str(uuid.uuid4())
                    
                    file_info = FileInfo(**file_data)
                    self.db_session.add(file_info)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"파일 삽입 실패: {e}")
                    error_count += 1
                    continue
            
            self.db_session.commit()
            return success_count, error_count
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"대량 삽입 실패: {e}")
            return 0, len(files_data)
    
    def bulk_update_files(self, updates: List[Dict[str, Any]]) -> Tuple[int, int]:
        """대량 파일 정보 업데이트"""
        success_count = 0
        error_count = 0
        
        try:
            for update_data in updates:
                try:
                    file_uuid = update_data.pop('file_uuid')
                    file_info = self.db_session.query(FileInfo).filter(
                        FileInfo.file_uuid == file_uuid
                    ).first()
                    
                    if file_info:
                        for key, value in update_data.items():
                            if hasattr(file_info, key):
                                setattr(file_info, key, value)
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"파일 업데이트 실패: {e}")
                    error_count += 1
                    continue
            
            self.db_session.commit()
            return success_count, error_count
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"대량 업데이트 실패: {e}")
            return 0, len(updates)
    
    # ==================== 시스템 설정 헬퍼 함수들 ====================
    
    def get_system_setting(self, key: str, default: Any = None) -> Any:
        """시스템 설정 조회"""
        try:
            setting = self.db_session.query(SystemSetting).filter(
                SystemSetting.setting_key == key
            ).first()
            
            if setting:
                # 타입에 따른 값 변환
                if setting.setting_type == 'integer':
                    return int(setting.setting_value) if setting.setting_value else default
                elif setting.setting_type == 'boolean':
                    return setting.setting_value.lower() == 'true' if setting.setting_value else default
                elif setting.setting_type == 'json':
                    import json
                    return json.loads(setting.setting_value) if setting.setting_value else default
                else:
                    return setting.setting_value
            
            return default
            
        except Exception as e:
            logger.error(f"시스템 설정 조회 실패: {e}")
            return default
    
    def set_system_setting(self, key: str, value: Any, setting_type: str = 'string', 
                          description: Optional[str] = None) -> bool:
        """시스템 설정 저장"""
        try:
            # 타입에 따른 값 변환
            if setting_type == 'json':
                import json
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            setting = self.db_session.query(SystemSetting).filter(
                SystemSetting.setting_key == key
            ).first()
            
            if setting:
                setting.setting_value = value_str
                setting.setting_type = setting_type
                setting.updated_at = datetime.utcnow()
                if description:
                    setting.description = description
            else:
                setting = SystemSetting(
                    setting_key=key,
                    setting_value=value_str,
                    setting_type=setting_type,
                    description=description
                )
                self.db_session.add(setting)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"시스템 설정 저장 실패: {e}")
            return False
    
    # ==================== 유틸리티 함수들 ====================
    
    @contextmanager
    def transaction(self):
        """트랜잭션 컨텍스트 매니저"""
        try:
            yield self.db_session
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """오래된 로그 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 오래된 조회 로그 삭제
            view_deleted = self.db_session.query(FileView).filter(
                FileView.created_at < cutoff_date
            ).delete()
            
            # 오래된 다운로드 로그 삭제
            download_deleted = self.db_session.query(FileDownload).filter(
                FileDownload.created_at < cutoff_date
            ).delete()
            
            # 오래된 업로드 로그 삭제
            upload_deleted = self.db_session.query(FileUpload).filter(
                FileUpload.created_at < cutoff_date
            ).delete()
            
            self.db_session.commit()
            return view_deleted + download_deleted + upload_deleted
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"로그 정리 실패: {e}")
            return 0
    
    def get_database_size_info(self) -> Dict[str, Any]:
        """데이터베이스 크기 정보 조회"""
        try:
            # 테이블별 크기 정보
            tables = ['files', 'file_views', 'file_downloads', 'file_uploads', 
                     'file_tags', 'file_tag_relations', 'file_categories', 'system_settings']
            
            size_info = {}
            for table in tables:
                result = self.db_session.execute(text(f"""
                    SELECT 
                        TABLE_ROWS,
                        DATA_LENGTH,
                        INDEX_LENGTH,
                        (DATA_LENGTH + INDEX_LENGTH) as TOTAL_LENGTH
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = '{table}'
                """)).fetchone()
                
                if result:
                    size_info[table] = {
                        'rows': result[0] or 0,
                        'data_size': result[1] or 0,
                        'index_size': result[2] or 0,
                        'total_size': result[3] or 0
                    }
            
            return size_info
            
        except Exception as e:
            logger.error(f"데이터베이스 크기 정보 조회 실패: {e}")
            return {}


# 편의 함수들
def generate_file_uuid() -> str:
    """UUID v4 생성"""
    return str(uuid.uuid4())


def calculate_file_hash(content: bytes) -> str:
    """파일 내용으로부터 SHA-256 해시 계산"""
    return hashlib.sha256(content).hexdigest()


def format_file_size(size_bytes: int) -> str:
    """파일 크기를 사람이 읽기 쉬운 형태로 변환"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB" 