# FileWallBall 인프라 설정 체크리스트

## 🔍 현재 상태 분석

### ✅ 이미 완료된 설정
- **MariaDB 연결**: pathcosmos.iptime.org:33377 정상 연결
- **파일 저장소**: ./uploads 디렉토리 생성 및 파일 저장 중
- **디스크 공간**: 1.5TB 사용 가능 (충분함)
- **애플리케이션**: FastAPI 서버 정상 동작

## 🚨 추가 고려해야 할 인프라 설정들

### 1. 🔒 **보안 설정**

#### SECRET_KEY 설정
**현재 문제**: 개발용 기본값 사용 중
```python
secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
```

**해결 방법**:
```bash
# 강력한 SECRET_KEY 생성 및 설정
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

#### CORS 설정 강화
**현재 문제**: 모든 도메인 허용 (`["*"]`)
```python
cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
```

**권장 설정**:
```bash
# 특정 도메인만 허용
export CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

### 2. 📁 **파일 저장소 관리**

#### 업로드 디렉토리 권한
**현재 상태**: 755 권한 (적절함)
```bash
chmod 755 ./uploads
```

#### 파일 정리 정책
**필요한 설정**: 자동 정리 스크립트
```bash
# 30일 이상 된 파일 자동 삭제 (예시)
find ./uploads -type f -mtime +30 -delete
```

#### 백업 정책
**권장 설정**:
```bash
# 일일 백업 스크립트
rsync -av ./uploads/ backup_server:/path/to/backup/$(date +%Y%m%d)/
```

### 3. 📊 **로깅 및 모니터링**

#### 로그 파일 설정
**현재 문제**: 로그가 콘솔에만 출력됨
```python
log_file: Optional[str] = Field(default=None, env="LOG_FILE")
```

**권장 설정**:
```bash
export LOG_FILE="/var/log/filewallball/app.log"
mkdir -p /var/log/filewallball
```

#### 로그 순환 설정
**필요한 설정**: logrotate 구성
```bash
# /etc/logrotate.d/filewallball
/var/log/filewallball/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        systemctl reload filewallball || true
    endscript
}
```

### 4. 🔧 **시스템 서비스 설정**

#### systemd 서비스 파일
**권장 설정**: `/etc/systemd/system/filewallball.service`
```ini
[Unit]
Description=FileWallBall API
After=network.target

[Service]
Type=exec
User=lanco
WorkingDirectory=/home/lanco/cursor/temp_git/dy_gh_filewallball
ExecStart=/home/lanco/cursor/temp_git/dy_gh_filewallball/.venv/bin/uvicorn app.main_simple:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
Environment=DB_HOST=pathcosmos.iptime.org
Environment=SECRET_KEY=your-secret-key-here

[Install]
WantedBy=multi-user.target
```

#### 서비스 활성화
```bash
sudo systemctl daemon-reload
sudo systemctl enable filewallball
sudo systemctl start filewallball
```

### 5. 🌐 **네트워크 및 방화벽**

#### 방화벽 설정
**필요한 포트**: 8000 (API 서버)
```bash
# UFW 사용 시
sudo ufw allow 8000/tcp

# iptables 사용 시
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

#### 리버스 프록시 (권장)
**Nginx 설정** (`/etc/nginx/sites-available/filewallball`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. 📈 **성능 최적화**

#### 업로드 크기 제한
**현재**: 100MB 기본값
```python
max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")
```

**고려사항**: 서버 리소스에 따라 조정 필요

#### 동시 연결 수 제한
**Uvicorn 설정**:
```bash
uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. 🔐 **데이터베이스 보안**

#### MariaDB 연결 보안
**현재**: 평문 비밀번호 설정 파일에 노출
**권장**: 환경변수 또는 시크릿 관리 도구 사용

#### 연결 풀 모니터링
**현재 설정**:
```python
db_pool_size: int = 10
db_max_overflow: int = 20
```

**모니터링**: 연결 풀 사용량 추적 필요

### 8. 💾 **백업 및 재해 복구**

#### 데이터베이스 백업
**자동 백업 스크립트**:
```bash
#!/bin/bash
# daily-backup.sh
mysqldump -h pathcosmos.iptime.org -P 33377 -u filewallball -p'password' filewallball > backup_$(date +%Y%m%d).sql
```

#### 파일 백업
**rsync 기반 증분 백업**:
```bash
rsync -av --link-dest=/backup/latest /uploads/ /backup/$(date +%Y%m%d)/
```

### 9. 📊 **헬스 체크 및 알림**

#### 외부 모니터링
**API 엔드포인트**: `/health` 활용
```bash
# 헬스 체크 스크립트
curl -f http://localhost:8000/health || echo "Service Down" | mail admin@domain.com
```

#### 디스크 공간 모니터링
```bash
# 디스크 사용률 90% 초과 시 알림
df /home | awk 'NR==2 {if($5+0 > 90) print "Disk usage high: " $5}'
```

## 🎯 **우선순위별 설정 권장 사항**

### **즉시 설정 필요 (HIGH)**
1. ✅ SECRET_KEY 강화
2. ✅ CORS 도메인 제한
3. ✅ systemd 서비스 등록
4. ✅ 방화벽 규칙 설정

### **단기간 내 설정 권장 (MEDIUM)**
1. 📊 로그 파일 및 순환 설정
2. 🌐 Nginx 리버스 프록시
3. 💾 자동 백업 스크립트
4. 📈 성능 모니터링

### **장기적 고려사항 (LOW)**
1. 📡 외부 모니터링 시스템
2. 🔄 로드 밸런싱
3. 📦 컨테이너화 (필요시)
4. 🌍 CDN 연동 (글로벌 서비스 시)

## 💡 **설정 스크립트 예시**

다음 스크립트로 기본적인 운영 환경을 빠르게 구성할 수 있습니다:

```bash
#!/bin/bash
# setup-production.sh

# 1. 강력한 SECRET_KEY 생성
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

# 2. 로그 디렉토리 생성
sudo mkdir -p /var/log/filewallball
sudo chown lanco:lanco /var/log/filewallball

# 3. 환경변수 설정
echo "SECRET_KEY=$SECRET_KEY" >> .env
echo "LOG_FILE=/var/log/filewallball/app.log" >> .env

# 4. systemd 서비스 설치
sudo cp filewallball.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable filewallball

echo "✅ 기본 운영 환경 설정 완료"
```