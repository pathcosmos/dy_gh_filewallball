"""
SQLAlchemy Base class with version compatibility.
"""

try:
    from sqlalchemy.orm import DeclarativeBase
    
    class Base(DeclarativeBase):
        """Base class for all SQLAlchemy 2.0+ models."""
        
        def __repr__(self):
            """Default string representation for all models."""
            return f"<{self.__class__.__name__}(id={getattr(self, 'id', 'N/A')})>"
            
except ImportError:
    # Fallback for SQLAlchemy < 2.0
    from sqlalchemy.ext.declarative import declarative_base
    
    Base = declarative_base()
    
    # Add __repr__ method to Base
    def base_repr(self):
        """Default string representation for all models."""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', 'N/A')})>"
    
    Base.__repr__ = base_repr
