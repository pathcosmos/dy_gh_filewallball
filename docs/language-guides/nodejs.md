# FileWallBall API - Node.js 사용법 가이드

Node.js 환경에서 FileWallBall API를 사용하여 파일 업로드, 다운로드, 관리 기능을 구현하는 방법을 설명합니다.

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
# Initialize project
# 프로젝트 초기화
npm init -y

# Install dependencies
# 의존성 설치
npm install axios form-data fs-extra
npm install --save-dev @types/node
```

### **package.json 의존성**

```json
{
  "dependencies": {
    "axios": "^1.6.0",
    "form-data": "^4.0.0",
    "fs-extra": "^11.1.1"
  },
  "devDependencies": {
    "@types/node": "^20.8.0"
  },
  "type": "module"
}
```

## 🚀 기본 사용법

### **HTTP 클라이언트 설정**

```javascript
import axios from 'axios';
import FormData from 'form-data';

class FileWallBallClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        
        // Create axios instance with default configuration
        // 기본 설정으로 axios 인스턴스 생성
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 60000,  // 60초 타임아웃
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'User-Agent': 'FileWallBall-NodeJS-Client/2.0.0'
            }
        });
        
        // Add request interceptor for logging
        // 로깅을 위한 요청 인터셉터 추가
        this.client.interceptors.request.use(
            config => {
                console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
                return config;
            },
            error => {
                console.error('Request error:', error);
                return Promise.reject(error);
            }
        );
        
        // Add response interceptor for error handling
        // 에러 처리를 위한 응답 인터셉터 추가
        this.client.interceptors.response.use(
            response => response,
            error => {
                console.error('Response error:', error.response?.status, error.response?.data);
                return Promise.reject(error);
            }
        );
    }
    
    // Create authenticated request headers
    // 인증된 요청 헤더 생성
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
        };
    }
}
```

## 📤 파일 업로드

### **기본 파일 업로드**

```javascript
import fs from 'fs-extra';
import path from 'path';

class FileUploader {
    constructor(client) {
        this.client = client;
    }
    
    // Upload file to FileWallBall API
    // FileWallBall API에 파일 업로드
    async uploadFile(filePath) {
        try {
            // Check if file exists
            // 파일 존재 여부 확인
            if (!await fs.pathExists(filePath)) {
                throw new Error(`File not found: ${filePath}`);
            }
            
            // Get file stats for validation
            // 파일 통계 정보로 유효성 검사
            const stats = await fs.stat(filePath);
            if (stats.size === 0) {
                throw new Error('Cannot upload empty file');
            }
            
            // Create form data for multipart upload
            // 멀티파트 업로드를 위한 폼 데이터 생성
            const form = new FormData();
            const fileStream = fs.createReadStream(filePath);
            
            // Add file to form with metadata
            // 메타데이터와 함께 폼에 파일 추가
            form.append('file', fileStream, {
                filename: path.basename(filePath),
                contentType: this.getMimeType(filePath)
            });
            
            // Upload file with progress tracking
            // 진행률 추적과 함께 파일 업로드
            const response = await this.client.post('/upload', form, {
                headers: {
                    ...form.getHeaders(),
                    'Content-Length': stats.size
                },
                maxContentLength: Infinity,  // 최대 콘텐츠 길이 무제한
                maxBodyLength: Infinity,     // 최대 본문 길이 무제한
                onUploadProgress: (progressEvent) => {
                    // Calculate upload progress
                    // 업로드 진행률 계산
                    const percentCompleted = Math.round(
                        (progressEvent.loaded * 100) / progressEvent.total
                    );
                    console.log(`Upload progress: ${percentCompleted}%`);
                }
            });
            
            return response.data;
            
        } catch (error) {
            console.error('Upload failed:', error.message);
            throw error;
        }
    }
    
    // Get MIME type based on file extension
    // 파일 확장자 기반 MIME 타입 추출
    getMimeType(filePath) {
        const ext = path.extname(filePath).toLowerCase();
        const mimeTypes = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        };
        
