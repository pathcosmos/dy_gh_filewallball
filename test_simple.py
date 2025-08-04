#!/usr/bin/env python3
"""FileWallBall 간단한 테스트 스크립트"""

import os
import time
from datetime import datetime

import requests

# 설정
API_URL = "http://filewallball:8000"
MASTER_KEY = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
PROJECT_NAME = f"test-{int(time.time())}"
REQUEST_DATE = datetime.now().strftime("%Y%m%d")


def main():
    print("=== FileWallBall 간단한 테스트 ===")
    print(f"API URL: {API_URL}")
    print(f"프로젝트: {PROJECT_NAME}")
    print()

    # 1. 헬스체크
    print("1. 헬스체크...")
    try:
        r = requests.get(f"{API_URL}/health", timeout=10)
        if r.status_code == 200:
            print(f"✅ 성공: {r.json()}")
        else:
            print(f"❌ 실패: {r.status_code}")
            return 1
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 1

    # 2. 프로젝트 키 생성
    print("\n2. 프로젝트 키 생성...")
    try:
        data = {
            "project_name": PROJECT_NAME,
            "request_date": REQUEST_DATE,
            "master_key": MASTER_KEY,
        }
        r = requests.post(f"{API_URL}/keygen", data=data, timeout=10)
        if r.status_code == 200:
            result = r.json()
            project_key = result.get("project_key")
            print(f"✅ 성공: {project_key}")
        else:
            print(f"❌ 실패: {r.status_code} - {r.text}")
            return 1
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 1

    # 3. 파일 업로드
    print("\n3. 파일 업로드...")
    try:
        # 테스트 파일 생성
        content = f"Hello FileWallBall! {datetime.now()}"
        with open("test.txt", "w") as f:
            f.write(content)

        files = {"file": ("test.txt", open("test.txt", "rb"), "text/plain")}
        data = {"project_key": project_key}

        r = requests.post(f"{API_URL}/upload", files=files, data=data, timeout=30)
        if r.status_code == 200:
            result = r.json()
            file_id = result.get("file_id")
            download_url = result.get("download_url")
            print(f"✅ 성공: {file_id}")
        else:
            print(f"❌ 실패: {r.status_code} - {r.text}")
            return 1
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 1

    # 4. 파일 다운로드
    print("\n4. 파일 다운로드...")
    try:
        r = requests.get(download_url, timeout=30)
        if r.status_code == 200:
            with open("downloaded.txt", "wb") as f:
                f.write(r.content)
            print(f"✅ 성공: {r.text}")
        else:
            print(f"❌ 실패: {r.status_code}")
            return 1
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 1

    # 5. 파일 비교
    print("\n5. 파일 비교...")
    try:
        with open("test.txt", "r") as f1, open("downloaded.txt", "r") as f2:
            if f1.read() == f2.read():
                print("✅ 파일이 동일합니다!")
            else:
                print("❌ 파일이 다릅니다!")
                return 1
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 1

    # 정리
    print("\n6. 정리...")
    for f in ["test.txt", "downloaded.txt"]:
        if os.path.exists(f):
            os.remove(f)
    print("✅ 정리 완료")

    print("\n🎉 모든 테스트가 성공했습니다!")
    return 0


if __name__ == "__main__":
    exit(main())
