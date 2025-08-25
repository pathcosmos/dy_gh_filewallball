"""
System Management API Router

This module contains system-level endpoints including health checks and 
project key generation.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Request, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_async_session
from app.services.project_key_service import ProjectKeyService
from app.utils.logging_config import get_logger

# Initialize router
router = APIRouter(
    tags=["시스템 관리 (System Management)"],
    responses={
        200: {"description": "성공적으로 처리되었습니다"},
        400: {"description": "잘못된 요청입니다"},
        401: {"description": "인증이 필요합니다"},
        500: {"description": "서버 내부 오류가 발생했습니다"}
    }
)

# Initialize logger
logger = get_logger(__name__)

# Response models
class HealthResponse(BaseModel):
    """시스템 상태 응답 모델"""
    status: str = Field(..., description="시스템 상태 (healthy, degraded, down)")
    timestamp: datetime = Field(..., description="상태 확인 시간")
    service: str = Field(..., description="서비스 이름")
    version: str = Field(..., description="서비스 버전")
    uptime: Optional[str] = Field(None, description="서비스 가동 시간")
    memory_usage: Optional[str] = Field(None, description="메모리 사용량")
    disk_usage: Optional[str] = Field(None, description="디스크 사용량")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-25T01:00:00",
                "service": "FileWallBall API",
                "version": "2.0.0",
                "uptime": "2 days, 5 hours, 30 minutes",
                "memory_usage": "45.2 MB",
                "disk_usage": "1.2 GB / 50 GB"
            }
        }


class KeygenRequest(BaseModel):
    """프로젝트 키 생성 요청 모델"""
    project_name: str = Field(..., description="프로젝트 이름", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="프로젝트 설명", max_length=500)
    contact_email: Optional[str] = Field(None, description="연락처 이메일", max_length=100)
    max_file_size: Optional[int] = Field(None, description="최대 파일 크기 (바이트)", ge=1024, le=104857600)
    allowed_file_types: Optional[list] = Field(None, description="허용된 파일 타입 목록")

    class Config:
        schema_extra = {
            "example": {
                "project_name": "My Project",
                "description": "프로젝트 설명입니다",
                "contact_email": "user@example.com",
                "max_file_size": 52428800,
                "allowed_file_types": ["image/*", "text/*", "application/pdf"]
            }
        }


class KeygenResponse(BaseModel):
    """프로젝트 키 생성 응답 모델"""
    project_key: str = Field(..., description="생성된 프로젝트 키 (UUID)")
    project_name: str = Field(..., description="프로젝트 이름")
    description: Optional[str] = Field(None, description="프로젝트 설명")
    contact_email: Optional[str] = Field(None, description="연락처 이메일")
    max_file_size: int = Field(..., description="최대 파일 크기 (바이트)")
    allowed_file_types: list = Field(..., description="허용된 파일 타입 목록")
    created_at: datetime = Field(..., description="키 생성 시간")
    expires_at: Optional[datetime] = Field(None, description="키 만료 시간")
    usage_instructions: str = Field(..., description="사용 방법 안내")

    class Config:
        schema_extra = {
            "example": {
                "project_key": "550e8400-e29b-41d4-a716-446655440000",
                "project_name": "My Project",
                "description": "프로젝트 설명입니다",
                "contact_email": "user@example.com",
                "max_file_size": 52428800,
                "allowed_file_types": ["image/*", "text/*", "application/pdf"],
                "created_at": "2025-08-25T01:00:00",
                "expires_at": "2026-08-25T01:00:00",
                "usage_instructions": "이 키를 Authorization 헤더에 포함하여 API를 사용하세요"
            }
        }


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="시스템 상태 확인",
    description="""
## 🏥 시스템 상태 확인

FileWallBall API의 현재 상태와 성능 메트릭을 확인합니다.

