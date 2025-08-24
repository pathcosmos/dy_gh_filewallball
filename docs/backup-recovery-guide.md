# FileWallBall 백업 및 복구 가이드

## 🔄 **개요**

FileWallBall 시스템의 백업 및 복구 전략을 설명합니다. 이 가이드는 데이터 손실을 방지하고 시스템 복구를 위한 포괄적인 방법을 제공합니다.

## 🏗️ **백업 아키텍처**

### **백업 구성 요소**
- **데이터베이스 백업**: MariaDB 전체 데이터베이스 덤프
- **파일 저장소 백업**: 업로드된 모든 파일 및 디렉토리
- **로그 백업**: 애플리케이션 및 시스템 로그
- **설정 백업**: Docker Compose 파일, Dockerfile, Nginx 설정

### **백업 서비스**
- **백업 컨테이너**: 전용 Ubuntu 22.04 기반 백업 서비스
- **자동화**: cron을 통한 스케줄링 지원
- **압축**: gzip을 통한 공간 절약
- **검증**: 백업 파일 무결성 자동 검증

## 🚀 **백업 시작하기**

### **1. 백업 서비스 시작**
```bash
# 백업 서비스 시작
docker-compose --profile backup up -d backup

# 백업 서비스 상태 확인
docker-compose ps backup
```

### **2. 수동 백업 실행**
```bash
# 전체 백업 실행
docker exec filewallball-backup scripts/backup-enhanced.sh

# 특정 백업 유형 지정
docker exec filewallball-backup scripts/backup-enhanced.sh --type full
docker exec filewallball-backup scripts/backup-enhanced.sh --type incremental
docker exec filewallball-backup scripts/backup-enhanced.sh --type differential
```

### **3. 백업 환경변수 설정**
```bash
# 백업 보존 기간 (일)
BACKUP_RETENTION_DAYS=30

# 압축 레벨 (1-9, 높을수록 압축률 증가)
COMPRESSION_LEVEL=6

# 백업 암호화 (GPG 키 필요)
ENCRYPT_BACKUP=false

# 백업 검증
VERIFY_BACKUP=true
```

## 📊 **백업 유형**

### **전체 백업 (Full Backup)**
- 모든 데이터를 완전히 백업
- 가장 안전하고 완전한 백업
- 시간과 공간이 많이 필요
- **권장**: 주간 또는 월간

### **증분 백업 (Incremental Backup)**
- 마지막 백업 이후 변경된 파일만 백업
- 빠르고 공간 효율적
- 복구 시 전체 백업 + 모든 증분 백업 필요
- **권장**: 일간

### **차등 백업 (Differential Backup)**
- 마지막 전체 백업 이후 변경된 모든 파일 백업
- 증분 백업보다 복구가 간단
- 전체 백업과 차등 백업만으로 복구 가능
- **권장**: 주간

## 🔍 **백업 모니터링**

### **백업 상태 확인**
```bash
# 백업 서비스 로그 확인
docker-compose logs backup

# 백업 디렉토리 내용 확인
docker exec filewallball-backup ls -la /host-backups/

# 백업 메타데이터 확인
docker exec filewallball-backup cat /host-backups/metadata/backup_manifest_*.json
```

### **백업 통계**
```bash
# 백업 파일 크기 및 개수
docker exec filewallball-backup find /host-backups -name "*.gz" -exec ls -lh {} \;

# 백업 보존 정책 확인
docker exec filewallball-backup find /host-backups -name "*.gz" -mtime +7
```

## 🔄 **복구 프로세스**

### **1. 사용 가능한 백업 확인**
```bash
# 백업 목록 조회
docker exec filewallball-backup scripts/restore-enhanced.sh --list

# 특정 백업 유형별 목록
docker exec filewallball-backup scripts/restore-enhanced.sh --type database --list
docker exec filewallball-backup scripts/restore-enhanced.sh --type uploads --list
```

### **2. 복구 실행**
```bash
# 전체 시스템 복구
docker exec filewallball-backup scripts/restore-enhanced.sh --type full backup_full_20250824_225057

# 데이터베이스만 복구
docker exec filewallball-backup scripts/restore-enhanced.sh --type database db_backup_full_20250824_225057.sql.gz

# 파일 저장소만 복구
docker exec filewallball-backup scripts/restore-enhanced.sh --type uploads uploads_backup_full_20250824_225057.tar.gz
```

### **3. 복구 옵션**
```bash
# 롤백 포인트 생성 없이 복구
docker exec filewallball-backup scripts/restore-enhanced.sh --no-rollback --type database db_backup_full_20250824_225057.sql.gz

# 검증 없이 복구
docker exec filewallball-backup scripts/restore-enhanced.sh --no-verify --type database db_backup_full_20250824_225057.sql.gz
```

## 🗂️ **볼륨 백업 및 복구**

### **볼륨 백업**
```bash
# 모든 Named Volume 백업
./scripts/backup-volumes.sh

# 특정 볼륨 백업
./scripts/backup-volumes.sh uploads_dev_data

# 백업 디렉토리 지정
./scripts/backup-volumes.sh --output ./custom-backups
```

