#!/usr/bin/env python3
"""
업로드 에러 처리 및 복구 시스템 테스트 스크립트
"""

import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock
from fastapi import Request, HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError

# 테스트용 모듈 임포트
import sys
sys.path.append('.')

from app.services.error_handler_service import ErrorHandlerService, ErrorType


class MockDBSession:
    """Mock 데이터베이스 세션"""
    
    def __init__(self):
        self.uploads = []
        self.files = []
    
    def add(self, obj):
        if hasattr(obj, 'upload_status'):
            self.uploads.append(obj)
        elif hasattr(obj, 'file_uuid'):
            self.files.append(obj)
    
    def commit(self):
        pass
    
    def rollback(self):
        pass
    
    def query(self, model):
        return MockQuery(self, model)
    
    def delete(self, obj):
        if obj in self.files:
            self.files.remove(obj)
        elif obj in self.uploads:
            self.uploads.remove(obj)


class MockQuery:
    """Mock 쿼리 객체"""
    
    def __init__(self, session, model):
        self.session = session
        self.model = model
    
    def filter(self, *args):
        return self
    
    def first(self):
        return None
    
    def count(self):
        return 0
    
    def group_by(self, *args):
        return self
    
    def all(self):
        return []


class MockRequest:
    """Mock FastAPI 요청 객체"""
    
    def __init__(self):
        self.client = Mock()
        self.client.host = '127.0.0.1'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Test Browser)',
            'x-forwarded-for': '192.168.1.100'
        }


async def test_error_handler():
    """에러 처리 서비스 테스트"""
    print("🧪 업로드 에러 처리 및 복구 시스템 테스트 시작\n")
    
    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 데이터베이스 세션 생성
        mock_db = MockDBSession()
        
        # 에러 처리 서비스 생성
        error_handler = ErrorHandlerService(mock_db, temp_dir)
        
        # Mock 요청 객체 생성
        mock_request = MockRequest()
        
        # 테스트 케이스들
        test_cases = [
            {
                'name': '검증 에러 처리',
                'error': HTTPException(status_code=400, detail="파일 크기 초과"),
                'file_uuid': 'test-uuid-1',
                'expected_type': ErrorType.VALIDATION_ERROR,
                'expected_status': 400
            },
            {
                'name': '저장소 에러 처리',
                'error': HTTPException(status_code=413, detail="파일이 너무 큽니다"),
                'file_uuid': 'test-uuid-2',
                'expected_type': ErrorType.STORAGE_ERROR,
                'expected_status': 413
            },
            {
                'name': '디스크 용량 부족 에러 처리',
                'error': HTTPException(status_code=507, detail="저장소 용량 부족"),
                'file_uuid': 'test-uuid-3',
                'expected_type': ErrorType.DISK_FULL_ERROR,
                'expected_status': 507
            },
            {
                'name': '데이터베이스 에러 처리',
                'error': IntegrityError("Duplicate entry", None, None),
                'file_uuid': 'test-uuid-4',
                'expected_type': ErrorType.DATABASE_ERROR,
                'expected_status': 500
            },
            {
                'name': '네트워크 에러 처리',
                'error': ConnectionError("Connection refused"),
                'file_uuid': 'test-uuid-5',
                'expected_type': ErrorType.NETWORK_ERROR,
                'expected_status': 503
            },
            {
                'name': '권한 에러 처리',
                'error': OSError("Permission denied"),
                'file_uuid': 'test-uuid-6',
                'expected_type': ErrorType.PERMISSION_ERROR,
                'expected_status': 500
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"📋 테스트 {i}: {test_case['name']}")
            
            try:
                # 에러 처리 수행
                result = await error_handler.handle_upload_error(
                    error=test_case['error'],
                    file_uuid=test_case['file_uuid'],
                    request=mock_request,
                    context={'test_case': test_case['name']}
                )
                
                # 결과 확인
                print(f"✅ 에러 처리 성공")
                print(f"   에러 타입: {result['error_type']}")
                print(f"   상태 코드: {result['status_code']}")
                print(f"   에러 메시지: {result['error_message']}")
                print(f"   재시도 가능: {result['is_retryable']}")
                print(f"   파일 UUID: {result['file_uuid']}")
                print(f"   에러 ID: {result['error_id']}")
                
                # 예상 결과와 비교
                if result['error_type'] == test_case['expected_type'].value:
                    print(f"   ✅ 에러 타입 일치")
                else:
                    print(f"   ❌ 에러 타입 불일치: 예상 {test_case['expected_type'].value}, 실제 {result['error_type']}")
                
                if result['status_code'] == test_case['expected_status']:
                    print(f"   ✅ 상태 코드 일치")
                else:
                    print(f"   ❌ 상태 코드 불일치: 예상 {test_case['expected_status']}, 실제 {result['status_code']}")
                
            except Exception as e:
                print(f"❌ 에러 처리 실패: {e}")
            
            print()
        
        # 에러 통계 테스트
        print("📋 에러 통계 테스트")
        try:
            stats = await error_handler.get_error_statistics(days=30)
            print(f"✅ 에러 통계 조회 성공")
            print(f"   조회 기간: {stats.get('period_days', 0)}일")
            print(f"   총 실패 업로드 수: {stats.get('total_failed_uploads', 0)}")
            print(f"   재시도 가능한 에러: {stats.get('retryable_errors', 0)}")
            print(f"   재시도 불가능한 에러: {stats.get('non_retryable_errors', 0)}")
            print(f"   에러 타입별 통계: {stats.get('error_types', {})}")
            
        except Exception as e:
            print(f"❌ 에러 통계 테스트 실패: {e}")
        
        # 오래된 에러 로그 정리 테스트
        print("\n📋 오래된 에러 로그 정리 테스트")
        try:
            deleted_count = await error_handler.cleanup_old_error_logs(days=90)
            print(f"✅ 오래된 에러 로그 정리 성공")
            print(f"   삭제된 로그 수: {deleted_count}")
            
        except Exception as e:
            print(f"❌ 오래된 에러 로그 정리 테스트 실패: {e}")
        
        # 로그 파일 생성 테스트
        print("\n📋 에러 로그 파일 생성 테스트")
        try:
            # 임시 에러 정보 생성
            error_info = {
                'error_id': 'test-error-id',
                'file_uuid': 'test-uuid',
                'error_type': 'test_error',
                'error_message': 'Test error message',
                'upload_ip': '127.0.0.1',
                'timestamp': '2024-01-01T00:00:00'
            }
            
            # 로그 파일에 기록
            await error_handler._write_error_log(error_info)
            
            # 로그 파일 존재 확인
            log_file = Path(temp_dir) / "logs" / "upload_errors.log"
            if log_file.exists():
                print(f"✅ 에러 로그 파일 생성 성공: {log_file}")
                print(f"   로그 파일 크기: {log_file.stat().st_size} bytes")
            else:
                print(f"❌ 에러 로그 파일 생성 실패")
                
        except Exception as e:
            print(f"❌ 에러 로그 파일 생성 테스트 실패: {e}")
    
    print("\n🎉 업로드 에러 처리 및 복구 시스템 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_error_handler()) 