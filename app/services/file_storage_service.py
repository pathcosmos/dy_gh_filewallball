"""
파일 저장 및 중복 관리 서비스
"""

import os
import hashlib
import shutil
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.orm_models import FileInfo
from app.utils.security_utils import generate_uuid
from app.utils.file_utils import calculate_file_hash


class FileStorageService:
    """파일 저장 및 중복 관리 서비스"""
    
    def __init__(self, db_session: Session, base_storage_path: str = "./uploads"):
        self.db_session = db_session
        self.base_storage_path = Path(base_storage_path)
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_file(self, file: UploadFile, original_filename: str) -> Dict[str, Any]:
        """
        파일 저장 및 중복 검사
        
        Args:
            file: 업로드된 파일
            original_filename: 원본 파일명
            
        Returns:
            파일 저장 결과 정보
        """
        try:
            # 1. 파일 내용 읽기 및 MD5 해시 계산
            content = await file.read()
            file_hash = hashlib.md5(content).hexdigest()
            
            # 2. 중복 파일 검사
            existing_file = self._check_duplicate_file(file_hash)
            if existing_file:
                return {
                    'is_duplicate': True,
                    'file_uuid': existing_file.file_uuid,
                    'message': '동일한 파일이 이미 존재합니다',
                    'existing_file': existing_file
                }
            
            # 3. UUID 생성
            file_uuid = generate_uuid()
            
            # 4. 저장 파일명 생성
            file_extension = Path(original_filename).suffix.lower()
            stored_filename = f"{file_uuid}{file_extension}"
            
            # 5. 저장 경로 생성 (계층적 구조)
            storage_path = self._create_storage_path(file_uuid, stored_filename)
            
            # 6. 디스크 용량 체크
            self._check_disk_space(len(content))
            
            # 7. 디렉토리 생성
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 8. 파일 저장
            await self._write_file(storage_path, content)
            
            # 9. 파일 정보 반환
            return {
                'is_duplicate': False,
                'file_uuid': file_uuid,
                'stored_filename': stored_filename,
                'storage_path': str(storage_path),
                'file_hash': file_hash,
                'file_size': len(content),
                'file_extension': file_extension
            }
            
        except Exception as e:
            # 저장 실패 시 임시 파일 정리
            await self._cleanup_failed_upload(file_uuid)
            raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")
    
    def _check_duplicate_file(self, file_hash: str) -> Optional[FileInfo]:
        """
        중복 파일 검사
        
        Args:
            file_hash: 파일 MD5 해시
            
        Returns:
            기존 파일 정보 (중복인 경우)
        """
        return self.db_session.query(FileInfo).filter(
            FileInfo.file_hash == file_hash,
            FileInfo.is_deleted == False
        ).first()
    
    def _create_storage_path(self, file_uuid: str, stored_filename: str) -> Path:
        """
        계층적 저장 경로 생성
        
        Args:
            file_uuid: 파일 UUID
            stored_filename: 저장 파일명
            
        Returns:
            저장 경로
        """
        # UUID의 첫 2글자와 다음 2글자로 계층 구조 생성
        uuid_prefix = file_uuid[:2]
        uuid_subprefix = file_uuid[2:4]
        
        storage_path = self.base_storage_path / uuid_prefix / uuid_subprefix / stored_filename
        return storage_path
    
    def _check_disk_space(self, required_bytes: int) -> None:
        """
        디스크 용량 체크
        
        Args:
            required_bytes: 필요한 바이트 수
            
        Raises:
            HTTPException: 용량 부족 시
        """
        try:
            # 현재 디스크 사용량 확인
            total, used, free = shutil.disk_usage(self.base_storage_path)
            
            # 여유 공간이 필요한 용량보다 작으면 오류
            if free < required_bytes:
                free_mb = free / (1024 * 1024)
                required_mb = required_bytes / (1024 * 1024)
                raise HTTPException(
                    status_code=507,  # Insufficient Storage
                    detail=f"디스크 용량 부족. 필요: {required_mb:.1f}MB, 여유: {free_mb:.1f}MB"
                )
                
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"디스크 용량 확인 실패: {str(e)}")
    
    async def _write_file(self, file_path: Path, content: bytes) -> None:
        """
        파일 쓰기
        
        Args:
            file_path: 저장할 파일 경로
            content: 파일 내용
        """
        try:
            # 파일 쓰기
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # 파일 쓰기 권한 확인
            if not os.access(file_path, os.W_OK):
                raise Exception("파일 쓰기 권한이 없습니다")
                
        except Exception as e:
            # 파일 쓰기 실패 시 파일 삭제
            if file_path.exists():
                file_path.unlink()
            raise Exception(f"파일 쓰기 실패: {str(e)}")
    
    async def _cleanup_failed_upload(self, file_uuid: str) -> None:
        """
        실패한 업로드 정리
        
        Args:
            file_uuid: 파일 UUID
        """
        try:
            # 저장 경로에서 파일 삭제
            uuid_prefix = file_uuid[:2]
            uuid_subprefix = file_uuid[2:4]
            cleanup_path = self.base_storage_path / uuid_prefix / uuid_subprefix
            
            if cleanup_path.exists():
                # 해당 디렉토리의 모든 파일 삭제
                for file_path in cleanup_path.glob(f"{file_uuid}*"):
                    file_path.unlink()
                
                # 빈 디렉토리 삭제
                if not any(cleanup_path.iterdir()):
                    cleanup_path.rmdir()
                    
        except Exception as e:
            # 정리 실패는 로그만 남기고 예외를 발생시키지 않음
            print(f"업로드 실패 정리 중 오류: {e}")
    
    def get_file_path(self, file_uuid: str) -> Optional[Path]:
        """
        파일 경로 조회
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            파일 경로 (존재하지 않으면 None)
        """
        try:
            # 데이터베이스에서 파일 정보 조회
            file_info = self.db_session.query(FileInfo).filter(
                FileInfo.file_uuid == file_uuid,
                FileInfo.is_deleted == False
            ).first()
            
            if not file_info:
                return None
            
            # 저장 경로 생성
            storage_path = Path(file_info.storage_path)
            
            # 파일 존재 확인
            if storage_path.exists():
                return storage_path
            else:
                return None
                
        except Exception as e:
            print(f"파일 경로 조회 중 오류: {e}")
            return None
    
    def delete_file(self, file_uuid: str) -> bool:
        """
        파일 삭제 (논리적 삭제)
        
        Args:
            file_uuid: 파일 UUID
            
        Returns:
            삭제 성공 여부
        """
        try:
            # 데이터베이스에서 파일 정보 조회
            file_info = self.db_session.query(FileInfo).filter(
                FileInfo.file_uuid == file_uuid,
                FileInfo.is_deleted == False
            ).first()
            
            if not file_info:
                return False
            
            # 논리적 삭제 (is_deleted = True)
            file_info.is_deleted = True
            self.db_session.commit()
            
            return True
            
        except Exception as e:
            self.db_session.rollback()
            print(f"파일 삭제 중 오류: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        저장소 통계 조회
        
        Returns:
            저장소 통계 정보
        """
        try:
            total_files = 0
            total_size = 0
            
            # 모든 파일 순회
            for file_path in self.base_storage_path.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            # 디스크 사용량
            total, used, free = shutil.disk_usage(self.base_storage_path)
            
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'disk_total_bytes': total,
                'disk_used_bytes': used,
                'disk_free_bytes': free,
                'disk_usage_percent': (used / total) * 100 if total > 0 else 0
            }
            
        except Exception as e:
            print(f"저장소 통계 조회 중 오류: {e}")
            return {} 