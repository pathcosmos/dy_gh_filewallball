# FileWallBall 파일 저장소 경로 매핑 가이드

## 📋 개요

FileWallBall은 다양한 환경(개발, 프로덕션, Docker, Kubernetes)에서 호스트 OS의 특정 위치와 컨테이너 내부 경로를 유연하게 매핑할 수 있는 고급 파일 저장소 시스템을 제공합니다.

## 🏗️ 아키텍처

### 기본 구조
```
호스트 OS 경로 ←→ 컨테이너 내부 경로
     ↓
파일 저장소 서비스
     ↓
설정 기반 경로 결정
```

### 지원하는 저장소 타입
- **Local Storage**: 로컬 파일 시스템
- **S3 Storage**: Amazon S3 호환 스토리지
- **Azure Blob Storage**: Microsoft Azure Blob Storage
- **Google Cloud Storage**: Google Cloud Storage

## ⚙️ 설정 옵션

### 1. 기본 파일 저장소 설정

```bash
# 기본 업로드 디렉토리
UPLOAD_DIR=/app/uploads

# 최대 파일 크기 (100MB)
MAX_FILE_SIZE=104857600

# 허용된 파일 확장자
ALLOWED_EXTENSIONS=.txt,.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.mp4,.mp3,.zip,.rar,.7z
```

### 2. 고급 경로 매핑 설정

```bash
# 호스트 OS 경로 (Docker/K8s에서 볼륨 마운트용)
HOST_UPLOAD_DIR=./uploads

# 컨테이너 내부 경로
CONTAINER_UPLOAD_DIR=/app/uploads

# 저장소 타입 (local, s3, azure, gcs)
STORAGE_TYPE=local

# 로컬 저장소 설정
LOCAL_STORAGE_PATH=./uploads
```

### 3. 파일 저장 구조 설정

```bash
# 저장 구조 타입
# date: 날짜 기반 (YYYY/MM/DD)
# uuid: UUID 기반 계층 구조
# flat: 평면 구조 (모든 파일을 하나의 디렉토리에)
STORAGE_STRUCTURE=date

# 날짜 형식 (STORAGE_STRUCTURE=date일 때 사용)
STORAGE_DATE_FORMAT=%Y/%m/%d

# UUID 계층 깊이 (STORAGE_STRUCTURE=uuid일 때 사용)
STORAGE_UUID_DEPTH=2
```

## 🔧 환경별 설정

### 개발 환경

```bash
# 개발 환경 설정
ENVIRONMENT=development
STORAGE_TYPE=local
STORAGE_STRUCTURE=uuid
HOST_UPLOAD_DIR=./uploads
CONTAINER_UPLOAD_DIR=/app/uploads
```

**특징:**
- UUID 기반 계층 구조로 파일 분산
- 호스트 경로 직접 사용
- 빠른 개발 및 테스트

### 프로덕션 환경

```bash
# 프로덕션 환경 설정
ENVIRONMENT=production
STORAGE_TYPE=local
STORAGE_STRUCTURE=date
HOST_UPLOAD_DIR=/mnt/filewallball/prod/uploads
CONTAINER_UPLOAD_DIR=/app/uploads
```

**특징:**
- 날짜 기반 구조로 파일 정리
- 전용 스토리지 마운트
- 백업 및 관리 용이

## 🐳 Docker 환경 설정

### Docker Compose 설정

```yaml
version: '3.8'
services:
  filewallball:
    build: .
    environment:
      # 파일 저장소 설정
      - UPLOAD_DIR=/app/uploads
      - HOST_UPLOAD_DIR=./uploads
      - CONTAINER_UPLOAD_DIR=/app/uploads
      - STORAGE_TYPE=local
      - LOCAL_STORAGE_PATH=/app/uploads
      - STORAGE_STRUCTURE=date
      - STORAGE_DATE_FORMAT=%Y/%m/%d
      - STORAGE_UUID_DEPTH=2
    volumes:
      # 호스트 OS 경로를 컨테이너 내부 경로에 매핑
      - ./uploads:/app/uploads
      - ./logs:/app/logs
      - ./backups:/app/backups
      # 추가 볼륨 마운트 옵션들
      - filewallball_data:/app/data
      - filewallball_temp:/app/temp
```

### Docker 단일 컨테이너 실행

```bash
# 환경 변수 설정
export HOST_UPLOAD_DIR=/home/user/filewallball/uploads
export CONTAINER_UPLOAD_DIR=/app/uploads
export STORAGE_TYPE=local
export STORAGE_STRUCTURE=date

# Docker 실행
docker run -d \
  --name filewallball \
  -p 8000:8000 \
  -v $HOST_UPLOAD_DIR:$CONTAINER_UPLOAD_DIR \
  -e HOST_UPLOAD_DIR=$HOST_UPLOAD_DIR \
  -e CONTAINER_UPLOAD_DIR=$CONTAINER_UPLOAD_DIR \
  -e STORAGE_TYPE=$STORAGE_TYPE \
  -e STORAGE_STRUCTURE=$STORAGE_STRUCTURE \
  filewallball:latest
```

