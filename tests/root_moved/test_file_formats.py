#!/usr/bin/env python3
"""
FileWallBall API - 다양한 파일 형식 테스트 스크립트

이 스크립트는 다양한 형식의 파일을 생성하고 API를 통해 업로드/다운로드하여
시스템의 안정성과 성능을 테스트합니다.
"""

import os
import time
import hashlib
import zipfile
import tempfile
import requests
import json
import threading
from pathlib import Path
from typing import Dict, List, Tuple
import psutil
import concurrent.futures

class FileFormatTester:
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base_url = api_base_url
        self.test_results = {}
        self.uploaded_files = []
        self.start_time = time.time()
        self.process = psutil.Process()
        
    def log(self, message: str):
        """로그 메시지 출력"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """현재 메모리 사용량 조회"""
        memory = self.process.memory_info()
        return {
            "rss_mb": memory.rss / 1024 / 1024,  # RSS in MB
            "vms_mb": memory.vms / 1024 / 1024,  # VMS in MB
            "percent": self.process.memory_percent()
        }
    
    def create_test_files(self) -> Dict[str, str]:
        """다양한 형식의 테스트 파일 생성"""
        self.log("테스트 파일 생성 시작...")
        test_files = {}
        
        # 1. 텍스트 파일 (1KB, UTF-8)
        text_content = "안녕하세요! Hello World! こんにちは! 🌍\n" * 50
        text_file = "test_text_1kb.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        test_files[text_file] = "text/plain"
        self.log(f"텍스트 파일 생성 완료: {text_file} ({os.path.getsize(text_file)} bytes)")
        
        # 2. 이미지 파일 (PNG, 100KB) - 간단한 PNG 생성
        png_file = "test_image_100kb.png"
        # 간단한 PNG 헤더와 데이터 생성 (실제로는 더 복잡하지만 테스트용)
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100000  # 100KB PNG
        with open(png_file, 'wb') as f:
            f.write(png_data)
        test_files[png_file] = "image/png"
        self.log(f"이미지 파일 생성 완료: {png_file} ({os.path.getsize(png_file)} bytes)")
        
        # 3. 바이너리 파일 (ZIP, 1MB)
        zip_file = "test_binary_1mb.zip"
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1MB 크기의 더미 데이터로 ZIP 파일 생성
            dummy_data = b'0' * 1000000
            zf.writestr('dummy.txt', dummy_data)
        test_files[zip_file] = "application/zip"
        self.log(f"바이너리 파일 생성 완료: {zip_file} ({os.path.getsize(zip_file)} bytes)")
        
        # 4. 대용량 파일 (10MB)
        large_file = "test_large_10mb.bin"
        with open(large_file, 'wb') as f:
            # 10MB 크기의 더미 데이터 생성
            chunk_size = 1024 * 1024  # 1MB
            for _ in range(10):
                f.write(b'1' * chunk_size)
        test_files[large_file] = "application/octet-stream"
        self.log(f"대용량 파일 생성 완료: {large_file} ({os.path.getsize(large_file)} bytes)")
        
        return test_files
    
    def calculate_file_hash(self, file_path: str) -> str:
        """파일의 SHA256 해시 계산"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def upload_file(self, file_path: str, mime_type: str) -> Dict:
        """파일 업로드"""
        start_time = time.time()
        memory_before = self.get_memory_usage()
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path, f, mime_type)}
                response = requests.post(f"{self.api_base_url}/upload", files=files)
                
            upload_time = time.time() - start_time
            memory_after = self.get_memory_usage()
            
            if response.status_code == 200:
                result = response.json()
                file_info = {
                    'file_id': result['file_id'],
                    'filename': result['filename'],
                    'file_size': result['file_size'],
                    'upload_time': upload_time,
                    'memory_before': memory_before,
                    'memory_after': memory_after,
                    'memory_diff': {
                        'rss_mb': memory_after['rss_mb'] - memory_before['rss_mb'],
                        'vms_mb': memory_after['vms_mb'] - memory_before['vms_mb']
                    }
                }
                self.log(f"파일 업로드 성공: {file_path} (ID: {result['file_id']}, 시간: {upload_time:.2f}s)")
                return file_info
            else:
                self.log(f"파일 업로드 실패: {file_path} (상태 코드: {response.status_code})")
                return None
                
        except Exception as e:
            self.log(f"파일 업로드 오류: {file_path} - {str(e)}")
            return None
    
    def download_file(self, file_id: str, original_filename: str) -> Dict:
        """파일 다운로드"""
        start_time = time.time()
        memory_before = self.get_memory_usage()
        
        try:
            response = requests.get(f"{self.api_base_url}/download/{file_id}")
            download_time = time.time() - start_time
            memory_after = self.get_memory_usage()
            
            if response.status_code == 200:
                # 다운로드된 파일 저장
                downloaded_filename = f"downloaded_{original_filename}"
                with open(downloaded_filename, 'wb') as f:
                    f.write(response.content)
                
                file_info = {
                    'file_id': file_id,
                    'filename': original_filename,
                    'download_time': download_time,
                    'memory_before': memory_before,
                    'memory_after': memory_after,
                    'memory_diff': {
                        'rss_mb': memory_after['rss_mb'] - memory_before['rss_mb'],
                        'vms_mb': memory_after['vms_mb'] - memory_before['vms_mb']
                    }
                }
                self.log(f"파일 다운로드 성공: {original_filename} (시간: {download_time:.2f}s)")
                return file_info
            else:
                self.log(f"파일 다운로드 실패: {original_filename} (상태 코드: {response.status_code})")
                return None
                
        except Exception as e:
            self.log(f"파일 다운로드 오류: {original_filename} - {str(e)}")
            return None
    
    def verify_file_integrity(self, original_file: str, downloaded_file: str) -> bool:
        """파일 무결성 검증 (SHA256 해시 비교)"""
        try:
            original_hash = self.calculate_file_hash(original_file)
            downloaded_hash = self.calculate_file_hash(downloaded_file)
            
            if original_hash == downloaded_hash:
                self.log(f"파일 무결성 검증 성공: {original_file}")
                return True
            else:
                self.log(f"파일 무결성 검증 실패: {original_file}")
                self.log(f"  원본 해시: {original_hash}")
                self.log(f"  다운로드 해시: {downloaded_hash}")
                return False
        except Exception as e:
            self.log(f"파일 무결성 검증 오류: {original_file} - {str(e)}")
            return False
    
    def test_single_file(self, file_path: str, mime_type: str) -> Dict:
        """단일 파일 테스트 (업로드 → 다운로드 → 무결성 검증)"""
        self.log(f"=== {file_path} 테스트 시작 ===")
        
        # 1. 파일 업로드
        upload_result = self.upload_file(file_path, mime_type)
        if not upload_result:
            return {'file': file_path, 'status': 'upload_failed'}
        
        # 2. 파일 다운로드
        download_result = self.download_file(upload_result['file_id'], upload_result['filename'])
        if not download_result:
            return {'file': file_path, 'status': 'download_failed'}
        
        # 3. 파일 무결성 검증
        downloaded_filename = f"downloaded_{upload_result['filename']}"
        integrity_ok = self.verify_file_integrity(file_path, downloaded_filename)
        
        # 4. 결과 정리
        result = {
            'file': file_path,
            'status': 'success' if integrity_ok else 'integrity_failed',
            'file_id': upload_result['file_id'],
            'file_size': upload_result['file_size'],
            'upload_time': upload_result['upload_time'],
            'download_time': download_result['download_time'],
            'integrity_ok': integrity_ok,
            'memory_usage': {
                'upload': upload_result['memory_diff'],
                'download': download_result['memory_diff']
            }
        }
        
        # 다운로드된 파일 정리
        if os.path.exists(downloaded_filename):
            os.remove(downloaded_filename)
        
        self.log(f"=== {file_path} 테스트 완료 ===")
        return result
    
    def test_concurrent_uploads(self, test_files: Dict[str, str], max_workers: int = 5) -> List[Dict]:
        """동시 업로드 테스트"""
        self.log(f"동시 업로드 테스트 시작 (최대 {max_workers}개 동시)")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 업로드 작업 제출
            future_to_file = {
                executor.submit(self.upload_file, file_path, mime_type): file_path
                for file_path, mime_type in test_files.items()
            }
            
            results = []
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.log(f"동시 업로드 완료: {file_path}")
                    else:
                        self.log(f"동시 업로드 실패: {file_path}")
                except Exception as e:
                    self.log(f"동시 업로드 오류: {file_path} - {str(e)}")
        
        return results
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        self.log("🚀 FileWallBall API 다양한 파일 형식 테스트 시작")
        self.log(f"API URL: {self.api_base_url}")
        
        # 메모리 사용량 초기 상태
        initial_memory = self.get_memory_usage()
        self.log(f"초기 메모리 사용량: RSS={initial_memory['rss_mb']:.2f}MB, VMS={initial_memory['vms_mb']:.2f}MB")
        
        try:
            # 1. 테스트 파일 생성
            test_files = self.create_test_files()
            
            # 2. 개별 파일 테스트
            self.log("\n📁 개별 파일 테스트 시작")
            individual_results = []
            for file_path, mime_type in test_files.items():
                result = self.test_single_file(file_path, mime_type)
                individual_results.append(result)
                self.uploaded_files.append(result.get('file_id', None))
            
            # 3. 동시 업로드 테스트
            self.log("\n🔄 동시 업로드 테스트 시작")
            concurrent_results = self.test_concurrent_uploads(test_files)
            
            # 4. 결과 분석
            self.log("\n📊 테스트 결과 분석")
            self.analyze_results(individual_results, concurrent_results, initial_memory)
            
            # 5. 정리
            self.cleanup_test_files(test_files.keys())
            
        except Exception as e:
            self.log(f"테스트 실행 중 오류 발생: {str(e)}")
            raise
        finally:
            # 최종 메모리 사용량 확인
            final_memory = self.get_memory_usage()
            self.log(f"최종 메모리 사용량: RSS={final_memory['rss_mb']:.2f}MB, VMS={final_memory['vms_mb']:.2f}MB")
            self.log(f"메모리 변화: RSS={final_memory['rss_mb'] - initial_memory['rss_mb']:.2f}MB, VMS={final_memory['vms_mb'] - initial_memory['vms_mb']:.2f}MB")
    
    def analyze_results(self, individual_results: List[Dict], concurrent_results: List[Dict], initial_memory: Dict):
        """테스트 결과 분석"""
        total_tests = len(individual_results)
        successful_tests = len([r for r in individual_results if r['status'] == 'success'])
        failed_tests = total_tests - successful_tests
        
        self.log(f"\n📈 테스트 결과 요약:")
        self.log(f"  총 테스트: {total_tests}개")
        self.log(f"  성공: {successful_tests}개")
        self.log(f"  실패: {failed_tests}개")
        self.log(f"  성공률: {(successful_tests/total_tests)*100:.1f}%")
        
        # 파일 형식별 성능 분석
        self.log(f"\n⚡ 성능 분석:")
        for result in individual_results:
            if result['status'] == 'success':
                self.log(f"  {result['file']}:")
                self.log(f"    업로드 시간: {result['upload_time']:.2f}s")
                self.log(f"    다운로드 시간: {result['download_time']:.2f}s")
                self.log(f"    파일 크기: {result['file_size']} bytes")
        
        # 동시 업로드 결과
        self.log(f"\n🔄 동시 업로드 결과:")
        self.log(f"  동시 업로드 성공: {len(concurrent_results)}개")
        
        # 메모리 사용량 분석
        final_memory = self.get_memory_usage()
        memory_increase = final_memory['rss_mb'] - initial_memory['rss_mb']
        self.log(f"\n💾 메모리 사용량 분석:")
        self.log(f"  초기 RSS: {initial_memory['rss_mb']:.2f}MB")
        self.log(f"  최종 RSS: {final_memory['rss_mb']:.2f}MB")
        self.log(f"  증가량: {memory_increase:.2f}MB")
        
        if memory_increase > 100:  # 100MB 이상 증가 시 경고
            self.log(f"  ⚠️  메모리 사용량이 크게 증가했습니다!")
        
        # 결과를 JSON 파일로 저장
        results_summary = {
            'test_summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': (successful_tests/total_tests)*100
            },
            'individual_results': individual_results,
            'concurrent_results': concurrent_results,
            'memory_analysis': {
                'initial': initial_memory,
                'final': final_memory,
                'increase': memory_increase
            },
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open('file_format_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results_summary, f, indent=2, ensure_ascii=False)
        
        self.log(f"\n💾 결과가 'file_format_test_results.json' 파일에 저장되었습니다.")
    
    def cleanup_test_files(self, test_files: List[str]):
        """테스트 파일 정리"""
        self.log("\n🧹 테스트 파일 정리 중...")
        for file_path in test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.log(f"  삭제됨: {file_path}")
        
        # 업로드된 파일들도 정리
        for file_id in self.uploaded_files:
            if file_id:
                try:
                    response = requests.delete(f"{self.api_base_url}/files/{file_id}")
                    if response.status_code == 200:
                        self.log(f"  API에서 삭제됨: {file_id}")
                except Exception as e:
                    self.log(f"  API 삭제 실패: {file_id} - {str(e)}")
        
        self.log("정리 완료!")

def main():
    """메인 함수"""
    tester = FileFormatTester()
    
    try:
        tester.run_all_tests()
        print("\n🎉 모든 테스트가 완료되었습니다!")
        
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류가 발생했습니다: {str(e)}")
        raise
    finally:
        # 정리 작업
        test_files = [
            "test_text_1kb.txt",
            "test_image_100kb.png", 
            "test_binary_1mb.zip",
            "test_large_10mb.bin"
        ]
        tester.cleanup_test_files(test_files)

if __name__ == "__main__":
    main()
