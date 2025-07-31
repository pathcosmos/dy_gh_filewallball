"""
보안 유틸리티 함수들
"""

import hashlib
import hmac
import secrets
import string
import uuid
from typing import Optional


def generate_encryption_key(length: int = 32) -> str:
    """암호화 키 생성"""
    return secrets.token_urlsafe(length)


def hash_key(key: str, salt: Optional[str] = None) -> str:
    """키 해시 생성"""
    if salt is None:
        salt = "FileWallBall_Salt_2024"

    # HMAC-SHA256을 사용한 키 해시
    return hmac.new(
        salt.encode("utf-8"), key.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_key_signature(
    key: str, signature: str, data: str, salt: Optional[str] = None
) -> bool:
    """키 서명 검증"""
    expected_signature = hmac.new(
        key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


def generate_request_signature(key: str, data: str) -> str:
    """요청 서명 생성"""
    return hmac.new(
        key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def sanitize_ip_address(ip_address: str) -> str:
    """IP 주소 정규화"""
    # IPv6 주소의 경우 대괄호 제거
    if ip_address.startswith("[") and ip_address.endswith("]"):
        ip_address = ip_address[1:-1]

    return ip_address.strip()


def is_valid_ip_address(ip_address: str) -> bool:
    """IP 주소 유효성 검사"""
    try:
        import ipaddress

        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False


def is_valid_cidr_range(cidr_range: str) -> bool:
    """CIDR 범위 유효성 검사"""
    try:
        import ipaddress

        ipaddress.ip_network(cidr_range, strict=False)
        return True
    except ValueError:
        return False


# 기존 호환성을 위한 함수들
def generate_uuid() -> str:
    """UUID 생성"""
    return str(uuid.uuid4())


def sanitize_filename(filename: str) -> str:
    """파일명 정리 (보안 강화)"""
    # 위험한 문자들을 언더스코어로 대체
    dangerous_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    sanitized = filename

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "_")

    # 연속된 언더스코어를 하나로
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")

    # 앞뒤 공백 및 점 제거
    sanitized = sanitized.strip(" .")

    return sanitized


def generate_random_string(length: int = 32) -> str:
    """랜덤 문자열 생성"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key() -> str:
    """API 키 생성"""
    return secrets.token_urlsafe(32)


def generate_session_token() -> str:
    """세션 토큰 생성"""
    return secrets.token_urlsafe(64)


def is_safe_filename(filename: str) -> bool:
    """안전한 파일명인지 확인"""
    dangerous_patterns = [
        "..",
        "\\",
        "/",
        ":",
        "*",
        "?",
        '"',
        "<",
        ">",
        "|",
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]

    filename_upper = filename.upper()
    for pattern in dangerous_patterns:
        if pattern in filename_upper:
            return False

    return True


def validate_file_extension(extension: str, allowed_extensions: list) -> bool:
    """파일 확장자 검증"""
    return extension.lower() in [ext.lower() for ext in allowed_extensions]
