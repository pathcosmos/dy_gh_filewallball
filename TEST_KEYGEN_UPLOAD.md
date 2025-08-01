# Keygen과 Upload 기능 연동 테스트 가이드

이 문서는 keygen 기능과 upload 기능의 연동 테스트 방법을 설명합니다.

## 📋 테스트 개요

### 테스트 대상 기능
1. **Keygen 엔드포인트** (`/keygen`)
   - 프로젝트 키 생성
   - 마스터 키 검증
   - 데이터베이스 저장

2. **프로젝트 API 엔드포인트** (`/api/v1/projects/`)
   - 프로젝트 키 생성 (JSON 형식)
   - JWT 토큰 생성

3. **파일 업로드 엔드포인트** (`/api/v1/files/upload`)
   - 프로젝트 키 인증
   - 파일 업로드 및 저장
   - 메타데이터 생성

4. **파일 다운로드 엔드포인트** (`/api/v1/files/{file_id}/download`)
   - 파일 스트리밍 다운로드
   - 인증 검증

5. **파일 정보 조회 엔드포인트** (`/api/v1/files/{file_id}`)
   - 파일 메타데이터 조회
   - 통계 정보 포함

## 🚀 테스트 실행 방법

### 1. 서버 실행
```bash
# 애플리케이션 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Python 스크립트 테스트
```bash
# 종합 테스트 스크립트 실행
python test_keygen_upload_integration.py
```

### 3. Curl 스크립트 테스트
```bash
# curl 기반 테스트 스크립트 실행
./test_keygen_upload_curl.sh
```

### 4. 수동 테스트
```bash
# 1. 헬스체크
curl -X GET "http://localhost:8000/health"

# 2. 프로젝트 키 생성
curl -X POST "http://localhost:8000/keygen" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "project_name=test_project" \
  -d "request_date=20241201" \
  -d "master_key=dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="

# 3. 파일 업로드
curl -X POST "http://localhost:8000/api/v1/files/upload" \
  -H "Authorization: Bearer YOUR_PROJECT_KEY" \
  -F "file=@test_file.txt"

# 4. 파일 정보 조회
curl -X GET "http://localhost:8000/api/v1/files/FILE_ID" \
  -H "Authorization: Bearer YOUR_PROJECT_KEY"

# 5. 파일 다운로드
curl -X GET "http://localhost:8000/api/v1/files/FILE_ID/download" \
  -H "Authorization: Bearer YOUR_PROJECT_KEY" \
  -o downloaded_file.txt
```

## 📊 테스트 시나리오

### 기본 워크플로우
1. **프로젝트 키 생성** → **파일 업로드** → **파일 정보 조회** → **파일 다운로드**

### 상세 테스트 케이스
1. **정상 케이스**
   - 텍스트 파일 업로드
   - JSON 파일 업로드
   - 다중 파일 업로드
   - 파일 정보 조회
   - 파일 다운로드

2. **에러 케이스**
   - 잘못된 프로젝트 키
   - 파일 없이 업로드
   - 존재하지 않는 파일 다운로드
   - 잘못된 마스터 키

3. **성능 테스트**
   - 동시 업로드
   - 대용량 파일 업로드
   - 연속 업로드

## 🔧 설정 정보

### 마스터 키
```
dysnt2025FileWallersBallKAuEZzTAsBjXiQ==
```

### API 엔드포인트
- **Keygen**: `POST /keygen`
- **프로젝트 API**: `POST /api/v1/projects/`
- **파일 업로드**: `POST /api/v1/files/upload`
- **파일 정보**: `GET /api/v1/files/{file_id}`
- **파일 다운로드**: `GET /api/v1/files/{file_id}/download`

### 인증 방식
- **Bearer Token**: `Authorization: Bearer {project_key}`
- **Form Data**: 프로젝트 키 생성 시
- **JSON**: 프로젝트 API 사용 시

## 📝 예상 결과

### 성공 응답 예시
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "download_url": "/api/v1/files/550e8400-e29b-41d4-a716-446655440000/download",
  "original_filename": "test.txt",
  "file_size": 1024,
  "mime_type": "text/plain",
  "message": "File uploaded successfully"
}
```

### 에러 응답 예시
```json
{
  "detail": "Invalid project key"
}
```

## 🐛 문제 해결

### 일반적인 문제들
1. **서버 연결 실패**
   - 서버가 실행 중인지 확인
   - 포트 8000이 사용 가능한지 확인

2. **인증 실패**
   - 프로젝트 키가 올바른지 확인
   - Bearer 토큰 형식이 올바른지 확인

3. **파일 업로드 실패**
   - 파일 크기 제한 확인 (100MB)
   - 파일 형식 지원 여부 확인
   - 저장 디렉토리 권한 확인

4. **데이터베이스 오류**
   - 데이터베이스 연결 상태 확인
   - 테이블 스키마 확인

### 로그 확인
```bash
# 애플리케이션 로그 확인
tail -f logs/app.log

# 데이터베이스 로그 확인
tail -f logs/database.log
```

## 📈 성능 모니터링

### 메트릭 확인
```bash
# Prometheus 메트릭 확인
curl -X GET "http://localhost:8000/metrics"

# 상세 메트릭 확인
curl -X GET "http://localhost:8000/api/v1/metrics/detailed"
```

### 헬스체크
```bash
# 기본 헬스체크
curl -X GET "http://localhost:8000/health"

# 상세 헬스체크
curl -X GET "http://localhost:8000/health/detailed"
```

## 🔄 지속적 테스트

### 자동화된 테스트
```bash
# 주기적 테스트 실행 (cron 사용)
0 */6 * * * /path/to/test_keygen_upload_curl.sh >> /var/log/test.log 2>&1
```

### 모니터링 스크립트
```bash
# 테스트 결과 모니터링
watch -n 30 'python test_keygen_upload_integration.py | tail -20'
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 서버 로그
2. 데이터베이스 상태
3. 네트워크 연결
4. 파일 시스템 권한

테스트 결과나 문제점은 이슈로 등록해주세요. 