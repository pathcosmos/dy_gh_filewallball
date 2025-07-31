"""
API dependencies and dependency injection.

This module contains FastAPI dependencies for:
- Database connections
- Authentication
- Rate limiting
- Caching
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.orm_models import User

# Database dependency
DatabaseSession = Annotated[Session, Depends(get_db)]

# Authentication dependency
CurrentUser = Annotated[User, Depends(get_current_user)]

# Optional authentication dependency
OptionalUser = Annotated[User | None, Depends(get_current_user)]


def require_authentication(user: CurrentUser) -> User:
    """Require user authentication for protected endpoints."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return user
