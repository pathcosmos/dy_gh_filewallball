#!/usr/bin/env python3
"""
FileWallBall Redis 연결 풀 설정
Redis 연결 풀 및 성능 최적화 설정
"""

import os
from typing import Dict, Any

# Redis 연결 풀 기본 설정
DEFAULT_POOL_CONFIG = {
    'max_connections': 20,
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30,
    'decode_responses': True
}

# 환경별 Redis 설정
REDIS_CONFIGS = {
    'development': {
        'host': 'localhost',
        'port': 6379,
        'password': 'filewallball2024',
        'db': 0,
        'max_connections': 10,
        'socket_timeout': 3,
        'socket_connect_timeout': 3
    },
    'production': {
        'host': 'redis',
        'port': 6379,
        'password': 'filewallball2024',
        'db': 0,
        'max_connections': 50,
        'socket_timeout': 10,
        'socket_connect_timeout': 10,
        'health_check_interval': 15
    },
    'kubernetes': {
        'host': 'redis',
        'port': 6379,
        'password': 'filewallball2024',
        'db': 0,
        'max_connections': 30,
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
        'retry_on_timeout': True,
        'health_check_interval': 30
    }
}

def get_redis_config(environment: str = None) -> Dict[str, Any]:
    """
    환경별 Redis 설정 반환
    
    Args:
        environment: 환경명 (development, production, kubernetes)
    
    Returns:
        Dict: Redis 설정
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'kubernetes')
    
    config = REDIS_CONFIGS.get(environment, REDIS_CONFIGS['kubernetes'])
    
    # 기본 설정과 병합
    final_config = DEFAULT_POOL_CONFIG.copy()
    final_config.update(config)
    
    return final_config

def get_pool_config(environment: str = None) -> Dict[str, Any]:
    """
    연결 풀 전용 설정 반환
    
    Args:
        environment: 환경명
    
    Returns:
        Dict: 연결 풀 설정
    """
    config = get_redis_config(environment)
    
    # 연결 풀 관련 설정만 추출
    pool_config = {
        'max_connections': config['max_connections'],
        'socket_timeout': config['socket_timeout'],
        'socket_connect_timeout': config['socket_connect_timeout'],
        'retry_on_timeout': config['retry_on_timeout'],
        'health_check_interval': config['health_check_interval'],
        'decode_responses': config['decode_responses']
    }
    
    return pool_config

# 성능 최적화 설정
PERFORMANCE_CONFIG = {
    'pipeline_batch_size': 100,
    'max_pipeline_size': 1000,
    'connection_pool_timeout': 10,
    'socket_keepalive': True,
    'socket_keepalive_options': {
        'TCP_KEEPIDLE': 300,
        'TCP_KEEPINTVL': 75,
        'TCP_KEEPCNT': 9
    }
}

# 모니터링 설정
MONITORING_CONFIG = {
    'enable_metrics': True,
    'metrics_interval': 60,
    'slow_query_threshold': 100,  # 밀리초
    'connection_pool_stats': True,
    'cache_hit_rate_threshold': 80.0  # 퍼센트
}

# 캐시 키 패턴 설정
CACHE_PATTERNS = {
    'file_meta': 'file:meta:{uuid}',
    'session': 'session:user:{user_id}',
    'temp_upload': 'temp:upload:progress:{upload_id}',
    'temp_download': 'temp:download:token:{token}',
    'system_settings': 'system:settings:{key}',
    'rate_limit': 'rate_limit:{ip}:{endpoint}',
    'file_stats': 'stats:file:{file_id}',
    'user_activity': 'activity:user:{user_id}'
}

# TTL 설정 (초 단위)
TTL_SETTINGS = {
    'file_meta': 3600,      # 1시간
    'session': 86400,       # 24시간
    'temp_data': 600,       # 10분
    'system_settings': 3600, # 1시간
    'rate_limit': 60,       # 1분
    'file_stats': 1800,     # 30분
    'user_activity': 7200   # 2시간
} 