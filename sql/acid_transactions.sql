-- =====================================================
-- FileWallBall ACID 트랜잭션 및 데이터 무결성 설정
-- MariaDB 트랜잭션 격리 수준 및 무결성 규칙 구현
-- =====================================================

USE filewallball_db;

-- =====================================================
-- 1. 트랜잭션 격리 수준 설정
-- =====================================================

-- 현재 격리 수준 확인
SELECT '=== 현재 트랜잭션 격리 수준 ===' as info;
SELECT @@tx_isolation as current_isolation;

-- 격리 수준을 REPEATABLE-READ로 설정 (기본값이지만 명시적 설정)
SET GLOBAL tx_isolation = 'REPEATABLE-READ';
SET SESSION tx_isolation = 'REPEATABLE-READ';

-- 설정 확인
SELECT '=== 설정된 트랜잭션 격리 수준 ===' as info;
SELECT @@tx_isolation as configured_isolation;

-- =====================================================
-- 2. 데이터 무결성 제약 조건 추가
-- =====================================================

-- 파일 크기 제약 조건 (이미 테이블에 있지만 확인)
SELECT '=== 파일 크기 제약 조건 확인 ===' as info;
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    EXTRA
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'filewallball_db' 
AND TABLE_NAME = 'files' 
AND COLUMN_NAME = 'file_size';

-- 파일 해시 길이 제약 조건 확인
SELECT '=== 파일 해시 제약 조건 확인 ===' as info;
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    IS_NULLABLE
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'filewallball_db' 
AND TABLE_NAME = 'files' 
AND COLUMN_NAME = 'file_hash';

-- =====================================================
-- 3. 트리거를 통한 데이터 무결성 보장
-- =====================================================

DELIMITER //

