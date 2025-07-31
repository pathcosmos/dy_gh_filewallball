#!/usr/bin/env python3
"""
FileWallBall 파일 검증 시스템 테스트
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

from fastapi import UploadFile

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.validators.file_validator import FileValidator


class MockDBSession:
    """Mock 데이터베이스 세션"""

    def __init__(self):
        self.extensions = [
            Mock(
                extension=".txt",
                mime_type="text/plain",
                is_allowed=True,
                max_file_size=1048576,
            ),
            Mock(
                extension=".jpg",
                mime_type="image/jpeg",
                is_allowed=True,
                max_file_size=10485760,
            ),
            Mock(
                extension=".pdf",
                mime_type="application/pdf",
                is_allowed=True,
                max_file_size=52428800,
            ),
            Mock(
                extension=".exe",
                mime_type="application/x-executable",
                is_allowed=False,
                max_file_size=1048576,
            ),
        ]

    def query(self, model):
        return MockQuery(self.extensions)

    def get_system_setting(self, key, default=None):
        if key == "max_file_size":
            return 104857600  # 100MB
        return default


class MockQuery:
    """Mock 쿼리 객체"""

    def __init__(self, extensions):
        self.extensions = extensions

    def filter(self, *args):
        return self

    def first(self):
        # 간단한 필터링 로직
        for ext in self.extensions:
            if hasattr(ext, "extension") and ext.extension == ".txt":
                return ext
        return None

    def all(self):
        return [ext for ext in self.extensions if ext.is_allowed]


class MockDatabaseHelpers:
    """Mock 데이터베이스 헬퍼"""

    def get_system_setting(self, key, default=None):
        if key == "max_file_size":
            return 104857600  # 100MB
        return default


async def create_test_file(content: bytes, filename: str) -> UploadFile:
    """테스트용 파일 생성"""
    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as f:
        f.write(content)
        temp_path = f.name

    # UploadFile 객체 생성
    file = UploadFile(filename=filename, file=open(temp_path, "rb"))
    file.content_type = "application/octet-stream"

    return file, temp_path


async def test_file_validation():
    """파일 검증 테스트"""
    print("🧪 파일 검증 시스템 테스트 시작\n")

    # Mock 데이터베이스 세션 생성
    mock_db = MockDBSession()

    # 파일 검증기 생성
    validator = FileValidator(mock_db)

    # 테스트 케이스들
    test_cases = [
        {
            "name": "정상 텍스트 파일",
            "content": b"Hello, World!",
            "filename": "test.txt",
            "expected_valid": True,
        },
        {
            "name": "허용되지 않는 확장자",
            "content": b"executable content",
            "filename": "test.exe",
            "expected_valid": False,
        },
        {
            "name": "빈 파일",
            "content": b"",
            "filename": "empty.txt",
            "expected_valid": False,
        },
        {
            "name": "위험한 파일명",
            "content": b"content",
            "filename": "test..txt",
            "expected_valid": False,
        },
        {
            "name": "큰 파일 (시뮬레이션)",
            "content": b"x" * 200 * 1024 * 1024,  # 200MB
            "filename": "large.txt",
            "expected_valid": False,
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"📋 테스트 {i}: {test_case['name']}")

        try:
            # 테스트 파일 생성
            file, temp_path = await create_test_file(
                test_case["content"], test_case["filename"]
            )

            # 파일 검증 수행
            result = await validator.validate_file(file)

            # 결과 확인
            if result["is_valid"] == test_case["expected_valid"]:
                print(
                    f"✅ 통과: 예상 {test_case['expected_valid']}, 실제 {result['is_valid']}"
                )
            else:
                print(
                    f"❌ 실패: 예상 {test_case['expected_valid']}, 실제 {result['is_valid']}"
                )

            # 오류 메시지 출력
            if result["errors"]:
                print(f"   오류: {', '.join(result['errors'])}")

            # 경고 메시지 출력
            if result["warnings"]:
                print(f"   경고: {', '.join(result['warnings'])}")

            # 임시 파일 정리
            file.file.close()
            os.unlink(temp_path)

        except Exception as e:
            print(f"❌ 테스트 실행 중 오류: {e}")

        print()

    # 허용된 확장자 목록 테스트
    print("📋 허용된 확장자 목록 테스트")
    try:
        allowed_extensions = validator.get_allowed_extensions()
        print(f"✅ 허용된 확장자: {allowed_extensions}")
    except Exception as e:
        print(f"❌ 확장자 목록 조회 실패: {e}")

    # 파일 크기 제한 테스트
    print("\n📋 파일 크기 제한 테스트")
    try:
        size_limits = validator.get_file_size_limits()
        print(f"✅ 전역 최대 크기: {size_limits['global_max'] / (1024*1024):.1f}MB")
        print(f"✅ 확장자별 제한: {size_limits['by_extension']}")
    except Exception as e:
        print(f"❌ 크기 제한 조회 실패: {e}")

    print("\n🎉 파일 검증 시스템 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_file_validation())
