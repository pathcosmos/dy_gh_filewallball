"""
Database dependencies for FastAPI.
"""

from typing import Generator
from sqlalchemy.orm import Session

from app.models.database import get_db as _get_db


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 의존성
    
    Yields:
        Session: SQLAlchemy 세션
        
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    yield from _get_db() 