        return mimeTypes[ext] || 'application/octet-stream';
    }
    
    // Upload multiple files with batch processing
    // 배치 처리로 여러 파일 업로드
    async uploadMultipleFiles(filePaths) {
        const results = [];
        const errors = [];
        
        for (const filePath of filePaths) {
            try {
                const result = await this.uploadFile(filePath);
                results.push(result);
                console.log(`✅ Uploaded: ${path.basename(filePath)}`);
            } catch (error) {
                errors.push({ filePath, error: error.message });
                console.error(`❌ Failed to upload: ${path.basename(filePath)}`);
            }
        }
        
        return { results, errors };
    }
}
```

### **응답 모델 타입 정의**

```javascript
// File upload response model
// 파일 업로드 응답 모델
class FileUploadResponse {
    constructor(data) {
        this.fileId = data.file_id;           // Generated unique file ID
        this.filename = data.filename;         // Original filename
        this.fileSize = data.file_size;        // File size in bytes
        this.uploadTime = new Date(data.upload_time); // Upload completion time
        this.downloadUrl = data.download_url;  // File download URL
        this.viewUrl = data.view_url;          // File viewer URL
        this.message = data.message;           // Processing result message
    }
    
    // Get human readable file size
    // 사람이 읽기 쉬운 파일 크기 반환
    getHumanReadableSize() {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = this.fileSize;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }
    
    // Get formatted upload time
    // 포맷된 업로드 시간 반환
    getFormattedUploadTime() {
        return this.uploadTime.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}
```

## ⬇️ 파일 다운로드

### **파일 다운로드 및 저장**

```javascript
import fs from 'fs-extra';
import path from 'path';

class FileDownloader {
    constructor(client) {
        this.client = client;
    }
    
    // Download file from FileWallBall API
    // FileWallBall API에서 파일 다운로드
    async downloadFile(fileId, outputPath) {
        try {
            // Create output directory if it doesn't exist
            // 출력 디렉토리가 없으면 생성
            const outputDir = path.dirname(outputPath);
            await fs.ensureDir(outputDir);
            
            // Download file with streaming
            // 스트리밍으로 파일 다운로드
            const response = await this.client.get(`/download/${fileId}`, {
                responseType: 'stream',
                onDownloadProgress: (progressEvent) => {
                    // Calculate download progress
                    // 다운로드 진행률 계산
                    if (progressEvent.total) {
                        const percentCompleted = Math.round(
                            (progressEvent.loaded * 100) / progressEvent.total
                        );
                        console.log(`Download progress: ${percentCompleted}%`);
                    }
                }
            });
            
            // Get filename from response headers
            // 응답 헤더에서 파일명 추출
            const contentDisposition = response.headers['content-disposition'];
            let filename = path.basename(outputPath);
            
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                    outputPath = path.join(outputDir, filename);
                }
            }
            
            // Save file to local path
            // 로컬 경로에 파일 저장
            const writer = fs.createWriteStream(outputPath);
            response.data.pipe(writer);
            
            return new Promise((resolve, reject) => {
                writer.on('finish', () => {
                    console.log(`✅ File downloaded: ${filename}`);
                    resolve({ filename, outputPath, size: response.headers['content-length'] });
                });
                
                writer.on('error', (error) => {
                    reject(new Error(`Failed to save file: ${error.message}`));
                });
            });
            
        } catch (error) {
            console.error('Download failed:', error.message);
            throw error;
        }
    }
    
    // Download file with custom filename
    // 사용자 정의 파일명으로 파일 다운로드
    async downloadFileAs(fileId, filename) {
        const outputPath = path.join(process.cwd(), 'downloads', filename);
        return this.downloadFile(fileId, outputPath);
    }
    
    // Download multiple files
    // 여러 파일 다운로드
    async downloadMultipleFiles(fileIds, outputDir = 'downloads') {
        const results = [];
        const errors = [];
        
        // Ensure output directory exists
        // 출력 디렉토리 존재 확인
        await fs.ensureDir(outputDir);
        
        for (const fileId of fileIds) {
            try {
                const outputPath = path.join(outputDir, `${fileId}_file`);
                const result = await this.downloadFile(fileId, outputPath);
                results.push(result);
            } catch (error) {
                errors.push({ fileId, error: error.message });
            }
        }
        
        return { results, errors };
    }
}
```

### **스트리밍 다운로드 (대용량 파일)**

```javascript
class StreamingDownloader {
    constructor(client) {
        this.client = client;
    }
    
