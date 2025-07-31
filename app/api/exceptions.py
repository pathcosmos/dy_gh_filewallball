"""
API-specific exceptions and error handling.

This module contains custom exceptions for the API layer.
"""

from fastapi import HTTPException, status


class FileWallBallException(HTTPException):
    """Base exception for FileWallBall API."""

    def __init__(
        self, status_code: int, detail: str, headers: dict | None = None
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class FileNotFoundError(FileWallBallException):
    """Raised when a requested file is not found."""

    def __init__(self, file_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found",
        )


class FileUploadError(FileWallBallException):
    """Raised when file upload fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File upload failed: {reason}",
        )


class ValidationError(FileWallBallException):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error in {field}: {message}",
        )


class RateLimitExceededError(FileWallBallException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers=headers,
        )
