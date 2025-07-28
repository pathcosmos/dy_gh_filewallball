"""
FileWallBall FastAPI Application Main Entry Point

A modern file management system built with FastAPI, MariaDB, and Redis.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.database import init_database
from app.middleware import RequestIdMiddleware, ResponseTimeMiddleware, LoggingMiddleware
from app.utils.logging_config import setup_logging
from app.routers import health_router, files_router

# 설정 가져오기
settings = get_settings()

# 로깅 시스템 설정
setup_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    log_file=settings.log_file
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기 관리"""
    # 시작 시 실행
    logger.info("Starting FileWallBall application...")
    
    # 데이터베이스 초기화
    if init_database():
        logger.info("Database initialized successfully")
    else:
        logger.error("Database initialization failed")
    
    yield
    
    # 종료 시 실행
    logger.info("Shutting down FileWallBall application...")


# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title=settings.app_name,
    description="A modern file management system API",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.debug
)

# 커스텀 미들웨어 추가
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ResponseTimeMiddleware)
app.add_middleware(LoggingMiddleware)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(files_router, prefix="/api/v1/files", tags=["files"])


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main_new:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 