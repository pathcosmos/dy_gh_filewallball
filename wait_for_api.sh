#!/bin/bash

API_URL="$1"
MAX_ATTEMPTS=30
ATTEMPT=1

echo "API 서버 대기 중: $API_URL"

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if curl -s -f "$API_URL/health" > /dev/null; then
        echo "API 서버가 준비되었습니다!"
        exit 0
    fi

    echo "시도 $ATTEMPT/$MAX_ATTEMPTS - API 서버 대기 중..."
    sleep 10
    ATTEMPT=$((ATTEMPT + 1))
done

echo "API 서버가 준비되지 않았습니다. 타임아웃."
exit 1
