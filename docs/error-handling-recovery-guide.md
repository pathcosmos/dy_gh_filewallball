# FileWallBall 에러 처리 및 복구 가이드

## ⚠️ 개요

FileWallBall의 에러 처리 및 복구 시스템은 예상치 못한 상황과 장애에 대한 견고한 방어 메커니즘을 제공합니다. 이 문서는 에러 처리 전략, 복구 방법, 그리고 장애 대응 절차를 상세히 설명합니다.

## 🔧 에러 처리 아키텍처

### 다층 에러 처리 모델

```
┌─────────────────────────────────────┐
│           클라이언트 레이어          │
│  (사용자 친화적 에러 메시지)         │
├─────────────────────────────────────┤
│           API 레이어                │
│  (HTTP 상태 코드, 에러 응답)         │
├─────────────────────────────────────┤
│         애플리케이션 레이어          │
│  (비즈니스 로직 에러 처리)           │
├─────────────────────────────────────┤
│           서비스 레이어              │
│  (서비스별 에러 처리)                │
├─────────────────────────────────────┤
│           인프라 레이어              │
│  (시스템 에러, 복구 메커니즘)        │
└─────────────────────────────────────┘
```

## 🛠️ Error Handler Service

### Error Handler Service (`error_handler_service.py`)

에러 처리 서비스는 모든 에러를 중앙에서 관리하고 적절한 응답을 생성합니다.

#### 에러 분류 시스템

```python
# 에러 타입 분류
ERROR_TYPES = {
    # 검증 에러
    "validation_error": {
        "http_status": 400,
        "category": "client_error",
        "retryable": False,
        "log_level": "warning"
    },

    # 인증 에러
    "authentication_error": {
        "http_status": 401,
        "category": "client_error",
        "retryable": False,
        "log_level": "warning"
    },

    # 권한 에러
    "authorization_error": {
        "http_status": 403,
        "category": "client_error",
        "retryable": False,
        "log_level": "warning"
    },

    # 리소스 없음
    "not_found_error": {
        "http_status": 404,
        "category": "client_error",
        "retryable": False,
        "log_level": "info"
    },

    # 요청 한도 초과
    "rate_limit_error": {
        "http_status": 429,
        "category": "client_error",
        "retryable": True,
        "retry_after": 60,
        "log_level": "warning"
    },

    # 서버 내부 에러
    "internal_error": {
        "http_status": 500,
        "category": "server_error",
        "retryable": True,
        "log_level": "error"
    },

    # 서비스 사용 불가
    "service_unavailable": {
        "http_status": 503,
        "category": "server_error",
        "retryable": True,
        "retry_after": 30,
        "log_level": "error"
    },

    # 파일 검증 에러
    "file_validation_error": {
        "http_status": 400,
        "category": "client_error",
        "retryable": False,
        "log_level": "warning"
    },

    # 저장소 에러
    "storage_error": {
        "http_status": 500,
        "category": "server_error",
        "retryable": True,
        "log_level": "error"
    },

    # 네트워크 에러
    "network_error": {
        "http_status": 503,
        "category": "server_error",
        "retryable": True,
        "retry_after": 10,
        "log_level": "error"
    }
}
```

#### 에러 처리 서비스 구현

