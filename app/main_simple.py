"""
Simple FileWallBall API - Streamlined version without Redis/Docker dependencies
"""
import os
from pathlib import Path
from typing import List, Optional
import uuid
from datetime import datetime

import aiofiles
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.config import get_config
from app.models.orm_models import FileInfo
from app.services.file_storage_service import FileStorageService
from app.services.file_validation_service import FileValidationService
from app.utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get configuration
config = get_config()

# Initialize FastAPI app
app = FastAPI(
    title="FileWallBall API",
    description="Simple file upload and management system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response models
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    upload_time: datetime
    download_url: str
    view_url: str
    message: str


class FileInfoResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    mime_type: Optional[str]
    upload_time: datetime
    file_hash: Optional[str]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str
    version: str


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        service="FileWallBall API",
        version="2.0.0"
    )


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a file."""
    try:
        # Validate file
        validator = FileValidationService()
        if not await validator.validate_file(file):
            raise HTTPException(status_code=400, detail="Invalid file type or size")

        # Initialize storage service
        storage_service = FileStorageService(db)
        
        # Store file
        file_info = await storage_service.store_file(file)
        
        return FileUploadResponse(
            file_id=file_info.id,
            filename=file_info.filename,
            file_size=file_info.file_size,
            upload_time=file_info.upload_time,
            download_url=f"/download/{file_info.id}",
            view_url=f"/view/{file_info.id}",
            message="File uploaded successfully"
        )
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{file_id}", response_model=FileInfoResponse)
async def get_file_info(file_id: str, db: Session = Depends(get_db)):
    """Get file information."""
    try:
        file_info = db.query(FileInfo).filter(FileInfo.id == file_id).first()
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileInfoResponse(
            file_id=file_info.id,
            filename=file_info.filename,
            file_size=file_info.file_size,
            mime_type=file_info.mime_type,
            upload_time=file_info.upload_time,
            file_hash=file_info.file_hash
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get file info error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/download/{file_id}")
async def download_file(file_id: str, db: Session = Depends(get_db)):
    """Download a file."""
    try:
        file_info = db.query(FileInfo).filter(FileInfo.id == file_id).first()
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_info.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Physical file not found")
        
        return FileResponse(
            path=file_path,
            filename=file_info.filename,
            media_type=file_info.mime_type or 'application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/view/{file_id}")
async def view_file(file_id: str, db: Session = Depends(get_db)):
    """View file content (for text files)."""
    try:
        file_info = db.query(FileInfo).filter(FileInfo.id == file_id).first()
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_info.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Physical file not found")
        
        # Check if file is text-based
        if not file_info.mime_type or not file_info.mime_type.startswith('text/'):
            # Return file info instead of content for non-text files
            return {
                "file_id": file_info.id,
                "filename": file_info.filename,
                "mime_type": file_info.mime_type,
                "message": "File is not text-based. Use /download endpoint instead."
            }
        
        # Read and return text content
        async with aiofiles.open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
            return {
                "file_id": file_info.id,
                "filename": file_info.filename,
                "content": content[:1000],  # Limit to first 1000 chars
                "truncated": len(content) > 1000
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"View error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/files")
async def list_files(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List uploaded files."""
    try:
        files = db.query(FileInfo).offset(offset).limit(limit).all()
        total = db.query(FileInfo).count()
        
        return {
            "files": [
                {
                    "file_id": f.id,
                    "filename": f.filename,
                    "file_size": f.file_size,
                    "mime_type": f.mime_type,
                    "upload_time": f.upload_time,
                    "download_url": f"/download/{f.id}"
                }
                for f in files
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"List files error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/files/{file_id}")
async def delete_file(file_id: str, db: Session = Depends(get_db)):
    """Delete a file."""
    try:
        file_info = db.query(FileInfo).filter(FileInfo.id == file_id).first()
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete physical file
        file_path = Path(file_info.file_path)
        if file_path.exists():
            file_path.unlink()
        
        # Delete database record
        db.delete(file_info)
        db.commit()
        
        return {"message": f"File {file_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logger.info("FileWallBall API starting up...")
    
    # Ensure upload directory exists
    upload_dir = Path(config.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Upload directory: {upload_dir}")
    logger.info("FileWallBall API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    logger.info("FileWallBall API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)