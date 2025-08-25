# FileWallBall Database Setup Guide

FileWallBall 데이터베이스 설정 및 원격 접속을 위한 상세한 가이드입니다.

## 📋 목차

- [개요](#개요)
- [기본 설정](#기본-설정)
- [데이터베이스 초기화](#데이터베이스-초기화)
- [원격 접속 설정](#원격-접속-설정)
- [연결 테스트](#연결-테스트)
- [문제 해결](#문제-해결)
- [보안 고려사항](#보안-고려사항)

## 🎯 개요

FileWallBall은 MariaDB를 사용하여 파일 메타데이터와 프로젝트 정보를 저장합니다. 이 가이드는 다음을 포함합니다:

- **Root 계정 설정**: 안전한 root 비밀번호 설정
- **FileWallBall 사용자 계정**: 애플리케이션 전용 계정 생성
- **원격 접속 설정**: 어디서나 데이터베이스에 접속할 수 있도록 설정
- **권한 관리**: 적절한 데이터베이스 권한 설정
- **연결 테스트**: 다양한 환경에서의 연결 확인

## ⚙️ 기본 설정

### **환경 변수 설정**

데이터베이스 설정을 위한 환경 변수를 설정합니다:

```bash
# 데이터베이스 기본 설정
export DB_ROOT_PASSWORD="FileWallBall_Root_2025!"
export DB_NAME="filewallball_db"
export DB_USER="filewallball_user"
export DB_PASSWORD="FileWallBall_User_2025!"
export DB_PORT="13306"
export DB_HOST="localhost"

# 또는 .env 파일에 저장
cat > .env << EOF
DB_ROOT_PASSWORD=FileWallBall_Root_2025!
DB_NAME=filewallball_db
DB_USER=filewallball_user
DB_PASSWORD=FileWallBall_User_2025!
DB_PORT=13306
DB_HOST=localhost
EOF
```

### **Docker Compose 설정 확인**

`docker-compose.yml`에서 데이터베이스 설정을 확인합니다:

```yaml
services:
  mariadb:
    image: mariadb:10.11
    container_name: filewallball-mariadb
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:-root_password}
      MYSQL_DATABASE: ${DB_NAME:-filewallball_db}
      MYSQL_USER: ${DB_USER:-filewallball_user}
      MYSQL_PASSWORD: ${DB_PASSWORD:-filewallball_user_password}
    ports:
      - "${DB_PORT:-13306}:3306"
```

## 🚀 데이터베이스 초기화

### **자동 설정 스크립트 사용 (권장)**

프로젝트에 포함된 자동 설정 스크립트를 사용하여 데이터베이스를 설정합니다:

```bash
# 1. 스크립트 실행 권한 확인
chmod +x scripts/setup-database.sh

# 2. 환경 변수 설정 후 스크립트 실행
export DB_ROOT_PASSWORD="your_secure_root_password"
export DB_USER="your_filewallball_user"
export DB_PASSWORD="your_secure_user_password"

# 3. 데이터베이스 설정 실행
./scripts/setup-database.sh
```

### **수동 설정**

스크립트를 사용하지 않고 수동으로 설정하는 경우:

```bash
# 1. MariaDB 컨테이너 시작
docker-compose up -d mariadb

# 2. 컨테이너가 준비될 때까지 대기
sleep 30

# 3. 데이터베이스 초기화 스크립트 실행
docker exec -i filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" < scripts/init-db.sql
```

## 🌐 원격 접속 설정

### **사용자 계정 생성 및 권한 설정**

FileWallBall 사용자 계정을 생성하고 원격 접속을 허용합니다:

```sql
-- FileWallBall 사용자 생성 (모든 호스트에서 접속 가능)
CREATE USER 'filewallball_user'@'%' IDENTIFIED BY 'your_secure_password';
CREATE USER 'filewallball_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- 데이터베이스 권한 부여
GRANT ALL PRIVILEGES ON filewallball_db.* TO 'filewallball_user'@'%';
GRANT ALL PRIVILEGES ON filewallball_db.* TO 'filewallball_user'@'localhost';

-- 추가 권한 (백업 및 유지보수용)
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER ON *.* TO 'filewallball_user'@'%';
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER ON *.* TO 'filewallball_user'@'localhost';

-- 권한 적용
FLUSH PRIVILEGES;
```

### **네트워크 설정**

Docker 네트워크를 통해 컨테이너 간 통신을 설정합니다:

```bash
# Docker 네트워크 확인
docker network ls

# app-network 상세 정보 확인
docker network inspect app-network

# 컨테이너가 네트워크에 연결되어 있는지 확인
docker network inspect app-network --format='{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{end}}'
```

## 🧪 연결 테스트

### **연결 테스트 스크립트 사용**

프로젝트에 포함된 연결 테스트 스크립트를 사용합니다:

```bash
# 1. 스크립트 실행 권한 확인
chmod +x scripts/test-db-connection.sh

# 2. 모든 테스트 실행
./scripts/test-db-connection.sh

# 3. 특정 테스트만 실행
./scripts/test-db-connection.sh --container-only    # 컨테이너 내부 연결만
./scripts/test-db-connection.sh --host-only         # 호스트 연결만
./scripts/test-db-connection.sh --network-only      # 네트워크 연결만
./scripts/test-db-connection.sh --permissions-only  # 사용자 권한만
./scripts/test-db-connection.sh --examples          # 연결 예제만
```

### **수동 연결 테스트**

#### **컨테이너 내부에서 테스트**

```bash
# Root 계정으로 연결
docker exec -it filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}"

# FileWallBall 사용자로 연결
docker exec -it filewallball-mariadb mysql -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}"
```

#### **호스트에서 테스트**

```bash
# MySQL 클라이언트 설치 (Ubuntu/Debian)
sudo apt install mysql-client

# Root 계정으로 연결
mysql -h localhost -P 13306 -u root -p"${DB_ROOT_PASSWORD}"

# FileWallBall 사용자로 연결
mysql -h localhost -P 13306 -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}"
```

#### **애플리케이션에서 테스트**

```python
# Python 예제
import mysql.connector

config = {
    'host': 'localhost',
    'port': 13306,
    'user': 'filewallball_user',
    'password': 'your_secure_password',
    'database': 'filewallball_db'
}

try:
    connection = mysql.connector.connect(**config)
    print("Database connection successful!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

## 🔧 문제 해결

### **일반적인 문제들**

#### **1. 컨테이너가 시작되지 않는 경우**

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs mariadb

# 컨테이너 강제 재시작
docker-compose restart mariadb
```

#### **2. 데이터베이스 연결 실패**

```bash
# 컨테이너 내부에서 MariaDB 상태 확인
docker exec filewallball-mariadb mysqladmin ping -h localhost -u root -p"${DB_ROOT_PASSWORD}"

# 포트 확인
netstat -tlnp | grep 13306

# 방화벽 설정 확인 (필요한 경우)
sudo ufw allow 13306
```

#### **3. 권한 문제**

```bash
# 사용자 권한 확인
docker exec -it filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "SHOW GRANTS FOR '${DB_USER}'@'%';"

# 사용자 재생성
docker exec -it filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "
DROP USER '${DB_USER}'@'%';
DROP USER '${DB_USER}'@'localhost';
CREATE USER '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
"
```

#### **4. 네트워크 문제**

```bash
# Docker 네트워크 확인
docker network ls

# 네트워크 재생성
docker-compose down
docker network prune -f
docker-compose up -d
```

### **디버깅 명령어**

```bash
# 컨테이너 내부 접속
docker exec -it filewallball-mariadb bash

# MariaDB 프로세스 확인
docker exec filewallball-mariadb ps aux | grep mysql

# MariaDB 설정 확인
docker exec filewallball-mariadb cat /etc/mysql/my.cnf

# 로그 파일 확인
docker exec filewallball-mariadb tail -f /var/log/mysql/error.log
```

## 🔒 보안 고려사항

### **비밀번호 보안**

- **강력한 비밀번호 사용**: 최소 12자, 대소문자, 숫자, 특수문자 포함
- **비밀번호 정기 변경**: 90일마다 비밀번호 변경 권장
- **환경 변수 사용**: 하드코딩된 비밀번호 사용 금지

### **네트워크 보안**

- **방화벽 설정**: 필요한 포트만 열기
- **VPN 사용**: 외부 접속 시 VPN 사용 권장
- **SSL/TLS**: 프로덕션 환경에서 SSL 연결 사용

### **사용자 권한**

- **최소 권한 원칙**: 필요한 권한만 부여
- **계정 분리**: 애플리케이션용과 관리용 계정 분리
- **정기 감사**: 사용자 권한 정기 검토

## 📚 추가 리소스

### **유용한 명령어**

```bash
# 데이터베이스 백업
docker exec filewallball-mariadb mysqldump -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" > backup.sql

# 데이터베이스 복원
docker exec -i filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < backup.sql

# 데이터베이스 상태 확인
docker exec filewallball-mariadb mysqladmin status -u root -p"${DB_ROOT_PASSWORD}"

# 사용자 목록 확인
docker exec -it filewallball-mariadb mysql -u root -p"${DB_ROOT_PASSWORD}" -e "SELECT User, Host FROM mysql.user;"
```

### **모니터링**

```bash
# 실시간 연결 모니터링
watch -n 1 'docker exec filewallball-mariadb mysqladmin processlist -u root -p"${DB_ROOT_PASSWORD}"'

# 리소스 사용량 모니터링
docker stats filewallball-mariadb

# 로그 모니터링
docker logs -f filewallball-mariadb
```

---

**🎉 데이터베이스 설정이 완료되었습니다!**

이제 FileWallBall 애플리케이션에서 데이터베이스에 안전하게 연결할 수 있으며, 원격에서도 데이터베이스에 접속할 수 있습니다.

문제가 발생하거나 추가 도움이 필요한 경우, 프로젝트의 이슈 트래커를 통해 문의해주세요.
