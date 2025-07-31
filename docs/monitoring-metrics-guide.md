# FileWallBall 모니터링 및 메트릭 가이드

## 📊 개요

FileWallBall의 모니터링 및 메트릭 시스템은 시스템 성능, 사용량, 오류, 보안 이벤트를 실시간으로 추적하고 분석합니다. 이 문서는 구현된 모니터링 기능들과 메트릭 수집 방법을 상세히 설명합니다.

## 🔍 모니터링 아키텍처

### 모니터링 시스템 구성

```
┌─────────────────────────────────────┐
│           프론트엔드 레이어          │
│  (Grafana 대시보드, 알림 시스템)     │
├─────────────────────────────────────┤
│           수집 레이어                │
│  (Prometheus, 로그 수집기)          │
├─────────────────────────────────────┤
│           애플리케이션 레이어        │
│  (메트릭 생성, 로깅, 헬스체크)       │
├─────────────────────────────────────┤
│           인프라 레이어              │
│  (시스템 메트릭, 네트워크 모니터링)  │
└─────────────────────────────────────┘
```

## 📈 Prometheus 메트릭

### 메트릭 수집 시스템

FileWallBall은 Prometheus 형식의 메트릭을 자동으로 생성하고 노출합니다.

#### 기본 메트릭 설정

```python
# app/main.py
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_fastapi_instrumentator import Instrumentator

# 커스텀 메트릭 정의
file_upload_counter = Counter(
    'file_uploads_total',
    'Total number of file uploads',
    ['status', 'file_type', 'client_ip']
)

file_download_counter = Counter(
    'file_downloads_total',
    'Total number of file downloads',
    ['file_type', 'client_ip']
)

file_upload_duration = Histogram(
    'file_upload_duration_seconds',
    'File upload duration',
    ['file_type']
)

file_size_distribution = Histogram(
    'file_size_bytes',
    'File size distribution',
    ['file_type']
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

error_rate_counter = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'endpoint']
)

# Prometheus Instrumentator 설정
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

#### 메트릭 엔드포인트

```http
# Prometheus 메트릭 노출
GET /metrics

Response:
# HELP file_uploads_total Total number of file uploads
# TYPE file_uploads_total counter
file_uploads_total{status="success",file_type="image/jpeg",client_ip="192.168.1.100"} 150
file_uploads_total{status="failed",file_type="image/jpeg",client_ip="192.168.1.100"} 5

# HELP file_upload_duration_seconds File upload duration
# TYPE file_upload_duration_seconds histogram
file_upload_duration_seconds_bucket{file_type="image/jpeg",le="0.1"} 50
file_upload_duration_seconds_bucket{file_type="image/jpeg",le="0.5"} 120
file_upload_duration_seconds_bucket{file_type="image/jpeg",le="1.0"} 145
file_upload_duration_seconds_bucket{file_type="image/jpeg",le="+Inf"} 150

