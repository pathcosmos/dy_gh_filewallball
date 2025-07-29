"""
Security headers middleware for enhanced web application security.
Task 12.3: CORS 정책 및 보안 헤더 설정
"""

import os
from typing import List
from fastapi import Request
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더를 추가하는 미들웨어"""
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",  # React 개발 서버
            "http://localhost:8080",  # Vue.js 개발 서버
            "https://filewallball.com",  # 프로덕션 도메인 (예시)
            "https://www.filewallball.com"
        ]
        
        # 환경 변수에서 추가 허용 도메인 가져오기
        env_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
        if env_origins and env_origins[0]:
            self.allowed_origins.extend([origin.strip() for origin in env_origins])
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """요청/응답 처리 및 보안 헤더 추가"""
        
        # CORS 헤더 처리
        origin = request.headers.get("origin")
        if origin and origin in self.allowed_origins:
            # 허용된 도메인에서의 요청
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Requested-With, "
                "Accept, Origin, Cache-Control, X-File-Name"
            )
        else:
            # 허용되지 않은 도메인에서의 요청
            if request.method == "OPTIONS":
                # Preflight 요청 처리
                return JSONResponse(
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": "",
                        "Access-Control-Allow-Methods": "",
                        "Access-Control-Allow-Headers": "",
                        "Access-Control-Max-Age": "86400"
                    }
                )
            else:
                # 일반 요청 처리
                response = await call_next(request)
        
        # 보안 헤더 추가
        response.headers.update({
            # XSS 보호
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "media-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; "
                "upgrade-insecure-requests"
            ),
            
            # HSTS (HTTPS 강제)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            
            # Cache Control (민감한 데이터)
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            
            # 서버 정보 숨김
            "Server": "FileWallBall/1.0",
            
            # 추가 보안 헤더
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin"
        })
        
        return response


class CORSValidationMiddleware(BaseHTTPMiddleware):
    """CORS 정책 검증 미들웨어"""
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://localhost:8080",
            "https://filewallball.com",
            "https://www.filewallball.com"
        ]
        
        # 환경 변수에서 추가 허용 도메인 가져오기
        env_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
        if env_origins and env_origins[0]:
            self.allowed_origins.extend([origin.strip() for origin in env_origins])
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """CORS 정책 검증"""
        
        origin = request.headers.get("origin")
        
        # Origin 헤더가 있는 경우 검증
        if origin:
            if origin not in self.allowed_origins:
                # 허용되지 않은 도메인에서의 요청
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CORS policy violation: Origin not allowed",
                        "allowed_origins": self.allowed_origins
                    },
                    headers={
                        "Access-Control-Allow-Origin": "",
                        "Access-Control-Allow-Methods": "",
                        "Access-Control-Allow-Headers": ""
                    }
                )
        
        # 허용된 요청 처리
        response = await call_next(request)
        return response 