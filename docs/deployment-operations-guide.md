# FileWallBall 배포 및 운영 가이드

## 🚀 개요

FileWallBall의 배포 및 운영 가이드는 시스템을 프로덕션 환경에 안전하고 효율적으로 배포하고 운영하기 위한 절차와 모범 사례를 설명합니다.

## 🐳 Docker 배포

### Dockerfile 최적화

```dockerfile
# 멀티스테이지 빌드
FROM python:3.11-slim as builder

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로덕션 이미지
FROM python:3.11-slim

# 런타임 의존성 설치
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 애플리케이션 코드 복사
COPY . .

# 비root 사용자 생성
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/filewallball
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=filewallball
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## ☸️ Kubernetes 배포

### 네임스페이스 설정

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: filewallball
  labels:
    name: filewallball
```

### ConfigMap 설정

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filewallball-config
  namespace: filewallball
data:
  DATABASE_URL: "postgresql://user:password@filewallball-db:5432/filewallball"
  REDIS_HOST: "filewallball-redis"
  REDIS_PORT: "6379"
  LOG_LEVEL: "INFO"
  MAX_FILE_SIZE: "104857600"
```

### Secret 설정

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: filewallball-secret
  namespace: filewallball
type: Opaque
data:
  REDIS_PASSWORD: ZmlsZXdhbGxiYWxsMjAyNA==  # base64 encoded
  DATABASE_PASSWORD: cGFzc3dvcmQ=  # base64 encoded
  JWT_SECRET: c2VjcmV0LWtleQ==  # base64 encoded
```

### 애플리케이션 배포

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: filewallball-app
  namespace: filewallball
spec:
  replicas: 3
  selector:
    matchLabels:
      app: filewallball
  template:
    metadata:
      labels:
        app: filewallball
    spec:
      containers:
      - name: app
        image: filewallball:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: filewallball-config
              key: DATABASE_URL
        - name: REDIS_HOST
          valueFrom:
            configMapKeyRef:
              name: filewallball-config
              key: REDIS_HOST
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: filewallball-secret
              key: REDIS_PASSWORD
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: uploads
        persistentVolumeClaim:
          claimName: filewallball-uploads-pvc
      - name: logs
        persistentVolumeClaim:
          claimName: filewallball-logs-pvc
```

### 서비스 설정

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: filewallball-service
  namespace: filewallball
spec:
  selector:
    app: filewallball
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress 설정

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: filewallball-ingress
  namespace: filewallball
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - filewallball.example.com
    secretName: filewallball-tls
  rules:
  - host: filewallball.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: filewallball-service
            port:
              number: 80
```

## 🔄 CI/CD 파이프라인

### GitHub Actions 워크플로우

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio

    - name: Run tests
      run: |
        pytest tests/ -v

    - name: Run linting
      run: |
        pip install flake8 black
        flake8 app/
        black --check app/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          ${{ secrets.DOCKER_USERNAME }}/filewallball:latest
          ${{ secrets.DOCKER_USERNAME }}/filewallball:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up kubectl
      uses: azure/setup-kubectl@v3

    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig

    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f k8s/namespace.yaml
        kubectl apply -f k8s/configmap.yaml
        kubectl apply -f k8s/secret.yaml
        kubectl apply -f k8s/deployment.yaml
        kubectl apply -f k8s/service.yaml
        kubectl apply -f k8s/ingress.yaml

        # 롤링 업데이트
        kubectl rollout restart deployment/filewallball-app -n filewallball
        kubectl rollout status deployment/filewallball-app -n filewallball
```

## 📊 모니터링 및 로깅

### Prometheus 설정

```yaml
# k8s/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s

    scrape_configs:
    - job_name: 'filewallball'
      static_configs:
      - targets: ['filewallball-service.filewallball.svc.cluster.local:8000']
      metrics_path: '/metrics'
      scrape_interval: 15s

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config
```

### Grafana 대시보드

```yaml
# k8s/grafana.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: grafana-secret
              key: admin-password
        volumeMounts:
        - name: dashboards
          mountPath: /var/lib/grafana/dashboards
      volumes:
      - name: dashboards
        configMap:
          name: grafana-dashboards
```

## 🔧 운영 스크립트

### 배포 스크립트

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

# 환경 변수 설정
ENVIRONMENT=${1:-production}
NAMESPACE="filewallball"

echo "Deploying FileWallBall to $ENVIRONMENT..."

# Kubernetes 리소스 적용
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 롤링 업데이트
kubectl rollout restart deployment/filewallball-app -n $NAMESPACE

# 배포 상태 확인
kubectl rollout status deployment/filewallball-app -n $NAMESPACE

echo "Deployment completed successfully!"
```

### 백업 스크립트

```bash
#!/bin/bash
# scripts/backup.sh

set -e

# 백업 디렉토리 생성
BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "Starting backup to $BACKUP_DIR..."

# 데이터베이스 백업
kubectl exec -n filewallball deployment/filewallball-db -- \
  pg_dump -U user filewallball > $BACKUP_DIR/database.sql

# 파일 백업
kubectl cp filewallball/filewallball-app-xxx:/app/uploads $BACKUP_DIR/uploads

# Redis 백업
kubectl exec -n filewallball deployment/filewallball-redis -- \
  redis-cli BGSAVE

# 백업 압축
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

### 복구 스크립트

```bash
#!/bin/bash
# scripts/restore.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "Restoring from $BACKUP_FILE..."

# 백업 압축 해제
tar -xzf $BACKUP_FILE
BACKUP_DIR=$(basename $BACKUP_FILE .tar.gz)

# 데이터베이스 복구
kubectl exec -i -n filewallball deployment/filewallball-db -- \
  psql -U user filewallball < $BACKUP_DIR/database.sql

# 파일 복구
kubectl cp $BACKUP_DIR/uploads filewallball/filewallball-app-xxx:/app/uploads

# 정리
rm -rf $BACKUP_DIR

echo "Restore completed successfully!"
```

## 📋 운영 체크리스트

### 배포 전 확인사항

- [ ] 모든 테스트가 통과됨
- [ ] 코드 리뷰가 완료됨
- [ ] 보안 스캔이 통과됨
- [ ] 성능 테스트가 완료됨
- [ ] 백업이 생성됨
- [ ] 롤백 계획이 준비됨

### 배포 후 확인사항

- [ ] 애플리케이션이 정상 시작됨
- [ ] 헬스체크가 통과됨
- [ ] 메트릭이 정상 수집됨
- [ ] 로그가 정상 출력됨
- [ ] 기능 테스트가 통과됨
- [ ] 성능이 목표치 달성됨

### 정기 운영 점검

- [ ] 리소스 사용량 모니터링
- [ ] 로그 분석 및 정리
- [ ] 백업 상태 확인
- [ ] 보안 업데이트 적용
- [ ] 성능 최적화 검토
- [ ] 용량 계획 업데이트

---

이 문서는 FileWallBall의 배포 및 운영 절차를 설명합니다. 배포 관련 질문이나 개선 제안이 있으시면 운영팀에 문의해 주세요.
