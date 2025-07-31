# FileWallBall 서비스 아키텍처 가이드

## 🏗️ 개요

FileWallBall은 마이크로서비스 아키텍처 패턴을 따르는 모듈화된 서비스 구조를 가지고 있습니다. 각 서비스는 특정 도메인 책임을 담당하며, 느슨한 결합과 높은 응집도를 유지합니다.

## 📋 서비스 아키텍처 개요

### 서비스 계층 구조

```
┌─────────────────────────────────────┐
│           API 레이어                │
│  (FastAPI 라우터, 엔드포인트)       │
├─────────────────────────────────────┤
│           서비스 레이어              │
│  (비즈니스 로직, 도메인 서비스)      │
├─────────────────────────────────────┤
│           리포지토리 레이어          │
│  (데이터 접근, ORM)                 │
├─────────────────────────────────────┤
│           인프라 레이어              │
│  (데이터베이스, Redis, 파일 시스템)  │
└─────────────────────────────────────┘
```

## 🔧 핵심 서비스 구성

### 1. 파일 관리 서비스

#### FileService (`app/services/file_service.py`)
**목적**: 파일 업로드, 다운로드, 조회의 기본 기능 제공

```python
class FileService:
    """파일 관리 기본 서비스"""

    async def upload_file(self, file: UploadFile, user_id: str) -> FileInfo:
        """파일 업로드 처리"""

    async def download_file(self, file_id: str, user_id: str) -> FileResponse:
        """파일 다운로드 처리"""

    async def get_file_info(self, file_id: str, user_id: str) -> FileInfo:
        """파일 정보 조회"""

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """파일 삭제"""
```

#### FileStorageService (`app/services/file_storage_service.py`)
**목적**: 파일 저장소 관리 및 파일 시스템 작업

```python
class FileStorageService:
    """파일 저장소 관리 서비스"""

    async def save_file(self, file: UploadFile, file_id: str) -> Path:
        """파일을 저장소에 저장"""

    async def get_file_path(self, file_id: str) -> Path:
        """파일 경로 조회"""

    async def delete_file(self, file_id: str) -> bool:
        """파일 시스템에서 파일 삭제"""

    async def get_file_size(self, file_id: str) -> int:
        """파일 크기 조회"""

    async def check_file_exists(self, file_id: str) -> bool:
        """파일 존재 여부 확인"""
```

#### FileValidationService (`app/services/file_validation_service.py`)
**목적**: 파일 검증 및 보안 검사

```python
class FileValidationService:
    """파일 검증 서비스"""

    async def validate_file(self, file: UploadFile) -> ValidationResult:
        """파일 검증 수행"""

    async def check_file_type(self, file: UploadFile) -> bool:
        """파일 타입 검증"""

    async def check_file_size(self, file: UploadFile) -> bool:
        """파일 크기 검증"""

    async def scan_for_viruses(self, file_path: Path) -> bool:
        """바이러스 스캔"""

    async def validate_content(self, file_path: Path) -> bool:
        """파일 콘텐츠 검증"""
```

### 2. 캐싱 서비스

#### CacheService (`app/services/cache_service.py`)
**목적**: Redis 기반 고성능 캐싱 시스템

```python
class CacheService:
    """Redis 캐싱 서비스"""

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회"""

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """캐시에 데이터 저장"""

    async def delete(self, key: str) -> bool:
        """캐시에서 데이터 삭제"""

    async def exists(self, key: str) -> bool:
        """캐시 키 존재 여부 확인"""

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """여러 키의 데이터 조회"""

    async def set_many(self, data: Dict[str, Any], ttl: int = None) -> bool:
        """여러 데이터를 캐시에 저장"""
```

#### CacheInvalidationService (`app/services/cache_invalidation_service.py`)
**목적**: 캐시 무효화 및 동기화 관리

```python
class CacheInvalidationService:
    """캐시 무효화 서비스"""

    async def invalidate_pattern(self, pattern: str) -> int:
        """패턴에 맞는 캐시 키 무효화"""

    async def invalidate_file_cache(self, file_id: str) -> bool:
        """파일 관련 캐시 무효화"""

    async def invalidate_user_cache(self, user_id: str) -> bool:
        """사용자 관련 캐시 무효화"""

    async def clear_all_cache(self) -> bool:
        """전체 캐시 초기화"""

    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
```

#### CacheMonitoringService (`app/services/cache_monitoring_service.py`)
**목적**: 캐시 성능 모니터링 및 최적화

