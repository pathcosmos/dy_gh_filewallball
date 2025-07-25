# FileWallBall API System

FastAPI 기반의 파일 업로드/조회/다운로드 API 시스템입니다. MicroK8s 환경에서 구동되며, 실시간 요청에 따른 자동 스케일링을 지원합니다.

## 🚀 주요 기능

- **파일 업로드**: POST `/upload` - 파일 업로드 후 조회 URL 반환
- **파일 조회**: GET `/files/{file_id}` - 파일 정보 조회
- **파일 다운로드**: GET `/download/{file_id}` - 파일 다운로드
- **파일 미리보기**: GET `/view/{file_id}` - 텍스트 파일 미리보기
- **파일 목록**: GET `/files` - 업로드된 파일 목록 조회
- **파일 삭제**: DELETE `/files/{file_id}` - 파일 삭제
- **자동 스케일링**: HPA를 통한 실시간 스케일링
- **모니터링**: Prometheus 메트릭 제공

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client        │    │   Ingress       │    │   FastAPI       │
│   (Browser/App) │───▶│   Controller    │───▶│   Application   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Redis         │
                                              │   (Cache)       │
                                              └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Persistent    │
                                              │   Volume        │
                                              └─────────────────┘
```

## 📋 요구사항

- MicroK8s
- Docker
- kubectl
- curl, jq (테스트용)

## 🛠️ 설치 및 배포

### 1. 저장소 클론
```bash
git clone <repository-url>
cd fileWallBall
```

### 2. 배포 스크립트 실행
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. 배포 상태 확인
```bash
kubectl get pods -n filewallball
kubectl get svc -n filewallball
```

## 📖 API 사용법

### 파일 업로드
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_file.txt"
```

응답 예시:
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "your_file.txt",
  "download_url": "http://localhost:8000/download/550e8400-e29b-41d4-a716-446655440000",
  "view_url": "http://localhost:8000/view/550e8400-e29b-41d4-a716-446655440000",
  "message": "File uploaded successfully"
}
```

### 파일 정보 조회
```bash
curl "http://localhost:8000/files/{file_id}"
```

### 파일 다운로드
```bash
curl "http://localhost:8000/download/{file_id}" -o downloaded_file
```

### 파일 미리보기
```bash
curl "http://localhost:8000/view/{file_id}"
```

### 파일 목록 조회
```bash
curl "http://localhost:8000/files?limit=10&offset=0"
```

### 파일 삭제
```bash
curl -X DELETE "http://localhost:8000/files/{file_id}"
```

## 🧪 테스트

### API 테스트 실행
```bash
chmod +x scripts/test-api.sh
./scripts/test-api.sh
```

### 시스템 모니터링
```bash
chmod +x scripts/monitor.sh
./scripts/monitor.sh
```

## 📊 모니터링

### 메트릭 확인
```bash
curl "http://localhost:8000/metrics"
```

### 헬스체크
```bash
curl "http://localhost:8000/health"
```

### HPA 상태 확인
```bash
kubectl get hpa -n filewallball
```

## 🔧 설정

### 환경 변수
- `BASE_URL`: API 기본 URL
- `REDIS_HOST`: Redis 서버 호스트
- `REDIS_PORT`: Redis 서버 포트

### Kubernetes 설정
- **네임스페이스**: `filewallball`
- **Replicas**: 2-10 (HPA)
- **Storage**: 10Gi PersistentVolume
- **CPU Limit**: 200m
- **Memory Limit**: 256Mi

## 🚨 문제 해결

### Pod가 시작되지 않는 경우
```bash
kubectl describe pod -n filewallball <pod-name>
kubectl logs -n filewallball <pod-name>
```

### Redis 연결 문제
```bash
kubectl logs -n filewallball deployment/redis-deployment
```

### 스토리지 문제
```bash
kubectl get pvc -n filewallball
kubectl describe pvc -n filewallball filewallball-pvc
```

## 📈 성능 최적화

### 자동 스케일링 설정
- **CPU 임계값**: 70%
- **메모리 임계값**: 80%
- **최소 Replicas**: 2
- **최대 Replicas**: 10

### 캐시 설정
- Redis TTL: 24시간
- 파일 메타데이터 캐싱
- 해시값 계산 (백그라운드)

## 🔒 보안 고려사항

- 파일 업로드 크기 제한
- 허용된 파일 타입 검증
- CORS 설정
- 적절한 에러 처리

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

MIT License

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해주세요. 