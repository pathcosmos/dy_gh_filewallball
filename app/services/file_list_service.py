"""
파일 목록 조회 및 검색 서비스
Task 11: 파일 목록 조회 및 검색 API
"""

import asyncio
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import asc, desc, func, text
from sqlalchemy.orm import Session

# Redis 클라이언트 제거됨
from app.database import get_db
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class SortBy(str, Enum):
    """정렬 기준"""

    UPLOAD_TIME = "upload_time"
    FILENAME = "filename"
    SIZE = "size"
    CONTENT_TYPE = "content_type"


class SortOrder(str, Enum):
    """정렬 순서"""

    ASC = "asc"
    DESC = "desc"


class FileListService:
    """파일 목록 조회 및 검색 서비스"""

    def __init__(self):
        self.cache_ttl = 300  # 5분
        self.max_page_size = 200
        self.default_page_size = 50

    async def get_file_list(
        self,
        page: int = 1,
        size: int = 50,
        sort_by: SortBy = SortBy.UPLOAD_TIME,
        sort_order: SortOrder = SortOrder.DESC,
        file_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        filename_search: Optional[str] = None,
        user_id: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """파일 목록 조회"""
        try:
            # 페이지 크기 제한
            size = min(size, self.max_page_size)

            # 캐시 키 생성
            cache_key = self._generate_cache_key(
                page,
                size,
                sort_by,
                sort_order,
                file_type,
                date_from,
                date_to,
                min_size,
                max_size,
                filename_search,
                user_id,
                include_deleted,
            )

            # Redis 캐시에서 조회
            redis_client = await get_async_redis_client()
            cached_result = await redis_client.get(cache_key)

            if cached_result:
                return json.loads(cached_result)

            # DB에서 조회
            result = await self._query_files_from_db(
                page,
                size,
                sort_by,
                sort_order,
                file_type,
                date_from,
                date_to,
                min_size,
                max_size,
                filename_search,
                user_id,
                include_deleted,
            )

            # 결과를 캐시에 저장
            await redis_client.set_with_ttl(
                cache_key, json.dumps(result), self.cache_ttl
            )

            return result

        except Exception as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            raise

    async def _query_files_from_db(
        self,
        page: int,
        size: int,
        sort_by: SortBy,
        sort_order: SortOrder,
        file_type: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        min_size: Optional[int],
        max_size: Optional[int],
        filename_search: Optional[str],
        user_id: Optional[str],
        include_deleted: bool,
    ) -> Dict[str, Any]:
        """DB에서 파일 목록 조회"""
        try:
            # DB 세션 생성
            db = next(get_db())

            # 기본 쿼리 (Redis에서 파일 정보 조회)
            # 실제로는 DB 테이블이 있다면 SQLAlchemy ORM 사용
            # 현재는 Redis 기반이므로 Redis에서 조회

            # Redis에서 모든 파일 키 조회
            redis_client = await get_async_redis_client()
            file_keys = await redis_client.keys("file:*")

            # 파일 정보 파싱
            files = []
            for key in file_keys:
                try:
                    file_data = await redis_client.get(key)
                    if file_data:
                        file_info = eval(file_data)  # ast.literal_eval 대신 eval 사용

                        # 필터링 적용
                        if not self._apply_filters(
                            file_info,
                            file_type,
                            date_from,
                            date_to,
                            min_size,
                            max_size,
                            filename_search,
                            user_id,
                            include_deleted,
                        ):
                            continue

                        files.append(file_info)

                except Exception as e:
                    logger.warning(f"파일 정보 파싱 실패: {e}")
                    continue

            # 정렬 적용
            files = self._sort_files(files, sort_by, sort_order)

            # 페이지네이션 적용
            total_count = len(files)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_files = files[start_idx:end_idx]

            # URL 생성
            base_url = "http://localhost:8000"  # 환경변수에서 가져오기
            for file_info in paginated_files:
                file_id = file_info["file_id"]
                file_info["download_url"] = f"{base_url}/download/{file_id}"
                file_info["view_url"] = f"{base_url}/view/{file_id}"
                file_info["thumbnail_url"] = f"{base_url}/thumbnails/{file_id}"

            return {
                "items": paginated_files,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_count": total_count,
                    "total_pages": (total_count + size - 1) // size,
                    "has_next": page * size < total_count,
                    "has_prev": page > 1,
                },
                "filters": {
                    "file_type": file_type,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                    "min_size": min_size,
                    "max_size": max_size,
                    "filename_search": filename_search,
                    "user_id": user_id,
                },
                "sorting": {"sort_by": sort_by.value, "sort_order": sort_order.value},
            }

        except Exception as e:
            logger.error(f"DB 쿼리 실패: {e}")
            raise
        finally:
            db.close()

    def _apply_filters(
        self,
        file_info: Dict[str, Any],
        file_type: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        min_size: Optional[int],
        max_size: Optional[int],
        filename_search: Optional[str],
        user_id: Optional[str],
        include_deleted: bool,
    ) -> bool:
        """파일 필터링 적용"""
        try:
            # 파일 타입 필터
            if (
                file_type
                and file_info.get("content_type", "").split("/")[0] != file_type
            ):
                return False

            # 날짜 범위 필터
            if date_from or date_to:
                upload_time = datetime.fromisoformat(file_info.get("upload_time", ""))
                if date_from and upload_time < date_from:
                    return False
                if date_to and upload_time > date_to:
                    return False

            # 크기 범위 필터
            file_size = file_info.get("size", 0)
            if min_size and file_size < min_size:
                return False
            if max_size and file_size > max_size:
                return False

            # 파일명 검색 필터
            if filename_search:
                filename = file_info.get("filename", "").lower()
                if filename_search.lower() not in filename:
                    return False

            # 사용자 ID 필터
            if user_id and file_info.get("user_id") != user_id:
                return False

            # 삭제된 파일 필터
            if not include_deleted and file_info.get("deleted", False):
                return False

            return True

        except Exception as e:
            logger.warning(f"필터 적용 실패: {e}")
            return False

    def _sort_files(
        self, files: List[Dict[str, Any]], sort_by: SortBy, sort_order: SortOrder
    ) -> List[Dict[str, Any]]:
        """파일 정렬"""
        try:
            reverse = sort_order == SortOrder.DESC

            if sort_by == SortBy.UPLOAD_TIME:
                files.sort(
                    key=lambda x: datetime.fromisoformat(x.get("upload_time", "")),
                    reverse=reverse,
                )
            elif sort_by == SortBy.FILENAME:
                files.sort(key=lambda x: x.get("filename", "").lower(), reverse=reverse)
            elif sort_by == SortBy.SIZE:
                files.sort(key=lambda x: x.get("size", 0), reverse=reverse)
            elif sort_by == SortBy.CONTENT_TYPE:
                files.sort(key=lambda x: x.get("content_type", ""), reverse=reverse)

            return files

        except Exception as e:
            logger.warning(f"정렬 실패: {e}")
            return files

    def _generate_cache_key(
        self,
        page: int,
        size: int,
        sort_by: SortBy,
        sort_order: SortOrder,
        file_type: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        min_size: Optional[int],
        max_size: Optional[int],
        filename_search: Optional[str],
        user_id: Optional[str],
        include_deleted: bool,
    ) -> str:
        """캐시 키 생성"""
        key_parts = [
            "file_list",
            f"page_{page}",
            f"size_{size}",
            f"sort_{sort_by.value}_{sort_order.value}",
            f"type_{file_type}" if file_type else "type_all",
            f"from_{date_from.isoformat()}" if date_from else "from_none",
            f"to_{date_to.isoformat()}" if date_to else "to_none",
            f"min_{min_size}" if min_size else "min_none",
            f"max_{max_size}" if max_size else "max_none",
            f"search_{filename_search}" if filename_search else "search_none",
            f"user_{user_id}" if user_id else "user_all",
            f"deleted_{include_deleted}",
        ]

        return ":".join(key_parts)

    async def get_file_statistics(
        self, user_id: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """파일 통계 조회"""
        try:
            # Redis에서 모든 파일 키 조회
            redis_client = await get_async_redis_client()
            file_keys = await redis_client.keys("file:*")

            # 날짜 범위 계산
            cutoff_date = datetime.now() - timedelta(days=days)

            # 통계 데이터 초기화
            stats = {
                "total_files": 0,
                "total_size": 0,
                "file_types": {},
                "daily_uploads": {},
                "size_ranges": {
                    "small": 0,  # < 1MB
                    "medium": 0,  # 1MB - 10MB
                    "large": 0,  # 10MB - 100MB
                    "huge": 0,  # > 100MB
                },
                "top_uploaders": {},
                "recent_uploads": [],
            }

            # 파일 분석
            for key in file_keys:
                try:
                    file_data = await redis_client.get(key)
                    if file_data:
                        file_info = eval(file_data)

                        # 사용자 필터
                        if user_id and file_info.get("user_id") != user_id:
                            continue

                        # 날짜 필터
                        upload_time = datetime.fromisoformat(
                            file_info.get("upload_time", "")
                        )
                        if upload_time < cutoff_date:
                            continue

                        # 기본 통계
                        stats["total_files"] += 1
                        file_size = file_info.get("size", 0)
                        stats["total_size"] += file_size

                        # 파일 타입 통계
                        content_type = file_info.get("content_type", "unknown")
                        file_type = content_type.split("/")[0]
                        stats["file_types"][file_type] = (
                            stats["file_types"].get(file_type, 0) + 1
                        )

                        # 일별 업로드 통계
                        date_key = upload_time.strftime("%Y-%m-%d")
                        stats["daily_uploads"][date_key] = (
                            stats["daily_uploads"].get(date_key, 0) + 1
                        )

                        # 크기 범위 통계
                        if file_size < 1024 * 1024:  # < 1MB
                            stats["size_ranges"]["small"] += 1
                        elif file_size < 10 * 1024 * 1024:  # < 10MB
                            stats["size_ranges"]["medium"] += 1
                        elif file_size < 100 * 1024 * 1024:  # < 100MB
                            stats["size_ranges"]["large"] += 1
                        else:
                            stats["size_ranges"]["huge"] += 1

                        # 상위 업로더 통계
                        uploader_id = file_info.get("user_id", "anonymous")
                        stats["top_uploaders"][uploader_id] = (
                            stats["top_uploaders"].get(uploader_id, 0) + 1
                        )

                        # 최근 업로드 (최대 10개)
                        if len(stats["recent_uploads"]) < 10:
                            stats["recent_uploads"].append(
                                {
                                    "file_id": file_info.get("file_id"),
                                    "filename": file_info.get("filename"),
                                    "upload_time": file_info.get("upload_time"),
                                    "size": file_size,
                                }
                            )

                except Exception as e:
                    logger.warning(f"파일 통계 분석 실패: {e}")
                    continue

            # 최근 업로드 정렬
            stats["recent_uploads"].sort(
                key=lambda x: datetime.fromisoformat(x["upload_time"]), reverse=True
            )

            # 상위 업로더 정렬 (상위 10개)
            stats["top_uploaders"] = dict(
                sorted(
                    stats["top_uploaders"].items(), key=lambda x: x[1], reverse=True
                )[:10]
            )

            return stats

        except Exception as e:
            logger.error(f"파일 통계 조회 실패: {e}")
            return {
                "total_files": 0,
                "total_size": 0,
                "file_types": {},
                "daily_uploads": {},
                "size_ranges": {"small": 0, "medium": 0, "large": 0, "huge": 0},
                "top_uploaders": {},
                "recent_uploads": [],
            }

    async def search_files(
        self,
        query: str,
        page: int = 1,
        size: int = 50,
        search_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """파일 검색"""
        try:
            if not search_fields:
                search_fields = ["filename", "content_type"]

            # Redis에서 모든 파일 키 조회
            redis_client = await get_async_redis_client()
            file_keys = await redis_client.keys("file:*")

            # 검색 결과
            search_results = []

            for key in file_keys:
                try:
                    file_data = await redis_client.get(key)
                    if file_data:
                        file_info = eval(file_data)

                        # 검색 필드 확인
                        match_found = False
                        for field in search_fields:
                            if field in file_info:
                                field_value = str(file_info[field]).lower()
                                if query.lower() in field_value:
                                    match_found = True
                                    break

                        if match_found:
                            search_results.append(file_info)

                except Exception as e:
                    logger.warning(f"파일 검색 실패: {e}")
                    continue

            # 페이지네이션 적용
            total_count = len(search_results)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_results = search_results[start_idx:end_idx]

            # URL 생성
            base_url = "http://localhost:8000"
            for file_info in paginated_results:
                file_id = file_info["file_id"]
                file_info["download_url"] = f"{base_url}/download/{file_id}"
                file_info["view_url"] = f"{base_url}/view/{file_id}"
                file_info["thumbnail_url"] = f"{base_url}/thumbnails/{file_id}"

            return {
                "items": paginated_results,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_count": total_count,
                    "total_pages": (total_count + size - 1) // size,
                    "has_next": page * size < total_count,
                    "has_prev": page > 1,
                },
                "search": {
                    "query": query,
                    "search_fields": search_fields,
                    "results_count": total_count,
                },
            }

        except Exception as e:
            logger.error(f"파일 검색 실패: {e}")
            return {
                "items": [],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False,
                },
                "search": {
                    "query": query,
                    "search_fields": search_fields,
                    "results_count": 0,
                },
            }

    async def invalidate_cache(self, pattern: str = "file_list:*"):
        """캐시 무효화"""
        try:
            redis_client = await get_async_redis_client()
            keys = await redis_client.keys(pattern)

            if keys:
                await redis_client.delete(*keys)
                logger.info(f"캐시 무효화 완료: {len(keys)}개 키 삭제")

            return len(keys)

        except Exception as e:
            logger.error(f"캐시 무효화 실패: {e}")
            return 0


# 전역 인스턴스
file_list_service = FileListService()
