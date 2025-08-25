# FileWallBall API - Java 사용법 가이드

Java 환경에서 FileWallBall API를 사용하여 파일 업로드, 다운로드, 관리 기능을 구현하는 방법을 설명합니다.

## 📋 목차

- [환경 설정](#환경-설정)
- [기본 사용법](#기본-사용법)
- [파일 업로드](#파일-업로드)
- [파일 다운로드](#파일-다운로드)
- [파일 관리](#파일-관리)
- [에러 처리](#에러-처리)
- [완전한 예제](#완전한-예제)

## 🔧 환경 설정

### **의존성 추가 (Maven)**

```xml
<dependencies>
    <!-- OkHttp - HTTP 클라이언트 -->
    <dependency>
        <groupId>com.squareup.okhttp3</groupId>
        <artifactId>okhttp</artifactId>
        <version>4.12.0</version>
    </dependency>
    
    <!-- OkHttp Multipart - 멀티파트 요청 지원 -->
    <dependency>
        <groupId>com.squareup.okhttp3</groupId>
        <artifactId>okhttp-multipart</artifactId>
        <version>4.12.0</version>
    </dependency>
    
    <!-- Jackson - JSON 처리 -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
        <version>2.15.2</version>
    </dependency>
    
    <!-- SLF4J - 로깅 -->
    <dependency>
        <groupId>org.slf4j</groupId>
        <artifactId>slf4j-api</artifactId>
        <version>2.0.9</version>
    </dependency>
</dependencies>
```

### **의존성 추가 (Gradle)**

```gradle
dependencies {
    implementation 'com.squareup.okhttp3:okhttp:4.12.0'
    implementation 'com.squareup.okhttp3:okhttp-multipart:4.12.0'
    implementation 'com.fasterxml.jackson.core:jackson-databind:2.15.2'
    implementation 'org.slf4j:slf4j-api:2.0.9'
}
```

## 🚀 기본 사용법

### **HTTP 클라이언트 설정**

```java
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import java.util.concurrent.TimeUnit;

public class FileWallBallClient {
    private final OkHttpClient client;
    private final String baseUrl;
    private final String apiKey;
    
    public FileWallBallClient(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        
        // HTTP Client Configuration (OkHttp 사용)
        // HTTP 클라이언트 설정
        this.client = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)  // 연결 타임아웃 설정
            .readTimeout(60, TimeUnit.SECONDS)     // 읽기 타임아웃 설정
            .writeTimeout(60, TimeUnit.SECONDS)    // 쓰기 타임아웃 설정
            .build();
    }
    
    // Create authenticated request builder
    // 인증된 요청 빌더 생성
    private Request.Builder createAuthenticatedRequest() {
        return new Request.Builder()
            .addHeader("Authorization", "Bearer " + apiKey)
            .addHeader("User-Agent", "FileWallBall-Java-Client/2.0.0");
    }
}
```

## 📤 파일 업로드

### **기본 파일 업로드**

```java
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.Response;
import java.io.File;

public class FileUploader {
    
    // Upload file to FileWallBall API
    // FileWallBall API에 파일 업로드
    public FileUploadResponse uploadFile(File file) throws IOException {
        // Create multipart request body
        // 멀티파트 요청 본문 생성
        RequestBody fileBody = RequestBody.create(
            MediaType.parse("application/octet-stream"), 
            file
        );
        
        MultipartBody requestBody = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", file.getName(), fileBody)  // 파일 데이터 추가
            .build();
        
        // Build request with authentication
        // 인증과 함께 요청 빌드
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/upload")
            .post(requestBody)
            .build();
        
        // Execute request
        // 요청 실행
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                String responseBody = response.body().string();
                return parseUploadResponse(responseBody);  // 응답 파싱
            } else {
                throw new IOException("Upload failed: " + response.code());
            }
        }
    }
    
    // Parse upload response JSON
    // 업로드 응답 JSON 파싱
    private FileUploadResponse parseUploadResponse(String json) throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        return mapper.readValue(json, FileUploadResponse.class);
    }
}
```

### **응답 모델 클래스**

```java
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;

public class FileUploadResponse {
    @JsonProperty("file_id")
    private String fileId;           // Generated unique file ID
    
    @JsonProperty("filename")
    private String filename;         // Original filename
    
    @JsonProperty("file_size")
    private long fileSize;           // File size in bytes
    
    @JsonProperty("upload_time")
    private LocalDateTime uploadTime; // Upload completion time
    
    @JsonProperty("download_url")
    private String downloadUrl;      // File download URL
    
    @JsonProperty("view_url")
    private String viewUrl;          // File viewer URL
    
    @JsonProperty("message")
    private String message;          // Processing result message
    
    // Getters and setters
    // 게터와 세터
    public String getFileId() { return fileId; }
    public void setFileId(String fileId) { this.fileId = fileId; }
    
    public String getFilename() { return filename; }
    public void setFilename(String filename) { this.filename = filename; }
    
    public long getFileSize() { return fileSize; }
    public void setFileSize(long fileSize) { this.fileSize = fileSize; }
    
    public LocalDateTime getUploadTime() { return uploadTime; }
    public void setUploadTime(LocalDateTime uploadTime) { this.uploadTime = uploadTime; }
    
    public String getDownloadUrl() { return downloadUrl; }
    public void setDownloadUrl(String downloadUrl) { this.downloadUrl = downloadUrl; }
    
    public String getViewUrl() { return viewUrl; }
    public void setViewUrl(String viewUrl) { this.viewUrl = viewUrl; }
    
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
}
```

## ⬇️ 파일 다운로드

### **파일 다운로드 및 저장**

```java
import java.io.FileOutputStream;
import java.io.InputStream;

public class FileDownloader {
    
    // Download file from FileWallBall API
    // FileWallBall API에서 파일 다운로드
    public void downloadFile(String fileId, String outputPath) throws IOException {
        // Build download request
        // 다운로드 요청 빌드
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/download/" + fileId)
            .get()
            .build();
        
        // Execute request and save file
        // 요청 실행 및 파일 저장
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                saveFile(response.body().byteStream(), outputPath);  // 파일 저장
            } else {
                throw new IOException("Download failed: " + response.code());
            }
        }
    }
    
    // Save downloaded file to local path
    // 다운로드된 파일을 로컬 경로에 저장
    private void saveFile(InputStream inputStream, String outputPath) throws IOException {
        File outputFile = new File(outputPath);
        outputFile.getParentFile().mkdirs();  // 디렉토리 생성
        
        try (FileOutputStream outputStream = new FileOutputStream(outputFile)) {
            byte[] buffer = new byte[8192];  // 8KB 버퍼
            int bytesRead;
            
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);  // 버퍼에 쓰기
            }
        }
    }
}
```

### **스트리밍 다운로드 (대용량 파일)**

```java
import okhttp3.ResponseBody;

public class StreamingDownloader {
    
    // Stream download for large files
    // 대용량 파일을 위한 스트리밍 다운로드
    public void streamDownload(String fileId, String outputPath, 
                             ProgressCallback callback) throws IOException {
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/download/" + fileId)
            .get()
            .build();
        
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                ResponseBody body = response.body();
                if (body != null) {
                    streamToFile(body, outputPath, callback);  // 파일로 스트리밍
                }
            } else {
                throw new IOException("Stream download failed: " + response.code());
            }
        }
    }
    
    // Stream response body to file with progress
    // 응답 본문을 진행률과 함께 파일로 스트리밍
    private void streamToFile(ResponseBody body, String outputPath, 
                             ProgressCallback callback) throws IOException {
        File outputFile = new File(outputPath);
        outputFile.getParentFile().mkdirs();
        
        long totalBytes = body.contentLength();
        long downloadedBytes = 0;
        
        try (InputStream inputStream = body.byteStream();
             FileOutputStream outputStream = new FileOutputStream(outputFile)) {
            
            byte[] buffer = new byte[8192];
            int bytesRead;
            
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
                downloadedBytes += bytesRead;
                
                // Report progress
                // 진행률 보고
                if (callback != null && totalBytes > 0) {
                    int progress = (int) ((downloadedBytes * 100) / totalBytes);
                    callback.onProgress(progress, downloadedBytes, totalBytes);
                }
            }
        }
    }
}

// Progress callback interface
// 진행률 콜백 인터페이스
interface ProgressCallback {
    void onProgress(int percentage, long downloaded, long total);
}
```

## 📋 파일 관리

### **파일 목록 조회**

```java
public class FileManager {
    
    // Get list of uploaded files
    // 업로드된 파일 목록 조회
    public FileListResponse getFileList(int page, int limit) throws IOException {
        String url = String.format("%s/files?page=%d&limit=%d", baseUrl, page, limit);
        
        Request request = createAuthenticatedRequest()
            .url(url)
            .get()
            .build();
        
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                String responseBody = response.body().string();
                return parseFileListResponse(responseBody);  // 응답 파싱
            } else {
                throw new IOException("Get file list failed: " + response.code());
            }
        }
    }
    
    // Get specific file information
    // 특정 파일 정보 조회
    public FileInfoResponse getFileInfo(String fileId) throws IOException {
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/files/" + fileId)
            .get()
            .build();
        
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                String responseBody = response.body().string();
                return parseFileInfoResponse(responseBody);  // 응답 파싱
            } else {
                throw new IOException("Get file info failed: " + response.code());
            }
        }
    }
    
    // Deactivate file (soft delete)
    // 파일 비활성화 (소프트 삭제)
    public DeactivateResponse deactivateFile(String fileId) throws IOException {
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/files/" + fileId)
            .delete()
            .build();
        
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                String responseBody = response.body().string();
                return parseDeactivateResponse(responseBody);  // 응답 파싱
            } else {
                throw new IOException("Deactivate file failed: " + response.code());
            }
        }
    }
}
```

## 🏥 시스템 관리

### **헬스체크**

```java
public class SystemMonitor {
    
    // Check system health status
    // 시스템 상태 확인
    public HealthResponse checkHealth() throws IOException {
        Request request = new Request.Builder()
            .url(baseUrl + "/health")
            .get()
            .build();
        
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                String responseBody = response.body().string();
                return parseHealthResponse(responseBody);  // 응답 파싱
            } else {
                throw new IOException("Health check failed: " + response.code());
            }
        }
    }
}
```

## ⚠️ 에러 처리

### **HTTP 에러 처리**

```java
public class ErrorHandler {
    
    // Handle HTTP errors with proper exception
    // 적절한 예외로 HTTP 에러 처리
    public static void handleHttpError(Response response) throws IOException {
        int code = response.code();
        String message = response.body() != null ? response.body().string() : "Unknown error";
        
        switch (code) {
            case 400:
                throw new BadRequestException("Bad request: " + message);
            case 401:
                throw new UnauthorizedException("Unauthorized: " + message);
            case 404:
                throw new FileNotFoundException("File not found: " + message);
            case 413:
                throw new FileTooLargeException("File too large: " + message);
            case 500:
                throw new ServerException("Server error: " + message);
            default:
                throw new IOException("HTTP " + code + ": " + message);
        }
    }
}

// Custom exception classes
// 커스텀 예외 클래스들
class BadRequestException extends IOException {
    public BadRequestException(String message) { super(message); }
}

class UnauthorizedException extends IOException {
    public UnauthorizedException(String message) { super(message); }
}

class FileNotFoundException extends IOException {
    public FileNotFoundException(String message) { super(message); }
}

class FileTooLargeException extends IOException {
    public FileTooLargeException(String message) { super(message); }
}

class ServerException extends IOException {
    public ServerException(String message) { super(message); }
}
```

## 🚀 완전한 예제

### **메인 애플리케이션**

```java
public class FileWallBallExample {
    public static void main(String[] args) {
        try {
            // Initialize client
            // 클라이언트 초기화
            FileWallBallClient client = new FileWallBallClient(
                "http://localhost:8000", 
                "your-api-key-here"
            );
            
            // Upload file
            // 파일 업로드
            File file = new File("example.txt");
            FileUploadResponse uploadResponse = client.uploadFile(file);
            System.out.println("File uploaded: " + uploadResponse.getFileId());
            
            // Download file
            // 파일 다운로드
            client.downloadFile(uploadResponse.getFileId(), "downloaded_example.txt");
            System.out.println("File downloaded successfully");
            
            // Get file list
            // 파일 목록 조회
            FileListResponse fileList = client.getFileList(1, 10);
            System.out.println("Total files: " + fileList.getPagination().getTotal());
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
```

## 📝 사용 팁

### **성능 최적화**
1. **연결 풀링**: OkHttpClient를 재사용하여 연결 풀 활용
2. **버퍼 크기**: 파일 업로드/다운로드 시 적절한 버퍼 크기 설정
3. **비동기 처리**: 대용량 파일 처리 시 비동기 방식 고려

### **에러 처리**
1. **재시도 로직**: 네트워크 오류 시 지수 백오프로 재시도
2. **로깅**: 상세한 에러 로그로 디버깅 지원
3. **사용자 피드백**: 진행률 표시 및 상태 메시지 제공

### **보안**
1. **API 키 관리**: 환경 변수나 설정 파일로 API 키 보호
2. **HTTPS 사용**: 프로덕션 환경에서는 HTTPS 필수
3. **입력 검증**: 파일명, 경로 등 사용자 입력 검증

---

**참고**: 이 가이드는 FileWallBall API v2.0.0을 기준으로 작성되었습니다.
