"""
User repository implementation.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm_models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    def __init__(self, session: AsyncSession):
        """Initialize User repository."""
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_active_users(self) -> List[User]:
        """Get all active users."""
        result = await self.session.execute(
            select(User).where(User.is_active == True).order_by(desc(User.created_at))
        )
        return result.scalars().all()

    async def get_users_by_role(self, role: str) -> List[User]:
        """Get users by role."""
        result = await self.session.execute(
            select(User)
            .where(User.role == role)
            .where(User.is_active == True)
            .order_by(desc(User.created_at))
        )
        return result.scalars().all()

    async def search_users(self, query: str) -> List[User]:
        """Search users by username or email."""
        result = await self.session.execute(
            select(User)
            .where(
                and_(
                    User.is_active == True,
                    or_(User.username.contains(query), User.email.contains(query)),
                )
            )
            .order_by(desc(User.created_at))
        )
        return result.scalars().all()

    async def get_recent_users(self, days: int = 7) -> List[User]:
        """Get users created in the last N days."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(User)
            .where(User.created_at >= cutoff_date)
            .where(User.is_active == True)
            .order_by(desc(User.created_at))
        )
        return result.scalars().all()

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def activate_user(self, user_id: int) -> bool:
        """Activate user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.is_active = True
            user.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def update_last_login(self, user_id: int) -> bool:
        """Update user's last login time."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def change_role(self, user_id: int, new_role: str) -> bool:
        """Change user role."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.role = new_role
            user.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def get_users_with_files(self) -> List[User]:
        """Get users who have uploaded files."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(User)
            .options(selectinload(User.owned_files))
            .where(User.is_active == True)
            .order_by(desc(User.created_at))
        )
        return result.scalars().all()

    async def get_user_stats(self, user_id: int) -> dict:
        """Get user statistics."""
        from sqlalchemy import func

        # Count owned files
        files_result = await self.session.execute(
            select(func.count(User.owned_files)).where(User.id == user_id)
        )
        file_count = files_result.scalar() or 0

        # Get user info
        user_result = await self.session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            return {}

        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "file_count": file_count,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
        }
