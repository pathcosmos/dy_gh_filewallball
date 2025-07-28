"""
Request ID middleware for tracking requests.
"""

import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """요청 ID를 추가하는 미들웨어"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 및 응답 ID 추가"""
        
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        
        # 요청 객체에 요청 ID 추가
        request.state.request_id = request_id
        
        # 응답 처리
        response = await call_next(request)
        
        # 응답 헤더에 요청 ID 추가
        response.headers["X-Request-ID"] = request_id
        
        logger.debug(f"Request processed with ID: {request_id}")
        
        return response 