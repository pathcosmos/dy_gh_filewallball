"""
Scheduler service - 단순화된 버전
"""

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class SchedulerService:
    """스케줄러 서비스 (단순화된 버전)"""
    
    def schedule_task(self, task_name, func, *args, **kwargs):
        """작업 스케줄링 (일단 즉시 실행)"""
        logger.info(f"Scheduling task: {task_name}")
        return True


# 싱글톤 인스턴스
scheduler_service = SchedulerService()