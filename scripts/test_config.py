#!/usr/bin/env python3
"""
Environment configuration test script.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import Settings


def test_basic_settings():
    """기본 설정 테스트"""
    print("=== Testing Basic Settings ===")
    
    settings = Settings()
    
    print(f"App Name: {settings.app_name}")
    print(f"App Version: {settings.app_version}")
    print(f"Debug: {settings.debug}")
    print(f"Host: {settings.host}")
    print(f"Port: {settings.port}")
    
    print("✅ Basic settings test passed")


def test_database_settings():
    """데이터베이스 설정 테스트"""
    print("\n=== Testing Database Settings ===")
    
    settings = Settings()
    
    print(f"DB Host: {settings.db_host}")
    print(f"DB Port: {settings.db_port}")
    print(f"DB Name: {settings.db_name}")
    print(f"DB User: {settings.db_user}")
    print(f"Database URL: {settings.database_url}")
    
    print("✅ Database settings test passed")


def test_redis_settings():
    """Redis 설정 테스트"""
    print("\n=== Testing Redis Settings ===")
    
    settings = Settings()
    
    print(f"Redis Host: {settings.redis_host}")
    print(f"Redis Port: {settings.redis_port}")
    print(f"Redis DB: {settings.redis_db}")
    print(f"Redis URL: {settings.redis_url}")
    
    print("✅ Redis settings test passed")


def test_file_settings():
    """파일 설정 테스트"""
    print("\n=== Testing File Settings ===")
    
    settings = Settings()
    
    print(f"Upload Dir: {settings.upload_dir}")
    print(f"Max File Size: {settings.max_file_size}")
    print(f"Allowed Extensions: {settings.allowed_extensions}")
    
    # 업로드 디렉토리 생성 확인
    upload_path = Path(settings.upload_dir)
    if upload_path.exists():
        print(f"✅ Upload directory exists: {upload_path}")
    else:
        print(f"⚠️ Upload directory does not exist: {upload_path}")
    
    print("✅ File settings test passed")


def test_validation():
    """설정 검증 테스트"""
    print("\n=== Testing Configuration Validation ===")
    
    try:
        settings = Settings()
        
        # 필수 설정 확인
        assert settings.app_name, "App name should not be empty"
        assert settings.db_host, "DB host should not be empty"
        assert settings.redis_host, "Redis host should not be empty"
        assert settings.upload_dir, "Upload directory should not be empty"
        
        # 타입 검증
        assert isinstance(settings.port, int), "Port should be integer"
        assert isinstance(settings.max_file_size, int), "Max file size should be integer"
        assert isinstance(settings.allowed_extensions, list), "Allowed extensions should be list"
        
        print("✅ Configuration validation test passed")
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    return True


def main():
    """메인 테스트 함수"""
    print("🚀 Starting Configuration Tests...\n")
    
    try:
        test_basic_settings()
        test_database_settings()
        test_redis_settings()
        test_file_settings()
        
        if test_validation():
            print("\n🎉 All configuration tests passed!")
            return 0
        else:
            print("\n❌ Some configuration tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Configuration test error: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 