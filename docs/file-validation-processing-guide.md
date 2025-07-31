# FileWallBall 파일 검증 및 처리 가이드

## 📋 개요

FileWallBall의 파일 검증 및 처리 시스템은 업로드된 파일의 안전성, 적합성, 품질을 보장하는 다층 검증 프로세스를 제공합니다. 이 문서는 파일 검증 단계, 처리 방법, 그리고 관련 설정을 상세히 설명합니다.

## 🔍 파일 검증 시스템

### File Validation Service (`file_validation_service.py`)

파일 검증 서비스는 업로드된 파일을 여러 단계에 걸쳐 검증하여 시스템 보안과 데이터 무결성을 보장합니다.

#### 검증 프로세스 플로우

```
파일 업로드
    ↓
1. 기본 검증 (크기, 확장자)
    ↓
2. MIME 타입 검증
    ↓
3. 파일 시그니처 검증
    ↓
4. 콘텐츠 검증
    ↓
5. 바이러스 스캔 (선택적)
    ↓
6. 중복 파일 검사
    ↓
검증 완료
```

### 1. 기본 검증

#### 파일 크기 검증

```python
# 파일 크기 제한 설정
FILE_SIZE_LIMITS = {
    "min_size": 1,  # 1바이트
    "max_size": 104857600,  # 100MB
    "image_max_size": 10485760,  # 10MB (이미지)
    "document_max_size": 52428800,  # 50MB (문서)
    "video_max_size": 104857600  # 100MB (비디오)
}

def validate_file_size(file_size: int, file_type: str) -> bool:
    """파일 크기 검증"""
    if file_size < FILE_SIZE_LIMITS["min_size"]:
        raise ValidationError("File size too small")

    max_size = FILE_SIZE_LIMITS.get(f"{file_type}_max_size",
                                   FILE_SIZE_LIMITS["max_size"])

    if file_size > max_size:
        raise ValidationError(f"File size exceeds limit: {max_size}")

    return True
```

#### 파일 확장자 검증

```python
# 허용된 파일 확장자
ALLOWED_EXTENSIONS = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"],
    "spreadsheets": [".xls", ".xlsx", ".csv"],
    "presentations": [".ppt", ".pptx"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "videos": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"]
}

# 차단된 파일 확장자
BLOCKED_EXTENSIONS = [
    ".exe", ".bat", ".cmd", ".com", ".scr", ".pif",
    ".vbs", ".js", ".jar", ".msi", ".dmg", ".app"
]

def validate_file_extension(filename: str) -> bool:
    """파일 확장자 검증"""
    ext = Path(filename).suffix.lower()

    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(f"File extension not allowed: {ext}")

    # 허용된 확장자 중 하나인지 확인
    allowed_extensions = []
    for extensions in ALLOWED_EXTENSIONS.values():
        allowed_extensions.extend(extensions)

    if ext not in allowed_extensions:
        raise ValidationError(f"File extension not supported: {ext}")

    return True
```

### 2. MIME 타입 검증

#### MIME 타입 매핑

```python
# 파일 확장자별 MIME 타입 매핑
MIME_TYPE_MAPPING = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".xml": "text/xml",
    ".zip": "application/zip",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg"
}

# 허용된 MIME 타입
ALLOWED_MIME_TYPES = [
    # 이미지
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
    # 문서
    "application/pdf", "text/plain", "text/markdown", "text/html",
    "application/json", "text/xml", "application/xml",
    # 스프레드시트
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # 프레젠테이션
    "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # 아카이브
    "application/zip", "application/x-rar-compressed", "application/x-7z-compressed",
    # 비디오
    "video/mp4", "video/avi", "video/quicktime", "video/x-msvideo",
    # 오디오
    "audio/mpeg", "audio/wav", "audio/flac", "audio/aac"
]

# 차단된 MIME 타입
BLOCKED_MIME_TYPES = [
    "application/x-executable",
    "application/x-msdownload",
    "application/x-msi",
    "application/x-dosexec",
    "application/x-shockwave-flash"
]

def validate_mime_type(file_content: bytes, filename: str) -> str:
    """MIME 타입 검증"""
    import magic

    # 파일 시그니처로 MIME 타입 확인
    detected_mime = magic.from_buffer(file_content, mime=True)

    # 확장자 기반 예상 MIME 타입
    expected_mime = MIME_TYPE_MAPPING.get(Path(filename).suffix.lower())

    # 차단된 MIME 타입 확인
    if detected_mime in BLOCKED_MIME_TYPES:
        raise ValidationError(f"Blocked MIME type: {detected_mime}")

    # 허용된 MIME 타입 확인
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"Unsupported MIME type: {detected_mime}")

    # MIME 타입과 확장자 일치성 확인
    if expected_mime and detected_mime != expected_mime:
        # 경고 로그 (차단하지는 않음)
        logger.warning(f"MIME type mismatch: expected {expected_mime}, got {detected_mime}")

    return detected_mime
```