```python
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class ErrorHandlerService:
    """중앙 집중식 에러 처리 서비스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counter = {}  # 에러 카운터

    def handle_error(
        self,
        error: Exception,
        request: Request,
        context: Dict[str, Any] = None
    ) -> JSONResponse:
        """에러 처리 메인 메서드"""

        # 에러 타입 분류
        error_type = self._classify_error(error)
        error_config = ERROR_TYPES.get(error_type, ERROR_TYPES["internal_error"])

        # 에러 정보 수집
        error_info = self._collect_error_info(error, request, context)

        # 에러 로깅
        self._log_error(error_info, error_config)

        # 메트릭 업데이트
        self._update_metrics(error_type, error_info)

        # 에러 응답 생성
        return self._create_error_response(error_info, error_config)

    def _classify_error(self, error: Exception) -> str:
        """에러 타입 분류"""
        if isinstance(error, HTTPException):
            if error.status_code == 400:
                return "validation_error"
            elif error.status_code == 401:
                return "authentication_error"
            elif error.status_code == 403:
                return "authorization_error"
            elif error.status_code == 404:
                return "not_found_error"
            elif error.status_code == 429:
                return "rate_limit_error"
            elif error.status_code == 503:
                return "service_unavailable"
            else:
                return "internal_error"

        # 특정 에러 타입 분류
        error_message = str(error).lower()
        if "validation" in error_message or "invalid" in error_message:
            return "validation_error"
        elif "authentication" in error_message or "unauthorized" in error_message:
            return "authentication_error"
        elif "permission" in error_message or "forbidden" in error_message:
            return "authorization_error"
        elif "not found" in error_message:
            return "not_found_error"
        elif "rate limit" in error_message:
            return "rate_limit_error"
        elif "storage" in error_message or "disk" in error_message:
            return "storage_error"
        elif "network" in error_message or "connection" in error_message:
            return "network_error"
        else:
            return "internal_error"

    def _collect_error_info(
        self,
        error: Exception,
        request: Request,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """에러 정보 수집"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": self._classify_error(error),
            "error_message": str(error),
            "error_class": error.__class__.__name__,
            "request_id": getattr(request.state, 'request_id', None),
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "context": context or {},
            "stack_trace": traceback.format_exc() if self.logger.isEnabledFor(logging.DEBUG) else None
        }

    def _log_error(self, error_info: Dict[str, Any], error_config: Dict[str, Any]):
        """에러 로깅"""
        log_level = getattr(logging, error_config["log_level"].upper())

        log_message = (
            f"Error: {error_info['error_type']} - {error_info['error_message']} "
            f"(Request: {error_info['method']} {error_info['path']}, "
            f"IP: {error_info['client_ip']})"
        )

        self.logger.log(
            log_level,
            log_message,
            extra={
                "error_info": error_info,
                "error_config": error_config
            }
        )

    def _update_metrics(self, error_type: str, error_info: Dict[str, Any]):
        """에러 메트릭 업데이트"""
        # 에러 카운터 업데이트
        if error_type not in self.error_counter:
            self.error_counter[error_type] = 0
        self.error_counter[error_type] += 1

        # Prometheus 메트릭 업데이트 (실제 구현에서는 Prometheus 클라이언트 사용)
        # error_rate_counter.labels(error_type=error_type).inc()

    def _create_error_response(
        self,
        error_info: Dict[str, Any],
        error_config: Dict[str, Any]
    ) -> JSONResponse:
        """에러 응답 생성"""
        response_data = {
            "error": {
                "code": error_info["error_type"].upper(),
                "message": self._get_user_friendly_message(error_info["error_type"]),
                "details": self._get_error_details(error_info),
                "timestamp": error_info["timestamp"],
                "request_id": error_info["request_id"]
            }
        }

        # 재시도 가능한 에러인 경우 Retry-After 헤더 추가
        headers = {}
        if error_config.get("retryable", False):
            retry_after = error_config.get("retry_after", 30)
            headers["Retry-After"] = str(retry_after)

        return JSONResponse(
            status_code=error_config["http_status"],
            content=response_data,
            headers=headers
        )

    def _get_user_friendly_message(self, error_type: str) -> str:
        """사용자 친화적 에러 메시지"""
        messages = {
            "validation_error": "입력 데이터가 올바르지 않습니다.",
            "authentication_error": "인증이 필요합니다.",
            "authorization_error": "이 작업을 수행할 권한이 없습니다.",
            "not_found_error": "요청한 리소스를 찾을 수 없습니다.",
            "rate_limit_error": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.",
            "internal_error": "서버 내부 오류가 발생했습니다.",
            "service_unavailable": "서비스가 일시적으로 사용할 수 없습니다.",
            "file_validation_error": "파일 검증에 실패했습니다.",
            "storage_error": "파일 저장 중 오류가 발생했습니다.",
            "network_error": "네트워크 연결 오류가 발생했습니다."
        }
        return messages.get(error_type, "알 수 없는 오류가 발생했습니다.")

    def _get_error_details(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """에러 상세 정보"""
        details = {}

        # 파일 관련 에러인 경우 파일 정보 추가
        if "file_size" in error_info.get("context", {}):
            details["file_size"] = error_info["context"]["file_size"]
        if "max_size" in error_info.get("context", {}):
            details["max_size"] = error_info["context"]["max_size"]
        if "file_type" in error_info.get("context", {}):
            details["file_type"] = error_info["context"]["file_type"]

        # 검증 에러인 경우 검증 실패 필드 추가
        if "validation_errors" in error_info.get("context", {}):
            details["validation_errors"] = error_info["context"]["validation_errors"]

        return details
```