    // Stream download for large files with progress tracking
    // 진행률 추적과 함께 대용량 파일 스트리밍 다운로드
    async streamDownload(fileId, outputPath, options = {}) {
        const {
            chunkSize = 8192,           // 8KB 청크
            onProgress = null,           // 진행률 콜백
            onChunk = null,             // 청크 콜백
            retryAttempts = 3           // 재시도 횟수
        } = options;
        
        let attempt = 0;
        
        while (attempt < retryAttempts) {
            try {
                return await this.performStreamDownload(fileId, outputPath, {
                    chunkSize,
                    onProgress,
                    onChunk
                });
            } catch (error) {
                attempt++;
                console.warn(`Download attempt ${attempt} failed:`, error.message);
                
                if (attempt >= retryAttempts) {
                    throw new Error(`Download failed after ${retryAttempts} attempts: ${error.message}`);
                }
                
                // Wait before retry with exponential backoff
                // 지수 백오프로 재시도 전 대기
                await this.delay(Math.pow(2, attempt) * 1000);
            }
        }
    }
    
    // Perform actual streaming download
    // 실제 스트리밍 다운로드 수행
    async performStreamDownload(fileId, outputPath, options) {
        const { chunkSize, onProgress, onChunk } = options;
        
        // Get file info first
        // 먼저 파일 정보 조회
        const fileInfo = await this.client.get(`/files/${fileId}`);
        const totalSize = fileInfo.data.file_size;
        
        // Create write stream
        // 쓰기 스트림 생성
        const writer = fs.createWriteStream(outputPath);
        let downloadedBytes = 0;
        
        // Download with range requests for large files
        // 대용량 파일을 위한 범위 요청으로 다운로드
        const response = await this.client.get(`/download/${fileId}`, {
            responseType: 'stream',
            headers: {
                'Range': `bytes=${downloadedBytes}-`
            }
        });
        
        return new Promise((resolve, reject) => {
            response.data.on('data', (chunk) => {
                downloadedBytes += chunk.length;
                
                // Report progress
                // 진행률 보고
                if (onProgress && totalSize > 0) {
                    const percentage = Math.round((downloadedBytes * 100) / totalSize);
                    onProgress(percentage, downloadedBytes, totalSize);
                }
                
                // Report chunk
                // 청크 보고
                if (onChunk) {
                    onChunk(chunk, downloadedBytes, totalSize);
                }
            });
            
            response.data.on('end', () => {
                writer.end();
                resolve({
                    filename: path.basename(outputPath),
                    size: downloadedBytes,
                    path: outputPath
                });
            });
            
            response.data.on('error', (error) => {
                writer.destroy();
                reject(error);
            });
            
            response.data.pipe(writer);
        });
    }
    
    // Utility function for delay
    // 지연을 위한 유틸리티 함수
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
```

## 📋 파일 관리

### **파일 목록 조회 및 관리**

```javascript
class FileManager {
    constructor(client) {
        this.client = client;
    }
    
    // Get list of uploaded files with pagination
    // 페이지네이션과 함께 업로드된 파일 목록 조회
    async getFileList(page = 1, limit = 20, sortBy = 'uploaded_at', order = 'desc') {
        try {
            const params = { page, limit, sort_by: sortBy, order };
            
            const response = await this.client.get('/files', { params });
            return response.data;
            
        } catch (error) {
            console.error('Failed to get file list:', error.message);
            throw error;
        }
    }
    
