import os
import uuid
import aiofiles
from datetime import datetime
from typing import List
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Redis 연결z
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

app = FastAPI(title="File Management API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 메트릭 설정
file_upload_counter = Counter('file_uploads_total', 'Total number of file uploads')
file_download_counter = Counter('file_downloads_total', 'Total number of file downloads')
file_upload_duration = Histogram('file_upload_duration_seconds', 'File upload duration')

# 파일 저장 디렉토리
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class FileInfo(BaseModel):
    file_id: str
    filename: str
    size: int
    upload_time: datetime
    download_url: str
    view_url: str

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    download_url: str
    view_url: str
    message: str

@app.get("/")
async def root():
    return {"message": "File Management API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """파일 업로드 API"""
    start_time = datetime.now()
    
    try:
        # 파일 ID 생성
        file_id = str(uuid.uuid4())
        
        # 파일 확장자 추출
        file_extension = Path(file.filename).suffix if file.filename else ""
        
        # 저장할 파일명 생성
        saved_filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / saved_filename
        
        # 파일 저장
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 파일 정보 저장
        file_info = {
            "file_id": file_id,
            "filename": file.filename,
            "size": len(content),
            "upload_time": datetime.now().isoformat(),
            "content_type": file.content_type,
            "saved_filename": saved_filename
        }
        
        # Redis에 파일 정보 저장 (24시간 만료)
        redis_client.setex(f"file:{file_id}", 86400, str(file_info))
        
        # URL 생성
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        download_url = f"{base_url}/download/{file_id}"
        view_url = f"{base_url}/view/{file_id}"
        
        # 메트릭 업데이트
        file_upload_counter.inc()
        file_upload_duration.observe((datetime.now() - start_time).total_seconds())
        
        # 백그라운드 작업: 파일 해시 계산
        background_tasks.add_task(calculate_file_hash, file_id, file_path)
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            download_url=download_url,
            view_url=view_url,
            message="File uploaded successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/files/{file_id}", response_model=FileInfo)
async def get_file_info(file_id: str):
    """파일 정보 조회 API"""
    file_info_str = redis_client.get(f"file:{file_id}")
    if not file_info_str:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        import ast
        file_info = ast.literal_eval(file_info_str)
        
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        download_url = f"{base_url}/download/{file_id}"
        view_url = f"{base_url}/view/{file_id}"
        
        return FileInfo(
            file_id=file_info["file_id"],
            filename=file_info["filename"],
            size=file_info["size"],
            upload_time=datetime.fromisoformat(file_info["upload_time"]),
            download_url=download_url,
            view_url=view_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file info: {str(e)}")

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """파일 다운로드 API"""
    file_info_str = redis_client.get(f"file:{file_id}")
    if not file_info_str:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        import ast
        file_info = ast.literal_eval(file_info_str)
        saved_filename = file_info["saved_filename"]
        file_path = UPLOAD_DIR / saved_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # 메트릭 업데이트
        file_download_counter.inc()
        
        return FileResponse(
            path=str(file_path),
            filename=file_info["filename"],
            media_type=file_info.get("content_type", "application/octet-stream")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/view/{file_id}")
async def view_file(file_id: str):
    """파일 미리보기 API (텍스트 파일의 경우)"""
    file_info_str = redis_client.get(f"file:{file_id}")
    if not file_info_str:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        import ast
        file_info = ast.literal_eval(file_info_str)
        saved_filename = file_info["saved_filename"]
        file_path = UPLOAD_DIR / saved_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # 텍스트 파일인지 확인
        text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
        if Path(file_info["filename"]).suffix.lower() in text_extensions:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return {"content": content, "filename": file_info["filename"]}
        else:
            return {"message": "File preview not available for this file type", "filename": file_info["filename"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"View failed: {str(e)}")

@app.get("/files", response_model=List[FileInfo])
async def list_files(limit: int = 100, offset: int = 0):
    """파일 목록 조회 API"""
    try:
        keys = redis_client.keys("file:*")
        files = []
        
        for key in keys[offset:offset + limit]:
            file_info_str = redis_client.get(key)
            if file_info_str:
                import ast
                file_info = ast.literal_eval(file_info_str)
                
                base_url = os.getenv('BASE_URL', 'http://localhost:8000')
                download_url = f"{base_url}/download/{file_info['file_id']}"
                view_url = f"{base_url}/view/{file_info['file_id']}"
                
                files.append(FileInfo(
                    file_id=file_info["file_id"],
                    filename=file_info["filename"],
                    size=file_info["size"],
                    upload_time=datetime.fromisoformat(file_info["upload_time"]),
                    download_url=download_url,
                    view_url=view_url
                ))
        
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """파일 삭제 API"""
    file_info_str = redis_client.get(f"file:{file_id}")
    if not file_info_str:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        import ast
        file_info = ast.literal_eval(file_info_str)
        saved_filename = file_info["saved_filename"]
        file_path = UPLOAD_DIR / saved_filename
        
        # Redis에서 파일 정보 삭제
        redis_client.delete(f"file:{file_id}")
        
        # 실제 파일 삭제
        if file_path.exists():
            file_path.unlink()
        
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

async def calculate_file_hash(file_id: str, file_path: Path):
    """파일 해시 계산 (백그라운드 작업)"""
    try:
        import hashlib
        hash_md5 = hashlib.md5()
        
        async with aiofiles.open(file_path, "rb") as f:
            for chunk in iter(lambda: await f.read(4096), b""):
                hash_md5.update(chunk)
        
        file_hash = hash_md5.hexdigest()
        redis_client.setex(f"hash:{file_id}", 86400, file_hash)
    except Exception as e:
        print(f"Error calculating hash for file {file_id}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)