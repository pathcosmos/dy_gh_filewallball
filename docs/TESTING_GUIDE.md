# FileWallBall API - 테스트 실행 가이드

이 문서는 FileWallBall API의 모든 테스트를 실행하는 방법을 설명합니다.

## 📋 **사전 요구사항**

### 🔧 **시스템 요구사항**
- Python 3.8+
- MySQL 데이터베이스
- 100MB 이상의 디스크 여유 공간
- 네트워크 접근 가능

### 📦 **Python 패키지**
```bash
# 필수 패키지 설치
pip install fastapi uvicorn sqlalchemy aiomysql psutil requests

# 또는 uv 사용
uv add fastapi uvicorn sqlalchemy aiomysql psutil requests
```

### 🗄️ **데이터베이스 설정**
```bash
# MySQL 연결 정보 확인
# .env 파일 또는 환경변수에 설정
DB_HOST=pathcosmos.iptime.org
DB_PORT=33377
DB_NAME=filewallball
DB_USER=filewallball
DB_PASSWORD=jK9#zQ$p&2@f!L7^xY*
```

## 🚀 **API 서버 시작**

### 1. **환경 변수 설정**
```bash
# .env 파일 생성 (필요한 경우)
cp .env.example .env
# 데이터베이스 연결 정보 수정
```

### 2. **API 서버 실행**
```bash
# 개발 모드로 실행
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 또는 프로덕션 모드
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. **서버 상태 확인**
```bash
curl http://127.0.0.1:8000/health
# 응답: {"status":"healthy","timestamp":"...","service":"FileWallBall API","version":"2.0.0"}
```

## 🧪 **테스트 실행 순서**

### 📊 **1. 기본 워크플로우 테스트**
```bash
# 실행 권한 부여
chmod +x test_workflow_simple.sh

# 테스트 실행
./test_workflow_simple.sh
```

**테스트 내용:**
- API 헬스체크
- 파일 업로드
- 파일 정보 조회
- 파일 다운로드
- MD5 무결성 검증
- 파일 목록 조회
- 정리 작업

**예상 결과:**
```
✅ API 헬스체크 성공
✅ 파일 업로드 성공
✅ 파일 정보 조회 성공
✅ 파일 다운로드 성공
✅ MD5 검증 성공
✅ 파일 목록 조회 성공
✅ 정리 작업 완료
```

### 🔍 **2. 다양한 파일 형식 테스트**
```bash
python3 test_file_formats.py
```

**테스트 내용:**
- 텍스트 파일 (.txt)
- 이미지 파일 (.jpg, .png)
- 바이너리 파일 (.bin)
- 대용량 파일 (100MB 이하)

**예상 결과:**
```
🚀 FileWallBall API 다양한 파일 형식 테스트 시작
✅ 텍스트 파일 테스트 완료
✅ 이미지 파일 테스트 완료
✅ 바이너리 파일 테스트 완료
✅ 대용량 파일 테스트 완료
```

### ⚠️ **3. 에러 처리 테스트**
```bash
python3 test_error_handling.py
```

**테스트 시나리오:**
- 404 에러: 존재하지 않는 파일 ID
- 413 에러: 파일 크기 제한 초과
- 400 에러: 잘못된 MIME 타입
- 422 에러: 잘못된 요청 형식
- 속도 제한: 연속 요청 처리
- 동시 요청: 동시성 처리

**예상 결과:**
```
🚀 FileWallBall API 에러 처리 및 예외 상황 테스트 시작
✅ 존재하지 않는 파일 ID 404 에러 테스트: PASS
✅ 파일 크기 제한 초과 413 에러 테스트: PASS
✅ 잘못된 MIME 타입 400 에러 테스트: PASS
✅ 잘못된 요청 형식 테스트: PASS
✅ 속도 제한 테스트: PASS
✅ 동시 요청 테스트: PASS
```

### 📈 **4. 성능 및 안정성 테스트**
```bash
python3 test_performance.py
```

**테스트 내용:**
- 헬스체크 엔드포인트 성능 (100회)
- 동시 업로드 성능 (10개 워커)
- 메모리 사용량 모니터링 (60초)
- Apache Bench 부하 테스트 (Apache Bench 설치 시)

**예상 결과:**
```
🚀 FileWallBall API 성능 및 안정성 테스트 시작
✅ 헬스체크 엔드포인트 성능 테스트: 성공
✅ 동시 업로드 성능 테스트: 성공
✅ 부하 상태에서의 메모리 사용량 모니터링: 성공
❌ Apache Bench 부하 테스트: 실패 (도구 미설치)
```

## 📊 **테스트 결과 확인**

### 📁 **생성되는 파일들**
```
test_workflow_simple.sh.log          # 워크플로우 테스트 로그
file_format_test_results.json        # 파일 형식 테스트 결과
error_handling_test_results.json     # 에러 처리 테스트 결과
performance_test_results.json        # 성능 테스트 결과
TEST_RESULTS_REPORT.md              # 종합 테스트 리포트
test_results_summary.csv             # 테스트 요약 (CSV)
performance_test_results.csv         # 성능 테스트 결과 (CSV)
```

### 📈 **결과 분석**
```bash
# JSON 결과 확인
cat performance_test_results.json | python3 -m json.tool

