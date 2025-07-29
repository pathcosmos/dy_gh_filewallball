#!/usr/bin/env python3
"""
FileWallBall Redis 연결 풀 설정
Redis 연결 풀 및 성능 최적화 설정 - Task #7.1 최적화
"""

import os
from typing import Dict, Any

# Redis 연결 풀 기본 설정 - Task #7.1 최적화
DEFAULT_POOL_CONFIG = {
    'max_connections': 50,  # 기본값 증가 (20 → 50)
    'socket_timeout': 5.0,  # 소켓 타임아웃 (초)
    'socket_connect_timeout': 2.0,  # 연결 타임아웃 (초)
    'socket_keepalive': True,  # 연결 유지 활성화
    'socket_keepalive_options': {
        'TCP_KEEPIDLE': 300,  # 5분 후 keepalive 시작
        'TCP_KEEPINTVL': 75,  # 75초 간격으로 keepalive
        'TCP_KEEPCNT': 9      # 9번 실패 시 연결 종료
    },
    'retry_on_timeout': True,
    'retry_on_error': ['ConnectionError', 'TimeoutError'],
    'health_check_interval': 30,  # 헬스체크 간격 (초)
    'decode_responses': True,
    'max_connections_per_node': 20  # 클러스터 모드용
}

# 환경별 Redis 설정 - Task #7.1 최적화
REDIS_CONFIGS = {
    'development': {
        'host': 'localhost',
        'port': 6379,
        'password': 'filewallball2024',
        'db': 0,
        'max_connections': 20,  # 개발환경에서는 적은 연결 수
        'socket_timeout': 3.0,
        'socket_connect_timeout': 1.0,
        'health_check_interval': 60  # 개발환경에서는 긴 간격
    },
    'production': {
        'host': 'redis',
        'port': 6379,
        'password': 'filewallball2024',
        'db': 0,
        'max_connections': 100,  # 프로덕션에서는 많은 연결 수
        'socket_timeout': 10.0,
        'socket_connect_timeout': 5.0,
        'health_check_interval': 15,  # 프로덕션에서는 짧은 간격
        'socket_keepalive_options': {
            'TCP_KEEPIDLE': 60,   # 1분 후 keepalive 시작
            'TCP_KEEPINTVL': 30,  # 30초 간격
            'TCP_KEEPCNT': 5      # 5번 실패 시 종료
        }
    },
    'kubernetes': {
        'host': 'redis',
        'port': 6379,
        'password': 'filewallball2024',
        'db': 0,
        'max_connections': 50,  # Kubernetes 환경에 최적화
        'socket_timeout': 5.0,
        'socket_connect_timeout': 2.0,
        'retry_on_timeout': True,
        'health_check_interval': 30,
        'socket_keepalive_options': {
            'TCP_KEEPIDLE': 300,
            'TCP_KEEPINTVL': 75,
            'TCP_KEEPCNT': 9
        }
    }
}

