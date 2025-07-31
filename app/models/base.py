"""
SQLAlchemy 2.0 Base class using DeclarativeBase.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 models."""

    def __repr__(self):
        """Default string representation for all models."""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', 'N/A')})>"
