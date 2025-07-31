"""
Prometheus 메트릭 수집 미들웨어
Task 9: Prometheus 메트릭 및 모니터링 시스템
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.metrics import (
    error_rate_counter,
    http_request_duration_seconds,
    http_requests_total,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """HTTP 요청 메트릭 수집 미들웨어"""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> StarletteResponse:
        """요청/응답 처리 및 메트릭 수집"""
        start_time = time.time()

        try:
            # 요청 처리
            response = await call_next(request)

            # 응답 시간 계산
            duration = time.time() - start_time

            # 메트릭 수집
            self._record_metrics(request, response, duration, None)

            return response

        except Exception as e:
            # 에러 발생 시 메트릭 수집
            duration = time.time() - start_time
            self._record_metrics(request, None, duration, e)
            raise

    def _record_metrics(
        self,
        request: Request,
        response: Response,
        duration: float,
        error: Exception = None,
    ):
        """메트릭 기록"""
        try:
            # 요청 정보 추출
            method = request.method
            path = request.url.path
            status_code = response.status_code if response else 500

            # 라벨 설정
            labels = {
                "method": method,
                "endpoint": self._normalize_endpoint(path),
                "status": str(status_code),
                "status_class": self._get_status_class(status_code),
            }

            # HTTP 요청 카운터 증가
            http_requests_total.labels(**labels).inc()

            # 요청 지속 시간 기록
            http_request_duration_seconds.labels(
                method=method,
                endpoint=self._normalize_endpoint(path),
                status_class=self._get_status_class(status_code),
            ).observe(duration)

            # 에러 발생 시 에러 카운터 증가
            if error or (response and status_code >= 400):
                error_type = type(error).__name__ if error else f"http_{status_code}"
                error_rate_counter.labels(
                    error_type=error_type, endpoint=self._normalize_endpoint(path)
                ).inc()

        except Exception as e:
            logger.error(f"메트릭 수집 실패: {e}")

    def _normalize_endpoint(self, path: str) -> str:
        """엔드포인트 정규화 (동적 경로를 패턴으로 변환)"""
        # UUID 패턴을 {id}로 변환
        import re

        normalized = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
        )

        # 숫자 ID를 {id}로 변환
        normalized = re.sub(r"/\d+", "/{id}", normalized)

        return normalized

    def _get_status_class(self, status_code: int) -> str:
        """HTTP 상태 코드 클래스 반환"""
        if status_code < 200:
            return "1xx"
        elif status_code < 300:
            return "2xx"
        elif status_code < 400:
            return "3xx"
        elif status_code < 500:
            return "4xx"
        else:
            return "5xx"


# 비즈니스 메트릭 수집 함수들
def record_file_upload_metric(file_type: str, status: str, user_id: str = "anonymous"):
    """파일 업로드 메트릭 기록"""
    try:
        from app.metrics import file_upload_counter

        file_upload_counter.labels(
            status=status, file_type=file_type, user_id=user_id
        ).inc()
    except Exception as e:
        logger.error(f"파일 업로드 메트릭 기록 실패: {e}")


def record_file_download_metric(
    file_type: str, status: str, user_id: str = "anonymous"
):
    """파일 다운로드 메트릭 기록"""
    try:
        from app.metrics import file_download_counter

        file_download_counter.labels(
            status=status, file_type=file_type, user_id=user_id
        ).inc()
    except Exception as e:
        logger.error(f"파일 다운로드 메트릭 기록 실패: {e}")


def record_upload_duration_metric(file_type: str, status: str, duration: float):
    """업로드 지속 시간 메트릭 기록"""
    try:
        from app.metrics import file_upload_duration

        file_upload_duration.labels(file_type=file_type, status=status).observe(
            duration
        )
    except Exception as e:
        logger.error(f"업로드 지속 시간 메트릭 기록 실패: {e}")


def record_upload_error_metric(error_type: str, file_type: str):
    """업로드 에러 메트릭 기록"""
    try:
        from app.metrics import file_upload_error_counter

        file_upload_error_counter.labels(
            error_type=error_type, file_type=file_type
        ).inc()
    except Exception as e:
        logger.error(f"업로드 에러 메트릭 기록 실패: {e}")


def record_cache_metric(
    operation: str, cache_type: str, status: str, duration: float = None
):
    """캐시 메트릭 기록"""
    try:
        from app.metrics import cache_operation_duration

        if duration is not None:
            cache_operation_duration.labels(
                operation=operation, cache_type=cache_type, status=status
            ).observe(duration)
    except Exception as e:
        logger.error(f"캐시 메트릭 기록 실패: {e}")


def record_active_connections(count: int):
    """활성 연결 수 메트릭 기록"""
    try:
        from app.metrics import active_connections_gauge

        active_connections_gauge.set(count)
    except Exception as e:
        logger.error(f"활성 연결 수 메트릭 기록 실패: {e}")


# 메트릭 데코레이터
def track_metrics(operation: str, metric_type: str = "counter"):
    """메트릭 추적 데코레이터"""

    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # 성공 메트릭 기록
                if metric_type == "counter":
                    record_file_upload_metric("success", operation)
                elif metric_type == "histogram":
                    duration = time.time() - start_time
                    record_upload_duration_metric(operation, "success", duration)

                return result

            except Exception as e:
                # 에러 메트릭 기록
                if metric_type == "counter":
                    record_file_upload_metric("error", operation)
                elif metric_type == "histogram":
                    duration = time.time() - start_time
                    record_upload_duration_metric(operation, "error", duration)

                record_upload_error_metric(type(e).__name__, operation)
                raise

        return wrapper

    return decorator