def get_redis_config(environment: str = None) -> Dict[str, Any]:
    """
    환경별 Redis 설정 반환 - Task #7.1 최적화
    
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
    연결 풀 전용 설정 반환 - Task #7.1 최적화
    
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
        'socket_keepalive': config['socket_keepalive'],
        'socket_keepalive_options': config['socket_keepalive_options'],
        'retry_on_timeout': config['retry_on_timeout'],
        'retry_on_error': config['retry_on_error'],
        'health_check_interval': config['health_check_interval'],
        'decode_responses': config['decode_responses'],
        'max_connections_per_node': config.get('max_connections_per_node', 20)
    }
    
    return pool_config

# 성능 최적화 설정 - Task #7.1 강화
PERFORMANCE_CONFIG = {
    'pipeline_batch_size': 100,
    'max_pipeline_size': 1000,
    'connection_pool_timeout': 10,
    'socket_keepalive': True,
    'socket_keepalive_options': {
        'TCP_KEEPIDLE': 300,
        'TCP_KEEPINTVL': 75,
        'TCP_KEEPCNT': 9
    },
    # Task #7.1 추가 최적화 설정
    'connection_pool_overflow': 10,  # 연결 풀 오버플로우 허용
    'connection_pool_retry_delay': 0.1,  # 연결 재시도 지연 (초)
    'connection_pool_max_retries': 3,  # 최대 재시도 횟수
    'connection_pool_backoff_factor': 2.0,  # 지수 백오프 계수
    'connection_pool_health_check_enabled': True,  # 헬스체크 활성화
    'connection_pool_cleanup_interval': 300,  # 정리 간격 (초)
    'connection_pool_idle_timeout': 600,  # 유휴 연결 타임아웃 (초)
}

# 모니터링 설정 - Task #7.1 강화
MONITORING_CONFIG = {
    'enable_metrics': True,
    'metrics_interval': 60,
    'slow_query_threshold': 100,  # 밀리초
    'connection_pool_stats': True,
    'cache_hit_rate_threshold': 80.0,  # 퍼센트
    # Task #7.1 추가 모니터링 설정
    'connection_pool_monitoring': True,
    'connection_pool_alert_threshold': 0.8,  # 80% 사용률 시 알림
    'connection_pool_metrics_export': True,
    'redis_info_metrics': True,
    'redis_memory_metrics': True,
    'redis_network_metrics': True,
    'redis_command_metrics': True,
}

# 클러스터 설정 - Task #7.1 추가
CLUSTER_CONFIG = {
    'cluster_mode': False,  # 기본값은 단일 모드
    'cluster_nodes': [],  # 클러스터 노드 목록
    'cluster_require_full_coverage': True,
    'cluster_slots_cache_timeout': 0.5,
    'cluster_retry_on_timeout': True,
    'cluster_retry_on_error': ['ConnectionError', 'TimeoutError'],
    'cluster_max_connections_per_node': 20,
    'cluster_connection_pool_timeout': 10,
}

# Sentinel 설정 - Task #7.1 추가
SENTINEL_CONFIG = {
    'sentinel_mode': False,  # 기본값은 단일 모드
    'sentinel_hosts': [],  # Sentinel 호스트 목록
    'sentinel_password': None,
    'sentinel_service_name': 'mymaster',
    'sentinel_socket_timeout': 5.0,
    'sentinel_socket_connect_timeout': 2.0,
    'sentinel_retry_on_timeout': True,
    'sentinel_retry_on_error': ['ConnectionError', 'TimeoutError'],
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

# Task #7.1 연결 풀 최적화 함수
def optimize_pool_config(environment: str, workload_type: str = 'default') -> Dict[str, Any]:
    """
    워크로드 타입에 따른 연결 풀 최적화
    
    Args:
        environment: 환경명
        workload_type: 워크로드 타입 (default, high_concurrency, low_latency, high_throughput)
    
    Returns:
        Dict: 최적화된 연결 풀 설정
    """
    base_config = get_pool_config(environment)
    
    # 워크로드별 최적화
    if workload_type == 'high_concurrency':
        base_config['max_connections'] = int(base_config['max_connections'] * 1.5)
        base_config['socket_timeout'] = min(base_config['socket_timeout'] * 1.2, 15.0)
        base_config['health_check_interval'] = max(base_config['health_check_interval'] // 2, 10)
    
    elif workload_type == 'low_latency':
        base_config['socket_timeout'] = max(base_config['socket_timeout'] * 0.5, 1.0)
        base_config['socket_connect_timeout'] = max(base_config['socket_connect_timeout'] * 0.5, 0.5)
        base_config['health_check_interval'] = min(base_config['health_check_interval'] * 2, 120)
    
    elif workload_type == 'high_throughput':
        base_config['max_connections'] = int(base_config['max_connections'] * 2.0)
        base_config['socket_keepalive_options']['TCP_KEEPIDLE'] = 60
        base_config['socket_keepalive_options']['TCP_KEEPINTVL'] = 30
    
    return base_config 