## ☸️ Kubernetes 환경 설정

### ConfigMap 설정

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filewallball-app-config
  namespace: filewallball
data:
  # 파일 업로드 설정 - 고급 경로 매핑
  HOST_UPLOAD_DIR: "/mnt/filewallball/uploads"
  CONTAINER_UPLOAD_DIR: "/app/uploads"
  STORAGE_TYPE: "local"
  LOCAL_STORAGE_PATH: "/app/uploads"
  STORAGE_STRUCTURE: "date"
  STORAGE_DATE_FORMAT: "%Y/%m/%d"
  STORAGE_UUID_DEPTH: "2"
```

### PersistentVolume 설정

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: filewallball-storage-pv
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  hostPath:
    path: /mnt/filewallball/uploads
  storageClassName: filewallball-storage
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: filewallball-storage-pvc
  namespace: filewallball
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: filewallball-storage
```

### Deployment 설정

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: filewallball-deployment
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
      - name: filewallball
        image: filewallball:latest
        env:
        - name: HOST_UPLOAD_DIR
          valueFrom:
            configMapKeyRef:
              name: filewallball-app-config
              key: HOST_UPLOAD_DIR
        - name: CONTAINER_UPLOAD_DIR
          valueFrom:
            configMapKeyRef:
              name: filewallball-app-config
              key: CONTAINER_UPLOAD_DIR
        - name: STORAGE_TYPE
          valueFrom:
            configMapKeyRef:
              name: filewallball-app-config
              key: STORAGE_TYPE
        - name: STORAGE_STRUCTURE
          valueFrom:
            configMapKeyRef:
              name: filewallball-app-config
              key: STORAGE_STRUCTURE
        volumeMounts:
        - name: filewallball-storage
          mountPath: /app/uploads
      volumes:
      - name: filewallball-storage
        persistentVolumeClaim:
          claimName: filewallball-storage-pvc
```

## 📁 파일 저장 구조

### 1. 날짜 기반 구조 (STORAGE_STRUCTURE=date)

```
uploads/
├── 2024/
│   ├── 01/
│   │   ├── 15/
│   │   │   ├── abc123.pdf
│   │   │   └── def456.jpg
│   │   └── 16/
│   │       └── ghi789.docx
│   └── 02/
│       └── 01/
│           └── jkl012.zip
└── 2023/
    └── 12/
        └── 31/
            └── mno345.png
```

**장점:**
- 날짜별 파일 정리
- 백업 및 아카이브 용이
- 파일 관리 직관적

### 2. UUID 기반 구조 (STORAGE_STRUCTURE=uuid)

```
uploads/
├── ab/
│   ├── c1/
│   │   ├── abc12345-6789-1234-5678-abcdef123456.pdf
│   │   └── abc12345-6789-1234-5678-abcdef123457.jpg
│   └── d2/
│       └── abd23456-7890-2345-6789-bcdef234567.docx
└── ef/
    └── 34/
        └── ef34567-8901-3456-7890-cdef345678.zip
```

**장점:**
- 파일 분산 저장
- 디렉토리 깊이 제한
- 성능 최적화

### 3. 평면 구조 (STORAGE_STRUCTURE=flat)

```
uploads/
├── abc12345-6789-1234-5678-abcdef123456.pdf
├── def23456-7890-2345-6789-bcdef234567.jpg
├── ghi34567-8901-3456-7890-cdef345678.docx
└── jkl45678-9012-4567-8901-def456789.zip
```

**장점:**
- 단순한 구조
- 빠른 파일 접근
- 디렉토리 오버헤드 없음

## 🔄 클라우드 스토리지 설정

### Amazon S3 설정

```bash
# S3 설정
STORAGE_TYPE=s3
S3_BUCKET=your-filewallball-bucket
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT_URL=https://s3.amazonaws.com
```

### Azure Blob Storage 설정

```bash
# Azure 설정
STORAGE_TYPE=azure
AZURE_CONNECTION_STRING=your-connection-string
AZURE_CONTAINER_NAME=filewallball-container
```

### Google Cloud Storage 설정

```bash
# GCS 설정
STORAGE_TYPE=gcs
GCS_BUCKET=your-filewallball-bucket
GCS_CREDENTIALS_FILE=path/to/credentials.json
```

## 🛠️ 설정 검증

### 설정 확인 스크립트

```bash
#!/bin/bash