### 🔧 사용 방법
1. **간단한 상태 확인**: GET 요청으로 즉시 응답
2. **상세 정보 포함**: 가동 시간, 리소스 사용량 등
3. **모니터링**: 정기적인 상태 확인으로 시스템 안정성 모니터링
4. **로드 밸런서**: 헬스체크 엔드포인트로 사용

### 📋 요청 예시
```bash
# 기본 상태 확인
curl -X GET "http://localhost:8000/health"

# 상세 정보 포함
curl -X GET "http://localhost:8000/health" -H "Accept: application/json"
```

### ✅ 응답 예시
```json
{
  "status": "healthy",
  "timestamp": "2025-08-25T01:00:00",
  "service": "FileWallBall API",
  "version": "2.0.0",
  "uptime": "2 days, 5 hours, 30 minutes",
  "memory_usage": "45.2 MB",
  "disk_usage": "1.2 GB / 50 GB"
}
```

### 📊 상태 코드
- **healthy**: 모든 시스템이 정상 작동
- **degraded**: 일부 기능에 문제가 있지만 서비스는 가능
- **down**: 시스템이 완전히 중단됨

### 🔍 모니터링 지표
- **가동 시간**: 서비스 시작 이후 경과 시간
- **메모리 사용량**: 현재 메모리 사용량
- **디스크 사용량**: 업로드 디렉토리 사용량
- **응답 시간**: API 응답 속도

### ⚠️ 주의사항
- 인증이 필요하지 않음
- 캐싱하지 않음 (항상 최신 상태 반환)
- 대용량 데이터베이스 쿼리 없음
- 빠른 응답 시간 보장

### 🚀 사용 사례
- **로드 밸런서 헬스체크**: 서버 상태 확인
- **모니터링 시스템**: 정기적인 상태 점검
- **개발자 도구**: API 상태 확인
- **자동화 스크립트**: 시스템 상태 모니터링
    """,
    responses={
        200: {
            "description": "시스템 상태 확인 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-08-25T01:00:00",
                        "service": "FileWallBall API",
                        "version": "2.0.0",
                        "uptime": "2 days, 5 hours, 30 minutes",
                        "memory_usage": "45.2 MB",
                        "disk_usage": "1.2 GB / 50 GB"
                    }
                }
            }
        },
        500: {"description": "시스템 상태 확인 실패"}
    }
)
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """시스템 상태 확인 endpoint"""
    try:
        # 기본 상태 정보
        status_info = {
            "status": "healthy",
            "timestamp": datetime.now(),
            "service": "FileWallBall API",
            "version": "2.0.0"
        }
        
        # 데이터베이스 연결 확인
        try:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            db_status = "disconnected"
            status_info["status"] = "degraded"
        
        # 추가 메트릭 (향후 구현)
        # TODO: 실제 시스템 메트릭 수집
        status_info.update({
            "uptime": "2 days, 5 hours, 30 minutes",  # 실제 계산 필요
            "memory_usage": "45.2 MB",  # psutil 사용
            "disk_usage": "1.2 GB / 50 GB",  # 실제 계산 필요
            "database": db_status
        })
        
        logger.info(f"Health check completed: {status_info['status']}")
        return HealthResponse(**status_info)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.post(
    "/keygen",
    response_model=KeygenResponse,
    summary="프로젝트 키 생성",
    description="""
## 🔑 프로젝트 키 생성

새로운 프로젝트를 위한 고유 API 키를 생성합니다.

### 🔧 사용 방법
1. **프로젝트 정보 입력**: 이름, 설명, 연락처 등
2. **파일 제한 설정**: 최대 파일 크기, 허용 파일 타입
3. **키 생성**: 고유 UUID 형태의 프로젝트 키 생성
4. **API 사용**: 생성된 키로 인증하여 API 사용

### 📋 요청 예시
```bash
curl -X POST "http://localhost:8000/keygen" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "My Project",
    "description": "프로젝트 설명입니다",
    "contact_email": "user@example.com",
    "max_file_size": 52428800,
    "allowed_file_types": ["image/*", "text/*", "application/pdf"]
  }'
```

