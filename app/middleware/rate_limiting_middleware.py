"""
레이트 리미팅 미들웨어
Task 8: 레이트 리미팅 및 보안 헤더 구현
"""

import time
from typing import Dict, Optional, Callable
from fastapi import Request, Response, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis.asyncio as redis
import asyncio

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 주소 추출 (프록시 환경 지원)"""
    # X-Forwarded-For 헤더 확인 (프록시 환경)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 첫 번째 IP 주소 사용 (클라이언트 IP)
        return forwarded_for.split(",")[0].strip()
    
    # X-Real-IP 헤더 확인
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # CloudFlare CF-Connecting-IP 헤더 확인
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    
    # 기본 클라이언트 IP
    return request.client.host


# Redis 기반 스토리지 함수
async def redis_storage_key_func(request: Request) -> str:
    """Redis 키 생성 함수"""
    client_ip = get_client_ip(request)
    path = request.url.path
    method = request.method
    return f"rate_limit:{client_ip}:{method}:{path}"


# Redis 연결 설정
def get_redis_connection():
    """Redis 연결 반환"""
    try:
        return redis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )
    except Exception as e:
        logger.error(f"Redis 연결 실패: {e}")
        return None


# slowapi Limiter 설정
limiter = Limiter(
    key_func=redis_storage_key_func,
    storage_uri="redis://localhost:6379",
    default_limits=["1000/hour"]  # 기본 제한
)


class AdvancedRateLimiter:
    """고급 레이트 리미터"""
    
    def __init__(self):
        self.redis_client = get_redis_connection()
        self.rate_limits = {
            # 업로드 제한 (더 엄격)
            "upload": {
                "requests": 10,
                "window": 60,  # 1분
                "description": "파일 업로드"
            },
            # 다운로드 제한
            "download": {
                "requests": 100,
                "window": 60,  # 1분
                "description": "파일 다운로드"
            },
            # 조회 제한
            "read": {
                "requests": 1000,
                "window": 60,  # 1분
                "description": "파일 조회"
            },
            # API 일반 제한
            "api": {
                "requests": 500,
                "window": 60,  # 1분
                "description": "API 요청"
            },
            # 인증 제한 (보안)
            "auth": {
                "requests": 5,
                "window": 60,  # 1분
                "description": "인증 시도"
            }
        }
    
    async def check_rate_limit(
        self, 
        request: Request, 
        limit_type: str = "api"
    ) -> Dict:
        """레이트 리미트 확인"""
        if not self.redis_client:
            # Redis 연결이 없으면 제한하지 않음
            return {"allowed": True, "remaining": 999}
        
        client_ip = get_client_ip(request)
        limit_config = self.rate_limits.get(limit_type, self.rate_limits["api"])
        
        # Redis 키 생성
        key = f"rate_limit:{limit_type}:{client_ip}"
        window = limit_config["window"]
        max_requests = limit_config["requests"]
        
        try:
            # 현재 카운트 조회
            current_count = await self.redis_client.get(key)
            
            if current_count is None:
                # 첫 요청
                await self.redis_client.setex(key, window, 1)
                return {
                    "allowed": True,
                    "remaining": max_requests - 1,
                    "reset_time": time.time() + window,
                    "limit": max_requests
                }
            
            current_count = int(current_count)
            
            if current_count >= max_requests:
                # 제한 초과
                ttl = await self.redis_client.ttl(key)
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": time.time() + ttl,
                    "limit": max_requests,
                    "retry_after": ttl
                }
            
            # 카운트 증가
            await self.redis_client.incr(key)
            ttl = await self.redis_client.ttl(key)
            
            return {
                "allowed": True,
                "remaining": max_requests - (current_count + 1),
                "reset_time": time.time() + ttl,
                "limit": max_requests
            }
            
        except Exception as e:
            logger.error(f"레이트 리미트 확인 오류: {e}")
            # 오류 시 허용
            return {"allowed": True, "remaining": 999}
    
    async def check_ddos_protection(self, request: Request) -> bool:
        """DDoS 공격 감지"""
        client_ip = get_client_ip(request)
        
        # 매우 짧은 시간 내 대량 요청 감지
        ddos_key = f"ddos_protection:{client_ip}"
        ddos_window = 10  # 10초
        ddos_threshold = 100  # 10초 내 100회 이상
        
        try:
            current_count = await self.redis_client.get(ddos_key)
            
            if current_count is None:
                await self.redis_client.setex(ddos_key, ddos_window, 1)
                return True
            
            current_count = int(current_count)
            
            if current_count >= ddos_threshold:
                # DDoS 공격으로 판단
                logger.warning(f"DDoS 공격 감지: IP {client_ip}, 요청 수: {current_count}")
                return False
            
            await self.redis_client.incr(ddos_key)
            return True
            
        except Exception as e:
            logger.error(f"DDoS 보호 확인 오류: {e}")
            return True


# 전역 레이트 리미터 인스턴스
advanced_limiter = AdvancedRateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """레이트 리미팅 미들웨어"""
    # 헬스체크 및 메트릭 엔드포인트는 제외
    excluded_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
    if any(request.url.path.startswith(path) for path in excluded_paths):
        return await call_next(request)
    
    # DDoS 보호 확인
    if not await advanced_limiter.check_ddos_protection(request):
        return Response(
            content="DDoS protection activated",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": "300"}  # 5분 후 재시도
        )
    
    # 경로별 레이트 리미트 타입 결정
    path = request.url.path
    method = request.method
    
    if "/upload" in path and method == "POST":
        limit_type = "upload"
    elif "/download" in path and method == "GET":
        limit_type = "download"
    elif "/files" in path and method == "GET":
        limit_type = "read"
    elif "/auth" in path or "/login" in path:
        limit_type = "auth"
    else:
        limit_type = "api"
    
    # 레이트 리미트 확인
    rate_limit_result = await advanced_limiter.check_rate_limit(request, limit_type)
    
    if not rate_limit_result["allowed"]:
        # 레이트 리미트 초과
        headers = {
            "X-RateLimit-Limit": str(rate_limit_result["limit"]),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(rate_limit_result["reset_time"])),
            "Retry-After": str(rate_limit_result.get("retry_after", 60))
        }
        
        return Response(
            content=f"Rate limit exceeded for {limit_type}",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers
        )
    
    # 요청 처리
    response = await call_next(request)
    
    # 응답에 레이트 리미트 헤더 추가
    response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
    response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result["reset_time"]))
    
    return response


# slowapi 에러 핸들러
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """레이트 리미트 초과 에러 핸들러"""
    response = Response(
        content=f"Rate limit exceeded: {exc.detail}",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS
    )
    
    # Retry-After 헤더 추가
    if hasattr(exc, 'retry_after'):
        response.headers["Retry-After"] = str(exc.retry_after)
    else:
        response.headers["Retry-After"] = "60"  # 기본 1분
    
    return response