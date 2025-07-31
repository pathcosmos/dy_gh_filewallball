# FileWallBall 보안 및 인증 가이드

## 🔐 개요

FileWallBall은 다층 보안 아키텍처를 통해 파일 업로드, 저장, 접근을 안전하게 관리합니다. 이 문서는 구현된 보안 기능들과 인증 메커니즘을 상세히 설명합니다.

## 🛡️ 보안 아키텍처

### 다층 보안 모델

```
┌─────────────────────────────────────┐
│           클라이언트 레이어           │
│  (IP 기반 접근 제어, Rate Limiting)  │
├─────────────────────────────────────┤
│           네트워크 레이어            │
│  (보안 헤더, CORS, HTTPS)           │
├─────────────────────────────────────┤
│         애플리케이션 레이어          │
│  (RBAC, 파일 검증, 감사 로그)        │
├─────────────────────────────────────┤
│           데이터 레이어              │
│  (암호화, 백업, 접근 제어)           │
└─────────────────────────────────────┘
```

## 🔒 IP 기반 인증 시스템

### IP 인증 서비스 (`ip_auth_service.py`)

IP 기반 인증은 클라이언트의 IP 주소를 기반으로 접근을 제어하는 시스템입니다.

#### 주요 기능

1. **IP 주소 등록 및 관리**
2. **액션별 권한 제어**
3. **Rate Limiting 설정**
4. **IP 블랙리스트/화이트리스트**

#### 데이터베이스 스키마

```sql
CREATE TABLE ip_auth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    description TEXT,
    allowed_actions TEXT,  -- JSON: ["upload", "download", "view"]
    rate_limit_config TEXT,  -- JSON: {"requests_per_minute": 60, "requests_per_hour": 1000}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 사용 예시

```python
from app.services.ip_auth_service import IPAuthService

# IP 인증 서비스 초기화
ip_auth = IPAuthService()

# IP 주소 등록
ip_auth.register_ip(
    ip_address="192.168.1.100",
    description="Office network",
    allowed_actions=["upload", "download", "view"],
    rate_limit={"requests_per_minute": 60, "requests_per_hour": 1000}
)

# IP 인증 확인
if ip_auth.is_authorized("192.168.1.100", "upload"):
    # 업로드 허용
    pass
else:
    # 업로드 거부
    pass
```

#### API 엔드포인트

```http
# IP 주소 등록
POST /api/v1/ip-auth/register
Content-Type: application/json

{
  "ip_address": "192.168.1.100",
  "description": "Office network",
  "allowed_actions": ["upload", "download", "view"],
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
  }
}

# IP 주소 조회
GET /api/v1/ip-auth/{ip_address}

# IP 주소 목록
GET /api/v1/ip-auth

# IP 주소 삭제
DELETE /api/v1/ip-auth/{ip_address}
```

## 👥 RBAC (Role-Based Access Control)

### RBAC 서비스 (`rbac_service.py`)

RBAC는 사용자 역할을 기반으로 권한을 관리하는 시스템입니다.

#### 역할 정의

```python
ROLES = {
    "admin": {
        "permissions": [
            "file:upload", "file:download", "file:delete", "file:view",
            "admin:manage_users", "admin:view_logs", "admin:system_config"
        ],
        "restrictions": {
            "max_file_size": 104857600,  # 100MB
            "allowed_types": ["*/*"],
            "daily_upload_limit": 1000
        }
    },
    "user": {
        "permissions": [
            "file:upload", "file:download", "file:view"
        ],
        "restrictions": {
            "max_file_size": 52428800,  # 50MB
            "allowed_types": ["image/*", "application/pdf", "text/*"],
            "daily_upload_limit": 100
        }
    },
    "guest": {
        "permissions": [
            "file:view"
        ],
        "restrictions": {
            "max_file_size": 10485760,  # 10MB
            "allowed_types": ["image/*"],
            "daily_upload_limit": 10
        }
    }
}
```

#### 권한 확인

```python
from app.services.rbac_service import RBACService

rbac = RBACService()

# 사용자 권한 확인
if rbac.has_permission(user_id=123, permission="file:upload"):
    # 업로드 허용
    pass

# 파일 크기 제한 확인
max_size = rbac.get_restriction(user_id=123, restriction="max_file_size")
if file_size <= max_size:
    # 파일 크기 허용
    pass
```

#### API 엔드포인트

```http
# 사용자 권한 조회
GET /api/v1/rbac/permissions
Authorization: Bearer <token>

