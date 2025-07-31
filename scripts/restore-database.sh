#!/bin/bash

# FileWallBall Database Restore Script
# MariaDB 데이터베이스 복구 및 관리

set -e

# 설정 변수
DB_NAME="filewallball_db"
DB_USER="root"
DB_PASSWORD="filewallball2024"
BACKUP_DIR="/backup"

# 로그 함수
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# 사용법 출력
usage() {
    echo "사용법: $0 [옵션]"
    echo "옵션:"
    echo "  -f, --file BACKUP_FILE    복구할 백업 파일 지정"
    echo "  -l, --list                사용 가능한 백업 파일 목록 출력"
    echo "  -h, --help                이 도움말 출력"
    echo ""
    echo "예시:"
    echo "  $0 -f filewallball_backup_20240725_120000.sql.gz"
    echo "  $0 --list"
}

# 백업 파일 목록 출력
list_backups() {
    log "=== 사용 가능한 백업 파일 목록 ==="

    MARIA_POD=$(microk8s kubectl get pods -n filewallball -l app=mariadb -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$MARIA_POD" ]; then
        log "❌ MariaDB Pod를 찾을 수 없습니다."
        exit 1
    fi

    # 백업 파일 목록 출력
    BACKUP_FILES=$(microk8s kubectl exec -n filewallball $MARIA_POD -- bash -c "ls -lh $BACKUP_DIR/filewallball_backup_*.sql.gz 2>/dev/null || echo '백업 파일이 없습니다.'")
    echo "$BACKUP_FILES"
}

# 복구 실행
restore_database() {
    local backup_file=$1

    log "=== FileWallBall Database Restore 시작 ==="

    # MariaDB Pod 이름 가져오기
    MARIA_POD=$(microk8s kubectl get pods -n filewallball -l app=mariadb -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$MARIA_POD" ]; then
        log "❌ MariaDB Pod를 찾을 수 없습니다."
        exit 1
    fi

    log "📦 MariaDB Pod: $MARIA_POD"

    # 백업 파일 존재 확인
    log "🔍 백업 파일 확인 중: $backup_file"
    if ! microk8s kubectl exec -n filewallball $MARIA_POD -- test -f "$BACKUP_DIR/$backup_file"; then
        log "❌ 백업 파일을 찾을 수 없습니다: $backup_file"
        exit 1
    fi

    # 백업 파일 무결성 검증
    log "🔍 백업 파일 무결성 검증 중..."
    microk8s kubectl exec -n filewallball $MARIA_POD -- gzip -t "$BACKUP_DIR/$backup_file"
    if [ $? -ne 0 ]; then
        log "❌ 백업 파일이 손상되었습니다: $backup_file"
        exit 1
    fi
    log "✅ 백업 파일 무결성 검증 성공"

    # 백업 파일 크기 확인
    BACKUP_SIZE=$(microk8s kubectl exec -n filewallball $MARIA_POD -- stat -c%s "$BACKUP_DIR/$backup_file")
    log "📊 백업 파일 크기: $(numfmt --to=iec $BACKUP_SIZE)"

    # 복구 전 확인
    log "⚠️  복구를 진행하시겠습니까? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log "❌ 복구가 취소되었습니다."
        exit 0
    fi

    # 데이터베이스 연결 확인
    log "🔗 데이터베이스 연결 확인 중..."
    microk8s kubectl exec -n filewallball $MARIA_POD -- mysql -u $DB_USER -p$DB_PASSWORD -e "SELECT 1;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log "❌ 데이터베이스에 연결할 수 없습니다."
        exit 1
    fi

    # 기존 데이터베이스 백업 (안전장치)
    log "🛡️ 기존 데이터베이스 백업 생성 중..."
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    SAFETY_BACKUP="safety_backup_${TIMESTAMP}.sql.gz"

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
    $DB_NAME | gzip > $BACKUP_DIR/$SAFETY_BACKUP
"

    log "✅ 안전 백업 생성 완료: $SAFETY_BACKUP"

    # 데이터베이스 복구 실행
    log "🗄️ 데이터베이스 복구 실행 중..."
    microk8s kubectl exec -n filewallball $MARIA_POD -- bash -c "
gunzip -c $BACKUP_DIR/$backup_file | mysql -u $DB_USER -p$DB_PASSWORD
"

    if [ $? -eq 0 ]; then
        log "✅ 데이터베이스 복구 성공!"

        # 복구 후 검증
        log "🔍 복구 결과 검증 중..."
        TABLE_COUNT=$(microk8s kubectl exec -n filewallball $MARIA_POD -- mysql -u $DB_USER -p$DB_PASSWORD -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';" -s -N)
        log "📊 복구된 테이블 수: $TABLE_COUNT"

        # 주요 테이블 확인
        log "📋 주요 테이블 상태 확인:"
        microk8s kubectl exec -n filewallball $MARIA_POD -- mysql -u $DB_USER -p$DB_PASSWORD -e "
SELECT
    table_name,
    table_rows,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.tables
WHERE table_schema = '$DB_NAME'
ORDER BY table_name;
"

    else
        log "❌ 데이터베이스 복구 실패!"
        log "🔄 안전 백업에서 복구하시겠습니까? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            log "🔄 안전 백업에서 복구 중..."
            microk8s kubectl exec -n filewallball $MARIA_POD -- bash -c "
gunzip -c $BACKUP_DIR/$SAFETY_BACKUP | mysql -u $DB_USER -p$DB_PASSWORD
"
            log "✅ 안전 백업에서 복구 완료!"
        fi
        exit 1
    fi

    log "✅ FileWallBall Database Restore 완료!"
    log "📁 복구된 백업 파일: $backup_file"
}

# 메인 로직
main() {
    local backup_file=""

    # 명령행 인수 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--file)
                backup_file="$2"
                shift 2
                ;;
            -l|--list)
                list_backups
                exit 0
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "❌ 알 수 없는 옵션: $1"
                usage
                exit 1
                ;;
        esac
    done

    # 백업 파일이 지정되지 않은 경우
    if [ -z "$backup_file" ]; then
        echo "❌ 백업 파일을 지정해주세요."
        usage
        exit 1
    fi

    # 복구 실행
    restore_database "$backup_file"
}

# 스크립트 실행
main "$@"
