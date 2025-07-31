"""
IP 기반 암호화 키 인증 서비스
"""

import hashlib
import hmac
import ipaddress
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.orm_models import AllowedIP, IPAuthLog, IPRateLimit
from app.utils.security_utils import generate_encryption_key, hash_key


class IPAuthService:
    """IP 기반 인증 서비스"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.security = HTTPBearer()

    def get_client_ip(self, request: Request) -> str:
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

    def verify_ip_and_key(self, client_ip: str, api_key: str) -> Optional[AllowedIP]:
        """IP 주소와 암호화 키 검증"""
        try:
            # API 키 해시 생성
            key_hash = hash_key(api_key)

            # 활성화된 IP 허용 목록에서 검색
            allowed_ip = (
                self.db.query(AllowedIP)
                .filter(
                    and_(
                        AllowedIP.is_active == True,
                        AllowedIP.key_hash == key_hash,
                        or_(
                            AllowedIP.ip_address == client_ip,
                            AllowedIP.ip_range.isnot(None),
                        ),
                    )
                )
                .first()
            )

            if not allowed_ip:
                return None

            # IP 범위가 있는 경우 CIDR 검증
            if allowed_ip.ip_range:
                if not self._is_ip_in_range(client_ip, allowed_ip.ip_range):
                    return None

            # 만료일 확인
            if allowed_ip.expires_at and allowed_ip.expires_at < datetime.utcnow():
                return None

            return allowed_ip

        except Exception as e:
            self._log_auth_event(
                client_ip, api_key, "auth_failed", error_message=f"검증 오류: {str(e)}"
            )
            return None

    def _is_ip_in_range(self, ip_address: str, ip_range: str) -> bool:
        """IP 주소가 CIDR 범위에 포함되는지 확인"""
        try:
            ip = ipaddress.ip_address(ip_address)
            network = ipaddress.ip_network(ip_range, strict=False)
            return ip in network
        except ValueError:
            return False

    def check_rate_limit(self, client_ip: str, api_key: str) -> bool:
        """Rate limiting 확인"""
        try:
            key_hash = hash_key(api_key)
            current_time = datetime.utcnow()
            window_start = current_time.replace(minute=0, second=0, microsecond=0)

            # 현재 시간대의 요청 수 확인
            rate_limit = (
                self.db.query(IPRateLimit)
                .filter(
                    and_(
                        IPRateLimit.ip_address == client_ip,
                        IPRateLimit.api_key_hash == key_hash,
                        IPRateLimit.window_start == window_start,
                    )
                )
                .first()
            )

            if not rate_limit:
                # 새로운 시간대 시작
                rate_limit = IPRateLimit(
                    ip_address=client_ip,
                    api_key_hash=key_hash,
                    window_start=window_start,
                    request_count=1,
                    last_request_at=current_time,
                )
                self.db.add(rate_limit)
            else:
                # 기존 시간대 업데이트
                rate_limit.request_count += 1
                rate_limit.last_request_at = current_time

            # 허용된 IP 정보 조회
            allowed_ip = (
                self.db.query(AllowedIP)
                .filter(
                    and_(
                        AllowedIP.is_active == True,
                        AllowedIP.key_hash == key_hash,
                        or_(
                            AllowedIP.ip_address == client_ip,
                            AllowedIP.ip_range.isnot(None),
                        ),
                    )
                )
                .first()
            )

            if allowed_ip and allowed_ip.ip_range:
                if not self._is_ip_in_range(client_ip, allowed_ip.ip_range):
                    return False

            # 요청 수 제한 확인
            max_requests = allowed_ip.max_uploads_per_hour if allowed_ip else 100
            is_limited = rate_limit.request_count > max_requests

            self.db.commit()
            return not is_limited

        except Exception as e:
            self.db.rollback()
            self._log_auth_event(
                client_ip,
                api_key,
                "rate_limit_error",
                error_message=f"Rate limit 오류: {str(e)}",
            )
            return False

    def log_auth_event(
        self,
        client_ip: str,
        api_key: str,
        action: str,
        file_uuid: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_code: Optional[int] = None,
        error_message: Optional[str] = None,
        request_size: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
    ) -> None:
        """인증 이벤트 로깅"""
        try:
            key_hash = hash_key(api_key) if api_key else None

            # 허용된 IP 정보 조회
            allowed_ip_id = None
            if key_hash:
                allowed_ip = (
                    self.db.query(AllowedIP)
                    .filter(
                        and_(
                            AllowedIP.is_active == True, AllowedIP.key_hash == key_hash
                        )
                    )
                    .first()
                )
                if allowed_ip:
                    allowed_ip_id = allowed_ip.id

            # 로그 생성
            auth_log = IPAuthLog(
                ip_address=client_ip,
                allowed_ip_id=allowed_ip_id,
                api_key_hash=key_hash,
                action=action,
                file_uuid=file_uuid,
                user_agent=user_agent,
                response_code=response_code,
                error_message=error_message,
                request_size=request_size,
                processing_time_ms=processing_time_ms,
            )

            self.db.add(auth_log)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            # 로깅 실패 시에도 애플리케이션은 계속 실행
            print(f"Auth log error: {str(e)}")

    def _log_auth_event(
        self,
        client_ip: str,
        api_key: str,
        action: str,
        error_message: Optional[str] = None,
    ) -> None:
        """내부 로깅 메서드"""
        self.log_auth_event(client_ip, api_key, action, error_message=error_message)

    def get_ip_statistics(
        self, ip_address: Optional[str] = None, days: int = 7
    ) -> Dict[str, Any]:
        """IP별 사용 통계 조회"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            query = self.db.query(IPAuthLog).filter(
                IPAuthLog.request_time >= start_date
            )

            if ip_address:
                query = query.filter(IPAuthLog.ip_address == ip_address)

            # 전체 요청 수
            total_requests = query.count()

            # 성공한 업로드 수
            successful_uploads = query.filter(
                and_(IPAuthLog.action == "upload", IPAuthLog.response_code == 200)
            ).count()

            # 실패한 요청 수
            failed_requests = (
                query.filter(IPAuthLog.response_code.isnot(None))
                .filter(IPAuthLog.response_code >= 400)
                .count()
            )

            # Rate limited 요청 수
            rate_limited = query.filter(IPAuthLog.action == "rate_limited").count()

            # 일별 통계
            daily_stats = (
                self.db.query(
                    func.date(IPAuthLog.request_time).label("date"),
                    func.count().label("total"),
                    func.sum(
                        func.case([(IPAuthLog.action == "upload", 1)], else_=0)
                    ).label("uploads"),
                    func.sum(
                        func.case([(IPAuthLog.response_code >= 400, 1)], else_=0)
                    ).label("errors"),
                )
                .filter(IPAuthLog.request_time >= start_date)
                .group_by(func.date(IPAuthLog.request_time))
                .order_by(func.date(IPAuthLog.request_time))
                .all()
            )

            return {
                "total_requests": total_requests,
                "successful_uploads": successful_uploads,
                "failed_requests": failed_requests,
                "rate_limited": rate_limited,
                "success_rate": (
                    (successful_uploads / total_requests * 100)
                    if total_requests > 0
                    else 0
                ),
                "daily_stats": [
                    {
                        "date": str(stat.date),
                        "total": stat.total,
                        "uploads": stat.uploads,
                        "errors": stat.errors,
                    }
                    for stat in daily_stats
                ],
            }

        except Exception as e:
            return {
                "error": f"통계 조회 오류: {str(e)}",
                "total_requests": 0,
                "successful_uploads": 0,
                "failed_requests": 0,
                "rate_limited": 0,
                "success_rate": 0,
                "daily_stats": [],
            }

    def add_allowed_ip(
        self,
        ip_address: str,
        encryption_key: str,
        ip_range: Optional[str] = None,
        permissions: Optional[Dict] = None,
        max_uploads_per_hour: int = 100,
        max_file_size: int = 104857600,
        expires_at: Optional[datetime] = None,
    ) -> AllowedIP:
        """허용된 IP 추가"""
        try:
            # IP 주소 유효성 검사
            ipaddress.ip_address(ip_address)

            # IP 범위 유효성 검사
            if ip_range:
                ipaddress.ip_network(ip_range, strict=False)

            # 키 해시 생성
            key_hash = hash_key(encryption_key)

            # 중복 확인
            existing = (
                self.db.query(AllowedIP)
                .filter(
                    and_(
                        AllowedIP.ip_address == ip_address,
                        AllowedIP.key_hash == key_hash,
                    )
                )
                .first()
            )

            if existing:
                raise ValueError("이미 존재하는 IP와 키 조합입니다")

            # 새로운 허용 IP 생성
            allowed_ip = AllowedIP(
                ip_address=ip_address,
                ip_range=ip_range,
                encryption_key=encryption_key,
                key_hash=key_hash,
                permissions=permissions,
                max_uploads_per_hour=max_uploads_per_hour,
                max_file_size=max_file_size,
                expires_at=expires_at,
            )

            self.db.add(allowed_ip)
            self.db.commit()
            self.db.refresh(allowed_ip)

            return allowed_ip

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"허용 IP 추가 실패: {str(e)}")

    def remove_allowed_ip(self, ip_address: str, encryption_key: str) -> bool:
        """허용된 IP 제거"""
        try:
            key_hash = hash_key(encryption_key)

            allowed_ip = (
                self.db.query(AllowedIP)
                .filter(
                    and_(
                        AllowedIP.ip_address == ip_address,
                        AllowedIP.key_hash == key_hash,
                    )
                )
                .first()
            )

            if not allowed_ip:
                return False

            self.db.delete(allowed_ip)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def regenerate_encryption_key(self, ip_address: str, old_key: str) -> str:
        """암호화 키 재생성"""
        try:
            old_key_hash = hash_key(old_key)

            allowed_ip = (
                self.db.query(AllowedIP)
                .filter(
                    and_(
                        AllowedIP.ip_address == ip_address,
                        AllowedIP.key_hash == old_key_hash,
                    )
                )
                .first()
            )

            if not allowed_ip:
                raise ValueError("IP와 키 조합을 찾을 수 없습니다")

            # 새 키 생성
            new_key = generate_encryption_key()
            new_key_hash = hash_key(new_key)

            # 키 업데이트
            allowed_ip.encryption_key = new_key
            allowed_ip.key_hash = new_key_hash
            allowed_ip.updated_at = datetime.utcnow()

            self.db.commit()

            return new_key

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"키 재생성 실패: {str(e)}")