Response:
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
    "max_file_size": 104857600,
    "allowed_types": ["*/*"],
    "daily_upload_limit": 1000
  }
}
```

## 🚦 Rate Limiting

### Rate Limiter 서비스 (`rate_limiter_service.py`)

Rate Limiting은 API 요청 빈도를 제한하여 시스템 보호와 공정한 사용을 보장합니다.

#### 구현 방식

1. **Redis 기반 카운터**
2. **Sliding Window 알고리즘**
3. **IP별 및 사용자별 제한**

#### 설정 예시

```python
RATE_LIMITS = {
    "default": {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "requests_per_day": 10000
    },
    "upload": {
        "requests_per_minute": 10,
        "requests_per_hour": 100,
        "requests_per_day": 1000
    },
    "download": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "requests_per_day": 5000
    }
}
```

#### 사용 예시

```python
from app.services.rate_limiter_service import RateLimiterService

rate_limiter = RateLimiterService()

# 요청 제한 확인
if rate_limiter.is_allowed("192.168.1.100", "upload"):
    # 업로드 허용
    pass
else:
    # 제한 초과
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

#### 응답 헤더

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642234567
Retry-After: 60
```

## 🛡️ 보안 헤더

### Security Headers Middleware (`security_headers.py`)

보안 헤더는 웹 애플리케이션의 보안을 강화하는 HTTP 헤더들을 자동으로 설정합니다.

#### 설정된 보안 헤더

```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}
```

#### CORS 설정

```python
CORS_CONFIG = {
    "allowed_origins": ["https://example.com", "https://admin.example.com"],
    "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
    "allowed_headers": ["Content-Type", "Authorization", "X-API-Key"],
    "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    "allow_credentials": True,
    "max_age": 86400
}
```

#### 테스트 엔드포인트

```http
GET /api/v1/security/headers-test

Response:
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

## 📝 감사 로그

### Audit Middleware (`audit_middleware.py`)

감사 로그는 모든 중요한 시스템 활동을 기록하여 보안 모니터링과 규정 준수를 지원합니다.

#### 로그 항목

```python
AUDIT_LOG_ENTRY = {
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
        "file_size": 1024000,
        "mime_type": "application/pdf"
    }
}
```

#### 데이터베이스 스키마

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    username VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API 엔드포인트

```http
# 감사 로그 조회
GET /api/v1/audit/logs
Authorization: Bearer <admin_token>

Query Parameters:
- page: 페이지 번호
- size: 페이지당 로그 수
- user_id: 사용자 ID 필터
- action: 액션 필터
- resource_type: 리소스 타입 필터
- status: 상태 필터
- date_from: 시작 날짜
- date_to: 종료 날짜
- ip_address: IP 주소 필터
```

## 🔍 파일 검증

### File Validation Service (`file_validation_service.py`)

파일 검증은 업로드된 파일의 안전성과 적합성을 확인합니다.

#### 검증 단계

1. **파일 크기 검증**
2. **MIME 타입 검증**
3. **파일 확장자 검증**
4. **바이러스 스캔 (선택적)**
5. **콘텐츠 검증**

#### 검증 정책

```python
VALIDATION_POLICY = {
    "file_size_limits": {
        "max_size": 104857600,  # 100MB
        "min_size": 1
    },
    "allowed_types": [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain", "text/markdown",
        "application/json", "text/xml"
    ],
    "blocked_types": [
        "application/x-executable",
        "application/x-msdownload",
        "application/x-msi"
    ],
    "virus_scan": True,
    "content_validation": True
}
```

#### API 엔드포인트

```http
# 검증 정책 조회
GET /api/v1/validation/policy

Response:
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

## 🔐 에러 처리 및 보안

### Error Handler Service (`error_handler_service.py`)

에러 처리 서비스는 보안 관련 에러를 적절히 처리하고 로깅합니다.

#### 에러 분류

```python
ERROR_TYPES = {
    "validation_error": "입력 데이터 검증 실패",
    "authentication_error": "인증 실패",
    "authorization_error": "권한 부족",
    "rate_limit_error": "요청 한도 초과",
    "file_validation_error": "파일 검증 실패",
    "storage_error": "저장소 오류",
    "network_error": "네트워크 오류",
    "internal_error": "서버 내부 오류"
}
```

#### 에러 응답 형식

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

## 🔧 보안 설정

### 환경 변수

```bash
# 보안 관련 환경 변수
SECURITY_SECRET_KEY=your-secret-key-here
SECURITY_ALGORITHM=HS256
SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=filewallball2024