-- 파일 업로드 시 자동 해시 생성 트리거
CREATE TRIGGER IF NOT EXISTS before_file_insert
BEFORE INSERT ON files
FOR EACH ROW
BEGIN
    -- 파일 크기가 0보다 큰지 확인
    IF NEW.file_size <= 0 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '파일 크기는 0보다 커야 합니다.';
    END IF;
    
    -- 파일 해시가 NULL이 아닌지 확인
    IF NEW.file_hash IS NULL OR LENGTH(NEW.file_hash) != 32 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '파일 해시는 32자리 MD5 해시여야 합니다.';
    END IF;
    
    -- 파일 확장자가 허용된 확장자인지 확인
    IF NOT EXISTS (
        SELECT 1 FROM file_extensions 
        WHERE extension = NEW.file_extension 
        AND is_allowed = TRUE
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '허용되지 않은 파일 확장자입니다.';
    END IF;
END//

-- 파일 업데이트 시 무결성 검증 트리거
CREATE TRIGGER IF NOT EXISTS before_file_update
BEFORE UPDATE ON files
FOR EACH ROW
BEGIN
    -- 파일 크기가 0보다 큰지 확인
    IF NEW.file_size <= 0 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '파일 크기는 0보다 커야 합니다.';
    END IF;
    
    -- 삭제된 파일의 UUID는 변경 불가
    IF OLD.is_deleted = TRUE AND NEW.file_uuid != OLD.file_uuid THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '삭제된 파일의 UUID는 변경할 수 없습니다.';
    END IF;
END//

-- 파일 조회 시 자동 기록 트리거
CREATE TRIGGER IF NOT EXISTS after_file_view_insert
AFTER INSERT ON file_views
FOR EACH ROW
BEGIN
    -- 조회한 파일이 실제로 존재하는지 확인
    IF NOT EXISTS (
        SELECT 1 FROM files 
        WHERE id = NEW.file_id 
        AND is_deleted = FALSE
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '존재하지 않거나 삭제된 파일입니다.';
    END IF;
END//

-- 파일 다운로드 시 자동 기록 트리거
CREATE TRIGGER IF NOT EXISTS after_file_download_insert
AFTER INSERT ON file_downloads
FOR EACH ROW
BEGIN
    -- 다운로드한 파일이 실제로 존재하는지 확인
    IF NOT EXISTS (
        SELECT 1 FROM files 
        WHERE id = NEW.file_id 
        AND is_deleted = FALSE
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '존재하지 않거나 삭제된 파일입니다.';
    END IF;
    
    -- 다운로드된 바이트 수가 파일 크기를 초과하지 않는지 확인
    IF NEW.bytes_downloaded IS NOT NULL AND NEW.bytes_downloaded > (
        SELECT file_size FROM files WHERE id = NEW.file_id
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '다운로드된 바이트 수가 파일 크기를 초과할 수 없습니다.';
    END IF;
END//

-- 파일 태그 관계 생성 시 무결성 검증 트리거
CREATE TRIGGER IF NOT EXISTS before_file_tag_relation_insert
BEFORE INSERT ON file_tag_relations
FOR EACH ROW
BEGIN
    -- 파일이 존재하는지 확인
    IF NOT EXISTS (
        SELECT 1 FROM files 
        WHERE id = NEW.file_id 
        AND is_deleted = FALSE
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '존재하지 않거나 삭제된 파일입니다.';
    END IF;
    
    -- 태그가 존재하는지 확인
    IF NOT EXISTS (
        SELECT 1 FROM file_tags 
        WHERE id = NEW.tag_id
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '존재하지 않는 태그입니다.';
    END IF;
END//

DELIMITER ;

-- =====================================================
-- 4. 동시성 제어를 위한 락 설정
-- =====================================================

-- 파일 업로드 시 동시성 제어를 위한 프로시저
DELIMITER //

CREATE PROCEDURE IF NOT EXISTS upload_file_with_lock(
    IN p_file_uuid VARCHAR(36),
    IN p_original_filename VARCHAR(255),
    IN p_stored_filename VARCHAR(255),
    IN p_file_extension VARCHAR(20),
    IN p_mime_type VARCHAR(100),
    IN p_file_size BIGINT UNSIGNED,
    IN p_file_hash VARCHAR(64),
    IN p_storage_path VARCHAR(500),
    IN p_file_category_id TINYINT UNSIGNED,
    IN p_is_public BOOLEAN,
    IN p_uploader_ip VARCHAR(45),
    IN p_user_agent TEXT,
    IN p_upload_method ENUM('web', 'api', 'batch'),
    IN p_session_id VARCHAR(100)
)
BEGIN
    DECLARE v_file_id BIGINT UNSIGNED;
    DECLARE v_upload_id BIGINT UNSIGNED;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- 파일 중복 검사 (UUID 기반)
    SELECT id INTO v_file_id 
    FROM files 
    WHERE file_uuid = p_file_uuid 
    FOR UPDATE;
    
    IF v_file_id IS NOT NULL THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '동일한 UUID를 가진 파일이 이미 존재합니다.';
    END IF;
    
    -- 파일 정보 삽입
    INSERT INTO files (
        file_uuid, original_filename, stored_filename, 
        file_extension, mime_type, file_size, file_hash, 
        storage_path, file_category_id, is_public
    ) VALUES (
        p_file_uuid, p_original_filename, p_stored_filename,
        p_file_extension, p_mime_type, p_file_size, p_file_hash,
        p_storage_path, p_file_category_id, p_is_public
    );
    
    SET v_file_id = LAST_INSERT_ID();
    
    -- 업로드 기록 삽입
    INSERT INTO file_uploads (
        file_id, uploader_ip, user_agent, upload_method, 
        upload_status, session_id
    ) VALUES (
        v_file_id, p_uploader_ip, p_user_agent, p_upload_method,
        'success', p_session_id
    );
    
    SET v_upload_id = LAST_INSERT_ID();
    
    COMMIT;
    
    -- 결과 반환
    SELECT v_file_id as file_id, v_upload_id as upload_id;
END//

-- 파일 다운로드 시 동시성 제어를 위한 프로시저
CREATE PROCEDURE IF NOT EXISTS download_file_with_lock(
    IN p_file_uuid VARCHAR(36),
    IN p_downloader_ip VARCHAR(45),
    IN p_user_agent TEXT,
    IN p_download_method ENUM('direct', 'api', 'web'),
    IN p_session_id VARCHAR(100)
)
BEGIN
    DECLARE v_file_id BIGINT UNSIGNED;
    DECLARE v_file_size BIGINT UNSIGNED;
    DECLARE v_download_id BIGINT UNSIGNED;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- 파일 정보 조회 (락 적용)
    SELECT id, file_size INTO v_file_id, v_file_size
    FROM files 
    WHERE file_uuid = p_file_uuid 
    AND is_deleted = FALSE 
    AND is_public = TRUE
    FOR UPDATE;
    
    IF v_file_id IS NULL THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = '파일을 찾을 수 없거나 접근 권한이 없습니다.';
    END IF;
    
    -- 다운로드 기록 삽입
    INSERT INTO file_downloads (
        file_id, downloader_ip, user_agent, download_method,
        bytes_downloaded, session_id
    ) VALUES (
        v_file_id, p_downloader_ip, p_user_agent, p_download_method,
        v_file_size, p_session_id
    );
    
    SET v_download_id = LAST_INSERT_ID();
    
    COMMIT;
    
    -- 결과 반환
    SELECT v_file_id as file_id, v_download_id as download_id, v_file_size as file_size;
END//

DELIMITER ;

-- =====================================================
-- 5. 트랜잭션 격리 수준 테스트
-- =====================================================

-- 격리 수준 테스트를 위한 임시 테이블 생성
CREATE TEMPORARY TABLE IF NOT EXISTS isolation_test (
    id INT AUTO_INCREMENT PRIMARY KEY,
    value VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 6. 데이터 무결성 검증 함수
-- =====================================================

DELIMITER //

-- 파일 무결성 검증 함수
CREATE FUNCTION IF NOT EXISTS validate_file_integrity(p_file_id BIGINT UNSIGNED)
RETURNS BOOLEAN
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_exists BOOLEAN DEFAULT FALSE;
    
    SELECT EXISTS(
        SELECT 1 FROM files 
        WHERE id = p_file_id 
        AND is_deleted = FALSE
    ) INTO v_exists;
    
    RETURN v_exists;
END//

-- 태그 무결성 검증 함수
CREATE FUNCTION IF NOT EXISTS validate_tag_integrity(p_tag_id INT UNSIGNED)
RETURNS BOOLEAN
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_exists BOOLEAN DEFAULT FALSE;
    
    SELECT EXISTS(
        SELECT 1 FROM file_tags 
        WHERE id = p_tag_id
    ) INTO v_exists;
    
    RETURN v_exists;
END//

DELIMITER ;

-- =====================================================
-- 7. 설정 확인 및 완료 메시지
-- =====================================================

SELECT '=== ACID 트랜잭션 설정 완료 ===' as info;
SELECT @@tx_isolation as transaction_isolation;
SELECT 'FileWallBall ACID Transactions and Data Integrity configured successfully!' as status; 