"""
Tests for async database functionality.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.async_database import (
    close_async_database,
    create_async_database_engine,
    create_async_session_factory,
    get_pool_status,
    init_async_database,
    test_async_connection,
)


@pytest.mark.asyncio
async def test_create_async_engine():
    """Test async engine creation."""
    engine = create_async_database_engine()
    assert engine is not None
    assert engine.pool.size() == 20
    assert engine.pool._max_overflow == 30


@pytest.mark.asyncio
async def test_create_async_session_factory():
    """Test async session factory creation."""
    session_factory = create_async_session_factory()
    assert session_factory is not None

    async with session_factory() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute("SELECT 1")
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_async_connection_works():
    """Test async database connection."""
    result = await test_async_connection()
    assert result is True


@pytest.mark.asyncio
async def test_pool_status():
    """Test connection pool status."""
    status = await get_pool_status()
    assert "pool_size" in status
    assert "checked_in" in status
    assert "checked_out" in status
    assert "overflow" in status
    assert "invalid" in status


@pytest.mark.asyncio
async def test_init_async_database():
    """Test async database initialization."""
    await init_async_database()
    # Should not raise any exceptions


@pytest.mark.asyncio
async def test_close_async_database():
    """Test async database cleanup."""
    await close_async_database()
    # Should not raise any exceptions


@pytest.fixture(autouse=True)
async def cleanup():
    """Cleanup after each test."""
    yield
    await close_async_database()
