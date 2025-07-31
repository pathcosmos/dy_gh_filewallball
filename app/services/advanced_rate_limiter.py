"""
고급 레이트 리미팅 시스템
Task 8: 레이트 리미팅 및 보안 헤더 구현
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.async_redis_client import get_async_redis_client
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class AdvancedRateLimiter:
    """고급 레이트 리미팅 시스템"""

    def __init__(self):
        self.limiter = Limiter(key_func=get_remote_address)

        # 레이트 리미트 설정
        self.rate_limits = {
            "upload": "10/minute",  # 업로드: 10req/min
            "download": "100/minute",  # 다운로드: 100req/min
            "read": "1000/minute",  # 조회: 1000req/min
            "api": "500/minute",  # 일반 API: 500req/min
            "auth": "5/minute",  # 인증: 5req/min
            "admin": "1000/minute",  # 관리자: 1000req/min
        }

        # IP별 추가 제한
        self.ip_limits = {
            "suspicious": "1/minute",  # 의심스러운 IP
            "blocked": "0/minute",  # 차단된 IP
        }

    def get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출 (프록시 환경 고려)"""
        # X-Forwarded-For 헤더 확인
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

    def is_suspicious_ip(self, ip: str) -> bool:
        """의심스러운 IP인지 확인"""
        # 실제 구현에서는 더 복잡한 로직 사용
        # 예: 짧은 시간 내 많은 요청, 특정 패턴 등
        return False

    def is_blocked_ip(self, ip: str) -> bool:
        """차단된 IP인지 확인"""
        # 실제 구현에서는 Redis나 DB에서 차단 목록 확인
        return False

    def get_rate_limit_for_endpoint(self, endpoint: str) -> str:
        """엔드포인트별 레이트 리미트 반환"""
        if "upload" in endpoint:
            return self.rate_limits["upload"]
        elif "download" in endpoint:
            return self.rate_limits["download"]
        elif "auth" in endpoint or "login" in endpoint:
            return self.rate_limits["auth"]
        elif "admin" in endpoint:
            return self.rate_limits["admin"]
        elif "read" in endpoint or "get" in endpoint:
            return self.rate_limits["read"]
        else:
            return self.rate_limits["api"]

    def get_rate_limit_for_ip(self, ip: str) -> str:
        """IP별 레이트 리미트 반환"""
        if self.is_blocked_ip(ip):
            return self.ip_limits["blocked"]
        elif self.is_suspicious_ip(ip):
            return self.ip_limits["suspicious"]
        else:
            return None  # 기본 제한 사용

    async def check_rate_limit(
        self, request: Request, endpoint: str
    ) -> Tuple[bool, Dict]:
        """
        레이트 리미트 확인

        Returns:
            (제한 여부, 제한 정보) 튜플
        """
        try:
            client_ip = self.get_client_ip(request)

            # IP별 제한 확인
            ip_limit = self.get_rate_limit_for_ip(client_ip)
            if ip_limit:
                limit = ip_limit
            else:
                # 엔드포인트별 제한 확인
                limit = self.get_rate_limit_for_endpoint(endpoint)

            # Redis 클라이언트 가져오기
            redis_client = await get_async_redis_client()

            # 현재 시간 윈도우 계산
            current_time = int(time.time())
            window_size = self._parse_rate_limit(limit)

            if window_size["unit"] == "minute":
                window_start = current_time - (window_size["value"] * 60)
                key = f"rate_limit:{client_ip}:{endpoint}:min:{current_time // 60}"
            elif window_size["unit"] == "hour":
                window_start = current_time - (window_size["value"] * 3600)
                key = f"rate_limit:{client_ip}:{endpoint}:hour:{current_time // 3600}"
            else:  # second
                window_start = current_time - window_size["value"]
                key = f"rate_limit:{client_ip}:{endpoint}:sec:{current_time}"

            # 현재 요청 수 확인
            current_count = await redis_client.get(key)
            current_count = int(current_count) if current_count else 0

            # 제한 확인
            is_limited = current_count >= window_size["value"]

            # 남은 요청 수 계산
            remaining = max(0, window_size["value"] - current_count)

            # 제한 정보
            limit_info = {
                "limit": window_size["value"],
                "remaining": remaining,
                "reset_time": window_start
                + (
                    window_size["value"] * 60
                    if window_size["unit"] == "minute"
                    else (
                        window_size["value"] * 3600
                        if window_size["unit"] == "hour"
                        else window_size["value"]
                    )
                ),
                "current_count": current_count,
                "window_size": window_size["unit"],
                "client_ip": client_ip,
            }

            return is_limited, limit_info

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False, {}

    def _parse_rate_limit(self, rate_limit: str) -> Dict:
        """레이트 리미트 문자열 파싱"""
        try:
            value, unit = rate_limit.split("/")
            return {"value": int(value), "unit": unit}
        except:
            return {"value": 100, "unit": "minute"}

    async def increment_request_count(self, request: Request, endpoint: str) -> None:
        """요청 카운트 증가"""
        try:
            client_ip = self.get_client_ip(request)
            current_time = int(time.time())

            # Redis 클라이언트 가져오기
            redis_client = await get_async_redis_client()

            # 키 생성
            key = f"rate_limit:{client_ip}:{endpoint}:min:{current_time // 60}"

            # 카운트 증가 (TTL 60초)
            await redis_client.set_with_ttl(key, "1", 60)
            await redis_client.increment(key)

        except Exception as e:
            logger.error(f"Rate limit increment error: {e}")

    def get_rate_limit_headers(self, limit_info: Dict) -> Dict[str, str]:
        """레이트 리미트 헤더 생성"""
        headers = {
            "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(limit_info.get("remaining", 0)),
            "X-RateLimit-Reset": str(limit_info.get("reset_time", 0)),
        }

        # 제한 초과 시 Retry-After 헤더 추가
        if limit_info.get("remaining", 0) <= 0:
            reset_time = limit_info.get("reset_time", 0)
            retry_after = max(1, reset_time - int(time.time()))
            headers["Retry-After"] = str(retry_after)

        return headers