## 🔄 전역 예외 처리

### FastAPI 전역 예외 핸들러

```python
# app/main.py
from app.services.error_handler_service import ErrorHandlerService

# 에러 핸들러 서비스 초기화
error_handler = ErrorHandlerService()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리 핸들러"""
    return error_handler.handle_error(exc, request)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리 핸들러"""
    return error_handler.handle_error(exc, request)

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """검증 예외 처리 핸들러"""
    context = {
        "validation_errors": exc.errors(),
        "field_errors": [error["loc"] for error in exc.errors()]
    }
    return error_handler.handle_error(exc, request, context)
```

## 🛡️ 서비스별 에러 처리

### 파일 업로드 에러 처리

```python
# app/services/file_validation_service.py
class FileValidationError(Exception):
    """파일 검증 에러"""
    pass

class FileValidationService:
    def validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """파일 검증"""
        try:
            # 파일 크기 검증
            file_size = len(file_content)
            if file_size > MAX_FILE_SIZE:
                raise FileValidationError(
                    f"File size {file_size} exceeds maximum limit {MAX_FILE_SIZE}"
                )

            # 파일 확장자 검증
            if not self._is_valid_extension(filename):
                raise FileValidationError(f"Invalid file extension: {filename}")

            # MIME 타입 검증
            mime_type = self._detect_mime_type(file_content)
            if not self._is_allowed_mime_type(mime_type):
                raise FileValidationError(f"Unsupported MIME type: {mime_type}")

            return {
                "valid": True,
                "file_size": file_size,
                "mime_type": mime_type
            }

        except FileValidationError:
            raise
        except Exception as e:
            # 예상치 못한 에러는 내부 에러로 변환
            raise FileValidationError(f"File validation failed: {str(e)}")
```

### 데이터베이스 에러 처리

```python
# app/services/database_service.py
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

class DatabaseService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def execute_with_retry(self, operation, max_retries=3):
        """재시도 로직이 포함된 데이터베이스 작업"""
        for attempt in range(max_retries):
            try:
                return operation()
            except OperationalError as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                    raise
                self.logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)  # 지수 백오프
            except IntegrityError as e:
                self.logger.error(f"Database integrity error: {e}")
                raise
            except SQLAlchemyError as e:
                self.logger.error(f"Database error: {e}")
                raise

    def safe_commit(self, session):
        """안전한 커밋"""
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            self.logger.error(f"Commit failed due to integrity error: {e}")
            raise
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Commit failed: {e}")
            raise
```

## 🔄 복구 메커니즘

### 자동 복구 시스템

