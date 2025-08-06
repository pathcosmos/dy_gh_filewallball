# MariaDB 설치 및 설정 가이드

## 현재 상황
- ❌ MariaDB 서버가 설치되어 있지 않음
- ❌ 포트 33377에서 실행 중인 MariaDB 서버가 없음
- 🔧 설치 및 설정이 필요함

## MariaDB 설치 방법

### 1. 시스템 패키지 관리자로 설치 (Ubuntu/Debian)

```bash
# 패키지 목록 업데이트
sudo apt update

# MariaDB 서버 및 클라이언트 설치
sudo apt install -y mariadb-server mariadb-client

# MariaDB 서비스 시작
sudo systemctl start mariadb

# 부팅 시 자동 시작 설정
sudo systemctl enable mariadb

# MariaDB 보안 설정
sudo mysql_secure_installation
```

### 2. Docker를 사용한 MariaDB 설치 (권장)

```bash
# MariaDB 컨테이너 실행
docker run --name mariadb-filewallball \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=filewallball \
  -e MYSQL_USER=filewallball \
  -e MYSQL_PASSWORD='jK9#zQ$p&2@f!L7^xY*' \
  -p 33377:3306 \
  -d mariadb:latest

# 컨테이너 상태 확인
docker ps

# MariaDB 연결 테스트
docker exec -it mariadb-filewallball mysql -u filewallball -p'jK9#zQ$p&2@f!L7^xY*' filewallball
```

### 3. 기존 MariaDB 서버 포트 변경

기존에 MariaDB가 설치되어 있다면:

```bash
# MariaDB 설정 파일 편집
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf

# 다음 라인 수정 (또는 추가)
[mysqld]
port = 33377
bind-address = 0.0.0.0

# MariaDB 재시작
sudo systemctl restart mariadb
```

## 현재 프로젝트 설정

### 데이터베이스 연결 정보
```
Host: localhost
Port: 33377
Database: filewallball
Username: filewallball
Password: jK9#zQ$p&2@f!L7^xY*
```

### 필요한 SQL 명령어
```sql
-- 데이터베이스 생성
CREATE DATABASE filewallball CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 생성 및 권한 부여
CREATE USER 'filewallball'@'localhost' IDENTIFIED BY 'jK9#zQ$p&2@f!L7^xY*';
GRANT ALL PRIVILEGES ON filewallball.* TO 'filewallball'@'localhost';
FLUSH PRIVILEGES;
```

## SQLite로 임시 테스트하기

MariaDB 설치 전에 SQLite로 임시 테스트 가능:

```bash
# SQLite 테스트용 설정
export DB_HOST=""
export DB_PORT=""
export DB_NAME="sqlite:///./filewallball_test.db"
export DB_USER=""
export DB_PASSWORD=""

# 테스트 실행
uv run python test_db_connection.py
```

## 다음 단계

1. **MariaDB 설치**: 위의 방법 중 하나 선택
2. **서비스 시작**: MariaDB 서비스 시작
3. **데이터베이스 생성**: 필요한 데이터베이스와 사용자 생성
4. **연결 테스트**: `python test_db_connection.py` 실행
5. **마이그레이션**: `uv run alembic upgrade head` 실행

## 문제 해결

### 연결 오류 시 확인 사항
- MariaDB 서비스 상태: `sudo systemctl status mariadb`
- 포트 확인: `sudo ss -tlnp | grep 33377`
- 방화벽 확인: `sudo ufw status`
- 로그 확인: `sudo journalctl -u mariadb -f`