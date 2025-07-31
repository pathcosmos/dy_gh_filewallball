# FileWallBall Swagger API 문서화 가이드

## 📚 개요

FileWallBall 프로젝트는 FastAPI의 자동 문서화 기능과 커스텀 Swagger UI를 통해 완전한 API 문서화를 제공합니다. 이 문서는 구현된 Swagger 문서화 시스템과 사용법을 상세히 설명합니다.

## 🔧 Swagger 문서화 아키텍처
### 문서화 시스템 구성

```
┌─────────────────────────────────────┐
│           Swagger UI                │
│  (커스텀 테마, 태그 그룹화)          │
├─────────────────────────────────────┤
│           OpenAPI 스키마            │
│  (자동 생성 + 커스텀 확장)          │
├─────────────────────────────────────┤
│           Pydantic 모델             │
│  (응답 모델, 에러 스키마)            │
├─────────────────────────────────────┤
│           FastAPI 엔드포인트         │
│  (summary, description, tags)       │
└─────────────────────────────────────┘
```

## 📋 구현된 문서화 구성요소

### 1. OpenAPI 메타데이터 설정

#### 기본 정보 설정
```python
# app/main.py
app = FastAPI(
    title="FileWallBall API",
    description="""
    # FileWallBall - 안전한 파일 공유 플랫폼 API

    FileWallBall은 안전하고 효율적인 파일 업로드, 저장, 공유를 위한 RESTful API 서비스입니다.

    ## 주요 기능
    * **파일 업로드**: 최대 100MB 파일 업로드 지원, 다양한 파일 형식 검증
    * **파일 관리**: 파일 조회, 다운로드, 미리보기, 삭제 기능
    * **보안**: IP 기반 인증, RBAC 권한 관리, 레이트 리미팅
    * **캐싱**: Redis 기반 고성능 캐싱 시스템
    * **모니터링**: Prometheus 메트릭, 감사 로그, 성능 모니터링
    * **백그라운드 작업**: 비동기 파일 처리, 썸네일 생성

    ## 인증
    대부분의 엔드포인트는 JWT Bearer 토큰 인증이 필요합니다.
    IP 기반 인증을 사용하는 엔드포인트는 별도로 표시됩니다.
    """,
    version="1.0.0",
    contact={
        "name": "FileWallBall Team",
        "email": "support@filewallball.com",
        "url": "https://github.com/filewallball/api",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "개발 환경"},
        {"url": "https://api.filewallball.com", "description": "프로덕션 환경"},
    ],
)
```

#### 태그 정의
```python
openapi_tags = [
    {"name": "파일 업로드", "description": "파일 업로드 관련 엔드포인트. 다양한 형식의 파일을 안전하게 업로드할 수 있습니다."},
    {"name": "파일 관리", "description": "파일 조회, 다운로드, 미리보기, 삭제 등 파일 관리 기능을 제공합니다."},
    {"name": "파일 검색", "description": "파일 목록 조회, 검색, 필터링 기능을 제공합니다."},
    {"name": "썸네일", "description": "이미지 파일의 썸네일 생성 및 조회 기능을 제공합니다."},
    {"name": "인증 및 권한", "description": "IP 기반 인증, RBAC 권한 관리, 사용자 권한 조회 기능을 제공합니다."},
    {"name": "IP 관리", "description": "IP 화이트리스트/블랙리스트 관리 및 IP 상태 확인 기능을 제공합니다."},
    {"name": "레이트 리미팅", "description": "요청 제한 관리, IP 차단/해제 기능을 제공합니다."},
    {"name": "감사 로그", "description": "시스템 활동에 대한 감사 로그 조회 및 통계 기능을 제공합니다."},
    {"name": "백그라운드 작업", "description": "백그라운드 작업 제출, 상태 조회, 취소 기능을 제공합니다."},
    {"name": "모니터링", "description": "시스템 메트릭, 헬스체크, 성능 모니터링 기능을 제공합니다."},
    {"name": "관리자", "description": "관리자 전용 기능으로 시스템 관리 및 정리 작업을 제공합니다."},
]
```

### 2. Pydantic 응답 모델

