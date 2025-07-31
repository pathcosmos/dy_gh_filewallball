#!/usr/bin/env python3
"""
Router endpoints test script.
"""

import asyncio
import sys
from pathlib import Path

import httpx

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main_new import app


async def test_health_endpoints():
    """헬스체크 엔드포인트 테스트"""
    print("=== Testing Health Endpoints ===")

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # 기본 헬스체크
        response = await client.get("/health")
        print(f"Basic health check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Service: {data.get('service')}")

        # 상세 헬스체크
        response = await client.get("/health/detailed")
        print(f"Detailed health check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data.get('status')}")
            checks = data.get("checks", {})
            for check_name, check_data in checks.items():
                print(f"  {check_name}: {check_data.get('status')}")

        # Readiness 체크
        response = await client.get("/health/ready")
        print(f"Readiness check: {response.status_code}")

        # Liveness 체크
        response = await client.get("/health/live")
        print(f"Liveness check: {response.status_code}")

        # 서비스 정보
        response = await client.get("/info")
        print(f"Service info: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Name: {data.get('name')}")
            print(f"  Version: {data.get('version')}")


async def test_file_endpoints():
    """파일 엔드포인트 테스트"""
    print("\n=== Testing File Endpoints ===")

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # 파일 목록 조회
        response = await client.get("/files/")
        print(f"List files: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Total files: {data.get('total')}")

        # 파일 정보 조회 (존재하는 파일)
        response = await client.get("/files/sample-file-1")
        print(f"Get file info (existing): {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Filename: {data.get('filename')}")
            print(f"  Size: {data.get('size')}")

        # 파일 정보 조회 (존재하지 않는 파일)
        response = await client.get("/files/non-existent-file")
        print(f"Get file info (non-existent): {response.status_code}")

        # 파일 다운로드
        response = await client.get("/files/sample-file-1/download")
        print(f"Download file: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Download URL: {data.get('download_url')}")


async def test_root_endpoint():
    """루트 엔드포인트 테스트"""
    print("\n=== Testing Root Endpoint ===")

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        print(f"Root endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Message: {data.get('message')}")
            print(f"  Version: {data.get('version')}")
            print(f"  Docs: {data.get('docs')}")


async def main():
    """메인 테스트 함수"""
    print("🚀 Starting Router Tests...\n")

    try:
        await test_root_endpoint()
        await test_health_endpoints()
        await test_file_endpoints()

        print("\n🎉 All router tests completed!")
        return 0

    except Exception as e:
        print(f"\n💥 Router test error: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