```python
class CacheMonitoringService:
    """캐시 모니터링 서비스"""

    async def get_hit_rate(self) -> float:
        """캐시 히트율 조회"""

    async def get_memory_usage(self) -> Dict[str, Any]:
        """메모리 사용량 조회"""

    async def get_connection_stats(self) -> Dict[str, Any]:
        """연결 통계 조회"""

    async def monitor_performance(self) -> PerformanceMetrics:
        """성능 메트릭 수집"""

    async def optimize_cache(self) -> OptimizationResult:
        """캐시 최적화 수행"""
```

### 3. 인증 및 권한 서비스

#### IPAuthService (`app/services/ip_auth_service.py`)
**목적**: IP 기반 인증 및 접근 제어

```python
class IPAuthService:
    """IP 기반 인증 서비스"""

    async def register_ip(self, ip_address: str, config: IPConfig) -> bool:
        """IP 주소 등록"""

    async def is_authorized(self, ip_address: str, action: str) -> bool:
        """IP 인증 확인"""

    async def get_ip_config(self, ip_address: str) -> Optional[IPConfig]:
        """IP 설정 조회"""

    async def update_ip_config(self, ip_address: str, config: IPConfig) -> bool:
        """IP 설정 업데이트"""

    async def remove_ip(self, ip_address: str) -> bool:
        """IP 주소 제거"""
```

#### RBACService (`app/services/rbac_service.py`)
**목적**: 역할 기반 접근 제어

```python
class RBACService:
    """RBAC 서비스"""

    async def has_permission(self, user_id: str, permission: str) -> bool:
        """권한 확인"""

    async def get_user_role(self, user_id: str) -> str:
        """사용자 역할 조회"""

    async def get_permissions(self, user_id: str) -> List[str]:
        """사용자 권한 목록 조회"""

    async def assign_role(self, user_id: str, role: str) -> bool:
        """역할 할당"""

    async def revoke_role(self, user_id: str) -> bool:
        """역할 해제"""
```

### 4. 레이트 리미팅 서비스

#### RateLimiterService (`app/services/rate_limiter_service.py`)
**목적**: 요청 제한 및 속도 제어

```python
class RateLimiterService:
    """레이트 리미터 서비스"""

    async def is_allowed(self, identifier: str, action: str) -> bool:
        """요청 허용 여부 확인"""

    async def record_request(self, identifier: str, action: str) -> bool:
        """요청 기록"""

    async def get_remaining_requests(self, identifier: str, action: str) -> int:
        """남은 요청 수 조회"""

    async def reset_limits(self, identifier: str) -> bool:
        """제한 초기화"""

    async def block_identifier(self, identifier: str, duration: int) -> bool:
        """식별자 차단"""
```

#### AdvancedRateLimiter (`app/services/advanced_rate_limiter.py`)
**목적**: 고급 레이트 리미팅 기능

```python
class AdvancedRateLimiter:
    """고급 레이트 리미터"""

    async def check_sliding_window(self, key: str, limit: int, window: int) -> bool:
        """슬라이딩 윈도우 기반 제한 확인"""

    async def check_token_bucket(self, key: str, capacity: int, rate: float) -> bool:
        """토큰 버킷 알고리즘 기반 제한 확인"""

    async def get_rate_limit_info(self, key: str) -> RateLimitInfo:
        """레이트 리미트 정보 조회"""

    async def apply_dynamic_limits(self, key: str, factors: Dict[str, Any]) -> bool:
        """동적 제한 적용"""
```

### 5. 모니터링 및 메트릭 서비스

#### HealthCheckService (`app/services/health_check_service.py`)
**목적**: 시스템 상태 모니터링

```python
class HealthCheckService:
    """헬스체크 서비스"""

    async def check_database(self) -> HealthStatus:
        """데이터베이스 상태 확인"""

    async def check_redis(self) -> HealthStatus:
        """Redis 상태 확인"""

    async def check_storage(self) -> HealthStatus:
        """저장소 상태 확인"""

    async def get_overall_health(self) -> OverallHealth:
        """전체 시스템 상태 조회"""

    async def get_detailed_health(self) -> DetailedHealth:
        """상세 시스템 상태 조회"""
```

#### StatisticsService (`app/services/statistics_service.py`)
**목적**: 통계 데이터 수집 및 분석

```python
class StatisticsService:
    """통계 서비스"""

    async def record_upload(self, file_info: FileInfo, user_id: str) -> bool:
        """업로드 통계 기록"""

    async def record_download(self, file_id: str, user_id: str) -> bool:
        """다운로드 통계 기록"""

    async def get_upload_statistics(self, user_id: str, days: int) -> UploadStats:
        """업로드 통계 조회"""

    async def get_system_statistics(self) -> SystemStats:
        """시스템 통계 조회"""

    async def generate_reports(self, report_type: str, params: Dict) -> Report:
        """보고서 생성"""
```

### 6. 감사 및 로깅 서비스