```python
# app/services/recovery_service.py
import asyncio
from typing import Callable, Any
from functools import wraps

class RecoveryService:
    """자동 복구 서비스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.recovery_strategies = {}

    def register_recovery_strategy(
        self,
        error_type: str,
        strategy: Callable,
        max_retries: int = 3
    ):
        """복구 전략 등록"""
        self.recovery_strategies[error_type] = {
            "strategy": strategy,
            "max_retries": max_retries
        }

    async def execute_with_recovery(
        self,
        operation: Callable,
        error_type: str = "default",
        *args,
        **kwargs
    ) -> Any:
        """복구 로직이 포함된 작업 실행"""
        strategy = self.recovery_strategies.get(error_type)
        if not strategy:
            return await operation(*args, **kwargs)

        for attempt in range(strategy["max_retries"]):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if attempt == strategy["max_retries"] - 1:
                    self.logger.error(f"Operation failed after {strategy['max_retries']} attempts: {e}")
                    raise

                self.logger.warning(f"Operation failed (attempt {attempt + 1}): {e}")

                # 복구 전략 실행
                try:
                    await strategy["strategy"](e, attempt, *args, **kwargs)
                except Exception as recovery_error:
                    self.logger.error(f"Recovery strategy failed: {recovery_error}")

                # 지수 백오프
                await asyncio.sleep(2 ** attempt)

    def recovery_decorator(self, error_type: str = "default"):
        """복구 데코레이터"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await self.execute_with_recovery(func, error_type, *args, **kwargs)
            return wrapper
        return decorator

# 복구 전략 등록
recovery_service = RecoveryService()

# Redis 연결 복구 전략
async def redis_recovery_strategy(error, attempt, *args, **kwargs):
    """Redis 연결 복구 전략"""
    if "Connection refused" in str(error) or "timeout" in str(error).lower():
        # Redis 재연결 시도
        await redis_client.reconnect()
        await asyncio.sleep(1)

recovery_service.register_recovery_strategy("redis_error", redis_recovery_strategy)

# 데이터베이스 연결 복구 전략
async def database_recovery_strategy(error, attempt, *args, **kwargs):
    """데이터베이스 연결 복구 전략"""
    if "connection" in str(error).lower():
        # 데이터베이스 연결 재설정
        await database_service.reconnect()
        await asyncio.sleep(1)

recovery_service.register_recovery_strategy("database_error", database_recovery_strategy)
```

### 서킷 브레이커 패턴

```python
# app/services/circuit_breaker.py
import asyncio
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # 정상 상태
    OPEN = "open"          # 차단 상태
    HALF_OPEN = "half_open"  # 반열림 상태

class CircuitBreaker:
    """서킷 브레이커"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.logger = logging.getLogger(__name__)

    async def call(self, func, *args, **kwargs):
        """서킷 브레이커를 통한 함수 호출"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """성공 시 처리"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.logger.info("Circuit breaker reset to CLOSED")

    def _on_failure(self):
        """실패 시 처리"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부 확인"""
        if not self.last_failure_time:
            return True

        return datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)

# 서킷 브레이커 인스턴스 생성
redis_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=(ConnectionError, TimeoutError)
)

database_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=SQLAlchemyError
)
```

## 📊 에러 모니터링 및 알림

### 에러 메트릭 수집

```python
# app/services/error_monitoring_service.py
from prometheus_client import Counter, Histogram, Gauge

class ErrorMonitoringService:
    """에러 모니터링 서비스"""

    def __init__(self):
        # Prometheus 메트릭
        self.error_counter = Counter(
            'errors_total',
            'Total number of errors',
            ['error_type', 'endpoint', 'method']
        )

        self.error_rate = Counter(
            'error_rate',
            'Error rate per minute',
            ['error_type']
        )

        self.error_duration = Histogram(
            'error_duration_seconds',
            'Error handling duration',
            ['error_type']
        )

        self.active_errors = Gauge(
            'active_errors',
            'Number of active errors',
            ['error_type']
        )

        self.logger = logging.getLogger(__name__)

    def record_error(self, error_info: Dict[str, Any]):
        """에러 기록"""
        # 메트릭 업데이트
        self.error_counter.labels(
            error_type=error_info["error_type"],
            endpoint=error_info["path"],
            method=error_info["method"]
        ).inc()

        self.error_rate.labels(
            error_type=error_info["error_type"]
        ).inc()

        # 활성 에러 수 증가
        self.active_errors.labels(
            error_type=error_info["error_type"]
        ).inc()

        # 에러 로깅
        self.logger.error(
            f"Error recorded: {error_info['error_type']} - {error_info['error_message']}",
            extra={"error_info": error_info}
        )

    def clear_error(self, error_type: str):
        """에러 해결 시 호출"""
        self.active_errors.labels(error_type=error_type).dec()

    def get_error_statistics(self) -> Dict[str, Any]:
        """에러 통계 조회"""
        # 실제 구현에서는 Prometheus 쿼리 사용
        return {
            "total_errors": self.error_counter._value.sum(),
            "error_rate": self.error_rate._value.sum(),
            "active_errors": self.active_errors._value.sum()
        }
```

