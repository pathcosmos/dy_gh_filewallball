#!/usr/bin/env python3
"""
직접 데이터베이스 테이블 생성 스크립트
Alembic 마이그레이션 대신 직접 테이블 생성
"""
import os
from sqlalchemy import create_engine
from app.models.orm_models import Base
from app.core.config import get_config

def create_tables():
    """데이터베이스 테이블 직접 생성"""
    
    # 환경 변수 설정
    os.environ["DB_HOST"] = "pathcosmos.iptime.org"
    
    config = get_config()
    
    print("🏗️ 데이터베이스 테이블 생성 시작")
    print("=" * 50)
    print(f"📋 연결 정보:")
    print(f"   - Host: {config.db_host}")
    print(f"   - Port: {config.db_port}")
    print(f"   - Database: {config.db_name}")
    print(f"   - User: {config.db_user}")
    
    try:
        # 데이터베이스 연결
        engine = create_engine(
            config.database_url,
            pool_size=1,
            max_overflow=0,
            connect_args={
                "connect_timeout": 30,
                "read_timeout": 30,
                "write_timeout": 30
            }
        )
        
        print(f"\n🔗 데이터베이스 연결 중...")
        
        # 모든 테이블 생성
        Base.metadata.create_all(engine)
        
        print("✅ 모든 테이블이 성공적으로 생성되었습니다!")
        
        # 생성된 테이블 확인
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = :db_name"),
                {"db_name": config.db_name}
            )
            tables = result.fetchall()
            
            print(f"\n📋 생성된 테이블 목록:")
            for table in tables:
                print(f"   - {table[0]}")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        return False

if __name__ == "__main__":
    success = create_tables()
    if success:
        print("\n🎉 데이터베이스 초기화 완료!")
    else:
        print("\n⚠️ 데이터베이스 초기화 실패")