#### AuditLogService (`app/services/audit_log_service.py`)
**목적**: 감사 로그 관리 및 보안 모니터링

```python
class AuditLogService:
    """감사 로그 서비스"""

    async def log_action(self, action: AuditAction, user_id: str,
                        resource_type: str, resource_id: str,
                        result: AuditResult, details: Dict = None) -> bool:
        """감사 로그 기록"""

    async def get_audit_logs(self, filters: AuditFilters) -> List[AuditLog]:
        """감사 로그 조회"""

    async def get_audit_statistics(self, days: int) -> AuditStats:
        """감사 통계 조회"""

    async def cleanup_old_logs(self, days: int) -> int:
        """오래된 로그 정리"""

    async def export_audit_logs(self, format: str, filters: AuditFilters) -> bytes:
        """감사 로그 내보내기"""
```

### 7. 백그라운드 작업 서비스

#### BackgroundTaskService (`app/services/background_task_service.py`)
**목적**: 비동기 작업 관리 및 처리

```python
class BackgroundTaskService:
    """백그라운드 작업 서비스"""

    async def submit_task(self, task_type: TaskType, data: Dict) -> str:
        """작업 제출"""

    async def get_task_status(self, task_id: str) -> TaskStatus:
        """작업 상태 조회"""

    async def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""

    async def get_task_result(self, task_id: str) -> Any:
        """작업 결과 조회"""

    async def list_tasks(self, filters: TaskFilters) -> List[TaskInfo]:
        """작업 목록 조회"""
```

#### SchedulerService (`app/services/scheduler_service.py`)
**목적**: 스케줄링된 작업 관리

```python
class SchedulerService:
    """스케줄러 서비스"""

    async def schedule_job(self, job_type: str, schedule: str, data: Dict) -> str:
        """작업 스케줄링"""

    async def cancel_scheduled_job(self, job_id: str) -> bool:
        """스케줄된 작업 취소"""

    async def get_scheduled_jobs(self) -> List[ScheduledJob]:
        """스케줄된 작업 목록 조회"""

    async def update_schedule(self, job_id: str, new_schedule: str) -> bool:
        """스케줄 업데이트"""
```

### 8. 파일 처리 서비스

#### FilePreviewService (`app/services/file_preview_service.py`)
**목적**: 파일 미리보기 및 변환

```python
class FilePreviewService:
    """파일 미리보기 서비스"""

    async def generate_preview(self, file_id: str, format: str = "html") -> bytes:
        """파일 미리보기 생성"""

    async def is_preview_supported(self, file_type: str) -> bool:
        """미리보기 지원 여부 확인"""

    async def get_preview_formats(self) -> List[str]:
        """지원되는 미리보기 형식 조회"""

    async def convert_file(self, file_id: str, target_format: str) -> bytes:
        """파일 형식 변환"""
```

#### ThumbnailService (`app/services/thumbnail_service.py`)
**목적**: 썸네일 생성 및 관리

```python
class ThumbnailService:
    """썸네일 서비스"""

    async def generate_thumbnail(self, file_id: str, size: str = "medium") -> bytes:
        """썸네일 생성"""

    async def get_thumbnail(self, file_id: str, size: str = "medium") -> bytes:
        """썸네일 조회"""

    async def delete_thumbnail(self, file_id: str) -> bool:
        """썸네일 삭제"""

    async def get_thumbnail_info(self, file_id: str) -> ThumbnailInfo:
        """썸네일 정보 조회"""
```

#### MetadataService (`app/services/metadata_service.py`)
**목적**: 파일 메타데이터 관리

```python
class MetadataService:
    """메타데이터 서비스"""

    async def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """메타데이터 추출"""

    async def store_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """메타데이터 저장"""

    async def get_metadata(self, file_id: str) -> Dict[str, Any]:
        """메타데이터 조회"""

    async def update_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """메타데이터 업데이트"""

    async def search_by_metadata(self, criteria: Dict[str, Any]) -> List[str]:
        """메타데이터 기반 검색"""
```

### 9. 파일 관리 고급 서비스

#### FileListService (`app/services/file_list_service.py`)
**목적**: 파일 목록 관리 및 검색

```python
class FileListService:
    """파일 목록 서비스"""

    async def get_file_list(self, filters: FileFilters,
                           pagination: Pagination) -> FileListResult:
        """파일 목록 조회"""

    async def search_files(self, query: str, filters: FileFilters) -> List[FileInfo]:
        """파일 검색"""

    async def get_file_statistics(self, user_id: str = None) -> FileStats:
        """파일 통계 조회"""

    async def get_file_categories(self) -> List[Category]:
        """파일 카테고리 조회"""
```

