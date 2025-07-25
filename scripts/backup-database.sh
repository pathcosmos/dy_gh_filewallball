#!/bin/bash

# FileWallBall Database Backup Script
# MariaDB 데이터베이스 백업 및 관리

set -e

# 설정 변수
DB_NAME="filewallball_db"
DB_USER="root"
DB_PASSWORD="filewallball2024"
BACKUP_DIR="/backup"
DATE_FORMAT=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="filewallball_backup_${DATE_FORMAT}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
RETENTION_DAYS=7

# 로그 함수
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# 백업 시작
log "=== FileWallBall Database Backup 시작 ==="

# MariaDB Pod 이름 가져오기
MARIA_POD=$(microk8s kubectl get pods -n filewallball -l app=mariadb -o jsonpath='{.items[0].metadata.name}')

if [ -z "$MARIA_POD" ]; then
    log "❌ MariaDB Pod를 찾을 수 없습니다."
    exit 1
fi

log "📦 MariaDB Pod: $MARIA_POD"

# 백업 디렉토리 확인 및 생성
log "📁 백업 디렉토리 확인 중..."
microk8s kubectl exec -n filewallball $MARIA_POD -- mkdir -p $BACKUP_DIR

# 데이터베이스 백업 실행
log "🗄️ 데이터베이스 백업 실행 중..."
microk8s kubectl exec -n filewallball $MARIA_POD -- bash -c "
mysqldump -u $DB_USER -p$DB_PASSWORD \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    --add-drop-database \
    --add-drop-table \
    --add-drop-trigger \
    --comments \
    --complete-insert \
    --extended-insert \
    --lock-tables=false \
    --set-charset \
    --default-character-set=utf8mb4 \
    $DB_NAME > $BACKUP_DIR/$BACKUP_FILE
"

# 백업 파일 압축
log "🗜️ 백업 파일 압축 중..."
microk8s kubectl exec -n filewallball $MARIA_POD -- gzip $BACKUP_DIR/$BACKUP_FILE

# 백업 파일 크기 확인
BACKUP_SIZE=$(microk8s kubectl exec -n filewallball $MARIA_POD -- stat -c%s $BACKUP_DIR/$COMPRESSED_FILE)
log "📊 백업 파일 크기: $(numfmt --to=iec $BACKUP_SIZE)"

# 백업 파일 무결성 검증
log "🔍 백업 파일 무결성 검증 중..."
microk8s kubectl exec -n filewallball $MARIA_POD -- gzip -t $BACKUP_DIR/$COMPRESSED_FILE
if [ $? -eq 0 ]; then
    log "✅ 백업 파일 무결성 검증 성공"
else
    log "❌ 백업 파일 무결성 검증 실패"
    exit 1
fi

# 오래된 백업 파일 정리
log "🧹 오래된 백업 파일 정리 중..."
microk8s kubectl exec -n filewallball $MARIA_POD -- bash -c "
find $BACKUP_DIR -name 'filewallball_backup_*.sql.gz' -mtime +$RETENTION_DAYS -delete
"

# 백업 파일 목록 확인
log "📋 백업 파일 목록:"
microk8s kubectl exec -n filewallball $MARIA_POD -- ls -lh $BACKUP_DIR/filewallball_backup_*.sql.gz 2>/dev/null || echo "백업 파일이 없습니다."

# 백업 완료
log "✅ FileWallBall Database Backup 완료!"
log "📁 백업 파일: $BACKUP_DIR/$COMPRESSED_FILE"
log "📅 보관 기간: $RETENTION_DAYS일" 