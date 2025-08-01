"""
프로젝트 키 생성 및 검증 서비스
"""

import hashlib
import hmac
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.orm_models import ProjectKey


class ProjectKeyService:
    """프로젝트 키 관리 서비스"""
    
    # 고정된 마스터 키
    MASTER_KEY = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_project_key(
        self, 
        project_name: str, 
        request_date: str, 
        request_ip: str
    ) -> str:
        """
        프로젝트 고유 키 생성
        
        Args:
            project_name: 프로젝트명
            request_date: 요청 날짜 (YYYYMMDD)
            request_ip: 요청 IP 주소
            
        Returns:
            str: 생성된 프로젝트 키
        """
        # 입력 데이터를 결합하여 키 생성
        key_data = f"{project_name}:{request_date}:{request_ip}:{self.MASTER_KEY}"
        
        # HMAC-SHA256을 사용하여 키 생성
        key_bytes = hmac.new(
            self.MASTER_KEY.encode('utf-8'),
            key_data.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Base64 인코딩으로 변환
        import base64
        project_key = base64.b64encode(key_bytes).decode('utf-8')
        
        return project_key
    
    def create_project_key(
        self, 
        project_name: str, 
        request_date: str, 
        request_ip: str
    ) -> ProjectKey:
        """
        프로젝트 키를 생성하고 데이터베이스에 저장
        
        Args:
            project_name: 프로젝트명
            request_date: 요청 날짜 (YYYYMMDD)
            request_ip: 요청 IP 주소
            
        Returns:
            ProjectKey: 생성된 프로젝트 키 객체
        """
        # 프로젝트 키 생성
        project_key = self.generate_project_key(project_name, request_date, request_ip)
        
        # 데이터베이스에 저장
        db_project_key = ProjectKey(
            project_name=project_name,
            project_key=project_key,
            request_date=request_date,
            request_ip=request_ip,
            is_active=True
        )
        
        self.db.add(db_project_key)
        self.db.commit()
        self.db.refresh(db_project_key)
        
        return db_project_key
    
    def validate_project_key(self, project_key: str) -> Optional[ProjectKey]:
        """
        프로젝트 키 유효성 검증
        
        Args:
            project_key: 검증할 프로젝트 키
            
        Returns:
            Optional[ProjectKey]: 유효한 경우 ProjectKey 객체, 그렇지 않으면 None
        """
        # 데이터베이스에서 프로젝트 키 조회
        db_project_key = self.db.query(ProjectKey).filter(
            ProjectKey.project_key == project_key,
            ProjectKey.is_active.is_(True)
        ).first()
        
        return db_project_key
    
    def get_project_by_key(self, project_key: str) -> Optional[ProjectKey]:
        """
        프로젝트 키로 프로젝트 정보 조회
        
        Args:
            project_key: 프로젝트 키
            
        Returns:
            Optional[ProjectKey]: 프로젝트 정보
        """
        return self.validate_project_key(project_key)
    
    def deactivate_project_key(self, project_key: str) -> bool:
        """
        프로젝트 키 비활성화
        
        Args:
            project_key: 비활성화할 프로젝트 키
            
        Returns:
            bool: 성공 여부
        """
        db_project_key = self.validate_project_key(project_key)
        if db_project_key:
            db_project_key.is_active = False
            db_project_key.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def get_project_files(self, project_key: str) -> list:
        """
        프로젝트에 속한 파일 목록 조회
        
        Args:
            project_key: 프로젝트 키
            
        Returns:
            list: 파일 목록
        """
        db_project_key = self.validate_project_key(project_key)
        if db_project_key:
            return db_project_key.files
        return [] 