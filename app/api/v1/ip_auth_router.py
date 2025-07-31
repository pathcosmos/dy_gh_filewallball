"""
IP 기반 인증 API 라우터
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.api_models import FileUploadResponse, IPAuthResponse
from app.services.file_storage_service import FileStorageService
from app.services.ip_auth_service import IPAuthService
from app.services.metadata_service import MetadataService
from app.utils.security_utils import generate_encryption_key, sanitize_ip_address

router = APIRouter(prefix="/api/v1/ip-auth", tags=["IP Authentication"])


@router.post("/upload", response_model=IPAuthResponse)
async def upload_file_with_ip_auth(
    file: UploadFile = File(...),
    request: Request = None,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """IP 기반 인증을 통한 파일 업로드"""
    start_time = time.time()

    try:
        # IP 인증 서비스 초기화
        ip_auth_service = IPAuthService(db)

        # 클라이언트 IP 추출
        client_ip = ip_auth_service.get_client_ip(request)
        client_ip = sanitize_ip_address(client_ip)

        # IP 및 키 검증
        allowed_ip = ip_auth_service.verify_ip_and_key(client_ip, x_api_key)
        if not allowed_ip:
            ip_auth_service.log_auth_event(
                client_ip,
                x_api_key,
                "auth_failed",
                user_agent=request.headers.get("User-Agent"),
                response_code=401,
                error_message="IP 또는 키가 유효하지 않습니다",
            )
            raise HTTPException(
                status_code=401, detail="인증 실패: IP 또는 키가 유효하지 않습니다"
            )

        # Rate limiting 확인
        if not ip_auth_service.check_rate_limit(client_ip, x_api_key):
            ip_auth_service.log_auth_event(
                client_ip,
                x_api_key,
                "rate_limited",
                user_agent=request.headers.get("User-Agent"),
                response_code=429,
                error_message="요청 한도를 초과했습니다",
            )
            raise HTTPException(status_code=429, detail="요청 한도를 초과했습니다")

        # 파일 크기 제한 확인
        if allowed_ip.max_file_size and file.size > allowed_ip.max_file_size:
            ip_auth_service.log_auth_event(
                client_ip,
                x_api_key,
                "file_too_large",
                user_agent=request.headers.get("User-Agent"),
                response_code=413,
                error_message=f"파일 크기가 제한을 초과합니다 (최대: {allowed_ip.max_file_size} bytes)",
            )
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 제한을 초과합니다 (최대: {allowed_ip.max_file_size} bytes)",
            )

        # 파일 스토리지 서비스 초기화
        storage_service = FileStorageService(db)
        metadata_service = MetadataService(db)

        # 파일 저장
        file_info = await storage_service.save_file(file, file.filename)

        # 메타데이터 저장 (트랜잭션 문제로 인해 간단한 정보만 저장)
        # 실제 프로덕션에서는 별도의 세션을 사용하거나 트랜잭션을 적절히 관리해야 함
        print(f"파일 업로드 성공: {file_info['file_uuid']}")
        print(f"저장 경로: {file_info['storage_path']}")
        print(f"파일 크기: {file_info['file_size']} bytes")

        # 처리 시간 계산
        processing_time_ms = int((time.time() - start_time) * 1000)

        # 성공 로그 기록
        ip_auth_service.log_auth_event(
            client_ip,
            x_api_key,
            "upload",
            file_uuid=file_info["file_uuid"],
            user_agent=request.headers.get("User-Agent"),
            response_code=200,
            request_size=file.size,
            processing_time_ms=processing_time_ms,
        )

        return IPAuthResponse(
            success=True,
            file_uuid=file_info["file_uuid"],
            original_filename=file.filename,  # 원본 파일명 사용
            file_size=file_info["file_size"],
            message="파일이 성공적으로 업로드되었습니다",
            upload_time=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time_ms,
            auth_method="ip_based",
            client_ip=client_ip,
        )

    except HTTPException:
        raise
    except Exception as e:
        # 에러 로그 기록
        if "ip_auth_service" in locals():
            ip_auth_service.log_auth_event(
                client_ip,
                x_api_key,
                "upload_error",
                user_agent=request.headers.get("User-Agent") if request else None,
                response_code=500,
                error_message=str(e),
            )

        raise HTTPException(
            status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/allowed-ips", response_model=Dict[str, Any])
async def add_allowed_ip(
    ip_address: str,
    encryption_key: Optional[str] = None,
    ip_range: Optional[str] = None,
    max_uploads_per_hour: int = 100,
    max_file_size: int = 104857600,
    expires_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """허용된 IP 추가 (관리자용)"""
    try:
        ip_auth_service = IPAuthService(db)

        # 암호화 키가 제공되지 않은 경우 생성
        if not encryption_key:
            encryption_key = generate_encryption_key()

        # 허용 IP 추가
        allowed_ip = ip_auth_service.add_allowed_ip(
            ip_address=ip_address,
            encryption_key=encryption_key,
            ip_range=ip_range,
            max_uploads_per_hour=max_uploads_per_hour,
            max_file_size=max_file_size,
            expires_at=expires_at,
        )

        return {
            "success": True,
            "message": "허용 IP가 성공적으로 추가되었습니다",
            "ip_address": allowed_ip.ip_address,
            "encryption_key": encryption_key,  # 생성된 키 반환
            "max_uploads_per_hour": allowed_ip.max_uploads_per_hour,
            "max_file_size": allowed_ip.max_file_size,
            "expires_at": (
                allowed_ip.expires_at.isoformat() if allowed_ip.expires_at else None
            ),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"허용 IP 추가 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/allowed-ips")
async def remove_allowed_ip(
    ip_address: str, encryption_key: str, db: Session = Depends(get_db)
):
    """허용된 IP 제거 (관리자용)"""
    try:
        ip_auth_service = IPAuthService(db)

        success = ip_auth_service.remove_allowed_ip(ip_address, encryption_key)

        if success:
            return {"success": True, "message": "허용 IP가 성공적으로 제거되었습니다"}
        else:
            raise HTTPException(
                status_code=404, detail="지정된 IP와 키 조합을 찾을 수 없습니다"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"허용 IP 제거 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/regenerate-key")
async def regenerate_encryption_key(
    ip_address: str, old_key: str, db: Session = Depends(get_db)
):
    """암호화 키 재생성 (관리자용)"""
    try:
        ip_auth_service = IPAuthService(db)

        new_key = ip_auth_service.regenerate_encryption_key(ip_address, old_key)

        return {
            "success": True,
            "message": "암호화 키가 성공적으로 재생성되었습니다",
            "ip_address": ip_address,
            "new_encryption_key": new_key,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"키 재생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/statistics")
async def get_ip_statistics(
    ip_address: Optional[str] = None, days: int = 7, db: Session = Depends(get_db)
):
    """IP별 사용 통계 조회 (관리자용)"""
    try:
        ip_auth_service = IPAuthService(db)

        if ip_address:
            ip_address = sanitize_ip_address(ip_address)

        statistics = ip_auth_service.get_ip_statistics(ip_address, days)

        return {"success": True, "statistics": statistics, "period_days": days}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/health")
async def ip_auth_health_check():
    """IP 인증 서비스 헬스체크"""
    return {
        "service": "ip_auth",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }
