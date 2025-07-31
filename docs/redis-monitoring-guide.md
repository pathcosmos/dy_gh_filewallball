# Redis 모니터링 및 성능 최적화 가이드

## 개요

FileWallBall 프로젝트의 Redis 캐싱 시스템 모니터링 및 성능 최적화 가이드입니다.

## 1. 모니터링 구성 요소

### 1.1 Redis Exporter
- **이미지**: `oliver006/redis_exporter:v1.55.0`
- **포트**: 9121
- **메트릭 엔드포인트**: `/metrics`
- **설정**: Redis Sentinel 모드 지원

### 1.2 주요 모니터링 지표

#### 메모리 관련 지표
- `redis_memory_used_bytes`: 현재 사용 중인 메모리
- `redis_memory_max_bytes`: 최대 메모리 설정
- `redis_memory_peak_bytes`: 피크 메모리 사용량
- `redis_memory_fragmentation_ratio`: 메모리 단편화 비율

#### 성능 관련 지표
- `redis_instantaneous_ops_per_sec`: 초당 명령 처리 수
- `redis_total_commands_processed`: 총 처리된 명령 수
- `redis_total_connections_received`: 총 연결 수
- `redis_connected_clients`: 현재 연결된 클라이언트 수

#### 캐시 효율성 지표
- `redis_keyspace_hits_total`: 캐시 히트 수
- `redis_keyspace_misses_total`: 캐시 미스 수
- `redis_evicted_keys_total`: 제거된 키 수
- `redis_expired_keys_total`: 만료된 키 수

#### 네트워크 지표
- `redis_instantaneous_input_kbps`: 초당 입력 KB
- `redis_instantaneous_output_kbps`: 초당 출력 KB
- `redis_total_net_input_bytes`: 총 입력 바이트
- `redis_total_net_output_bytes`: 총 출력 바이트

## 2. 알림 규칙

### 2.1 Critical 알림
- **RedisDown**: Redis 인스턴스가 1분 이상 다운된 경우
- **RedisMemoryCritical**: 메모리 사용량이 95% 이상인 경우

### 2.2 Warning 알림
- **RedisMemoryHigh**: 메모리 사용량이 80% 이상인 경우
- **RedisConnectionsHigh**: 연결된 클라이언트가 100개 이상인 경우
- **RedisEvictionsHigh**: 5분 내 10개 이상의 키가 제거된 경우
- **RedisSlowQueries**: 5분 내 5개 이상의 느린 쿼리가 있는 경우
- **RedisHitRateLow**: 캐시 히트율이 80% 미만인 경우

## 3. 성능 최적화

### 3.1 메모리 최적화

#### 메모리 정책 설정
```redis
# allkeys-lru: 모든 키에 대해 LRU 알고리즘 적용
CONFIG SET maxmemory-policy allkeys-lru

# 메모리 제한 설정 (256MB)
CONFIG SET maxmemory 268435456
```

#### 메모리 모니터링
```bash
# 메모리 사용량 확인
redis-cli info memory

# 메모리 단편화 확인
redis-cli memory stats
```

### 3.2 네트워크 최적화

#### 연결 풀 설정
```python
# Python redis-py 설정
import redis

pool = redis.ConnectionPool(
    host='redis',
    port=6379,
    password='filewallball2024',
    max_connections=20,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True
)

redis_client = redis.Redis(connection_pool=pool)
```

#### 네트워크 설정
```redis
# TCP keepalive 설정
CONFIG SET tcp-keepalive 300

# TCP nodelay 설정
CONFIG SET tcp-nodelay yes
```

### 3.3 캐시 최적화

#### TTL 정책
- **파일 메타데이터**: 1시간 (3600초)
- **세션 데이터**: 24시간 (86400초)
- **임시 데이터**: 10분 (600초)

#### 키 네이밍 규칙
```
file:meta:{uuid}          # 파일 메타데이터
session:user:{user_id}    # 사용자 세션
temp:upload:progress:{id} # 업로드 진행률
system:settings:{key}     # 시스템 설정
rate_limit:{ip}:{endpoint} # 속도 제한
```

## 4. 모니터링 스크립트

### 4.1 성능 모니터링 스크립트
```bash
# Redis 성능 모니터링 실행
./scripts/redis-performance-monitor.sh
```

### 4.2 성능 테스트 스크립트
```bash
# Redis 성능 테스트 실행
python3 scripts/redis-performance-test.py
```

## 5. Grafana 대시보드

