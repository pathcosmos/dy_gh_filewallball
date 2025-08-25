"""
Simple FileWallBall API - Streamlined version without Redis/Docker dependencies

This file has been refactored to use modular routers for better code organization.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logging_config import get_logger
from app.routers import files, download, system

# Initialize logger
logger = get_logger(__name__)

# Get configuration
config = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="FileWallBall API - 파일 관리 시스템",
    description="""
# FileWallBall API - 파일 업로드 및 관리 시스템

## 📋 시스템 개요
FileWallBall은 파일 업로드, 저장, 다운로드, 관리 기능을 제공하는 RESTful API 시스템입니다.

## 🚀 주요 기능
- **파일 업로드**: 다양한 형식의 파일 업로드 및 저장
- **파일 관리**: 업로드된 파일 목록 조회, 정보 조회, 삭제
- **파일 다운로드**: 저장된 파일 다운로드 및 스트리밍
- **파일 뷰어**: 텍스트 파일 내용 보기, 이미지 파일 미리보기
- **프로젝트 관리**: 프로젝트별 API 키 생성 및 관리

## 📚 API 문서
- **Swagger UI**: `/docs` - 인터랙티브 API 문서 및 테스트 도구
- **ReDoc**: `/redoc` - 읽기 쉬운 API 문서

## 🔧 사용 방법
1. **프로젝트 키 생성**: `/keygen` endpoint로 프로젝트 키 생성
2. **파일 업로드**: `/upload` endpoint로 파일 업로드
3. **파일 목록 조회**: `/files` endpoint로 업로드된 파일 목록 확인
4. **파일 다운로드**: `/download/{file_id}` endpoint로 파일 다운로드
5. **파일 미리보기**: `/preview/{file_id}` endpoint로 파일 내용 미리보기

## 📁 지원 파일 형식
- **텍스트 파일**: .txt, .md, .json, .xml 등
- **이미지 파일**: .jpg, .png, .gif, .bmp 등
- **문서 파일**: .pdf, .doc, .docx 등
- **기타 파일**: 모든 바이너리 파일 지원

## 🔒 보안
- 프로젝트 키 기반 인증
- 파일 크기 제한 (기본 100MB)
- MIME 타입 검증
- 파일 해시 검증

## 📊 시스템 모니터링
- `/health` endpoint로 시스템 상태 확인
- 상세한 로깅 및 에러 추적
- 성능 메트릭 수집

---
**개발팀**: FileWallBall Team  
**버전**: 2.0.0  
**최종 업데이트**: 2025년 8월
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True,
        "displayRequestDuration": True,
        "persistAuthorization": True,
        "deepLinking": True,
        "syntaxHighlight.theme": "monokai"
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files.router)
app.include_router(download.router)
app.include_router(system.router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logger.info("FileWallBall API starting up...")
    
    # Ensure upload directory exists
    upload_dir = Path(config.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Upload directory: {upload_dir}")
    logger.info("FileWallBall API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    logger.info("FileWallBall API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)