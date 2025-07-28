"""
Authentication and authorization dependencies.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# HTTP Bearer 토큰 스키마
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    현재 인증된 사용자 정보 반환
    
    Args:
        credentials: HTTP Bearer 토큰
        
    Returns:
        dict: 사용자 정보
        
    Raises:
        HTTPException: 인증 실패 시
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # TODO: JWT 토큰 검증 및 사용자 정보 추출
        # 현재는 임시 구현
        token = credentials.credentials
        
        # 토큰 검증 로직 (실제로는 JWT 검증 필요)
        if not token or token == "invalid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 임시 사용자 정보 (실제로는 데이터베이스에서 조회)
        user = {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin"
        }
        
        logger.info(f"User authenticated: {user['username']}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    선택적 사용자 인증 (토큰이 없어도 에러 발생하지 않음)
    
    Args:
        credentials: HTTP Bearer 토큰
        
    Returns:
        Optional[dict]: 사용자 정보 또는 None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    관리자 권한 확인
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        dict: 사용자 정보
        
    Raises:
        HTTPException: 관리자 권한이 없는 경우
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user 