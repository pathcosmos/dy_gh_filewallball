# FileWallBall API 엔드포인트 가이드

## 📋 개요

FileWallBall API는 파일 업로드, 다운로드, 관리 및 시스템 모니터링을 위한 RESTful API를 제공합니다. 이 문서는 모든 API 엔드포인트의 사용법과 응답 형식을 설명합니다.

## 🔐 인증 및 보안

### 기본 인증
- **IP 기반 인증**: 클라이언트 IP 주소를 기반으로 한 접근 제어
- **RBAC (Role-Based Access Control)**: 사용자 역할 기반 권한 관리
- **보안 헤더**: CORS, CSP, HSTS 등 보안 헤더 자동 적용

### 인증 헤더
```http
Authorization: Bearer <token>
X-API-Key: <api_key>
```

## 📁 파일 관리 API

### 1. 파일 업로드

#### 기본 업로드
```http
POST /upload
Content-Type: multipart/form-data
```

**요청 파라미터:**
- `file` (required): 업로드할 파일
- `category_id` (optional): 파일 카테고리 ID
- `tags` (optional): 파일 태그 목록
- `is_public` (optional): 공개 여부 (기본값: true)
- `description` (optional): 파일 설명

**응답 예시:**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.pdf",
  "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
  "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
  "message": "File uploaded successfully"
}
```

#### 고급 업로드 (v2)
```http
POST /api/v1/files/upload
Content-Type: multipart/form-data
```

**추가 기능:**
- 파일 중복 검사
- 메타데이터 자동 추출
- 썸네일 생성
- 보안 검증

**응답 예시:**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf",
  "upload_time": "2024-01-15T10:30:00Z",
  "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
  "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
  "thumbnail_url": "/thumbnail/550e8400-e29b-41d4-a716-446655440000",
  "is_duplicate": false,
  "original_file_id": null,
  "message": "File uploaded successfully"
}
```

### 2. 파일 정보 조회

```http
GET /files/{file_id}
```

