#!/usr/bin/env python3
"""
최소한의 파일 업로드 테스트
"""

import requests
import json
import os
from pathlib import Path

# API 기본 URL
BASE_URL = "http://127.0.0.1:8000"

def test_upload_without_db():
    """데이터베이스 없이 파일 저장만 테스트"""
    print("🔍 파일 저장 테스트 (데이터베이스 제외)...")
    
    # 테스트 파일 생성
    test_file = "test_minimal.txt"
    test_content = "Minimal test content"
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    try:
        # 파일 업로드
        with open(test_file, "rb") as f:
            files = {"file": (test_file, f, "text/plain")}
            response = requests.post(f"{BASE_URL}/upload", files=files)
        
        print(f"📊 응답 상태: {response.status_code}")
        print(f"📋 응답 내용: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 업로드 성공: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data.get("file_id")
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

def test_upload_directory_access():
    """업로드 디렉토리 접근 테스트"""
    print("\n📁 업로드 디렉토리 접근 테스트...")
    
    try:
        from app.config import get_settings
        
        settings = get_settings()
        upload_dir = Path(settings.effective_upload_dir)
        
        print(f"설정된 업로드 디렉토리: {upload_dir}")
        print(f"절대 경로: {upload_dir.absolute()}")
        print(f"존재 여부: {upload_dir.exists()}")
        
        if upload_dir.exists():
            print(f"권한: {oct(upload_dir.stat().st_mode)[-3:]}")
            print(f"소유자: {upload_dir.owner()}")
            
            # 쓰기 테스트
            test_file = upload_dir / "test_write_access.txt"
            try:
                test_file.write_text("Test write access")
                print("✅ 쓰기 권한 확인됨")
                test_file.unlink()  # 테스트 파일 삭제
            except Exception as e:
                print(f"❌ 쓰기 권한 없음: {e}")
        
    except Exception as e:
        print(f"❌ 디렉토리 테스트 실패: {e}")

def main():
    """메인 테스트 실행"""
    print("🚀 최소 파일 업로드 테스트 시작")
    print("=" * 50)
    
    # 1. 업로드 디렉토리 접근 테스트
    test_upload_directory_access()
    
    # 2. 파일 업로드 테스트
    file_id = test_upload_without_db()
    
    print("\n" + "=" * 50)
    if file_id:
        print("✅ 테스트 성공!")
    else:
        print("❌ 테스트 실패")
    print("🏁 테스트 완료")

if __name__ == "__main__":
    main()
