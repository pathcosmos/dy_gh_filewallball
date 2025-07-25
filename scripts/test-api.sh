#!/bin/bash

# API 테스트 스크립트
BASE_URL="http://localhost:8000"

echo "🧪 FileWallBall API 테스트 시작..."

# 헬스체크
echo "1. 헬스체크 테스트"
curl -s "${BASE_URL}/health" | jq .

# 메트릭 확인
echo "2. 메트릭 확인"
curl -s "${BASE_URL}/metrics" | head -20

# 파일 업로드 테스트
echo "3. 파일 업로드 테스트"
echo "Hello, FileWallBall!" > test_file.txt

UPLOAD_RESPONSE=$(curl -s -X POST "${BASE_URL}/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_file.txt")

echo "업로드 응답:"
echo $UPLOAD_RESPONSE | jq .

# 파일 ID 추출
FILE_ID=$(echo $UPLOAD_RESPONSE | jq -r '.file_id')
echo "파일 ID: $FILE_ID"

# 파일 정보 조회
echo "4. 파일 정보 조회 테스트"
curl -s "${BASE_URL}/files/${FILE_ID}" | jq .

# 파일 다운로드 테스트
echo "5. 파일 다운로드 테스트"
curl -s "${BASE_URL}/download/${FILE_ID}" -o downloaded_file.txt
echo "다운로드된 파일 내용:"
cat downloaded_file.txt

# 파일 미리보기 테스트
echo "6. 파일 미리보기 테스트"
curl -s "${BASE_URL}/view/${FILE_ID}" | jq .

# 파일 목록 조회
echo "7. 파일 목록 조회 테스트"
curl -s "${BASE_URL}/files" | jq .

# 파일 삭제 테스트
echo "8. 파일 삭제 테스트"
curl -s -X DELETE "${BASE_URL}/files/${FILE_ID}" | jq .

# 정리
rm -f test_file.txt downloaded_file.txt

echo "✅ API 테스트 완료!" 