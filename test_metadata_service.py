#!/usr/bin/env python3
"""
메타데이터 저장 및 관계 설정 시스템 테스트 스크립트
"""

import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock
from fastapi import Request

# 테스트용 모듈 임포트
import sys
sys.path.append('.')

from app.services.metadata_service import MetadataService


class MockDBSession:
    """Mock 데이터베이스 세션"""
    
    def __init__(self):
        self.files = []
        self.uploads = []
        self.tags = []
        self.tag_relations = []
        self.categories = []
    
    def begin(self):
        pass
    
    def add(self, obj):
        if hasattr(obj, 'file_uuid'):
            self.files.append(obj)
        elif hasattr(obj, 'upload_ip'):
            self.uploads.append(obj)
        elif hasattr(obj, 'name'):
            self.tags.append(obj)
        elif hasattr(obj, 'tag_id'):
            self.tag_relations.append(obj)
        elif hasattr(obj, 'category_name'):
            self.categories.append(obj)
    
    def flush(self):
        pass
    
    def commit(self):
        pass
    
    def rollback(self):
        pass
    
    def query(self, model):
        return MockQuery(self, model)
    
    def filter(self, *args):
        return self
    
    def order_by(self, *args):
        return self
    
    def first(self):
        return None
    
    def all(self):
        return []


class MockQuery:
    """Mock 쿼리 객체"""
    
    def __init__(self, session, model):
        self.session = session
        self.model = model
    
    def filter(self, *args):
        return self
    
    def join(self, *args):
        return self
    
    def order_by(self, *args):
        return self
    
    def with_entities(self, *args):
        return self
    
    def scalar(self):
        return 0
    
    def count(self):
        return 0
    
    def first(self):
        return None
    
    def all(self):
        return []
    
    def delete(self):
        return 0


class MockRequest:
    """Mock FastAPI 요청 객체"""
    
    def __init__(self):
        self.client = Mock()
        self.client.host = '127.0.0.1'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Test Browser)',
            'x-forwarded-for': '192.168.1.100'
        }


class MockFileInfo:
    """Mock 파일 정보 객체"""
    
    def __init__(self, file_uuid, original_filename, stored_filename, 
                 file_extension, mime_type, file_size, file_hash, 
                 storage_path, category_id=None, is_public=True, 
                 description=None, is_deleted=False):
        self.file_uuid = file_uuid
        self.original_filename = original_filename
        self.stored_filename = stored_filename
        self.file_extension = file_extension
        self.mime_type = mime_type
        self.file_size = file_size
        self.file_hash = file_hash
        self.storage_path = storage_path
        self.category_id = category_id
        self.is_public = is_public
        self.description = description
        self.is_deleted = is_deleted
        self.created_at = Mock()
        self.updated_at = Mock()


class MockFileUpload:
    """Mock 업로드 기록 객체"""
    
    def __init__(self, file_uuid, upload_status, upload_ip, user_agent, upload_time):
        self.file_uuid = file_uuid
        self.upload_status = upload_status
        self.upload_ip = upload_ip
        self.user_agent = user_agent
        self.upload_time = upload_time
        self.created_at = Mock()


class MockFileTag:
    """Mock 태그 객체"""
    
    def __init__(self, id, name, display_name=None):
        self.id = id
        self.name = name
        self.display_name = display_name or name
        self.created_at = Mock()


class MockFileCategory:
    """Mock 카테고리 객체"""
    
    def __init__(self, id, name, description=None, is_active=True):
        self.id = id
        self.name = name
        self.description = description
        self.is_active = is_active


