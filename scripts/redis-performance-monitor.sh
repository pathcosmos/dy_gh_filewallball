#!/bin/bash

# Redis 성능 모니터링 스크립트
# FileWallBall Redis 캐싱 시스템 모니터링

REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_PASSWORD="filewallball2024"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Redis 성능 모니터링 시작 ===${NC}"
echo "시간: $(date)"
echo ""

# Redis 연결 테스트
echo -e "${GREEN}1. Redis 연결 상태 확인${NC}"
if redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping | grep -q "PONG"; then
    echo -e "${GREEN}✓ Redis 연결 성공${NC}"
else
    echo -e "${RED}✗ Redis 연결 실패${NC}"
    exit 1
fi
echo ""

# 기본 정보 조회
echo -e "${GREEN}2. Redis 기본 정보${NC}"
echo "Redis 버전: $(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info server | grep redis_version | cut -d: -f2)"
echo "업타임: $(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info server | grep uptime_in_seconds | cut -d: -f2 | awk '{print int($1/3600)"시간 "int(($1%3600)/60)"분"}')"
echo ""

# 메모리 사용량
echo -e "${GREEN}3. 메모리 사용량${NC}"
MEMORY_USED=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info memory | grep used_memory_human | cut -d: -f2)
MEMORY_MAX=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info memory | grep maxmemory_human | cut -d: -f2)
MEMORY_PEAK=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info memory | grep used_memory_peak_human | cut -d: -f2)

echo "현재 사용량: $MEMORY_USED"
echo "최대 메모리: $MEMORY_MAX"
echo "피크 사용량: $MEMORY_PEAK"
echo ""

# 연결 정보
echo -e "${GREEN}4. 연결 정보${NC}"
CONNECTED_CLIENTS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info clients | grep connected_clients | cut -d: -f2)
BLOCKED_CLIENTS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info clients | grep blocked_clients | cut -d: -f2)

echo "연결된 클라이언트: $CONNECTED_CLIENTS"
echo "블록된 클라이언트: $BLOCKED_CLIENTS"
echo ""

# 통계 정보
echo -e "${GREEN}5. 통계 정보${NC}"
TOTAL_COMMANDS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info stats | grep total_commands_processed | cut -d: -f2)
TOTAL_CONNECTIONS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info stats | grep total_connections_received | cut -d: -f2)
KEYS_HITS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info stats | grep keyspace_hits | cut -d: -f2)
KEYS_MISSES=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info stats | grep keyspace_misses | cut -d: -f2)

# 히트율 계산
if [ "$KEYS_HITS" -gt 0 ] || [ "$KEYS_MISSES" -gt 0 ]; then
    HIT_RATE=$(echo "scale=2; $KEYS_HITS * 100 / ($KEYS_HITS + $KEYS_MISSES)" | bc)
else
    HIT_RATE="0.00"
fi

echo "총 명령 처리: $TOTAL_COMMANDS"
echo "총 연결 수: $TOTAL_CONNECTIONS"
echo "키 히트: $KEYS_HITS"
echo "키 미스: $KEYS_MISSES"
echo -e "캐시 히트율: ${YELLOW}${HIT_RATE}%${NC}"
echo ""

# 키 정보
echo -e "${GREEN}6. 키 정보${NC}"
TOTAL_KEYS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD dbsize)
echo "총 키 수: $TOTAL_KEYS"

# 키 패턴별 통계
echo "키 패턴별 통계:"
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --scan --pattern "filewallball:*" | wc -l | xargs echo "  filewallball:* 키 수:"
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --scan --pattern "session:*" | wc -l | xargs echo "  session:* 키 수:"
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --scan --pattern "temp:*" | wc -l | xargs echo "  temp:* 키 수:"
echo ""

# 성능 지표
echo -e "${GREEN}7. 성능 지표${NC}"
INSTANTANEOUS_OPS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info stats | grep instantaneous_ops_per_sec | cut -d: -f2)
INSTANTANEOUS_INPUT=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info stats | grep instantaneous_input_kbps | cut -d: -f2)
INSTANTANEOUS_OUTPUT=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info stats | grep instantaneous_output_kbps | cut -d: -f2)

echo "초당 명령 처리: $INSTANTANEOUS_OPS"
echo "초당 입력 KB: $INSTANTANEOUS_INPUT"
echo "초당 출력 KB: $INSTANTANEOUS_OUTPUT"
echo ""

# 경고 체크
echo -e "${GREEN}8. 경고 체크${NC}"

# 메모리 사용량 경고
MEMORY_USED_BYTES=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info memory | grep used_memory | head -1 | cut -d: -f2)
MEMORY_MAX_BYTES=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info memory | grep maxmemory | head -1 | cut -d: -f2)

if [ "$MEMORY_MAX_BYTES" -gt 0 ]; then
    MEMORY_USAGE_PERCENT=$(echo "scale=2; $MEMORY_USED_BYTES * 100 / $MEMORY_MAX_BYTES" | bc)
    if (( $(echo "$MEMORY_USAGE_PERCENT > 80" | bc -l) )); then
        echo -e "${RED}⚠️  메모리 사용량이 높습니다: ${MEMORY_USAGE_PERCENT}%${NC}"
    else
        echo -e "${GREEN}✓ 메모리 사용량 정상: ${MEMORY_USAGE_PERCENT}%${NC}"
    fi
fi

# 연결 수 경고
if [ "$CONNECTED_CLIENTS" -gt 100 ]; then
    echo -e "${RED}⚠️  연결된 클라이언트가 많습니다: $CONNECTED_CLIENTS${NC}"
else
    echo -e "${GREEN}✓ 연결된 클라이언트 수 정상: $CONNECTED_CLIENTS${NC}"
fi

# 히트율 경고
if (( $(echo "$HIT_RATE < 80" | bc -l) )); then
    echo -e "${RED}⚠️  캐시 히트율이 낮습니다: ${HIT_RATE}%${NC}"
else
    echo -e "${GREEN}✓ 캐시 히트율 정상: ${HIT_RATE}%${NC}"
fi

echo ""
echo -e "${BLUE}=== 모니터링 완료 ===${NC}" 