### 3. 파일 시그니처 검증

#### 매직 바이트 검증

```python
# 파일 시그니처 (매직 바이트)
FILE_SIGNATURES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],
    "application/pdf": [b"%PDF"],
    "application/zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "text/plain": [],  # 텍스트 파일은 시그니처 없음
    "application/json": []  # JSON 파일은 시그니처 없음
}

def validate_file_signature(file_content: bytes, mime_type: str) -> bool:
    """파일 시그니처 검증"""
    if mime_type not in FILE_SIGNATURES:
        return True  # 시그니처가 정의되지 않은 타입은 건너뜀

    signatures = FILE_SIGNATURES[mime_type]
    if not signatures:
        return True  # 시그니처가 없는 타입은 건너뜀

    for signature in signatures:
        if file_content.startswith(signature):
            return True

    raise ValidationError(f"Invalid file signature for {mime_type}")
```

### 4. 콘텐츠 검증

#### 이미지 파일 검증

```python
from PIL import Image
import io

def validate_image_content(file_content: bytes) -> dict:
    """이미지 파일 콘텐츠 검증"""
    try:
        image = Image.open(io.BytesIO(file_content))

        # 이미지 정보 추출
        width, height = image.size
        format_name = image.format
        mode = image.mode

        # 이미지 크기 제한
        if width > 8192 or height > 8192:
            raise ValidationError("Image dimensions too large")

        # 이미지 품질 검증
        if width < 10 or height < 10:
            raise ValidationError("Image dimensions too small")

        return {
            "width": width,
            "height": height,
            "format": format_name,
            "mode": mode,
            "size": len(file_content)
        }
    except Exception as e:
        raise ValidationError(f"Invalid image file: {str(e)}")
```

#### PDF 파일 검증

```python
import PyPDF2
import io

def validate_pdf_content(file_content: bytes) -> dict:
    """PDF 파일 콘텐츠 검증"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))

        # 페이지 수 확인
        num_pages = len(pdf_reader.pages)

        # PDF 크기 제한
        if num_pages > 1000:
            raise ValidationError("PDF too many pages")

        # 메타데이터 추출
        metadata = pdf_reader.metadata

        return {
            "num_pages": num_pages,
            "metadata": metadata,
            "size": len(file_content)
        }
    except Exception as e:
        raise ValidationError(f"Invalid PDF file: {str(e)}")
```

### 5. 바이러스 스캔 (선택적)

#### ClamAV 통합

```python
import clamd

def scan_for_viruses(file_content: bytes, filename: str) -> bool:
    """바이러스 스캔"""
    try:
        # ClamAV 데몬에 연결
        cd = clamd.ClamdUnixSocket()

        # 파일 스캔
        scan_result = cd.instream(io.BytesIO(file_content))

        for result in scan_result:
            if result[1] == 'FOUND':
                virus_name = result[2]
                raise ValidationError(f"Virus detected: {virus_name}")

        return True
    except Exception as e:
        logger.warning(f"Virus scan failed: {str(e)}")
        return True  # 스캔 실패 시 허용
```

### 6. 중복 파일 검사

#### 파일 해시 기반 중복 검사

```python
import hashlib

def calculate_file_hash(file_content: bytes) -> str:
    """파일 해시 계산"""
    return hashlib.sha256(file_content).hexdigest()

def check_duplicate_file(file_hash: str, db_session) -> Optional[str]:
    """중복 파일 검사"""
    # 데이터베이스에서 동일한 해시를 가진 파일 검색
    existing_file = db_session.query(FileInfo).filter(
        FileInfo.file_hash == file_hash
    ).first()

    if existing_file:
        return existing_file.file_id

    return None
```

## 🖼️ 썸네일 생성 시스템

### Thumbnail Service (`thumbnail_service.py`)

썸네일 서비스는 업로드된 이미지와 문서에 대한 미리보기 이미지를 자동으로 생성합니다.

#### 지원 형식

```python
THUMBNAIL_SUPPORTED_FORMATS = {
    "images": ["jpeg", "png", "gif", "webp", "bmp", "tiff"],
    "documents": ["pdf"],  # PDF 첫 페이지
    "videos": ["mp4", "avi", "mov"]  # 비디오 첫 프레임
}

THUMBNAIL_SIZES = {
    "small": (150, 150),
    "medium": (300, 300),
    "large": (600, 600),
    "preview": (800, 600)
}
```