### 에러 알림 시스템

```python
# app/services/error_alert_service.py
import asyncio
from typing import List, Dict, Any

class ErrorAlertService:
    """에러 알림 서비스"""

    def __init__(self):
        self.alert_rules = {
            "high_error_rate": {
                "threshold": 0.05,  # 5%
                "window": 300,  # 5분
                "severity": "warning"
            },
            "critical_errors": {
                "threshold": 10,
                "window": 60,  # 1분
                "severity": "critical"
            },
            "service_unavailable": {
                "threshold": 1,
                "window": 30,  # 30초
                "severity": "critical"
            }
        }

        self.alert_channels = {
            "email": self._send_email_alert,
            "slack": self._send_slack_alert,
            "sms": self._send_sms_alert
        }

        self.logger = logging.getLogger(__name__)

    async def check_alerts(self, error_statistics: Dict[str, Any]):
        """알림 조건 확인"""
        for rule_name, rule in self.alert_rules.items():
            if await self._should_alert(rule_name, rule, error_statistics):
                await self._send_alert(rule_name, rule, error_statistics)

    async def _should_alert(
        self,
        rule_name: str,
        rule: Dict[str, Any],
        statistics: Dict[str, Any]
    ) -> bool:
        """알림 발송 여부 확인"""
        if rule_name == "high_error_rate":
            error_rate = statistics.get("error_rate", 0)
            return error_rate > rule["threshold"]

        elif rule_name == "critical_errors":
            critical_errors = statistics.get("critical_errors", 0)
            return critical_errors > rule["threshold"]

        elif rule_name == "service_unavailable":
            service_errors = statistics.get("service_unavailable", 0)
            return service_errors > rule["threshold"]

        return False

    async def _send_alert(
        self,
        rule_name: str,
        rule: Dict[str, Any],
        statistics: Dict[str, Any]
    ):
        """알림 발송"""
        alert_message = self._create_alert_message(rule_name, rule, statistics)

        # 여러 채널로 알림 발송
        for channel_name, channel_func in self.alert_channels.items():
            try:
                await channel_func(alert_message, rule["severity"])
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel_name}: {e}")

    def _create_alert_message(
        self,
        rule_name: str,
        rule: Dict[str, Any],
        statistics: Dict[str, Any]
    ) -> str:
        """알림 메시지 생성"""
        messages = {
            "high_error_rate": f"High error rate detected: {statistics.get('error_rate', 0):.2%}",
            "critical_errors": f"Critical errors detected: {statistics.get('critical_errors', 0)} errors",
            "service_unavailable": "Service unavailable errors detected"
        }

        return messages.get(rule_name, f"Alert: {rule_name}")

    async def _send_email_alert(self, message: str, severity: str):
        """이메일 알림 발송"""
        # 이메일 발송 로직
        pass

    async def _send_slack_alert(self, message: str, severity: str):
        """Slack 알림 발송"""
        # Slack 웹훅 발송 로직
        pass

    async def _send_sms_alert(self, message: str, severity: str):
        """SMS 알림 발송"""
        # SMS 발송 로직
        pass
```

## 🔧 복구 전략

### 데이터베이스 복구