**응답 예시:**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf",
  "upload_time": "2024-01-15T10:30:00Z",
  "last_accessed": "2024-01-15T11:00:00Z",
  "download_count": 5,
  "view_count": 12,
  "is_public": true,
  "category": "documents",
  "tags": ["pdf", "document"],
  "description": "Sample PDF document",
  "file_hash": "sha256:abc123...",
  "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
  "view_url": "/view/550e8400-e29b-41d4-a716-446655440000"
}
```

### 3. 파일 다운로드

```http
GET /download/{file_id}
```

**응답:**
- 파일 바이너리 데이터
- 적절한 Content-Type 헤더
- Content-Disposition 헤더 (파일명 포함)

### 4. 파일 미리보기

```http
GET /view/{file_id}
```

**지원 형식:**
- 이미지: PNG, JPG, GIF, WebP
- 문서: PDF (썸네일)
- 텍스트: TXT, MD, JSON, XML
- 기타: 다운로드 링크 제공

## 🔍 검색 및 필터링 API

### 1. 파일 검색

```http
GET /api/v1/files/search
```

**쿼리 파라미터:**
- `q` (optional): 검색어
- `category` (optional): 카테고리 필터
- `tags` (optional): 태그 필터 (쉼표로 구분)
- `date_from` (optional): 시작 날짜
- `date_to` (optional): 종료 날짜
- `size_min` (optional): 최소 파일 크기
- `size_max` (optional): 최대 파일 크기
- `mime_type` (optional): MIME 타입 필터
- `page` (optional): 페이지 번호 (기본값: 1)
- `size` (optional): 페이지당 항목 수 (기본값: 20)

**응답 예시:**
```json
{
  "files": [
    {
      "file_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "example.pdf",
      "file_size": 1024000,
      "upload_time": "2024-01-15T10:30:00Z",
      "download_url": "/download/550e8400-e29b-41d4-a716-446655440000"
    }
  ],
  "total": 150,
  "page": 1,
  "size": 20,
  "pages": 8
}
```

## 📊 통계 및 메트릭 API

### 1. 업로드 통계

```http
GET /api/v1/upload/statistics/{client_ip}
```

**쿼리 파라미터:**
- `days` (optional): 통계 기간 (기본값: 7)

**응답 예시:**
```json
{
  "client_ip": "192.168.1.100",
  "period_days": 7,
  "total_uploads": 25,
  "total_size": 52428800,
  "successful_uploads": 23,
  "failed_uploads": 2,
  "average_file_size": 2097152,
  "most_common_type": "image/jpeg",
  "upload_trend": [
    {"date": "2024-01-15", "count": 5, "size": 10485760},
    {"date": "2024-01-16", "count": 3, "size": 6291456}
  ]
}
```

### 2. 상세 메트릭

```http
GET /api/v1/metrics/detailed
```

**응답 예시:**
```json
{
  "system_metrics": {
    "total_files": 1250,
    "total_storage_used": 1073741824,
    "average_file_size": 858993,
    "files_by_type": {
      "image/jpeg": 450,
      "application/pdf": 200,
      "text/plain": 150
    }
  },
  "performance_metrics": {
    "average_upload_time": 2.5,
    "average_download_time": 0.8,
    "cache_hit_rate": 85.5,
    "error_rate": 0.5
  },
  "user_metrics": {
    "active_users_today": 45,
    "total_downloads_today": 120,
    "total_views_today": 300
  }
}
```

### 3. 에러 통계

```http
GET /api/v1/upload/errors
```

**쿼리 파라미터:**
- `days` (optional): 조회 기간 (기본값: 30)

**응답 예시:**
```json
{
  "period_days": 30,
  "total_errors": 15,
  "error_types": {
    "file_too_large": 8,
    "invalid_file_type": 4,
    "storage_full": 2,
    "network_error": 1
  },
  "error_trend": [
    {"date": "2024-01-15", "count": 2, "type": "file_too_large"},
    {"date": "2024-01-16", "count": 1, "type": "invalid_file_type"}
  ]
}
```

## 🔧 시스템 관리 API

### 1. 헬스 체크

```http
GET /health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "storage": "healthy"
  }
}
```

### 2. Prometheus 메트릭

```http
GET /metrics
```

**응답:** Prometheus 형식의 메트릭 데이터

### 3. 보안 헤더 테스트

```http
GET /api/v1/security/headers-test
```

**응답 예시:**
```json
{
  "headers": {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
  },
  "cors": {
    "allowed_origins": ["https://example.com"],
    "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
    "allowed_headers": ["Content-Type", "Authorization"]
  }
}
```

### 4. 검증 정책 조회

```http
GET /api/v1/validation/policy
```

**응답 예시:**
```json
{
  "file_size_limits": {
    "max_size": 104857600,
    "min_size": 1
  },
  "allowed_types": [
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/pdf",
    "text/plain"
  ],
  "blocked_types": [
    "application/x-executable",
    "application/x-msdownload"
  ],
  "virus_scan": true,
  "content_validation": true
}
```

## 🔐 권한 관리 API

### 1. 사용자 권한 조회

```http
GET /api/v1/rbac/permissions
Authorization: Bearer <token>
```

**응답 예시:**
```json
{
  "user_id": 123,
  "role": "admin",
  "permissions": [
    "file:upload",
    "file:download",
    "file:delete",
    "file:view",
    "admin:manage_users",
    "admin:view_logs"
  ],
  "restrictions": {
    "max_file_size": 52428800,
    "allowed_types": ["image/*", "application/pdf"],
    "daily_upload_limit": 100
  }
}
```

## 📝 감사 로그 API

### 1. 감사 로그 조회

```http
GET /api/v1/audit/logs
Authorization: Bearer <token>
```

**쿼리 파라미터:**
- `page` (optional): 페이지 번호 (기본값: 1)
- `size` (optional): 페이지당 로그 수 (기본값: 50)
- `user_id` (optional): 사용자 ID 필터
- `action` (optional): 액션 필터 (create, read, update, delete)
- `resource_type` (optional): 리소스 타입 필터 (file, user, system)
- `status` (optional): 상태 필터 (success, failed, denied)
- `date_from` (optional): 시작 날짜
- `date_to` (optional): 종료 날짜
- `ip_address` (optional): IP 주소 필터

**응답 예시:**
```json
{
  "logs": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "user_id": 123,
      "username": "john.doe",
      "action": "file:upload",
      "resource_type": "file",
      "resource_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "success",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "details": {
        "filename": "example.pdf",
        "file_size": 1024000
      }
    }
  ],
  "total": 150,
  "page": 1,
  "size": 50,
  "pages": 3
}
```

## 🗑️ 관리 API

### 1. 에러 로그 정리

```http
DELETE /api/v1/upload/errors/cleanup
Authorization: Bearer <admin_token>
```

**쿼리 파라미터:**
- `days` (optional): 보관 기간 (기본값: 90)

**응답 예시:**
```json
{
  "deleted_count": 150,
  "retention_days": 90,
  "message": "Error logs cleaned up successfully"
}
```

## 📋 IP 인증 API

### 1. IP 주소 등록

```http
POST /api/v1/ip-auth/register
Content-Type: application/json
```

**요청 본문:**
```json
{
  "ip_address": "192.168.1.100",
  "description": "Office network",
  "allowed_actions": ["upload", "download", "view"],
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
  }
}
```

### 2. IP 주소 조회

```http
GET /api/v1/ip-auth/{ip_address}
```

### 3. IP 주소 목록

```http
GET /api/v1/ip-auth
```

### 4. IP 주소 삭제

```http
DELETE /api/v1/ip-auth/{ip_address}
```

## ⚠️ 에러 응답 형식

모든 API는 일관된 에러 응답 형식을 사용합니다:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "File size exceeds maximum limit",
    "details": {
      "file_size": 104857600,
      "max_size": 52428800
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### 일반적인 에러 코드

| 코드 | 설명 | HTTP 상태 |
|------|------|-----------|
| `VALIDATION_ERROR` | 입력 데이터 검증 실패 | 400 |
| `UNAUTHORIZED` | 인증 실패 | 401 |
| `FORBIDDEN` | 권한 부족 | 403 |
| `NOT_FOUND` | 리소스를 찾을 수 없음 | 404 |
| `RATE_LIMIT_EXCEEDED` | 요청 한도 초과 | 429 |
| `INTERNAL_ERROR` | 서버 내부 오류 | 500 |
| `SERVICE_UNAVAILABLE` | 서비스 사용 불가 | 503 |

## 📊 요청 제한

### 기본 제한
- **파일 업로드**: 최대 100MB
- **API 요청**: 분당 60회, 시간당 1000회
- **동시 업로드**: 최대 5개 파일

### IP별 제한
- **신뢰할 수 있는 IP**: 더 높은 제한 적용 가능
- **차단된 IP**: 모든 요청 거부

## 🔄 웹훅 및 알림

### 업로드 완료 웹훅
```http
POST /api/v1/webhooks/upload-complete
Content-Type: application/json
```

**요청 본문:**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.pdf",
  "upload_time": "2024-01-15T10:30:00Z",
  "file_size": 1024000,
  "uploader_ip": "192.168.1.100"
}
```

## 📝 사용 예시

### Python 클라이언트 예시

```python
import requests

# 파일 업로드
with open('example.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/upload', files=files)
    file_data = response.json()

# 파일 다운로드
file_id = file_data['file_id']
response = requests.get(f'http://localhost:8000/download/{file_id}')
with open('downloaded_file.pdf', 'wb') as f:
    f.write(response.content)

# 파일 정보 조회
response = requests.get(f'http://localhost:8000/files/{file_id}')
file_info = response.json()
```

### cURL 예시

```bash
# 파일 업로드
curl -X POST -F "file=@example.pdf" http://localhost:8000/upload

# 파일 다운로드
curl -O http://localhost:8000/download/550e8400-e29b-41d4-a716-446655440000

# 통계 조회
curl http://localhost:8000/api/v1/upload/statistics/192.168.1.100
```

## 🔧 개발 및 테스트

### 개발 환경 설정
```bash
# 환경 변수 설정
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=filewallball2024

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API 문서
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

이 문서는 FileWallBall API의 모든 엔드포인트와 사용법을 설명합니다. 추가 질문이나 기능 요청이 있으시면 개발팀에 문의해 주세요.