#### 썸네일 생성 예시

```python
from PIL import Image, ImageOps
import fitz  # PyMuPDF for PDF

def generate_image_thumbnail(file_content: bytes, size: tuple = (300, 300)) -> bytes:
    """이미지 썸네일 생성"""
    image = Image.open(io.BytesIO(file_content))

    # EXIF 정보 제거 (보안상)
    image = ImageOps.exif_transpose(image)

    # 썸네일 생성 (비율 유지)
    image.thumbnail(size, Image.Resampling.LANCZOS)

    # JPEG로 변환
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=85, optimize=True)

    return output.getvalue()

def generate_pdf_thumbnail(file_content: bytes, size: tuple = (300, 300)) -> bytes:
    """PDF 썸네일 생성"""
    pdf_document = fitz.open(stream=file_content, filetype="pdf")

    # 첫 페이지 렌더링
    page = pdf_document[0]
    mat = fitz.Matrix(2, 2)  # 2배 확대
    pix = page.get_pixmap(matrix=mat)

    # PIL Image로 변환
    img_data = pix.tobytes("ppm")
    image = Image.open(io.BytesIO(img_data))

    # 썸네일 생성
    image.thumbnail(size, Image.Resampling.LANCZOS)

    # JPEG로 변환
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=85, optimize=True)

    return output.getvalue()
```

## 📊 메타데이터 추출

### Metadata Service (`metadata_service.py`)

메타데이터 서비스는 업로드된 파일에서 자동으로 메타데이터를 추출하고 저장합니다.

#### 메타데이터 추출 예시

```python
import exifread
from PIL import Image
import PyPDF2

def extract_image_metadata(file_content: bytes) -> dict:
    """이미지 메타데이터 추출"""
    metadata = {}

    try:
        # EXIF 데이터 추출
        tags = exifread.process_file(io.BytesIO(file_content))

        if tags:
            metadata["exif"] = {
                "camera_make": str(tags.get('Image Make', '')),
                "camera_model": str(tags.get('Image Model', '')),
                "date_taken": str(tags.get('EXIF DateTimeOriginal', '')),
                "gps_latitude": str(tags.get('GPS GPSLatitude', '')),
                "gps_longitude": str(tags.get('GPS GPSLongitude', '')),
                "orientation": str(tags.get('Image Orientation', ''))
            }

        # 기본 이미지 정보
        image = Image.open(io.BytesIO(file_content))
        metadata["basic"] = {
            "width": image.size[0],
            "height": image.size[1],
            "format": image.format,
            "mode": image.mode
        }

    except Exception as e:
        logger.warning(f"Failed to extract image metadata: {str(e)}")

    return metadata

def extract_pdf_metadata(file_content: bytes) -> dict:
    """PDF 메타데이터 추출"""
    metadata = {}

    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))

        # PDF 메타데이터
        if pdf_reader.metadata:
            metadata["pdf"] = {
                "title": pdf_reader.metadata.get('/Title', ''),
                "author": pdf_reader.metadata.get('/Author', ''),
                "subject": pdf_reader.metadata.get('/Subject', ''),
                "creator": pdf_reader.metadata.get('/Creator', ''),
                "producer": pdf_reader.metadata.get('/Producer', ''),
                "creation_date": str(pdf_reader.metadata.get('/CreationDate', '')),
                "modification_date": str(pdf_reader.metadata.get('/ModDate', ''))
            }

        # 기본 정보
        metadata["basic"] = {
            "num_pages": len(pdf_reader.pages),
            "encrypted": pdf_reader.is_encrypted
        }

    except Exception as e:
        logger.warning(f"Failed to extract PDF metadata: {str(e)}")

    return metadata
```

## 🔄 파일 처리 파이프라인

### 처리 단계

