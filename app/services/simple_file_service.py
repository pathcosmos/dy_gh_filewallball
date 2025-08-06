"""
Simplified file service without Redis dependencies
"""
import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.models.orm_models import FileInfo
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
config = get_config()


class SimpleFileService:
    """Simplified file service for basic file operations."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.upload_dir = Path(config.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(self, file: UploadFile) -> FileInfo:
        """Upload and store a file."""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Calculate file hash
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Check for duplicates
            existing_file = self.db_session.query(FileInfo).filter(
                FileInfo.file_hash == file_hash
            ).first()
            
            if existing_file:
                logger.info(f"Duplicate file detected: {file_hash}")
                return existing_file
            
            # Determine file path
            file_extension = Path(file.filename).suffix if file.filename else ""
            stored_filename = f"{file_id}{file_extension}"
            file_path = self.upload_dir / stored_filename
            
            # Write file to disk
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Create database record
            file_info = FileInfo(
                id=file_id,
                filename=file.filename or "unnamed",
                file_size=file_size,
                file_path=str(file_path),
                file_hash=file_hash,
                mime_type=file.content_type,
                upload_time=datetime.utcnow()
            )
            
            self.db_session.add(file_info)
            self.db_session.commit()
            
            logger.info(f"File uploaded: {file_id} ({file.filename})")
            return file_info
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"File upload error: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """Get file information by ID."""
        return self.db_session.query(FileInfo).filter(FileInfo.id == file_id).first()
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file by ID."""
        try:
            file_info = self.get_file_info(file_id)
            if not file_info:
                return False
            
            # Delete physical file
            file_path = Path(file_info.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Delete database record
            self.db_session.delete(file_info)
            self.db_session.commit()
            
            logger.info(f"File deleted: {file_id}")
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"File deletion error: {e}")
            return False
    
    def list_files(self, limit: int = 10, offset: int = 0):
        """List files with pagination."""
        files = self.db_session.query(FileInfo).offset(offset).limit(limit).all()
        total = self.db_session.query(FileInfo).count()
        return files, total