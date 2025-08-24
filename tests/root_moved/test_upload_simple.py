#!/usr/bin/env python3
"""
간단한 파일 업로드 API 테스트 스크립트
"""

import requests
import json
import os
from pathlib import Path

# API 기본 URL
BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Health check 테스트"""
    print("🔍 Health Check 테스트...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check 성공: {data}")
            return True
        else:
            print(f"❌ Health Check 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check 오류: {e}")
        return False

def test_file_upload():
    """파일 업로드 테스트"""
    print("\n📤 파일 업로드 테스트...")
    
    # 테스트 파일 생성
    test_file = "test_upload_simple.txt"
    test_content = "Hello, FileWallBall! This is a test file for upload API testing."
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    try:
        # 파일 업로드
        with open(test_file, "rb") as f:
            files = {"file": (test_file, f, "text/plain")}
            response = requests.post(f"{BASE_URL}/upload", files=files)
        
        print(f"📊 응답 상태: {response.status_code}")
        print(f"📋 응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 업로드 성공: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 업로드된 파일 정보 저장
            file_id = data.get("file_id")
            if file_id:
                print(f"📁 파일 ID: {file_id}")
                return file_id
        else:
            print(f"❌ 업로드 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 업로드 오류: {e}")
    
    finally:
        # 테스트 파일 정리
        if os.path.exists(test_file):
            os.remove(test_file)
    
    return None

def test_file_info(file_id):
    """파일 정보 조회 테스트"""
    if not file_id:
        print("❌ 파일 ID가 없어 정보 조회를 건너뜁니다.")
        return
    
    print(f"\n📋 파일 정보 조회 테스트 (ID: {file_id})...")
    
    try:
        response = requests.get(f"{BASE_URL}/files/{file_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 파일 정보 조회 성공: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 파일 정보 조회 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ 파일 정보 조회 오류: {e}")

def test_file_list():
    """파일 목록 조회 테스트"""
    print("\n📚 파일 목록 조회 테스트...")
    
    try:
        response = requests.get(f"{BASE_URL}/files?limit=5&offset=0")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 파일 목록 조회 성공: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 파일 목록 조회 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ 파일 목록 조회 오류: {e}")

def main():
    """메인 테스트 실행"""
    print("🚀 FileWallBall API 테스트 시작")
    print("=" * 50)
    
    # 1. Health Check
    if not test_health():
        print("❌ Health Check 실패로 테스트를 중단합니다.")
        return
    
    # 2. 파일 업로드
    file_id = test_file_upload()
    
    # 3. 파일 정보 조회
    test_file_info(file_id)
    
    # 4. 파일 목록 조회
    test_file_list()
    
    print("\n" + "=" * 50)
    print("🏁 테스트 완료")

if __name__ == "__main__":
    main()
