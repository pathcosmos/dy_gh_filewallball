"""
Base Repository pattern implementation for SQLAlchemy 2.0.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """Initialize repository with model and session."""
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all records with pagination."""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """Update record by ID."""
        result = await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        instance = result.scalar_one_or_none()
        if instance:
            await self.session.refresh(instance)
        return instance

    async def delete(self, id: Any) -> bool:
        """Delete record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0

    async def count(self) -> int:
        """Count total records."""
        result = await self.session.execute(select(self.model))
        return len(result.scalars().all())

    async def exists(self, id: Any) -> bool:
        """Check if record exists by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None

    async def find_by(self, **kwargs) -> List[ModelType]:
        """Find records by multiple criteria."""
        query = select(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_one_by(self, **kwargs) -> Optional[ModelType]:
        """Find single record by multiple criteria."""
        query = select(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def bulk_create(self, instances: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records at once."""
        created_instances = []
        for instance_data in instances:
            instance = self.model(**instance_data)
            self.session.add(instance)
            created_instances.append(instance)

        await self.session.flush()
        for instance in created_instances:
            await self.session.refresh(instance)

        return created_instances

    async def bulk_update(self, instances: List[ModelType]) -> List[ModelType]:
        """Update multiple records at once."""
        for instance in instances:
            await self.session.merge(instance)

        await self.session.flush()
        return instances

    async def bulk_delete(self, ids: List[Any]) -> int:
        """Delete multiple records by IDs."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id.in_(ids))
        )
        return result.rowcount
