# FileWallBall API - 공통 기능 및 고급 사용법 가이드

모든 프로그래밍 언어에서 FileWallBall API를 사용할 때 공통적으로 적용할 수 있는 고급 기능과 모범 사례를 설명합니다.

## 📋 목차

- [API 인증 및 보안](#api-인증-및-보안)
- [파일 다운로드 및 스트리밍](#파일-다운로드-및-스트리밍)
- [이미지 뷰어 및 미리보기](#이미지-뷰어-및-미리보기)
- [에러 처리 및 재시도](#에러-처리-및-재시도)
- [진행률 표시 및 사용자 피드백](#진행률-표시-및-사용자-피드백)
- [성능 최적화](#성능-최적화)
- [모니터링 및 로깅](#모니터링-및-로깅)

## 🔐 API 인증 및 보안

### **프로젝트 키 생성 및 관리**

```bash
# Generate project API key
# 프로젝트 API 키 생성
curl -X POST "http://localhost:8000/keygen" \
  -H "Content-Type: application/json" \
  -d '{"project_name": "my-application"}'
```

### **환경 변수 관리**

```bash
# .env file example
# .env 파일 예시
FILEWALLBALL_API_KEY=your_generated_api_key_here
FILEWALLBALL_BASE_URL=http://localhost:8000
FILEWALLBALL_TIMEOUT=60
FILEWALLBALL_MAX_RETRIES=3
```

### **보안 헤더 설정**

```javascript
// Common security headers for all languages
// 모든 언어에 공통적인 보안 헤더
const securityHeaders = {
    'Authorization': `Bearer ${process.env.FILEWALLBALL_API_KEY}`,
    'User-Agent': 'MyApp/1.0.0',
    'X-Request-ID': generateRequestId(),  // Request tracking
    'X-Client-Version': '1.0.0'          // Client version tracking
};
```

## ⬇️ 파일 다운로드 및 스트리밍

### **스트리밍 다운로드 구현**

```python
# Python example - Streaming download with progress
# Python 예제 - 진행률과 함께 스트리밍 다운로드
import requests
from tqdm import tqdm

def stream_download(file_id, output_path, chunk_size=8192):
    """Stream download with progress tracking
    
    진행률 추적과 함께 스트리밍 다운로드
    """
    response = requests.get(
        f"{BASE_URL}/download/{file_id}",
        stream=True,
        headers=get_auth_headers()
    )
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as file:
        with tqdm(total=total_size, unit='B') as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)
                    pbar.update(len(chunk))
```

```java
// Java example - Streaming download with progress
// Java 예제 - 진행률과 함께 스트리밍 다운로드
public void streamDownload(String fileId, String outputPath) throws IOException {
    Request request = new Request.Builder()
        .url(BASE_URL + "/download/" + fileId)
        .headers(getAuthHeaders())
        .build();
    
    try (Response response = client.newCall(request).execute()) {
        if (!response.isSuccessful()) {
            throw new IOException("Download failed: " + response.code());
        }
        
        ResponseBody body = response.body();
        if (body == null) {
            throw new IOException("Response body is null");
        }
        
        long totalSize = body.contentLength();
        InputStream inputStream = body.byteStream();
        
        try (FileOutputStream outputStream = new FileOutputStream(outputPath)) {
            byte[] buffer = new byte[8192];
            long downloaded = 0;
            
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
                downloaded += bytesRead;
                
                // Report progress
                // 진행률 보고
                if (totalSize > 0) {
                    int progress = (int) ((downloaded * 100) / totalSize);
                    System.out.printf("Download progress: %d%%\n", progress);
                }
            }
        }
    }
}
```

### **범위 요청 (Range Requests)**

```javascript
// Node.js example - Range requests for large files
// Node.js 예제 - 대용량 파일을 위한 범위 요청
async function downloadWithRange(fileId, outputPath, chunkSize = 1024 * 1024) {
    const fileInfo = await getFileInfo(fileId);
    const totalSize = fileInfo.file_size;
    
    const fileStream = fs.createWriteStream(outputPath);
    
    for (let start = 0; start < totalSize; start += chunkSize) {
        const end = Math.min(start + chunkSize - 1, totalSize - 1);
        
        const response = await axios.get(
            `${BASE_URL}/download/${fileId}`,
            {
                headers: {
                    ...getAuthHeaders(),
                    'Range': `bytes=${start}-${end}`
                },
                responseType: 'stream'
            }
        );
        
        response.data.pipe(fileStream, { end: false });
        
        // Wait for chunk to complete
        // 청크 완료까지 대기
        await new Promise((resolve, reject) => {
            response.data.on('end', resolve);
            response.data.on('error', reject);
        });
        
        console.log(`Downloaded chunk: ${start}-${end} (${end - start + 1} bytes)`);
    }
    
    fileStream.end();
}
```

## 👁️ 이미지 뷰어 및 미리보기

### **이미지 파일 미리보기**

```python
# Python example - Image preview and thumbnail
# Python 예제 - 이미지 미리보기 및 썸네일
import requests
from PIL import Image
import io

def get_image_preview(file_id, max_width=800, max_height=600):
    """Get image preview with resizing
    
    크기 조정과 함께 이미지 미리보기 가져오기
    """
    # Get image preview
    # 이미지 미리보기 가져오기
    response = requests.get(
        f"{BASE_URL}/preview/{file_id}",
        headers=get_auth_headers()
    )
    
    if response.status_code == 200:
        # Process image with PIL
        # PIL로 이미지 처리
        image = Image.open(io.BytesIO(response.content))
        
        # Resize image maintaining aspect ratio
        # 종횡비를 유지하면서 이미지 크기 조정
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convert to bytes for display
        # 표시를 위해 바이트로 변환
        output = io.BytesIO()
        image.save(output, format=image.format or 'JPEG')
        return output.getvalue()
    
    return None
```

### **텍스트 파일 미리보기**

```javascript
// Node.js example - Text file preview
// Node.js 예제 - 텍스트 파일 미리보기
async function getTextPreview(fileId, maxLength = 1000) {
    try {
        const response = await axios.get(
            `${BASE_URL}/preview/${fileId}`,
            {
                headers: getAuthHeaders(),
                params: { max_length: maxLength }
            }
        );
        
        if (response.status === 200) {
            const preview = response.data;
            
            // Format preview text
            // 미리보기 텍스트 포맷
            let formattedPreview = preview.content;
            
            // Add ellipsis if truncated
            // 잘린 경우 생략 부호 추가
            if (preview.is_truncated) {
                formattedPreview += '...';
            }
            
            // Add file info
            // 파일 정보 추가
            formattedPreview += `\n\n---\n`;
            formattedPreview += `File: ${preview.filename}\n`;
            formattedPreview += `Size: ${formatFileSize(preview.file_size)}\n`;
            formattedPreview += `Type: ${preview.mime_type}\n`;
            
            return formattedPreview;
        }
    } catch (error) {
        console.error('Failed to get text preview:', error.message);
    }
    
    return null;
}
```

## ⚠️ 에러 처리 및 재시도

### **지수 백오프 재시도 로직**

```python
# Python example - Exponential backoff retry
# Python 예제 - 지수 백오프 재시도
import time
import random
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0):
    """Retry decorator with exponential backoff
    
    지수 백오프가 있는 재시도 데코레이터
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        raise e
                    
                    # Calculate delay with exponential backoff
                    # 지수 백오프로 지연 시간 계산
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    # Add jitter to prevent thundering herd
                    # 천둥 소리 방지를 위한 지터 추가
                    jitter = random.uniform(0, 0.1 * delay)
                    delay += jitter
                    
                    print(f"Attempt {attempt + 1} failed: {e}")
                    print(f"Retrying in {delay:.2f} seconds...")
                    
                    time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator
```

### **HTTP 상태 코드별 에러 처리**

```javascript
// Node.js example - HTTP status code error handling
// Node.js 예제 - HTTP 상태 코드별 에러 처리
class FileWallBallError extends Error {
    constructor(message, statusCode, response) {
        super(message);
        this.name = 'FileWallBallError';
        this.statusCode = statusCode;
        this.response = response;
    }
}

function handleHttpError(response) {
    const { status, data } = response;
    
    switch (status) {
        case 400:
            throw new FileWallBallError(
                'Bad Request: Invalid parameters or file format',
                status,
                data
            );
            
        case 401:
            throw new FileWallBallError(
                'Unauthorized: Invalid or missing API key',
                status,
                data
            );
            
        case 404:
            throw new FileWallBallError(
                'File not found: The requested file does not exist',
                status,
                data
            );
            
        case 413:
            throw new FileWallBallError(
                'File too large: Exceeds maximum allowed size',
                status,
                data
            );
            
        case 429:
            throw new FileWallBallError(
                'Rate limited: Too many requests, please try again later',
                status,
                data
            );
            
        case 500:
            throw new FileWallBallError(
                'Internal server error: Please try again later',
                status,
                data
            );
            
        default:
            throw new FileWallBallError(
                `Unexpected error: HTTP ${status}`,
                status,
                data
            );
    }
}
```

## 📊 진행률 표시 및 사용자 피드백

### **진행률 표시 구현**

```go
// Go example - Progress tracking with channels
// Go 예제 - 채널을 사용한 진행률 추적
type ProgressTracker struct {
    Total     int64
    Current   int64
    Progress  chan ProgressUpdate
    Done      chan bool
}

type ProgressUpdate struct {
    Bytes     int64
    Percentage int
    Speed     float64 // bytes per second
}

func (pt *ProgressTracker) Start() {
    go func() {
        ticker := time.NewTicker(100 * time.Millisecond) // Update every 100ms
        defer ticker.Stop()
        
        startTime := time.Now()
        
        for {
            select {
            case <-ticker.C:
                if pt.Total > 0 {
                    percentage := int((pt.Current * 100) / pt.Total)
                    elapsed := time.Since(startTime).Seconds()
                    speed := float64(pt.Current) / elapsed
                    
                    pt.Progress <- ProgressUpdate{
                        Bytes:      pt.Current,
                        Percentage: percentage,
                        Speed:      speed,
                    }
                }
            case <-pt.Done:
                return
            }
        }
    }()
}
```

### **사용자 피드백 및 알림**

```python
# Python example - User feedback and notifications
# Python 예제 - 사용자 피드백 및 알림
import time
from datetime import datetime
from typing import Callable, Optional

class UserFeedback:
    """User feedback and notification system
    
    사용자 피드백 및 알림 시스템
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.start_time = None
        self.operation_name = ""
    
    def start_operation(self, operation_name: str):
        """Start timing an operation
        
        작업 타이밍 시작
        """
        self.operation_name = operation_name
        self.start_time = time.time()
        
        if self.verbose:
            print(f"🚀 Starting: {operation_name}")
    
    def update_progress(self, current: int, total: int, 
                       message: Optional[str] = None):
        """Update operation progress
        
        작업 진행률 업데이트
        """
        if not self.verbose:
            return
        
        percentage = (current / total * 100) if total > 0 else 0
        bar_length = 30
        filled_length = int(bar_length * current // total)
        
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        progress_text = f"\r{self.operation_name}: [{bar}] {percentage:.1f}%"
        if message:
            progress_text += f" - {message}"
        
        print(progress_text, end='', flush=True)
    
    def complete_operation(self, success: bool = True, 
                          message: Optional[str] = None):
        """Mark operation as complete
        
        작업 완료 표시
        """
        if not self.verbose:
            return
        
        elapsed_time = time.time() - self.start_time
        
        if success:
            status_icon = "✅"
            status_text = "Completed"
        else:
            status_icon = "❌"
            status_text = "Failed"
        
        print(f"\n{status_icon} {self.operation_name}: {status_text}")
        print(f"   Time: {elapsed_time:.2f} seconds")
        
        if message:
            print(f"   Details: {message}")
```

## 🚀 성능 최적화

### **청크 업로드 및 병렬 처리**

```javascript
// Node.js example - Chunked upload with parallel processing
// Node.js 예제 - 병렬 처리가 있는 청크 업로드
class ChunkedUploader {
    constructor(filePath, chunkSize = 1024 * 1024) { // 1MB chunks
        this.filePath = filePath;
        this.chunkSize = chunkSize;
        this.fileSize = fs.statSync(filePath).size;
        this.totalChunks = Math.ceil(this.fileSize / this.chunkSize);
        this.uploadedChunks = new Set();
        this.failedChunks = new Set();
    }
    
    async uploadChunk(chunkIndex) {
        const start = chunkIndex * this.chunkSize;
        const end = Math.min(start + this.chunkSize, this.fileSize);
        const chunk = fs.createReadStream(this.filePath, { start, end });
        
        try {
            const form = new FormData();
            form.append('chunk', chunk);
            form.append('chunkIndex', chunkIndex.toString());
            form.append('totalChunks', this.totalChunks.toString());
            
            const response = await axios.post(
                `${BASE_URL}/upload-chunk`,
                form,
                {
                    headers: { ...form.getHeaders(), ...getAuthHeaders() },
                    timeout: 30000
                }
            );
            
            this.uploadedChunks.add(chunkIndex);
            return { success: true, chunkIndex };
            
        } catch (error) {
            this.failedChunks.add(chunkIndex);
            return { success: false, chunkIndex, error: error.message };
        }
    }
    
    async uploadWithRetry(maxConcurrency = 3) {
        const chunks = Array.from({ length: this.totalChunks }, (_, i) => i);
        
        // Process chunks in batches
        // 청크를 배치로 처리
        for (let i = 0; i < chunks.length; i += maxConcurrency) {
            const batch = chunks.slice(i, i + maxConcurrency);
            
            const promises = batch.map(chunkIndex => this.uploadChunk(chunkIndex));
            const results = await Promise.allSettled(promises);
            
            // Handle results
            // 결과 처리
            results.forEach((result, index) => {
                if (result.status === 'fulfilled') {
                    const { success, chunkIndex, error } = result.value;
                    if (success) {
                        console.log(`✅ Chunk ${chunkIndex} uploaded successfully`);
                    } else {
                        console.log(`❌ Chunk ${chunkIndex} failed: ${error}`);
                    }
                } else {
                    console.log(`❌ Chunk ${batch[index]} failed: ${result.reason}`);
                }
            });
            
            // Progress update
            // 진행률 업데이트
            const progress = ((i + batch.length) / chunks.length * 100).toFixed(1);
            console.log(`📊 Upload progress: ${progress}%`);
        }
        
        // Finalize upload if all chunks succeeded
        // 모든 청크가 성공하면 업로드 완료
        if (this.uploadedChunks.size === this.totalChunks) {
            return await this.finalizeUpload();
        } else {
            throw new Error(`Upload incomplete: ${this.failedChunks.size} chunks failed`);
        }
    }
}
```

## 📊 모니터링 및 로깅

### **구조화된 로깅**

```python
# Python example - Structured logging
# Python 예제 - 구조화된 로깅
import logging
import json
from datetime import datetime
from typing import Dict, Any

class StructuredLogger:
    """Structured logging for FileWallBall operations
    
    FileWallBall 작업을 위한 구조화된 로깅
    """
    
    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # JSON formatter
        # JSON 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_operation(self, operation: str, **kwargs):
        """Log operation with structured data
        
        구조화된 데이터와 함께 작업 로깅
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "level": "INFO",
            **kwargs
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_error(self, operation: str, error: Exception, **kwargs):
        """Log error with structured data
        
        구조화된 데이터와 함께 에러 로깅
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "level": "ERROR",
            "error_type": type(error).__name__,
            "error_message": str(error),
            **kwargs
        }
        
        self.logger.error(json.dumps(log_data))
```

---

**참고**: 이 가이드는 FileWallBall API v2.0.0을 기준으로 작성되었습니다.
