#!/usr/bin/env python3
"""
간단한 Keygen과 Upload 기능 테스트 스크립트
"""

import requests
import time
from datetime import datetime

# API 기본 URL
BASE_URL = "http://localhost:8000"
MASTER_KEY = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="

def wait_for_server(max_retries=10):
    """서버가 준비될 때까지 대기"""
    print("서버 시작 대기 중...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ 서버가 준비되었습니다!")
                return True
        except requests.exceptions.RequestException:
            pass
        print(f"   재시도 {i+1}/{max_retries}...")
        time.sleep(2)
    print("❌ 서버 연결 실패")
    return False

def test_keygen():
    """Keygen 엔드포인트 테스트"""
    print("\n=== Keygen 테스트 ===")
    
    url = f"{BASE_URL}/keygen"
    current_date = datetime.now().strftime("%Y%m%d")
    project_name = f"test_project_{int(time.time())}"
    
    data = {
        "project_name": project_name,
        "request_date": current_date,
        "master_key": MASTER_KEY
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            project_key = result.get('project_key')
            print(f"✅ 프로젝트 키 생성 성공: {project_key[:20]}...")
            return project_key
        else:
            print(f"❌ 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

def test_upload(project_key):
    """파일 업로드 테스트"""
    print(f"\n=== 파일 업로드 테스트 ===")
    
    if not project_key:
        print("❌ 프로젝트 키가 없습니다.")
        return None
    
    url = f"{BASE_URL}/api/v1/files/upload"
    
    # 테스트 파일 생성
    test_content = f"Test file content - {datetime.now().isoformat()}"
    test_filename = f"test_upload_{int(time.time())}.txt"
    
    files = {
        'file': (test_filename, test_content, 'text/plain')
    }
    
    headers = {
        'Authorization': f'Bearer {project_key}'
    }
    
    try:
        response = requests.post(url, files=files, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            file_id = result.get('file_id')
            print(f"✅ 파일 업로드 성공: {file_id}")
            return file_id
        else:
            print(f"❌ 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

def test_download(file_id, project_key):
    """파일 다운로드 테스트"""
    print(f"\n=== 파일 다운로드 테스트 ===")
    
    if not file_id:
        print("❌ 파일 ID가 없습니다.")
        return False
    
    url = f"{BASE_URL}/api/v1/files/{file_id}/download"
    
    headers = {
        'Authorization': f'Bearer {project_key}'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ 파일 다운로드 성공: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 Keygen과 Upload 기능 연동 테스트 시작")
    print("=" * 50)
    
    # 1. 서버 대기
    if not wait_for_server():
        return
    
    # 2. Keygen 테스트
    project_key = test_keygen()
    if not project_key:
        print("❌ Keygen 테스트 실패")
        return
    
    # 3. Upload 테스트
    file_id = test_upload(project_key)
    if not file_id:
        print("❌ Upload 테스트 실패")
        return
    
    # 4. Download 테스트
    success = test_download(file_id, project_key)
    if not success:
        print("❌ Download 테스트 실패")
        return
    
    print("\n" + "=" * 50)
    print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
    print(f"📅 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 