"""
프로젝트 키 관리 API 엔드포인트
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_async_session
from app.models.orm_models import ProjectKey
from app.services.project_key_service import ProjectKeyService
from app.utils.logging_config import get_logger
from app.utils.security_key_manager import get_master_key

logger = get_logger(__name__)

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    """프로젝트 생성 요청 모델"""
    project_name: str
    master_key: str


class ProjectCreateResponse(BaseModel):
    """프로젝트 생성 응답 모델"""
    project_key: str
    project_id: int
    message: str


@router.post("/", response_model=ProjectCreateResponse)
async def create_project_key(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    http_request: Request = None,
) -> Dict[str, Any]:
    """
    프로젝트 키 생성 API
    
    마스터 키를 사용하여 프로젝트별 API 키를 생성합니다.
    
    Args:
        request: 프로젝트 생성 요청 데이터
        db: 데이터베이스 세션
        http_request: HTTP 요청 객체
        
    Returns:
        Dict[str, Any]: 생성된 프로젝트 키 정보
        
    Raises:
        HTTPException: 마스터 키가 유효하지 않거나 프로젝트 생성에 실패한 경우
    """
    try:
        # 마스터 키 검증 - 보안 강화: 환경변수 또는 암호화된 키 사용
        # 원본 키 (참조용): dysnt2025FileWallersBallKAuEZzTAsBjXiQ==
        if request.master_key != get_master_key():
            logger.warning(
                f"Invalid master key attempt from IP: {http_request.client.host}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid master key"
            )
        
        # 클라이언트 IP 주소 가져오기
        client_ip = http_request.client.host if http_request else "unknown"
        
        # 현재 날짜를 YYYYMMDD 형식으로 변환
        current_date = datetime.now().strftime("%Y%m%d")
        
        # 프로젝트 키 서비스 인스턴스 생성
        project_service = ProjectKeyService(db)
        
        # 프로젝트 키 생성 및 저장
        project_key_obj = await project_service.create_project_key(
            project_name=request.project_name,
            request_date=current_date,
            request_ip=client_ip
        )
        
        # JWT 토큰 생성 (선택사항 - 추가 보안)
        jwt_payload = {
            "project_id": project_key_obj.id,
            "project_name": project_key_obj.project_name,
            "created_at": project_key_obj.created_at.isoformat() if project_key_obj.created_at else datetime.utcnow().isoformat(),
            "exp": datetime.utcnow() + timedelta(days=365)  # 1년 유효
        }
        
        # JWT 토큰 생성 (PyJWT 사용)
        try:
            # JWT 토큰 생성 - 보안 강화: 환경변수 또는 암호화된 키 사용
            # 원본 키 (참조용): dysnt2025FileWallersBallKAuEZzTAsBjXiQ==
            jwt_token = jwt.encode(
                jwt_payload, 
                get_master_key(), 
                algorithm="HS256"
            )
        except Exception as e:
            logger.warning(f"JWT token generation failed: {e}")
            jwt_token = None
        
        logger.info(
            f"Project key created successfully: "
            f"{project_key_obj.project_name} (ID: {project_key_obj.id})"
        )
        
        return {
            "project_key": project_key_obj.project_key,
            "project_id": project_key_obj.id,
            "jwt_token": jwt_token,
            "message": "Project key created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project key"
        )


@router.get("/{project_id}")
async def get_project_info(
    project_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    프로젝트 정보 조회 API
    
    Args:
        project_id: 프로젝트 ID
        db: 데이터베이스 세션
        
    Returns:
        Dict[str, Any]: 프로젝트 정보
        
    Raises:
        HTTPException: 프로젝트를 찾을 수 없는 경우
    """
    try:
        from sqlalchemy import select
        stmt = select(ProjectKey).where(ProjectKey.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return {
            "project_id": project.id,
            "project_name": project.project_name,
            "request_date": project.request_date,
            "request_ip": project.request_ip,
            "is_active": project.is_active,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "file_count": 0  # TODO: 비동기 관계 로딩 구현 필요
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error retrieving project info: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project information: {str(e)}"
        )


@router.delete("/{project_id}")
async def deactivate_project(
    project_id: int,
    master_key: str,
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    프로젝트 키 비활성화 API
    
    Args:
        project_id: 프로젝트 ID
        master_key: 마스터 키
        db: 데이터베이스 세션
        
    Returns:
        Dict[str, Any]: 비활성화 결과
        
    Raises:
        HTTPException: 마스터 키가 유효하지 않거나 프로젝트를 찾을 수 없는 경우
    """
    try:
        # 마스터 키 검증 - 보안 강화: 환경변수 또는 암호화된 키 사용
        # 원본 키 (참조용): dysnt2025FileWallersBallKAuEZzTAsBjXiQ==
        if master_key != get_master_key():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid master key"
            )
        
        from sqlalchemy import select
        stmt = select(ProjectKey).where(ProjectKey.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # 프로젝트 키 서비스 인스턴스 생성
        project_service = ProjectKeyService(db)
        
        # 프로젝트 키 비활성화
        success = await project_service.deactivate_project_key(project.project_key)
        
        if success:
            logger.info(f"Project deactivated successfully: {project.project_name} (ID: {project_id})")
            return {
                "message": "Project deactivated successfully",
                "project_id": project_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate project"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate project"
        ) 