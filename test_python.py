#!/usr/bin/env python3
"""
FileWallBall API 테스트 스크립트 (Python)
"""

import requests
import time
import os
from datetime import datetime

# 설정
API_BASE_URL = "http://filewallball:8000"  # Docker 네트워크 내에서의 접근
MASTER_KEY = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
PROJECT_NAME = f"test-project-{int(time.time())}"
REQUEST_DATE = datetime.now().strftime("%Y%m%d")

def log_info(message):
    print(f"[INFO] {message}")


def log_success(message):
    print(f"[SUCCESS] {message}")


def log_error(message):
    print(f"[ERROR] {message}")


def log_warning(message):
    print(f"[WARNING] {message}")

def test_health_check():
    """1. 헬스체크 테스트"""
    log_info("1. 헬스체크 확인 중...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_success(f"API 서버 정상: {data}")
            return True
        else:
            log_error(f"헬스체크 실패: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"헬스체크 오류: {e}")
        return False

def test_project_key_generation():
    """2. 프로젝트 키 생성 테스트"""
    log_info("2. 프로젝트 키 생성 중...")
    try:
        data = {
            "project_name": PROJECT_NAME,
            "request_date": REQUEST_DATE,
            "master_key": MASTER_KEY
        }
        
        response = requests.post(f"{API_BASE_URL}/keygen", data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            log_success(f"프로젝트 키 생성 성공: {result}")
            return result.get("project_key")
        else:
            log_error(f"프로젝트 키 생성 실패: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_error(f"프로젝트 키 생성 오류: {e}")
        return None

def test_file_upload(project_key):
    """3. 파일 업로드 테스트"""
    log_info("3. 파일 업로드 중...")
    try:
        # 테스트 파일 생성
        test_content = f"Hello FileWallBall!\n생성 시간: {datetime.now()}\n프로젝트: {PROJECT_NAME}"
        with open("test.txt", "w") as f:
            f.write(test_content)
        
        log_info(f"테스트 파일 생성: {test_content}")
        
        # 파일 업로드
        files = {"file": ("test.txt", open("test.txt", "rb"), "text/plain")}
        data = {"project_key": project_key}
        
        response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            log_success(f"파일 업로드 성공: {result}")
            return result
        else:
            log_error(f"파일 업로드 실패: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_error(f"파일 업로드 오류: {e}")
        return None

def test_file_download(upload_result):
    """4. 파일 다운로드 테스트"""
    log_info("4. 파일 다운로드 중...")
    try:
        file_id = upload_result.get("file_id")
        download_url = upload_result.get("download_url")
        
        if not file_id or not download_url:
            log_error("업로드 결과에서 파일 ID 또는 다운로드 URL을 찾을 수 없습니다.")
            return False
        
        log_info(f"다운로드 URL: {download_url}")
        
        # 파일 다운로드
        response = requests.get(download_url, timeout=30)
        if response.status_code == 200:
            with open("downloaded.txt", "wb") as f:
                f.write(response.content)
            
            log_success("파일 다운로드 성공")
            log_info(f"다운로드된 파일 내용: {response.text}")
            return True
        else:
            log_error(f"파일 다운로드 실패: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"파일 다운로드 오류: {e}")
        return False

def test_file_comparison():
    """5. 파일 비교 테스트"""
    log_info("5. 파일 비교 중...")
    try:
        if not os.path.exists("test.txt") or not os.path.exists("downloaded.txt"):
            log_error("비교할 파일이 없습니다.")
            return False
        
        with open("test.txt", "r") as f1, open("downloaded.txt", "r") as f2:
            content1 = f1.read()
            content2 = f2.read()
        
        if content1 == content2:
            log_success("✅ 업로드된 파일과 다운로드된 파일이 동일합니다!")
            return True
        else:
            log_error("❌ 업로드된 파일과 다운로드된 파일이 다릅니다!")
            log_info(f"원본 파일 크기: {len(content1)} bytes")
            log_info(f"다운로드 파일 크기: {len(content2)} bytes")
            return False
    except Exception as e:
        log_error(f"파일 비교 오류: {e}")
        return False

def test_file_info(upload_result):
    """6. 파일 정보 조회 테스트"""
    log_info("6. 파일 정보 조회 중...")
    try:
        file_id = upload_result.get("file_id")
        if not file_id:
            log_error("업로드 결과에서 파일 ID를 찾을 수 없습니다.")
            return False
        
        response = requests.get(f"{API_BASE_URL}/files/{file_id}", timeout=10)
        if response.status_code == 200:
            result = response.json()
            log_success(f"파일 정보 조회 성공: {result}")
            return True
        else:
            log_warning(f"파일 정보 조회 실패 (인증 필요할 수 있음): {response.status_code}")
            return False
    except Exception as e:
        log_warning(f"파일 정보 조회 오류: {e}")
        return False

def test_metrics():
    """7. 시스템 메트릭 테스트"""
    log_info("7. 시스템 메트릭 확인 중...")
    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=10)
        if response.status_code == 200:
            log_success("시스템 메트릭 조회 성공")
            log_info(f"메트릭 내용 (처음 500자): {response.text[:500]}...")
            return True
        else:
            log_warning(f"시스템 메트릭 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        log_warning(f"시스템 메트릭 조회 오류: {e}")
        return False

def cleanup():
    """정리"""
    log_info("8. 테스트 정리 중...")
    try:
        for file in ["test.txt", "downloaded.txt"]:
            if os.path.exists(file):
                os.remove(file)
        log_success("테스트 파일 정리 완료")
    except Exception as e:
        log_warning(f"정리 중 오류: {e}")

def main():
    """메인 테스트 함수"""
    print("=== FileWallBall Python 테스트 ===")
    print(f"API URL: {API_BASE_URL}")
    print(f"프로젝트명: {PROJECT_NAME}")
    print(f"요청 날짜: {REQUEST_DATE}")
    print()
    
    # 테스트 실행
    tests = []
    
    # 1. 헬스체크
    tests.append(("헬스체크", test_health_check()))
    
    # 2. 프로젝트 키 생성
    project_key = test_project_key_generation()
    tests.append(("프로젝트 키 생성", project_key is not None))
    
    if project_key:
        # 3. 파일 업로드
        upload_result = test_file_upload(project_key)
        tests.append(("파일 업로드", upload_result is not None))
        
        if upload_result:
            # 4. 파일 다운로드
            tests.append(("파일 다운로드", test_file_download(upload_result)))
            
            # 5. 파일 비교
            tests.append(("파일 비교", test_file_comparison()))
            
            # 6. 파일 정보 조회
            tests.append(("파일 정보 조회", test_file_info(upload_result)))
    else:
        tests.extend([
            ("파일 업로드", False),
            ("파일 다운로드", False),
            ("파일 비교", False),
            ("파일 정보 조회", False)
        ])
    
    # 7. 시스템 메트릭
    tests.append(("시스템 메트릭", test_metrics()))
    
    # 정리
    cleanup()
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n전체: {passed}/{total} 테스트 통과")
    
    if passed == total:
        log_success("모든 테스트가 성공적으로 완료되었습니다!")
        return 0
    else:
        log_error(f"{total - passed}개 테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    exit(main()) 