"""
Common dependencies for FastAPI dependency injection.
"""

from .database import get_db
from .redis import get_redis_client
from .auth import get_current_user, get_optional_user
from .settings import get_settings

__all__ = [
    "get_db",
    "get_redis_client", 
    "get_current_user",
    "get_optional_user",
    "get_settings"
] 