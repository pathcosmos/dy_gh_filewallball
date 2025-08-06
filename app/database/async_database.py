"""
Async database configuration for SQLAlchemy 2.0.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Async database engine
async_engine: AsyncEngine = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] = None


def create_async_database_engine() -> AsyncEngine:
    """Create async database engine with connection pooling."""
    global async_engine

    if async_engine is not None:
        return async_engine

    # Convert sync URL to async URL for MariaDB
    database_url = settings.database_url
    if database_url.startswith("mysql"):
        # MySQL/MariaDB async URL
        async_database_url = database_url.replace(
            "mysql+pymysql://", "mysql+aiomysql://"
        )
        connect_args = {}
    elif database_url.startswith("postgresql"):
        # PostgreSQL async URL  
        async_database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        connect_args = {}
    else:
        raise ValueError(f"Unsupported database URL: {database_url}. Only MySQL/MariaDB and PostgreSQL are supported.")

    async_engine = create_async_engine(
        async_database_url,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.debug,
        connect_args=connect_args,
    )

    logger.info(f"Created async database engine: {async_database_url}")
    return async_engine


def create_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    global AsyncSessionLocal

    if AsyncSessionLocal is not None:
        return AsyncSessionLocal

    engine = create_async_database_engine()
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Created async session factory")
    return AsyncSessionLocal


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency."""
    session_factory = create_async_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database session."""
    async with get_async_db() as session:
        yield session


async def init_async_database():
    """Initialize async database tables."""
    from app.models.base import Base

    engine = create_async_database_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Initialized async database tables")


async def close_async_database():
    """Close async database connections."""
    global async_engine, AsyncSessionLocal

    if AsyncSessionLocal:
        await AsyncSessionLocal.close_all()
        AsyncSessionLocal = None

    if async_engine:
        await async_engine.dispose()
        async_engine = None

    logger.info("Closed async database connections")


async def test_async_connection() -> bool:
    """Test async database connection."""
    try:
        session_factory = create_async_session_factory()
        async with session_factory() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Async database connection test failed: {e}")
        return False


async def get_pool_status() -> dict:
    """Get database connection pool status."""
    if not async_engine:
        return {"error": "Engine not initialized"}

    pool = async_engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
    }
