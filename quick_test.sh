#!/bin/bash

echo "=== FileWallBall 빠른 테스트 ==="

# 환경 변수
API_URL="http://localhost:8001"
MASTER_KEY="dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
PROJECT_NAME="quick-test-$(date +%s)"
REQUEST_DATE=$(date +%Y%m%d)

echo "1. 헬스체크"
HEALTH_RESPONSE=$(wget -qO- "$API_URL/health" 2>/dev/null || echo "연결 실패")
echo "응답: $HEALTH_RESPONSE"
echo "$HEALTH_RESPONSE" | jq '.' 2>/dev/null || echo "JSON 파싱 실패"

echo -e "\n2. 프로젝트 키 생성"
echo "요청 데이터:"
echo "  프로젝트명: $PROJECT_NAME"
echo "  요청날짜: $REQUEST_DATE"
echo "  마스터키: $MASTER_KEY"

PROJECT_KEY_RESPONSE=$(wget -qO- --post-data="project_name=$PROJECT_NAME&request_date=$REQUEST_DATE&master_key=$MASTER_KEY" \
    --header="Content-Type: application/x-www-form-urlencoded" \
    "$API_URL/keygen" 2>/dev/null || echo "연결 실패")
echo "응답: $PROJECT_KEY_RESPONSE"
echo "$PROJECT_KEY_RESPONSE" | jq '.' 2>/dev/null || echo "JSON 파싱 실패"

PROJECT_KEY=$(echo "$PROJECT_KEY_RESPONSE" | jq -r '.project_key')

echo -e "\n3. 테스트 파일 생성"
echo "Hello FileWallBall!" > test.txt

echo -e "\n4. 파일 업로드"
echo "업로드할 파일 내용:"
cat test.txt
echo ""
echo "프로젝트 키: $PROJECT_KEY"

UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/upload" \
    -F "file=@test.txt" \
    -F "project_key=$PROJECT_KEY")
echo "응답: $UPLOAD_RESPONSE"
echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "JSON 파싱 실패"

FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.file_id')
DOWNLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.download_url')

echo -e "\n5. 파일 다운로드"
echo "다운로드 URL: $DOWNLOAD_URL"
curl -s -o downloaded.txt "$DOWNLOAD_URL"
echo "다운로드 상태: $?"
echo "다운로드된 파일 내용:"
if [ -f downloaded.txt ]; then
    cat downloaded.txt
else
    echo "다운로드된 파일이 없습니다."
fi

echo -e "\n6. 파일 비교"
if cmp -s test.txt downloaded.txt; then
    echo "✅ 파일이 동일합니다!"
else
    echo "❌ 파일이 다릅니다!"
fi

# 정리
rm -f test.txt downloaded.txt

echo -e "\n=== 테스트 완료 ===" 