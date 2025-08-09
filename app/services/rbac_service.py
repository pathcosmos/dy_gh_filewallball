"""
RBAC service - 단순화된 버전
"""

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RBACService:
    """RBAC 서비스 (단순화된 버전)"""
    
    def has_permission(self, user, resource, action):
        """권한 확인 (일단 모든 권한 허용)"""
        return True


# 싱글톤 인스턴스
rbac_service = RBACService()