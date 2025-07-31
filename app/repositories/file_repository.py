"""
File repository implementation.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm_models import FileInfo
from app.repositories.base import BaseRepository


class FileRepository(BaseRepository[FileInfo]):
    """Repository for File operations."""

    def __init__(self, session: AsyncSession):
        """Initialize File repository."""
        super().__init__(FileInfo, session)

    async def get_by_uuid(self, file_uuid: str) -> Optional[FileInfo]:
        """Get file by UUID."""
        result = await self.session.execute(
            select(FileInfo).where(FileInfo.file_uuid == file_uuid)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str) -> Optional[FileInfo]:
        """Get file by hash value."""
        result = await self.session.execute(
            select(FileInfo).where(FileInfo.file_hash == file_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_content_type(self, content_type: str) -> List[FileInfo]:
        """Get files by content type."""
        result = await self.session.execute(
            select(FileInfo).where(FileInfo.mime_type == content_type)
        )
        return result.scalars().all()

    async def get_public_files(
        self, limit: int = 100, offset: int = 0
    ) -> List[FileInfo]:
        """Get public files with pagination."""
        result = await self.session.execute(
            select(FileInfo)
            .where(FileInfo.is_public == True)
            .where(FileInfo.is_deleted == False)
            .order_by(desc(FileInfo.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_files_by_owner(self, owner_id: int) -> List[FileInfo]:
        """Get files by owner ID."""
        result = await self.session.execute(
            select(FileInfo)
            .where(FileInfo.owner_id == owner_id)
            .where(FileInfo.is_deleted == False)
            .order_by(desc(FileInfo.created_at))
        )
        return result.scalars().all()

    async def search_files(
        self,
        query: str,
        content_type: Optional[str] = None,
        owner_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FileInfo]:
        """Search files by filename and other criteria."""
        conditions = [
            FileInfo.is_deleted == False,
            or_(
                FileInfo.original_filename.contains(query),
                FileInfo.stored_filename.contains(query),
            ),
        ]

        if content_type:
            conditions.append(FileInfo.mime_type == content_type)

        if owner_id:
            conditions.append(FileInfo.owner_id == owner_id)

        result = await self.session.execute(
            select(FileInfo)
            .where(and_(*conditions))
            .order_by(desc(FileInfo.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_files_by_category(self, category_id: int) -> List[FileInfo]:
        """Get files by category ID."""
        result = await self.session.execute(
            select(FileInfo)
            .where(FileInfo.file_category_id == category_id)
            .where(FileInfo.is_deleted == False)
            .order_by(desc(FileInfo.created_at))
        )
        return result.scalars().all()

    async def get_recent_files(self, days: int = 7) -> List[FileInfo]:
        """Get files uploaded in the last N days."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(FileInfo)
            .where(FileInfo.created_at >= cutoff_date)
            .where(FileInfo.is_deleted == False)
            .order_by(desc(FileInfo.created_at))
        )
        return result.scalars().all()

    async def get_large_files(self, min_size: int) -> List[FileInfo]:
        """Get files larger than specified size."""
        result = await self.session.execute(
            select(FileInfo)
            .where(FileInfo.file_size >= min_size)
            .where(FileInfo.is_deleted == False)
            .order_by(desc(FileInfo.file_size))
        )
        return result.scalars().all()

    async def soft_delete(self, file_uuid: str) -> bool:
        """Soft delete file by UUID."""
        result = await self.session.execute(
            select(FileInfo).where(FileInfo.file_uuid == file_uuid)
        )
        file_info = result.scalar_one_or_none()

        if file_info:
            file_info.is_deleted = True
            file_info.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def restore(self, file_uuid: str) -> bool:
        """Restore soft-deleted file by UUID."""
        result = await self.session.execute(
            select(FileInfo).where(FileInfo.file_uuid == file_uuid)
        )
        file_info = result.scalar_one_or_none()

        if file_info:
            file_info.is_deleted = False
            file_info.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def update_hash(self, file_uuid: str, file_hash: str) -> bool:
        """Update file hash."""
        result = await self.session.execute(
            select(FileInfo).where(FileInfo.file_uuid == file_uuid)
        )
        file_info = result.scalar_one_or_none()

        if file_info:
            file_info.file_hash = file_hash
            file_info.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def get_duplicate_files(self) -> List[FileInfo]:
        """Get files with duplicate hashes."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(FileInfo)
            .join(
                select(FileInfo.file_hash)
                .group_by(FileInfo.file_hash)
                .having(func.count(FileInfo.file_hash) > 1)
                .subquery(),
                FileInfo.file_hash == FileInfo.file_hash,
            )
            .where(FileInfo.is_deleted == False)
            .order_by(FileInfo.file_hash, desc(FileInfo.created_at))
        )
        return result.scalars().all()