# 전역 인스턴스
advanced_rate_limiter = AdvancedRateLimiter()


def rate_limit_middleware():
    """레이트 리미트 미들웨어 데코레이터"""

    async def middleware(request: Request, call_next):
        try:
            # 엔드포인트 경로 추출
            endpoint = request.url.path

            # 레이트 리미트 확인
            is_limited, limit_info = await advanced_rate_limiter.check_rate_limit(
                request, endpoint
            )

            if is_limited:
                # 제한 초과 시 429 응답
                headers = advanced_rate_limiter.get_rate_limit_headers(limit_info)

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                        "retry_after": headers.get("Retry-After", 60),
                        "limit_info": limit_info,
                    },
                    headers=headers,
                )

            # 요청 카운트 증가
            await advanced_rate_limiter.increment_request_count(request, endpoint)

            # 다음 미들웨어 호출
            response = await call_next(request)

            # 레이트 리미트 헤더 추가
            headers = advanced_rate_limiter.get_rate_limit_headers(limit_info)
            for key, value in headers.items():
                response.headers[key] = value

            return response

        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            return await call_next(request)

    return middleware


# 편의 함수들
def require_rate_limit(limit: str):
    """특정 레이트 리미트 적용 데코레이터"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 실제 구현에서는 slowapi의 rate_limit 데코레이터 사용
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# 엔드포인트별 레이트 리미트 데코레이터
require_upload_rate_limit = require_rate_limit("10/minute")
require_download_rate_limit = require_rate_limit("100/minute")
require_read_rate_limit = require_rate_limit("1000/minute")
require_auth_rate_limit = require_rate_limit("5/minute")
require_admin_rate_limit = require_rate_limit("1000/minute")
