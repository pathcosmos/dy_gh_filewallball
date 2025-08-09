"""
Common dependencies for FastAPI dependency injection.
"""

from .auth import get_current_user, get_optional_user
from .database import get_db
from .settings import get_settings

__all__ = [
    "get_db",
    "get_current_user",
    "get_optional_user",
    "get_settings",
]