#### Swagger 모델 정의 (`app/models/swagger_models.py`)
```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class UploadResponse(BaseModel):
    """파일 업로드 응답 모델"""
    file_id: str = Field(..., description="업로드된 파일의 고유 식별자 (UUID)", example="550e8400-e29b-41d4-a716-446655440000")
    filename: str = Field(..., description="원본 파일명", example="document.pdf")
    download_url: str = Field(..., description="파일 다운로드 URL", example="/download/550e8400-e29b-41d4-a716-446655440000")
    view_url: str = Field(..., description="파일 미리보기 URL", example="/view/550e8400-e29b-41d4-a716-446655440000")
    message: str = Field(..., description="업로드 결과 메시지", example="파일이 성공적으로 업로드되었습니다.")

    class Config:
        schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "document.pdf",
                "download_url": "/download/550e8400-e29b-41d4-a716-446655440000",
                "view_url": "/view/550e8400-e29b-41d4-a716-446655440000",
                "message": "파일이 성공적으로 업로드되었습니다."
            }
        }

class FileInfoResponse(BaseModel):
    """파일 정보 응답 모델"""
    file_uuid: str = Field(..., description="파일 고유 식별자", example="550e8400-e29b-41d4-a716-446655440000")
    filename: str = Field(..., description="원본 파일명", example="document.pdf")
    file_size: int = Field(..., description="파일 크기 (바이트)", example=1024000)
    content_type: str = Field(..., description="MIME 타입", example="application/pdf")
    upload_time: datetime = Field(..., description="업로드 시간", example="2024-01-15T10:30:00Z")
    last_accessed: Optional[datetime] = Field(None, description="마지막 접근 시간")
    download_count: int = Field(..., description="다운로드 횟수", example=5)
    is_public: bool = Field(..., description="공개 여부", example=True)
    tags: List[str] = Field(default=[], description="파일 태그 목록", example=["pdf", "document"])
    description: Optional[str] = Field(None, description="파일 설명", example="샘플 PDF 문서")
    download_url: str = Field(..., description="다운로드 URL")
    preview_url: str = Field(..., description="미리보기 URL")

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    detail: str = Field(..., description="에러 메시지", example="파일 크기가 최대 제한을 초과했습니다.")
    error_type: str = Field(..., description="에러 타입", example="validation_error")
    error_code: int = Field(..., description="HTTP 상태 코드", example=400)
    timestamp: str = Field(..., description="에러 발생 시간", example="2024-01-15T10:30:00Z")

class HealthCheckResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str = Field(..., description="서비스 상태", example="healthy")
    timestamp: str = Field(..., description="응답 시간", example="2024-01-15T10:30:00Z")
    service: str = Field(..., description="서비스 이름", example="FileWallBall API")
    version: str = Field(..., description="API 버전", example="1.0.0")

class DetailedHealthCheckResponse(BaseModel):
    """상세 헬스체크 응답 모델"""
    status: str = Field(..., description="전체 시스템 상태", example="healthy")
    timestamp: str = Field(..., description="응답 시간", example="2024-01-15T10:30:00Z")
    service: str = Field(..., description="서비스 정보", example="FileWallBall API v1.0.0")
    version: str = Field(..., description="API 버전", example="1.0.0")
    checks: dict = Field(..., description="각 컴포넌트별 상태")
```

### 3. 인증 스키마 정의

#### JWT Bearer 토큰 인증 (`app/dependencies/auth_schema.py`)
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List

# JWT Bearer 토큰 인증 스키마
security = HTTPBearer(
    scheme_name="JWT Bearer Token",
    description="JWT Bearer 토큰을 사용한 인증. Authorization 헤더에 'Bearer <token>' 형식으로 전송하세요.",
    auto_error=True
)

class TokenResponse(BaseModel):
    """토큰 응답 모델"""
    access_token: str = Field(..., description="액세스 토큰")
    token_type: str = Field(..., description="토큰 타입", example="bearer")
    expires_in: int = Field(..., description="만료 시간 (초)", example=3600)

class TokenData(BaseModel):
    """토큰 데이터 모델"""
    username: Optional[str] = None
    scopes: List[str] = []

class ErrorCodes:
    """에러 코드 상수"""
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    FILE_TOO_LARGE = "file_too_large"
    INVALID_FILE_TYPE = "invalid_file_type"
    INTERNAL_SERVER_ERROR = "internal_server_error"