# HELP active_connections Number of active connections
# TYPE active_connections gauge
active_connections 25
```

### 상세 메트릭 API

#### 시스템 메트릭 조회

```http
GET /api/v1/metrics/detailed
```

**응답 예시:**
```json
{
  "system_metrics": {
    "total_files": 1250,
    "total_storage_used": 1073741824,
    "average_file_size": 858993,
    "files_by_type": {
      "image/jpeg": 450,
      "application/pdf": 200,
      "text/plain": 150,
      "video/mp4": 100
    },
    "storage_utilization": 75.5,
    "disk_free_space": 268435456
  },
  "performance_metrics": {
    "average_upload_time": 2.5,
    "average_download_time": 0.8,
    "cache_hit_rate": 85.5,
    "error_rate": 0.5,
    "response_time_p95": 1.2,
    "response_time_p99": 3.5
  },
  "user_metrics": {
    "active_users_today": 45,
    "total_downloads_today": 120,
    "total_views_today": 300,
    "unique_ips_today": 25
  },
  "security_metrics": {
    "failed_authentications": 12,
    "rate_limit_violations": 8,
    "suspicious_uploads": 3,
    "blocked_ips": 2
  }
}
```

## 🏥 헬스 체크 시스템

### Health Check Service (`health.py`)

헬스 체크 시스템은 시스템의 전반적인 상태를 모니터링합니다.

#### 헬스 체크 엔드포인트

```http
GET /health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": "72h 15m 30s",
  "services": {
    "database": {
      "status": "healthy",
      "response_time": "0.002s",
      "connections": 5
    },
    "redis": {
      "status": "healthy",
      "response_time": "0.001s",
      "memory_usage": "45%"
    },
    "storage": {
      "status": "healthy",
      "free_space": "2.5GB",
      "utilization": "75%"
    }
  },
  "dependencies": {
    "mariadb": "healthy",
    "redis": "healthy",
    "file_system": "healthy"
  }
}
```

#### 상세 헬스 체크

```http
GET /health/detailed
```

**응답 예시:**
```json
{
  "status": "healthy",
  "checks": {
    "database_connection": {
      "status": "healthy",
      "response_time": "0.002s",
      "details": {
        "active_connections": 5,
        "max_connections": 100,
        "connection_pool_size": 10
      }
    },
    "redis_connection": {
      "status": "healthy",
      "response_time": "0.001s",
      "details": {
        "memory_used": "45MB",
        "memory_max": "100MB",
        "connected_clients": 3
      }
    },
    "file_system": {
      "status": "healthy",
      "response_time": "0.005s",
      "details": {
        "total_space": "10GB",
        "used_space": "7.5GB",
        "free_space": "2.5GB",
        "inodes_used": "15000",
        "inodes_total": "100000"
      }
    },
    "external_services": {
      "status": "healthy",
      "checks": {
        "virus_scan_service": "healthy",
        "thumbnail_service": "healthy",
        "backup_service": "healthy"
      }
    }
  }
}
```

## 📝 로깅 시스템

### 로깅 미들웨어 (`logging.py`)

로깅 시스템은 모든 요청과 응답을 구조화된 형태로 기록합니다.

#### 로그 형식

```python
# 로그 설정
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/filewallball.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        }
    },
    "loggers": {
        "filewallball": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}
