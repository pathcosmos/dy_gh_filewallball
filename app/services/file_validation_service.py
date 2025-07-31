"""
File validation service for enhanced security.
Task 12.4: 파일 업로드 유효성 검사 및 제한 정책 강화
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import magic
from fastapi import HTTPException, UploadFile, status

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FileValidationService:
    """파일 업로드 유효성 검사 서비스"""

    def __init__(self):
        # 허용된 MIME 타입 정의
        self.allowed_mime_types = {
            # 이미지 파일
            "image/jpeg": [".jpg", ".jpeg"],
            "image/png": [".png"],
            "image/gif": [".gif"],
            "image/webp": [".webp"],
            "image/svg+xml": [".svg"],
            # 문서 파일
            "application/pdf": [".pdf"],
            "application/msword": [".doc"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
                ".docx"
            ],
            "application/vnd.ms-excel": [".xls"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
                ".xlsx"
            ],
            "application/vnd.ms-powerpoint": [".ppt"],
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": [
                ".pptx"
            ],
            "text/plain": [".txt"],
            "text/csv": [".csv"],
            "text/markdown": [".md"],
            # 압축 파일
            "application/zip": [".zip"],
            "application/x-rar-compressed": [".rar"],
            "application/x-7z-compressed": [".7z"],
            "application/gzip": [".gz"],
            "application/x-tar": [".tar"],
            # 미디어 파일
            "video/mp4": [".mp4"],
            "video/avi": [".avi"],
            "video/quicktime": [".mov"],
            "audio/mpeg": [".mp3"],
            "audio/wav": [".wav"],
            "audio/ogg": [".ogg"],
            # 기타
            "application/json": [".json"],
            "application/xml": [".xml"],
            "text/html": [".html", ".htm"],
        }

        # 차단된 MIME 타입 (실행 파일, 스크립트 등)
        self.blocked_mime_types = {
            "application/x-executable",
            "application/x-dosexec",
            "application/x-msdownload",
            "application/x-msi",
            "application/x-shockwave-flash",
            "application/x-java-applet",
            "application/x-java-archive",
            "text/x-python",
            "text/x-php",
            "text/x-javascript",
            "text/x-shellscript",
            "application/x-shellscript",
            "application/x-perl",
            "application/x-ruby",
        }

        # 차단된 확장자
        self.blocked_extensions = {
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".pif",
            ".scr",
            ".vbs",
            ".js",
            ".jar",
            ".war",
            ".ear",
            ".class",
            ".py",
            ".php",
            ".pl",
            ".rb",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".ps1",
            ".psm1",
            ".psd1",
            ".msi",
            ".msm",
            ".msp",
            ".app",
            ".dmg",
            ".deb",
            ".rpm",
            ".apk",
            ".ipa",
            ".xap",
            ".swf",
            ".fla",
            ".flv",
        }

        # 최대 파일 크기 (100MB)
        self.max_file_size = 100 * 1024 * 1024

        # 최소 파일 크기 (1KB)
        self.min_file_size = 1024

        # 파일명 검증 패턴
        self.forbidden_filename_patterns = [
            "..",
            "~",
            "con",
            "prn",
            "aux",
            "nul",
            "com1",
            "com2",
            "com3",
            "com4",
            "com5",
            "com6",
            "com7",
            "com8",
            "com9",
            "lpt1",
            "lpt2",
            "lpt3",
            "lpt4",
            "lpt5",
            "lpt6",
            "lpt7",
            "lpt8",
            "lpt9",
        ]

    def validate_file_size(self, file_size: int) -> Tuple[bool, str]:
        """파일 크기 검증"""
        if file_size > self.max_file_size:
            return (
                False,
                f"파일 크기가 너무 큽니다. 최대 {self.max_file_size // (1024*1024)}MB까지 허용됩니다.",
            )

        if file_size < self.min_file_size:
            return (
                False,
                f"파일 크기가 너무 작습니다. 최소 {self.min_file_size // 1024}KB 이상이어야 합니다.",
            )

        return True, "파일 크기가 적절합니다."

    def validate_filename(self, filename: str) -> Tuple[bool, str]:
        """파일명 검증"""
        if not filename or len(filename.strip()) == 0:
            return False, "파일명이 비어있습니다."

        if len(filename) > 255:
            return False, "파일명이 너무 깁니다. 255자 이하여야 합니다."

        # 위험한 패턴 검사
        filename_lower = filename.lower()
        for pattern in self.forbidden_filename_patterns:
            if pattern in filename_lower:
                return (
                    False,
                    f"허용되지 않는 파일명 패턴이 포함되어 있습니다: {pattern}",
                )

        # 특수 문자 검사
        forbidden_chars = ["<", ">", ":", '"', "|", "?", "*", "\\", "/"]
        for char in forbidden_chars:
            if char in filename:
                return False, f"허용되지 않는 문자가 포함되어 있습니다: {char}"

        return True, "파일명이 유효합니다."

    def validate_file_extension(self, filename: str) -> Tuple[bool, str]:
        """파일 확장자 검증"""
        file_path = Path(filename)
        extension = file_path.suffix.lower()

        if not extension:
            return False, "파일 확장자가 없습니다."

        if extension in self.blocked_extensions:
            return False, f"허용되지 않는 파일 확장자입니다: {extension}"

        return True, "파일 확장자가 유효합니다."

    def validate_mime_type(
        self, file_content: bytes, filename: str
    ) -> Tuple[bool, str, str]:
        """MIME 타입 검증 (Magic Number 기반)"""
        try:
            # Magic Number로 실제 MIME 타입 확인
            detected_mime = magic.from_buffer(file_content, mime=True)

            # 파일 확장자로 예상 MIME 타입 확인
            file_path = Path(filename)
            extension = file_path.suffix.lower()

            # 차단된 MIME 타입 검사
            if detected_mime in self.blocked_mime_types:
                return (
                    False,
                    f"허용되지 않는 파일 타입입니다: {detected_mime}",
                    detected_mime,
                )

            # 허용된 MIME 타입 검사
            if detected_mime not in self.allowed_mime_types:
                return (
                    False,
                    f"지원되지 않는 파일 타입입니다: {detected_mime}",
                    detected_mime,
                )

            # 확장자와 MIME 타입 일치성 검사
            expected_extensions = self.allowed_mime_types[detected_mime]
            if extension not in expected_extensions:
                logger.warning(
                    f"파일 확장자와 MIME 타입이 일치하지 않습니다. "
                    f"파일: {filename}, 확장자: {extension}, "
                    f"감지된 MIME: {detected_mime}, 예상 확장자: {expected_extensions}"
                )
                # 경고만 하고 차단하지는 않음 (사용자가 확장자를 잘못 지정했을 수 있음)

            return True, f"파일 타입이 유효합니다: {detected_mime}", detected_mime

        except Exception as e:
            logger.error(f"MIME 타입 검증 중 오류 발생: {e}")
            return False, f"파일 타입 검증에 실패했습니다: {str(e)}", "unknown"

    def validate_file_content(self, file_content: bytes) -> Tuple[bool, str]:
        """파일 내용 검증 (악성 패턴 검사)"""
        try:
            content_str = file_content.decode("utf-8", errors="ignore")

            # 악성 패턴 검사
            malicious_patterns = [
                "<?php",
                "<script",
                "javascript:",
                "vbscript:",
                "data:text/html",
                "eval(",
                "document.cookie",
                "window.location",
                "alert(",
                "exec(",
                "system(",
                "shell_exec(",
                "passthru(",
                "base64_decode(",
                "gzinflate(",
                "str_rot13(",
                "<?=",
                "<? ",
                "<%",
                "<% ",
                "<script>",
                "</script>",
            ]

            for pattern in malicious_patterns:
                if pattern.lower() in content_str.lower():
                    return False, f"악성 코드 패턴이 감지되었습니다: {pattern}"

            return True, "파일 내용이 유효합니다."

        except Exception as e:
            logger.error(f"파일 내용 검증 중 오류 발생: {e}")
            return True, "파일 내용 검증을 건너뜁니다."  # 바이너리 파일의 경우

    async def validate_upload_file(self, file: UploadFile) -> Dict[str, any]:
        """파일 업로드 종합 검증"""
        validation_result = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "mime_type": None,
            "file_size": 0,
            "validation_details": {},
        }

        try:
            # 파일 크기 확인
            file_content = await file.read()
            file_size = len(file_content)
            validation_result["file_size"] = file_size

            # 파일 크기 검증
            size_valid, size_message = self.validate_file_size(file_size)
            if not size_valid:
                validation_result["errors"].append(size_message)
            else:
                validation_result["validation_details"]["size"] = size_message

            # 파일명 검증
            filename_valid, filename_message = self.validate_filename(file.filename)
            if not filename_valid:
                validation_result["errors"].append(filename_message)
            else:
                validation_result["validation_details"]["filename"] = filename_message

            # 파일 확장자 검증
            extension_valid, extension_message = self.validate_file_extension(
                file.filename
            )
            if not extension_valid:
                validation_result["errors"].append(extension_message)
            else:
                validation_result["validation_details"]["extension"] = extension_message

            # MIME 타입 검증
            mime_valid, mime_message, detected_mime = self.validate_mime_type(
                file_content, file.filename
            )
            validation_result["mime_type"] = detected_mime

            if not mime_valid:
                validation_result["errors"].append(mime_message)
            else:
                validation_result["validation_details"]["mime_type"] = mime_message

            # 파일 내용 검증 (텍스트 파일의 경우)
            if detected_mime and detected_mime.startswith("text/"):
                content_valid, content_message = self.validate_file_content(
                    file_content
                )
                if not content_valid:
                    validation_result["errors"].append(content_message)
                else:
                    validation_result["validation_details"]["content"] = content_message

            # 파일 포인터를 처음으로 되돌림
            await file.seek(0)

            # 검증 결과 결정
            validation_result["is_valid"] = len(validation_result["errors"]) == 0

            # 로깅
            if validation_result["is_valid"]:
                logger.info(
                    f"파일 검증 성공: {file.filename}, "
                    f"크기: {file_size}, MIME: {detected_mime}"
                )
            else:
                logger.warning(
                    f"파일 검증 실패: {file.filename}, "
                    f"오류: {validation_result['errors']}"
                )

            return validation_result

        except Exception as e:
            logger.error(f"파일 검증 중 예외 발생: {e}")
            validation_result["errors"].append(
                f"파일 검증 중 오류가 발생했습니다: {str(e)}"
            )
            return validation_result

    def get_allowed_extensions(self) -> List[str]:
        """허용된 확장자 목록 반환"""
        extensions = []
        for mime_extensions in self.allowed_mime_types.values():
            extensions.extend(mime_extensions)
        return sorted(list(set(extensions)))

    def get_blocked_extensions(self) -> List[str]:
        """차단된 확장자 목록 반환"""
        return sorted(list(self.blocked_extensions))


# 전역 인스턴스
file_validation_service = FileValidationService()
