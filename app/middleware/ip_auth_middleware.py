"""
IP 기반 인증 미들웨어
Task 7: IP 기반 인증 및 RBAC 시스템 구현
"""

import ipaddress
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm_models import AllowedIP, User
from app.services.ip_auth_service import IPAuthService
from app.services.rbac_service import RBACService
from app.utils.security_utils import hash_key, sanitize_ip_address

# 전역 서비스 인스턴스
rbac_service = RBACService()
security = HTTPBearer(auto_error=False)


class IPAuthMiddleware:
    """IP 기반 인증 미들웨어"""

    def __init__(self):
        self.ip_whitelist: List[str] = []
        self.ip_blacklist: List[str] = []
        self.cidr_whitelist: List[str] = []
        self.cidr_blacklist: List[str] = []

    def add_whitelist_ip(self, ip: str):
        """화이트리스트 IP 추가"""
        if "/" in ip:  # CIDR 표기법
            self.cidr_whitelist.append(ip)
        else:
            self.ip_whitelist.append(ip)

    def add_blacklist_ip(self, ip: str):
        """블랙리스트 IP 추가"""
        if "/" in ip:  # CIDR 표기법
            self.cidr_blacklist.append(ip)
        else:
            self.ip_blacklist.append(ip)

    def is_ip_allowed(self, ip: str) -> bool:
        """IP가 허용되는지 확인"""
        # 블랙리스트 확인
        if self._is_ip_in_list(ip, self.ip_blacklist, self.cidr_blacklist):
            return False

        # 화이트리스트가 비어있으면 모든 IP 허용
        if not self.ip_whitelist and not self.cidr_whitelist:
            return True

        # 화이트리스트 확인
        return self._is_ip_in_list(ip, self.ip_whitelist, self.cidr_whitelist)

    def _is_ip_in_list(self, ip: str, ip_list: List[str], cidr_list: List[str]) -> bool:
        """IP가 리스트에 포함되는지 확인"""
        # 정확한 IP 매칭
        if ip in ip_list:
            return True

        # CIDR 범위 확인
        try:
            ip_obj = ipaddress.ip_address(ip)
            for cidr in cidr_list:
                network = ipaddress.ip_network(cidr, strict=False)
                if ip_obj in network:
                    return True
        except ValueError:
            pass

        return False


# 전역 미들웨어 인스턴스
ip_auth_middleware = IPAuthMiddleware()


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 주소 추출"""
    # X-Forwarded-For 헤더 확인 (프록시 환경)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 첫 번째 IP 주소 사용 (클라이언트 IP)
        return forwarded_for.split(",")[0].strip()

    # X-Real-IP 헤더 확인
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 기본 클라이언트 IP
    return request.client.host


async def verify_ip_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[AllowedIP]:
    """IP 기반 인증 검증"""
    client_ip = get_client_ip(request)
    client_ip = sanitize_ip_address(client_ip)

    # 기본 IP 필터링
    if not ip_auth_middleware.is_ip_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="IP 주소가 허용되지 않습니다"
        )

    # API 키가 제공되지 않은 경우 기본 인증만 수행
    if not credentials:
        return None

    # IP 인증 서비스로 검증
    ip_auth_service = IPAuthService(db)
    allowed_ip = ip_auth_service.verify_ip_and_key(client_ip, credentials.credentials)

    if not allowed_ip:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 실패: IP 또는 키가 유효하지 않습니다",
        )

    # Rate limiting 확인
    if not ip_auth_service.check_rate_limit(client_ip, credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="요청 한도를 초과했습니다",
        )

    return allowed_ip


async def require_ip_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AllowedIP:
    """IP 기반 인증 필수 (API 키 필요)"""
    allowed_ip = await verify_ip_auth(request, credentials, db)
    if not allowed_ip:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API 키가 필요합니다"
        )
    return allowed_ip


async def optional_ip_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[AllowedIP]:
    """선택적 IP 기반 인증 (API 키 선택사항)"""
    return await verify_ip_auth(request, credentials, db)


def get_current_user(
    allowed_ip: Optional[AllowedIP] = Depends(optional_ip_auth),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """현재 사용자 정보 반환 (IP 인증 기반)"""
    if not allowed_ip:
        return None

    # IP 기반 사용자 정보 생성 또는 조회
    # 실제 구현에서는 IP와 연결된 사용자 정보를 DB에서 조회
    user = User(
        id=allowed_ip.id,
        username=f"ip_user_{allowed_ip.ip_address}",
        email=f"{allowed_ip.ip_address}@ip.auth",
        role="user",  # 기본 역할
        is_active=True,
    )

    return user


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    """사용자 인증 필수"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다"
        )
    return user


def require_admin_role(user: User = Depends(require_user)) -> User:
    """관리자 역할 필수"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다"
        )
    return user


def require_permission(resource_type: str, action: str):
    """특정 권한 필수 데코레이터"""

    def permission_checker(user: User = Depends(require_user)) -> User:
        if not rbac_service.has_permission(user, resource_type, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{resource_type}에 대한 {action} 권한이 없습니다",
            )
        return user

    return permission_checker


# 기본 IP 화이트리스트/블랙리스트 설정
def setup_default_ip_lists():
    """기본 IP 리스트 설정"""
    # 예시: 특정 IP 범위 허용
    ip_auth_middleware.add_whitelist_ip("127.0.0.1")  # localhost
    ip_auth_middleware.add_whitelist_ip("192.168.1.0/24")  # 로컬 네트워크
    ip_auth_middleware.add_whitelist_ip("10.0.0.0/8")  # 프라이빗 네트워크

    # 예시: 차단할 IP
    ip_auth_middleware.add_blacklist_ip("0.0.0.0")
    ip_auth_middleware.add_blacklist_ip("255.255.255.255")


# 애플리케이션 시작 시 기본 설정
setup_default_ip_lists()
