"""
Database dependencies for FastAPI.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.async_database import get_db


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for FastAPI dependency injection."""
    async for session in get_db():
        yield session


# FastAPI dependency
AsyncSessionDep = Depends(get_async_session)