# CSV 결과 확인
cat performance_test_results.csv

# 종합 리포트 확인
cat TEST_RESULTS_REPORT.md
```

## 🔧 **문제 해결**

### ❌ **API 서버 연결 실패**
```bash
# 서버 상태 확인
ps aux | grep uvicorn

# 포트 사용 확인
netstat -tlnp | grep 8000

# 서버 재시작
pkill -f uvicorn
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### ❌ **데이터베이스 연결 실패**
```bash
# MySQL 서버 상태 확인
mysql -h pathcosmos.iptime.org -P 33377 -u filewallball -p

# 환경 변수 확인
echo $DB_HOST
echo $DB_PORT
echo $DB_NAME
```

### ❌ **파일 업로드 실패**
```bash
# 업로드 디렉토리 권한 확인
ls -la uploads/

# 디스크 공간 확인
df -h

# 로그 확인
tail -f app.log
```

### ❌ **테스트 스크립트 실행 실패**
```bash
# 실행 권한 확인
ls -la test_*.sh

# 권한 부여
chmod +x test_*.sh

# Python 버전 확인
python3 --version

# 의존성 확인
pip list | grep -E "(requests|psutil)"
```

## 📋 **테스트 체크리스트**

### ✅ **기본 기능 테스트**
- [ ] API 서버 시작 및 헬스체크
- [ ] 파일 업로드 (텍스트, 이미지, 바이너리)
- [ ] 파일 정보 조회
- [ ] 파일 다운로드 및 무결성 검증
- [ ] 파일 목록 조회 (페이징, 정렬)
- [ ] 파일 비활성화 (소프트 삭제)

### ✅ **에러 처리 테스트**
- [ ] 404 에러 (존재하지 않는 파일)
- [ ] 413 에러 (파일 크기 초과)
- [ ] 400 에러 (잘못된 MIME 타입)
- [ ] 422 에러 (잘못된 요청 형식)
- [ ] 속도 제한 및 동시성 처리

### ✅ **성능 테스트**
- [ ] 헬스체크 응답 시간 (< 100ms)
- [ ] 동시 업로드 처리 (10개 워커)
- [ ] 메모리 사용량 모니터링
- [ ] 시스템 리소스 효율성

### ✅ **문서화**
- [ ] 테스트 결과 리포트 생성
- [ ] CSV 데이터 생성
- [ ] 실행 가이드 작성
- [ ] 문제 해결 가이드 작성

## 🎯 **성능 목표**

| 지표 | 목표 | 현재 달성 | 상태 |
|------|------|-----------|------|
| 응답 시간 | < 100ms | 1.04ms | ✅ 초과 달성 |
| 처리량 | > 100 TPS | 959.36 TPS | ✅ 초과 달성 |
| 동시 처리 | > 5개 | 10개 | ✅ 달성 |
| 메모리 안정성 | 메모리 누수 없음 | 안정적 | ✅ 달성 |
| 가용성 | 99%+ | 100% | ✅ 달성 |

## 📞 **지원 및 문의**

테스트 실행 중 문제가 발생하거나 추가 지원이 필요한 경우:

1. **로그 확인**: 각 테스트 스크립트의 로그 파일 확인
2. **API 상태 확인**: `/health` 엔드포인트로 서버 상태 점검
3. **데이터베이스 연결**: MySQL 연결 상태 확인
4. **시스템 리소스**: CPU, 메모리, 디스크 사용량 확인

---

**마지막 업데이트**: 2025-08-24  
**문서 버전**: 1.0.0  
**API 버전**: 2.0.0
