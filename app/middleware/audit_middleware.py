"""
Audit middleware for automatic logging of API requests.
Task 12.5: 역할 기반 접근 제어(RBAC) 및 감사 로그 구현
"""

import time
import json
from typing import Optional
from fastapi import Request
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from app.dependencies.database import get_db
from app.services.rbac_service import rbac_service
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """API 요청 감사 로그 미들웨어"""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            '/health',
            '/metrics',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/favicon.ico'
        ]
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """요청/응답 처리 및 감사 로그 기록"""
        
        # 제외할 경로인지 확인
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.time()
        
        # 요청 정보 수집
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        request_path = str(request.url.path)
        request_method = request.method
        
        # 사용자 정보 (인증이 완료된 후에만)
        current_user = None
        try:
            # 인증된 사용자 정보 가져오기 (실제 구현에서는 인증 미들웨어에서 설정)
            current_user = getattr(request.state, 'current_user', None)
        except Exception:
            pass
        
        # 응답 처리
        try:
            response = await call_next(request)
            processing_time = int((time.time() - start_time) * 1000)
            response_code = response.status_code
            status = 'success' if response_code < 400 else 'failed'
            error_message = None
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            response_code = 500
            status = 'failed'
            error_message = str(e)
            raise
        
        finally:
            # 감사 로그 기록 (비동기로 처리)
            try:
                await self._log_audit_event(
                    current_user=current_user,
                    action=self._determine_action(request_path, request_method),
                    resource_type=self._determine_resource_type(request_path),
                    resource_id=self._extract_resource_id(request_path),
                    resource_name=self._extract_resource_name(request_path),
                    status=status,
                    error_message=error_message,
                    request_path=request_path,
                    request_method=request_method,
                    response_code=response_code,
                    processing_time_ms=processing_time,
                    ip_address=client_ip,
                    user_agent=user_agent
                )
            except Exception as e:
                logger.error(f"Failed to log audit event: {e}")
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # X-Forwarded-For 헤더 확인 (프록시 환경)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 기본 클라이언트 IP
        return request.client.host if request.client else "unknown"
    
    def _determine_action(self, path: str, method: str) -> str:
        """요청 경로와 메서드로부터 액션 결정"""
        if method == "GET":
            if "/download" in path:
                return "download"
            elif "/preview" in path or "/thumbnail" in path:
                return "preview"
            else:
                return "read"
        elif method == "POST":
            if "/upload" in path:
                return "create"
            else:
                return "create"
        elif method == "PUT":
            return "update"
        elif method == "DELETE":
            if "/permanent" in path:
                return "permanent_delete"
            else:
                return "delete"
        else:
            return "other"
    
    def _determine_resource_type(self, path: str) -> str:
        """요청 경로로부터 리소스 타입 결정"""
        if "/files" in path:
            return "file"
        elif "/users" in path:
            return "user"
        elif "/audit" in path or "/logs" in path:
            return "audit"
        elif "/system" in path or "/settings" in path:
            return "system"
        else:
            return "other"
    
    def _extract_resource_id(self, path: str) -> Optional[str]:
        """요청 경로에서 리소스 ID 추출"""
        parts = path.split("/")
        for i, part in enumerate(parts):
            if part in ["files", "users"] and i + 1 < len(parts):
                return parts[i + 1]
        return None
    
    def _extract_resource_name(self, path: str) -> Optional[str]:
        """요청 경로에서 리소스 이름 추출"""
        if "/files" in path:
            return "File"
        elif "/users" in path:
            return "User"
        elif "/audit" in path:
            return "Audit Log"
        elif "/system" in path:
            return "System"
        else:
            return None
    
    async def _log_audit_event(self, **kwargs):
        """감사 로그 이벤트 기록"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            rbac_service.log_audit_event(db=db, **kwargs)
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
        finally:
            try:
                db.close()
            except:
                pass


class AuditDecorator:
    """감사 로그 데코레이터"""
    
    def __init__(self, action: str, resource_type: str):
        self.action = action
        self.resource_type = resource_type
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # 함수 실행 전후로 감사 로그 기록
            # 실제 구현에서는 더 복잡한 로직이 필요
            return await func(*args, **kwargs)
        return wrapper


def audit_log(action: str, resource_type: str):
    """감사 로그 데코레이터 팩토리"""
    return AuditDecorator(action, resource_type) 