    // Get specific file information
    // 특정 파일 정보 조회
    async getFileInfo(fileId) {
        try {
            const response = await this.client.get(`/files/${fileId}`);
            return response.data;
            
        } catch (error) {
            console.error('Failed to get file info:', error.message);
            throw error;
        }
    }
    
    // Deactivate file (soft delete)
    // 파일 비활성화 (소프트 삭제)
    async deactivateFile(fileId) {
        try {
            const response = await this.client.delete(`/files/${fileId}`);
            return response.data;
            
        } catch (error) {
            console.error('Failed to deactivate file:', error.message);
            throw error;
        }
    }
    
    // Search files by criteria
    // 조건으로 파일 검색
    async searchFiles(criteria) {
        try {
            const { filename, mimeType, minSize, maxSize, dateFrom, dateTo } = criteria;
            const params = {};
            
            if (filename) params.filename = filename;
            if (mimeType) params.mime_type = mimeType;
            if (minSize) params.min_size = minSize;
            if (maxSize) params.max_size = maxSize;
            if (dateFrom) params.date_from = dateFrom;
            if (dateTo) params.date_to = dateTo;
            
            const response = await this.client.get('/files', { params });
            return response.data;
            
        } catch (error) {
            console.error('Failed to search files:', error.message);
            throw error;
        }
    }
}
```

## 🏥 시스템 관리

### **헬스체크 및 모니터링**

```javascript
class SystemMonitor {
    constructor(client) {
        this.client = client;
    }
    
    // Check system health status
    // 시스템 상태 확인
    async checkHealth() {
        try {
            const response = await this.client.get('/health');
            return response.data;
            
        } catch (error) {
            console.error('Health check failed:', error.message);
            throw error;
        }
    }
    
    // Monitor system health periodically
    // 주기적으로 시스템 상태 모니터링
    async startHealthMonitoring(intervalMs = 30000) { // 30초마다
        console.log('Starting health monitoring...');
        
        const monitor = setInterval(async () => {
            try {
                const health = await this.checkHealth();
                console.log(`Health check: ${health.status} at ${new Date().toISOString()}`);
                
                if (health.status === 'down') {
                    console.error('🚨 System is down!');
                    // Send alert or notification
                    // 알림 또는 알림 전송
                }
                
            } catch (error) {
                console.error('Health monitoring error:', error.message);
            }
        }, intervalMs);
        
        return monitor;
    }
    
    // Stop health monitoring
    // 상태 모니터링 중지
    stopHealthMonitoring(monitor) {
        if (monitor) {
            clearInterval(monitor);
            console.log('Health monitoring stopped');
        }
    }
}
```

## ⚠️ 에러 처리

### **HTTP 에러 처리 및 재시도**

```javascript
class ErrorHandler {
    // Handle HTTP errors with proper error types
    // 적절한 에러 타입으로 HTTP 에러 처리
    static handleHttpError(error) {
        if (error.response) {
            const { status, data } = error.response;
            
            switch (status) {
                case 400:
                    throw new BadRequestError(`Bad request: ${data.detail || 'Invalid input'}`);
                case 401:
                    throw new UnauthorizedError(`Unauthorized: ${data.detail || 'Invalid API key'}`);
                case 404:
                    throw new NotFoundError(`Not found: ${data.detail || 'Resource not found'}`);
                case 413:
                    throw new FileTooLargeError(`File too large: ${data.detail || 'File exceeds size limit'}`);
                case 429:
                    throw new RateLimitError(`Rate limited: ${data.detail || 'Too many requests'}`);
                case 500:
                    throw new ServerError(`Server error: ${data.detail || 'Internal server error'}`);
                default:
                    throw new HttpError(`HTTP ${status}: ${data.detail || 'Unknown error'}`);
            }
        } else if (error.request) {
            throw new NetworkError('Network error: No response received');
        } else {
            throw new Error(`Request error: ${error.message}`);
        }
    }
    
