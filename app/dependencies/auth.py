"""
Authentication and authorization dependencies.
Task 7: IP 기반 인증 및 RBAC 시스템 구현
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.ip_auth_middleware import (
    get_client_ip,
)
from app.middleware.ip_auth_middleware import get_current_user as get_ip_user
from app.middleware.ip_auth_middleware import (
    ip_auth_middleware,
    optional_ip_auth,
    require_admin_role,
    require_ip_auth,
    require_permission,
    require_user,
    verify_ip_auth,
)
from app.models.orm_models import AllowedIP, User
from app.services.rbac_service import rbac_service
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# HTTP Bearer 토큰 스키마
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    현재 인증된 사용자 정보 반환 (IP 기반 인증)

    Args:
        request: FastAPI Request 객체
        credentials: HTTP Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        Optional[User]: 사용자 정보 또는 None

    Raises:
        HTTPException: 인증 실패 시
    """
    try:
        # IP 기반 인증 수행
        allowed_ip = await verify_ip_auth(request, credentials, db)

        if not allowed_ip:
            # 인증되지 않은 사용자
            return None

        # IP 기반 사용자 정보 생성
        user = User(
            id=allowed_ip.id,
            username=f"ip_user_{allowed_ip.ip_address}",
            email=f"{allowed_ip.ip_address}@ip.auth",
            role=allowed_ip.role if hasattr(allowed_ip, "role") else "user",
            is_active=True,
        )

        logger.info(f"IP-based user authenticated: {user.username}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IP authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    선택적 사용자 인증 (토큰이 없어도 에러 발생하지 않음)

    Args:
        request: FastAPI Request 객체
        credentials: HTTP Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        Optional[User]: 사용자 정보 또는 None
    """
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


async def require_authenticated_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    인증된 사용자 필수

    Args:
        user: 현재 사용자 정보

    Returns:
        User: 사용자 정보

    Raises:
        HTTPException: 인증되지 않은 경우
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(user: User = Depends(require_authenticated_user)) -> User:
    """
    관리자 권한 확인

    Args:
        user: 현재 사용자 정보

    Returns:
        User: 사용자 정보

    Raises:
        HTTPException: 관리자 권한이 없는 경우
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


def require_file_permission(action: str):
    """
    파일 관련 권한 확인 데코레이터

    Args:
        action: 필요한 액션 (create, read, update, delete)

    Returns:
        권한 확인 함수
    """

    def permission_checker(user: User = Depends(require_authenticated_user)) -> User:
        if not rbac_service.has_permission(user, "file", action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"File {action} permission required",
            )
        return user

    return permission_checker


def require_system_permission(action: str):
    """
    시스템 관련 권한 확인 데코레이터

    Args:
        action: 필요한 액션 (read, update, delete)

    Returns:
        권한 확인 함수
    """

    def permission_checker(user: User = Depends(require_authenticated_user)) -> User:
        if not rbac_service.has_permission(user, "system", action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"System {action} permission required",
            )
        return user

    return permission_checker


def require_audit_permission(action: str):
    """
    감사 로그 관련 권한 확인 데코레이터

    Args:
        action: 필요한 액션 (read, export)

    Returns:
        권한 확인 함수
    """

    def permission_checker(user: User = Depends(require_authenticated_user)) -> User:
        if not rbac_service.has_permission(user, "audit", action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Audit {action} permission required",
            )
        return user

    return permission_checker


# 편의 함수들
require_file_create = require_file_permission("create")
require_file_read = require_file_permission("read")
require_file_update = require_file_permission("update")
require_file_delete = require_file_permission("delete")

require_system_read = require_system_permission("read")
require_system_update = require_system_permission("update")
require_system_delete = require_system_permission("delete")

require_audit_read = require_audit_permission("read")
require_audit_export = require_audit_permission("export")


# IP 관리 함수들
def add_ip_to_whitelist(ip: str):
    """IP를 화이트리스트에 추가"""
    ip_auth_middleware.add_whitelist_ip(ip)
    logger.info(f"Added IP to whitelist: {ip}")


def add_ip_to_blacklist(ip: str):
    """IP를 블랙리스트에 추가"""
    ip_auth_middleware.add_blacklist_ip(ip)
    logger.info(f"Added IP to blacklist: {ip}")


def is_ip_allowed(ip: str) -> bool:
    """IP가 허용되는지 확인"""
    return ip_auth_middleware.is_ip_allowed(ip)
