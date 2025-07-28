#!/usr/bin/env python3
"""
파일 저장 및 중복 관리 시스템 테스트 스크립트
"""

import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock
from fastapi import UploadFile

# 테스트용 모듈 임포트
import sys
sys.path.append('.')

from app.services.file_storage_service import FileStorageService


class MockDBSession:
    """Mock 데이터베이스 세션"""
    
    def __init__(self):
        self.files = []
    
    def query(self, model):
        return MockQuery(self.files)
    
    def add(self, file_info):
        self.files.append(file_info)
    
    def commit(self):
        pass
    
    def rollback(self):
        pass


class MockQuery:
    """Mock 쿼리 객체"""
    
    def __init__(self, files):
        self.files = files
    
    def filter(self, *args):
        return self
    
    def first(self):
        # 간단한 필터링 로직
        for file_info in self.files:
            if hasattr(file_info, 'file_hash') and hasattr(file_info, 'is_deleted'):
                if file_info.file_hash == 'test_hash' and not file_info.is_deleted:
                    return file_info
        return None


class MockFileInfo:
    """Mock 파일 정보 객체"""
    
    def __init__(self, file_uuid, file_hash, storage_path, is_deleted=False):
        self.file_uuid = file_uuid
        self.file_hash = file_hash
        self.storage_path = storage_path
        self.is_deleted = is_deleted


def create_mock_upload_file(content: bytes, filename: str) -> Mock:
    """Mock UploadFile 객체 생성"""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = filename
    mock_file.content_type = 'application/octet-stream'
    
    # 비동기 read 메서드 구현
    async def async_read():
        return content
    
    # 비동기 seek 메서드 구현
    async def async_seek(position):
        pass
    
    mock_file.read = async_read
    mock_file.seek = async_seek
    return mock_file


async def test_file_storage():
    """파일 저장 시스템 테스트"""
    print("🧪 파일 저장 및 중복 관리 시스템 테스트 시작\n")
    
    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 데이터베이스 세션 생성
        mock_db = MockDBSession()
        
        # 파일 저장 서비스 생성
        storage_service = FileStorageService(mock_db, temp_dir)
        
        # 테스트 케이스들
        test_cases = [
            {
                'name': '정상 파일 저장',
                'content': b'Hello, World! This is a test file.',
                'filename': 'test.txt',
                'expected_duplicate': False
            },
            {
                'name': '중복 파일 검사',
                'content': b'Hello, World! This is a test file.',
                'filename': 'test2.txt',
                'expected_duplicate': True
            },
            {
                'name': '다른 내용의 파일',
                'content': b'This is a different file content.',
                'filename': 'different.txt',
                'expected_duplicate': False
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"📋 테스트 {i}: {test_case['name']}")
            
            try:
                # Mock UploadFile 객체 생성
                mock_file = create_mock_upload_file(
                    test_case['content'], 
                    test_case['filename']
                )
                
                # 파일 저장 수행
                result = await storage_service.save_file(mock_file, test_case['filename'])
                
                # 결과 확인
                if result['is_duplicate'] == test_case['expected_duplicate']:
                    print(f"✅ 통과: 예상 {test_case['expected_duplicate']}, 실제 {result['is_duplicate']}")
                else:
                    print(f"❌ 실패: 예상 {test_case['expected_duplicate']}, 실제 {result['is_duplicate']}")
                
                # 상세 정보 출력
                if not result['is_duplicate']:
                    print(f"   파일 UUID: {result['file_uuid']}")
                    print(f"   저장 파일명: {result['stored_filename']}")
                    print(f"   파일 크기: {result['file_size']} bytes")
                    print(f"   파일 해시: {result['file_hash']}")
                    
                    # 실제 파일 존재 확인
                    storage_path = Path(result['storage_path'])
                    if storage_path.exists():
                        print(f"   ✅ 파일이 실제로 저장됨: {storage_path}")
                    else:
                        print(f"   ❌ 파일이 저장되지 않음: {storage_path}")
                else:
                    print(f"   중복 파일 UUID: {result['file_uuid']}")
                    print(f"   메시지: {result['message']}")
                
            except Exception as e:
                print(f"❌ 테스트 실행 중 오류: {e}")
            
            print()
        
        # 저장소 통계 테스트
        print("📋 저장소 통계 테스트")
        try:
            stats = storage_service.get_storage_stats()
            print(f"✅ 총 파일 수: {stats.get('total_files', 0)}")
            print(f"✅ 총 크기: {stats.get('total_size_mb', 0):.2f} MB")
            print(f"✅ 디스크 사용률: {stats.get('disk_usage_percent', 0):.1f}%")
        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
        
        # 디렉토리 구조 확인
        print("\n📋 디렉토리 구조 확인")
        try:
            base_path = Path(temp_dir)
            for file_path in base_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(base_path)
                    print(f"   📄 {relative_path}")
        except Exception as e:
            print(f"❌ 디렉토리 구조 확인 실패: {e}")
    
    print("\n🎉 파일 저장 및 중복 관리 시스템 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_file_storage()) 