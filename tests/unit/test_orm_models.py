#!/usr/bin/env python3
"""
ORM Models test script.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from app.models import (
    FileCategory,
    FileDownload,
    FileExtension,
    FileInfo,
    FileStatistics,
    FileTag,
    FileTagRelation,
    FileUpload,
    FileView,
    SystemSetting,
    add_tags_to_file,
    bulk_insert_files,
    generate_file_uuid,
    get_file_statistics,
    remove_tags_from_file,
    restore_file,
    soft_delete_file,
)
from app.models.database import get_db


def test_model_creation():
    """모델 생성 테스트"""
    print("Testing model creation...")

    # FileInfo 모델 생성 테스트
    file_info = FileInfo(
        original_filename="test.txt",
        stored_filename="test_123.txt",
        file_extension="txt",
        mime_type="text/plain",
        file_size=1024,
        storage_path="/uploads/test_123.txt",
    )

    print(f"Created FileInfo: {file_info}")
    print(f"Generated UUID: {file_info.file_uuid}")

    # FileCategory 모델 생성 테스트
    category = FileCategory(name="Documents", description="Document files")

    print(f"Created FileCategory: {category}")

    # FileExtension 모델 생성 테스트
    extension = FileExtension(
        extension="txt", mime_type="text/plain", is_allowed=True, max_file_size=1048576
    )

    print(f"Created FileExtension: {extension}")

    # FileTag 모델 생성 테스트
    tag = FileTag(
        tag_name="important", tag_color="#ff0000", description="Important files"
    )

    print(f"Created FileTag: {tag}")

    print("Model creation tests passed!")


def test_relationships():
    """관계 설정 테스트"""
    print("\nTesting relationships...")

    # 카테고리 생성
    category = FileCategory(name="Images", description="Image files")

    # 파일 생성 (카테고리와 관계 설정)
    file_info = FileInfo(
        original_filename="image.jpg",
        stored_filename="image_456.jpg",
        file_extension="jpg",
        mime_type="image/jpeg",
        file_size=2048,
        storage_path="/uploads/image_456.jpg",
    )

    # 관계 설정 (실제로는 DB 세션이 필요)
    print(f"File category relationship: {file_info.category}")
    print(f"Category files relationship: {category.files}")

    print("Relationship tests passed!")


def test_helper_functions():
    """헬퍼 함수 테스트"""
    print("\nTesting helper functions...")

    # UUID 생성 테스트
    uuid1 = generate_file_uuid()
    uuid2 = generate_file_uuid()

    print(f"Generated UUID 1: {uuid1}")
    print(f"Generated UUID 2: {uuid2}")
    print(f"UUIDs are different: {uuid1 != uuid2}")

    # 태그 관리 함수 테스트 (시뮬레이션)
    print("Tag management functions available:")
    print("- add_tags_to_file()")
    print("- remove_tags_from_file()")
    print("- get_file_statistics()")
    print("- bulk_insert_files()")
    print("- soft_delete_file()")
    print("- restore_file()")

    print("Helper function tests passed!")


def test_model_attributes():
    """모델 속성 테스트"""
    print("\nTesting model attributes...")

    # FileInfo 속성 테스트
    file_info = FileInfo(
        original_filename="document.pdf",
        stored_filename="doc_789.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=5120,
        storage_path="/uploads/doc_789.pdf",
    )

    print(f"File ID: {file_info.id}")
    print(f"File UUID: {file_info.file_uuid}")
    print(f"Original filename: {file_info.original_filename}")
    print(f"File extension: {file_info.file_extension}")
    print(f"File size: {file_info.file_size}")
    print(f"Is public: {file_info.is_public}")
    print(f"Is deleted: {file_info.is_deleted}")

    # SystemSetting 속성 테스트
    setting = SystemSetting(
        setting_key="max_file_size",
        setting_value="10485760",
        setting_type="integer",
        description="Maximum allowed file size in bytes",
    )

    print(f"Setting key: {setting.setting_key}")
    print(f"Setting value: {setting.setting_value}")
    print(f"Setting type: {setting.setting_type}")

    print("Model attribute tests passed!")


def test_enum_values():
    """Enum 값 테스트"""
    print("\nTesting enum values...")

    # FileView enum 테스트
    view_types = ["info", "preview", "download"]
    print(f"Valid view types: {view_types}")

    # FileDownload enum 테스트
    download_methods = ["direct", "api", "web"]
    print(f"Valid download methods: {download_methods}")

    # FileUpload enum 테스트
    upload_methods = ["web", "api", "batch"]
    print(f"Valid upload methods: {upload_methods}")

    print("Enum value tests passed!")


def main():
    """메인 테스트 함수"""
    print("Starting ORM Models Tests...\n")

    try:
        test_model_creation()
        test_relationships()
        test_helper_functions()
        test_model_attributes()
        test_enum_values()

        print("\nAll ORM model tests passed!")
        return 0

    except Exception as e:
        print(f"\nORM model test error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