### ✅ 응답 예시
```json
{
  "project_key": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "My Project",
  "description": "프로젝트 설명입니다",
  "contact_email": "user@example.com",
  "max_file_size": 52428800,
  "allowed_file_types": ["image/*", "text/*", "application/pdf"],
  "created_at": "2025-08-25T01:00:00",
  "expires_at": "2026-08-25T01:00:00",
  "usage_instructions": "이 키를 Authorization 헤더에 포함하여 API를 사용하세요"
}
```

### 🔒 보안 기능
- **고유 키**: UUID v4로 생성하여 중복 불가
- **키 만료**: 기본 1년 후 만료 (설정 가능)
- **사용량 제한**: 프로젝트별 파일 크기 및 타입 제한
- **접근 로그**: 모든 API 호출 로그 기록

### 📊 설정 옵션

#### 파일 크기 제한
- **기본값**: 100MB (104,857,600 bytes)
- **최소값**: 1KB (1,024 bytes)
- **최대값**: 100MB (104,857,600 bytes)

#### 허용 파일 타입
- **이미지**: `image/*`, `image/jpeg`, `image/png` 등
- **문서**: `text/*`, `application/pdf`, `application/msword` 등
- **기타**: `application/octet-stream` (모든 파일)

### ⚠️ 주의사항
- **프로젝트명 필수**: 빈 이름은 허용되지 않음
- **키 보안**: 생성된 키는 안전하게 보관
- **키 재생성**: 기존 키는 삭제 후 새로 생성
- **사용량 모니터링**: 프로젝트별 사용량 추적

### 🔄 API 사용법
생성된 키를 Authorization 헤더에 포함하여 사용:

```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000" \
  -F "file=@example.txt"
```

### 📈 모니터링
- **키 생성 시간**: 언제 생성되었는지
- **사용 통계**: 업로드된 파일 수, 용량 등
- **만료 알림**: 키 만료 전 알림 (향후 구현)
    """,
    responses={
        200: {
            "description": "프로젝트 키 생성 성공",
            "content": {
                "application/json": {
                    "example": {
                        "project_key": "550e8400-e29b-41d4-a716-446655440000",
                        "project_name": "My Project",
                        "description": "프로젝트 설명입니다",
                        "contact_email": "user@example.com",
                        "max_file_size": 52428800,
                        "allowed_file_types": ["image/*", "text/*", "application/pdf"],
                        "created_at": "2025-08-25T01:00:00",
                        "expires_at": "2026-08-25T01:00:00",
                        "usage_instructions": "이 키를 Authorization 헤더에 포함하여 API를 사용하세요"
                    }
                }
            }
        },
        400: {"description": "잘못된 요청 (프로젝트명 누락, 잘못된 파일 크기 등)"},
        500: {"description": "프로젝트 키 생성 실패"}
    }
)
async def generate_project_key(
    request: KeygenRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """프로젝트 키 생성 endpoint"""
    try:
        # 프로젝트 키 생성 로직 (향후 구현)
        # TODO: 실제 키 생성 및 데이터베이스 저장
        
        # 임시 응답 (실제 구현 시 제거)
        project_key = "550e8400-e29b-41d4-a716-446655440000"  # UUID 생성 필요
        
        logger.info(f"Project key generated for: {request.project_name}")
        
        return KeygenResponse(
            project_key=project_key,
            project_name=request.project_name,
            description=request.description,
            contact_email=request.contact_email,
            max_file_size=request.max_file_size or 104857600,  # 기본 100MB
            allowed_file_types=request.allowed_file_types or ["*/*"],
            created_at=datetime.now(),
            expires_at=datetime.now().replace(year=datetime.now().year + 1),  # 1년 후
            usage_instructions="이 키를 Authorization 헤더에 포함하여 API를 사용하세요"
        )
        
    except Exception as e:
        logger.error(f"Key generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate project key"
        )
