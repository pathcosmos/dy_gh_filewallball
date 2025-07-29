"""
Role-Based Access Control (RBAC) service for file management.
Task 12.5: 역할 기반 접근 제어(RBAC) 및 감사 로그 구현
"""

import json
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.orm_models import User, FileInfo, AuditLog
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RBACService:
    """역할 기반 접근 제어 서비스"""
    
    def __init__(self):
        # 권한 정의
        self.permissions = {
            'admin': {
                'file': ['create', 'read', 'update', 'delete', 'permanent_delete'],
                'user': ['create', 'read', 'update', 'delete'],
                'system': ['read', 'update', 'delete'],
                'audit': ['read', 'export']
            },
            'moderator': {
                'file': ['create', 'read', 'update', 'delete'],
                'user': ['read'],
                'system': ['read'],
                'audit': ['read']
            },
            'user': {
                'file': ['create', 'read', 'update', 'delete'],
                'user': ['read'],
                'system': ['read'],
                'audit': []
            }
        }
        
        # 파일 접근 권한 규칙
        self.file_access_rules = {
            'read': {
                'admin': 'all',  # 모든 파일 접근 가능
                'moderator': 'all',  # 모든 파일 접근 가능
                'user': 'own_or_public'  # 자신의 파일 또는 공개 파일만
            },
            'update': {
                'admin': 'all',
                'moderator': 'all',
                'user': 'own_only'  # 자신의 파일만
            },
            'delete': {
                'admin': 'all',
                'moderator': 'all',
                'user': 'own_only'
            },
            'permanent_delete': {
                'admin': 'all',
                'moderator': 'none',
                'user': 'none'
            }
        }
    
    def has_permission(self, user: User, resource_type: str, action: str) -> bool:
        """사용자가 특정 리소스에 대한 특정 액션 권한을 가지고 있는지 확인"""
        if not user or not user.is_active:
            return False
        
        user_role = user.role
        if user_role not in self.permissions:
            return False
        
        resource_permissions = self.permissions.get(user_role, {})
        allowed_actions = resource_permissions.get(resource_type, [])
        
        return action in allowed_actions
    
    def can_access_file(self, user: User, file_info: FileInfo, action: str) -> Tuple[bool, str]:
        """사용자가 특정 파일에 대한 특정 액션을 수행할 수 있는지 확인"""
        if not user or not user.is_active:
            return False, "사용자가 비활성화되었습니다"
        
        if not file_info:
            return False, "파일이 존재하지 않습니다"
        
        user_role = user.role
        if user_role not in self.file_access_rules:
            return False, "알 수 없는 사용자 역할입니다"
        
        action_rules = self.file_access_rules.get(action, {})
        access_level = action_rules.get(user_role, 'none')
        
        if access_level == 'none':
            return False, f"{action} 권한이 없습니다"
        
        if access_level == 'all':
            return True, "관리자 권한으로 접근 가능"
        
        # 자신의 파일인지 확인
        is_owner = file_info.owner_id == user.id
        
        if access_level == 'own_only':
            if is_owner:
                return True, "파일 소유자로 접근 가능"
            else:
                return False, "자신의 파일만 수정/삭제할 수 있습니다"
        
        if access_level == 'own_or_public':
            if is_owner:
                return True, "파일 소유자로 접근 가능"
            elif file_info.is_public:
                return True, "공개 파일로 접근 가능"
            else:
                return False, "비공개 파일에 대한 접근 권한이 없습니다"
        
        return False, "접근 권한이 없습니다"
    
    def get_user_files_query(self, db: Session, user: User, include_public: bool = True):
        """사용자가 접근할 수 있는 파일들의 쿼리 생성"""
        if not user or not user.is_active:
            return db.query(FileInfo).filter(FileInfo.id == 0)  # 빈 결과
        
        if user.role in ['admin', 'moderator']:
            # 관리자/모더레이터는 모든 파일 접근 가능
            query = db.query(FileInfo).filter(FileInfo.is_deleted == False)
        else:
            # 일반 사용자는 자신의 파일과 공개 파일만 접근 가능
            conditions = [FileInfo.is_deleted == False]
            
            # 자신의 파일
            conditions.append(FileInfo.owner_id == user.id)
            
            # 공개 파일 (include_public이 True인 경우)
            if include_public:
                conditions.append(FileInfo.is_public == True)
            
            query = db.query(FileInfo).filter(or_(*conditions))
        
        return query
    
    def validate_file_ownership(self, user: User, file_info: FileInfo) -> bool:
        """파일 소유권 검증"""
        if not user or not file_info:
            return False
        
        # 관리자/모더레이터는 모든 파일에 대한 권한
        if user.role in ['admin', 'moderator']:
            return True
        
        # 일반 사용자는 자신의 파일만
        return file_info.owner_id == user.id
    
    def get_user_permissions(self, user: User) -> Dict[str, List[str]]:
        """사용자의 모든 권한 반환"""
        if not user or not user.is_active:
            return {}
        
        return self.permissions.get(user.role, {})
    
    def log_audit_event(
        self, 
        db: Session, 
        user: Optional[User], 
        action: str, 
        resource_type: str, 
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        details: Optional[Dict] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        request_path: str = '',
        request_method: str = '',
        response_code: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        ip_address: str = '',
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditLog:
        """감사 로그 기록"""
        try:
            audit_log = AuditLog(
                user_id=user.id if user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                details=json.dumps(details) if details else None,
                status=status,
                error_message=error_message,
                request_path=request_path,
                request_method=request_method,
                response_code=response_code,
                processing_time_ms=processing_time_ms,
                session_id=session_id
            )
            
            db.add(audit_log)
            db.commit()
            
            logger.info(
                f"Audit log created: {action} on {resource_type} "
                f"by user {user.username if user else 'anonymous'} "
                f"from {ip_address}"
            )
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            db.rollback()
            return None
    
    def get_audit_logs(
        self, 
        db: Session, 
        user: User, 
        filters: Optional[Dict] = None,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[AuditLog], int]:
        """감사 로그 조회 (권한 기반)"""
        if not self.has_permission(user, 'audit', 'read'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="감사 로그 조회 권한이 없습니다"
            )
        
        query = db.query(AuditLog)
        
        # 필터 적용
        if filters:
            if filters.get('user_id'):
                query = query.filter(AuditLog.user_id == filters['user_id'])
            if filters.get('action'):
                query = query.filter(AuditLog.action == filters['action'])
            if filters.get('resource_type'):
                query = query.filter(AuditLog.resource_type == filters['resource_type'])
            if filters.get('status'):
                query = query.filter(AuditLog.status == filters['status'])
            if filters.get('date_from'):
                query = query.filter(AuditLog.created_at >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(AuditLog.created_at <= filters['date_to'])
            if filters.get('ip_address'):
                query = query.filter(AuditLog.ip_address == filters['ip_address'])
        
        # 일반 사용자는 자신의 로그만 조회 가능
        if user.role == 'user':
            query = query.filter(AuditLog.user_id == user.id)
        
        # 정렬 (최신순)
        query = query.order_by(AuditLog.created_at.desc())
        
        # 전체 개수
        total = query.count()
        
        # 페이지네이션
        offset = (page - 1) * size
        logs = query.offset(offset).limit(size).all()
        
        return logs, total


# 전역 인스턴스
rbac_service = RBACService() 