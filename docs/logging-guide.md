# FileWallBall 로깅 가이드

## kubectl logs 명령어 활용

### 기본 로그 확인
```bash
# 특정 Pod의 로그 확인
kubectl logs <pod-name> -n filewallball

# 실시간 로그 스트리밍
kubectl logs -f <pod-name> -n filewallball

# 최근 N줄만 확인
kubectl logs --tail=100 <pod-name> -n filewallball

# 특정 시간 이후 로그 확인
kubectl logs --since=1h <pod-name> -n filewallball
```

### 애플리케이션별 로그 확인
```bash
# API 서비스 로그
kubectl logs -l app=filewallball-api -n filewallball

# MariaDB 로그
kubectl logs -l app=mariadb -n filewallball

# Redis 로그
kubectl logs -l app=redis -n filewallball
```

### 로그 레벨별 필터링
```bash
# ERROR 레벨 로그만 확인
kubectl logs <pod-name> -n filewallball | grep ERROR

# WARN 이상 레벨 로그 확인
kubectl logs <pod-name> -n filewallball | grep -E "(WARN|ERROR|FATAL)"
```

### 다중 Pod 로그 확인
```bash
# 모든 Pod의 로그 확인
kubectl logs -l app=filewallball-api -n filewallball --all-containers=true

# 특정 컨테이너의 로그만 확인
kubectl logs <pod-name> -c <container-name> -n filewallball
```

## 로그 설정

### 로그 레벨
- **filewallball-api**: INFO (JSON 형식, stdout)
- **mariadb**: WARN (텍스트 형식, stderr)
- **redis**: INFO (JSON 형식, stdout)

### 로그 저장 경로
- 호스트 경로: `/var/log/filewallball/`
- 로그 로테이션: 일별, 7일 보관, 압축

### 모니터링 메트릭
- Prometheus 메트릭 엔드포인트: `/metrics`
- 수집 간격: 30초
- 알림 규칙: 높은 에러율, 높은 지연시간

## 새로운 DB 스키마 관련 로깅

### 데이터베이스 테이블별 로깅 포인트
```bash
# 파일 업로드 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(file_upload|file_uuid|stored_filename)"

# 파일 조회 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(file_view|view_type|viewer_ip)"

# 파일 다운로드 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(file_download|download_method|bytes_downloaded)"

# 태그 시스템 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(file_tag|tag_relation|usage_count)"

# 시스템 설정 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(system_setting|setting_key|setting_value)"
```

### 성능 모니터링 로그
```bash
# 인덱스 사용 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(index_usage|query_performance|slow_query)"

# 트리거 실행 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(trigger_execution|tag_usage_update)"

# 통계 뷰 관련 로그
kubectl logs <api-pod> -n filewallball | grep -E "(file_statistics|view_count|download_count)"
```

### 확장자 매핑 로그
```bash
# 파일 확장자 검증 로그
kubectl logs <api-pod> -n filewallball | grep -E "(file_extension|mime_type|is_allowed)"

# 파일 크기 제한 로그
kubectl logs <api-pod> -n filewallball | grep -E "(max_file_size|file_size_validation)"
```

## 데이터베이스 직접 로그 확인

### MariaDB 로그에서 테이블 생성 확인
```bash
# 테이블 생성 로그
kubectl logs <mariadb-pod> -n filewallball | grep -E "(CREATE TABLE|filewallball_db)"

# 인덱스 생성 로그
kubectl logs <mariadb-pod> -n filewallball | grep -E "(CREATE INDEX|idx_)"

# 트리거 생성 로그
kubectl logs <mariadb-pod> -n filewallball | grep -E "(CREATE TRIGGER|update_tag_usage)"
```

### 데이터베이스 성능 로그
```bash
# 느린 쿼리 로그
kubectl logs <mariadb-pod> -n filewallball | grep -E "(slow_query|long_query_time)"

# 연결 수 관련 로그
kubectl logs <mariadb-pod> -n filewallball | grep -E "(max_connections|connection_count)"
```
