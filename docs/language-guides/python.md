# FileWallBall API - Python 사용법 가이드

Python 환경에서 FileWallBall API를 사용하여 파일 업로드, 다운로드, 관리 기능을 구현하는 방법을 설명합니다.

## 📋 목차

- [환경 설정](#환경-설정)
- [기본 사용법](#기본-사용법)
- [파일 업로드](#파일-업로드)
- [파일 다운로드](#파일-다운로드)
- [파일 관리](#파일-관리)
- [에러 처리](#에러-처리)
- [완전한 예제](#완전한-예제)

## 🔧 환경 설정

### **패키지 설치**

```bash
# Create virtual environment
# 가상환경 생성
python -m venv filewallball-env

# Activate virtual environment
# 가상환경 활성화
# Windows
filewallball-env\Scripts\activate
# macOS/Linux
source filewallball-env/bin/activate

# Install dependencies
# 의존성 설치
pip install requests requests-toolbelt tqdm python-dotenv
```

### **requirements.txt**

```txt
# HTTP client library
requests>=2.31.0

# Multipart form data support
requests-toolbelt>=1.0.0

# Progress bar for uploads/downloads
tqdm>=4.66.0

# Environment variable management
python-dotenv>=1.0.0
```

## 🚀 기본 사용법

### **HTTP 클라이언트 설정**

```python
import requests
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

class FileWallBallClient:
    """FileWallBall API client for Python
    
    FileWallBall API를 위한 Python 클라이언트
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize FileWallBall client
        
        FileWallBall 클라이언트 초기화
        
        Args:
            base_url: API base URL (e.g., 'http://localhost:8000')
            api_key: API authentication key (optional, can be loaded from .env)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or self._load_api_key()
        
        # Create session for connection pooling
        # 연결 풀링을 위한 세션 생성
        self.session = requests.Session()
        
        # Set default headers
        # 기본 헤더 설정
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'FileWallBall-Python-Client/2.0.0'
        })
        
        # Configure timeouts
        # 타임아웃 설정
        self.session.timeout = (30, 60)  # (connect_timeout, read_timeout)
    
    def _load_api_key(self) -> str:
        """Load API key from environment variables
        
        환경 변수에서 API 키 로드
        
        Returns:
            API key string
            
        Raises:
            ValueError: If API key not found
        """
        load_dotenv()  # Load .env file
        
        api_key = os.getenv('FILEWALLBALL_API_KEY')
        if not api_key:
            raise ValueError(
                "API key not found. Set FILEWALLBALL_API_KEY environment variable "
                "or pass api_key parameter to constructor."
            )
        return api_key
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers
        
        인증 헤더 반환
        
        Returns:
            Dictionary containing authorization headers
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
```

## 📤 파일 업로드

### **기본 파일 업로드**

```python
import os
from pathlib import Path
from typing import Union, Optional
from requests_toolbelt.multipart.encoder import MultipartEncoder
from tqdm import tqdm

class FileUploader:
    """File upload functionality for FileWallBall API
    
    FileWallBall API를 위한 파일 업로드 기능
    """
    
    def __init__(self, client: FileWallBallClient):
        """Initialize file uploader
        
        파일 업로더 초기화
        
        Args:
            client: FileWallBall client instance
        """
        self.client = client
    
    def upload_file(self, file_path: Union[str, Path], 
                   show_progress: bool = True) -> Dict[str, Any]:
        """Upload file to FileWallBall API
        
        FileWallBall API에 파일 업로드
        
        Args:
            file_path: Path to file to upload
            show_progress: Whether to show upload progress bar
            
        Returns:
            Upload response data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is empty
            requests.RequestException: If upload fails
        """
        file_path = Path(file_path)
        
        # Validate file exists and is not empty
        # 파일 존재 여부 및 빈 파일 여부 검증
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValueError("Cannot upload empty file")
        
        # Get MIME type based on file extension
        # 파일 확장자 기반 MIME 타입 추출
        mime_type = self._get_mime_type(file_path)
        
        # Create multipart encoder
        # 멀티파트 인코더 생성
        with open(file_path, 'rb') as file:
            encoder = MultipartEncoder(
                fields={
                    'file': (
                        file_path.name,  # filename
                        file,            # file object
                        mime_type        # content type
                    )
                }
            )
            
            # Prepare headers
            # 헤더 준비
            headers = {
                'Content-Type': encoder.content_type,
                'Content-Length': str(encoder.len)
            }
            
            # Upload with progress tracking
            # 진행률 추적과 함께 업로드
            if show_progress:
                return self._upload_with_progress(encoder, headers, file_size)
            else:
                return self._upload_simple(encoder, headers)
    
    def _upload_with_progress(self, encoder: MultipartEncoder, 
                             headers: Dict[str, str], 
                             file_size: int) -> Dict[str, Any]:
        """Upload file with progress bar
        
        진행률 표시줄과 함께 파일 업로드
        
        Args:
            encoder: Multipart encoder
            headers: Request headers
            file_size: Size of file in bytes
            
        Returns:
            Upload response data
        """
        # Create custom progress bar
        # 커스텀 진행률 표시줄 생성
        with tqdm(total=file_size, unit='B', unit_scale=True, 
                 desc="Uploading") as pbar:
            
            # Custom encoder that tracks progress
            # 진행률을 추적하는 커스텀 인코더
            class ProgressEncoder:
                def __init__(self, original_encoder, progress_bar):
                    self.encoder = original_encoder
                    self.pbar = progress_bar
                    self.bytes_read = 0
                
                def read(self, size: int = -1) -> bytes:
                    chunk = self.encoder.read(size)
                    self.bytes_read += len(chunk)
                    self.pbar.update(len(chunk))
                    return chunk
                
                @property
                def content_type(self):
                    return self.encoder.content_type
                
                @property
                def len(self):
                    return self.encoder.len
            
            progress_encoder = ProgressEncoder(encoder, pbar)
            
            # Perform upload
            # 업로드 수행
            response = self.client.session.post(
                f"{self.client.base_url}/upload",
                data=progress_encoder,
                headers=headers
            )
            
            response.raise_for_status()
            return response.json()
    
    def _upload_simple(self, encoder: MultipartEncoder, 
                       headers: Dict[str, str]) -> Dict[str, Any]:
        """Upload file without progress tracking
        
        진행률 추적 없이 파일 업로드
        
        Args:
            encoder: Multipart encoder
            headers: Request headers
            
        Returns:
            Upload response data
        """
        response = self.client.session.post(
            f"{self.client.base_url}/upload",
            data=encoder,
            headers=headers
        )
        
        response.raise_for_status()
        return response.json()
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension
        
        파일 확장자 기반 MIME 타입 추출
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type string
        """
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf'
        }
        
        return mime_types.get(file_path.suffix.lower(), 'application/octet-stream')
```

## ⬇️ 파일 다운로드

### **파일 다운로드 및 저장**

```python
import os
from pathlib import Path
from typing import Union, Optional
from tqdm import tqdm

class FileDownloader:
    """File download functionality for FileWallBall API
    
    FileWallBall API를 위한 파일 다운로드 기능
    """
    
    def __init__(self, client: FileWallBallClient):
        """Initialize file downloader
        
        파일 다운로더 초기화
        
        Args:
            client: FileWallBall client instance
        """
        self.client = client
    
    def download_file(self, file_id: str, output_path: Union[str, Path],
                     show_progress: bool = True,
                     chunk_size: int = 8192) -> Dict[str, Any]:
        """Download file from FileWallBall API
        
        FileWallBall API에서 파일 다운로드
        
        Args:
            file_id: ID of file to download
            output_path: Path where to save downloaded file
            show_progress: Whether to show download progress
            chunk_size: Size of chunks for streaming download
            
        Returns:
            Download result information
            
        Raises:
            requests.RequestException: If download fails
        """
        output_path = Path(output_path)
        
        # Create output directory if it doesn't exist
        # 출력 디렉토리가 없으면 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download file with streaming
        # 스트리밍으로 파일 다운로드
        response = self.client.session.get(
            f"{self.client.base_url}/download/{file_id}",
            stream=True
        )
        
        response.raise_for_status()
        
        # Get file size for progress bar
        # 진행률 표시줄을 위한 파일 크기
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress tracking
        # 진행률 추적과 함께 다운로드
        if show_progress and total_size > 0:
            return self._download_with_progress(
                response, output_path, total_size, chunk_size
            )
        else:
            return self._download_simple(response, output_path, chunk_size)
    
    def _download_with_progress(self, response: requests.Response,
                               output_path: Path, total_size: int,
                               chunk_size: int) -> Dict[str, Any]:
        """Download file with progress bar
        
        진행률 표시줄과 함께 파일 다운로드
        
        Args:
            response: HTTP response object
            output_path: Path to save file
            total_size: Total file size in bytes
            chunk_size: Size of chunks
            
        Returns:
            Download result information
        """
        downloaded_size = 0
        
        with tqdm(total=total_size, unit='B', unit_scale=True,
                 desc="Downloading") as pbar:
            
            with open(output_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        pbar.update(len(chunk))
        
        return {
            'filename': output_path.name,
            'path': str(output_path),
            'size': downloaded_size,
            'status': 'completed'
        }
```

## 📋 파일 관리

### **파일 목록 조회 및 관리**

```python
class FileManager:
    """File management functionality for FileWallBall API
    
    FileWallBall API를 위한 파일 관리 기능
    """
    
    def __init__(self, client: FileWallBallClient):
        """Initialize file manager
        
        파일 매니저 초기화
        
        Args:
            client: FileWallBall client instance
        """
        self.client = client
    
    def get_file_list(self, page: int = 1, limit: int = 20,
                      sort_by: str = 'uploaded_at', order: str = 'desc') -> Dict[str, Any]:
        """Get list of uploaded files with pagination
        
        페이지네이션과 함께 업로드된 파일 목록 조회
        
        Args:
            page: Page number
            limit: Number of items per page
            sort_by: Field to sort by
            order: Sort order ('asc' or 'desc')
            
        Returns:
            File list response data
        """
        params = {
            'page': page,
            'limit': limit,
            'sort_by': sort_by,
            'order': order
        }
        
        response = self.client.session.get(
            f"{self.client.base_url}/files",
            params=params
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get specific file information
        
        특정 파일 정보 조회
        
        Args:
            file_id: ID of file to get info for
            
        Returns:
            File information data
        """
        response = self.client.session.get(
            f"{self.client.base_url}/files/{file_id}"
        )
        
        response.raise_for_status()
        return response.json()
    
    def deactivate_file(self, file_id: str) -> Dict[str, Any]:
        """Deactivate file (soft delete)
        
        파일 비활성화 (소프트 삭제)
        
        Args:
            file_id: ID of file to deactivate
            
        Returns:
            Deactivation response data
        """
        response = self.client.session.delete(
            f"{self.client.base_url}/files/{file_id}"
        )
        
        response.raise_for_status()
        return response.json()
```

## 🏥 시스템 관리

### **헬스체크 및 모니터링**

```python
import time
from threading import Thread, Event

class SystemMonitor:
    """System monitoring functionality for FileWallBall API
    
    FileWallBall API를 위한 시스템 모니터링 기능
    """
    
    def __init__(self, client: FileWallBallClient):
        """Initialize system monitor
        
        시스템 모니터 초기화
        
        Args:
            client: FileWallBall client instance
        """
        self.client = client
        self.monitoring = False
        self.monitor_thread = None
        self.stop_event = Event()
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health status
        
        시스템 상태 확인
        
        Returns:
            Health status data
        """
        response = self.client.session.get(
            f"{self.client.base_url}/health"
        )
        
        response.raise_for_status()
        return response.json()
    
    def start_health_monitoring(self, interval_seconds: int = 30) -> None:
        """Start periodic health monitoring
        
        주기적 시스템 상태 모니터링 시작
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self.monitoring:
            print("Health monitoring is already running")
            return
        
        self.monitoring = True
        self.stop_event.clear()
        
        self.monitor_thread = Thread(
            target=self._monitor_health,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        
        print(f"Health monitoring started (interval: {interval_seconds}s)")
    
    def stop_health_monitoring(self) -> None:
        """Stop health monitoring
        
        상태 모니터링 중지
        """
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print("Health monitoring stopped")
```

## 🚀 완전한 예제

### **메인 애플리케이션**

```python
def main():
    """Main application function
    
    메인 애플리케이션 함수
    """
    try:
        # Initialize client
        # 클라이언트 초기화
        client = FileWallBallClient('http://localhost:8000')
        
        # Initialize services
        # 서비스 초기화
        uploader = FileUploader(client)
        downloader = FileDownloader(client)
        file_manager = FileManager(client)
        system_monitor = SystemMonitor(client)
        
        # Check system health
        # 시스템 상태 확인
        health = system_monitor.check_health()
        print(f"System health: {health['status']}")
        
        # Upload file
        # 파일 업로드
        upload_result = uploader.upload_file('./example.txt')
        print(f"File uploaded: {upload_result['file_id']}")
        
        # Get file list
        # 파일 목록 조회
        file_list = file_manager.get_file_list(1, 10)
        print(f"Total files: {file_list['pagination']['total']}")
        
        # Download file
        # 파일 다운로드
        download_result = downloader.download_file(
            upload_result['file_id'],
            './downloaded_example.txt'
        )
        print(f"File downloaded: {download_result['filename']}")
        
        print("Example completed")
        
    except Exception as e:
        print(f"Error in main: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Run main function
    # 메인 함수 실행
    exit(main())
```

## 📝 사용 팁

### **성능 최적화**
1. **세션 재사용**: `requests.Session`을 사용하여 연결 풀링 활용
2. **스트리밍**: 대용량 파일은 스트리밍 방식 사용
3. **병렬 처리**: 여러 파일 업로드/다운로드 시 `ThreadPoolExecutor` 활용
4. **청크 크기**: 적절한 청크 크기로 메모리 사용량 최적화

### **에러 처리**
1. **재시도 로직**: 네트워크 오류 시 지수 백오프로 재시도
2. **로깅**: 상세한 에러 로그로 디버깅 지원
3. **사용자 피드백**: 진행률 표시 및 상태 메시지 제공

### **보안**
1. **API 키 관리**: 환경 변수로 API 키 보호
2. **HTTPS 사용**: 프로덕션 환경에서는 HTTPS 필수
3. **입력 검증**: 파일명, 경로 등 사용자 입력 검증

---

**참고**: 이 가이드는 FileWallBall API v2.0.0을 기준으로 작성되었습니다.
