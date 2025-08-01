#!/usr/bin/env python3
"""
간단한 Keygen과 Upload 기능 테스트 스크립트 (데이터베이스 없이)
"""

import requests
import time
from datetime import datetime

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
        print(f"❌ 헬스체크 실패: {e}")
        return False

def test_simple_keygen():
    """간단한 Keygen 테스트 (데이터베이스 없이)"""
    print("\n=== 간단한 Keygen 테스트 ===")
    
    # 현재 날짜
    current_date = datetime.now().strftime("%Y%m%d")
    project_name = f"test_project_{int(time.time())}"
    
    url = f"{BASE_URL}/keygen"
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
            print(f"✅ 성공!")
            print(f"Project Key: {result.get('project_key', 'N/A')}")
            print(f"Project ID: {result.get('project_id', 'N/A')}")
            return result.get('project_key')
        else:
            print(f"❌ 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return None

def test_simple_upload(project_key):
    """간단한 Upload 테스트"""
    print(f"\n=== 간단한 Upload 테스트 ===")
    
    if not project_key:
        print("❌ 프로젝트 키가 없어서 업로드 테스트를 건너뜁니다.")
        return False
    
    # 간단한 테스트 파일 생성
    test_content = f"Test file content - {datetime.now().isoformat()}"
    
    url = f"{BASE_URL}/api/v1/files/upload"
    files = {
        'file': ('test_file.txt', test_content, 'text/plain')
    }
    headers = {
        'Authorization': f'Bearer {project_key}'
    }
    
    try:
        response = requests.post(url, files=files, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 업로드 성공!")
            print(f"File ID: {result.get('file_id', 'N/A')}")
            print(f"Filename: {result.get('filename', 'N/A')}")
            print(f"Download URL: {result.get('download_url', 'N/A')}")
            return result.get('file_id')
        else:
            print(f"❌ 업로드 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 업로드 예외 발생: {e}")
        return None

def test_file_download(file_id, project_key):
    """파일 다운로드 테스트"""
    print(f"\n=== 파일 다운로드 테스트 ===")
    
    if not file_id or not project_key:
        print("❌ 파일 ID 또는 프로젝트 키가 없어서 다운로드 테스트를 건너뜁니다.")
        return False
    
    url = f"{BASE_URL}/api/v1/files/{file_id}/download"
    headers = {
        'Authorization': f'Bearer {project_key}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ 다운로드 성공!")
            print(f"Content Length: {len(response.content)} bytes")
            print(f"Content: {response.text[:100]}...")
            return True
        else:
            print(f"❌ 다운로드 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 다운로드 예외 발생: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 간단한 Keygen과 Upload 기능 연동 테스트 시작")
    print("=" * 50)
    
    # 1. 헬스체크
    if not test_health_check():
        print("❌ 헬스체크 실패로 테스트를 중단합니다.")
        return
    
    # 2. Keygen 테스트
    project_key = test_simple_keygen()
    
    # 3. Upload 테스트
    file_id = test_simple_upload(project_key)
    
    # 4. Download 테스트
    if file_id:
        test_file_download(file_id, project_key)
    
    print("\n" + "=" * 50)
    print("🏁 테스트 완료!")

if __name__ == "__main__":
    main() 