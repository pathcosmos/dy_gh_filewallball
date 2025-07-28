"""
파일 유틸리티 함수들
"""

import hashlib
import os
from pathlib import Path
from typing import Optional


def calculate_file_hash(file_path: Path, algorithm: str = 'md5') -> str:
    """
    파일 해시 계산
    
    Args:
        file_path: 파일 경로
        algorithm: 해시 알고리즘 (md5, sha1, sha256)
        
    Returns:
        파일 해시 문자열
    """
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def get_file_extension(filename: str) -> str:
    """
    파일명에서 확장자 추출
    
    Args:
        filename: 파일명
        
    Returns:
        확장자 (소문자, 점 포함)
    """
    return Path(filename).suffix.lower()


def validate_file_type(filename: str, allowed_extensions: list) -> bool:
    """
    파일 타입 검증
    
    Args:
        filename: 파일명
        allowed_extensions: 허용된 확장자 목록
        
    Returns:
        허용된 파일 타입인지 여부
    """
    extension = get_file_extension(filename)
    return extension in allowed_extensions


def get_file_size(file_path: Path) -> int:
    """
    파일 크기 조회
    
    Args:
        file_path: 파일 경로
        
    Returns:
        파일 크기 (bytes)
    """
    return os.path.getsize(file_path)


def is_text_file(filename: str) -> bool:
    """
    텍스트 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        텍스트 파일인지 여부
    """
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', 
        '.xml', '.csv', '.log', '.ini', '.cfg', '.conf'
    }
    return get_file_extension(filename) in text_extensions


def is_image_file(filename: str) -> bool:
    """
    이미지 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        이미지 파일인지 여부
    """
    image_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
        '.webp', '.svg', '.ico'
    }
    return get_file_extension(filename) in image_extensions


def is_video_file(filename: str) -> bool:
    """
    비디오 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        비디오 파일인지 여부
    """
    video_extensions = {
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', 
        '.mkv', '.m4v', '.3gp', '.ogv'
    }
    return get_file_extension(filename) in video_extensions


def is_audio_file(filename: str) -> bool:
    """
    오디오 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        오디오 파일인지 여부
    """
    audio_extensions = {
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', 
        '.m4a', '.opus', '.aiff'
    }
    return get_file_extension(filename) in audio_extensions


def is_archive_file(filename: str) -> bool:
    """
    압축 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        압축 파일인지 여부
    """
    archive_extensions = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', 
        '.xz', '.lzma', '.cab'
    }
    return get_file_extension(filename) in archive_extensions


def get_mime_type(filename: str) -> str:
    """
    파일의 MIME 타입 추정
    
    Args:
        filename: 파일명
        
    Returns:
        MIME 타입
    """
    import mimetypes
    
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def sanitize_filename(filename: str) -> str:
    """
    파일명 정리 (위험한 문자 제거)
    
    Args:
        filename: 원본 파일명
        
    Returns:
        정리된 파일명
    """
    # 위험한 문자들을 언더스코어로 대체
    dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # 연속된 언더스코어를 하나로
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    
    # 앞뒤 공백 및 점 제거
    sanitized = sanitized.strip(' .')
    
    return sanitized 