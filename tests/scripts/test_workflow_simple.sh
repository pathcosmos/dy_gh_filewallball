#!/bin/bash

# FileWallBall API 간단한 워크플로우 테스트
set -e

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
API_BASE_URL="http://127.0.0.1:8000"
TEST_FILE="simple_test.txt"
TEST_CONTENT="Simple test content for workflow testing"

echo "🚀 FileWallBall API 워크플로우 테스트 시작"

# 1. API 헬스체크
echo "1️⃣ API 헬스체크..."
if curl -s "$API_BASE_URL/health" | jq -e '.status == "healthy"' > /dev/null; then
    echo -e "${GREEN}✅ API 헬스체크 성공${NC}"
else
    echo -e "${RED}❌ API 헬스체크 실패${NC}"
    exit 1
fi

# 2. 테스트 파일 생성
echo "2️⃣ 테스트 파일 생성..."
echo "$TEST_CONTENT" > "$TEST_FILE"
echo -e "${GREEN}✅ 테스트 파일 생성 완료${NC}"

# 3. 파일 업로드
echo "3️⃣ 파일 업로드..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE_URL/upload" -F "file=@$TEST_FILE")
FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.file_id')

if [ "$FILE_ID" != "null" ] && [ "$FILE_ID" != "" ]; then
    echo -e "${GREEN}✅ 파일 업로드 성공 - ID: $FILE_ID${NC}"
else
    echo -e "${RED}❌ 파일 업로드 실패${NC}"
    exit 1
fi

# 4. 파일 정보 조회
echo "4️⃣ 파일 정보 조회..."
if curl -s "$API_BASE_URL/files/$FILE_ID" | jq -e '.file_id' > /dev/null; then
    echo -e "${GREEN}✅ 파일 정보 조회 성공${NC}"
else
    echo -e "${RED}❌ 파일 정보 조회 실패${NC}"
    exit 1
fi

# 5. 파일 다운로드
echo "5️⃣ 파일 다운로드..."
if curl -s -o "downloaded_$TEST_FILE" "$API_BASE_URL/download/$FILE_ID"; then
    echo -e "${GREEN}✅ 파일 다운로드 성공${NC}"
else
    echo -e "${RED}❌ 파일 다운로드 실패${NC}"
    exit 1
fi

# 6. 파일 무결성 검증
echo "6️⃣ 파일 무결성 검증..."
ORIGINAL_HASH=$(md5sum "$TEST_FILE" | cut -d' ' -f1)
DOWNLOADED_HASH=$(md5sum "downloaded_$TEST_FILE" | cut -d' ' -f1)

if [ "$ORIGINAL_HASH" = "$DOWNLOADED_HASH" ]; then
    echo -e "${GREEN}✅ 파일 무결성 검증 성공 - MD5: $ORIGINAL_HASH${NC}"
else
    echo -e "${RED}❌ 파일 무결성 검증 실패${NC}"
    echo "원본: $ORIGINAL_HASH"
    echo "다운로드: $DOWNLOADED_HASH"
    exit 1
fi

# 7. 파일 목록 조회
echo "7️⃣ 파일 목록 조회..."
if curl -s "$API_BASE_URL/files?limit=3" | jq -e '.files' > /dev/null; then
    echo -e "${GREEN}✅ 파일 목록 조회 성공${NC}"
else
    echo -e "${RED}❌ 파일 목록 조회 실패${NC}"
    exit 1
fi

# 정리
echo "🧹 테스트 파일 정리..."
rm -f "$TEST_FILE" "downloaded_$TEST_FILE"

echo -e "${GREEN}🎉 모든 워크플로우 테스트 통과!${NC}"
echo "🏁 워크플로우 테스트 완료"