    // Retry function with exponential backoff
    // 지수 백오프로 재시도 함수
    static async retryWithBackoff(fn, maxRetries = 3, baseDelay = 1000) {
        let lastError;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return await fn();
            } catch (error) {
                lastError = error;
                
                if (attempt === maxRetries) {
                    throw error;
                }
                
                // Calculate delay with exponential backoff
                // 지수 백오프로 지연 시간 계산
                const delay = baseDelay * Math.pow(2, attempt - 1);
                console.log(`Attempt ${attempt} failed, retrying in ${delay}ms...`);
                
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        throw lastError;
    }
}

// Custom error classes
// 커스텀 에러 클래스들
class HttpError extends Error {
    constructor(message) {
        super(message);
        this.name = 'HttpError';
    }
}

class BadRequestError extends HttpError {
    constructor(message) {
        super(message);
        this.name = 'BadRequestError';
    }
}

class UnauthorizedError extends HttpError {
    constructor(message) {
        super(message);
        this.name = 'UnauthorizedError';
    }
}

class NotFoundError extends HttpError {
    constructor(message) {
        super(message);
        this.name = 'NotFoundError';
    }
}

class FileTooLargeError extends HttpError {
    constructor(message) {
        super(message);
        this.name = 'FileTooLargeError';
    }
}

class RateLimitError extends HttpError {
    constructor(message) {
        super(message);
        this.name = 'RateLimitError';
    }
}

class ServerError extends HttpError {
    constructor(message) {
        super(message);
        this.name = 'ServerError';
    }
}

class NetworkError extends Error {
    constructor(message) {
        super(message);
        this.name = 'NetworkError';
    }
}
```

## 🚀 완전한 예제

### **메인 애플리케이션**

```javascript
import { FileWallBallClient, FileUploader, FileDownloader, FileManager, SystemMonitor } from './filewallball-client.js';

async function main() {
    try {
        // Initialize client
        // 클라이언트 초기화
        const client = new FileWallBallClient(
            'http://localhost:8000',
            'your-api-key-here'
        );
        
        // Initialize services
        // 서비스 초기화
        const uploader = new FileUploader(client);
        const downloader = new FileDownloader(client);
        const fileManager = new FileManager(client);
        const systemMonitor = new SystemMonitor(client);
        
        // Check system health
        // 시스템 상태 확인
        const health = await systemMonitor.checkHealth();
        console.log('System health:', health.status);
        
        // Upload file
        // 파일 업로드
        const uploadResult = await uploader.uploadFile('./example.txt');
        console.log('File uploaded:', uploadResult.fileId);
        
        // Get file list
        // 파일 목록 조회
        const fileList = await fileManager.getFileList(1, 10);
        console.log('Total files:', fileList.pagination.total);
        
        // Download file
        // 파일 다운로드
        const downloadResult = await downloader.downloadFile(
            uploadResult.fileId, 
            './downloaded_example.txt'
        );
        console.log('File downloaded:', downloadResult.filename);
        
        // Start health monitoring
        // 상태 모니터링 시작
        const monitor = await systemMonitor.startHealthMonitoring(60000); // 1분마다
        
        // Cleanup after 5 minutes
        // 5분 후 정리
        setTimeout(() => {
            systemMonitor.stopHealthMonitoring(monitor);
            console.log('Example completed');
        }, 300000);
        
    } catch (error) {
        console.error('Error in main:', error.message);
        process.exit(1);
    }
}

// Run main function
// 메인 함수 실행
if (import.meta.url === `file://${process.argv[1]}`) {
    main().catch(console.error);
}

export { main };
```

## 📝 사용 팁

### **성능 최적화**
1. **스트리밍**: 대용량 파일은 스트리밍 방식 사용
2. **병렬 처리**: 여러 파일 업로드/다운로드 시 Promise.all 활용
3. **청크 크기**: 적절한 청크 크기로 메모리 사용량 최적화

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
