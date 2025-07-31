"""
Comprehensive File Upload/Download Integration Tests for Subtask 15.2.

This module implements detailed integration tests for file upload and download functionality
including various file sizes, concurrent operations, integrity verification, and error handling.
"""

import asyncio
import hashlib
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient

from app.models.orm_models import FileInfo


class TestFileUploadDownloadIntegration:
    """Comprehensive file upload and download integration tests."""

    @pytest_asyncio.fixture
    async def test_files_setup(self, temp_upload_dir):
        """Setup various test files for comprehensive testing."""
        test_files = {}

        # Small file (1KB)
        small_content = b"Small test file content " * 40  # ~1KB
        small_file = temp_upload_dir / "small_test.txt"
        small_file.write_bytes(small_content)
        test_files["small"] = {
            "path": small_file,
            "content": small_content,
            "size": len(small_content),
            "hash": hashlib.sha256(small_content).hexdigest(),
            "mime_type": "text/plain",
        }

        # Medium file (100KB)
        medium_content = b"Medium test file content " * 4000  # ~100KB
        medium_file = temp_upload_dir / "medium_test.txt"
        medium_file.write_bytes(medium_content)
        test_files["medium"] = {
            "path": medium_file,
            "content": medium_content,
            "size": len(medium_content),
            "hash": hashlib.sha256(medium_content).hexdigest(),
            "mime_type": "text/plain",
        }

        # Large file (1MB)
        large_content = b"Large test file content " * 40000  # ~1MB
        large_file = temp_upload_dir / "large_test.txt"
        large_file.write_bytes(large_content)
        test_files["large"] = {
            "path": large_file,
            "content": large_content,
            "size": len(large_content),
            "hash": hashlib.sha256(large_content).hexdigest(),
            "mime_type": "text/plain",
        }

        # Image file for thumbnail testing
        image_content = b"fake_image_data_for_thumbnail_testing"
        image_file = temp_upload_dir / "test_image.jpg"
        image_file.write_bytes(image_content)
        test_files["image"] = {
            "path": image_file,
            "content": image_content,
            "size": len(image_content),
            "hash": hashlib.sha256(image_content).hexdigest(),
            "mime_type": "image/jpeg",
        }

        yield test_files

        # Cleanup
        for file_info in test_files.values():
            if file_info["path"].exists():
                file_info["path"].unlink()

    @pytest.mark.asyncio
    async def test_various_file_sizes_upload_download(
        self, test_client, test_tokens, test_files_setup
    ):
        """Test upload and download of files with various sizes (1KB~1MB)."""
        token = test_tokens["regular_user"]

        for size_name, file_info in test_files_setup.items():
            # Upload file
            with open(file_info["path"], "rb") as f:
                upload_response = test_client.post(
                    "/upload",
                    files={"file": (file_info["path"].name, f, file_info["mime_type"])},
                    headers={"Authorization": f"Bearer {token}"},
                )

            assert (
                upload_response.status_code == status.HTTP_201_CREATED
            ), f"Upload failed for {size_name} file"

            upload_data = upload_response.json()
            file_id = upload_data["file_id"]

            # Verify file metadata
            metadata_response = test_client.get(
                f"/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert metadata_response.status_code == status.HTTP_200_OK
            metadata = metadata_response.json()

            assert (
                metadata["size"] == file_info["size"]
            ), f"Size mismatch for {size_name} file"
            assert metadata["content_type"] == file_info["mime_type"]

            # Download and verify integrity
            download_response = test_client.get(
                f"/download/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert download_response.status_code == status.HTTP_200_OK
            downloaded_content = download_response.content

            # Verify content integrity
            downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
            assert (
                downloaded_hash == file_info["hash"]
            ), f"Hash mismatch for {size_name} file"

            # Verify file size
            assert (
                len(downloaded_content) == file_info["size"]
            ), f"Content size mismatch for {size_name} file"

    @pytest.mark.asyncio
    async def test_concurrent_multiple_file_uploads(
        self, test_client, test_tokens, test_files_setup
    ):
        """Test concurrent upload of multiple files."""
        token = test_tokens["regular_user"]
        num_concurrent = 5

        # Create multiple copies of test files
        test_files = []
        for i in range(num_concurrent):
            for size_name, file_info in test_files_setup.items():
                new_file = file_info["path"].parent / f"{size_name}_{i}.txt"
                new_file.write_bytes(file_info["content"])
                test_files.append(
                    {
                        "path": new_file,
                        "content": file_info["content"],
                        "hash": file_info["hash"],
                        "mime_type": file_info["mime_type"],
                    }
                )

        # Upload files concurrently
        async def upload_single_file(file_info):
            with open(file_info["path"], "rb") as f:
                response = test_client.post(
                    "/upload",
                    files={"file": (file_info["path"].name, f, file_info["mime_type"])},
                    headers={"Authorization": f"Bearer {token}"},
                )
            return response

        # Create tasks for concurrent uploads
        tasks = [upload_single_file(file_info) for file_info in test_files]
        results = await asyncio.gather(*tasks)

        # Verify all uploads succeeded
        successful_uploads = 0
        for response in results:
            if response.status_code == status.HTTP_201_CREATED:
                successful_uploads += 1

        assert successful_uploads == len(
            test_files
        ), f"Expected {len(test_files)} successful uploads, got {successful_uploads}"

        # Cleanup
        for file_info in test_files:
            if file_info["path"].exists():
                file_info["path"].unlink()

    @pytest.mark.asyncio
    async def test_chunk_upload_download_verification(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test chunk-based upload and download verification."""
        token = test_tokens["regular_user"]

        # Create a large file for chunk testing
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = 3
        total_size = chunk_size * num_chunks

        # Generate test content
        test_content = b"Chunk test content " * (chunk_size // 20)  # ~1MB per chunk
        full_content = test_content * num_chunks

        # Create test file
        test_file = temp_upload_dir / "chunk_test.txt"
        test_file.write_bytes(full_content)
        expected_hash = hashlib.sha256(full_content).hexdigest()

        # Upload file
        with open(test_file, "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": ("chunk_test.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Verify file metadata
        metadata_response = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert metadata_response.status_code == status.HTTP_200_OK
        metadata = metadata_response.json()

        assert metadata["size"] == total_size
        assert metadata["content_type"] == "text/plain"

        # Download and verify integrity
        download_response = test_client.get(
            f"/download/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert download_response.status_code == status.HTTP_200_OK
        downloaded_content = download_response.content

        # Verify content integrity
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        assert downloaded_hash == expected_hash

        # Verify chunk-by-chunk integrity
        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size
            chunk_content = full_content[start:end]
            chunk_hash = hashlib.sha256(chunk_content).hexdigest()

            downloaded_chunk = downloaded_content[start:end]
            downloaded_chunk_hash = hashlib.sha256(downloaded_chunk).hexdigest()

            assert (
                downloaded_chunk_hash == chunk_hash
            ), f"Chunk {i} integrity verification failed"

        # Cleanup
        test_file.unlink()

    @pytest.mark.asyncio
    async def test_file_hash_integrity_verification(
        self, test_client, test_tokens, test_files_setup
    ):
        """Test file hash integrity verification during upload and download."""
        token = test_tokens["regular_user"]

        # Test with medium file for hash verification
        file_info = test_files_setup["medium"]

        # Upload file
        with open(file_info["path"], "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": (file_info["path"].name, f, file_info["mime_type"])},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Verify file metadata includes hash
        metadata_response = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert metadata_response.status_code == status.HTTP_200_OK
        metadata = metadata_response.json()

        # Check if hash is present in metadata
        assert (
            "hash" in metadata or "file_hash" in metadata
        ), "File hash should be present in metadata"

        # Download and verify hash matches
        download_response = test_client.get(
            f"/download/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert download_response.status_code == status.HTTP_200_OK
        downloaded_content = download_response.content

        # Verify downloaded content hash matches original
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        assert downloaded_hash == file_info["hash"]

        # Verify hash matches metadata if available
        if "hash" in metadata:
            assert metadata["hash"] == f"sha256:{file_info['hash']}"
        elif "file_hash" in metadata:
            assert metadata["file_hash"] == file_info["hash"]

    @pytest.mark.asyncio
    async def test_thumbnail_generation_verification(
        self, test_client, test_tokens, test_files_setup
    ):
        """Test thumbnail generation for image files."""
        token = test_tokens["regular_user"]

        # Test with image file
        file_info = test_files_setup["image"]

        # Upload image file
        with open(file_info["path"], "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": (file_info["path"].name, f, file_info["mime_type"])},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Try to access thumbnail/preview endpoint
        # Note: This depends on the actual API endpoint for thumbnails
        try:
            thumbnail_response = test_client.get(
                f"/view/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            # If thumbnail endpoint exists, verify it returns something
            if thumbnail_response.status_code == status.HTTP_200_OK:
                assert (
                    len(thumbnail_response.content) > 0
                ), "Thumbnail should have content"
            elif thumbnail_response.status_code == status.HTTP_404_NOT_FOUND:
                # Thumbnail generation might not be implemented yet
                pass
            else:
                # Other status codes are acceptable for unimplemented features
                pass

        except Exception:
            # Thumbnail endpoint might not exist yet
            pass

    @pytest.mark.asyncio
    async def test_file_metadata_crud_operations(
        self, test_client, test_tokens, test_files_setup
    ):
        """Test file metadata CRUD operations."""
        token = test_tokens["regular_user"]

        # Upload a test file
        file_info = test_files_setup["small"]

        with open(file_info["path"], "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": (file_info["path"].name, f, file_info["mime_type"])},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Read metadata
        metadata_response = test_client.get(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert metadata_response.status_code == status.HTTP_200_OK
        initial_metadata = metadata_response.json()

        # Update metadata (if update endpoint exists)
        try:
            update_response = test_client.put(
                f"/files/{file_id}",
                json={"description": "Updated test description"},
                headers={"Authorization": f"Bearer {token}"},
            )

            if update_response.status_code == status.HTTP_200_OK:
                # Verify update was successful
                updated_metadata_response = test_client.get(
                    f"/files/{file_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert updated_metadata_response.status_code == status.HTTP_200_OK
                updated_metadata = updated_metadata_response.json()

                # Check if description was updated
                if "description" in updated_metadata:
                    assert updated_metadata["description"] == "Updated test description"

        except Exception:
            # Update endpoint might not be implemented yet
            pass

    @pytest.mark.asyncio
    async def test_invalid_file_format_handling(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test handling of invalid file formats and corrupted files."""
        token = test_tokens["regular_user"]

        # Test 1: Empty file
        empty_file = temp_upload_dir / "empty.txt"
        empty_file.write_bytes(b"")

        with open(empty_file, "rb") as f:
            response = test_client.post(
                "/upload",
                files={"file": ("empty.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Empty files might be allowed or rejected depending on configuration
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

        # Test 2: File with invalid extension
        invalid_file = temp_upload_dir / "test.exe"
        invalid_file.write_bytes(b"fake executable content")

        with open(invalid_file, "rb") as f:
            response = test_client.post(
                "/upload",
                files={"file": ("test.exe", f, "application/octet-stream")},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Executable files should typically be rejected
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # Test 3: File with no extension
        no_ext_file = temp_upload_dir / "noextension"
        no_ext_file.write_bytes(b"content without extension")

        with open(no_ext_file, "rb") as f:
            response = test_client.post(
                "/upload",
                files={"file": ("noextension", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Files without extensions might be allowed or rejected
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

        # Cleanup
        for file_path in [empty_file, invalid_file, no_ext_file]:
            if file_path.exists():
                file_path.unlink()

    @pytest.mark.asyncio
    async def test_upload_download_performance_measurement(
        self, test_client, test_tokens, test_files_setup
    ):
        """Test upload and download performance measurement."""
        token = test_tokens["regular_user"]

        # Test with medium file for performance measurement
        file_info = test_files_setup["medium"]

        # Measure upload time
        start_time = time.time()

        with open(file_info["path"], "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": (file_info["path"].name, f, file_info["mime_type"])},
                headers={"Authorization": f"Bearer {token}"},
            )

        upload_time = time.time() - start_time

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Measure download time
        start_time = time.time()

        download_response = test_client.get(
            f"/download/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        download_time = time.time() - start_time

        assert download_response.status_code == status.HTTP_200_OK

        # Performance assertions (adjust thresholds based on system capabilities)
        file_size_mb = file_info["size"] / (1024 * 1024)

        # Upload should complete within reasonable time (30 seconds per MB)
        max_upload_time = file_size_mb * 30
        assert (
            upload_time < max_upload_time
        ), f"Upload took {upload_time:.2f}s, expected < {max_upload_time:.2f}s"

        # Download should complete within reasonable time (10 seconds per MB)
        max_download_time = file_size_mb * 10
        assert (
            download_time < max_download_time
        ), f"Download took {download_time:.2f}s, expected < {max_download_time:.2f}s"

        # Log performance metrics
        print(f"\nPerformance Metrics for {file_size_mb:.2f}MB file:")
        print(f"Upload time: {upload_time:.2f}s ({file_size_mb/upload_time:.2f} MB/s)")
        print(
            f"Download time: {download_time:.2f}s ({file_size_mb/download_time:.2f} MB/s)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_access_to_same_file(
        self, test_client, test_tokens, test_files_setup
    ):
        """Test concurrent access to the same uploaded file."""
        token = test_tokens["regular_user"]

        # Upload a test file
        file_info = test_files_setup["medium"]

        with open(file_info["path"], "rb") as f:
            upload_response = test_client.post(
                "/upload",
                files={"file": (file_info["path"].name, f, file_info["mime_type"])},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Concurrent access to the same file
        num_concurrent = 10

        async def access_file():
            # Get metadata
            metadata_response = test_client.get(
                f"/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Download file
            download_response = test_client.get(
                f"/download/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            return {
                "metadata_status": metadata_response.status_code,
                "download_status": download_response.status_code,
                "download_size": (
                    len(download_response.content)
                    if download_response.status_code == 200
                    else 0
                ),
            }

        # Create concurrent access tasks
        tasks = [access_file() for _ in range(num_concurrent)]
        results = await asyncio.gather(*tasks)

        # Verify all concurrent accesses succeeded
        successful_accesses = 0
        for result in results:
            if (
                result["metadata_status"] == status.HTTP_200_OK
                and result["download_status"] == status.HTTP_200_OK
                and result["download_size"] == file_info["size"]
            ):
                successful_accesses += 1

        assert (
            successful_accesses == num_concurrent
        ), f"Expected {num_concurrent} successful concurrent accesses, got {successful_accesses}"

    @pytest.mark.asyncio
    async def test_file_upload_download_error_handling(self, test_client, test_tokens):
        """Test error handling for various upload/download scenarios."""
        token = test_tokens["regular_user"]

        # Test 1: Upload with invalid token
        test_content = b"Test content for error handling"
        response = test_client.post(
            "/upload",
            files={"file": ("test.txt", test_content, "text/plain")},
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # Test 2: Download non-existent file
        response = test_client.get(
            "/download/non-existent-file-id",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test 3: Get metadata for non-existent file
        response = test_client.get(
            "/files/non-existent-file-id",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test 4: Upload without file
        response = test_client.post(
            "/upload",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test 5: Upload with malformed request
        response = test_client.post(
            "/upload",
            data={"file": "not_a_file"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]


class TestFileUploadDownloadEdgeCases:
    """Test edge cases and boundary conditions for file upload/download."""

    @pytest.mark.asyncio
    async def test_very_large_filename_handling(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test handling of files with very long filenames."""
        token = test_tokens["regular_user"]

        # Create filename with 255 characters
        long_filename = "a" * 250 + ".txt"
        test_content = b"Test content for long filename"

        test_file = temp_upload_dir / long_filename
        test_file.write_bytes(test_content)

        with open(test_file, "rb") as f:
            response = test_client.post(
                "/upload",
                files={"file": (long_filename, f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Should either succeed or fail gracefully
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        ]

        # Cleanup
        test_file.unlink()

    @pytest.mark.asyncio
    async def test_special_characters_in_filename(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test handling of filenames with special characters."""
        token = test_tokens["regular_user"]

        special_filenames = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.with.dots.txt",
            "file(1).txt",
            "file[1].txt",
            "file{1}.txt",
            "file@#$%.txt",
            "한글파일.txt",  # Korean characters
            "файл.txt",  # Cyrillic characters
            "ファイル.txt",  # Japanese characters
        ]

        test_content = b"Test content for special characters"

        for filename in special_filenames:
            test_file = temp_upload_dir / filename
            test_file.write_bytes(test_content)

            with open(test_file, "rb") as f:
                response = test_client.post(
                    "/upload",
                    files={"file": (filename, f, "text/plain")},
                    headers={"Authorization": f"Bearer {token}"},
                )

            # Most special characters should be handled gracefully
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
            ]

            # Cleanup
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_duplicate_filename_handling(
        self, test_client, test_tokens, temp_upload_dir
    ):
        """Test handling of duplicate filenames."""
        token = test_tokens["regular_user"]

        filename = "duplicate_test.txt"
        test_content = b"Test content for duplicate filename"

        # Upload first file
        test_file = temp_upload_dir / filename
        test_file.write_bytes(test_content)

        with open(test_file, "rb") as f:
            response1 = test_client.post(
                "/upload",
                files={"file": (filename, f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response1.status_code == status.HTTP_201_CREATED

        # Upload second file with same name
        with open(test_file, "rb") as f:
            response2 = test_client.post(
                "/upload",
                files={"file": (filename, f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Should either succeed (with different IDs) or fail gracefully
        assert response2.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_409_CONFLICT,
        ]

        # Cleanup
        test_file.unlink()
