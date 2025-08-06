"""
Security Key Manager - 암호화된 마스터 키 관리
"""

import base64
import hashlib
import os
from typing import Optional


class SecurityKeyManager:
    """보안 키 관리 클래스"""
    
    # 원본 키 (참조용 주석) - dysnt2025FileWallersBallKAuEZzTAsBjXiQ==
    # 환경변수에서 읽거나 기본 암호화된 키 사용
    
    @staticmethod
    def get_master_key() -> str:
        """
        마스터 키를 환경변수에서 가져오거나 기본값 반환
        
        Returns:
            str: 마스터 키
        """
        # 환경변수에서 마스터 키 읽기 (최우선)
        env_key = os.getenv('MASTER_KEY')
        if env_key:
            return env_key
        
        # 환경변수가 없으면 암호화된 기본 키 사용
        return SecurityKeyManager._get_default_encrypted_key()
    
    @staticmethod
    def _get_default_encrypted_key() -> str:
        """
        기본 암호화된 키 반환 (PBKDF2 기반)
        원본: dysnt2025FileWallersBallKAuEZzTAsBjXiQ==
        """
        # PBKDF2로 파생된 키 (100,000 반복, 고정 솔트)
        return "J1NNggqKXb3q0jOdbcCQdgeM02qnEHH/QLOFoowRdSU="
    
    @staticmethod
    def _get_legacy_key() -> str:
        """
        레거시 원본 키 반환 (호환성용) - 보안상 암호화된 버전 사용
        원본: dysnt2025FileWallersBallKAuEZzTAsBjXiQ==
        """
        # 보안상 암호화된 키 반환 (원본 키는 주석으로만 보존)
        return SecurityKeyManager._get_default_encrypted_key()
    
    @staticmethod
    def generate_pbkdf2_key(original_key: str, salt: bytes = b'FileWallBall2024Salt', iterations: int = 100000) -> str:
        """
        PBKDF2를 사용하여 키 파생
        
        Args:
            original_key: 원본 키
            salt: 솔트 바이트
            iterations: 반복 횟수
            
        Returns:
            str: Base64 인코딩된 파생 키
        """
        pbkdf2_key = hashlib.pbkdf2_hmac('sha256', original_key.encode(), salt, iterations)
        return base64.b64encode(pbkdf2_key).decode()
    
    @staticmethod
    def validate_key_strength(key: str) -> bool:
        """
        키 강도 검증
        
        Args:
            key: 검증할 키
            
        Returns:
            bool: 키가 충분히 강한지 여부
        """
        if len(key) < 32:
            return False
        
        # Base64 형식인지 확인
        try:
            base64.b64decode(key.encode())
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_environment_setup_command() -> str:
        """
        환경변수 설정 명령어 반환
        
        Returns:
            str: 환경변수 설정 명령어
        """
        import secrets
        new_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        return f'export MASTER_KEY="{new_key}"'


# 전역 함수로 키 접근
def get_master_key() -> str:
    """마스터 키 반환"""
    return SecurityKeyManager.get_master_key()


def is_using_environment_key() -> bool:
    """환경변수 키 사용 여부 확인"""
    return os.getenv('MASTER_KEY') is not None


def get_key_info() -> dict:
    """현재 사용 중인 키 정보 반환"""
    current_key = get_master_key()
    return {
        "source": "environment" if is_using_environment_key() else "default_encrypted",
        "key_length": len(current_key),
        "is_strong": SecurityKeyManager.validate_key_strength(current_key),
        "key_preview": current_key[:10] + "..." if len(current_key) > 10 else current_key
    }