#### FileDeletionService (`app/services/file_deletion_service.py`)
**목적**: 파일 삭제 및 복구 관리

```python
class FileDeletionService:
    """파일 삭제 서비스"""

    async def soft_delete_file(self, file_id: str, user_id: str) -> bool:
        """소프트 삭제"""

    async def hard_delete_file(self, file_id: str, user_id: str) -> bool:
        """하드 삭제"""

    async def restore_file(self, file_id: str, user_id: str) -> bool:
        """파일 복구"""

    async def get_deleted_files(self, user_id: str = None) -> List[FileInfo]:
        """삭제된 파일 목록 조회"""

    async def cleanup_deleted_files(self, days: int) -> int:
        """삭제된 파일 정리"""
```

### 10. 에러 처리 서비스

#### ErrorHandlerService (`app/services/error_handler_service.py`)
**목적**: 중앙화된 에러 처리 및 로깅

```python
class ErrorHandlerService:
    """에러 처리 서비스"""

    async def handle_error(self, error: Exception, context: Dict = None) -> ErrorResponse:
        """에러 처리"""

    async def log_error(self, error: Exception, level: str = "error") -> bool:
        """에러 로깅"""

    async def get_error_statistics(self, days: int) -> ErrorStats:
        """에러 통계 조회"""

    async def classify_error(self, error: Exception) -> ErrorType:
        """에러 분류"""

    async def should_retry(self, error: Exception) -> bool:
        """재시도 여부 확인"""
```

## 🔄 서비스 간 의존성

### 의존성 주입 구조

```python
# app/main.py
from app.services.file_service import FileService
from app.services.cache_service import CacheService
from app.services.auth_service import AuthService

# 서비스 인스턴스 생성
file_service = FileService()
cache_service = CacheService()
auth_service = AuthService()

# 의존성 주입
def get_file_service() -> FileService:
    return file_service

def get_cache_service() -> CacheService:
    return cache_service

def get_auth_service() -> AuthService:
    return auth_service
```

### 서비스 통신 패턴

1. **동기 통신**: 직접 메서드 호출
2. **비동기 통신**: async/await 패턴
3. **이벤트 기반**: 백그라운드 작업을 통한 이벤트 처리
4. **캐시 기반**: Redis를 통한 서비스 간 데이터 공유

## 📊 서비스 모니터링

### 성능 메트릭

```python
# 각 서비스별 메트릭 수집
class ServiceMetrics:
    """서비스 메트릭 수집"""

    async def record_service_call(self, service_name: str, method: str, duration: float):
        """서비스 호출 기록"""

    async def record_service_error(self, service_name: str, error_type: str):
        """서비스 에러 기록"""

    async def get_service_performance(self, service_name: str) -> PerformanceMetrics:
        """서비스 성능 조회"""
```

### 헬스체크

```python
# 각 서비스별 헬스체크
class ServiceHealthCheck:
    """서비스 헬스체크"""

    async def check_service_health(self, service_name: str) -> HealthStatus:
        """서비스 상태 확인"""

    async def get_all_services_health(self) -> Dict[str, HealthStatus]:
        """모든 서비스 상태 조회"""
```

## 🚀 서비스 확장성

### 수평 확장 전략

1. **무상태 서비스**: 모든 서비스는 상태를 외부 저장소에 저장
2. **로드 밸런싱**: 여러 인스턴스 간 요청 분산
3. **데이터 파티셔닝**: 데이터를 여러 노드에 분산 저장
4. **캐시 계층**: Redis를 통한 성능 최적화

### 수직 확장 전략

1. **리소스 증가**: CPU, 메모리, 스토리지 증가
2. **성능 최적화**: 코드 최적화 및 알고리즘 개선
3. **비동기 처리**: 백그라운드 작업을 통한 응답 시간 개선

## 🔧 서비스 개발 가이드

### 새 서비스 추가 시 체크리스트

- [ ] 서비스 인터페이스 정의
- [ ] 의존성 주입 설정
- [ ] 에러 처리 구현
- [ ] 로깅 및 모니터링 추가
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 문서화 완료
- [ ] 성능 테스트 수행

### 서비스 설계 원칙

1. **단일 책임 원칙**: 각 서비스는 하나의 명확한 책임을 가짐
2. **개방-폐쇄 원칙**: 확장에는 열려있고 수정에는 닫혀있음
3. **의존성 역전 원칙**: 추상화에 의존하고 구체화에 의존하지 않음
4. **인터페이스 분리 원칙**: 클라이언트는 사용하지 않는 인터페이스에 의존하지 않음

---

이 문서는 FileWallBall의 서비스 아키텍처를 상세히 설명합니다. 서비스 관련 질문이나 개선 제안이 있으시면 개발팀에 문의해 주세요.