```python
class FileProcessingPipeline:
    """파일 처리 파이프라인"""

    def __init__(self):
        self.validation_service = FileValidationService()
        self.thumbnail_service = ThumbnailService()
        self.metadata_service = MetadataService()

    async def process_file(self, file_content: bytes, filename: str, user_id: int) -> dict:
        """파일 처리 메인 파이프라인"""

        # 1. 기본 검증
        file_size = len(file_content)
        self.validation_service.validate_file_size(file_size, filename)
        self.validation_service.validate_file_extension(filename)

        # 2. MIME 타입 검증
        mime_type = self.validation_service.validate_mime_type(file_content, filename)

        # 3. 파일 시그니처 검증
        self.validation_service.validate_file_signature(file_content, mime_type)

        # 4. 콘텐츠 검증
        content_info = self.validation_service.validate_content(file_content, mime_type)

        # 5. 바이러스 스캔 (선택적)
        if settings.ENABLE_VIRUS_SCAN:
            self.validation_service.scan_for_viruses(file_content, filename)

        # 6. 중복 파일 검사
        file_hash = calculate_file_hash(file_content)
        duplicate_file_id = check_duplicate_file(file_hash, db_session)

        # 7. 메타데이터 추출
        metadata = self.metadata_service.extract_metadata(file_content, mime_type)

        # 8. 썸네일 생성
        thumbnail_data = None
        if self.thumbnail_service.is_supported(mime_type):
            thumbnail_data = self.thumbnail_service.generate_thumbnail(
                file_content, size=(300, 300)
            )

        # 9. 파일 저장
        file_id = str(uuid.uuid4())
        file_path = self.save_file(file_content, file_id, filename)

        # 10. 데이터베이스에 정보 저장
        file_info = FileInfo(
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            file_path=file_path,
            metadata=metadata,
            user_id=user_id,
            is_duplicate=duplicate_file_id is not None,
            original_file_id=duplicate_file_id
        )

        db_session.add(file_info)
        db_session.commit()

        return {
            "file_id": file_id,
            "filename": filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "is_duplicate": duplicate_file_id is not None,
            "original_file_id": duplicate_file_id,
            "metadata": metadata,
            "has_thumbnail": thumbnail_data is not None
        }
```

## ⚙️ 설정 및 구성

### 검증 정책 설정

```python
# config/validation.py
VALIDATION_CONFIG = {
    "file_size_limits": {
        "min_size": 1,
        "max_size": 104857600,  # 100MB
        "image_max_size": 10485760,  # 10MB
        "document_max_size": 52428800,  # 50MB
        "video_max_size": 104857600  # 100MB
    },
    "allowed_extensions": {
        "images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "documents": [".pdf", ".doc", ".docx", ".txt", ".md"],
        "videos": [".mp4", ".avi", ".mov", ".wmv"],
        "audio": [".mp3", ".wav", ".flac", ".aac"]
    },
    "blocked_extensions": [
        ".exe", ".bat", ".cmd", ".com", ".scr", ".pif",
        ".vbs", ".js", ".jar", ".msi", ".dmg", ".app"
    ],
    "virus_scan": {
        "enabled": True,
        "engine": "clamav",
        "timeout": 30
    },
    "thumbnail": {
        "enabled": True,
        "sizes": {
            "small": (150, 150),
            "medium": (300, 300),
            "large": (600, 600)
        },
        "quality": 85,
        "format": "jpeg"
    },
    "metadata_extraction": {
        "enabled": True,
        "include_exif": True,
        "include_pdf_metadata": True
    }
}
```

### API 엔드포인트

```http
# 검증 정책 조회
GET /api/v1/validation/policy

Response:
{
  "file_size_limits": {
    "min_size": 1,
    "max_size": 104857600,
    "image_max_size": 10485760,
    "document_max_size": 52428800,
    "video_max_size": 104857600
  },
  "allowed_extensions": {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".md"],
    "videos": [".mp4", ".avi", ".mov", ".wmv"],
    "audio": [".mp3", ".wav", ".flac", ".aac"]
  },
  "blocked_extensions": [
    ".exe", ".bat", ".cmd", ".com", ".scr", ".pif"
  ],
  "virus_scan": {
    "enabled": true,
    "engine": "clamav",
    "timeout": 30
  },
  "thumbnail": {
    "enabled": true,
    "sizes": {
      "small": [150, 150],
      "medium": [300, 300],
      "large": [600, 600]
    }
  }
}

# 파일 검증 테스트
POST /api/v1/validation/test
Content-Type: multipart/form-data

{
  "file": "test_file.jpg"
}

Response:
{
  "valid": true,
  "validation_results": {
    "size_check": "passed",
    "extension_check": "passed",
    "mime_type_check": "passed",
    "signature_check": "passed",
    "content_check": "passed",
    "virus_scan": "passed"
  },
  "metadata": {
    "width": 1920,
    "height": 1080,
    "format": "JPEG"
  }
}
```

## 🧪 테스트 및 검증

### 검증 테스트 스크립트

