-- =====================================================
-- FileWallBall Database Schema
-- MariaDB 기반 파일 관리 시스템
-- =====================================================

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS filewallball_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE filewallball_db;

-- =====================================================
-- 1. 파일 정보 테이블 (핵심 테이블)
-- =====================================================
CREATE TABLE files (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '파일 고유 ID (내부)',
    file_uuid VARCHAR(36) NOT NULL UNIQUE COMMENT '파일 UUID (외부 노출용)',
    original_filename VARCHAR(255) NOT NULL COMMENT '원본 파일명',
    stored_filename VARCHAR(255) NOT NULL COMMENT '저장된 파일명',
    file_extension VARCHAR(20) NOT NULL COMMENT '파일 확장자',
    mime_type VARCHAR(100) NOT NULL COMMENT 'MIME 타입',
    file_size BIGINT UNSIGNED NOT NULL COMMENT '파일 크기 (bytes)',
    file_hash VARCHAR(64) COMMENT '파일 MD5 해시',
    storage_path VARCHAR(500) NOT NULL COMMENT '파일 저장 경로',
    file_category_id TINYINT UNSIGNED COMMENT '파일 카테고리 ID',
    is_public BOOLEAN DEFAULT TRUE COMMENT '공개 여부',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '삭제 여부',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정 시간',

    INDEX idx_file_uuid (file_uuid),
    INDEX idx_original_filename (original_filename),
    INDEX idx_file_extension (file_extension),
    INDEX idx_file_category (file_category_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_deleted (is_deleted),
    INDEX idx_is_public (is_public)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일 메타데이터 정보';

-- =====================================================
-- 2. 파일 카테고리 테이블
-- =====================================================
CREATE TABLE file_categories (
    id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '카테고리 ID',
    name VARCHAR(50) NOT NULL UNIQUE COMMENT '카테고리명',
    description TEXT COMMENT '카테고리 설명',
    icon VARCHAR(50) COMMENT '카테고리 아이콘',
    color VARCHAR(7) COMMENT '카테고리 색상 (HEX)',
    is_active BOOLEAN DEFAULT TRUE COMMENT '활성화 여부',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간',

    INDEX idx_name (name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일 카테고리 정보';

-- 카테고리 외래키 제약조건
ALTER TABLE files
ADD CONSTRAINT fk_files_category
FOREIGN KEY (file_category_id) REFERENCES file_categories(id)
ON DELETE SET NULL;

-- =====================================================
-- 3. 파일 확장자 매핑 테이블
-- =====================================================
CREATE TABLE file_extensions (
    id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '확장자 ID',
    extension VARCHAR(20) NOT NULL UNIQUE COMMENT '파일 확장자',
    mime_type VARCHAR(100) NOT NULL COMMENT '기본 MIME 타입',
    description VARCHAR(200) COMMENT '확장자 설명',
    is_text_file BOOLEAN DEFAULT FALSE COMMENT '텍스트 파일 여부',
    is_image_file BOOLEAN DEFAULT FALSE COMMENT '이미지 파일 여부',
    is_video_file BOOLEAN DEFAULT FALSE COMMENT '비디오 파일 여부',
    is_audio_file BOOLEAN DEFAULT FALSE COMMENT '오디오 파일 여부',
    is_document_file BOOLEAN DEFAULT FALSE COMMENT '문서 파일 여부',
    is_archive_file BOOLEAN DEFAULT FALSE COMMENT '압축 파일 여부',
    max_file_size BIGINT UNSIGNED DEFAULT 104857600 COMMENT '최대 파일 크기 (100MB)',
    is_allowed BOOLEAN DEFAULT TRUE COMMENT '허용된 확장자 여부',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간',

    INDEX idx_extension (extension),
    INDEX idx_mime_type (mime_type),
    INDEX idx_is_allowed (is_allowed),
    INDEX idx_is_text_file (is_text_file)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일 확장자 정보 및 설정';

-- =====================================================
-- 4. 파일 조회 기록 테이블
-- =====================================================
CREATE TABLE file_views (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '조회 기록 ID',
    file_id BIGINT UNSIGNED NOT NULL COMMENT '파일 ID',
    viewer_ip VARCHAR(45) COMMENT '조회자 IP 주소',
    user_agent TEXT COMMENT '사용자 에이전트',
    referer VARCHAR(500) COMMENT '리퍼러 URL',
    view_type ENUM('info', 'preview', 'download') NOT NULL COMMENT '조회 타입',
    session_id VARCHAR(100) COMMENT '세션 ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '조회 시간',

    INDEX idx_file_id (file_id),
    INDEX idx_viewer_ip (viewer_ip),
    INDEX idx_view_type (view_type),
    INDEX idx_created_at (created_at),
    INDEX idx_session_id (session_id),

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일 조회 기록';

-- =====================================================
-- 5. 파일 다운로드 기록 테이블
-- =====================================================
CREATE TABLE file_downloads (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '다운로드 기록 ID',
    file_id BIGINT UNSIGNED NOT NULL COMMENT '파일 ID',
    downloader_ip VARCHAR(45) COMMENT '다운로더 IP 주소',
    user_agent TEXT COMMENT '사용자 에이전트',
    download_method ENUM('direct', 'api', 'web') NOT NULL COMMENT '다운로드 방법',
    bytes_downloaded BIGINT UNSIGNED COMMENT '다운로드된 바이트 수',
    download_duration_ms INT UNSIGNED COMMENT '다운로드 소요 시간 (ms)',
    session_id VARCHAR(100) COMMENT '세션 ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '다운로드 시간',

    INDEX idx_file_id (file_id),
    INDEX idx_downloader_ip (downloader_ip),
    INDEX idx_download_method (download_method),
    INDEX idx_created_at (created_at),
    INDEX idx_session_id (session_id),

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일 다운로드 기록';

-- =====================================================
-- 6. 파일 업로드 기록 테이블
-- =====================================================
CREATE TABLE file_uploads (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '업로드 기록 ID',
    file_id BIGINT UNSIGNED NOT NULL COMMENT '파일 ID',
    uploader_ip VARCHAR(45) COMMENT '업로더 IP 주소',
    user_agent TEXT COMMENT '사용자 에이전트',
    upload_method ENUM('web', 'api', 'batch') NOT NULL COMMENT '업로드 방법',
    upload_duration_ms INT UNSIGNED COMMENT '업로드 소요 시간 (ms)',
    upload_status ENUM('success', 'failed', 'partial') NOT NULL COMMENT '업로드 상태',
    error_message TEXT COMMENT '에러 메시지',
    session_id VARCHAR(100) COMMENT '세션 ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '업로드 시간',

    INDEX idx_file_id (file_id),
    INDEX idx_uploader_ip (uploader_ip),
    INDEX idx_upload_method (upload_method),
    INDEX idx_upload_status (upload_status),
    INDEX idx_created_at (created_at),
    INDEX idx_session_id (session_id),

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일 업로드 기록';

-- =====================================================
-- 7. 파일 태그 테이블
-- =====================================================
CREATE TABLE file_tags (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '태그 ID',
    name VARCHAR(50) NOT NULL UNIQUE COMMENT '태그명',
    description TEXT COMMENT '태그 설명',
    color VARCHAR(7) COMMENT '태그 색상 (HEX)',
    usage_count INT UNSIGNED DEFAULT 0 COMMENT '사용 횟수',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간',

    INDEX idx_name (name),
    INDEX idx_usage_count (usage_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일 태그 정보';

-- =====================================================
-- 8. 파일-태그 연결 테이블 (다대다 관계)
-- =====================================================
CREATE TABLE file_tag_relations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '관계 ID',
    file_id BIGINT UNSIGNED NOT NULL COMMENT '파일 ID',
    tag_id INT UNSIGNED NOT NULL COMMENT '태그 ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '연결 시간',

    UNIQUE KEY unique_file_tag (file_id, tag_id),
    INDEX idx_file_id (file_id),
    INDEX idx_tag_id (tag_id),

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES file_tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='파일-태그 다대다 관계';

-- =====================================================
-- 9. 시스템 설정 테이블
-- =====================================================
CREATE TABLE system_settings (
    id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '설정 ID',
    setting_key VARCHAR(100) NOT NULL UNIQUE COMMENT '설정 키',
    setting_value TEXT COMMENT '설정 값',
    setting_type ENUM('string', 'integer', 'boolean', 'json') NOT NULL COMMENT '설정 타입',
    description TEXT COMMENT '설정 설명',
    is_public BOOLEAN DEFAULT FALSE COMMENT '공개 설정 여부',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정 시간',

    INDEX idx_setting_key (setting_key),
    INDEX idx_is_public (is_public)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='시스템 설정 정보';

-- =====================================================
-- 10. 통계 뷰 (성능 최적화용)
-- =====================================================
CREATE VIEW file_statistics AS
SELECT
    f.id,
    f.file_uuid,
    f.original_filename,
    f.file_extension,
    f.file_size,
    f.created_at,
    COUNT(DISTINCT fv.id) as view_count,
    COUNT(DISTINCT fd.id) as download_count,
    MAX(fv.created_at) as last_viewed_at,
    MAX(fd.created_at) as last_downloaded_at
FROM files f
LEFT JOIN file_views fv ON f.id = fv.file_id
LEFT JOIN file_downloads fd ON f.id = fd.file_id
WHERE f.is_deleted = FALSE
GROUP BY f.id;

-- =====================================================
-- 기본 데이터 삽입
-- =====================================================

-- 파일 카테고리 기본 데이터
INSERT INTO file_categories (name, description, icon, color) VALUES
('문서', '문서 파일 (PDF, DOC, TXT 등)', 'document', '#4A90E2'),
('이미지', '이미지 파일 (JPG, PNG, GIF 등)', 'image', '#7ED321'),
('비디오', '비디오 파일 (MP4, AVI, MOV 등)', 'video', '#F5A623'),
('오디오', '오디오 파일 (MP3, WAV, FLAC 등)', 'audio', '#BD10E0'),
('압축파일', '압축 파일 (ZIP, RAR, 7Z 등)', 'archive', '#FF6B6B'),
('기타', '기타 파일 형식', 'file', '#9B9B9B');

-- 파일 확장자 기본 데이터
INSERT INTO file_extensions (extension, mime_type, description, is_text_file, is_image_file, is_video_file, is_audio_file, is_document_file, is_archive_file) VALUES
-- 텍스트 파일
('.txt', 'text/plain', '텍스트 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.md', 'text/markdown', '마크다운 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.json', 'application/json', 'JSON 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.xml', 'application/xml', 'XML 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.csv', 'text/csv', 'CSV 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.py', 'text/x-python', 'Python 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.js', 'application/javascript', 'JavaScript 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.html', 'text/html', 'HTML 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),
('.css', 'text/css', 'CSS 파일', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE),

-- 이미지 파일
('.jpg', 'image/jpeg', 'JPEG 이미지', FALSE, TRUE, FALSE, FALSE, FALSE, FALSE),
('.jpeg', 'image/jpeg', 'JPEG 이미지', FALSE, TRUE, FALSE, FALSE, FALSE, FALSE),
('.png', 'image/png', 'PNG 이미지', FALSE, TRUE, FALSE, FALSE, FALSE, FALSE),
('.gif', 'image/gif', 'GIF 이미지', FALSE, TRUE, FALSE, FALSE, FALSE, FALSE),
('.bmp', 'image/bmp', 'BMP 이미지', FALSE, TRUE, FALSE, FALSE, FALSE, FALSE),
('.svg', 'image/svg+xml', 'SVG 이미지', FALSE, TRUE, FALSE, FALSE, FALSE, FALSE),
('.webp', 'image/webp', 'WebP 이미지', FALSE, TRUE, FALSE, FALSE, FALSE, FALSE),

-- 비디오 파일
('.mp4', 'video/mp4', 'MP4 비디오', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE),
('.avi', 'video/x-msvideo', 'AVI 비디오', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE),
('.mov', 'video/quicktime', 'MOV 비디오', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE),
('.wmv', 'video/x-ms-wmv', 'WMV 비디오', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE),
('.flv', 'video/x-flv', 'FLV 비디오', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE),
('.webm', 'video/webm', 'WebM 비디오', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE),

-- 오디오 파일
('.mp3', 'audio/mpeg', 'MP3 오디오', FALSE, FALSE, FALSE, TRUE, FALSE, FALSE),
('.wav', 'audio/wav', 'WAV 오디오', FALSE, FALSE, FALSE, TRUE, FALSE, FALSE),
('.flac', 'audio/flac', 'FLAC 오디오', FALSE, FALSE, FALSE, TRUE, FALSE, FALSE),
('.ogg', 'audio/ogg', 'OGG 오디오', FALSE, FALSE, FALSE, TRUE, FALSE, FALSE),
('.aac', 'audio/aac', 'AAC 오디오', FALSE, FALSE, FALSE, TRUE, FALSE, FALSE),

-- 문서 파일
('.pdf', 'application/pdf', 'PDF 문서', FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),
('.doc', 'application/msword', 'Word 문서', FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),
('.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Word 문서', FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),
('.xls', 'application/vnd.ms-excel', 'Excel 문서', FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),
('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Excel 문서', FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),
('.ppt', 'application/vnd.ms-powerpoint', 'PowerPoint 문서', FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),
('.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'PowerPoint 문서', FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),

-- 압축 파일
('.zip', 'application/zip', 'ZIP 압축파일', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE),
('.rar', 'application/vnd.rar', 'RAR 압축파일', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE),
('.7z', 'application/x-7z-compressed', '7Z 압축파일', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE),
('.tar', 'application/x-tar', 'TAR 압축파일', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE),
('.gz', 'application/gzip', 'GZIP 압축파일', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE);

-- 시스템 설정 기본 데이터
INSERT INTO system_settings (setting_key, setting_value, setting_type, description, is_public) VALUES
('max_file_size', '104857600', 'integer', '최대 파일 업로드 크기 (bytes)', TRUE),
('allowed_extensions', '["jpg","png","pdf","txt","zip"]', 'json', '허용된 파일 확장자 목록', TRUE),
('file_retention_days', '30', 'integer', '파일 보관 기간 (일)', TRUE),
('enable_public_access', 'true', 'boolean', '공개 접근 허용 여부', TRUE),
('redis_cache_ttl', '86400', 'integer', 'Redis 캐시 TTL (초)', FALSE),
('upload_path', '/app/uploads', 'string', '파일 업로드 경로', FALSE),
('database_backup_enabled', 'true', 'boolean', '데이터베이스 백업 활성화', FALSE);

-- =====================================================
-- 인덱스 최적화
-- =====================================================

-- 복합 인덱스 생성 (성능 최적화)
CREATE INDEX idx_files_composite ON files (is_deleted, is_public, created_at);
CREATE INDEX idx_views_composite ON file_views (file_id, created_at);
CREATE INDEX idx_downloads_composite ON file_downloads (file_id, created_at);
CREATE INDEX idx_uploads_composite ON file_uploads (file_id, upload_status, created_at);

-- =====================================================
-- 트리거 생성 (자동 업데이트)
-- =====================================================

DELIMITER //

-- 파일 태그 사용 횟수 자동 업데이트 트리거
CREATE TRIGGER update_tag_usage_count_insert
AFTER INSERT ON file_tag_relations
FOR EACH ROW
BEGIN
    UPDATE file_tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
END//

CREATE TRIGGER update_tag_usage_count_delete
AFTER DELETE ON file_tag_relations
FOR EACH ROW
BEGIN
    UPDATE file_tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
END//

DELIMITER ;

-- =====================================================
-- 권한 설정
-- =====================================================

-- 애플리케이션 사용자 생성
CREATE USER IF NOT EXISTS 'filewallball_user'@'%' IDENTIFIED BY 'secure_password_here';
GRANT SELECT, INSERT, UPDATE, DELETE ON filewallball_db.* TO 'filewallball_user'@'%';
FLUSH PRIVILEGES;

-- =====================================================
-- 완료 메시지
-- =====================================================
SELECT 'FileWallBall Database Schema created successfully!' as status;
