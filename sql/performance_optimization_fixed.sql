-- =====================================================
-- FileWallBall 성능 최적화 스크립트 (수정된 버전)
-- MariaDB 인덱스 최적화 및 성능 튜닝
-- =====================================================

USE filewallball_db;

-- =====================================================
-- 1. 추가 인덱스 생성 (성능 최적화)
-- =====================================================

-- 파일 검색을 위한 복합 인덱스
CREATE INDEX idx_files_search ON files (is_deleted, is_public, file_extension, created_at);

-- 파일 크기 기반 정렬을 위한 인덱스
CREATE INDEX idx_files_size ON files (file_size DESC, created_at DESC);

-- 카테고리별 파일 조회 최적화
CREATE INDEX idx_files_category_public ON files (file_category_id, is_public, created_at DESC);

-- 파일 해시 기반 중복 검사 최적화
CREATE INDEX idx_files_hash ON files (file_hash, is_deleted);

-- =====================================================
-- 2. 조회/다운로드 기록 테이블 인덱스 최적화
-- =====================================================

-- 조회 기록 성능 최적화
CREATE INDEX idx_views_performance ON file_views (file_id, created_at DESC);
CREATE INDEX idx_views_ip_time ON file_views (viewer_ip, created_at DESC);
CREATE INDEX idx_views_type_time ON file_views (view_type, created_at DESC);

-- 다운로드 기록 성능 최적화
CREATE INDEX idx_downloads_performance ON file_downloads (file_id, created_at DESC);
CREATE INDEX idx_downloads_method_time ON file_downloads (download_method, created_at DESC);
CREATE INDEX idx_downloads_ip_time ON file_downloads (downloader_ip, created_at DESC);

-- 업로드 기록 성능 최적화
CREATE INDEX idx_uploads_performance ON file_uploads (file_id, created_at DESC);
CREATE INDEX idx_uploads_status_time ON file_uploads (upload_status, created_at DESC);
CREATE INDEX idx_uploads_method_time ON file_uploads (upload_method, created_at DESC);

-- =====================================================
-- 3. 태그 시스템 인덱스 최적화
-- =====================================================

-- 태그 사용 빈도 기반 정렬
CREATE INDEX idx_tags_usage ON file_tags (usage_count DESC, name);

-- 태그 관계 조회 최적화
CREATE INDEX idx_tag_relations_performance ON file_tag_relations (file_id, tag_id);
CREATE INDEX idx_tag_relations_reverse ON file_tag_relations (tag_id, file_id);

-- =====================================================
-- 4. 확장자 및 카테고리 인덱스 최적화
-- =====================================================

-- 확장자 검색 최적화
CREATE INDEX idx_extensions_search ON file_extensions (is_allowed, extension);
CREATE INDEX idx_extensions_type ON file_extensions (is_text_file, is_image_file, is_video_file, is_audio_file, is_document_file, is_archive_file);

-- 카테고리 활성화 상태 기반 조회
CREATE INDEX idx_categories_active ON file_categories (is_active, name);

-- =====================================================
-- 5. 시스템 설정 인덱스 최적화
-- =====================================================

-- 설정 키 기반 빠른 조회
CREATE INDEX idx_settings_public ON system_settings (is_public, setting_key);

-- =====================================================
-- 6. 통계 뷰 성능 최적화
-- =====================================================

-- 통계 뷰를 위한 추가 인덱스
CREATE INDEX idx_files_stats ON files (is_deleted, created_at, file_size);
CREATE INDEX idx_views_stats ON file_views (file_id, created_at);
CREATE INDEX idx_downloads_stats ON file_downloads (file_id, created_at);

-- =====================================================
-- 7. 성능 모니터링 설정 (수정 가능한 변수만)
-- =====================================================

-- 느린 쿼리 로그 활성화
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 2; -- 2초 이상 쿼리 로깅
SET GLOBAL log_queries_not_using_indexes = 1;

-- =====================================================
-- 8. 인덱스 사용 통계 확인
-- =====================================================

-- 인덱스 사용 통계 확인
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    CARDINALITY,
    SUB_PART,
    PACKED,
    NULLABLE,
    INDEX_TYPE
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'filewallball_db' 
ORDER BY TABLE_NAME, INDEX_NAME;

-- =====================================================
-- 9. 성능 최적화 완료 메시지
-- =====================================================

SELECT 'FileWallBall Performance Optimization completed successfully!' as status; 