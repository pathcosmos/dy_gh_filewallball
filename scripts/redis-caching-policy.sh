#!/bin/bash

# FileWallBall Redis 캐싱 정책 설정 및 테스트 스크립트

set -e

# 설정 변수
REDIS_PASSWORD="filewallball2024"
REDIS_POD=$(microk8s kubectl get pods -n filewallball -l app=redis -o jsonpath='{.items[0].metadata.name}')

# 로그 함수
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Redis 연결 테스트
test_redis_connection() {
    log "🔗 Redis 연결 테스트 중..."
    microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD ping
    if [ $? -eq 0 ]; then
        log "✅ Redis 연결 성공"
    else
        log "❌ Redis 연결 실패"
        exit 1
    fi
}

# TTL 정책 테스트
test_ttl_policy() {
    log "⏰ TTL 정책 테스트 중..."

    # 파일 메타데이터 캐시 (1시간)
    log "📁 파일 메타데이터 캐시 테스트 (TTL: 1시간)"
    microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD SET file:meta:test123 '{"name":"test.txt","size":1024,"type":"text/plain"}' EX 3600
    TTL=$(microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD TTL file:meta:test123)
    log "📊 파일 메타데이터 TTL: ${TTL}초"

    # 세션 데이터 캐시 (24시간)
    log "👤 세션 데이터 캐시 테스트 (TTL: 24시간)"
    microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD SET session:user:123 '{"user_id":123,"login_time":"2024-01-01","permissions":["read","write"]}' EX 86400
    TTL=$(microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD TTL session:user:123)
    log "📊 세션 데이터 TTL: ${TTL}초"

    # 임시 데이터 캐시 (10분)
    log "⚡ 임시 데이터 캐시 테스트 (TTL: 10분)"
    microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD SET temp:upload:progress:456 '{"progress":75,"status":"uploading"}' EX 600
    TTL=$(microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD TTL temp:upload:progress:456)
    log "📊 임시 데이터 TTL: ${TTL}초"
}

# 메모리 정책 테스트
test_memory_policy() {
    log "🧠 메모리 정책 테스트 중..."

    # 현재 메모리 설정 확인
    MAXMEMORY=$(microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD CONFIG GET maxmemory | tail -1)
    POLICY=$(microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD CONFIG GET maxmemory-policy | tail -1)

    log "📊 최대 메모리: ${MAXMEMORY}바이트"
    log "📊 메모리 정책: ${POLICY}"

    # 메모리 사용량 확인
    INFO=$(microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD INFO memory)
    USED_MEMORY=$(echo "$INFO" | grep "used_memory:" | cut -d: -f2)
    USED_MEMORY_HUMAN=$(echo "$INFO" | grep "used_memory_human:" | cut -d: -f2)

    log "📊 사용 중인 메모리: ${USED_MEMORY}바이트 (${USED_MEMORY_HUMAN})"
}

# 캐시 성능 테스트
test_cache_performance() {
    log "⚡ 캐시 성능 테스트 중..."

    # 대량 데이터 삽입
    log "📥 대량 데이터 삽입 테스트"
    for i in {1..100}; do
        microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD SET "test:key:$i" "value_$i" EX 3600 > /dev/null 2>&1
    done

    # 키 개수 확인
    KEY_COUNT=$(microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD DBSIZE)
    log "📊 총 키 개수: ${KEY_COUNT}"

    # 랜덤 읽기 성능 테스트
    log "📖 랜덤 읽기 성능 테스트"
    START_TIME=$(date +%s.%N)
    for i in {1..50}; do
        RANDOM_KEY=$((RANDOM % 100 + 1))
        microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD GET "test:key:$RANDOM_KEY" > /dev/null 2>&1
    done
    END_TIME=$(date +%s.%N)
    ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
    log "📊 50회 랜덤 읽기 시간: ${ELAPSED}초"
}

# 캐시 정리
cleanup_cache() {
    log "🧹 캐시 정리 중..."

    # 테스트 키 삭제
    microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD DEL file:meta:test123 session:user:123 temp:upload:progress:456 > /dev/null 2>&1

    # 테스트 키들 삭제
    for i in {1..100}; do
        microk8s kubectl exec -n filewallball $REDIS_POD -- redis-cli -a $REDIS_PASSWORD DEL "test:key:$i" > /dev/null 2>&1
    done

    log "✅ 캐시 정리 완료"
}

# 메인 실행
main() {
    log "=== FileWallBall Redis 캐싱 정책 테스트 시작 ==="

    # Redis Pod 확인
    if [ -z "$REDIS_POD" ]; then
        log "❌ Redis Pod를 찾을 수 없습니다."
        exit 1
    fi

    log "📦 Redis Pod: $REDIS_POD"

    # 테스트 실행
    test_redis_connection
    test_ttl_policy
    test_memory_policy
    test_cache_performance
    cleanup_cache

    log "✅ FileWallBall Redis 캐싱 정책 테스트 완료!"
}

# 스크립트 실행
main "$@"