```python
# tests/test_file_validation.py
import pytest
from app.services.file_validation_service import FileValidationService

class TestFileValidation:

    def setup_method(self):
        self.validation_service = FileValidationService()

    def test_valid_image_upload(self):
        """유효한 이미지 업로드 테스트"""
        # 테스트 이미지 생성
        from PIL import Image
        import io

        image = Image.new('RGB', (100, 100), color='red')
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)

        # 검증 실행
        result = self.validation_service.validate_file(
            image_bytes.getvalue(), "test.jpg"
        )

        assert result["valid"] == True
        assert result["mime_type"] == "image/jpeg"

    def test_invalid_file_extension(self):
        """잘못된 파일 확장자 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            self.validation_service.validate_file(
                b"fake executable content", "test.exe"
            )

        assert "File extension not allowed" in str(exc_info.value)

    def test_file_size_limit(self):
        """파일 크기 제한 테스트"""
        # 100MB보다 큰 파일 생성
        large_file = b"x" * (104857600 + 1)

        with pytest.raises(ValidationError) as exc_info:
            self.validation_service.validate_file(
                large_file, "large_file.txt"
            )

        assert "File size exceeds limit" in str(exc_info.value)

    def test_mime_type_mismatch(self):
        """MIME 타입 불일치 테스트"""
        # JPEG 확장자지만 실제로는 텍스트 파일
        text_content = b"This is a text file"

        with pytest.raises(ValidationError) as exc_info:
            self.validation_service.validate_file(
                text_content, "fake.jpg"
            )

        assert "Unsupported MIME type" in str(exc_info.value)
```

## 📊 성능 최적화

### 검증 성능 개선

```python
# 비동기 검증 처리
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncFileValidationService:
    """비동기 파일 검증 서비스"""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def validate_file_async(self, file_content: bytes, filename: str) -> dict:
        """비동기 파일 검증"""

        # 기본 검증 (동기)
        basic_validation = await asyncio.get_event_loop().run_in_executor(
            self.executor, self._basic_validation, file_content, filename
        )

        # MIME 타입 검증 (동기)
        mime_validation = await asyncio.get_event_loop().run_in_executor(
            self.executor, self._mime_validation, file_content, filename
        )

        # 콘텐츠 검증 (동기)
        content_validation = await asyncio.get_event_loop().run_in_executor(
            self.executor, self._content_validation, file_content, mime_validation["mime_type"]
        )

        # 바이러스 스캔 (비동기, 선택적)
        virus_scan = None
        if settings.ENABLE_VIRUS_SCAN:
            virus_scan = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._virus_scan, file_content, filename
            )

        return {
            "valid": True,
            "basic_validation": basic_validation,
            "mime_validation": mime_validation,
            "content_validation": content_validation,
            "virus_scan": virus_scan
        }
```

## 🔧 모니터링 및 로깅

### 검증 메트릭

```python
# Prometheus 메트릭
validation_counter = Counter(
    'file_validations_total',
    'Total number of file validations',
    ['validation_type', 'status']
)

validation_duration = Histogram(
    'file_validation_duration_seconds',
    'File validation duration',
    ['validation_type']
)

file_size_distribution = Histogram(
    'file_size_bytes',
    'File size distribution',
    ['file_type']
)

# 검증 로깅
import logging

logger = logging.getLogger(__name__)

def log_validation_event(file_id: str, validation_type: str, status: str, details: dict):
    """검증 이벤트 로깅"""
    logger.info(
        f"File validation: {file_id}, type: {validation_type}, status: {status}",
        extra={
            "file_id": file_id,
            "validation_type": validation_type,
            "status": status,
            "details": details
        }
    )

    # 메트릭 업데이트
    validation_counter.labels(
        validation_type=validation_type,
        status=status
    ).inc()
```

## 📋 검증 체크리스트

### 배포 전 검증 설정 확인

- [ ] 파일 크기 제한이 적절히 설정됨
- [ ] 허용된 파일 확장자가 업데이트됨
- [ ] 차단된 파일 확장자가 설정됨
- [ ] MIME 타입 검증이 활성화됨
- [ ] 파일 시그니처 검증이 구현됨
- [ ] 콘텐츠 검증이 구현됨
- [ ] 바이러스 스캔이 구성됨 (선택적)
- [ ] 썸네일 생성이 설정됨
- [ ] 메타데이터 추출이 활성화됨
- [ ] 검증 테스트가 통과됨

### 정기 검증 정책 점검

- [ ] 새로운 파일 형식 지원 검토
- [ ] 보안 위협 파일 형식 업데이트
- [ ] 검증 성능 모니터링
- [ ] 오탐지/미탐지 분석
- [ ] 사용자 피드백 반영

---

이 문서는 FileWallBall의 파일 검증 및 처리 시스템을 상세히 설명합니다. 검증 관련 질문이나 개선 제안이 있으시면 개발팀에 문의해 주세요.