echo "=== FileWallBall Storage Configuration ==="
echo "Environment: $ENVIRONMENT"
echo "Storage Type: $STORAGE_TYPE"
echo "Storage Structure: $STORAGE_STRUCTURE"
echo "Host Upload Dir: $HOST_UPLOAD_DIR"
echo "Container Upload Dir: $CONTAINER_UPLOAD_DIR"
echo "Effective Upload Dir: $(python -c 'from app.config import settings; print(settings.effective_upload_dir)')"

# 디렉토리 존재 확인
if [ -d "$HOST_UPLOAD_DIR" ]; then
    echo "✅ Host upload directory exists: $HOST_UPLOAD_DIR"
else
    echo "❌ Host upload directory missing: $HOST_UPLOAD_DIR"
fi

# 권한 확인
if [ -w "$HOST_UPLOAD_DIR" ]; then
    echo "✅ Host upload directory is writable"
else
    echo "❌ Host upload directory is not writable"
fi
```

### API를 통한 설정 확인

```bash
# 저장소 통계 조회
curl -X GET "http://localhost:8000/api/v1/storage/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 응답 예시
{
  "total_files": 150,
  "total_size_bytes": 1073741824,
  "total_size_mb": 1024.0,
  "file_types": {
    ".pdf": 50,
    ".jpg": 30,
    ".docx": 20,
    ".zip": 10
  },
  "disk_total_gb": 100.0,
  "disk_used_gb": 50.0,
  "disk_free_gb": 50.0,
  "storage_structure": "date",
  "base_path": "/app/uploads"
}
```

## 🔍 문제 해결

### 일반적인 문제들

#### 1. 권한 문제
```bash
# 호스트 디렉토리 권한 설정
sudo chown -R $USER:$USER /mnt/filewallball/uploads
sudo chmod -R 755 /mnt/filewallball/uploads

# Docker 컨테이너 내부 권한 설정
docker exec -it filewallball chown -R app:app /app/uploads
```

#### 2. 볼륨 마운트 문제
```bash
# Docker 볼륨 확인
docker inspect filewallball | grep -A 10 "Mounts"

# Kubernetes PVC 상태 확인
kubectl get pvc -n filewallball
kubectl describe pvc filewallball-storage-pvc -n filewallball
```

#### 3. 경로 매핑 문제
```bash
# 설정 확인
docker exec -it filewallball env | grep -E "(UPLOAD|STORAGE)"

# 파일 시스템 확인
docker exec -it filewallball ls -la /app/uploads
```

### 로그 확인

```bash
# 애플리케이션 로그
docker logs filewallball | grep -i "storage\|upload"

# Kubernetes 로그
kubectl logs deployment/filewallball-deployment -n filewallball | grep -i "storage"
```

## 📊 성능 최적화

### 1. 디스크 I/O 최적화

```bash
# SSD 사용 권장
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=/mnt/ssd/filewallball/uploads

# 파일 시스템 최적화
sudo mount -o noatime,nodiratime /dev/sdb1 /mnt/ssd
```

### 2. 캐싱 최적화

```bash
# Redis 캐시 설정
CACHE_TTL_FILE_METADATA=3600
CACHE_TTL_SESSION=86400
CACHE_TTL_TEMP=600
```

### 3. 병렬 처리 최적화

```bash
# 업로드 청크 크기
UPLOAD_CHUNK_SIZE=8192
DOWNLOAD_CHUNK_SIZE=8192
```

## 🔒 보안 고려사항

### 1. 파일 접근 제어

```bash
# 파일 권한 설정
chmod 644 /mnt/filewallball/uploads/*
chmod 755 /mnt/filewallball/uploads/*/

# 디렉토리 접근 제한
chmod 750 /mnt/filewallball/uploads
```

### 2. 네트워크 보안

```bash
# 방화벽 설정
sudo ufw allow from 10.0.0.0/8 to any port 8000
sudo ufw deny from any to any port 22
```

### 3. 암호화

```bash
# 파일 시스템 암호화
sudo cryptsetup luksFormat /dev/sdb1
sudo cryptsetup luksOpen /dev/sdb1 filewallball_crypt
```

## 📚 추가 리소스

### 관련 문서
- [프로젝트 개요](project-overview.md)
- [API 엔드포인트 가이드](api-endpoints-guide.md)
- [배포 및 운영 가이드](deployment-operations-guide.md)
- [보안 및 인증 가이드](security-authentication-guide.md)

### 외부 링크
- [Docker 볼륨 마운트](https://docs.docker.com/storage/volumes/)
- [Kubernetes PersistentVolumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Amazon S3 API](https://docs.aws.amazon.com/s3/index.html)
- [Azure Blob Storage](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)

---

이 가이드를 통해 FileWallBall의 파일 저장소 경로 매핑 기능을 효과적으로 활용할 수 있습니다. 추가 질문이나 문제가 있으시면 [GitHub Issues](https://github.com/filewallball/api/issues)에 등록해 주세요.
