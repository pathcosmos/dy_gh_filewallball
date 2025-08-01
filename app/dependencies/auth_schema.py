"""
JWT Bearer 토큰 인증 스키마 정의
"""

from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from app.models.api_models import ErrorResponse

# JWT Bearer 토큰 인증 스키마
security = HTTPBearer(
    scheme_name="JWT Bearer Token",
    description="JWT Bearer 토큰을 사용한 인증. Authorization 헤더에 'Bearer <token>' 형식으로 전송하세요.",
    auto_error=True,
)


class TokenResponse(BaseModel):
    """토큰 응답 모델"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """토큰 데이터 모델"""

    username: Optional[str] = None
    user_id: Optional[str] = None
    permissions: list[str] = []


# 에러 코드 정의
class ErrorCodes:
    """에러 코드 상수"""

    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    FILE_TOO_LARGE = "file_too_large"
    INVALID_FILE_TYPE = "invalid_file_type"
    INTERNAL_SERVER_ERROR = "internal_server_error"


# 공통 에러 응답 정의
def get_common_error_responses():
    """공통 에러 응답 정의"""
    return {
        400: {
            "description": "잘못된 요청",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "요청 파라미터가 올바르지 않습니다.",
                        "error_type": ErrorCodes.VALIDATION_ERROR,
                        "error_code": 400,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        401: {
            "description": "인증 실패",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "유효한 인증 토큰이 필요합니다.",
                        "error_type": ErrorCodes.UNAUTHORIZED,
                        "error_code": 401,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        403: {
            "description": "권한 없음",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "해당 리소스에 대한 접근 권한이 없습니다.",
                        "error_type": ErrorCodes.FORBIDDEN,
                        "error_code": 403,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        404: {
            "description": "리소스 없음",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "요청한 리소스를 찾을 수 없습니다.",
                        "error_type": ErrorCodes.NOT_FOUND,
                        "error_code": 404,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        413: {
            "description": "파일 크기 초과",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "파일 크기가 허용된 최대 크기를 초과했습니다.",
                        "error_type": ErrorCodes.FILE_TOO_LARGE,
                        "error_code": 413,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        429: {
            "description": "요청 한도 초과",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                        "error_type": ErrorCodes.RATE_LIMIT_EXCEEDED,
                        "error_code": 429,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        500: {
            "description": "서버 내부 오류",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "서버 내부 오류가 발생했습니다.",
                        "error_type": ErrorCodes.INTERNAL_SERVER_ERROR,
                        "error_code": 500,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    }


# 파일 관련 에러 응답
def get_file_error_responses():
    """파일 관련 에러 응답 정의"""
    base_responses = get_common_error_responses()
    file_specific_responses = {
        415: {
            "description": "지원되지 않는 파일 형식",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "지원되지 않는 파일 형식입니다.",
                        "error_type": ErrorCodes.INVALID_FILE_TYPE,
                        "error_code": 415,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        416: {
            "description": "Range 요청 범위 오류",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "요청한 범위가 파일 크기를 초과합니다.",
                        "error_type": "range_not_satisfiable",
                        "error_code": 416,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    }
    base_responses.update(file_specific_responses)
    return base_responses


# 관리자 전용 에러 응답
def get_admin_error_responses():
    """관리자 전용 에러 응답 정의"""
    base_responses = get_common_error_responses()
    admin_specific_responses = {
        403: {
            "description": "관리자 권한 필요",
            "model": "ErrorResponse",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "이 작업을 수행하려면 관리자 권한이 필요합니다.",
                        "error_type": ErrorCodes.FORBIDDEN,
                        "error_code": 403,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        }
    }
    base_responses.update(admin_specific_responses)
    return base_responses


# 인증 헤더 예제
def get_auth_header_example():
    """인증 헤더 예제"""
    return {
        "Authorization": {
            "summary": "JWT Bearer 토큰",
            "description": "JWT Bearer 토큰을 사용한 인증",
            "value": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwidXNlcl9pZCI6IjEyMyIsInBlcm1pc3Npb25zIjpbImZpbGVfcmVhZCIsImZpbGVfd3JpdGUiXSwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "required": True,
        }
    }


# 파일 업로드 예제
def get_file_upload_example():
    """파일 업로드 예제"""
    return {
        "multipart/form-data": {
            "summary": "파일 업로드",
            "description": "파일을 업로드합니다.",
            "value": {
                "file": "(binary)",
                "category_id": 1,
                "tags": "document,pdf",
                "is_public": True,
                "description": "중요한 문서",
            },
        }
    }


# 파일 다운로드 예제
def get_file_download_example():
    """파일 다운로드 예제"""
    return {
        "application/octet-stream": {
            "summary": "파일 다운로드",
            "description": "파일 바이너리 데이터",
            "value": "(binary file data)",
        }
    }


# 성공 응답 예제
def get_success_response_example():
    """성공 응답 예제"""
    return {
        "application/json": {
            "summary": "성공 응답",
            "description": "작업이 성공적으로 완료되었습니다.",
            "value": {
                "status": "success",
                "message": "작업이 성공적으로 완료되었습니다.",
                "timestamp": "2024-01-15T10:30:00Z",
            },
        }
    }