```

#### 요청 로깅

```python
# 요청 로그 예시
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "filewallball.request",
  "message": "HTTP request processed",
  "request_id": "req_123456789",
  "method": "POST",
  "path": "/upload",
  "status_code": 200,
  "response_time": 2.5,
  "client_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "file_size": 1048576,
  "file_type": "image/jpeg"
}
```

#### 에러 로깅

```python
# 에러 로그 예시
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "logger": "filewallball.error",
  "message": "File upload failed",
  "request_id": "req_123456789",
  "error_type": "ValidationError",
  "error_message": "File size exceeds limit",
  "client_ip": "192.168.1.100",
  "file_size": 104857600,
  "max_size": 52428800,
  "stack_trace": "..."
}
```

## 📊 통계 및 분석

### Statistics Service (`statistics_service.py`)

통계 서비스는 사용 패턴과 시스템 성능을 분석합니다.

#### 업로드 통계

```http
GET /api/v1/upload/statistics/{client_ip}
```

**응답 예시:**
```json
{
  "client_ip": "192.168.1.100",
  "period_days": 7,
  "total_uploads": 25,
  "total_size": 52428800,
  "successful_uploads": 23,
  "failed_uploads": 2,
  "average_file_size": 2097152,
  "most_common_type": "image/jpeg",
  "upload_trend": [
    {
      "date": "2024-01-15",
      "count": 5,
      "size": 10485760,
      "success_rate": 100.0
    },
    {
      "date": "2024-01-16",
      "count": 3,
      "size": 6291456,
      "success_rate": 66.7
    }
  ],
  "file_type_distribution": {
    "image/jpeg": 15,
    "image/png": 5,
    "application/pdf": 3,
    "text/plain": 2
  },
  "error_breakdown": {
    "file_too_large": 1,
    "invalid_file_type": 1
  }
}
```

#### 에러 통계

```http
GET /api/v1/upload/errors
```

**응답 예시:**
```json
{
  "period_days": 30,
  "total_errors": 15,
  "error_rate": 0.5,
  "error_types": {
    "file_too_large": 8,
    "invalid_file_type": 4,
    "storage_full": 2,
    "network_error": 1
  },
  "error_trend": [
    {
      "date": "2024-01-15",
      "count": 2,
      "type": "file_too_large",
      "percentage": 13.3
    },
    {
      "date": "2024-01-16",
      "count": 1,
      "type": "invalid_file_type",
      "percentage": 6.7
    }
  ],
  "top_error_sources": [
    {
      "client_ip": "192.168.1.100",
      "error_count": 5,
      "most_common_error": "file_too_large"
    },
    {
      "client_ip": "192.168.1.101",
      "error_count": 3,
      "most_common_error": "invalid_file_type"
    }
  ]
}
```

## 🔍 감사 로그

### Audit Middleware (`audit_middleware.py`)

감사 로그는 모든 중요한 시스템 활동을 기록합니다.

#### 감사 로그 조회

```http
GET /api/v1/audit/logs
Authorization: Bearer <admin_token>
```

**쿼리 파라미터:**
- `page`: 페이지 번호 (기본값: 1)
- `size`: 페이지당 로그 수 (기본값: 50)
- `user_id`: 사용자 ID 필터
- `action`: 액션 필터 (create, read, update, delete)
- `resource_type`: 리소스 타입 필터 (file, user, system)
- `status`: 상태 필터 (success, failed, denied)
- `date_from`: 시작 날짜
- `date_to`: 종료 날짜
- `ip_address`: IP 주소 필터

**응답 예시:**
```json
{
  "logs": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "user_id": 123,
      "username": "john.doe",
      "action": "file:upload",
      "resource_type": "file",
      "resource_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "success",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "details": {
        "filename": "example.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf"
      }
    }
  ],
  "total": 150,
  "page": 1,
  "size": 50,
  "pages": 3,
  "filters": {
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-01-15T23:59:59Z",
    "action": "file:upload",
    "status": "success"
  }
}
```

## 🚨 알림 시스템

### 알림 설정

```python
# 알림 규칙 설정
ALERT_RULES = {
    "high_error_rate": {
        "condition": "error_rate > 5%",
        "duration": "5m",
        "severity": "warning",
        "notification": ["email", "slack"]
    },
    "storage_full": {
        "condition": "storage_utilization > 90%",
        "duration": "1m",
        "severity": "critical",
        "notification": ["email", "slack", "sms"]
    },
    "service_down": {
        "condition": "health_check_failed",
        "duration": "30s",
        "severity": "critical",
        "notification": ["email", "slack", "sms", "pagerduty"]
    },
    "suspicious_activity": {
        "condition": "failed_auth > 10 in 5m",
        "duration": "5m",
        "severity": "warning",
        "notification": ["email", "slack"]
    }
}
```

### 알림 채널

```python
# 알림 채널 설정
NOTIFICATION_CHANNELS = {
    "email": {
        "enabled": True,
        "recipients": ["admin@example.com", "ops@example.com"],
        "smtp_server": "smtp.example.com",
        "smtp_port": 587
    },
    "slack": {
        "enabled": True,
        "webhook_url": "https://hooks.slack.com/services/...",
        "channel": "#alerts"
    },
    "sms": {
        "enabled": True,
        "provider": "twilio",
        "phone_numbers": ["+1234567890"]
    }
}
```

## 📊 대시보드 구성

### Grafana 대시보드

#### 시스템 대시보드

```json
{
  "dashboard": {
    "title": "FileWallBall System Overview",
    "panels": [
      {
        "title": "File Uploads",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(file_uploads_total[5m])",
            "legendFormat": "{{status}} - {{file_type}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(file_upload_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(errors_total[5m])",
            "legendFormat": "{{error_type}}"
          }
        ]
      },
      {
        "title": "Storage Usage",
        "type": "gauge",
        "targets": [
          {
            "expr": "storage_utilization_percent",
            "legendFormat": "Storage Usage"
          }
        ]
      }
    ]
  }
}
```

#### 보안 대시보드

```json
{
  "dashboard": {
    "title": "FileWallBall Security",
    "panels": [
      {
        "title": "Failed Authentications",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(authentication_failures_total[5m])",
            "legendFormat": "{{failure_type}}"
          }
        ]
      },
      {
        "title": "Rate Limit Violations",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(rate_limit_violations_total[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Suspicious Uploads",
        "type": "stat",
        "targets": [
          {
            "expr": "suspicious_uploads_total",
            "legendFormat": "Suspicious Uploads"
          }
        ]
      }
    ]
  }
}
```

## 🔧 모니터링 설정

### 환경 변수

```bash
# 모니터링 관련 환경 변수
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
GRAFANA_ENABLED=true
GRAFANA_PORT=3000

