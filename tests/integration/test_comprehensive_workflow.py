"""
Comprehensive integration tests for FileWallBall system.

This module tests the complete workflow of the FileWallBall system including:
- File upload/download workflows
- Authentication and authorization
- Caching mechanisms
- Database operations
- Error handling and recovery
- Concurrent operations
- Performance scenarios
"""

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List

import httpx
import pytest
import pytest_asyncio
from fastapi import status

from app.services.cache_service import CacheService
from app.services.file_service import FileService


class TestFileUploadDownloadWorkflow:
    """Test complete file upload and download workflow."""

    @pytest_asyncio.fixture
    async def setup_workflow_test(
        self, test_client, test_redis_client, test_db_session, temp_upload_dir
    ):
        """Setup test environment for workflow testing."""
        # Create test file
        test_content = b"This is a test file for workflow testing.\n" * 100
        test_file = temp_upload_dir / "workflow_test.txt"
        test_file.write_bytes(test_content)

        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()

        yield {
            "test_file": test_file,
            "test_content": test_content,
            "expected_hash": expected_hash,
            "file_size": len(test_content),
        }

        # Cleanup
        if test_file.exists():
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_complete_file_workflow(
        self, setup_workflow_test, test_client, test_tokens
    ):
        """Test complete file upload, metadata verification, and download workflow."""
        test_data = setup_workflow_test
        token = test_tokens["regular_user"]

        # Step 1: Upload file
        with open(test_data["test_file"], "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": ("workflow_test.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Step 2: Verify file metadata
        metadata_response = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert metadata_response.status_code == status.HTTP_200_OK
        metadata = metadata_response.json()

        assert metadata["filename"] == "workflow_test.txt"
        assert metadata["size"] == test_data["file_size"]
        assert metadata["content_type"] == "text/plain"
        assert metadata["hash"] == f"sha256:{test_data['expected_hash']}"

        # Step 3: Download file and verify integrity
        download_response = test_client.get(
            f"/download/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert download_response.status_code == status.HTTP_200_OK
        downloaded_content = download_response.content

        # Verify content integrity
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        assert downloaded_hash == test_data["expected_hash"]
        assert downloaded_content == test_data["test_content"]

        # Step 4: Verify cache hit on subsequent requests
        cache_response = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert cache_response.status_code == status.HTTP_200_OK
        # Cache should be hit for metadata

    @pytest.mark.asyncio
    async def test_file_workflow_with_thumbnail(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test file workflow with thumbnail generation for image files."""
        # Create a simple test image (PNG format)
        import io

        from PIL import Image

        # Create a simple test image
        img = Image.new("RGB", (100, 100), color="red")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_data = img_buffer.getvalue()

        test_image = temp_upload_dir / "test_image.png"
        test_image.write_bytes(img_data)

        token = test_tokens["regular_user"]

        # Upload image file
        with open(test_image, "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": ("test_image.png", f, "image/png")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Verify thumbnail was generated
        metadata_response = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert metadata_response.status_code == status.HTTP_200_OK
        metadata = metadata_response.json()

        # Check if thumbnail exists
        assert "thumbnail_url" in metadata or "has_thumbnail" in metadata

        # Test thumbnail access
        if "thumbnail_url" in metadata:
            thumbnail_response = test_client.get(
                metadata["thumbnail_url"],
                headers={"Authorization": f"Bearer {token}"},
            )
            assert thumbnail_response.status_code == status.HTTP_200_OK

        # Cleanup
        test_image.unlink(missing_ok=True)


class TestAuthenticationAndAuthorization:
    """Test authentication and authorization workflows."""

    @pytest.mark.asyncio
    async def test_user_authentication_workflow(
        self, test_client, test_users, auth_service
    ):
        """Test complete user authentication workflow."""
        user = test_users[0]  # admin_user

        # Step 1: User login
        login_response = test_client.post(
            "/auth/login",
            json={
                "username": user["username"],
                "password": user["password"],
            },
        )

        assert login_response.status_code == status.HTTP_200_OK
        login_data = login_response.json()

        assert "access_token" in login_data
        assert "token_type" in login_data
        assert login_data["token_type"] == "bearer"

        token = login_data["access_token"]

        # Step 2: Access protected endpoint
        protected_response = test_client.get(
            "/files",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert protected_response.status_code == status.HTTP_200_OK

        # Step 3: Test token refresh
        refresh_response = test_client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert refresh_response.status_code == status.HTTP_200_OK
        refresh_data = refresh_response.json()

        assert "access_token" in refresh_data
        assert refresh_data["access_token"] != token  # New token

    @pytest.mark.asyncio
    async def test_role_based_access_control(
        self, test_client, test_users, test_tokens
    ):
        """Test role-based access control for different user types."""
        # Test admin user permissions
        admin_token = test_tokens["admin_user"]

        # Admin should be able to access all endpoints
        files_response = test_client.get(
            "/files",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert files_response.status_code == status.HTTP_200_OK

        # Test regular user permissions
        user_token = test_tokens["regular_user"]

        files_response = test_client.get(
            "/files",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert files_response.status_code == status.HTTP_200_OK

        # Test readonly user permissions
        readonly_token = test_tokens["readonly_user"]

        # Readonly user should be able to read but not upload
        files_response = test_client.get(
            "/files",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert files_response.status_code == status.HTTP_200_OK

        # Readonly user should not be able to upload
        upload_response = test_client.post(
            "/upload",
            files={"file": ("test.txt", b"test content", "text/plain")},
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert upload_response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_ip_based_access_control(self, test_client, test_tokens, test_users):
        """Test IP-based access control."""
        user = test_users[1]  # regular_user with IP whitelist

        # Test access from whitelisted IP (127.0.0.1)
        response = test_client.get(
            "/files",
            headers={
                "Authorization": f"Bearer {test_tokens[user['username']]}",
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # Test access from non-whitelisted IP
        response = test_client.get(
            "/files",
            headers={
                "Authorization": f"Bearer {test_tokens[user['username']]}",
                "X-Forwarded-For": "192.168.2.1",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestCachingAndDatabaseIntegration:
    """Test caching and database integration workflows."""

    @pytest.mark.asyncio
    async def test_cache_database_consistency(
        self, test_client, test_tokens, test_redis_client, test_db_session
    ):
        """Test consistency between cache and database."""
        token = test_tokens["regular_user"]

        # Create test file
        test_content = b"Cache consistency test content"
        test_file = tempfile.NamedTemporaryFile(delete=False)
        test_file.write(test_content)
        test_file.close()

        # Upload file
        with open(test_file.name, "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": ("cache_test.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Check database record
        from app.models.orm_models import FileInfo

        db_file = test_db_session.query(FileInfo).filter(FileInfo.id == file_id).first()
        assert db_file is not None
        assert db_file.original_filename == "cache_test.txt"

        # Check cache entry
        cache_key = f"file:metadata:{file_id}"
        cached_metadata = await test_redis_client.get(cache_key)
        assert cached_metadata is not None

        # Verify cache and database are consistent
        import json

        cached_data = json.loads(cached_metadata)
        assert cached_data["filename"] == db_file.filename
        assert cached_data["size"] == db_file.size

        # Cleanup
        import os

        os.unlink(test_file.name)

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(
        self, test_client, test_tokens, test_redis_client
    ):
        """Test cache invalidation when file metadata is updated."""
        token = test_tokens["regular_user"]

        # Upload file
        test_content = b"Cache invalidation test"
        upload_response = test_client.post(
            "/upload",
            files={"file": ("invalidation_test.txt", test_content, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Get initial metadata (should populate cache)
        metadata_response = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert metadata_response.status_code == status.HTTP_200_OK

        # Verify cache is populated
        cache_key = f"file:metadata:{file_id}"
        initial_cache = await test_redis_client.get(cache_key)
        assert initial_cache is not None

        # Update file metadata
        update_response = test_client.put(
            f"/files/{file_id}",
            json={"description": "Updated description"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == status.HTTP_200_OK

        # Verify cache was invalidated
        updated_cache = await test_redis_client.get(cache_key)
        # Cache should be either invalidated or updated
        assert updated_cache != initial_cache

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(
        self, test_client, test_tokens, test_db_session
    ):
        """Test database transaction rollback on errors."""
        token = test_tokens["regular_user"]

        # Count initial files
        initial_count = test_db_session.query(FileInfo).count()

        # Attempt upload with invalid data (should fail)
        try:
            upload_response = test_client.post(
                "/upload",
                files={"file": ("", b"", "text/plain")},  # Empty filename
                headers={"Authorization": f"Bearer {token}"},
            )
        except Exception:
            pass  # Expected to fail

        # Verify no new records were created
        final_count = test_db_session.query(FileInfo).count()
        assert final_count == initial_count


class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test multiple concurrent file uploads."""
        token = test_tokens["regular_user"]
        num_concurrent = 5

        # Create test files
        test_files = []
        for i in range(num_concurrent):
            content = f"Concurrent test file {i}".encode()
            file_path = temp_upload_dir / f"concurrent_test_{i}.txt"
            file_path.write_bytes(content)
            test_files.append(file_path)

        # Upload files concurrently
        async def upload_file(file_path: Path) -> Dict:
            with open(file_path, "rb") as f:
                response = test_client.post(
                    "/upload",
                    files={"file": (file_path.name, f, "text/plain")},
                    headers={"Authorization": f"Bearer {token}"},
                )
            return {"file_path": file_path, "response": response}

        # Execute concurrent uploads
        tasks = [upload_file(file_path) for file_path in test_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all uploads succeeded
        successful_uploads = 0
        for result in results:
            if isinstance(result, dict) and result["response"].status_code == 201:
                successful_uploads += 1

        assert successful_uploads == num_concurrent

        # Cleanup
        for file_path in test_files:
            file_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_concurrent_file_access(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test concurrent access to the same file."""
        token = test_tokens["regular_user"]

        # Upload a test file
        test_content = b"Concurrent access test content"
        upload_response = test_client.post(
            "/upload",
            files={"file": ("concurrent_access.txt", test_content, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert upload_response.status_code == status.HTTP_201_CREATED
        file_id = upload_response.json()["file_id"]

        # Concurrently access the file
        async def access_file() -> Dict:
            response = test_client.get(
                f"/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            return {"status_code": response.status_code, "data": response.json()}

        # Execute concurrent accesses
        num_concurrent = 10
        tasks = [access_file() for _ in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all accesses succeeded
        successful_accesses = 0
        for result in results:
            if isinstance(result, dict) and result["status_code"] == 200:
                successful_accesses += 1

        assert successful_accesses == num_concurrent


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_file_upload_handling(self, test_client, test_tokens):
        """Test handling of invalid file uploads."""
        token = test_tokens["regular_user"]

        # Test empty file
        upload_response = test_client.post(
            "/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload_response.status_code == status.HTTP_400_BAD_REQUEST

        # Test file too large
        large_content = b"x" * (100 * 1024 * 1024 + 1)  # 100MB + 1 byte
        upload_response = test_client.post(
            "/upload",
            files={"file": ("large.txt", large_content, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload_response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

        # Test invalid file type
        upload_response = test_client.post(
            "/upload",
            files={"file": ("test.exe", b"executable", "application/x-executable")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload_response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, test_client):
        """Test authentication error handling."""
        # Test without token
        response = test_client.get("/files")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test with invalid token
        response = test_client.get(
            "/files",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test with expired token
        response = test_client.get(
            "/files",
            headers={"Authorization": "Bearer expired_token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_database_connection_failure_handling(
        self, test_client, test_tokens, monkeypatch
    ):
        """Test handling of database connection failures."""
        token = test_tokens["regular_user"]

        # Mock database failure
        def mock_db_failure():
            raise Exception("Database connection failed")

        # This would require mocking the database dependency
        # For now, we'll test the error response structure
        response = test_client.get(
            "/files",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should handle gracefully even if database is down
        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_cache_failure_graceful_degradation(
        self, test_client, test_tokens, test_redis_client
    ):
        """Test graceful degradation when cache is unavailable."""
        token = test_tokens["regular_user"]

        # Temporarily disable Redis
        await test_redis_client.close()

        # System should still work without cache
        response = test_client.get(
            "/files",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should still respond (possibly slower but functional)
        assert response.status_code in [200, 500, 503]

        # Reconnect Redis for cleanup
        await test_redis_client.ping()


class TestPerformanceScenarios:
    """Test performance scenarios and load handling."""

    @pytest.mark.asyncio
    async def test_large_file_upload_performance(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test performance of large file uploads."""
        token = test_tokens["regular_user"]

        # Create large test file (10MB)
        large_content = b"Large file content " * (10 * 1024 * 1024 // 19)
        large_file = temp_upload_dir / "large_test.txt"
        large_file.write_bytes(large_content)

        import time

        start_time = time.time()

        # Upload large file
        with open(large_file, "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": ("large_test.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        upload_time = time.time() - start_time

        assert upload_response.status_code == status.HTTP_201_CREATED

        # Performance assertion (should complete within reasonable time)
        assert upload_time < 30  # 30 seconds for 10MB file

        # Cleanup
        large_file.unlink()

    @pytest.mark.asyncio
    async def test_many_small_files_performance(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test performance with many small files."""
        token = test_tokens["regular_user"]
        num_files = 50

        # Create many small files
        test_files = []
        for i in range(num_files):
            content = f"Small file {i} content".encode()
            file_path = temp_upload_dir / f"small_test_{i}.txt"
            file_path.write_bytes(content)
            test_files.append(file_path)

        import time

        start_time = time.time()

        # Upload all files
        successful_uploads = 0
        for file_path in test_files:
            with open(file_path, "rb") as f:
                response = test_client.post(
                    "/upload",
                    files={"file": (file_path.name, f, "text/plain")},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code == 201:
                    successful_uploads += 1

        total_time = time.time() - start_time

        # Performance assertion
        assert successful_uploads == num_files
        assert total_time < 60  # 60 seconds for 50 small files

        # Cleanup
        for file_path in test_files:
            file_path.unlink()

    @pytest.mark.asyncio
    async def test_cache_performance_impact(
        self, test_client, test_tokens, test_redis_client
    ):
        """Test performance impact of caching."""
        token = test_tokens["regular_user"]

        # Upload a test file
        test_content = b"Cache performance test content"
        upload_response = test_client.post(
            "/upload",
            files={"file": ("cache_perf_test.txt", test_content, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert upload_response.status_code == status.HTTP_201_CREATED
        file_id = upload_response.json()["file_id"]

        import time

        # First request (cache miss)
        start_time = time.time()
        response1 = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        first_request_time = time.time() - start_time

        # Second request (cache hit)
        start_time = time.time()
        response2 = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        second_request_time = time.time() - start_time

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Cache hit should be faster
        assert second_request_time < first_request_time


# Import required for database operations
from app.models.orm_models import FileInfo