# 데이터베이스 설정
DATABASE_URL=sqlite:///./filewallball.db
DATABASE_ENCRYPTION_KEY=your-encryption-key

# 파일 업로드 설정
MAX_FILE_SIZE=104857600
UPLOAD_DIR=./uploads
ALLOWED_FILE_TYPES=image/*,application/pdf,text/*
```

### 보안 모범 사례

1. **HTTPS 강제 사용**
   ```python
   # 모든 HTTP 요청을 HTTPS로 리다이렉트
   if request.url.scheme == "http":
       return RedirectResponse(url=str(request.url).replace("http://", "https://", 1))
   ```

2. **세션 관리**
   ```python
   # 세션 타임아웃 설정
   SESSION_TIMEOUT = 3600  # 1시간
   ```

3. **패스워드 정책**
   ```python
   PASSWORD_POLICY = {
       "min_length": 8,
       "require_uppercase": True,
       "require_lowercase": True,
       "require_digits": True,
       "require_special": True
   }
   ```

4. **API 키 관리**
   ```python
   # API 키 검증
   def validate_api_key(api_key: str):
       # API 키 형식 검증
       if not re.match(r'^[A-Za-z0-9]{32}$', api_key):
           raise ValueError("Invalid API key format")

       # 데이터베이스에서 API 키 확인
       return api_key_service.is_valid(api_key)
   ```

## 📊 보안 모니터링

### 보안 메트릭

```python
# Prometheus 메트릭
security_violations_counter = Counter(
    'security_violations_total',
    'Total number of security violations',
    ['violation_type', 'ip_address']
)

authentication_failures_counter = Counter(
    'authentication_failures_total',
    'Total number of authentication failures',
    ['failure_type', 'ip_address']
)

rate_limit_violations_counter = Counter(
    'rate_limit_violations_total',
    'Total number of rate limit violations',
    ['endpoint', 'ip_address']
)
```

### 보안 알림

```python
# 보안 이벤트 알림
SECURITY_ALERTS = {
    "multiple_failed_logins": {
        "threshold": 5,
        "time_window": 300,  # 5분
        "action": "block_ip"
    },
    "suspicious_file_upload": {
        "threshold": 1,
        "action": "flag_for_review"
    },
    "rate_limit_exceeded": {
        "threshold": 10,
        "time_window": 60,  # 1분
        "action": "temporary_ban"
    }
}
```

## 🧪 보안 테스트

### 보안 테스트 스크립트

```python
# test_security.py
import requests
import pytest

def test_ip_authentication():
    """IP 인증 테스트"""
    # 허용되지 않은 IP에서 접근 시도
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": ("test.txt", b"test content")},
        headers={"X-Forwarded-For": "192.168.1.200"}
    )
    assert response.status_code == 403

def test_rate_limiting():
    """Rate Limiting 테스트"""
    # 연속 요청으로 한도 초과 테스트
    for i in range(65):  # 기본 한도 60회 초과
        response = requests.get("http://localhost:8000/health")
        if i >= 60:
            assert response.status_code == 429

def test_file_validation():
    """파일 검증 테스트"""
    # 실행 파일 업로드 시도
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": ("test.exe", b"fake executable")}
    )
    assert response.status_code == 400
    assert "executable" in response.json()["error"]["message"]
```

## 📋 보안 체크리스트

### 배포 전 보안 검사

- [ ] 모든 환경 변수가 안전하게 설정됨
- [ ] HTTPS가 강제됨
- [ ] 보안 헤더가 올바르게 설정됨
- [ ] CORS 정책이 적절히 구성됨
- [ ] Rate Limiting이 활성화됨
- [ ] IP 인증이 구성됨
- [ ] RBAC 권한이 설정됨
- [ ] 감사 로그가 활성화됨
- [ ] 파일 검증이 구현됨
- [ ] 에러 처리가 적절함
- [ ] 보안 테스트가 통과됨

### 정기 보안 점검

- [ ] 보안 로그 검토
- [ ] 권한 매트릭스 검토
- [ ] IP 화이트리스트/블랙리스트 업데이트
- [ ] Rate Limiting 설정 검토
- [ ] 파일 검증 정책 업데이트
- [ ] 보안 헤더 설정 검토
- [ ] 감사 로그 보관 정책 확인

---

이 문서는 FileWallBall의 보안 및 인증 시스템을 상세히 설명합니다. 보안 관련 질문이나 개선 제안이 있으시면 보안팀에 문의해 주세요.
