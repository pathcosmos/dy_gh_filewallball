"""
Security headers middleware for enhanced web application security.
Task 12.3: CORS 정책 및 보안 헤더 설정
Task 8: 레이트 리미팅 및 보안 헤더 구현 (강화)
"""

import os
import hashlib
import secrets
from typing import List, Dict, Optional
from fastapi import Request
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class EnhancedSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """강화된 보안 헤더 미들웨어"""
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",  # React 개발 서버
            "http://localhost:8080",  # Vue.js 개발 서버
            "http://127.0.0.1:3000",  # 로컬 개발
            "http://127.0.0.1:8080",  # 로컬 개발
        ]
        
        # 프로덕션 환경 설정
        if os.getenv("ENVIRONMENT") == "production":
            self.allowed_origins.extend([
                "https://filewallball.com",
                "https://www.filewallball.com",
                "https://api.filewallball.com"
            ])
        
        # 환경 변수에서 추가 허용 도메인 가져오기
        env_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
        if env_origins and env_origins[0]:
            self.allowed_origins.extend([origin.strip() for origin in env_origins])
        
        # CSP 논스 생성
        self.csp_nonce = secrets.token_urlsafe(16)
        
        # 보안 설정
        self.is_production = os.getenv("ENVIRONMENT") == "production"
        self.enable_hsts = self.is_production  # HTTPS 환경에서만 HSTS 활성화
    
    def _generate_csp_policy(self) -> str:
        """Content Security Policy 생성"""
        # 개발/프로덕션 환경별 CSP 설정
        if self.is_production:
            # 프로덕션: 더 엄격한 정책
            csp_policy = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{self.csp_nonce}'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' https:; "
                "connect-src 'self'; "
                "media-src 'self'; "
                "object-src 'none'; "
                "child-src 'none'; "
                "frame-src 'none'; "
                "worker-src 'self'; "
                "manifest-src 'self'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; "
                "block-all-mixed-content; "
                "upgrade-insecure-requests; "
                "require-sri-for script style"
            )
        else:
            # 개발: 더 유연한 정책
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self' ws: wss:; "  # WebSocket 지원
                "media-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'"
            )
        
        return csp_policy
    
    def _get_security_headers(self, request: Request) -> Dict[str, str]:
        """보안 헤더 생성"""
        headers = {
            # XSS 보호
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "0",  # 현대 브라우저에서는 비활성화 권장
            
            # Content Security Policy
            "Content-Security-Policy": self._generate_csp_policy(),
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy (Feature Policy의 후속)
            "Permissions-Policy": (
                "accelerometer=(), autoplay=(), camera=(), "
                "cross-origin-isolated=(), display-capture=(), "
                "encrypted-media=(), fullscreen=(), geolocation=(), "
                "gyroscope=(), keyboard-map=(), magnetometer=(), "
                "microphone=(), midi=(), payment=(), picture-in-picture=(), "
                "publickey-credentials-get=(), screen-wake-lock=(), "
                "sync-xhr=(), usb=(), web-share=(), xr-spatial-tracking=()"
            ),
            
            # Cross-Origin 정책
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            
            # 캐시 제어 (민감한 정보가 포함된 응답)
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            
            # 서버 정보 숨김
            "Server": "FileWallBall",
            
            # 추가 보안 헤더
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen",
            
            # CSP 논스 (스크립트에서 사용 가능)
            "X-CSP-Nonce": self.csp_nonce
        }
        
        # HTTPS 환경에서만 HSTS 추가
        if self.enable_hsts and (
            request.url.scheme == "https" or 
            request.headers.get("x-forwarded-proto") == "https"
        ):
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # 파일 다운로드 관련 보안 헤더
        if "/download/" in request.url.path:
            headers.update({
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": "attachment",
                "X-Download-Options": "noopen"
            })
        
        return headers
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """요청/응답 처리 및 보안 헤더 추가"""
        
        # CORS 헤더 처리
        origin = request.headers.get("origin")
        response = await call_next(request)
        
        # CORS 헤더 설정
        if origin and origin in self.allowed_origins:
            response.headers.update({
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": (
                    "Content-Type, Authorization, X-Requested-With, "
                    "Accept, Origin, Cache-Control, X-File-Name, "
                    "X-API-Key, X-CSP-Nonce"
                ),
                "Access-Control-Expose-Headers": (
                    "X-RateLimit-Limit, X-RateLimit-Remaining, "
                    "X-RateLimit-Reset, Content-Length, Content-Range"
                ),
                "Access-Control-Max-Age": "86400"  # 24시간
            })
        
        # 보안 헤더 추가
        security_headers = self._get_security_headers(request)
        response.headers.update(security_headers)
        
        # 보안 로깅
        if origin and origin not in self.allowed_origins:
            logger.warning(f"Unauthorized origin attempt: {origin} from IP: {request.client.host}")
        
        return response


class CORSValidationMiddleware(BaseHTTPMiddleware):
    """강화된 CORS 정책 검증 미들웨어"""
    
    def __init__(self, app, allowed_origins: List[str] = None, strict_mode: bool = True):
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080"
        ]
        self.strict_mode = strict_mode  # 엄격 모드
        
        # 프로덕션 환경 설정
        if os.getenv("ENVIRONMENT") == "production":
            self.allowed_origins.extend([
                "https://filewallball.com",
                "https://www.filewallball.com",
                "https://api.filewallball.com"
            ])
            self.strict_mode = True  # 프로덕션에서는 항상 엄격 모드
        
        # 환경 변수에서 추가 허용 도메인
        env_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
        if env_origins and env_origins[0]:
            self.allowed_origins.extend([origin.strip() for origin in env_origins])
        
        # 허용된 메서드 및 헤더
        self.allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        self.allowed_headers = [
            "Content-Type", "Authorization", "X-Requested-With",
            "Accept", "Origin", "Cache-Control", "X-File-Name", "X-API-Key"
        ]
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Origin이 허용되는지 확인"""
        if not origin:
            return not self.strict_mode  # 엄격 모드가 아니면 Origin 없는 요청 허용
        
        # 정확히 일치하는 origin 확인
        if origin in self.allowed_origins:
            return True
        
        # 개발 환경에서는 localhost 변형 허용
        if not self.strict_mode and "localhost" in origin:
            return True
        
        return False
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """CORS 정책 검증 및 Preflight 처리"""
        
        origin = request.headers.get("origin")
        method = request.method
        
        # Preflight 요청 처리 (OPTIONS)
        if method == "OPTIONS":
            if not self._is_origin_allowed(origin):
                logger.warning(f"CORS preflight rejected for origin: {origin}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "CORS policy violation",
                        "message": "Origin not allowed",
                        "origin": origin
                    },
                    headers={
                        "Access-Control-Allow-Origin": "",
                        "Access-Control-Allow-Methods": "",
                        "Access-Control-Allow-Headers": ""
                    }
                )
            
            # Preflight 응답
            return JSONResponse(
                status_code=200,
                content={},
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
                    "Access-Control-Allow-Headers": ", ".join(self.allowed_headers),
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "86400"
                }
            )
        
        # 실제 요청 처리
        if self.strict_mode and origin and not self._is_origin_allowed(origin):
            logger.warning(f"CORS violation: {method} {request.url.path} from {origin}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "CORS policy violation",
                    "message": "Origin not allowed for this resource",
                    "origin": origin,
                    "allowed_origins": self.allowed_origins
                }
            )
        
        # 허용된 요청 처리
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(EnhancedSecurityHeadersMiddleware):
    """하위 호환성을 위한 별칭"""
    pass 