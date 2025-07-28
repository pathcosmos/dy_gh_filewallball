"""
Structured logging configuration for the application.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from app.config import get_settings


def setup_logging(
    log_level: str = "INFO",
    log_format: str = None,
    log_file: Optional[str] = None
) -> None:
    """
    애플리케이션 로깅 시스템 설정
    
    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 로그 포맷 문자열
        log_file: 로그 파일 경로 (None이면 콘솔만 출력)
    """
    settings = get_settings()
    
    # 로그 레벨 설정
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 로그 포맷 설정
    if log_format is None:
        log_format = settings.log_format
    
    # 로그 포맷터 생성
    formatter = logging.Formatter(log_format)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (지정된 경우)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 로테이션 핸들러 (일별, 30일 보관)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 특정 로거들의 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    이름으로 로거 가져오기
    
    Args:
        name: 로거 이름
        
    Returns:
        설정된 로거 인스턴스
    """
    return logging.getLogger(name)


class RequestIdFilter(logging.Filter):
    """요청 ID를 로그에 추가하는 필터"""
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.request_id = None
    
    def filter(self, record):
        if hasattr(record, 'request_id'):
            record.request_id = self.request_id
        return True


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포맷터"""
    
    def format(self, record):
        import json
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 요청 ID가 있으면 추가
        if hasattr(record, 'request_id') and record.request_id:
            log_entry["request_id"] = record.request_id
        
        # 예외 정보가 있으면 추가
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_json_logging(log_file: str) -> None:
    """
    JSON 형식 로깅 설정
    
    Args:
        log_file: JSON 로그 파일 경로
    """
    settings = get_settings()
    
    # JSON 포맷터 생성
    json_formatter = JSONFormatter()
    
    # 파일 핸들러 생성
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    json_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    json_handler.setLevel(getattr(logging, settings.log_level.upper()))
    json_handler.setFormatter(json_formatter)
    
    # 루트 로거에 추가
    root_logger = logging.getLogger()
    root_logger.addHandler(json_handler) 