# FileWallBall API - Simple Version

간단하고 깔끔한 파일 업로드/관리 API 시스템입니다.

## 🎯 특징

- **간단한 구조**: Redis, Docker 의존성 제거
- **외부 MariaDB**: 별도 설치된 MariaDB 사용
- **기본 기능**: 파일 업로드, 다운로드, 조회, 삭제
- **중복 제거**: SHA-256 해시 기반 파일 중복 방지
- **FastAPI**: 현대적인 Python 웹 프레임워크

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
# uv 사용 (권장)
uv sync

# 또는 pip 사용
pip install -r requirements.txt
```

### 2. 환경 설정

```bash
# 환경 변수 파일 복사
cp .env.simple .env

# 필요시 .env 파일 편집
nano .env
```

**기본 데이터베이스 설정**:
```env
DB_HOST="pathcosmos.iptime.org"
DB_PORT=33377
DB_NAME="filewallball"
DB_USER="filewallball"
DB_PASSWORD="jK9#zQ$p&2@f!L7^xY*"
```

### 3. 데이터베이스 연결 확인

```bash
# 데이터베이스 연결 테스트
uv run python test_db_connection.py
```


### 4. 데이터베이스 테이블 생성

```bash
# 직접 테이블 생성 (권장)
uv run python create_tables_direct.py

# 또는 Alembic 사용 (선택사항)
uv run alembic upgrade head
```

### 5. 애플리케이션 실행

```bash
# 간편 시작 스크립트 (권장)
./start_app.sh

# 또는 직접 실행
uv run uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API 사용법

### Health Check
```bash
curl http://localhost:8000/health
```

### 파일 업로드
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@your_file.txt"
```

### 파일 정보 조회
```bash
curl "http://localhost:8000/files/{file_id}"
```

### 파일 다운로드
```bash
curl "http://localhost:8000/download/{file_id}" -o downloaded_file
```

### 파일 목록 조회
```bash
curl "http://localhost:8000/files?limit=10&offset=0"
```

### 파일 삭제
```bash
curl -X DELETE "http://localhost:8000/files/{file_id}"
```

## 📁 프로젝트 구조

```
app/
├── main_simple.py          # 간단한 메인 애플리케이션
├── main.py                 # 기본 메인 애플리케이션 (더 많은 기능)
├── core/
│   └── config.py           # 설정 관리
├── database.py             # 데이터베이스 연결
├── models/
│   ├── orm_models.py       # SQLAlchemy 모델
│   └── api_models.py       # API 응답 모델
├── services/
│   ├── simple_file_service.py    # 간단한 파일 서비스
│   ├── file_storage_service.py   # 파일 저장 서비스
│   └── file_validation_service.py # 파일 검증 서비스
└── utils/
    ├── logging_config.py   # 로깅 설정
    └── database_helpers.py # 데이터베이스 유틸리티
```

## 🔧 개발 도구

```bash
# 개발 서버 시작
uv run uvicorn app.main_simple:app --reload

# 코드 포맷팅
uv run black app/
uv run isort app/

# 린팅
uv run flake8 app/

# 타입 체킹
uv run mypy app/

# 테스트 실행
uv run pytest tests/
```

## 📊 기능 비교

| 기능 | Simple Version | Full Version |
|------|----------------|--------------|
| 파일 업로드/다운로드 | ✅ | ✅ |
| 파일 중복 제거 | ✅ | ✅ |
| 파일 검증 | ✅ | ✅ |
| 기본 API | ✅ | ✅ |
| Redis 캐싱 | ❌ | ✅ |
| 고급 인증 | ❌ | ✅ |
| 배경 작업 | ❌ | ✅ |
| 썸네일 생성 | ❌ | ✅ |
| 감사 로그 | ❌ | ✅ |
| 레이트 리미팅 | ❌ | ✅ |

## 🔒 보안 고려사항

- 파일 타입 검증
- 파일 크기 제한
- SQL 인젝션 방지
- CORS 설정
- 적절한 에러 처리

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포할 수 있는 오픈소스 라이선스입니다.

## 📞 지원

문의사항: lanco.gh@gmail.com