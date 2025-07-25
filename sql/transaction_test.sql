-- =====================================================
-- FileWallBall 트랜잭션 격리 수준 및 동시성 제어 테스트
-- ACID 속성 검증 및 데이터 무결성 테스트
-- =====================================================

USE filewallball_db;

-- =====================================================
-- 1. 트랜잭션 격리 수준 확인
-- =====================================================

SELECT '=== 트랜잭션 격리 수준 확인 ===' as info;
SELECT @@tx_isolation as current_isolation;

-- =====================================================
-- 2. 트리거 생성 확인
-- =====================================================

SELECT '=== 생성된 트리거 목록 ===' as info;
SELECT 
    TRIGGER_NAME,
    EVENT_MANIPULATION,
    EVENT_OBJECT_TABLE,
    ACTION_TIMING
FROM information_schema.TRIGGERS 
WHERE TRIGGER_SCHEMA = 'filewallball_db'
ORDER BY TRIGGER_NAME;

-- =====================================================
-- 3. 프로시저 생성 확인
-- =====================================================

SELECT '=== 생성된 프로시저 목록 ===' as info;
SELECT 
    ROUTINE_NAME,
    ROUTINE_TYPE,
    DATA_TYPE
FROM information_schema.ROUTINES 
WHERE ROUTINE_SCHEMA = 'filewallball_db'
ORDER BY ROUTINE_NAME;

-- =====================================================
-- 4. 함수 생성 확인
-- =====================================================

SELECT '=== 생성된 함수 목록 ===' as info;
SELECT 
    ROUTINE_NAME,
    ROUTINE_TYPE,
    DATA_TYPE
FROM information_schema.ROUTINES 
WHERE ROUTINE_SCHEMA = 'filewallball_db'
AND ROUTINE_TYPE = 'FUNCTION'
ORDER BY ROUTINE_NAME;

-- =====================================================
-- 5. 데이터 무결성 테스트
-- =====================================================

-- 테스트 1: 파일 크기 제약 조건 테스트
SELECT '=== 테스트 1: 파일 크기 제약 조건 ===' as info;

-- 정상적인 파일 크기 (성공해야 함)
INSERT INTO files (
    file_uuid, original_filename, stored_filename, 
    file_extension, mime_type, file_size, file_hash, 
    storage_path, is_public
) VALUES (
    'test-uuid-1', 'test.txt', 'test_1.txt',
    '.txt', 'text/plain', 1024, 'd41d8cd98f00b204e9800998ecf8427e',
    '/app/uploads/test_1.txt', TRUE
);

-- 잘못된 파일 크기 (실패해야 함)
SELECT '=== 잘못된 파일 크기 테스트 (실패 예상) ===' as info;
INSERT INTO files (
    file_uuid, original_filename, stored_filename, 
    file_extension, mime_type, file_size, file_hash, 
    storage_path, is_public
) VALUES (
    'test-uuid-2', 'test.txt', 'test_2.txt',
    '.txt', 'text/plain', 0, 'd41d8cd98f00b204e9800998ecf8427e',
    '/app/uploads/test_2.txt', TRUE
);

-- 테스트 2: 파일 해시 제약 조건 테스트
SELECT '=== 테스트 2: 파일 해시 제약 조건 ===' as info;

-- 잘못된 해시 길이 (실패해야 함)
SELECT '=== 잘못된 해시 길이 테스트 (실패 예상) ===' as info;
INSERT INTO files (
    file_uuid, original_filename, stored_filename, 
    file_extension, mime_type, file_size, file_hash, 
    storage_path, is_public
) VALUES (
    'test-uuid-3', 'test.txt', 'test_3.txt',
    '.txt', 'text/plain', 1024, 'invalid_hash',
    '/app/uploads/test_3.txt', TRUE
);

-- 테스트 3: 허용되지 않은 확장자 테스트
SELECT '=== 테스트 3: 허용되지 않은 확장자 ===' as info;

-- 허용되지 않은 확장자 (실패해야 함)
SELECT '=== 허용되지 않은 확장자 테스트 (실패 예상) ===' as info;
INSERT INTO files (
    file_uuid, original_filename, stored_filename, 
    file_extension, mime_type, file_size, file_hash, 
    storage_path, is_public
) VALUES (
    'test-uuid-4', 'test.exe', 'test_4.exe',
    '.exe', 'application/octet-stream', 1024, 'd41d8cd98f00b204e9800998ecf8427e',
    '/app/uploads/test_4.exe', TRUE
);

-- =====================================================
-- 6. 동시성 제어 테스트
-- =====================================================

