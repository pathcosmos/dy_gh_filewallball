"""
Rate Limiting 서비스
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import redis
from fastapi import HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.orm_models import FileUpload


class RateLimiterService:
    """Rate Limiting 서비스 클래스"""

    def __init__(self, db_session: Session, redis_client: redis.Redis):
        self.db_session = db_session
        self.redis_client = redis_client
        self.default_limits = {
            "uploads_per_hour": 100,
            "uploads_per_day": 1000,
            "max_file_size": 100 * 1024 * 1024,  # 100MB
            "concurrent_uploads": 5,
        }

    def get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # 프록시 환경 고려
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host

    def is_rate_limited(
        self, client_ip: str, limit_type: str = "uploads_per_hour"
    ) -> Tuple[bool, Dict]:
        """
        Rate limiting 확인

        Args:
            client_ip: 클라이언트 IP 주소
            limit_type: 제한 타입 (uploads_per_hour, uploads_per_day, etc.)

        Returns:
            (제한 여부, 제한 정보) 튜플
        """
        try:
            # Redis 키 생성
            current_time = int(time.time())

            if limit_type == "uploads_per_hour":
                window_start = current_time - 3600  # 1시간
                limit = self.default_limits["uploads_per_hour"]
                key = f"rate_limit:{client_ip}:hour:{current_time // 3600}"
            elif limit_type == "uploads_per_day":
                window_start = current_time - 86400  # 24시간
                limit = self.default_limits["uploads_per_day"]
                key = f"rate_limit:{client_ip}:day:{current_time // 86400}"
            else:
                return False, {}

            # 현재 요청 수 확인
            current_count = self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0

            # 제한 확인
            is_limited = current_count >= limit

            # 남은 요청 수 계산
            remaining = max(0, limit - current_count)

            # 제한 정보
            limit_info = {
                "limit": limit,
                "remaining": remaining,
                "reset_time": (
                    window_start + 3600
                    if limit_type == "uploads_per_hour"
                    else window_start + 86400
                ),
                "current_count": current_count,
            }

            return is_limited, limit_info

        except Exception as e:
            # Redis 오류 시 제한하지 않음
            print(f"Rate limiting 오류: {e}")
            return False, {}

    def increment_request_count(
        self, client_ip: str, limit_type: str = "uploads_per_hour"
    ):
        """요청 카운트 증가"""
        try:
            current_time = int(time.time())

            if limit_type == "uploads_per_hour":
                key = f"rate_limit:{client_ip}:hour:{current_time // 3600}"
                expire_time = 3600  # 1시간
            elif limit_type == "uploads_per_day":
                key = f"rate_limit:{client_ip}:day:{current_time // 86400}"
                expire_time = 86400  # 24시간
            else:
                return

            # 카운트 증가
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, expire_time)
            pipe.execute()

        except Exception as e:
            print(f"Rate limiting 카운트 증가 오류: {e}")

    def check_file_size_limit(self, file_size: int, client_ip: str) -> bool:
        """파일 크기 제한 확인"""
        try:
            # IP별 파일 크기 제한 확인 (향후 확장 가능)
            max_size = self.default_limits["max_file_size"]

            # 데이터베이스에서 IP별 설정 확인
            # TODO: IP별 설정 테이블 구현 시 여기서 조회

            return file_size <= max_size

        except Exception as e:
            print(f"파일 크기 제한 확인 오류: {e}")
            return True  # 오류 시 허용

    def check_concurrent_uploads(self, client_ip: str) -> bool:
        """동시 업로드 제한 확인"""
        try:
            key = f"concurrent_uploads:{client_ip}"
            current_count = self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0

            limit = self.default_limits["concurrent_uploads"]
            return current_count < limit

        except Exception as e:
            print(f"동시 업로드 제한 확인 오류: {e}")
            return True  # 오류 시 허용

    def start_upload_session(self, client_ip: str):
        """업로드 세션 시작"""
        try:
            key = f"concurrent_uploads:{client_ip}"
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 300)  # 5분 만료
            pipe.execute()

        except Exception as e:
            print(f"업로드 세션 시작 오류: {e}")

    def end_upload_session(self, client_ip: str):
        """업로드 세션 종료"""
        try:
            key = f"concurrent_uploads:{client_ip}"
            current_count = self.redis_client.get(key)
            if current_count:
                count = int(current_count)
                if count > 1:
                    self.redis_client.decr(key)
                else:
                    self.redis_client.delete(key)

        except Exception as e:
            print(f"업로드 세션 종료 오류: {e}")

    def get_upload_statistics(self, client_ip: str, days: int = 7) -> Dict:
        """업로드 통계 조회"""
        try:
            # 데이터베이스에서 업로드 통계 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 일별 업로드 수
            daily_stats = (
                self.db_session.query(
                    func.date(FileUpload.upload_time).label("date"),
                    func.count(FileUpload.id).label("count"),
                    func.sum(FileUpload.file_size).label("total_size"),
                )
                .filter(
                    FileUpload.upload_ip == client_ip,
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_time <= end_date,
                )
                .group_by(func.date(FileUpload.upload_time))
                .all()
            )

            # 전체 통계
            total_uploads = (
                self.db_session.query(func.count(FileUpload.id))
                .filter(
                    FileUpload.upload_ip == client_ip,
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_time <= end_date,
                )
                .scalar()
            )

            total_size = (
                self.db_session.query(func.sum(FileUpload.file_size))
                .filter(
                    FileUpload.upload_ip == client_ip,
                    FileUpload.upload_time >= start_date,
                    FileUpload.upload_time <= end_date,
                )
                .scalar()
                or 0
            )

            return {
                "client_ip": client_ip,
                "period_days": days,
                "total_uploads": total_uploads,
                "total_size": total_size,
                "daily_stats": [
                    {
                        "date": stat.date.isoformat(),
                        "count": stat.count,
                        "total_size": stat.total_size or 0,
                    }
                    for stat in daily_stats
                ],
            }

        except Exception as e:
            print(f"업로드 통계 조회 오류: {e}")
            return {
                "client_ip": client_ip,
                "period_days": days,
                "total_uploads": 0,
                "total_size": 0,
                "daily_stats": [],
            }

    def get_rate_limit_headers(self, client_ip: str) -> Dict[str, str]:
        """Rate limit 헤더 생성"""
        try:
            # 시간별 제한 확인
            is_hour_limited, hour_info = self.is_rate_limited(
                client_ip, "uploads_per_hour"
            )
            is_day_limited, day_info = self.is_rate_limited(
                client_ip, "uploads_per_day"
            )

            headers = {
                "X-RateLimit-Hour-Limit": str(hour_info.get("limit", 0)),
                "X-RateLimit-Hour-Remaining": str(hour_info.get("remaining", 0)),
                "X-RateLimit-Hour-Reset": str(hour_info.get("reset_time", 0)),
                "X-RateLimit-Day-Limit": str(day_info.get("limit", 0)),
                "X-RateLimit-Day-Remaining": str(day_info.get("remaining", 0)),
                "X-RateLimit-Day-Reset": str(day_info.get("reset_time", 0)),
            }

            return headers

        except Exception as e:
            print(f"Rate limit 헤더 생성 오류: {e}")
            return {}
