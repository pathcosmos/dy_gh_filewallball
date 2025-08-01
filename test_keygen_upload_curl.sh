#!/bin/bash

# Keygen과 Upload 기능 연동 테스트 스크립트 (curl 버전)

BASE_URL="http://localhost:8000"
MASTER_KEY="dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "Keygen과 Upload 기능 연동 테스트 시작"
echo "=========================================="

# 1. 헬스체크
echo "1. 헬스체크 테스트"
echo "------------------"
curl -s -X GET "${BASE_URL}/health" | jq '.'
echo ""

# 2. Keygen 엔드포인트 테스트
echo "2. Keygen 엔드포인트 테스트"
echo "--------------------------"
PROJECT_NAME="test_project_${TIMESTAMP}"
CURRENT_DATE=$(date +%Y%m%d)

KEYGEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/keygen" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "project_name=${PROJECT_NAME}" \
  -d "request_date=${CURRENT_DATE}" \
  -d "master_key=${MASTER_KEY}")

echo "$KEYGEN_RESPONSE" | jq '.'

# 프로젝트 키 추출
PROJECT_KEY=$(echo "$KEYGEN_RESPONSE" | jq -r '.project_key')
echo "추출된 프로젝트 키: $PROJECT_KEY"
echo ""

# 3. 프로젝트 API 엔드포인트 테스트
echo "3. 프로젝트 API 엔드포인트 테스트"
echo "--------------------------------"
PROJECT_API_NAME="test_project_api_${TIMESTAMP}"

PROJECT_API_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/projects/" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_name\": \"${PROJECT_API_NAME}\",
    \"master_key\": \"${MASTER_KEY}\"
  }")

echo "$PROJECT_API_RESPONSE" | jq '.'

# 두 번째 프로젝트 키 추출
PROJECT_KEY_2=$(echo "$PROJECT_API_RESPONSE" | jq -r '.project_key')
echo "추출된 두 번째 프로젝트 키: $PROJECT_KEY_2"
echo ""

# 4. 첫 번째 프로젝트 키로 파일 업로드 테스트
echo "4. 첫 번째 프로젝트 키로 파일 업로드 테스트"
echo "-------------------------------------------"

# 테스트 파일 생성
TEST_FILE="test_upload_${TIMESTAMP}.txt"
echo "Test file content - $(date -Iseconds)" > "$TEST_FILE"
echo "This is a test file for upload functionality." >> "$TEST_FILE"

UPLOAD_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/files/upload" \
  -H "Authorization: Bearer ${PROJECT_KEY}" \
  -F "file=@${TEST_FILE}")

echo "$UPLOAD_RESPONSE" | jq '.'

# 파일 ID 추출
FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.file_id')
echo "업로드된 파일 ID: $FILE_ID"
echo ""

# 5. 파일 정보 조회 테스트
echo "5. 파일 정보 조회 테스트"
echo "-----------------------"
curl -s -X GET "${BASE_URL}/api/v1/files/${FILE_ID}" \
  -H "Authorization: Bearer ${PROJECT_KEY}" | jq '.'
echo ""

# 6. 파일 다운로드 테스트
echo "6. 파일 다운로드 테스트"
echo "-----------------------"
DOWNLOAD_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/files/${FILE_ID}/download" \
  -H "Authorization: Bearer ${PROJECT_KEY}")

echo "다운로드 응답 헤더:"
curl -s -I -X GET "${BASE_URL}/api/v1/files/${FILE_ID}/download" \
  -H "Authorization: Bearer ${PROJECT_KEY}" | grep -E "(HTTP|Content-|Content-Disposition)"

echo "다운로드된 파일 크기: $(echo "$DOWNLOAD_RESPONSE" | wc -c) bytes"
echo ""

# 7. 두 번째 프로젝트 키로 JSON 파일 업로드 테스트
echo "7. 두 번째 프로젝트 키로 JSON 파일 업로드 테스트"
echo "------------------------------------------------"

# JSON 테스트 파일 생성
JSON_FILE="test_data_${TIMESTAMP}.json"
cat > "$JSON_FILE" << EOF
{
  "test_data": "upload_test",
  "timestamp": "$(date -Iseconds)",
  "project_key": "${PROJECT_KEY_2:0:10}...",
  "file_type": "json"
}
EOF

JSON_UPLOAD_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/files/upload" \
  -H "Authorization: Bearer ${PROJECT_KEY_2}" \
  -F "file=@${JSON_FILE}")

echo "$JSON_UPLOAD_RESPONSE" | jq '.'

# JSON 파일 ID 추출
JSON_FILE_ID=$(echo "$JSON_UPLOAD_RESPONSE" | jq -r '.file_id')
echo "업로드된 JSON 파일 ID: $JSON_FILE_ID"
echo ""

# 8. 에러 케이스 테스트
echo "8. 에러 케이스 테스트"
echo "--------------------"

# 잘못된 프로젝트 키로 업로드 시도
echo "8.1. 잘못된 프로젝트 키로 업로드 시도"
ERROR_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/files/upload" \
  -H "Authorization: Bearer invalid_key" \
  -F "file=@${TEST_FILE}")
echo "$ERROR_RESPONSE" | jq '.'
echo ""

# 파일 없이 업로드 시도
echo "8.2. 파일 없이 업로드 시도"
NO_FILE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/files/upload" \
  -H "Authorization: Bearer ${PROJECT_KEY}")
echo "$NO_FILE_RESPONSE" | jq '.'
echo ""

# 존재하지 않는 파일 다운로드 시도
echo "8.3. 존재하지 않는 파일 다운로드 시도"
FAKE_FILE_ID="00000000-0000-0000-0000-000000000000"
NOT_FOUND_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/files/${FAKE_FILE_ID}/download" \
  -H "Authorization: Bearer ${PROJECT_KEY}")
echo "$NOT_FOUND_RESPONSE" | jq '.'
echo ""

# 9. 정리
echo "9. 테스트 파일 정리"
echo "------------------"
rm -f "$TEST_FILE" "$JSON_FILE"
echo "테스트 파일 삭제 완료"
echo ""

echo "=========================================="
echo "Keygen과 Upload 기능 연동 테스트 완료"
echo "테스트 시간: $(date)"
echo "==========================================" 