"""
Request/Response logging middleware.
"""

import json
from typing import Any, Callable, Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청/응답 로깅"""

        # 요청 정보 로깅
        await self._log_request(request)

        # 응답 처리
        response = await call_next(request)

        # 응답 정보 로깅
        await self._log_response(request, response)

        return response

    async def _log_request(self, request: Request) -> None:
        """요청 정보 로깅"""
        request_id = getattr(request.state, "request_id", "unknown")

        # 요청 헤더에서 민감한 정보 제거
        headers = dict(request.headers)
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "headers": headers,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        logger.info(f"Request: {json.dumps(log_data, default=str)}")

    async def _log_response(self, request: Request, response: Response) -> None:
        """응답 정보 로깅"""
        request_id = getattr(request.state, "request_id", "unknown")

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "response_headers": dict(response.headers),
        }

        logger.info(f"Response: {json.dumps(log_data, default=str)}")