async def test_metadata_service():
    """메타데이터 서비스 테스트"""
    print("🧪 메타데이터 저장 및 관계 설정 시스템 테스트 시작\n")
    
    # Mock 데이터베이스 세션 생성
    mock_db = MockDBSession()
    
    # 메타데이터 서비스 생성
    metadata_service = MetadataService(mock_db)
    
    # Mock 요청 객체 생성
    mock_request = MockRequest()
    
    # 테스트 케이스들
    test_cases = [
        {
            'name': '기본 메타데이터 저장',
            'file_uuid': 'test-uuid-1',
            'original_filename': 'test.txt',
            'stored_filename': 'test-uuid-1.txt',
            'file_extension': '.txt',
            'mime_type': 'text/plain',
            'file_size': 1024,
            'file_hash': 'test-hash-1',
            'storage_path': '/uploads/test/test-uuid-1.txt',
            'metadata': {
                'is_public': True,
                'description': '테스트 파일입니다.'
            }
        },
        {
            'name': '태그가 포함된 메타데이터 저장',
            'file_uuid': 'test-uuid-2',
            'original_filename': 'image.jpg',
            'stored_filename': 'test-uuid-2.jpg',
            'file_extension': '.jpg',
            'mime_type': 'image/jpeg',
            'file_size': 2048,
            'file_hash': 'test-hash-2',
            'storage_path': '/uploads/test/test-uuid-2.jpg',
            'metadata': {
                'is_public': True,
                'description': '테스트 이미지입니다.',
                'tags': ['이미지', '테스트', 'jpg']
            }
        },
        {
            'name': '카테고리가 포함된 메타데이터 저장',
            'file_uuid': 'test-uuid-3',
            'original_filename': 'document.pdf',
            'stored_filename': 'test-uuid-3.pdf',
            'file_extension': '.pdf',
            'mime_type': 'application/pdf',
            'file_size': 5120,
            'file_hash': 'test-hash-3',
            'storage_path': '/uploads/test/test-uuid-3.pdf',
            'metadata': {
                'is_public': False,
                'description': '비공개 문서입니다.',
                'category_id': 1,
                'tags': ['문서', 'pdf', '비공개']
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📋 테스트 {i}: {test_case['name']}")
        
        try:
            # 메타데이터 저장 수행
            result = await metadata_service.save_file_metadata(
                file_uuid=test_case['file_uuid'],
                original_filename=test_case['original_filename'],
                stored_filename=test_case['stored_filename'],
                file_extension=test_case['file_extension'],
                mime_type=test_case['mime_type'],
                file_size=test_case['file_size'],
                file_hash=test_case['file_hash'],
                storage_path=test_case['storage_path'],
                request=mock_request,
                metadata=test_case.get('metadata')
            )
            
            # 결과 확인
            print(f"✅ 메타데이터 저장 성공")
            print(f"   파일 UUID: {result['file_uuid']}")
            print(f"   원본 파일명: {result['original_filename']}")
            print(f"   저장 파일명: {result['stored_filename']}")
            print(f"   파일 크기: {result['file_size']} bytes")
            print(f"   MIME 타입: {result['mime_type']}")
            print(f"   파일 해시: {result['file_hash']}")
            print(f"   공개 여부: {result['is_public']}")
            print(f"   설명: {result['description']}")
            print(f"   업로드 IP: {result['upload_ip']}")
            print(f"   태그: {result['tags']}")
            
        except Exception as e:
            print(f"❌ 메타데이터 저장 실패: {e}")
        
        print()
    
    # 메타데이터 조회 테스트
    print("📋 메타데이터 조회 테스트")
    try:
        # Mock 파일 정보 설정
        mock_file_info = MockFileInfo(
            file_uuid='test-uuid-1',
            original_filename='test.txt',
            stored_filename='test-uuid-1.txt',
            file_extension='.txt',
            mime_type='text/plain',
            file_size=1024,
            file_hash='test-hash-1',
            storage_path='/uploads/test/test-uuid-1.txt',
            is_public=True,
            description='테스트 파일입니다.'
        )
        
        # Mock 업로드 기록 설정
        mock_upload = MockFileUpload(
            file_uuid='test-uuid-1',
            upload_status='success',
            upload_ip='192.168.1.100',
            user_agent='Mozilla/5.0 (Test Browser)',
            upload_time=Mock()
        )
        
        # Mock 태그 설정
        mock_tags = [
            MockFileTag(1, '테스트'),
            MockFileTag(2, '텍스트')
        ]
        
        # Mock 카테고리 설정
        mock_category = MockFileCategory(
            id=1,
            name='일반',
            description='일반 파일'
        )
        
        # Mock 쿼리 결과 설정
        mock_db.files = [mock_file_info]
        mock_db.uploads = [mock_upload]
        mock_db.tags = mock_tags
        mock_db.categories = [mock_category]
        
        # 메타데이터 조회
        metadata = metadata_service.get_file_metadata('test-uuid-1')
        
        if metadata:
            print(f"✅ 메타데이터 조회 성공")
            print(f"   파일 UUID: {metadata['file_uuid']}")
            print(f"   원본 파일명: {metadata['original_filename']}")
            print(f"   파일 크기: {metadata['file_size']} bytes")
            print(f"   공개 여부: {metadata['is_public']}")
            print(f"   설명: {metadata['description']}")
            print(f"   업로드 IP: {metadata['upload_ip']}")
            print(f"   태그 수: {len(metadata['tags'])}")
            print(f"   카테고리: {metadata['category']['name'] if metadata['category'] else '없음'}")
        else:
            print("❌ 메타데이터 조회 실패")
            
    except Exception as e:
        print(f"❌ 메타데이터 조회 테스트 실패: {e}")
    
    # 업로드 통계 테스트
    print("\n📋 업로드 통계 테스트")
    try:
        stats = metadata_service.get_upload_statistics(days=30)
        print(f"✅ 업로드 통계 조회 성공")
        print(f"   조회 기간: {stats.get('period_days', 0)}일")
        print(f"   총 업로드 수: {stats.get('total_uploads', 0)}")
        print(f"   성공한 업로드 수: {stats.get('successful_uploads', 0)}")
        print(f"   실패한 업로드 수: {stats.get('failed_uploads', 0)}")
        print(f"   성공률: {stats.get('success_rate', 0):.1f}%")
        print(f"   총 파일 크기: {stats.get('total_size_mb', 0):.2f} MB")
        
    except Exception as e:
        print(f"❌ 업로드 통계 테스트 실패: {e}")
    
    print("\n🎉 메타데이터 저장 및 관계 설정 시스템 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_metadata_service()) 