```

#### 에러 응답 생성 함수
```python
def get_common_error_responses():
    """공통 에러 응답 정의"""
    return {
        400: {
            "description": "잘못된 요청",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "요청 파라미터가 올바르지 않습니다.",
                        "error_type": ErrorCodes.VALIDATION_ERROR,
                        "error_code": 400,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        401: {
            "description": "인증 실패",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "유효한 인증 토큰이 필요합니다.",
                        "error_type": ErrorCodes.UNAUTHORIZED,
                        "error_code": 401,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        403: {
            "description": "권한 없음",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "이 작업을 수행할 권한이 없습니다.",
                        "error_type": ErrorCodes.FORBIDDEN,
                        "error_code": 403,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        404: {
            "description": "리소스를 찾을 수 없음",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "요청한 리소스를 찾을 수 없습니다.",
                        "error_type": ErrorCodes.NOT_FOUND,
                        "error_code": 404,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        429: {
            "description": "요청 한도 초과",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.",
                        "error_type": ErrorCodes.RATE_LIMIT_EXCEEDED,
                        "error_code": 429,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        500: {
            "description": "서버 내부 오류",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "서버 내부 오류가 발생했습니다.",
                        "error_type": ErrorCodes.INTERNAL_SERVER_ERROR,
                        "error_code": 500,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
```

### 4. Swagger UI 커스터마이징

#### 커스텀 OpenAPI 스키마 (`app/utils/swagger_customization.py`)
```python
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI

def custom_openapi(app: FastAPI):
    """Swagger UI 커스터마이징을 위한 custom_openapi 함수"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # 로고 추가
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
        "altText": "FileWallBall API"
    }

    # 태그 그룹화
    openapi_schema["info"]["x-tagGroups"] = [
        {
            "name": "파일 관리",
            "tags": ["파일 업로드", "파일 관리", "파일 검색", "썸네일"]
        },
        {
            "name": "시스템 관리",
            "tags": ["인증 및 권한", "모니터링", "관리자", "백그라운드 작업"]
        }
    ]

    # Swagger UI 커스터마이징
    openapi_schema["x-swagger-ui"] = {
        "docExpansion": "list",
        "defaultModelsExpandDepth": 1,
        "displayRequestDuration": True,
        "filter": True,
        "requestInterceptor": """
        function(request) {
            if (request.headers && request.headers.Authorization) {
                console.log('Authorization header found:', request.headers.Authorization);
            }
            return request;
        }
        """,
        "responseInterceptor": """
        function(response) {
            if (response.status >= 400) {
                console.error('API Error:', response.status, response.body);
            }
            return response;
        }
        """
    }

    # ReDoc 커스터마이징
    openapi_schema["x-redoc"] = {
        "theme": {
            "colors": {"primary": {"main": "#1976d2"}},
            "typography": {"fontSize": "14px", "lineHeight": "1.5em"}
        },
        "hideDownloadButton": False,
        "pathInMiddlePanel": True,
        "requiredPropsFirst": True,
        "sortPropsAlphabetically": True
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

### 5. 엔드포인트 문서화 예시

#### 파일 업로드 엔드포인트
```python
@app.post(
    "/upload",
    response_model=UploadResponse,
    summary="파일 업로드",
    description="""
    파일을 업로드하고 시스템에 저장합니다.

    ## 기능
    - 최대 100MB 파일 업로드 지원
    - 파일 형식 검증 및 바이러스 스캔
    - 자동 썸네일 생성 (이미지 파일)
    - 파일 해시 계산 (백그라운드)
    - 업로드 통계 기록

    ## 지원 파일 형식
    - 이미지: jpg, jpeg, png, gif, webp, bmp, tiff
    - 문서: pdf, doc, docx, xls, xlsx, ppt, pptx, txt
    - 비디오: mp4, avi, mov, wmv, flv, webm
    - 오디오: mp3, wav, flac, aac, ogg
    - 압축: zip, rar, 7z, tar, gz

    ## 응답
    - `file_id`: 업로드된 파일의 고유 식별자
    - `filename`: 원본 파일명
    - `download_url`: 파일 다운로드 URL
    - `view_url`: 파일 미리보기 URL (지원되는 경우)
    - `message`: 성공 메시지
    """,
    tags=["파일 업로드"],
    responses=get_file_error_responses()
)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="업로드할 파일", example="document.pdf"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_file_create),
):
    # 구현 내용...
```

#### 헬스체크 엔드포인트
```python
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="기본 헬스체크",
    description="""
    애플리케이션의 기본 상태를 확인합니다.

    ## 기능
    - 애플리케이션 실행 상태 확인
    - 간단한 응답 시간 측정
    - Kubernetes liveness probe용

    ## 응답
    - `status`: 애플리케이션 상태 (healthy/unhealthy)
    - `timestamp`: 응답 시간 (ISO 8601 형식)
    - `service`: 서비스 이름
    - `version`: API 버전

    ## 사용 예제
    ```bash
    curl -X GET "http://localhost:8000/health"
    ```

    ## Kubernetes 연동
    이 엔드포인트는 Kubernetes liveness probe에서 사용됩니다.
    """,
    tags=["모니터링"],
    responses={
        200: {"description": "애플리케이션 정상 동작"},
        503: {
            "description": "애플리케이션 비정상 상태",
            "model": ErrorResponse
        }
    }
)
async def health_check():
    # 구현 내용...
```

## 🌐 Swagger UI 접근

### 문서 접근 URL
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Swagger UI 기능
1. **인터랙티브 API 테스트**: 브라우저에서 직접 API 호출 가능
2. **인증 토큰 설정**: 우측 상단의 "Authorize" 버튼으로 토큰 설정
3. **요청/응답 예시**: 각 엔드포인트별 상세한 예시 제공
4. **에러 코드 문서**: 모든 에러 응답 형식 문서화
5. **태그별 그룹화**: 기능별로 엔드포인트 분류

## 📝 API 사용 예제

### cURL 예제
```bash
# 파일 업로드
curl -X POST "http://localhost:8000/upload" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@document.pdf"

# 파일 다운로드
curl -X GET "http://localhost:8000/download/{file_id}" \
     -H "Authorization: Bearer YOUR_TOKEN"

# 파일 목록 조회
curl -X GET "http://localhost:8000/api/v1/files?page=1&size=20" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### Python 예제
```python
import requests

# 파일 업로드
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    headers = {'Authorization': 'Bearer YOUR_TOKEN'}
    response = requests.post('http://localhost:8000/upload', files=files, headers=headers)
    file_data = response.json()

# 파일 다운로드
file_id = file_data['file_id']
response = requests.get(f'http://localhost:8000/download/{file_id}', headers=headers)
with open('downloaded_file.pdf', 'wb') as f:
    f.write(response.content)
```

### JavaScript 예제
```javascript
// 파일 업로드
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/upload', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN'
    },
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));

// 파일 다운로드
fetch(`http://localhost:8000/download/${fileId}`, {
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN'
    }
})
.then(response => response.blob())
.then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'downloaded_file.pdf';
    a.click();
});
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

### Swagger UI 테스트
1. 브라우저에서 `http://localhost:8000/docs` 접속
2. "Authorize" 버튼 클릭하여 토큰 설정
3. 원하는 엔드포인트 선택
4. "Try it out" 버튼 클릭
5. 파라미터 입력 후 "Execute" 버튼 클릭
6. 응답 확인

## 📊 문서화 품질 관리

### 문서화 체크리스트
- [ ] 모든 엔드포인트에 summary와 description 추가
- [ ] 적절한 태그 분류 완료
- [ ] 요청/응답 모델 정의 완료
- [ ] 에러 응답 스키마 정의 완료
- [ ] 사용 예제 제공 완료
- [ ] 인증 방법 문서화 완료
- [ ] 파라미터 설명 완료
- [ ] 응답 예시 제공 완료

### 문서 업데이트 가이드
1. **새 엔드포인트 추가 시**:
   - `summary`와 `description` 추가
   - 적절한 `tags` 설정
   - `response_model` 지정
   - `responses` 에러 스키마 추가

2. **기존 엔드포인트 수정 시**:
   - `description` 업데이트
   - 파라미터 설명 수정
   - 응답 모델 업데이트

3. **새 모델 추가 시**:
   - `app/models/swagger_models.py`에 모델 정의
   - `Field` 데코레이터로 상세 설명 추가
   - `Config.schema_extra`로 예시 추가

## 🚀 향후 개선 계획

### 계획된 기능
1. **API 버전 관리**: 버전별 문서 분리
2. **웹훅 문서화**: 웹훅 엔드포인트 문서화
3. **실시간 문서**: WebSocket 엔드포인트 문서화
4. **다국어 지원**: 한국어/영어 문서 전환
5. **API 키 관리**: API 키 생성/관리 문서화

### 성능 최적화
1. **문서 캐싱**: OpenAPI 스키마 캐싱
2. **지연 로딩**: 대용량 문서 지연 로딩
3. **압축**: 문서 응답 압축

---

이 문서는 FileWallBall의 Swagger API 문서화 시스템을 상세히 설명합니다. 문서화 관련 질문이나 개선 제안이 있으시면 개발팀에 문의해 주세요.
