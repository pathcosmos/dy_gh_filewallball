-- =====================================================
-- FileWallBall 성능 테스트 스크립트
-- 인덱스 성능 및 쿼리 최적화 테스트
-- =====================================================

USE filewallball_db;

-- =====================================================
-- 1. 테스트 데이터 생성 (시뮬레이션)
-- =====================================================

-- 파일 카테고리 확인
SELECT '=== 파일 카테고리 ===' as info;
SELECT * FROM file_categories;

-- 파일 확장자 확인
SELECT '=== 파일 확장자 ===' as info;
SELECT extension, mime_type, is_allowed FROM file_extensions LIMIT 10;

-- 시스템 설정 확인
SELECT '=== 시스템 설정 ===' as info;
SELECT setting_key, setting_value, setting_type FROM system_settings;

-- =====================================================
-- 2. 인덱스 사용 통계 확인
-- =====================================================

SELECT '=== 인덱스 통계 ===' as info;
SELECT
    TABLE_NAME,
    INDEX_NAME,
    CARDINALITY,
    INDEX_TYPE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'filewallball_db'
AND TABLE_NAME = 'files'
ORDER BY INDEX_NAME;

-- =====================================================
-- 3. 성능 테스트 쿼리들
-- =====================================================

-- 테스트 1: 파일 검색 성능 (복합 인덱스 활용)
SELECT '=== 테스트 1: 파일 검색 성능 ===' as info;
EXPLAIN SELECT * FROM files
WHERE is_deleted = FALSE
AND is_public = TRUE
AND file_extension = 'pdf'
ORDER BY created_at DESC
LIMIT 10;

-- 테스트 2: 카테고리별 파일 조회
SELECT '=== 테스트 2: 카테고리별 파일 조회 ===' as info;
EXPLAIN SELECT f.*, c.name as category_name
FROM files f
LEFT JOIN file_categories c ON f.file_category_id = c.id
WHERE f.is_deleted = FALSE
AND f.is_public = TRUE
AND f.file_category_id = 1
ORDER BY f.created_at DESC;

-- 테스트 3: 파일 크기 기반 정렬
SELECT '=== 테스트 3: 파일 크기 기반 정렬 ===' as info;
EXPLAIN SELECT * FROM files
WHERE is_deleted = FALSE
ORDER BY file_size DESC, created_at DESC
LIMIT 10;

-- 테스트 4: 태그 기반 검색 (시뮬레이션)
SELECT '=== 테스트 4: 태그 기반 검색 ===' as info;
EXPLAIN SELECT f.*, t.name as tag_name
FROM files f
JOIN file_tag_relations ftr ON f.id = ftr.file_id
JOIN file_tags t ON ftr.tag_id = t.id
WHERE f.is_deleted = FALSE
AND t.name = 'important'
ORDER BY f.created_at DESC;

-- 테스트 5: 통계 뷰 성능
SELECT '=== 테스트 5: 통계 뷰 성능 ===' as info;
EXPLAIN SELECT * FROM file_statistics
WHERE view_count > 0
ORDER BY download_count DESC
LIMIT 10;

-- =====================================================
-- 4. 인덱스 사용률 확인
-- =====================================================

SELECT '=== 인덱스 사용률 ===' as info;
SELECT
    TABLE_SCHEMA,
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
-- 5. 테이블 크기 및 통계
-- =====================================================

SELECT '=== 테이블 통계 ===' as info;
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    DATA_LENGTH,
    INDEX_LENGTH,
    (DATA_LENGTH + INDEX_LENGTH) as TOTAL_SIZE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'filewallball_db'
ORDER BY TABLE_NAME;

-- =====================================================
-- 6. 성능 최적화 완료 메시지
-- =====================================================

SELECT 'FileWallBall Performance Test completed successfully!' as status;
