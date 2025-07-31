"""
썸네일 생성 및 관리 서비스 모듈
Task 8.7: 이미지 썸네일 생성 및 제공 API 구현
Pillow를 사용한 이미지 리사이징 및 썸네일 캐싱
"""

import hashlib
import os
from typing import Optional, Tuple

from PIL import Image

from app.dependencies.settings import get_app_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_app_settings()


class ThumbnailService:
    """썸네일 생성 및 관리 서비스 클래스 - Task 8.7"""

    def __init__(self):
        # Task 8.7: 썸네일 크기 정의
        self.thumbnail_sizes = {
            "small": (150, 150),
            "medium": (300, 300),
            "large": (500, 500),
        }

        # Task 8.7: 썸네일 저장 디렉토리 설정
        self.thumbnail_dir = os.path.join(settings.upload_dir, "thumbnails")
        self._ensure_thumbnail_dir()

    def _ensure_thumbnail_dir(self):
        """썸네일 디렉토리 생성"""
        if not os.path.exists(self.thumbnail_dir):
            os.makedirs(self.thumbnail_dir, exist_ok=True)
            logger.info(f"Created thumbnail directory: {self.thumbnail_dir}")

    def _get_thumbnail_path(self, file_uuid: str, size: str) -> str:
        """썸네일 파일 경로 생성"""
        # 파일 UUID와 크기를 기반으로 고유한 썸네일 파일명 생성
        thumbnail_filename = f"{file_uuid}_{size}.jpg"
        return os.path.join(self.thumbnail_dir, thumbnail_filename)

    def _generate_thumbnail_hash(self, original_path: str, size: str) -> str:
        """원본 파일과 크기를 기반으로 썸네일 해시 생성"""
        # 파일 수정 시간과 크기를 포함한 해시 생성
        stat = os.stat(original_path)
        hash_input = f"{original_path}_{stat.st_mtime}_{stat.st_size}_{size}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def create_thumbnail(
        self, original_path: str, file_uuid: str, size: str = "medium"
    ) -> Optional[str]:
        """
        이미지 썸네일 생성

        Args:
            original_path: 원본 이미지 파일 경로
            file_uuid: 파일 UUID
            size: 썸네일 크기 (small, medium, large)

        Returns:
            Optional[str]: 생성된 썸네일 파일 경로
        """
        try:
            if size not in self.thumbnail_sizes:
                raise ValueError(f"Unsupported thumbnail size: {size}")

            thumbnail_path = self._get_thumbnail_path(file_uuid, size)
            target_size = self.thumbnail_sizes[size]

            # 원본 이미지 열기
            with Image.open(original_path) as img:
                # RGB 모드로 변환 (JPEG 저장을 위해)
                if img.mode in ("RGBA", "LA", "P"):
                    # 투명도가 있는 이미지는 흰색 배경으로 변환
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1] if img.mode == "RGBA" else None
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # 비율을 유지하면서 리사이징
                img.thumbnail(target_size, Image.Resampling.LANCZOS)

                # 썸네일 저장
                img.save(thumbnail_path, "JPEG", quality=85, optimize=True)

                logger.info(f"Thumbnail created: {thumbnail_path}, size: {img.size}")
                return thumbnail_path

        except Exception as e:
            logger.error(f"Failed to create thumbnail for {file_uuid}: {e}")
            return None

    def get_thumbnail(
        self, original_path: str, file_uuid: str, size: str = "medium"
    ) -> Optional[str]:
        """
        썸네일 가져오기 (캐시 확인 후 필요시 생성)

        Args:
            original_path: 원본 이미지 파일 경로
            file_uuid: 파일 UUID
            size: 썸네일 크기

        Returns:
            Optional[str]: 썸네일 파일 경로
        """
        try:
            thumbnail_path = self._get_thumbnail_path(file_uuid, size)

            # 썸네일이 이미 존재하는지 확인
            if os.path.exists(thumbnail_path):
                # 원본 파일이 변경되었는지 확인
                original_hash = self._generate_thumbnail_hash(original_path, size)
                thumbnail_hash_file = f"{thumbnail_path}.hash"

                if os.path.exists(thumbnail_hash_file):
                    with open(thumbnail_hash_file, "r") as f:
                        stored_hash = f.read().strip()

                    if stored_hash == original_hash:
                        logger.info(f"Using cached thumbnail: {thumbnail_path}")
                        return thumbnail_path

                # 해시가 다르면 기존 썸네일 삭제
                os.remove(thumbnail_path)
                if os.path.exists(thumbnail_hash_file):
                    os.remove(thumbnail_hash_file)

            # 새로운 썸네일 생성
            thumbnail_path = self.create_thumbnail(original_path, file_uuid, size)
            if thumbnail_path:
                # 해시 파일 저장
                original_hash = self._generate_thumbnail_hash(original_path, size)
                hash_file_path = f"{thumbnail_path}.hash"
                with open(hash_file_path, "w") as f:
                    f.write(original_hash)

                logger.info(f"New thumbnail created and cached: {thumbnail_path}")
                return thumbnail_path

            return None

        except Exception as e:
            logger.error(f"Failed to get thumbnail for {file_uuid}: {e}")
            return None

    def delete_thumbnail(self, file_uuid: str, size: str = None):
        """
        썸네일 삭제

        Args:
            file_uuid: 파일 UUID
            size: 특정 크기만 삭제 (None이면 모든 크기 삭제)
        """
        try:
            if size:
                # 특정 크기만 삭제
                thumbnail_path = self._get_thumbnail_path(file_uuid, size)
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
                    hash_file = f"{thumbnail_path}.hash"
                    if os.path.exists(hash_file):
                        os.remove(hash_file)
                    logger.info(f"Deleted thumbnail: {thumbnail_path}")
            else:
                # 모든 크기 삭제
                for size_name in self.thumbnail_sizes.keys():
                    thumbnail_path = self._get_thumbnail_path(file_uuid, size_name)
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                        hash_file = f"{thumbnail_path}.hash"
                        if os.path.exists(hash_file):
                            os.remove(hash_file)
                        logger.info(f"Deleted thumbnail: {thumbnail_path}")

        except Exception as e:
            logger.error(f"Failed to delete thumbnail for {file_uuid}: {e}")

    def get_thumbnail_info(self, file_uuid: str) -> dict:
        """
        썸네일 정보 조회

        Args:
            file_uuid: 파일 UUID

        Returns:
            dict: 썸네일 정보
        """
        info = {"file_uuid": file_uuid, "available_sizes": [], "total_size": 0}

        try:
            for size_name in self.thumbnail_sizes.keys():
                thumbnail_path = self._get_thumbnail_path(file_uuid, size_name)
                if os.path.exists(thumbnail_path):
                    info["available_sizes"].append(size_name)
                    info["total_size"] += os.path.getsize(thumbnail_path)

            return info

        except Exception as e:
            logger.error(f"Failed to get thumbnail info for {file_uuid}: {e}")
            return info


# 전역 썸네일 서비스 인스턴스
thumbnail_service = ThumbnailService()
