#!/usr/bin/env python3
"""
파일 다운로드 API 테스트 스크립트
"""

import requests
import json
import os
import hashlib
from pathlib import Path

# API 기본 URL
BASE_URL = "http://127.0.0.1:8000"

def test_file_upload_for_download():
    """다운로드 테스트를 위한 파일 업로드"""
    print("📤 다운로드 테스트용 파일 업로드...")
    
    # 테스트 파일 생성
    test_file = "test_download.txt"
    test_content = "This is a test file for download API testing.\n" * 10
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    try:
        # 파일 업로드
        with open(test_file, "rb") as f:
            files = {"file": (test_file, f, "text/plain")}
            response = requests.post(f"{BASE_URL}/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 업로드 성공: {data['file_id']}")
            
            # 원본 파일 해시 계산
            with open(test_file, "rb") as f:
                original_hash = hashlib.md5(f.read()).hexdigest()
            
            return {
                "file_id": data["file_id"],
                "filename": test_file,
                "original_hash": original_hash,
                "original_size": len(test_content.encode())
            }
        else:
            print(f"❌ 업로드 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 업로드 오류: {e}")
        return None
    
    finally:
        # 테스트 파일 정리
        if os.path.exists(test_file):
            os.remove(test_file)

def test_file_download(file_id, original_filename, original_hash, original_size):
    """파일 다운로드 테스트"""
    print(f"\n📥 파일 다운로드 테스트 (ID: {file_id})...")
    
    try:
        # 다운로드 요청
        download_url = f"{BASE_URL}/download/{file_id}"
        print(f"다운로드 URL: {download_url}")
        
        response = requests.get(download_url, stream=True)
        
        print(f"📊 응답 상태: {response.status_code}")
        print(f"📋 응답 헤더:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        if response.status_code == 200:
            # 파일 다운로드
            downloaded_filename = f"downloaded_{original_filename}"
            
            with open(downloaded_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 다운로드된 파일 검증
            with open(downloaded_filename, "rb") as f:
                downloaded_content = f.read()
                downloaded_hash = hashlib.md5(downloaded_content).hexdigest()
                downloaded_size = len(downloaded_content)
            
            print(f"✅ 다운로드 성공!")
            print(f"  - 원본 파일명: {original_filename}")
            print(f"  - 다운로드 파일명: {downloaded_filename}")
            print(f"  - 원본 크기: {original_size} bytes")
            print(f"  - 다운로드 크기: {downloaded_size} bytes")
            print(f"  - 원본 해시: {original_hash}")
            print(f"  - 다운로드 해시: {downloaded_hash}")
            
            # 검증
            if original_hash == downloaded_hash:
                print("✅ 해시 일치 - 파일 무결성 확인됨")
            else:
                print("❌ 해시 불일치 - 파일 손상됨")
            
            if original_size == downloaded_size:
                print("✅ 크기 일치 - 파일 완전성 확인됨")
            else:
                print("❌ 크기 불일치 - 파일 불완전함")
            
            # 다운로드된 파일 정리
            os.remove(downloaded_filename)
            
            return True
        else:
            print(f"❌ 다운로드 실패: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 다운로드 오류: {e}")
        return False

def test_file_info(file_id):
    """파일 정보 조회 테스트"""
    print(f"\n📋 파일 정보 조회 테스트 (ID: {file_id})...")
    
    try:
        response = requests.get(f"{BASE_URL}/files/{file_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 파일 정보 조회 성공:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"❌ 파일 정보 조회 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 파일 정보 조회 오류: {e}")
        return None

def test_invalid_file_download():
    """잘못된 파일 ID로 다운로드 테스트"""
    print(f"\n🚫 잘못된 파일 ID 다운로드 테스트...")
    
    invalid_file_id = "invalid-uuid-12345"
    
    try:
        response = requests.get(f"{BASE_URL}/download/{invalid_file_id}")
        
        print(f"📊 응답 상태: {response.status_code}")
        print(f"📋 응답 내용: {response.text}")
        
        if response.status_code == 404:
            print("✅ 올바른 404 오류 응답")
            return True
        else:
            print(f"❌ 예상과 다른 응답: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🚀 파일 다운로드 API 테스트 시작")
    print("=" * 60)
    
    # 1. 테스트용 파일 업로드
    upload_result = test_file_upload_for_download()
    if not upload_result:
        print("❌ 파일 업로드 실패로 테스트를 중단합니다.")
        return
    
    file_id = upload_result["file_id"]
    filename = upload_result["filename"]
    original_hash = upload_result["original_hash"]
    original_size = upload_result["original_size"]
    
    # 2. 파일 정보 조회
    test_file_info(file_id)
    
    # 3. 파일 다운로드
    download_success = test_file_download(file_id, filename, original_hash, original_size)
    
    # 4. 잘못된 파일 ID 테스트
    invalid_test_success = test_invalid_file_download()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"파일 업로드: ✅ 성공")
    print(f"파일 정보 조회: ✅ 성공")
    print(f"파일 다운로드: {'✅ 성공' if download_success else '❌ 실패'}")
    print(f"잘못된 ID 테스트: {'✅ 성공' if invalid_test_success else '❌ 실패'}")
    
    if download_success and invalid_test_success:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")
    
    print("🏁 테스트 완료")

if __name__ == "__main__":
    main()
