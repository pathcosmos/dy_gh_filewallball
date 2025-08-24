#!/usr/bin/env python3
"""
FileWallBall API - 에러 처리 및 예외 상황 테스트 스크립트

이 스크립트는 다양한 에러 상황을 시뮬레이션하여 API의 안정성과
적절한 에러 응답을 검증합니다.
"""

import os
import time
import requests
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

class ErrorHandlingTester:
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base_url = api_base_url
        self.test_results = {}
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "INFO"):
        """로그 메시지 출력"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def test_health_check(self) -> bool:
        """API 헬스체크 테스트"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                self.log("✅ API 헬스체크 성공")
                return True
            else:
                self.log(f"❌ API 헬스체크 실패: {response.status_code}", "ERROR")
                return False
        except requests.exceptions.RequestException as e:
            self.log(f"❌ API 헬스체크 연결 실패: {e}", "ERROR")
            return False
    
    def test_invalid_file_id_404(self) -> Dict:
        """존재하지 않는 파일 ID로 404 에러 테스트"""
        self.log("\n--- 존재하지 않는 파일 ID 404 에러 테스트 ---")
        
        invalid_file_id = "non-existent-file-id-12345"
        test_cases = [
            ("GET", f"/files/{invalid_file_id}", "파일 정보 조회"),
            ("GET", f"/download/{invalid_file_id}", "파일 다운로드"),
            ("GET", f"/view/{invalid_file_id}", "파일 뷰"),
            ("GET", f"/preview/{invalid_file_id}", "이미지 프리뷰"),
            ("GET", f"/thumbnail/{invalid_file_id}", "이미지 썸네일"),
            ("DELETE", f"/files/{invalid_file_id}", "파일 삭제")
        ]
        
        results = []
        for method, endpoint, description in test_cases:
            try:
                if method == "GET":
                    response = requests.get(f"{self.api_base_url}{endpoint}", timeout=5)
                elif method == "DELETE":
                    response = requests.delete(f"{self.api_base_url}{endpoint}", timeout=5)
                
                if response.status_code == 404:
                    self.log(f"✅ {description}: 404 에러 정상 반환")
                    results.append({
                        "endpoint": endpoint,
                        "method": method,
                        "status": "PASS",
                        "status_code": response.status_code,
                        "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:100]
                    })
                else:
                    self.log(f"❌ {description}: 예상 404가 아닌 {response.status_code} 반환", "ERROR")
                    results.append({
                        "endpoint": endpoint,
                        "method": method,
                        "status": "FAIL",
                        "status_code": response.status_code,
                        "expected": 404,
                        "response": response.text[:100]
                    })
                    
            except requests.exceptions.RequestException as e:
                self.log(f"❌ {description}: 요청 실패 - {e}", "ERROR")
                results.append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return {
            "test_name": "존재하지 않는 파일 ID 404 에러 테스트",
            "results": results,
            "passed": all(r["status"] == "PASS" for r in results if r["status"] != "ERROR")
        }
    
    def test_file_size_limit_413(self) -> Dict:
        """파일 크기 제한 초과 413 에러 테스트"""
        self.log("\n--- 파일 크기 제한 초과 413 에러 테스트 ---")
        
        # 큰 파일 생성 (예: 100MB)
        large_file_size = 100 * 1024 * 1024  # 100MB
        large_file_path = Path("test_large_file.bin")
        
        try:
            # 큰 파일 생성
            self.log(f"테스트용 큰 파일 생성 중... ({large_file_size / (1024*1024):.1f}MB)")
            with open(large_file_path, 'wb') as f:
                f.write(os.urandom(large_file_size))
            
            # 파일 업로드 시도
            self.log("큰 파일 업로드 시도...")
            with open(large_file_path, 'rb') as f:
                files = {'file': (large_file_path.name, f, 'application/octet-stream')}
                response = requests.post(f"{self.api_base_url}/upload", files=files, timeout=30)
            
            if response.status_code == 413:
                self.log("✅ 파일 크기 제한 초과 413 에러 정상 반환")
                result = {
                    "status": "PASS",
                    "status_code": response.status_code,
                    "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:100]
                }
            else:
                self.log(f"❌ 예상 413이 아닌 {response.status_code} 반환", "ERROR")
                result = {
                    "status": "FAIL",
                    "status_code": response.status_code,
                    "expected": 413,
                    "response": response.text[:100]
                }
                
        except requests.exceptions.RequestException as e:
            self.log(f"❌ 큰 파일 업로드 요청 실패 - {e}", "ERROR")
            result = {
                "status": "ERROR",
                "error": str(e)
            }
        finally:
            # 테스트 파일 정리
            if large_file_path.exists():
                large_file_path.unlink()
                self.log("테스트용 큰 파일 정리 완료")
        
        return {
            "test_name": "파일 크기 제한 초과 413 에러 테스트",
            "result": result,
            "passed": result.get("status") == "PASS"
        }
    
    def test_invalid_mime_type_400(self) -> Dict:
        """잘못된 MIME 타입 400 에러 테스트"""
        self.log("\n--- 잘못된 MIME 타입 400 에러 테스트 ---")
        
        # 잘못된 MIME 타입으로 파일 생성
        test_file_path = Path("test_invalid_mime.txt")
        test_file_path.write_text("This is a test file with invalid MIME type")
        
        try:
            # 잘못된 MIME 타입으로 업로드 시도
            with open(test_file_path, 'rb') as f:
                files = {'file': (test_file_path.name, f, 'invalid/mime-type')}
                response = requests.post(f"{self.api_base_url}/upload", files=files, timeout=10)
            
            if response.status_code == 400:
                self.log("✅ 잘못된 MIME 타입 400 에러 정상 반환")
                result = {
                    "status": "PASS",
                    "status_code": response.status_code,
                    "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:100]
                }
            else:
                self.log(f"❌ 예상 400이 아닌 {response.status_code} 반환", "ERROR")
                result = {
                    "status": "FAIL",
                    "status_code": response.status_code,
                    "expected": 400,
                    "response": response.text[:100]
                }
                
        except requests.exceptions.RequestException as e:
            self.log(f"❌ 잘못된 MIME 타입 업로드 요청 실패 - {e}", "ERROR")
            result = {
                "status": "ERROR",
                "error": str(e)
            }
        finally:
            # 테스트 파일 정리
            if test_file_path.exists():
                test_file_path.unlink()
        
        return {
            "test_name": "잘못된 MIME 타입 400 에러 테스트",
            "result": result,
            "passed": result.get("status") == "PASS"
        }
    
    def test_malformed_requests(self) -> Dict:
        """잘못된 요청 형식 테스트"""
        self.log("\n--- 잘못된 요청 형식 테스트 ---")
        
        test_cases = [
            {
                "name": "빈 파일 업로드",
                "method": "POST",
                "endpoint": "/upload",
                "files": {},
                "expected_status": 422  # FastAPI validation error
            },
            {
                "name": "잘못된 JSON 형식",
                "method": "POST",
                "endpoint": "/upload",
                "headers": {"Content-Type": "application/json"},
                "data": '{"invalid": json}',
                "expected_status": 422
            }
        ]
        
        results = []
        for test_case in test_cases:
            try:
                if test_case["method"] == "POST":
                    response = requests.post(
                        f"{self.api_base_url}{test_case['endpoint']}", 
                        files=test_case.get("files", {}),
                        headers=test_case.get("headers", {}),
                        data=test_case.get("data"),
                        timeout=10
                    )
                
                if response.status_code == test_case["expected_status"]:
                    self.log(f"✅ {test_case['name']}: {test_case['expected_status']} 에러 정상 반환")
                    results.append({
                        "test_case": test_case["name"],
                        "status": "PASS",
                        "status_code": response.status_code,
                        "expected": test_case["expected_status"]
                    })
                else:
                    self.log(f"❌ {test_case['name']}: 예상 {test_case['expected_status']}가 아닌 {response.status_code} 반환", "ERROR")
                    results.append({
                        "test_case": test_case["name"],
                        "status": "FAIL",
                        "status_code": response.status_code,
                        "expected": test_case["expected_status"]
                    })
                    
            except requests.exceptions.RequestException as e:
                self.log(f"❌ {test_case['name']}: 요청 실패 - {e}", "ERROR")
                results.append({
                    "test_case": test_case["name"],
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return {
            "test_name": "잘못된 요청 형식 테스트",
            "results": results,
            "passed": all(r["status"] == "PASS" for r in results if r["status"] != "ERROR")
        }
    
    def test_rate_limiting(self) -> Dict:
        """속도 제한 테스트 (연속 요청)"""
        self.log("\n--- 속도 제한 테스트 (연속 요청) ---")
        
        # 작은 테스트 파일 생성
        test_file_path = Path("test_rate_limit.txt")
        test_file_path.write_text("Rate limit test file")
        
        try:
            # 연속으로 여러 번 업로드 시도
            upload_results = []
            for i in range(10):  # 10번 연속 시도
                try:
                    with open(test_file_path, 'rb') as f:
                        files = {'file': (f"rate_limit_test_{i}.txt", f, 'text/plain')}
                        response = requests.post(f"{self.api_base_url}/upload", files=files, timeout=10)
                    
                    upload_results.append({
                        "attempt": i + 1,
                        "status_code": response.status_code,
                        "success": response.status_code == 200
                    })
                    
                    if response.status_code == 429:  # Too Many Requests
                        self.log(f"✅ 속도 제한 429 에러 감지 (시도 {i+1})")
                        break
                        
                except requests.exceptions.RequestException as e:
                    upload_results.append({
                        "attempt": i + 1,
                        "error": str(e)
                    })
            
            # 결과 분석
            success_count = sum(1 for r in upload_results if r.get("success", False))
            rate_limited = any(r.get("status_code") == 429 for r in upload_results)
            
            self.log(f"연속 업로드 결과: {success_count}/10 성공, 속도 제한: {rate_limited}")
            
            result = {
                "status": "PASS" if rate_limited or success_count < 10 else "INFO",
                "success_count": success_count,
                "rate_limited": rate_limited,
                "details": upload_results
            }
            
        except Exception as e:
            self.log(f"❌ 속도 제한 테스트 실패 - {e}", "ERROR")
            result = {
                "status": "ERROR",
                "error": str(e)
            }
        finally:
            # 테스트 파일 정리
            if test_file_path.exists():
                test_file_path.unlink()
        
        return {
            "test_name": "속도 제한 테스트",
            "result": result,
            "passed": result.get("status") in ["PASS", "INFO"]
        }
    
    def test_concurrent_requests(self) -> Dict:
        """동시 요청 테스트"""
        self.log("\n--- 동시 요청 테스트 ---")
        
        import concurrent.futures
        import threading
        
        # 테스트 파일들 생성
        test_files = []
        for i in range(5):
            file_path = Path(f"concurrent_test_{i}.txt")
            file_path.write_text(f"Concurrent test file {i}")
            test_files.append(file_path)
        
        def upload_file(file_path: Path) -> Dict:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.name, f, 'text/plain')}
                    response = requests.post(f"{self.api_base_url}/upload", files=files, timeout=10)
                
                return {
                    "filename": file_path.name,
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response": response.json() if response.status_code == 200 else response.text[:100]
                }
            except Exception as e:
                return {
                    "filename": file_path.name,
                    "error": str(e)
                }
        
        try:
            # 동시 업로드 실행
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(upload_file, file_path) for file_path in test_files]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # 결과 분석
            success_count = sum(1 for r in results if r.get("success", False))
            error_count = sum(1 for r in results if "error" in r)
            
            self.log(f"동시 업로드 결과: {success_count}/5 성공, {error_count}/5 실패")
            
            for result_item in results:
                if result_item.get("success"):
                    self.log(f"✅ {result_item['filename']}: 업로드 성공")
                else:
                    self.log(f"❌ {result_item['filename']}: 업로드 실패 - {result_item.get('error', result_item.get('response', 'Unknown error'))}")
            
            result = {
                "status": "PASS" if success_count > 0 else "FAIL",
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }
            
        except Exception as e:
            self.log(f"❌ 동시 요청 테스트 실패 - {e}", "ERROR")
            result = {
                "status": "ERROR",
                "error": str(e)
            }
        finally:
            # 테스트 파일들 정리
            for file_path in test_files:
                if file_path.exists():
                    file_path.unlink()
        
        return {
            "test_name": "동시 요청 테스트",
            "result": result,
            "passed": result.get("status") == "PASS"
        }
    
    def run_all_tests(self):
        """모든 에러 처리 테스트를 실행합니다."""
        self.log("🚀 FileWallBall API 에러 처리 및 예외 상황 테스트 시작")
        
        # API 헬스체크
        if not self.test_health_check():
            self.log("❌ API가 실행 중이지 않습니다. 테스트를 중단합니다.", "ERROR")
            return
        
        # 각 테스트 실행
        tests = [
            self.test_invalid_file_id_404,
            self.test_file_size_limit_413,
            self.test_invalid_mime_type_400,
            self.test_malformed_requests,
            self.test_rate_limiting,
            self.test_concurrent_requests
        ]
        
        for test_func in tests:
            try:
                test_result = test_func()
                self.test_results[test_result["test_name"]] = test_result
            except Exception as e:
                self.log(f"❌ 테스트 실행 중 오류 발생: {test_func.__name__} - {e}", "ERROR")
                self.test_results[test_func.__name__] = {
                    "test_name": test_func.__name__,
                    "status": "ERROR",
                    "error": str(e)
                }
        
        # 결과 요약
        self.log("\n" + "="*60)
        self.log("🏁 에러 처리 테스트 완료 요약")
        self.log("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r.get("passed", False))
        failed_tests = total_tests - passed_tests
        
        self.log(f"총 테스트: {total_tests}")
        self.log(f"성공: {passed_tests}")
        self.log(f"실패: {failed_tests}")
        
        # 상세 결과
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result.get("passed", False) else "❌"
            self.log(f"{status_icon} {test_name}: {result.get('status', 'UNKNOWN')}")
        
        # 결과 저장
        with open("error_handling_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=4, ensure_ascii=False)
        self.log("\n테스트 결과가 error_handling_test_results.json에 저장되었습니다.")
        
        end_time = time.time()
        total_duration = end_time - self.start_time
        self.log(f"총 소요 시간: {total_duration:.2f}초")

if __name__ == "__main__":
    tester = ErrorHandlingTester()
    tester.run_all_tests()
