"""
캐시 무효화 및 동기화 서비스 모듈
Task 7.3: 캐시 무효화 및 동기화 메커니즘 구현
Redis Pub/Sub을 활용한 분산 환경 캐시 동기화
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from app.services.cache_service import CacheService
from app.services.redis_connection_manager import get_redis_manager

logger = logging.getLogger(__name__)


class CacheInvalidationService:
    """캐시 무효화 및 동기화 서비스 클래스 - Task 7.3"""

    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.client = self.redis_manager.get_client()
        self.cache_service = CacheService()

        # Task 7.3: Pub/Sub 채널 설정
        self.pubsub_channels = {
            "cache_invalidation": "cache:invalidation",
            "cache_sync": "cache:sync",
            "cache_recovery": "cache:recovery",
        }

        # Task 7.3: 캐시 태그 관리
        self.cache_tags = {
            "file_info": "tag:file_info",
            "file_meta": "tag:file_meta",
            "file_stats": "tag:file_stats",
            "user_data": "tag:user_data",
            "system_config": "tag:system_config",
        }

        # Task 7.3: 무효화 이벤트 타입
        self.invalidation_events = {
            "file_updated": "file_updated",
            "file_deleted": "file_deleted",
            "file_metadata_changed": "file_metadata_changed",
            "user_data_changed": "user_data_changed",
            "system_config_changed": "system_config_changed",
            "bulk_invalidation": "bulk_invalidation",
        }

        # Task 7.3: Pub/Sub 구독자 관리
        self.pubsub = None
        self.subscription_handlers: Dict[str, Callable] = {}
        self.is_listening = False

        # Task 7.3: 트랜잭션 롤백 추적
        self.transaction_cache_ops: Dict[str, List[Dict]] = {}

        # Task 7.3: 무효화 이벤트 로그
        self.invalidation_log: List[Dict] = []
        self.max_log_size = 1000

    async def start_listening(self):
        """Pub/Sub 리스닝 시작"""
        if self.is_listening:
            return

        try:
            self.pubsub = self.client.pubsub()

            # 모든 채널 구독
            for channel_name in self.pubsub_channels.values():
                await self.pubsub.subscribe(channel_name)
                logger.info(f"캐시 무효화 채널 구독: {channel_name}")

            self.is_listening = True

            # 백그라운드에서 메시지 처리
            asyncio.create_task(self._process_messages())

            logger.info("캐시 무효화 Pub/Sub 리스닝 시작")

        except Exception as e:
            logger.error(f"Pub/Sub 리스닝 시작 실패: {e}")
            self.is_listening = False

    async def stop_listening(self):
        """Pub/Sub 리스닝 중지"""
        if not self.is_listening or not self.pubsub:
            return

        try:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
            self.is_listening = False
            logger.info("캐시 무효화 Pub/Sub 리스닝 중지")

        except Exception as e:
            logger.error(f"Pub/Sub 리스닝 중지 실패: {e}")

    async def _process_messages(self):
        """Pub/Sub 메시지 처리"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_invalidation_message(message)

        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {e}")
            self.is_listening = False

    async def _handle_invalidation_message(self, message: Dict):
        """무효화 메시지 처리"""
        try:
            channel = message["channel"]
            data = json.loads(message["data"])

            event_type = data.get("event_type")
            target_keys = data.get("target_keys", [])
            tags = data.get("tags", [])
            timestamp = data.get("timestamp")

            logger.info(f"캐시 무효화 이벤트 수신: {event_type}")

            # 키 기반 무효화
            if target_keys:
                await self._invalidate_keys(target_keys)

            # 태그 기반 무효화
            if tags:
                await self._invalidate_by_tags(tags)

            # 이벤트 로그 기록
            self._log_invalidation_event(event_type, target_keys, tags, timestamp)

        except Exception as e:
            logger.error(f"무효화 메시지 처리 실패: {e}")

    async def publish_invalidation_event(
        self,
        event_type: str,
        target_keys: List[str] = None,
        tags: List[str] = None,
        channel: str = "cache_invalidation",
    ):
        """
        무효화 이벤트 발행

        Args:
            event_type: 이벤트 타입
            target_keys: 무효화할 키 목록
            tags: 무효화할 태그 목록
            channel: 발행할 채널
        """
        try:
            event_data = {
                "event_type": event_type,
                "target_keys": target_keys or [],
                "tags": tags or [],
                "timestamp": datetime.utcnow().isoformat(),
                "source": "cache_invalidation_service",
            }

            channel_name = self.pubsub_channels.get(channel, channel)
            await self.redis_manager.execute_with_retry(
                self.client.publish, channel_name, json.dumps(event_data)
            )

            logger.info(f"캐시 무효화 이벤트 발행: {event_type}")

        except Exception as e:
            logger.error(f"무효화 이벤트 발행 실패: {e}")

    async def invalidate_file_cache(
        self, file_uuid: str, event_type: str = "file_updated"
    ):
        """
        파일 캐시 무효화 (로컬 + 분산)

        Args:
            file_uuid: 파일 UUID
            event_type: 이벤트 타입
        """
        try:
            # 로컬 캐시 무효화
            await self.cache_service.invalidate_file_cache(file_uuid)

            # 분산 환경에 이벤트 발행
            target_keys = [
                f"file:info:{file_uuid}",
                f"file:meta:{file_uuid}",
                f"file:stats:{file_uuid}",
                f"file:access:{file_uuid}",
            ]

            tags = ["file_info", "file_meta", "file_stats"]

            await self.publish_invalidation_event(
                event_type=event_type, target_keys=target_keys, tags=tags
            )

            logger.info(f"파일 캐시 무효화 완료: {file_uuid}")

        except Exception as e:
            logger.error(f"파일 캐시 무효화 실패: {e}")

    async def _invalidate_keys(self, keys: List[str]):
        """키 목록 무효화"""
        try:
            for key in keys:
                await self.cache_service.delete(key)

            logger.info(f"키 기반 캐시 무효화 완료: {len(keys)}개 키")

        except Exception as e:
            logger.error(f"키 기반 캐시 무효화 실패: {e}")

    async def _invalidate_by_tags(self, tags: List[str]):
        """태그 기반 캐시 무효화"""
        try:
            for tag in tags:
                tag_key = self.cache_tags.get(tag)
                if tag_key:
                    # 태그와 연결된 모든 키 조회
                    pattern = f"{tag_key}:*"
                    keys = await self.redis_manager.execute_with_retry(
                        self.client.keys, pattern
                    )

                    if keys:
                        await self._invalidate_keys(keys)
                        logger.info(
                            f"태그 기반 캐시 무효화 완료: {tag}, {len(keys)}개 키"
                        )

        except Exception as e:
            logger.error(f"태그 기반 캐시 무효화 실패: {e}")

    async def add_cache_tag(self, key: str, tag: str):
        """
        캐시 키에 태그 추가

        Args:
            key: 캐시 키
            tag: 태그명
        """
        try:
            tag_key = self.cache_tags.get(tag)
            if tag_key:
                tagged_key = f"{tag_key}:{key}"
                await self.redis_manager.execute_with_retry(
                    self.client.set, tagged_key, "1", ex=3600
                )

        except Exception as e:
            logger.error(f"캐시 태그 추가 실패: {e}")

    async def remove_cache_tag(self, key: str, tag: str):
        """
        캐시 키에서 태그 제거

        Args:
            key: 캐시 키
            tag: 태그명
        """
        try:
            tag_key = self.cache_tags.get(tag)
            if tag_key:
                tagged_key = f"{tag_key}:{key}"
                await self.cache_service.delete(tagged_key)

        except Exception as e:
            logger.error(f"캐시 태그 제거 실패: {e}")

    # Task 7.3: 트랜잭션 롤백 시 캐시 복구 메커니즘
    async def start_transaction_tracking(self, transaction_id: str):
        """
        트랜잭션 캐시 작업 추적 시작

        Args:
            transaction_id: 트랜잭션 ID
        """
        self.transaction_cache_ops[transaction_id] = []
        logger.info(f"트랜잭션 캐시 추적 시작: {transaction_id}")

    async def track_cache_operation(
        self,
        transaction_id: str,
        operation: str,
        key: str,
        value: Any = None,
        ttl: int = None,
    ):
        """
        트랜잭션 중 캐시 작업 추적

        Args:
            transaction_id: 트랜잭션 ID
            operation: 작업 타입 (set, delete, expire)
            key: 캐시 키
            value: 값 (set 작업의 경우)
            ttl: 만료 시간 (set 작업의 경우)
        """
        if transaction_id not in self.transaction_cache_ops:
            return

        op_record = {
            "operation": operation,
            "key": key,
            "value": value,
            "ttl": ttl,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.transaction_cache_ops[transaction_id].append(op_record)

    async def rollback_transaction_cache(self, transaction_id: str):
        """
        트랜잭션 롤백 시 캐시 복구

        Args:
            transaction_id: 트랜잭션 ID
        """
        if transaction_id not in self.transaction_cache_ops:
            return

        try:
            operations = self.transaction_cache_ops[transaction_id]

            # 역순으로 작업 실행 (롤백)
            for op in reversed(operations):
                operation = op["operation"]
                key = op["key"]

                if operation == "set":
                    # set 작업 롤백: 키 삭제
                    await self.cache_service.delete(key)
                elif operation == "delete":
                    # delete 작업 롤백: 원래 값 복원 (value가 있는 경우)
                    if op.get("value") is not None:
                        ttl = op.get("ttl", 3600)
                        await self.cache_service.set(key, op["value"], ttl)
                elif operation == "expire":
                    # expire 작업 롤백: 만료 시간 제거
                    await self.redis_manager.execute_with_retry(
                        self.client.persist, key
                    )

            # 트랜잭션 기록 정리
            del self.transaction_cache_ops[transaction_id]

            logger.info(f"트랜잭션 캐시 롤백 완료: {transaction_id}")

        except Exception as e:
            logger.error(f"트랜잭션 캐시 롤백 실패: {e}")

    async def commit_transaction_cache(self, transaction_id: str):
        """
        트랜잭션 커밋 시 추적 기록 정리

        Args:
            transaction_id: 트랜잭션 ID
        """
        if transaction_id in self.transaction_cache_ops:
            del self.transaction_cache_ops[transaction_id]
            logger.info(f"트랜잭션 캐시 커밋 완료: {transaction_id}")

    def _log_invalidation_event(
        self, event_type: str, target_keys: List[str], tags: List[str], timestamp: str
    ):
        """무효화 이벤트 로그 기록"""
        log_entry = {
            "event_type": event_type,
            "target_keys_count": len(target_keys),
            "tags": tags,
            "timestamp": timestamp,
        }

        self.invalidation_log.append(log_entry)

        # 로그 크기 제한
        if len(self.invalidation_log) > self.max_log_size:
            self.invalidation_log = self.invalidation_log[-self.max_log_size :]

    async def get_invalidation_stats(self) -> Dict[str, Any]:
        """
        무효화 통계 조회

        Returns:
            무효화 통계 정보
        """
        try:
            # 최근 무효화 이벤트 분석
            recent_events = (
                self.invalidation_log[-100:] if self.invalidation_log else []
            )

            event_counts = {}
            for event in recent_events:
                event_type = event["event_type"]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            return {
                "total_invalidations": len(self.invalidation_log),
                "recent_invalidations": len(recent_events),
                "event_type_distribution": event_counts,
                "is_listening": self.is_listening,
                "active_transactions": len(self.transaction_cache_ops),
            }

        except Exception as e:
            logger.error(f"무효화 통계 조회 실패: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """
        캐시 무효화 서비스 헬스체크

        Returns:
            헬스체크 결과
        """
        try:
            # Pub/Sub 연결 상태 확인
            pubsub_healthy = self.is_listening and self.pubsub is not None

            # Redis 연결 확인
            redis_healthy = await self.redis_manager.health_check()

            # 간단한 이벤트 발행 테스트
            test_event_sent = False
            try:
                await self.publish_invalidation_event(
                    event_type="health_check",
                    target_keys=["test_key"],
                    channel="cache_invalidation",
                )
                test_event_sent = True
            except Exception:
                pass

            return {
                "status": (
                    "healthy" if pubsub_healthy and redis_healthy else "unhealthy"
                ),
                "pubsub_connected": pubsub_healthy,
                "redis_connected": redis_healthy,
                "test_event_sent": test_event_sent,
                "active_transactions": len(self.transaction_cache_ops),
            }

        except Exception as e:
            logger.error(f"캐시 무효화 서비스 헬스체크 실패: {e}")
            return {"status": "unhealthy", "error": str(e)}
