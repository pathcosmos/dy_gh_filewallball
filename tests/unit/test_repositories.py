"""
Tests for repository pattern implementation.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm_models import FileInfo
from app.repositories.base import BaseRepository
from app.repositories.file_repository import FileRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_base_repository_create(test_db_session: AsyncSession):
    """Test base repository create method."""
    repo = BaseRepository(FileInfo, test_db_session)

    file_data = {
        "file_uuid": "test-uuid-123",
        "original_filename": "test.txt",
        "stored_filename": "test_stored.txt",
        "file_extension": "txt",
        "mime_type": "text/plain",
        "file_size": 1024,
        "storage_path": "/uploads/test.txt",
    }

    file_info = await repo.create(**file_data)
    assert file_info is not None
    assert file_info.file_uuid == "test-uuid-123"
    assert file_info.original_filename == "test.txt"


@pytest.mark.asyncio
async def test_base_repository_get_by_id(test_db_session: AsyncSession):
    """Test base repository get_by_id method."""
    repo = BaseRepository(FileInfo, test_db_session)

    # Create a file first
    file_data = {
        "file_uuid": "test-uuid-456",
        "original_filename": "test2.txt",
        "stored_filename": "test2_stored.txt",
        "file_extension": "txt",
        "mime_type": "text/plain",
        "file_size": 2048,
        "storage_path": "/uploads/test2.txt",
    }

    created_file = await repo.create(**file_data)

    # Get by ID
    retrieved_file = await repo.get_by_id(created_file.id)
    assert retrieved_file is not None
    assert retrieved_file.file_uuid == "test-uuid-456"


@pytest.mark.asyncio
async def test_file_repository_get_by_uuid(test_db_session: AsyncSession):
    """Test file repository get_by_uuid method."""
    repo = FileRepository(test_db_session)

    # Create a file first
    file_data = {
        "file_uuid": "test-uuid-789",
        "original_filename": "test3.txt",
        "stored_filename": "test3_stored.txt",
        "file_extension": "txt",
        "mime_type": "text/plain",
        "file_size": 3072,
        "storage_path": "/uploads/test3.txt",
    }

    await repo.create(**file_data)

    # Get by UUID
    retrieved_file = await repo.get_by_uuid("test-uuid-789")
    assert retrieved_file is not None
    assert retrieved_file.original_filename == "test3.txt"


@pytest.mark.asyncio
async def test_file_repository_get_by_hash(test_db_session: AsyncSession):
    """Test file repository get_by_hash method."""
    repo = FileRepository(test_db_session)

    # Create a file with hash
    file_data = {
        "file_uuid": "test-uuid-hash",
        "original_filename": "test_hash.txt",
        "stored_filename": "test_hash_stored.txt",
        "file_extension": "txt",
        "mime_type": "text/plain",
        "file_size": 4096,
        "storage_path": "/uploads/test_hash.txt",
        "file_hash": "abc123def456",
    }

    await repo.create(**file_data)

    # Get by hash
    retrieved_file = await repo.get_by_hash("abc123def456")
    assert retrieved_file is not None
    assert retrieved_file.file_uuid == "test-uuid-hash"


@pytest.mark.asyncio
async def test_user_repository_get_by_username(test_db_session: AsyncSession):
    """Test user repository get_by_username method."""
    repo = UserRepository(test_db_session)

    # Create a user first
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "role": "user",
    }

    await repo.create(**user_data)

    # Get by username
    retrieved_user = await repo.get_by_username("testuser")
    assert retrieved_user is not None
    assert retrieved_user.email == "test@example.com"


@pytest.mark.asyncio
async def test_user_repository_get_by_email(test_db_session: AsyncSession):
    """Test user repository get_by_email method."""
    repo = UserRepository(test_db_session)

    # Create a user first
    user_data = {
        "username": "testuser2",
        "email": "test2@example.com",
        "password_hash": "hashed_password2",
        "role": "user",
    }

    await repo.create(**user_data)

    # Get by email
    retrieved_user = await repo.get_by_email("test2@example.com")
    assert retrieved_user is not None
    assert retrieved_user.username == "testuser2"


@pytest.mark.asyncio
async def test_base_repository_bulk_operations(test_db_session: AsyncSession):
    """Test base repository bulk operations."""
    repo = BaseRepository(FileInfo, test_db_session)

    # Bulk create
    files_data = [
        {
            "file_uuid": f"bulk-uuid-{i}",
            "original_filename": f"bulk{i}.txt",
            "stored_filename": f"bulk{i}_stored.txt",
            "file_extension": "txt",
            "mime_type": "text/plain",
            "file_size": 1024 * i,
            "storage_path": f"/uploads/bulk{i}.txt",
        }
        for i in range(1, 4)
    ]

    created_files = await repo.bulk_create(files_data)
    assert len(created_files) == 3

    # Test count
    count = await repo.count()
    assert count >= 3

    # Test exists
    exists = await repo.exists(created_files[0].id)
    assert exists is True


@pytest.mark.asyncio
async def test_file_repository_search(test_db_session: AsyncSession):
    """Test file repository search functionality."""
    repo = FileRepository(test_db_session)

    # Create test files
    files_data = [
        {
            "file_uuid": "search-uuid-1",
            "original_filename": "document.pdf",
            "stored_filename": "doc1.pdf",
            "file_extension": "pdf",
            "mime_type": "application/pdf",
            "file_size": 1024,
            "storage_path": "/uploads/doc1.pdf",
        },
        {
            "file_uuid": "search-uuid-2",
            "original_filename": "image.jpg",
            "stored_filename": "img1.jpg",
            "file_extension": "jpg",
            "mime_type": "image/jpeg",
            "file_size": 2048,
            "storage_path": "/uploads/img1.jpg",
        },
    ]

    for file_data in files_data:
        await repo.create(**file_data)

    # Search by filename
    results = await repo.search_files("document")
    assert len(results) >= 1
    assert any("document" in f.original_filename for f in results)

    # Search by content type
    pdf_files = await repo.get_by_content_type("application/pdf")
    assert len(pdf_files) >= 1
    assert all(f.mime_type == "application/pdf" for f in pdf_files)
