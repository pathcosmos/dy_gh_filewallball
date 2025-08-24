# FileWallBall API 프로덕션 배포 가이드

## 📋 개요

이 가이드는 FileWallBall API를 프로덕션 환경에 배포하는 방법을 설명합니다.

## 🚀 빠른 시작

### 1. 환경 변수 설정

```bash
# 프로덕션 환경 변수 파일 복사
cp .env.example .env.prod

# 필수 환경 변수 설정
ENVIRONMENT="production"
DEBUG=false
LOG_LEVEL="WARNING"
SECRET_KEY="your-super-secret-production-key"
CORS_ORIGINS="*"
```

### 2. 프로덕션 환경 시작

```bash
# 프로덕션 환경 시작
docker-compose --env-file .env.prod up -d

# 서비스 상태 확인
docker-compose --env-file .env.prod ps

# 로그 확인
docker-compose --env-file .env.prod logs -f app
```

## ⚙️ 환경별 설정

### 개발 환경 (.env.dev)
- `DEBUG=true`
- `LOG_LEVEL=DEBUG`
- `ENVIRONMENT=development`
- 로컬 Docker 컨테이너 사용

### 프로덕션 환경 (.env.prod)
- `DEBUG=false`
- `LOG_LEVEL=WARNING`
- `ENVIRONMENT=production`
- 외부 데이터베이스 사용

## 🔧 Docker Compose 명령어

### 환경별 서비스 관리

```bash
# 개발 환경
docker-compose --env-file .env.dev up -d
docker-compose --env-file .env.dev down

# 프로덕션 환경
docker-compose --env-file .env.prod up -d
docker-compose --env-file .env.prod down
```

### 서비스 모니터링

```bash
# 서비스 상태 확인
docker-compose --env-file .env.prod ps

# 리소스 사용량 확인
docker stats

# 로그 실시간 모니터링
docker-compose --env-file .env.prod logs -f app
```

## 📊 헬스체크 및 모니터링

### API 헬스체크

```bash
# 헬스체크 엔드포인트
curl http://localhost:8000/health

# 파일 목록 확인
curl http://localhost:8000/files
```

### 서비스 헬스체크

```bash
# MariaDB 헬스체크
docker-compose --env-file .env.prod exec mariadb mysqladmin ping -h localhost -u root -p

# Redis 헬스체크 (선택사항)
docker-compose --env-file .env.prod exec redis redis-cli ping
```

## 🔒 보안 설정

### 환경 변수 보안

- `SECRET_KEY`: 강력한 비밀키 사용
- `DB_PASSWORD`: 데이터베이스 비밀번호 보안
- `CORS_ORIGINS`: 허용된 도메인만 설정

### 컨테이너 보안

- `no-new-privileges: true`
- `read_only: true` (Nginx)
- 비루트 사용자 실행

## 📈 성능 최적화

### 리소스 제한

```yaml
# docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
    reservations:
      memory: 512M
      cpus: '0.5'
```

### 워커 프로세스

```bash
# 4개 워커 프로세스로 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🚨 문제 해결

### 일반적인 문제

1. **환경 변수 로드 실패**
   - `.env.prod` 파일 존재 확인
   - 필수 환경 변수 설정 확인

2. **데이터베이스 연결 실패**
   - 데이터베이스 서비스 상태 확인
   - 환경 변수 설정 확인

3. **권한 문제**
   - 볼륨 마운트 권한 확인
   - 컨테이너 내부 사용자 권한 확인

### 로그 분석

```bash
# 애플리케이션 로그
docker-compose --env-file .env.prod logs app

# 데이터베이스 로그
docker-compose --env-file .env.prod logs mariadb

# 전체 로그
docker-compose --env-file .env.prod logs
```

## 📝 배포 체크리스트

### 배포 전 확인사항

- [ ] 환경 변수 파일 설정 완료
- [ ] 데이터베이스 연결 확인
- [ ] 보안 설정 검증
- [ ] 리소스 제한 설정 확인

### 배포 후 확인사항

- [ ] 서비스 정상 시작 확인
- [ ] 헬스체크 통과 확인
- [ ] API 엔드포인트 동작 확인
- [ ] 로그 모니터링 설정

## 🔄 업데이트 및 배포

### 코드 업데이트

```bash
# 코드 변경 후 이미지 재빌드
docker-compose --env-file .env.prod build app

# 서비스 재시작
docker-compose --env-file .env.prod restart app
```

### 롤백

```bash
# 이전 이미지로 롤백
docker-compose --env-file .env.prod up -d app:previous-tag
```

## 📞 지원 및 문의

문제가 발생하거나 추가 지원이 필요한 경우:

1. 로그 파일 확인
2. 환경 변수 설정 검증
3. Docker Compose 설정 확인
4. 시스템 리소스 상태 확인

---

**마지막 업데이트**: 2025년 8월 24일
**버전**: 1.0.0
