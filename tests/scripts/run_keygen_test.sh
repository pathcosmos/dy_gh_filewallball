#!/bin/bash
# Keygen API 테스트 실행 스크립트

echo "🔥 Keygen API 테스트를 시작합니다..."
echo "================================"

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# Python 가상환경 활성화 (존재하는 경우)
if [ -d ".venv" ]; then
    echo "📦 가상환경 활성화..."
    source .venv/bin/activate
fi

# 테스트 실행
echo "🚀 테스트 실행 중..."
python test_keygen_api.py

# 결과 확인
EXIT_CODE=$?

echo ""
echo "================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 테스트가 성공적으로 완료되었습니다!"
else
    echo "❌ 테스트 실행 중 오류가 발생했습니다."
fi

# 남은 테스트 서버 프로세스 정리 (안전 장치)
REMAINING_SERVERS=$(pgrep -f "uvicorn.*app\.main.*800[0-9]" 2>/dev/null | wc -l)
if [ $REMAINING_SERVERS -gt 0 ]; then
    echo "🧹 남은 테스트 서버 정리 중..."
    pkill -f "uvicorn.*app\.main.*800[0-9]" 2>/dev/null || true
    echo "✅ 서버 정리 완료"
else
    echo "✅ 모든 테스트 서버가 정상적으로 정리되었습니다."
fi

echo "🏁 테스트 완료"