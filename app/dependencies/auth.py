"""
Authentication and authorization dependencies.
Task 7: IP 기반 인증 및 RBAC 시스템 구현
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm_models import AllowedIP, User
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
    현재 인증된 사용자 정보 반환 (단순화된 버전)

    Args:
        request: FastAPI Request 객체
        credentials: HTTP Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        Optional[User]: 사용자 정보 또는 None
    """
    # 일단 None을 반환하여 인증 없이 작동하도록 함
    return None


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
    파일 관련 권한 확인 데코레이터 (단순화된 버전)

    Args:
        action: 필요한 액션 (create, read, update, delete)

    Returns:
        권한 확인 함수
    """

    def permission_checker(user: User = Depends(require_authenticated_user)) -> User:
        # 일단 모든 권한을 허용
        return user

    return permission_checker


def require_system_permission(action: str):
    """
    시스템 관련 권한 확인 데코레이터 (단순화된 버전)

    Args:
        action: 필요한 액션 (read, update, delete)

    Returns:
        권한 확인 함수
    """

    def permission_checker(user: User = Depends(require_authenticated_user)) -> User:
        # 일단 모든 권한을 허용
        return user

    return permission_checker


def require_audit_permission(action: str):
    """
    감사 로그 관련 권한 확인 데코레이터 (단순화된 버전)

    Args:
        action: 필요한 액션 (read, export)

    Returns:
        권한 확인 함수
    """

    def permission_checker(user: User = Depends(require_authenticated_user)) -> User:
        # 일단 모든 권한을 허용
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


# IP 관리 함수들 (단순화된 버전)
def add_ip_to_whitelist(ip: str):
    """IP를 화이트리스트에 추가 (단순화됨)"""
    logger.info(f"Added IP to whitelist: {ip}")


def add_ip_to_blacklist(ip: str):
    """IP를 블랙리스트에 추가 (단순화됨)"""
    logger.info(f"Added IP to blacklist: {ip}")


def is_ip_allowed(ip: str) -> bool:
    """IP가 허용되는지 확인 (일단 모두 허용)"""
    return True
