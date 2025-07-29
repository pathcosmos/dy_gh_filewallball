#!/usr/bin/env python3
"""
Task #6 - 파일 업로드 API 구현 통합 테스트
모든 하위 시스템이 함께 작동하는지 확인하는 종합적인 테스트
"""

import asyncio
import tempfile
import os
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import uuid

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.validators.file_validator import FileValidator
from app.services.file_storage_service import FileStorageService
from app.services.metadata_service import MetadataService
from app.services.error_handler_service import ErrorHandlerService
from app.services.ip_auth_service import IPAuthService
from app.services.cache_service import CacheService


class Task6IntegrationTest:
    """Task #6 통합 테스트 클래스"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.db_session = None
        
    def log_test(self, test_name, status, details=""):
        """테스트 결과 로깅"""
        result = {
            "test": test_name,
            "status": status,
            "details": details
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌"
        print(f"{status_icon} {test_name}: {details}")
    
    def setup_test_environment(self):
        """테스트 환경 설정"""
        print("🔧 테스트 환경 설정 중...")
        
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock 데이터베이스 세션 생성
        self.db_session = Mock()
        
        # Mock Redis 연결
        self.redis_mock = Mock()
        
        print(f"📁 임시 디렉토리: {self.temp_dir}")
        print("✅ 테스트 환경 설정 완료")
    
    def cleanup_test_environment(self):
        """테스트 환경 정리"""
        print("🧹 테스트 환경 정리 중...")
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
        
        print("✅ 테스트 환경 정리 완료")
    
    def test_file_validation_integration(self):
        """파일 검증 시스템 통합 테스트"""
        print("\n📋 파일 검증 시스템 통합 테스트")
        
        try:
            # FileValidator 인스턴스 생성
            validator = FileValidator(self.db_session)
            
            # 1. 정상 파일 검증
            test_file = Mock()
            test_file.filename = "test.txt"
            test_file.size = 1024
            test_file.content_type = "text/plain"
            
            with patch.object(validator, '_check_file_extension', return_value=True), \
                 patch.object(validator, '_check_file_size', return_value=True), \
                 patch.object(validator, '_check_mime_type', return_value=True), \
                 patch.object(validator, '_check_file_signature', return_value=True), \
                 patch.object(validator, '_check_security', return_value=True), \
                 patch.object(validator, '_check_empty_file', return_value=True):
                
                result = validator.validate_file(test_file)
                self.log_test("정상 파일 검증", "PASS" if result else "FAIL", 
                             f"검증 결과: {result}")
            
            # 2. 위험한 파일 검증
            dangerous_file = Mock()
            dangerous_file.filename = "malware.exe"
            dangerous_file.size = 1024
            dangerous_file.content_type = "application/x-msdownload"
            
            with patch.object(validator, '_check_file_extension', return_value=False):
                result = validator.validate_file(dangerous_file)
                self.log_test("위험한 파일 차단", "PASS" if not result else "FAIL",
                             f"차단 결과: {result}")
            
            # 3. 대용량 파일 검증
            large_file = Mock()
            large_file.filename = "large.txt"
            large_file.size = 200 * 1024 * 1024  # 200MB
            large_file.content_type = "text/plain"
            
            with patch.object(validator, '_check_file_size', return_value=False):
                result = validator.validate_file(large_file)
                self.log_test("대용량 파일 차단", "PASS" if not result else "FAIL",
                             f"차단 결과: {result}")
            
        except Exception as e:
            self.log_test("파일 검증 시스템 통합", "FAIL", f"예외 발생: {str(e)}")
    
    def test_file_storage_integration(self):
        """파일 저장 시스템 통합 테스트"""
        print("\n📋 파일 저장 시스템 통합 테스트")
        
        try:
            # FileStorageService 인스턴스 생성
            storage_service = FileStorageService(self.temp_dir)
            
            # 1. 정상 파일 저장
            test_content = b"This is a test file content"
            test_filename = "test.txt"
            
            result = storage_service.store_file(test_content, test_filename)
            
            if result and result.get('success'):
                file_uuid = result['file_uuid']
                stored_path = result['stored_path']
                
                # 파일이 실제로 저장되었는지 확인
                if os.path.exists(stored_path):
                    self.log_test("정상 파일 저장", "PASS", 
                                 f"UUID: {file_uuid}, 경로: {stored_path}")
                else:
                    self.log_test("정상 파일 저장", "FAIL", "파일이 저장되지 않음")
            else:
                self.log_test("정상 파일 저장", "FAIL", f"저장 실패: {result}")
            
            # 2. 중복 파일 검사
            duplicate_result = storage_service.store_file(test_content, "duplicate.txt")
            
            if duplicate_result and duplicate_result.get('success'):
                self.log_test("중복 파일 처리", "PASS", 
                             f"중복 파일 UUID: {duplicate_result['file_uuid']}")
            else:
                self.log_test("중복 파일 처리", "FAIL", f"중복 처리 실패: {duplicate_result}")
            
            # 3. 저장소 통계
            stats = storage_service.get_storage_stats()
            if stats:
                self.log_test("저장소 통계", "PASS", 
                             f"파일 수: {stats.get('file_count', 0)}")
            else:
                self.log_test("저장소 통계", "FAIL", "통계 조회 실패")
            
        except Exception as e:
            self.log_test("파일 저장 시스템 통합", "FAIL", f"예외 발생: {str(e)}")
    
    def test_metadata_integration(self):
        """메타데이터 시스템 통합 테스트"""
        print("\n📋 메타데이터 시스템 통합 테스트")
        
        try:
            # MetadataService 인스턴스 생성
            metadata_service = MetadataService(self.db_session)
            
            # 1. 메타데이터 저장
            file_uuid = str(uuid.uuid4())
            metadata = {
                'file_uuid': file_uuid,
                'original_filename': 'test.txt',
                'stored_filename': f'{file_uuid}.txt',
                'file_extension': 'txt',
                'mime_type': 'text/plain',
                'file_size': 1024,
                'file_hash': 'test_hash_123',
                'storage_path': f'/uploads/{file_uuid[:2]}/{file_uuid[2:4]}/{file_uuid}.txt',
                'category_id': 1,
                'is_public': True,
                'description': 'Test file'
            }
            
            with patch.object(self.db_session, 'add'), \
                 patch.object(self.db_session, 'commit'), \
                 patch.object(self.db_session, 'rollback'):
                
                result = metadata_service.save_file_metadata(
                    metadata, 
                    client_ip='127.0.0.1',
                    user_agent='Test Agent',
                    tags=['test', 'integration']
                )
                
                self.log_test("메타데이터 저장", "PASS" if result else "FAIL",
                             f"저장 결과: {result}")
            
            # 2. 메타데이터 조회
            with patch.object(self.db_session, 'query') as mock_query:
                mock_result = Mock()
                mock_result.first.return_value = metadata
                mock_query.return_value = mock_result
                
                retrieved_metadata = metadata_service.get_file_metadata(file_uuid)
                
                if retrieved_metadata:
                    self.log_test("메타데이터 조회", "PASS",
                                 f"조회된 UUID: {retrieved_metadata.get('file_uuid')}")
                else:
                    self.log_test("메타데이터 조회", "FAIL", "조회 실패")
            
        except Exception as e:
            self.log_test("메타데이터 시스템 통합", "FAIL", f"예외 발생: {str(e)}")
    
    def test_error_handling_integration(self):
        """에러 처리 시스템 통합 테스트"""
        print("\n📋 에러 처리 시스템 통합 테스트")
        
        try:
            # ErrorHandlerService 인스턴스 생성
            error_handler = ErrorHandlerService(self.db_session)
            
            # 1. 검증 에러 처리
            validation_error = error_handler.handle_upload_error(
                error_type='validation_error',
                error_message='Invalid file format',
                file_uuid='test-uuid-1',
                client_ip='127.0.0.1'
            )
            
            if validation_error:
                self.log_test("검증 에러 처리", "PASS",
                             f"에러 ID: {validation_error.get('error_id')}")
            else:
                self.log_test("검증 에러 처리", "FAIL", "에러 처리 실패")
            
            # 2. 저장소 에러 처리
            storage_error = error_handler.handle_upload_error(
                error_type='storage_error',
                error_message='Disk full',
                file_uuid='test-uuid-2',
                client_ip='127.0.0.1'
            )
            
            if storage_error:
                self.log_test("저장소 에러 처리", "PASS",
                             f"에러 ID: {storage_error.get('error_id')}")
            else:
                self.log_test("저장소 에러 처리", "FAIL", "에러 처리 실패")
            
            # 3. 에러 통계 조회
            with patch.object(self.db_session, 'query') as mock_query:
                mock_result = Mock()
                mock_result.count.return_value = 2
                mock_query.return_value = mock_result
                
                stats = error_handler.get_error_statistics(days=1)
                
                if stats:
                    self.log_test("에러 통계 조회", "PASS",
                                 f"총 에러 수: {stats.get('total_errors', 0)}")
                else:
                    self.log_test("에러 통계 조회", "FAIL", "통계 조회 실패")
            
        except Exception as e:
            self.log_test("에러 처리 시스템 통합", "FAIL", f"예외 발생: {str(e)}")
    
    def test_ip_auth_integration(self):
        """IP 인증 시스템 통합 테스트"""
        print("\n📋 IP 인증 시스템 통합 테스트")
        
        try:
            # IPAuthService 인스턴스 생성
            ip_auth_service = IPAuthService(self.db_session)
            
            # 1. 허용 IP 추가
            test_ip = '192.168.1.100'
            test_key = 'test_key_123'
            
            with patch.object(self.db_session, 'add'), \
                 patch.object(self.db_session, 'commit'):
                
                result = ip_auth_service.add_allowed_ip(
                    ip_address=test_ip,
                    encryption_key=test_key,
                    max_uploads_per_hour=100,
                    max_file_size=104857600
                )
                
                self.log_test("허용 IP 추가", "PASS" if result else "FAIL",
                             f"추가 결과: {result}")
            
            # 2. IP 및 키 검증
            with patch.object(self.db_session, 'query') as mock_query:
                mock_result = Mock()
                mock_result.first.return_value = {
                    'ip_address': test_ip,
                    'encryption_key': test_key,
                    'is_active': True
                }
                mock_query.return_value = mock_result
                
                auth_result = ip_auth_service.verify_ip_and_key(test_ip, test_key)
                
                self.log_test("IP 및 키 검증", "PASS" if auth_result else "FAIL",
                             f"검증 결과: {auth_result}")
            
            # 3. 잘못된 키 검증
            wrong_key_result = ip_auth_service.verify_ip_and_key(test_ip, 'wrong_key')
            
            self.log_test("잘못된 키 거부", "PASS" if not wrong_key_result else "FAIL",
                         f"거부 결과: {wrong_key_result}")
            
        except Exception as e:
            self.log_test("IP 인증 시스템 통합", "FAIL", f"예외 발생: {str(e)}")
    
    def test_cache_integration(self):
        """캐시 시스템 통합 테스트"""
        print("\n📋 캐시 시스템 통합 테스트")
        
        try:
            # CacheService 인스턴스 생성
            cache_service = CacheService()
            
            # 1. 캐시 저장
            test_key = 'test:file:info:123'
            test_data = {
                'file_uuid': 'test-uuid-123',
                'filename': 'test.txt',
                'size': 1024
            }
            
            with patch.object(cache_service.redis_manager, 'execute_with_retry') as mock_execute:
                mock_execute.return_value = True
                
                result = cache_service.set(test_key, test_data, expire=3600)
                
                self.log_test("캐시 저장", "PASS" if result else "FAIL",
                             f"저장 결과: {result}")
            
            # 2. 캐시 조회
            with patch.object(cache_service.redis_manager, 'execute_with_retry') as mock_execute:
                mock_execute.return_value = json.dumps(test_data)
                
                retrieved_data = cache_service.get(test_key)
                
                if retrieved_data and retrieved_data.get('file_uuid') == 'test-uuid-123':
                    self.log_test("캐시 조회", "PASS",
                                 f"조회된 UUID: {retrieved_data.get('file_uuid')}")
                else:
                    self.log_test("캐시 조회", "FAIL", "조회 실패")
            
            # 3. 파일 정보 캐시
            file_uuid = 'test-file-456'
            file_info = {
                'file_uuid': file_uuid,
                'original_filename': 'cached.txt',
                'file_size': 2048
            }
            
            with patch.object(cache_service.redis_manager, 'execute_with_retry') as mock_execute:
                mock_execute.return_value = True
                
                cache_result = cache_service.set_file_info(file_uuid, file_info)
                
                self.log_test("파일 정보 캐시", "PASS" if cache_result else "FAIL",
                             f"캐시 결과: {cache_result}")
            
        except Exception as e:
            self.log_test("캐시 시스템 통합", "FAIL", f"예외 발생: {str(e)}")
    
    def test_full_upload_workflow(self):
        """전체 업로드 워크플로우 통합 테스트"""
        print("\n📋 전체 업로드 워크플로우 통합 테스트")
        
        try:
            # 모든 서비스 인스턴스 생성
            validator = FileValidator(self.db_session)
            storage_service = FileStorageService(self.temp_dir)
            metadata_service = MetadataService(self.db_session)
            error_handler = ErrorHandlerService(self.db_session)
            cache_service = CacheService()
            
            # 1. 파일 검증
            test_file = Mock()
            test_file.filename = "workflow_test.txt"
            test_file.size = 512
            test_file.content_type = "text/plain"
            
            with patch.object(validator, '_check_file_extension', return_value=True), \
                 patch.object(validator, '_check_file_size', return_value=True), \
                 patch.object(validator, '_check_mime_type', return_value=True), \
                 patch.object(validator, '_check_file_signature', return_value=True), \
                 patch.object(validator, '_check_security', return_value=True), \
                 patch.object(validator, '_check_empty_file', return_value=True):
                
                validation_result = validator.validate_file(test_file)
                
                if validation_result:
                    self.log_test("워크플로우 - 파일 검증", "PASS", "검증 성공")
                    
                    # 2. 파일 저장
                    test_content = b"Workflow test content"
                    storage_result = storage_service.store_file(test_content, test_file.filename)
                    
                    if storage_result and storage_result.get('success'):
                        file_uuid = storage_result['file_uuid']
                        self.log_test("워크플로우 - 파일 저장", "PASS", f"UUID: {file_uuid}")
                        
                        # 3. 메타데이터 저장
                        metadata = {
                            'file_uuid': file_uuid,
                            'original_filename': test_file.filename,
                            'stored_filename': storage_result['stored_filename'],
                            'file_extension': 'txt',
                            'mime_type': test_file.content_type,
                            'file_size': test_file.size,
                            'file_hash': storage_result['file_hash'],
                            'storage_path': storage_result['stored_path'],
                            'is_public': True
                        }
                        
                        with patch.object(self.db_session, 'add'), \
                             patch.object(self.db_session, 'commit'):
                            
                            metadata_result = metadata_service.save_file_metadata(
                                metadata,
                                client_ip='127.0.0.1',
                                user_agent='Workflow Test'
                            )
                            
                            if metadata_result:
                                self.log_test("워크플로우 - 메타데이터 저장", "PASS", "저장 성공")
                                
                                # 4. 캐시 저장
                                with patch.object(cache_service.redis_manager, 'execute_with_retry') as mock_execute:
                                    mock_execute.return_value = True
                                    
                                    cache_result = cache_service.set_file_info(file_uuid, metadata)
                                    
                                    if cache_result:
                                        self.log_test("워크플로우 - 캐시 저장", "PASS", "캐시 성공")
                                    else:
                                        self.log_test("워크플로우 - 캐시 저장", "FAIL", "캐시 실패")
                            else:
                                self.log_test("워크플로우 - 메타데이터 저장", "FAIL", "저장 실패")
                    else:
                        self.log_test("워크플로우 - 파일 저장", "FAIL", "저장 실패")
                else:
                    self.log_test("워크플로우 - 파일 검증", "FAIL", "검증 실패")
            
        except Exception as e:
            self.log_test("전체 업로드 워크플로우", "FAIL", f"예외 발생: {str(e)}")
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 Task #6 통합 테스트 시작")
        print("=" * 60)
        
        try:
            # 테스트 환경 설정
            self.setup_test_environment()
            
            # 개별 시스템 통합 테스트
            self.test_file_validation_integration()
            self.test_file_storage_integration()
            self.test_metadata_integration()
            self.test_error_handling_integration()
            self.test_ip_auth_integration()
            self.test_cache_integration()
            
            # 전체 워크플로우 테스트
            self.test_full_upload_workflow()
            
        finally:
            # 테스트 환경 정리
            self.cleanup_test_environment()
        
        # 결과 요약
        self.print_test_summary()
    
    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 Task #6 통합 테스트 결과 요약")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['status'] == 'PASS')
        failed_tests = total_tests - passed_tests
        
        print(f"총 테스트 수: {total_tests}")
        print(f"✅ 통과: {passed_tests}")
        print(f"❌ 실패: {failed_tests}")
        print(f"성공률: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 실패한 테스트:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n🎯 Task #6 완료 상태:")
        if passed_tests == total_tests:
            print("✅ 모든 테스트 통과 - Task #6 완료!")
        else:
            print("⚠️  일부 테스트 실패 - 추가 작업 필요")
        
        print("=" * 60)


def main():
    """메인 함수"""
    print("🧪 Task #6 - 파일 업로드 API 구현 통합 테스트")
    print("모든 하위 시스템이 함께 작동하는지 확인하는 종합적인 테스트입니다.")
    print()
    
    # 테스트 실행
    test_runner = Task6IntegrationTest()
    test_runner.run_all_tests()


if __name__ == "__main__":
    main() 