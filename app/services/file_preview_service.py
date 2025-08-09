"""
파일 미리보기 및 썸네일 생성 서비스
Task 6: 파일 미리보기 및 썸네일 생성 시스템
"""

import asyncio
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import chardet
from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps

# Redis 클라이언트 제거됨
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FilePreviewService:
    """파일 미리보기 및 썸네일 생성 서비스"""

    def __init__(self):
        # 지원하는 텍스트 파일 확장자
        self.text_extensions = {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".csv",
            ".log",
            ".ini",
            ".cfg",
            ".conf",
            ".yml",
            ".yaml",
            ".toml",
            ".sql",
            ".sh",
            ".bat",
            ".ps1",
            ".r",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".php",
            ".rb",
            ".go",
            ".rs",
            ".swift",
            ".kt",
            ".scala",
            ".clj",
        }

        # 지원하는 이미지 파일 확장자
        self.image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".tif",
            ".webp",
            ".svg",
            ".ico",
            ".heic",
            ".heif",
        }

        # 썸네일 크기 설정
        self.thumbnail_sizes = {
            "small": (200, 200),
            "medium": (400, 400),
            "large": (800, 800),
        }

        # 최대 미리보기 크기 (1MB)
        self.max_preview_size = 1024 * 1024

        # 텍스트 미리보기 최대 라인 수
        self.max_preview_lines = 100

    def is_text_file(self, filename: str) -> bool:
        """텍스트 파일인지 확인"""
        ext = Path(filename).suffix.lower()
        return ext in self.text_extensions

    def is_image_file(self, filename: str) -> bool:
        """이미지 파일인지 확인"""
        ext = Path(filename).suffix.lower()
        return ext in self.image_extensions

    async def detect_encoding(self, file_path: Path) -> str:
        """파일 인코딩 감지"""
        try:
            # 파일의 처음 1KB만 읽어서 인코딩 감지
            with open(file_path, "rb") as f:
                raw_data = f.read(1024)

            # chardet로 인코딩 감지
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            confidence = result["confidence"]

            # 신뢰도가 낮거나 None인 경우 기본값 사용
            if not encoding or confidence < 0.7:
                encoding = "utf-8"

            # 일반적인 인코딩으로 정규화
            if encoding.lower() in ["gbk", "gb2312", "gb18030"]:
                encoding = "gbk"
            elif encoding.lower() in ["euc-kr", "cp949"]:
                encoding = "cp949"
            elif encoding.lower() in ["utf-8", "utf8"]:
                encoding = "utf-8"
            else:
                encoding = "utf-8"

            return encoding

        except Exception as e:
            logger.warning(f"인코딩 감지 실패: {e}")
            return "utf-8"

    async def get_text_preview(self, file_path: Path) -> Dict:
        """텍스트 파일 미리보기"""
        try:
            # 파일 크기 확인
            file_size = file_path.stat().st_size
            if file_size > self.max_preview_size:
                return {
                    "type": "text",
                    "preview_available": False,
                    "reason": f"파일이 너무 큽니다 ({file_size / 1024 / 1024:.1f}MB > 1MB)",
                    "file_size": file_size,
                }

            # 인코딩 감지
            encoding = await self.detect_encoding(file_path)

            # 파일 읽기
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                # 인코딩 실패 시 바이너리로 읽기
                with open(file_path, "rb") as f:
                    content = f.read(self.max_preview_size)
                    return {
                        "type": "text",
                        "preview_available": False,
                        "reason": "인코딩을 감지할 수 없습니다",
                        "file_size": file_size,
                        "encoding": "unknown",
                    }

            # 미리보기 생성
            preview_lines = lines[: self.max_preview_lines]
            preview_content = "".join(preview_lines)

            # 통계 정보
            total_lines = len(lines)
            total_chars = sum(len(line) for line in lines)

            return {
                "type": "text",
                "preview_available": True,
                "content": preview_content,
                "encoding": encoding,
                "file_size": file_size,
                "total_lines": total_lines,
                "preview_lines": len(preview_lines),
                "total_chars": total_chars,
                "truncated": total_lines > self.max_preview_lines,
            }

        except Exception as e:
            logger.error(f"텍스트 미리보기 생성 실패: {e}")
            return {
                "type": "text",
                "preview_available": False,
                "reason": f"미리보기 생성 실패: {str(e)}",
            }

    async def generate_thumbnail(
        self, image_path: Path, size: str = "medium", format: str = "webp"
    ) -> Optional[Path]:
        """이미지 썸네일 생성"""
        try:
            if size not in self.thumbnail_sizes:
                size = "medium"

            width, height = self.thumbnail_sizes[size]

            # 원본 이미지 열기
            with Image.open(image_path) as img:
                # 이미지 모드 변환 (RGBA -> RGB)
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # 썸네일 생성 (비율 유지)
                img.thumbnail((width, height), Image.Resampling.LANCZOS)

                # 썸네일 저장 경로 생성
                thumbnail_dir = Path("thumbnails") / size
                thumbnail_dir.mkdir(parents=True, exist_ok=True)

                thumbnail_path = thumbnail_dir / f"{image_path.stem}_{size}.{format}"

                # 썸네일 저장
                if format.lower() == "webp":
                    img.save(thumbnail_path, "WEBP", quality=85, optimize=True)
                elif format.lower() == "jpeg":
                    img.save(thumbnail_path, "JPEG", quality=85, optimize=True)
                elif format.lower() == "png":
                    img.save(thumbnail_path, "PNG", optimize=True)
                else:
                    img.save(thumbnail_path, "WEBP", quality=85, optimize=True)

                return thumbnail_path

        except Exception as e:
            logger.error(f"썸네일 생성 실패: {e}")
            return None

    async def get_image_preview(self, file_path: Path) -> Dict:
        """이미지 파일 미리보기"""
        try:
            # 이미지 정보 가져오기
            with Image.open(file_path) as img:
                width, height = img.size
                format = img.format
                mode = img.mode

                # 파일 크기
                file_size = file_path.stat().st_size

                # 썸네일 생성 (백그라운드)
                thumbnail_task = asyncio.create_task(
                    self.generate_thumbnail(file_path, "medium", "webp")
                )

                return {
                    "type": "image",
                    "preview_available": True,
                    "width": width,
                    "height": height,
                    "format": format,
                    "mode": mode,
                    "file_size": file_size,
                    "thumbnail_task": thumbnail_task,
                }

        except Exception as e:
            logger.error(f"이미지 미리보기 생성 실패: {e}")
            return {
                "type": "image",
                "preview_available": False,
                "reason": f"이미지 처리 실패: {str(e)}",
            }

    async def get_file_preview(self, file_path: Path, filename: str) -> Dict:
        """파일 미리보기 생성"""
        try:
            if not file_path.exists():
                raise FileNotFoundError("파일이 존재하지 않습니다")

            if self.is_text_file(filename):
                return await self.get_text_preview(file_path)
            elif self.is_image_file(filename):
                return await self.get_image_preview(file_path)
            else:
                # 지원하지 않는 파일 타입
                file_size = file_path.stat().st_size
                return {
                    "type": "unknown",
                    "preview_available": False,
                    "reason": "지원하지 않는 파일 타입입니다",
                    "file_size": file_size,
                }

        except Exception as e:
            logger.error(f"파일 미리보기 생성 실패: {e}")
            return {
                "type": "unknown",
                "preview_available": False,
                "reason": f"미리보기 생성 실패: {str(e)}",
            }

    async def cache_thumbnail(self, file_id: str, thumbnail_path: Path, size: str):
        """썸네일 경로를 Redis에 캐시"""
        try:
            redis_client = await get_async_redis_client()
            cache_key = f"thumbnail:{file_id}:{size}"
            await redis_client.set_with_ttl(
                cache_key, str(thumbnail_path), 3600
            )  # 1시간
        except Exception as e:
            logger.error(f"썸네일 캐시 저장 실패: {e}")

    async def get_cached_thumbnail(self, file_id: str, size: str) -> Optional[Path]:
        """Redis에서 썸네일 경로 조회"""
        try:
            redis_client = await get_async_redis_client()
            cache_key = f"thumbnail:{file_id}:{size}"
            thumbnail_path = await redis_client.get(cache_key)

            if thumbnail_path:
                path = Path(thumbnail_path)
                if path.exists():
                    return path
                else:
                    # 파일이 존재하지 않으면 캐시에서 제거
                    await redis_client.delete(cache_key)

            return None
        except Exception as e:
            logger.error(f"썸네일 캐시 조회 실패: {e}")
            return None


# 전역 인스턴스
file_preview_service = FilePreviewService()
