"""
Health check endpoints for monitoring application status.
"""

import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies.database import get_db
# Redis 클라이언트 제거됨
from app.dependencies.settings import get_app_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    기본 헬스체크 엔드포인트

    Returns:
        Dict[str, Any]: 애플리케이션 상태 정보
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "FileWallBall API",
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Dict[str, Any]:
    """
    상세 헬스체크 엔드포인트 (데이터베이스, Redis 연결 확인)

    Args:
        db: 데이터베이스 세션
        redis_client: Redis 클라이언트
        settings: 애플리케이션 설정

    Returns:
        Dict[str, Any]: 상세 상태 정보
    """
    start_time = time.time()

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.app_version,
        "checks": {
            "database": {"status": "unknown", "response_time": 0},
            "redis": {"status": "unknown", "response_time": 0},
            "application": {"status": "healthy", "response_time": 0},
        },
    }

    # 데이터베이스 연결 확인
    try:
        db_start = time.time()
        result = db.execute("SELECT 1 as test")
        row = result.fetchone()
        db_time = time.time() - db_start

        if row and row.test == 1:
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time": round(db_time * 1000, 2),
            }
        else:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "response_time": round(db_time * 1000, 2),
                "error": "Database query failed",
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "response_time": 0,
            "error": str(e),
        }

    # Redis 연결 확인 (현재 비활성화)
    health_status["checks"]["redis"] = {
        "status": "disabled",
        "response_time": 0,
    }

    # 전체 응답 시간 계산
    total_time = time.time() - start_time
    health_status["checks"]["application"]["response_time"] = round(
        total_time * 1000, 2
    )

    # 전체 상태 결정
    all_healthy = all(
        check["status"] == "healthy" for check in health_status["checks"].values()
    )

    if not all_healthy:
        health_status["status"] = "unhealthy"
        return health_status

    return health_status


@router.get("/health/ready")
async def readiness_check(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Readiness 체크 (Kubernetes용)

    Args:
        db: 데이터베이스 세션
        redis_client: Redis 클라이언트

    Returns:
        Dict[str, Any]: 준비 상태 정보
    """
    try:
        # 데이터베이스 연결 확인
        result = db.execute("SELECT 1 as test")
        row = result.fetchone()
        if not row or row.test != 1:
            raise HTTPException(status_code=503, detail="Database not ready")

        # Redis 연결 확인 (현재 비활성화)
        # await redis_client.ping()

        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness 체크 (Kubernetes용)

    Returns:
        Dict[str, Any]: 생존 상태 정보
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/info")
async def service_info(
    settings: Settings = Depends(get_app_settings),
) -> Dict[str, Any]:
    """
    서비스 정보 엔드포인트

    Args:
        settings: 애플리케이션 설정

    Returns:
        Dict[str, Any]: 서비스 정보
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": "development",  # TODO: 환경별 설정
        "debug": settings.debug,
        "database": {
            "host": settings.db_host,
            "port": settings.db_port,
            "name": settings.db_name,
        },
        "redis": {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
        },
        "features": {
            "file_upload": True,
            "file_download": True,
            "caching": True,
            "authentication": True,
        },
    }