```python
# app/services/database_recovery_service.py
class DatabaseRecoveryService:
    """데이터베이스 복구 서비스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backup_service = BackupService()

    async def recover_database(self, error_type: str) -> bool:
        """데이터베이스 복구"""
        try:
            if error_type == "connection_lost":
                return await self._recover_connection()
            elif error_type == "corruption":
                return await self._recover_from_backup()
            elif error_type == "performance":
                return await self._optimize_performance()
            else:
                self.logger.warning(f"Unknown database error type: {error_type}")
                return False
        except Exception as e:
            self.logger.error(f"Database recovery failed: {e}")
            return False

    async def _recover_connection(self) -> bool:
        """연결 복구"""
        try:
            # 연결 풀 재설정
            await database_service.reset_connection_pool()

            # 연결 테스트
            await database_service.test_connection()

            self.logger.info("Database connection recovered")
            return True
        except Exception as e:
            self.logger.error(f"Connection recovery failed: {e}")
            return False

    async def _recover_from_backup(self) -> bool:
        """백업에서 복구"""
        try:
            # 최신 백업 찾기
            latest_backup = await self.backup_service.get_latest_backup()

            if not latest_backup:
                self.logger.error("No backup available for recovery")
                return False

            # 데이터베이스 복구
            await self.backup_service.restore_database(latest_backup)

            self.logger.info("Database recovered from backup")
            return True
        except Exception as e:
            self.logger.error(f"Backup recovery failed: {e}")
            return False

    async def _optimize_performance(self) -> bool:
        """성능 최적화"""
        try:
            # 인덱스 재구성
            await database_service.rebuild_indexes()

            # 통계 업데이트
            await database_service.update_statistics()

            # 캐시 정리
            await cache_service.clear_cache()

            self.logger.info("Database performance optimized")
            return True
        except Exception as e:
            self.logger.error(f"Performance optimization failed: {e}")
            return False
```

### 파일 시스템 복구

```python
# app/services/file_system_recovery_service.py
class FileSystemRecoveryService:
    """파일 시스템 복구 서비스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def recover_file_system(self, error_type: str) -> bool:
        """파일 시스템 복구"""
        try:
            if error_type == "disk_full":
                return await self._handle_disk_full()
            elif error_type == "permission_error":
                return await self._fix_permissions()
            elif error_type == "corrupted_file":
                return await self._repair_corrupted_file()
            else:
                self.logger.warning(f"Unknown file system error type: {error_type}")
                return False
        except Exception as e:
            self.logger.error(f"File system recovery failed: {e}")
            return False

    async def _handle_disk_full(self) -> bool:
        """디스크 공간 부족 처리"""
        try:
            # 오래된 파일 정리
            await self._cleanup_old_files()

            # 임시 파일 정리
            await self._cleanup_temp_files()

            # 로그 파일 압축
            await self._compress_log_files()

            self.logger.info("Disk space recovered")
            return True
        except Exception as e:
            self.logger.error(f"Disk cleanup failed: {e}")
            return False

    async def _fix_permissions(self) -> bool:
        """권한 수정"""
        try:
            # 업로드 디렉토리 권한 수정
            upload_dir = Path("uploads")
            upload_dir.chmod(0o755)

            # 로그 디렉토리 권한 수정
            log_dir = Path("logs")
            log_dir.chmod(0o755)

            self.logger.info("File permissions fixed")
            return True
        except Exception as e:
            self.logger.error(f"Permission fix failed: {e}")
            return False

    async def _repair_corrupted_file(self) -> bool:
        """손상된 파일 복구"""
        try:
            # 파일 무결성 검사
            corrupted_files = await self._find_corrupted_files()

            for file_path in corrupted_files:
                # 백업에서 복구 시도
                if await self._restore_from_backup(file_path):
                    self.logger.info(f"File restored from backup: {file_path}")
                else:
                    # 파일 삭제
                    file_path.unlink()
                    self.logger.warning(f"Corrupted file deleted: {file_path}")

            return True
        except Exception as e:
            self.logger.error(f"File repair failed: {e}")
            return False
```

## 📋 에러 처리 체크리스트

### 배포 전 에러 처리 확인

- [ ] 전역 예외 핸들러가 구성됨
- [ ] 에러 분류 시스템이 구현됨
- [ ] 복구 메커니즘이 설정됨
- [ ] 에러 모니터링이 활성화됨
- [ ] 알림 시스템이 구성됨
- [ ] 에러 테스트가 통과됨

### 정기 에러 처리 점검

- [ ] 에러 로그 분석
- [ ] 복구 성공률 모니터링
- [ ] 알림 규칙 검토
- [ ] 에러 패턴 분석
- [ ] 복구 전략 개선

---

이 문서는 FileWallBall의 에러 처리 및 복구 시스템을 상세히 설명합니다. 에러 처리 관련 질문이나 개선 제안이 있으시면 개발팀에 문의해 주세요.
