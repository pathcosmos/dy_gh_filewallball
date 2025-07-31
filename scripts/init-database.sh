#!/bin/bash

set -e

echo "🗄️ MariaDB 데이터베이스 초기화 시작..."

# MariaDB Pod 이름 가져오기
MARIA_POD=$(kubectl get pods -n filewallball -l app=mariadb -o jsonpath='{.items[0].metadata.name}')

if [ -z "$MARIA_POD" ]; then
    echo "❌ MariaDB Pod를 찾을 수 없습니다."
    exit 1
fi

echo "📦 MariaDB Pod: $MARIA_POD"

# 데이터베이스 스키마 적용
echo "📋 데이터베이스 스키마 적용 중..."
kubectl cp sql/filewallball_schema.sql filewallball/$MARIA_POD:/tmp/filewallball_schema.sql

# 스키마 실행
echo "🚀 스키마 실행 중..."
kubectl exec -n filewallball $MARIA_POD -- mysql -u filewallball_user -pfilewallball_user_password filewallball_db < sql/filewallball_schema.sql

# 또는 Pod 내부에서 실행
kubectl exec -n filewallball $MARIA_POD -- bash -c "
mysql -u filewallball_user -pfilewallball_user_password filewallball_db < /tmp/filewallball_schema.sql
"

echo "✅ 데이터베이스 초기화 완료!"

# 데이터베이스 상태 확인
echo "📊 데이터베이스 상태 확인:"
kubectl exec -n filewallball $MARIA_POD -- mysql -u filewallball_user -pfilewallball_user_password filewallball_db -e "
SHOW TABLES;
SELECT COUNT(*) as file_count FROM files;
SELECT COUNT(*) as view_count FROM file_views;
SELECT COUNT(*) as download_count FROM file_downloads;
"
