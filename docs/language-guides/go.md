# FileWallBall API - Go 사용법 가이드

Go 언어 환경에서 FileWallBall API를 사용하여 파일 업로드, 다운로드, 관리 기능을 구현하는 방법을 설명합니다.

## 📋 목차

- [환경 설정](#환경-설정)
- [기본 사용법](#기본-사용법)
- [파일 업로드](#파일-업로드)
- [파일 다운로드](#파일-다운로드)
- [파일 관리](#파일-관리)
- [에러 처리](#에러-처리)
- [완전한 예제](#완전한-예제)

## 🔧 환경 설정

### **Go 모듈 초기화**

```bash
# Initialize Go module
# Go 모듈 초기화
go mod init filewallball-client

# Install dependencies
# 의존성 설치
go get github.com/schollz/progressbar/v3
go get github.com/joho/godotenv
```

### **go.mod 파일**

```go
module filewallball-client

go 1.21

require (
    github.com/schollz/progressbar/v3 v3.13.1
    github.com/joho/godotenv v1.5.1
)
```

## 🚀 기본 사용법

### **HTTP 클라이언트 설정**

```go
package main

import (
    "crypto/tls"
    "net/http"
    "os"
    "time"
    
    "github.com/joho/godotenv"
)

// FileWallBallClient represents the main API client
// FileWallBallClient는 메인 API 클라이언트를 나타냅니다
type FileWallBallClient struct {
    BaseURL    string
    APIKey     string
    HTTPClient *http.Client
}

// NewFileWallBallClient creates a new client instance
// NewFileWallBallClient는 새로운 클라이언트 인스턴스를 생성합니다
func NewFileWallBallClient(baseURL, apiKey string) *FileWallBallClient {
    // Load environment variables if .env file exists
    // .env 파일이 존재하면 환경 변수 로드
    godotenv.Load()
    
    // Use provided API key or load from environment
    // 제공된 API 키 사용 또는 환경에서 로드
    if apiKey == "" {
        apiKey = os.Getenv("FILEWALLBALL_API_KEY")
    }
    
    // Create HTTP client with custom configuration
    // 커스텀 설정으로 HTTP 클라이언트 생성
    httpClient := &http.Client{
        Timeout: 60 * time.Second,  // 60초 타임아웃
        Transport: &http.Transport{
            TLSClientConfig: &tls.Config{
                InsecureSkipVerify: false,  // TLS 검증 활성화
            },
            MaxIdleConns:        100,              // 최대 유휴 연결 수
            MaxIdleConnsPerHost: 10,               // 호스트당 최대 유휴 연결 수
            IdleConnTimeout:     90 * time.Second, // 유휴 연결 타임아웃
        },
    }
    
    return &FileWallBallClient{
        BaseURL:    baseURL,
        APIKey:     apiKey,
        HTTPClient: httpClient,
    }
}

// getAuthHeaders returns authentication headers
// getAuthHeaders는 인증 헤더를 반환합니다
func (c *FileWallBallClient) getAuthHeaders() map[string]string {
    return map[string]string{
        "Authorization": "Bearer " + c.APIKey,
        "User-Agent":    "FileWallBall-Go-Client/2.0.0",
    }
}

// Close closes the HTTP client
// Close는 HTTP 클라이언트를 종료합니다
func (c *FileWallBallClient) Close() {
    c.HTTPClient.CloseIdleConnections()
}
```

## 📤 파일 업로드

### **기본 파일 업로드**

```go
import (
    "bytes"
    "fmt"
    "io"
    "mime/multipart"
    "net/http"
    "os"
    "path/filepath"
)

// FileUploader handles file upload operations
// FileUploader는 파일 업로드 작업을 처리합니다
type FileUploader struct {
    client *FileWallBallClient
}

// NewFileUploader creates a new file uploader
// NewFileUploader는 새로운 파일 업로더를 생성합니다
func NewFileUploader(client *FileWallBallClient) *FileUploader {
    return &FileUploader{client: client}
}

// FileUploadResponse represents the upload response
// FileUploadResponse는 업로드 응답을 나타냅니다
type FileUploadResponse struct {
    FileID       string `json:"file_id"`        // Generated unique file ID
    Filename     string `json:"filename"`        // Original filename
    FileSize     int64  `json:"file_size"`      // File size in bytes
    UploadTime   string `json:"upload_time"`    // Upload completion time
    DownloadURL  string `json:"download_url"`   // File download URL
    ViewURL      string `json:"view_url"`       // File viewer URL
    Message      string `json:"message"`         // Processing result message
}

// UploadFile uploads a file to FileWallBall API
// UploadFile은 FileWallBall API에 파일을 업로드합니다
func (u *FileUploader) UploadFile(filePath string) (*FileUploadResponse, error) {
    // Check if file exists
    // 파일 존재 여부 확인
    file, err := os.Open(filePath)
    if err != nil {
        return nil, fmt.Errorf("failed to open file: %w", err)
    }
    defer file.Close()
    
    // Get file info for validation
    // 유효성 검사를 위한 파일 정보 조회
    fileInfo, err := file.Stat()
    if err != nil {
        return nil, fmt.Errorf("failed to get file info: %w", err)
    }
    
    // Check if file is empty
    // 파일이 비어있는지 확인
    if fileInfo.Size() == 0 {
        return nil, fmt.Errorf("cannot upload empty file")
    }
    
    // Create multipart form data
    // 멀티파트 폼 데이터 생성
    body := &bytes.Buffer{}
    writer := multipart.NewWriter(body)
    
    // Create form file part
    // 폼 파일 파트 생성
    part, err := writer.CreateFormFile("file", filepath.Base(filePath))
    if err != nil {
        return nil, fmt.Errorf("failed to create form file: %w", err)
    }
    
    // Copy file content to form part
    // 파일 내용을 폼 파트에 복사
    _, err = io.Copy(part, file)
    if err != nil {
        return nil, fmt.Errorf("failed to copy file content: %w", err)
    }
    
    // Close multipart writer
    // 멀티파트 라이터 종료
    err = writer.Close()
    if err != nil {
        return nil, fmt.Errorf("failed to close multipart writer: %w", err)
    }
    
    // Create HTTP request
    // HTTP 요청 생성
    req, err := http.NewRequest("POST", u.client.BaseURL+"/upload", body)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    // Set headers
    // 헤더 설정
    req.Header.Set("Content-Type", writer.FormDataContentType())
    for key, value := range u.client.getAuthHeaders() {
        req.Header.Set(key, value)
    }
    
    // Execute request
    // 요청 실행
    resp, err := u.client.HTTPClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response status
    // 응답 상태 확인
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("upload failed with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    // Parse response
    // 응답 파싱
    var uploadResp FileUploadResponse
    if err := json.NewDecoder(resp.Body).Decode(&uploadResp); err != nil {
        return nil, fmt.Errorf("failed to decode response: %w", err)
    }
    
    return &uploadResp, nil
}

// UploadFileWithProgress uploads file with progress tracking
// UploadFileWithProgress는 진행률 추적과 함께 파일을 업로드합니다
func (u *FileUploader) UploadFileWithProgress(filePath string) (*FileUploadResponse, error) {
    // Get file size for progress calculation
    // 진행률 계산을 위한 파일 크기 조회
    fileInfo, err := os.Stat(filePath)
    if err != nil {
        return nil, fmt.Errorf("failed to get file info: %w", err)
    }
    
    // Create progress bar
    // 진행률 표시줄 생성
    bar := progressbar.NewOptions64(
        fileInfo.Size(),
        progressbar.OptionEnableColorCodes(true),
        progressbar.OptionShowBytes(true),
        progressbar.OptionSetWidth(15),
        progressbar.OptionSetDescription("Uploading"),
        progressbar.OptionSetTheme(progressbar.Theme{
            Saucer:        "[green]=[reset]",
            SaucerHead:    "[green]>[reset]",
            SaucerPadding: " ",
            BarStart:      "[",
            BarEnd:        "]",
        }),
    )
    
    // Open file for reading
    // 파일을 읽기 위해 열기
    file, err := os.Open(filePath)
    if err != nil {
        return nil, fmt.Errorf("failed to open file: %w", err)
    }
    defer file.Close()
    
    // Create progress reader
    // 진행률 리더 생성
    progressReader := &ProgressReader{
        Reader:   file,
        Progress: bar,
    }
    
    // Create multipart form data with progress
    // 진행률과 함께 멀티파트 폼 데이터 생성
    body := &bytes.Buffer{}
    writer := multipart.NewWriter(body)
    
    part, err := writer.CreateFormFile("file", filepath.Base(filePath))
    if err != nil {
        return nil, fmt.Errorf("failed to create form file: %w", err)
    }
    
    // Copy file content with progress tracking
    // 진행률 추적과 함께 파일 내용 복사
    _, err = io.Copy(part, progressReader)
    if err != nil {
        return nil, fmt.Errorf("failed to copy file content: %w", err)
    }
    
    writer.Close()
    
    // Create and execute request
    // 요청 생성 및 실행
    req, err := http.NewRequest("POST", u.client.BaseURL+"/upload", body)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    req.Header.Set("Content-Type", writer.FormDataContentType())
    for key, value := range u.client.getAuthHeaders() {
        req.Header.Set(key, value)
    }
    
    resp, err := u.client.HTTPClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response and parse
    // 응답 확인 및 파싱
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("upload failed with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    var uploadResp FileUploadResponse
    if err := json.NewDecoder(resp.Body).Decode(&uploadResp); err != nil {
        return nil, fmt.Errorf("failed to decode response: %w", err)
    }
    
    return &uploadResp, nil
}

// ProgressReader wraps io.Reader to track progress
// ProgressReader는 진행률을 추적하기 위해 io.Reader를 래핑합니다
type ProgressReader struct {
    Reader   io.Reader
    Progress *progressbar.ProgressBar
}

// Read implements io.Reader interface
// Read는 io.Reader 인터페이스를 구현합니다
func (pr *ProgressReader) Read(p []byte) (n int, err error) {
    n, err = pr.Reader.Read(p)
    if n > 0 {
        pr.Progress.Add(n)
    }
    return n, err
}
```

### **MIME 타입 처리**

```go
// getMimeType returns MIME type based on file extension
// getMimeType는 파일 확장자 기반 MIME 타입을 반환합니다
func getMimeType(filePath string) string {
    ext := strings.ToLower(filepath.Ext(filePath))
    
    mimeTypes := map[string]string{
        ".txt":  "text/plain",
        ".md":   "text/markdown",
        ".json": "application/json",
        ".xml":  "application/xml",
        ".csv":  "text/csv",
        ".html": "text/html",
        ".css":  "text/css",
        ".js":   "application/javascript",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".bmp":  "image/bmp",
        ".webp": "image/webp",
        ".pdf":  "application/pdf",
        ".doc":  "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".zip":  "application/zip",
        ".tar":  "application/x-tar",
        ".gz":   "application/gzip",
    }
    
    if mimeType, exists := mimeTypes[ext]; exists {
        return mimeType
    }
    
    return "application/octet-stream"
}
```

## ⬇️ 파일 다운로드

### **파일 다운로드 및 저장**

```go
import (
    "fmt"
    "io"
    "net/http"
    "os"
    "path/filepath"
)

// FileDownloader handles file download operations
// FileDownloader는 파일 다운로드 작업을 처리합니다
type FileDownloader struct {
    client *FileWallBallClient
}

// NewFileDownloader creates a new file downloader
// NewFileDownloader는 새로운 파일 다운로더를 생성합니다
func NewFileDownloader(client *FileWallBallClient) *FileDownloader {
    return &FileDownloader{client: client}
}

// DownloadResult represents download operation result
// DownloadResult는 다운로드 작업 결과를 나타냅니다
type DownloadResult struct {
    Filename string `json:"filename"`
    Path     string `json:"path"`
    Size     int64  `json:"size"`
    Status   string `json:"status"`
}

// DownloadFile downloads a file from FileWallBall API
// DownloadFile은 FileWallBall API에서 파일을 다운로드합니다
func (d *FileDownloader) DownloadFile(fileID, outputPath string) (*DownloadResult, error) {
    // Create output directory if it doesn't exist
    // 출력 디렉토리가 없으면 생성
    outputDir := filepath.Dir(outputPath)
    if err := os.MkdirAll(outputDir, 0755); err != nil {
        return nil, fmt.Errorf("failed to create output directory: %w", err)
    }
    
    // Create HTTP request
    // HTTP 요청 생성
    req, err := http.NewRequest("GET", d.client.BaseURL+"/download/"+fileID, nil)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    // Set authentication headers
    // 인증 헤더 설정
    for key, value := range d.client.getAuthHeaders() {
        req.Header.Set(key, value)
    }
    
    // Execute request
    // 요청 실행
    resp, err := d.client.HTTPClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response status
    // 응답 상태 확인
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("download failed with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    // Get filename from response headers
    // 응답 헤더에서 파일명 추출
    filename := filepath.Base(outputPath)
    if contentDisposition := resp.Header.Get("Content-Disposition"); contentDisposition != "" {
        if strings.Contains(contentDisposition, "filename=") {
            // Extract filename from Content-Disposition header
            // Content-Disposition 헤더에서 파일명 추출
            start := strings.Index(contentDisposition, "filename=")
            if start != -1 {
                start += 9 // "filename=" length
                end := strings.Index(contentDisposition[start:], "\"")
                if end != -1 {
                    filename = contentDisposition[start : start+end]
                    outputPath = filepath.Join(outputDir, filename)
                }
            }
        }
    }
    
    // Create output file
    // 출력 파일 생성
    outputFile, err := os.Create(outputPath)
    if err != nil {
        return nil, fmt.Errorf("failed to create output file: %w", err)
    }
    defer outputFile.Close()
    
    // Copy response body to file
    // 응답 본문을 파일에 복사
    bytesWritten, err := io.Copy(outputFile, resp.Body)
    if err != nil {
        return nil, fmt.Errorf("failed to write file: %w", err)
    }
    
    return &DownloadResult{
        Filename: filename,
        Path:     outputPath,
        Size:     bytesWritten,
        Status:   "completed",
    }, nil
}

// DownloadFileWithProgress downloads file with progress tracking
// DownloadFileWithProgress는 진행률 추적과 함께 파일을 다운로드합니다
func (d *FileDownloader) DownloadFileWithProgress(fileID, outputPath string) (*DownloadResult, error) {
    // Create output directory
    // 출력 디렉토리 생성
    outputDir := filepath.Dir(outputPath)
    if err := os.MkdirAll(outputDir, 0755); err != nil {
        return nil, fmt.Errorf("failed to create output directory: %w", err)
    }
    
    // Create HTTP request
    // HTTP 요청 생성
    req, err := http.NewRequest("GET", d.client.BaseURL+"/download/"+fileID, nil)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    // Set authentication headers
    // 인증 헤더 설정
    for key, value := range d.client.getAuthHeaders() {
        req.Header.Set(key, value)
    }
    
    // Execute request
    // 요청 실행
    resp, err := d.client.HTTPClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response status
    // 응답 상태 확인
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("download failed with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    // Get file size for progress bar
    // 진행률 표시줄을 위한 파일 크기 조회
    totalSize := resp.ContentLength
    if totalSize <= 0 {
        // If content length is not available, download without progress
        // 콘텐츠 길이를 사용할 수 없으면 진행률 없이 다운로드
        return d.DownloadFile(fileID, outputPath)
    }
    
    // Create progress bar
    // 진행률 표시줄 생성
    bar := progressbar.NewOptions64(
        totalSize,
        progressbar.OptionEnableColorCodes(true),
        progressbar.OptionShowBytes(true),
        progressbar.OptionSetWidth(15),
        progressbar.OptionSetDescription("Downloading"),
        progressbar.OptionSetTheme(progressbar.Theme{
            Saucer:        "[blue]=[reset]",
            SaucerHead:    "[blue]>[reset]",
            SaucerPadding: " ",
            BarStart:      "[",
            BarEnd:        "]",
        }),
    )
    
    // Create output file
    // 출력 파일 생성
    outputFile, err := os.Create(outputPath)
    if err != nil {
        return nil, fmt.Errorf("failed to create output file: %w", err)
    }
    defer outputFile.Close()
    
    // Create progress writer
    // 진행률 라이터 생성
    progressWriter := &ProgressWriter{
        Writer:   outputFile,
        Progress: bar,
    }
    
    // Copy response body with progress tracking
    // 진행률 추적과 함께 응답 본문 복사
    bytesWritten, err := io.Copy(progressWriter, resp.Body)
    if err != nil {
        return nil, fmt.Errorf("failed to write file: %w", err)
    }
    
    return &DownloadResult{
        Filename: filepath.Base(outputPath),
        Path:     outputPath,
        Size:     bytesWritten,
        Status:   "completed",
    }, nil
}

// ProgressWriter wraps io.Writer to track progress
// ProgressWriter는 진행률을 추적하기 위해 io.Writer를 래핑합니다
type ProgressWriter struct {
    Writer   io.Writer
    Progress *progressbar.ProgressBar
}

// Write implements io.Writer interface
// Write는 io.Writer 인터페이스를 구현합니다
func (pw *ProgressWriter) Write(p []byte) (n int, err error) {
    n, err = pw.Writer.Write(p)
    if n > 0 {
        pw.Progress.Add(n)
    }
    return n, err
}
```

## 📋 파일 관리

### **파일 목록 조회 및 관리**

```go
import (
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
)

// FileManager handles file management operations
// FileManager는 파일 관리 작업을 처리합니다
type FileManager struct {
    client *FileWallBallClient
}

// NewFileManager creates a new file manager
// NewFileManager는 새로운 파일 매니저를 생성합니다
func NewFileManager(client *FileWallBallClient) *FileManager {
    return &FileManager{client: client}
}

// FileInfo represents file information
// FileInfo는 파일 정보를 나타냅니다
type FileInfo struct {
    FileID     string `json:"file_id"`
    Filename   string `json:"filename"`
    FileSize   int64  `json:"file_size"`
    MimeType   string `json:"mime_type"`
    UploadTime string `json:"upload_time"`
    Status     string `json:"status"`
}

// FileListResponse represents file list response
// FileListResponse는 파일 목록 응답을 나타냅니다
type FileListResponse struct {
    Files       []FileInfo `json:"files"`
    Pagination  struct {
        Page       int `json:"page"`
        Limit      int `json:"limit"`
        Total      int `json:"total"`
        TotalPages int `json:"total_pages"`
    } `json:"pagination"`
}

// GetFileList retrieves list of uploaded files
// GetFileList는 업로드된 파일 목록을 조회합니다
func (fm *FileManager) GetFileList(page, limit int, sortBy, order string) (*FileListResponse, error) {
    // Build query parameters
    // 쿼리 매개변수 빌드
    params := url.Values{}
    params.Set("page", fmt.Sprintf("%d", page))
    params.Set("limit", fmt.Sprintf("%d", limit))
    if sortBy != "" {
        params.Set("sort_by", sortBy)
    }
    if order != "" {
        params.Set("order", order)
    }
    
    // Create HTTP request
    // HTTP 요청 생성
    req, err := http.NewRequest("GET", fm.client.BaseURL+"/files?"+params.Encode(), nil)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    // Set authentication headers
    // 인증 헤더 설정
    for key, value := range fm.client.getAuthHeaders() {
        req.Header.Set(key, value)
    }
    
    // Execute request
    // 요청 실행
    resp, err := fm.client.HTTPClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response status
    // 응답 상태 확인
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("failed to get file list with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    // Parse response
    // 응답 파싱
    var fileListResp FileListResponse
    if err := json.NewDecoder(resp.Body).Decode(&fileListResp); err != nil {
        return nil, fmt.Errorf("failed to decode response: %w", err)
    }
    
    return &fileListResp, nil
}

// GetFileInfo retrieves specific file information
// GetFileInfo는 특정 파일 정보를 조회합니다
func (fm *FileManager) GetFileInfo(fileID string) (*FileInfo, error) {
    // Create HTTP request
    // HTTP 요청 생성
    req, err := http.NewRequest("GET", fm.client.BaseURL+"/files/"+fileID, nil)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    // Set authentication headers
    // 인증 헤더 설정
    for key, value := range fm.client.getAuthHeaders() {
        req.Header.Set(key, value)
    }
    
    // Execute request
    // 요청 실행
    resp, err := fm.client.HTTPClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response status
    // 응답 상태 확인
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("failed to get file info with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    // Parse response
    // 응답 파싱
    var fileInfo FileInfo
    if err := json.NewDecoder(resp.Body).Decode(&fileInfo); err != nil {
        return nil, fmt.Errorf("failed to decode response: %w", err)
    }
    
    return &fileInfo, nil
}

// DeactivateFile deactivates a file (soft delete)
// DeactivateFile은 파일을 비활성화합니다 (소프트 삭제)
func (fm *FileManager) DeactivateFile(fileID string) error {
    // Create HTTP request
    // HTTP 요청 생성
    req, err := http.NewRequest("DELETE", fm.client.BaseURL+"/files/"+fileID, nil)
    if err != nil {
        return fmt.Errorf("failed to create request: %w", err)
    }
    
    // Set authentication headers
    // 인증 헤더 설정
    for key, value := range fm.client.getAuthHeaders() {
        req.Header.Set(key, value)
    }
    
    // Execute request
    // 요청 실행
    resp, err := fm.client.HTTPClient.Do(req)
    if err != nil {
        return fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response status
    // 응답 상태 확인
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return fmt.Errorf("failed to deactivate file with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    return nil
}
```

## 🏥 시스템 관리

### **헬스체크 및 모니터링**

```go
import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

// SystemMonitor handles system monitoring operations
// SystemMonitor는 시스템 모니터링 작업을 처리합니다
type SystemMonitor struct {
    client *FileWallBallClient
}

// NewSystemMonitor creates a new system monitor
// NewSystemMonitor는 새로운 시스템 모니터를 생성합니다
func NewSystemMonitor(client *FileWallBallClient) *SystemMonitor {
    return &SystemMonitor{client: client}
}

// HealthResponse represents health check response
// HealthResponse는 헬스체크 응답을 나타냅니다
type HealthResponse struct {
    Status    string    `json:"status"`
    Timestamp time.Time `json:"timestamp"`
    Uptime    string    `json:"uptime"`
    Version   string    `json:"version"`
}

// CheckHealth checks system health status
// CheckHealth는 시스템 상태를 확인합니다
func (sm *SystemMonitor) CheckHealth() (*HealthResponse, error) {
    // Create HTTP request
    // HTTP 요청 생성
    req, err := http.NewRequest("GET", sm.client.BaseURL+"/health", nil)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    // Execute request
    // 요청 실행
    resp, err := sm.client.HTTPClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check response status
    // 응답 상태 확인
    if resp.StatusCode != http.StatusOK {
        bodyBytes, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("health check failed with status %d: %s", resp.StatusCode, string(bodyBytes))
    }
    
    // Parse response
    // 응답 파싱
    var healthResp HealthResponse
    if err := json.NewDecoder(resp.Body).Decode(&healthResp); err != nil {
        return nil, fmt.Errorf("failed to decode response: %w", err)
    }
    
    return &healthResp, nil
}

// StartHealthMonitoring starts periodic health monitoring
// StartHealthMonitoring은 주기적 시스템 상태 모니터링을 시작합니다
func (sm *SystemMonitor) StartHealthMonitoring(ctx context.Context, interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()
    
    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            if health, err := sm.CheckHealth(); err != nil {
                fmt.Printf("Health check error: %v\n", err)
            } else {
                fmt.Printf("Health check: %s at %s\n", health.Status, health.Timestamp.Format("2006-01-02 15:04:05"))
                
                if health.Status == "down" {
                    fmt.Println("🚨 System is down!")
                    // Send alert or notification here
                    // 여기서 알림 또는 알림 전송
                }
            }
        }
    }
}
```

## 🚀 완전한 예제

### **메인 애플리케이션**

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "time"
)

func main() {
    // Initialize client
    // 클라이언트 초기화
    client := NewFileWallBallClient("http://localhost:8000", "")
    defer client.Close()
    
    // Initialize services
    // 서비스 초기화
    uploader := NewFileUploader(client)
    downloader := NewFileDownloader(client)
    fileManager := NewFileManager(client)
    systemMonitor := NewSystemMonitor(client)
    
    // Check system health
    // 시스템 상태 확인
    health, err := systemMonitor.CheckHealth()
    if err != nil {
        log.Printf("Health check failed: %v", err)
        return
    }
    fmt.Printf("System health: %s\n", health.Status)
    
    // Upload file
    // 파일 업로드
    uploadResult, err := uploader.UploadFile("./example.txt")
    if err != nil {
        log.Printf("Upload failed: %v", err)
        return
    }
    fmt.Printf("File uploaded: %s\n", uploadResult.FileID)
    
    // Get file list
    // 파일 목록 조회
    fileList, err := fileManager.GetFileList(1, 10, "uploaded_at", "desc")
    if err != nil {
        log.Printf("Failed to get file list: %v", err)
        return
    }
    fmt.Printf("Total files: %d\n", fileList.Pagination.Total)
    
    // Download file
    // 파일 다운로드
    downloadResult, err := downloader.DownloadFile(
        uploadResult.FileID,
        "./downloaded_example.txt",
    )
    if err != nil {
        log.Printf("Download failed: %v", err)
        return
    }
    fmt.Printf("File downloaded: %s\n", downloadResult.Filename)
    
    // Start health monitoring in background
    // 백그라운드에서 상태 모니터링 시작
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
    defer cancel()
    
    go systemMonitor.StartHealthMonitoring(ctx, 1*time.Minute)
    
    // Wait for monitoring to complete
    // 모니터링 완료까지 대기
    <-ctx.Done()
    
    fmt.Println("Example completed")
}
```

## 📝 사용 팁

### **성능 최적화**
1. **연결 풀링**: `http.Transport` 설정으로 연결 재사용
2. **스트리밍**: 대용량 파일은 스트리밍 방식 사용
3. **고루틴**: 여러 파일 업로드/다운로드 시 고루틴 활용
4. **버퍼 크기**: 적절한 버퍼 크기로 메모리 사용량 최적화

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
