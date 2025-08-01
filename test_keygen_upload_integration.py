#!/usr/bin/env python3
"""
Keygen과 Upload 기능 연동 종합 테스트 스크립트
"""

import requests
import time
from datetime import datetime
import os


# API 기본 URL
BASE_URL = "http://localhost:8000"
MASTER_KEY = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="


def test_health_check():
    """헬스체크 테스트"""
    print("=== 헬스체크 테스트 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Status: {result.get('status')}")
            print(f"Service: {result.get('service')}")
            print(f"Version: {result.get('version')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False


def test_keygen_endpoint():
    """Keygen 엔드포인트 테스트"""
    print("\n=== Keygen 엔드포인트 테스트 ===")
    
    url = f"{BASE_URL}/keygen"
    
    # 현재 날짜를 YYYYMMDD 형식으로 변환
    current_date = datetime.now().strftime("%Y%m%d")
    project_name = f"test_project_{current_date}_{int(time.time())}"
    
    data = {
        "project_name": project_name,
        "request_date": current_date,
        "master_key": MASTER_KEY
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Project Key: {result.get('project_key')}")
            print(f"Project Name: {result.get('project_name')}")
            print(f"Request Date: {result.get('request_date')}")
            print(f"Request IP: {result.get('request_ip')}")
            print(f"Message: {result.get('message')}")
            return result.get('project_key')
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None


def test_project_api_endpoint():
    """프로젝트 API 엔드포인트 테스트"""
    print("\n=== 프로젝트 API 엔드포인트 테스트 ===")
    
    url = f"{BASE_URL}/api/v1/projects/"
    
    data = {
        "project_name": f"test_project_api_{int(time.time())}",
        "master_key": MASTER_KEY
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Project Key: {result.get('project_key')}")
            print(f"Project ID: {result.get('project_id')}")
            print(f"JWT Token: {result.get('jwt_token', 'None')}")
            print(f"Message: {result.get('message')}")
            return result.get('project_key')
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None


def test_file_upload_with_key(project_key, test_type="text"):
    """프로젝트 키를 사용한 파일 업로드 테스트"""
    print(f"\n=== 파일 업로드 테스트 ({test_type}) ===")
    
    if not project_key:
        print("프로젝트 키가 없습니다.")
        return None
    
    url = f"{BASE_URL}/api/v1/files/upload"
    
    # 테스트 파일 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if test_type == "text":
        test_content = f"Test file content - {datetime.now().isoformat()}\nThis is a test file for upload functionality."
        test_filename = f"test_upload_{timestamp}.txt"
        content_type = "text/plain"
    elif test_type == "json":
        test_content = json.dumps({
            "test_data": "upload_test",
            "timestamp": datetime.now().isoformat(),
            "project_key": project_key[:10] + "...",
            "file_type": "json"
        }, indent=2)
        test_filename = f"test_data_{timestamp}.json"
        content_type = "application/json"
    else:
        test_content = f"Binary test content - {timestamp}"
        test_filename = f"test_binary_{timestamp}.bin"
        content_type = "application/octet-stream"
    
    files = {
        'file': (test_filename, test_content, content_type)
    }
    
    headers = {
        'Authorization': f'Bearer {project_key}'
    }
    
    try:
        response = requests.post(url, files=files, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"File ID: {result.get('file_id')}")
            print(f"Download URL: {result.get('download_url')}")
            print(f"Original Filename: {result.get('original_filename')}")
            print(f"File Size: {result.get('file_size')}")
            print(f"MIME Type: {result.get('mime_type')}")
            print(f"Message: {result.get('message')}")
            return result.get('file_id')
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None


def test_file_download(file_id, project_key):
    """파일 다운로드 테스트"""
    print(f"\n=== 파일 다운로드 테스트 ===")
    
    if not file_id:
        print("파일 ID가 없습니다.")
        return False
    
    url = f"{BASE_URL}/api/v1/files/{file_id}/download"
    
    headers = {
        'Authorization': f'Bearer {project_key}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Content Length: {len(response.content)}")
            print(f"Content Type: {response.headers.get('content-type')}")
            print(f"Content Disposition: {response.headers.get('content-disposition')}")
            print(f"Content Preview: {response.text[:100]}...")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False


def test_file_info(file_id, project_key):
    """파일 정보 조회 테스트"""
    print(f"\n=== 파일 정보 조회 테스트 ===")
    
    if not file_id:
        print("파일 ID가 없습니다.")
        return False
    
    url = f"{BASE_URL}/api/v1/files/{file_id}"
    
    headers = {
        'Authorization': f'Bearer {project_key}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"File UUID: {result.get('file_uuid')}")
            print(f"Original Filename: {result.get('original_filename')}")
            print(f"Stored Filename: {result.get('stored_filename')}")
            print(f"File Size: {result.get('file_size')}")
            print(f"MIME Type: {result.get('mime_type')}")
            print(f"File Hash: {result.get('file_hash')}")
            print(f"Storage Path: {result.get('storage_path')}")
            print(f"Is Public: {result.get('is_public')}")
            print(f"Created At: {result.get('created_at')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False


def test_multiple_uploads(project_key, count=3):
    """다중 파일 업로드 테스트"""
    print(f"\n=== 다중 파일 업로드 테스트 ({count}개) ===")
    
    if not project_key:
        print("프로젝트 키가 없습니다.")
        return []
    
    uploaded_files = []
    
    for i in range(count):
        print(f"\n--- 파일 {i+1}/{count} 업로드 ---")
        file_id = test_file_upload_with_key(project_key, f"text_{i+1}")
        if file_id:
            uploaded_files.append(file_id)
        time.sleep(1)  # 요청 간 간격
    
    print(f"\n총 {len(uploaded_files)}개 파일 업로드 완료")
    return uploaded_files


def test_error_cases(project_key):
    """에러 케이스 테스트"""
    print(f"\n=== 에러 케이스 테스트 ===")
    
    # 1. 잘못된 프로젝트 키로 업로드 시도
    print("\n--- 잘못된 프로젝트 키 테스트 ---")
    url = f"{BASE_URL}/api/v1/files/upload"
    files = {'file': ('test.txt', 'test content', 'text/plain')}
    headers = {'Authorization': 'Bearer invalid_key'}
    
    try:
        response = requests.post(url, files=files, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Expected: 401 or 403, Got: {response.status_code}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # 2. 파일 없이 업로드 시도
    print("\n--- 파일 없이 업로드 테스트 ---")
    headers = {'Authorization': f'Bearer {project_key}'}
    
    try:
        response = requests.post(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Expected: 422, Got: {response.status_code}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # 3. 존재하지 않는 파일 다운로드 시도
    print("\n--- 존재하지 않는 파일 다운로드 테스트 ---")
    fake_file_id = "00000000-0000-0000-0000-000000000000"
    download_url = f"{BASE_URL}/api/v1/files/{fake_file_id}/download"
    
    try:
        response = requests.get(download_url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Expected: 404, Got: {response.status_code}")
    except Exception as e:
        print(f"Exception: {e}")


def main():
    """메인 테스트 함수"""
    print("Keygen과 Upload 기능 연동 종합 테스트 시작")
    print("=" * 60)
    
    # 1. 헬스체크
    if not test_health_check():
        print("헬스체크 실패. 서버가 실행 중인지 확인하세요.")
        return
    
    # 2. Keygen 엔드포인트 테스트
    project_key_1 = test_keygen_endpoint()
    
    # 3. 프로젝트 API 엔드포인트 테스트
    project_key_2 = test_project_api_endpoint()
    
    # 4. 첫 번째 프로젝트 키로 파일 업로드 테스트
    if project_key_1:
        print(f"\n{'='*60}")
        print("첫 번째 프로젝트 키로 테스트 진행")
        
        # 텍스트 파일 업로드
        file_id_1 = test_file_upload_with_key(project_key_1, "text")
        
        if file_id_1:
            # 파일 정보 조회
            test_file_info(file_id_1, project_key_1)
            
            # 파일 다운로드
            test_file_download(file_id_1, project_key_1)
        
        # JSON 파일 업로드
        file_id_2 = test_file_upload_with_key(project_key_1, "json")
        
        if file_id_2:
            test_file_info(file_id_2, project_key_1)
            test_file_download(file_id_2, project_key_1)
    
    # 5. 두 번째 프로젝트 키로 다중 파일 업로드 테스트
    if project_key_2:
        print(f"\n{'='*60}")
        print("두 번째 프로젝트 키로 다중 파일 테스트 진행")
        
        uploaded_files = test_multiple_uploads(project_key_2, 3)
        
        # 업로드된 파일들 정보 조회
        for i, file_id in enumerate(uploaded_files):
            print(f"\n--- 업로드된 파일 {i+1} 정보 ---")
            test_file_info(file_id, project_key_2)
    
    # 6. 에러 케이스 테스트
    if project_key_1:
        test_error_cases(project_key_1)
    
    print(f"\n{'='*60}")
    print("Keygen과 Upload 기능 연동 종합 테스트 완료")
    print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    import json  # JSON 테스트를 위해 import
    main() 