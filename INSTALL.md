# FileWallBall 설치 가이드

## 📋 개요

FileWallBall은 다양한 방법으로 설치할 수 있는 안전한 파일 업로드/관리 API 시스템입니다. 이 문서는 여러 설치 방법을 제공합니다.

## 🚀 빠른 시작

### 방법 1: 자동 설치 스크립트 (권장)

```bash
# 저장소 클론
git clone <repository-url>
cd fileWallBall

# 자동 설치 (uv 사용)
./install.sh uv

# 또는 pip 사용
./install.sh pip

# 또는 Docker 사용
./install.sh docker
```

### 방법 2: 수동 설치

#### 2.1 uv를 사용한 설치 (권장)

```bash
# 1. uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 의존성 설치
uv sync --dev

# 3. 환경 설정
cp env.example .env
# .env 파일 편집

# 4. 개발 서버 실행
./scripts/dev.sh run
```

#### 2.2 pip를 사용한 설치

```bash
# 1. Python 3.11+ 설치 확인
python --version

# 2. 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. 환경 설정
cp env.example .env
# .env 파일 편집

# 4. 개발 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2.3 setup.py를 사용한 설치

```bash
# 1. 개발 모드로 설치
pip install -e .[dev]

# 2. 환경 설정
cp env.example .env
# .env 파일 편집

# 3. 개발 서버 실행
filewallball
```

## 🐳 Docker 설치

### 단일 컨테이너 실행

```bash
# 1. Docker 이미지 빌드
docker build -t filewallball:latest .

# 2. 환경 변수 설정
cp env.example .env
# .env 파일 편집

# 3. 컨테이너 실행
docker run -p 8000:8000 --env-file .env filewallball:latest
```

### Docker Compose를 사용한 전체 스택 실행

```bash
# 1. 전체 스택 실행 (개발 환경)
docker-compose up -d

# 2. 로그 확인
docker-compose logs -f filewallball

# 3. 서비스 중지
docker-compose down
```

### 프로덕션 환경 실행

```bash
# 프로덕션 프로필로 실행
docker-compose --profile production up -d
```

## ☸️ Kubernetes 설치

### MicroK8s 환경

```bash
# 1. MicroK8s 배포 스크립트 실행
./scripts/deploy.sh

# 2. 배포 상태 확인
kubectl get pods -n filewallball
kubectl get svc -n filewallball
```

### 수동 Kubernetes 배포

```bash
# 1. 네임스페이스 생성
kubectl apply -f k8s/namespace.yaml

# 2. ConfigMap 및 Secret 배포
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/02-configmap-secret.yaml

# 3. 데이터베이스 배포
kubectl apply -f k8s/mariadb-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml

# 4. 애플리케이션 배포
kubectl apply -f k8s/03-deployment-service.yaml

# 5. Ingress 배포
kubectl apply -f k8s/ingress.yaml
```

## 🔧 환경 설정

### 필수 환경 변수

```bash
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=3306
DB_NAME=filewallball_db
DB_USER=filewallball_user
DB_PASSWORD=your_password

# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# 애플리케이션 설정
SECRET_KEY=your-super-secret-key
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=104857600
```

### 환경별 설정

#### 개발 환경
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

#### 프로덕션 환경
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

## 📊 모니터링 설정

### Prometheus 메트릭

```bash
# 메트릭 엔드포인트 확인
curl http://localhost:8000/metrics
```

### Grafana 대시보드

```bash
# Grafana 접속
# URL: http://localhost:3000
# Username: admin
# Password: admin
```

## 🧪 설치 검증

### 1. 애플리케이션 상태 확인

```bash
# 헬스체크
curl http://localhost:8000/health

# 상세 헬스체크
curl http://localhost:8000/health/detailed
```

### 2. API 문서 확인

```bash
# Swagger UI
# URL: http://localhost:8000/docs

# ReDoc
# URL: http://localhost:8000/redoc
```

### 3. 테스트 실행

```bash
# 전체 테스트
./scripts/dev.sh test

# 커버리지 포함 테스트
./scripts/dev.sh test-cov

# 통합 테스트
make test-integration
```

## 🔍 문제 해결

### 일반적인 문제들

#### 1. 포트 충돌
```bash
# 포트 사용 확인
netstat -tulpn | grep :8000

# 다른 포트로 실행
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### 2. 데이터베이스 연결 실패
```bash
# 데이터베이스 상태 확인
mysql -h localhost -u filewallball_user -p filewallball_db

# 연결 문자열 확인
echo $DATABASE_URL
```

#### 3. Redis 연결 실패
```bash
# Redis 상태 확인
redis-cli ping

# Redis 연결 테스트
redis-cli -h localhost -p 6379 -a your_password ping
```

#### 4. 권한 문제
```bash
# 업로드 디렉토리 권한 설정
chmod 755 uploads/
chown -R $USER:$USER uploads/
```

### 로그 확인

```bash
# 애플리케이션 로그
tail -f logs/app.log

# Docker 로그
docker logs -f filewallball

# Kubernetes 로그
kubectl logs -f deployment/filewallball-deployment -n filewallball
```

## 📚 추가 문서

- [프로젝트 개요](docs/project-overview.md)
- [API 엔드포인트 가이드](docs/api-endpoints-guide.md)
- [배포 및 운영 가이드](docs/deployment-operations-guide.md)
- [보안 및 인증 가이드](docs/security-authentication-guide.md)

## 🤝 지원

문제가 발생하거나 질문이 있으시면:

1. [GitHub Issues](https://github.com/filewallball/api/issues)에 등록
2. 문서를 확인: [docs/](docs/) 폴더
3. 개발팀 문의: dev@filewallball.com

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