### 5.1 주요 패널

#### Redis 개요
- Redis 상태 (Up/Down)
- 메모리 사용률
- 연결된 클라이언트 수
- 초당 명령 처리 수

#### 메모리 사용량
- 메모리 사용량 그래프
- 메모리 단편화 비율
- 피크 메모리 사용량
- 메모리 제한 대비 사용률

#### 성능 지표
- 캐시 히트율
- 명령 처리 속도
- 네트워크 I/O
- 응답 시간 분포

#### 알림 및 이벤트
- Redis 다운 이벤트
- 메모리 부족 경고
- 느린 쿼리 알림
- 키 제거 이벤트

### 5.2 대시보드 쿼리 예시

#### 캐시 히트율 계산
```
(redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) * 100
```

#### 메모리 사용률
```
(redis_memory_used_bytes / redis_memory_max_bytes) * 100
```

#### 초당 명령 처리 수
```
rate(redis_total_commands_processed[5m])
```

## 6. 문제 해결

### 6.1 메모리 부족 문제

#### 증상
- Redis가 키를 제거하기 시작
- 메모리 사용률이 90% 이상
- 응답 시간 증가

#### 해결 방법
1. 메모리 제한 증가
2. TTL 정책 조정
3. 불필요한 키 정리
4. 메모리 정책 변경

### 6.2 느린 응답 문제

#### 증상
- 응답 시간이 100ms 이상
- 연결 타임아웃 발생
- 클라이언트 에러 증가

#### 해결 방법
1. 연결 풀 크기 조정
2. 네트워크 설정 최적화
3. Redis 설정 튜닝
4. 클라이언트 타임아웃 조정

### 6.3 캐시 미스 문제

#### 증상
- 캐시 히트율이 80% 미만
- 데이터베이스 부하 증가
- 응답 시간 불안정

#### 해결 방법
1. 캐시 키 전략 재검토
2. TTL 정책 조정
3. 캐시 워밍 전략 구현
4. 캐시 크기 증가

## 7. 모니터링 체크리스트

### 7.1 일일 체크
- [ ] Redis 상태 확인
- [ ] 메모리 사용률 확인
- [ ] 캐시 히트율 확인
- [ ] 연결 수 확인
- [ ] 알림 확인

### 7.2 주간 체크
- [ ] 성능 테스트 실행
- [ ] 메모리 단편화 확인
- [ ] 느린 쿼리 분석
- [ ] 설정 최적화 검토
- [ ] 백업 상태 확인

### 7.3 월간 체크
- [ ] 용량 계획 검토
- [ ] 성능 트렌드 분석
- [ ] 보안 설정 검토
- [ ] 업그레이드 계획 수립

## 8. 유용한 명령어

### 8.1 Redis CLI 명령어
```bash
# Redis 정보 확인
redis-cli info

# 메모리 정보 확인
redis-cli info memory

# 클라이언트 정보 확인
redis-cli info clients

# 통계 정보 확인
redis-cli info stats

# 키 개수 확인
redis-cli dbsize

# 메모리 사용량 확인
redis-cli memory usage key_name
```

### 8.2 Kubernetes 명령어
```bash
# Redis Pod 상태 확인
kubectl get pods -n filewallball | grep redis

# Redis 로그 확인
kubectl logs -n filewallball deployment/redis-master

# Redis Exporter 로그 확인
kubectl logs -n filewallball deployment/redis-exporter

# Redis 서비스 확인
kubectl get svc -n filewallball | grep redis
```

## 9. 성능 벤치마크

### 9.1 목표 성능 지표
- **기본 작업**: 10,000+ ops/sec
- **Hash 작업**: 8,000+ ops/sec
- **List 작업**: 6,000+ ops/sec
- **동시 작업**: 5,000+ ops/sec
- **응답 시간**: 평균 < 1ms
- **캐시 히트율**: > 90%

### 9.2 성능 테스트 실행
```bash
# 전체 성능 테스트
python3 scripts/redis-performance-test.py

# 특정 테스트만 실행
python3 -c "
from scripts.redis_performance_test import RedisPerformanceTest
tester = RedisPerformanceTest()
tester.test_basic_operations(1000)
"
```

## 10. 결론

Redis 모니터링 및 성능 최적화는 FileWallBall 시스템의 안정성과 성능에 중요한 역할을 합니다. 정기적인 모니터링과 성능 테스트를 통해 시스템의 최적 상태를 유지할 수 있습니다.
