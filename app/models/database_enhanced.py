"""
Enhanced database connection and session management.
"""

import functools
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class EnhancedDatabaseManager:
    """향상된 데이터베이스 연결 및 관리 클래스"""

    def __init__(self):
        # 데이터베이스 설정
        self.db_host = os.getenv("DB_HOST", "mariadb-service")
        self.db_port = os.getenv("DB_PORT", "3306")
        self.db_name = os.getenv("DB_NAME", "filewallball_db")
        self.db_user = os.getenv("DB_USER", "filewallball_user")
        self.db_password = os.getenv("DB_PASSWORD", "filewallball_user_password")

        # 데이터베이스 URL
        self.database_url = f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

        # 향상된 SQLAlchemy 엔진 설정
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=20,  # Task 5.2 요구사항: pool_size=20
            max_overflow=30,  # Task 5.2 요구사항: max_overflow=30
            pool_pre_ping=True,  # 연결 상태 확인
            pool_recycle=3600,  # 연결 재활용 (1시간)
            pool_timeout=30,  # 연결 타임아웃
            echo=False,  # SQL 로그 출력 여부
            # MariaDB 특화 설정
            connect_args={
                "charset": "utf8mb4",
                "autocommit": False,
                "sql_mode": "STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO",
            },
        )

        # 세션 팩토리
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        logger.info(
            f"Enhanced database manager initialized with pool_size=20, max_overflow=30"
        )

    def get_db(self) -> Session:
        """데이터베이스 세션 반환"""
        return self.SessionLocal()

    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def get_connection_info(self) -> dict:
        """연결 정보 반환"""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }

    def get_pool_status(self) -> dict:
        """연결 풀 상태 정보 반환"""
        try:
            pool = self.engine.pool
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
            }
        except Exception as e:
            logger.error(f"Failed to get pool status: {e}")
            return {}

    @contextmanager
    def get_db_session(self):
        """컨텍스트 매니저를 사용한 데이터베이스 세션"""
        session = self.get_db()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()


def transaction_rollback_decorator(func: Callable) -> Callable:
    """트랜잭션 롤백 처리 데코레이터"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        db_session = None

        # 세션 인자 찾기
        for arg in args:
            if isinstance(arg, Session):
                db_session = arg
                break

        if not db_session:
            for value in kwargs.values():
                if isinstance(value, Session):
                    db_session = value
                    break

        if not db_session:
            logger.warning("No database session found in function arguments")
            return func(*args, **kwargs)

        try:
            result = func(*args, **kwargs)
            db_session.commit()
            return result
        except Exception as e:
            db_session.rollback()
            logger.error(f"Transaction rollback for function {func.__name__}: {e}")
            raise

    return wrapper


def with_transaction(db_session: Session):
    """트랜잭션 컨텍스트 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                db_session.commit()
                return result
            except Exception as e:
                db_session.rollback()
                logger.error(f"Transaction rollback for {func.__name__}: {e}")
                raise

        return wrapper

    return decorator


class DatabaseHealthChecker:
    """데이터베이스 헬스 체크 클래스"""

    def __init__(self, db_manager: EnhancedDatabaseManager):
        self.db_manager = db_manager

    def check_connection(self) -> dict:
        """연결 상태 체크"""
        try:
            is_connected = self.db_manager.test_connection()
            pool_status = self.db_manager.get_pool_status()

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "pool_status": pool_status,
                "timestamp": "2025-07-28T01:40:00Z",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "connected": False,
                "timestamp": "2025-07-28T01:40:00Z",
            }

    def check_performance(self) -> dict:
        """성능 체크"""
        try:
            with self.db_manager.get_db_session() as session:
                # 간단한 쿼리 성능 테스트
                import time

                start_time = time.time()

                result = session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables")
                )
                result.fetchone()

                query_time = time.time() - start_time

                return {
                    "query_time_ms": round(query_time * 1000, 2),
                    "status": "good" if query_time < 0.1 else "slow",
                    "timestamp": "2025-07-28T01:40:00Z",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": "2025-07-28T01:40:00Z",
            }


# 전역 향상된 데이터베이스 매니저 인스턴스
enhanced_db_manager = EnhancedDatabaseManager()

# 헬스 체커 인스턴스
db_health_checker = DatabaseHealthChecker(enhanced_db_manager)


def get_enhanced_db():
    """향상된 FastAPI 의존성 주입용 데이터베이스 세션"""
    db = enhanced_db_manager.get_db()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """컨텍스트 매니저를 사용한 데이터베이스 세션"""
    return enhanced_db_manager.get_db_session()


def init_enhanced_database():
    """향상된 데이터베이스 초기화"""
    try:
        # 연결 테스트
        if not enhanced_db_manager.test_connection():
            logger.error("Enhanced database connection failed")
            return False

        # 연결 정보 로깅
        connection_info = enhanced_db_manager.get_connection_info()
        logger.info(f"Enhanced database initialized: {connection_info}")

        # 풀 상태 로깅
        pool_status = enhanced_db_manager.get_pool_status()
        logger.info(f"Initial pool status: {pool_status}")

        return True
    except Exception as e:
        logger.error(f"Enhanced database initialization failed: {e}")
        return False


# 기존 호환성을 위한 별칭
get_db = get_enhanced_db
init_database = init_enhanced_database
