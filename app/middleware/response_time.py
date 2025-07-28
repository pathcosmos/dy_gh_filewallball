"""
Response time measurement middleware.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """응답 시간을 측정하는 미들웨어"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 및 응답 시간 측정"""
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 응답 처리
        response = await call_next(request)
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        
        # 응답 헤더에 응답 시간 추가
        response.headers["X-Response-Time"] = f"{response_time:.4f}s"
        
        # 로그 기록
        logger.info(
            f"Request {request.method} {request.url.path} "
            f"completed in {response_time:.4f}s"
        )
        
        return response 