# 로깅 설정
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/filewallball.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5

# 알림 설정
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_RECIPIENTS=admin@example.com,ops@example.com
ALERT_SLACK_ENABLED=true
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/...

# 헬스 체크 설정
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=5s
```

### Prometheus 설정

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "filewallball_alerts.yml"

scrape_configs:
  - job_name: 'filewallball'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'filewallball-health'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/health'
    scrape_interval: 30s
```

### 알림 규칙

```yaml
# filewallball_alerts.yml
groups:
  - name: filewallball
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: StorageFull
        expr: storage_utilization_percent > 90
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Storage is nearly full"
          description: "Storage utilization is {{ $value }}%"

      - alert: ServiceDown
        expr: up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "FileWallBall service is not responding"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(file_upload_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time"
          description: "95th percentile response time is {{ $value }}s"
```

## 🧪 모니터링 테스트

### 모니터링 테스트 스크립트

```python
# tests/test_monitoring.py
import pytest
import requests
import time

class TestMonitoring:

    def test_health_check(self):
        """헬스 체크 테스트"""
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]

    def test_metrics_endpoint(self):
        """메트릭 엔드포인트 테스트"""
        response = requests.get("http://localhost:8000/metrics")
        assert response.status_code == 200

        content = response.text
        assert "file_uploads_total" in content
        assert "file_upload_duration_seconds" in content
        assert "errors_total" in content

    def test_detailed_metrics(self):
        """상세 메트릭 테스트"""
        response = requests.get("http://localhost:8000/api/v1/metrics/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "system_metrics" in data
        assert "performance_metrics" in data
        assert "user_metrics" in data

    def test_audit_logs(self):
        """감사 로그 테스트"""
        response = requests.get("http://localhost:8000/api/v1/audit/logs")
        assert response.status_code == 200

        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "page" in data

    def test_error_statistics(self):
        """에러 통계 테스트"""
        response = requests.get("http://localhost:8000/api/v1/upload/errors")
        assert response.status_code == 200

        data = response.json()
        assert "total_errors" in data
        assert "error_types" in data
        assert "error_trend" in data
```

## 📋 모니터링 체크리스트

### 배포 전 모니터링 설정 확인

- [ ] Prometheus 메트릭이 올바르게 노출됨
- [ ] 헬스 체크 엔드포인트가 작동함
- [ ] 로깅 시스템이 구성됨
- [ ] 알림 규칙이 설정됨
- [ ] 대시보드가 구성됨
- [ ] 모니터링 테스트가 통과됨

### 정기 모니터링 점검

- [ ] 메트릭 수집 상태 확인
- [ ] 알림 규칙 검토 및 조정
- [ ] 대시보드 업데이트
- [ ] 로그 보관 정책 확인
- [ ] 성능 지표 분석
- [ ] 용량 계획 검토

---

이 문서는 FileWallBall의 모니터링 및 메트릭 시스템을 상세히 설명합니다. 모니터링 관련 질문이나 개선 제안이 있으시면 운영팀에 문의해 주세요.
