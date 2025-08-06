#!/usr/bin/env python3
"""
MariaDB 연결 테스트 스크립트
"""
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import pymysql
from app.core.config import get_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_pymysql_connection():
    """PyMySQL을 사용한 직접 연결 테스트"""
    config = get_config()
    
    print("\n" + "="*60)
    print("🔍 MariaDB 연결 테스트 시작")
    print("="*60)
    
    print(f"📋 연결 정보:")
    print(f"   - Host: {config.db_host}")
    print(f"   - Port: {config.db_port}")
    print(f"   - Database: {config.db_name}")
    print(f"   - User: {config.db_user}")
    print(f"   - Password: {'*' * len(config.db_password)}")
    
    try:
        print(f"\n🔌 PyMySQL 직접 연결 시도...")
        connection = pymysql.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_name,
            connect_timeout=10
        )
        
        with connection.cursor() as cursor:
            # 버전 확인
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"✅ MariaDB 연결 성공! 버전: {version}")
            
            # 데이터베이스 목록
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print(f"📚 사용 가능한 데이터베이스:")
            for db in databases:
                print(f"   - {db[0]}")
            
            # 현재 데이터베이스의 테이블 확인
            cursor.execute(f"USE {config.db_name}")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 '{config.db_name}' 데이터베이스의 테이블:")
            if tables:
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print("   - (테이블 없음)")
        
        connection.close()
        return True
        
    except pymysql.Error as e:
        print(f"❌ PyMySQL 연결 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def test_sqlalchemy_connection():
    """SQLAlchemy를 사용한 연결 테스트"""
    config = get_config()
    
    print(f"\n🔧 SQLAlchemy 연결 테스트...")
    print(f"   Database URL: {config.database_url}")
    
    try:
        engine = create_engine(
            config.database_url,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 10}
        )
        
        with engine.connect() as connection:
            # 테스트 쿼리 실행
            result = connection.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            print(f"✅ SQLAlchemy 연결 성공! 버전: {version}")
            
            # 연결 풀 정보
            print(f"📊 연결 풀 정보:")
            print(f"   - Pool size: {engine.pool.size()}")
            print(f"   - Checked in: {engine.pool.checkedin()}")
            print(f"   - Checked out: {engine.pool.checkedout()}")
        
        engine.dispose()
        return True
        
    except OperationalError as e:
        print(f"❌ SQLAlchemy 연결 실패 (운영 오류): {e}")
        return False
    except Exception as e:
        print(f"❌ SQLAlchemy 연결 실패: {e}")
        return False

def check_network_connectivity():
    """네트워크 연결 확인"""
    import socket
    
    config = get_config()
    print(f"\n🌐 네트워크 연결 확인...")
    print(f"   호스트: {config.db_host}")
    print(f"   포트: {config.db_port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 타임아웃 증가
        result = sock.connect_ex((config.db_host, config.db_port))
        sock.close()
        
        if result == 0:
            print(f"✅ {config.db_host}:{config.db_port}에 연결 가능")
            return True
        else:
            print(f"❌ {config.db_host}:{config.db_port}에 연결 불가 (오류 코드: {result})")
            
            # 추가 진단
            try:
                import subprocess
                result = subprocess.run(['nc', '-zv', config.db_host, str(config.db_port)], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"🔧 nc 명령어로는 연결 성공: {result.stderr.strip()}")
                else:
                    print(f"🔧 nc 명령어로도 연결 실패: {result.stderr.strip()}")
            except Exception as nc_e:
                print(f"🔧 nc 명령어 실행 실패: {nc_e}")
            
            return False
            
    except Exception as e:
        print(f"❌ 네트워크 연결 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 FileWallBall MariaDB 연결 진단 시작\n")
    
    # 1. 네트워크 연결 확인
    network_ok = check_network_connectivity()
    
    if not network_ok:
        print("\n" + "="*60)
        print("❌ 네트워크 연결 실패")
        print("="*60)
        print("📝 문제 해결 방법:")
        print("1. MariaDB 서버가 실행 중인지 확인")
        print("2. 포트 33377이 올바른지 확인")
        print("3. 방화벽 설정 확인")
        print("4. MariaDB 설정에서 bind-address 확인")
        sys.exit(1)
    
    # 2. PyMySQL 직접 연결 테스트
    pymysql_ok = test_pymysql_connection()
    
    # 3. SQLAlchemy 연결 테스트
    sqlalchemy_ok = test_sqlalchemy_connection()
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 연결 테스트 결과 요약")
    print("="*60)
    print(f"🌐 네트워크 연결: {'✅ 성공' if network_ok else '❌ 실패'}")
    print(f"🔌 PyMySQL 연결: {'✅ 성공' if pymysql_ok else '❌ 실패'}")
    print(f"🔧 SQLAlchemy 연결: {'✅ 성공' if sqlalchemy_ok else '❌ 실패'}")
    
    if all([network_ok, pymysql_ok, sqlalchemy_ok]):
        print("\n🎉 모든 연결 테스트 통과! MariaDB 연결이 올바르게 설정되었습니다.")
        sys.exit(0)
    else:
        print("\n⚠️  일부 연결 테스트 실패. 설정을 확인해주세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()