### **볼륨 복구**
```bash
# 사용 가능한 백업 목록
./scripts/restore-volumes.sh --list

# 특정 백업에서 복구
./scripts/restore-volumes.sh --backup 20250824_143022 uploads_dev_data

# 전체 시스템 복구
./scripts/restore-volumes.sh --backup 20250824_143022 --all
```

## ⚙️ **자동화 및 스케줄링**

### **Cron 설정**
```bash
# 백업 컨테이너 내부에서 cron 설정
docker exec -it filewallball-backup bash

# crontab 편집
crontab -e

# 매일 새벽 2시에 전체 백업
0 2 * * * /app/scripts/backup-enhanced.sh --type full

# 매주 일요일 새벽 3시에 증분 백업
0 3 * * 0 /app/scripts/backup-enhanced.sh --type incremental
```

### **백업 스케줄 환경변수**
```yaml
# docker-compose.yml
environment:
  - BACKUP_SCHEDULE=0 2 * * *  # 매일 새벽 2시
  - BACKUP_RETENTION_DAYS=30   # 30일 보존
```

## 🔒 **보안 및 암호화**

### **GPG 암호화 설정**
```bash
# GPG 키 생성
gpg --gen-key

# 백업 암호화 활성화
ENCRYPT_BACKUP=true
GPG_KEY_ID=your_gpg_key_id

# 암호화된 백업 생성
docker exec filewallball-backup scripts/backup-enhanced.sh --encrypt
```

### **백업 파일 권한**
```bash
# 백업 파일 권한 설정
chmod 600 backups/*.gz
chown backup:backup backups/*.gz

# 백업 디렉토리 보안
chmod 700 backups/
chmod 700 backups/metadata/
```

## 📈 **백업 성능 최적화**

### **압축 최적화**
```bash
# 빠른 압축 (낮은 압축률)
COMPRESSION_LEVEL=1

# 균형잡힌 압축 (권장)
COMPRESSION_LEVEL=6

# 최고 압축률 (느림)
COMPRESSION_LEVEL=9
```

### **백업 시간 최적화**
```bash
# 백업 중 서비스 중지 (데이터 일관성)
docker-compose stop app

# 백업 실행
docker exec filewallball-backup scripts/backup-enhanced.sh

# 서비스 재시작
docker-compose start app
```

## 🚨 **문제 해결**

### **일반적인 백업 오류**

#### **1. mysqldump 오류**
```bash
# MariaDB 연결 확인
docker exec filewallball-backup mysql -h mariadb -u root -p -e "SELECT 1"

# 환경변수 확인
docker exec filewallball-backup env | grep DB_
```

#### **2. 볼륨 마운트 오류**
```bash
# 볼륨 상태 확인
docker volume ls | grep filewallball

# 백업 컨테이너 볼륨 확인
docker exec filewallball-backup ls -la /app/
```

#### **3. 공간 부족 오류**
```bash
# 디스크 공간 확인
df -h

# 오래된 백업 정리
docker exec filewallball-backup find /host-backups -name "*.gz" -mtime +30 -delete
```

### **복구 오류 해결**

#### **1. 데이터베이스 복구 실패**
```bash
# MariaDB 서비스 상태 확인
docker-compose ps mariadb

# 데이터베이스 연결 테스트
docker exec filewallball-backup mysql -h mariadb -u root -p -e "SHOW DATABASES;"
```

#### **2. 파일 복구 실패**
```bash
# 백업 파일 무결성 확인
docker exec filewallball-backup gzip -t /host-backups/uploads/uploads_backup_*.tar.gz

# 백업 파일 크기 확인
docker exec filewallball-backup ls -lh /host-backups/uploads/
```

## 📋 **백업 체크리스트**

### **일일 점검**
- [ ] 백업 서비스 상태 확인
- [ ] 백업 로그 확인
- [ ] 백업 파일 크기 확인
- [ ] 디스크 공간 확인

### **주간 점검**
- [ ] 백업 파일 무결성 검증
- [ ] 복구 테스트 실행
- [ ] 백업 보존 정책 확인
- [ ] 백업 성능 분석

### **월간 점검**
- [ ] 전체 백업 실행
- [ ] 백업 전략 검토
- [ ] 백업 문서 업데이트
- [ ] 재해 복구 계획 검토

## 📚 **추가 리소스**

### **MariaDB 백업**
- [MariaDB 백업 및 복구](https://mariadb.com/kb/en/backup-and-restore/)
- [mysqldump 옵션](https://mariadb.com/kb/en/mysqldump/)

### **Docker 볼륨 관리**
- [Docker 볼륨 관리](https://docs.docker.com/storage/volumes/)
- [Docker 볼륨 백업](https://docs.docker.com/storage/volumes/#backup-restore-or-migrate-data-volumes)

### **백업 전략**
- [3-2-1 백업 규칙](https://www.backblaze.com/blog/the-3-2-1-backup-strategy/)
- [백업 유형 비교](https://www.backupassist.com/backup-software/backup-types.html)

---

**마지막 업데이트**: 2025-08-24
**버전**: 1.0.0
