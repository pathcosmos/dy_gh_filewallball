#!/usr/bin/env python3
"""
업로드 기능 수정 사항 테스트 스크립트
"""

import requests
import json
import os
from datetime import datetime

# API 기본 URL
BASE_URL = "http://localhost:8000"

def test_project_key_creation():
    """프로젝트 키 생성 테스트"""
    print("=== 프로젝트 키 생성 테스트 ===")
    
    url = f"{BASE_URL}/api/v1/projects/"
    data = {
        "project_name": "test_project_upload",
        "master_key": "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Project Key: {result.get('project_key')}")
            print(f"Project ID: {result.get('project_id')}")
            return result.get('project_key')
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def test_file_upload(project_key):
    """파일 업로드 테스트"""
    print("\n=== 파일 업로드 테스트 ===")
    
    if not project_key:
        print("프로젝트 키가 없습니다.")
        return None
    
    url = f"{BASE_URL}/api/v1/files/upload"
    
    # 테스트 파일 생성
    test_content = f"Test file content - {datetime.now().isoformat()}"
    test_filename = f"test_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    files = {
        'file': (test_filename, test_content, 'text/plain')
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
            print(f"File Size: {result.get('file_size')}")
            return result.get('file_id')
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def test_file_download(file_id, project_key):
    """파일 다운로드 테스트"""
    print("\n=== 파일 다운로드 테스트 ===")
    
    if not file_id:
        print("파일 ID가 없습니다.")
        return
    
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
            print(f"Content: {response.text[:100]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

def test_file_info(file_id, project_key):
    """파일 정보 조회 테스트"""
    print("\n=== 파일 정보 조회 테스트 ===")
    
    if not file_id:
        print("파일 ID가 없습니다.")
        return
    
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
            print(f"File Size: {result.get('file_size')}")
            print(f"MIME Type: {result.get('mime_type')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

def main():
    """메인 테스트 함수"""
    print("업로드 기능 수정 사항 테스트 시작")
    print("=" * 50)
    
    # 1. 프로젝트 키 생성
    project_key = test_project_key_creation()
    
    if not project_key:
        print("프로젝트 키 생성 실패. 테스트를 중단합니다.")
        return
    
    # 2. 파일 업로드
    file_id = test_file_upload(project_key)
    
    if not file_id:
        print("파일 업로드 실패. 테스트를 중단합니다.")
        return
    
    # 3. 파일 정보 조회
    test_file_info(file_id, project_key)
    
    # 4. 파일 다운로드
    test_file_download(file_id, project_key)
    
    print("\n" + "=" * 50)
    print("업로드 기능 수정 사항 테스트 완료")

if __name__ == "__main__":
    main() 