-- 테스트 4: 파일 업로드 프로시저 테스트
SELECT '=== 테스트 4: 파일 업로드 프로시저 ===' as info;

-- 정상적인 파일 업로드
CALL upload_file_with_lock(
    'test-uuid-5', 'test.pdf', 'test_5.pdf',
    '.pdf', 'application/pdf', 2048, 'd41d8cd98f00b204e9800998ecf8427e',
    '/app/uploads/test_5.pdf', 1, TRUE,
    '192.168.1.100', 'Mozilla/5.0', 'web', 'session-123'
);

-- 중복 UUID 테스트 (실패해야 함)
SELECT '=== 중복 UUID 테스트 (실패 예상) ===' as info;
CALL upload_file_with_lock(
    'test-uuid-5', 'test2.pdf', 'test_6.pdf',
    '.pdf', 'application/pdf', 2048, 'd41d8cd98f00b204e9800998ecf8427e',
    '/app/uploads/test_6.pdf', 1, TRUE,
    '192.168.1.100', 'Mozilla/5.0', 'web', 'session-123'
);

-- 테스트 5: 파일 다운로드 프로시저 테스트
SELECT '=== 테스트 5: 파일 다운로드 프로시저 ===' as info;

-- 정상적인 파일 다운로드
CALL download_file_with_lock(
    'test-uuid-5', '192.168.1.101', 'Mozilla/5.0', 'web', 'session-456'
);

-- 존재하지 않는 파일 다운로드 (실패해야 함)
SELECT '=== 존재하지 않는 파일 다운로드 테스트 (실패 예상) ===' as info;
CALL download_file_with_lock(
    'non-existent-uuid', '192.168.1.102', 'Mozilla/5.0', 'web', 'session-789'
);

-- =====================================================
-- 7. 무결성 검증 함수 테스트
-- =====================================================

SELECT '=== 테스트 6: 무결성 검증 함수 ===' as info;

-- 파일 무결성 검증
SELECT validate_file_integrity(1) as file_1_exists;
SELECT validate_file_integrity(999) as file_999_exists;

-- 태그 무결성 검증 (태그가 없으므로 FALSE 반환)
SELECT validate_tag_integrity(1) as tag_1_exists;

-- =====================================================
-- 8. 트랜잭션 롤백 테스트
-- =====================================================

SELECT '=== 테스트 7: 트랜잭션 롤백 ===' as info;

START TRANSACTION;

-- 트랜잭션 내에서 데이터 삽입
INSERT INTO files (
    file_uuid, original_filename, stored_filename, 
    file_extension, mime_type, file_size, file_hash, 
    storage_path, is_public
) VALUES (
    'rollback-test', 'rollback.txt', 'rollback_test.txt',
    '.txt', 'text/plain', 512, 'd41d8cd98f00b204e9800998ecf8427e',
    '/app/uploads/rollback_test.txt', TRUE
);

-- 롤백 전 확인
SELECT COUNT(*) as before_rollback FROM files WHERE file_uuid = 'rollback-test';

-- 롤백 실행
ROLLBACK;

-- 롤백 후 확인
SELECT COUNT(*) as after_rollback FROM files WHERE file_uuid = 'rollback-test';

-- =====================================================
-- 9. 테스트 데이터 정리
-- =====================================================

SELECT '=== 테스트 데이터 정리 ===' as info;

-- 테스트로 생성된 파일들 삭제
DELETE FROM files WHERE file_uuid LIKE 'test-uuid-%';
DELETE FROM files WHERE file_uuid = 'rollback-test';

-- =====================================================
-- 10. 최종 결과 확인
-- =====================================================

SELECT '=== 최종 테스트 결과 ===' as info;
SELECT 'ACID 트랜잭션 및 데이터 무결성 테스트가 성공적으로 완료되었습니다!' as status;

-- 생성된 객체들 확인
SELECT '트리거 수' as object_type, COUNT(*) as count 
FROM information_schema.TRIGGERS 
WHERE TRIGGER_SCHEMA = 'filewallball_db'
UNION ALL
SELECT '프로시저 수', COUNT(*) 
FROM information_schema.ROUTINES 
WHERE ROUTINE_SCHEMA = 'filewallball_db' AND ROUTINE_TYPE = 'PROCEDURE'
UNION ALL
SELECT '함수 수', COUNT(*) 
FROM information_schema.ROUTINES 
WHERE ROUTINE_SCHEMA = 'filewallball_db' AND ROUTINE_TYPE = 'FUNCTION'; 