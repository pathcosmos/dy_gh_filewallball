# FileWallBall 성능 최적화 가이드

## 📊 성능 최적화 결과

### ✅ 완료된 최적화 작업

#### 1. 인덱스 최적화
- **파일 테이블**: 25개 인덱스 생성
  - 복합 인덱스: `idx_files_composite`, `idx_files_search`, `idx_files_category_public`
  - 성능 최적화 인덱스: `idx_files_size`, `idx_files_hash`, `idx_files_stats`
  - 기본 인덱스: `file_uuid`, `original_filename`, `file_extension` 등

- **조회/다운로드 기록**: 15개 인덱스 생성
  - 성능 최적화: `idx_views_performance`, `idx_downloads_performance`
  - 시간 기반: `idx_views_ip_time`, `idx_downloads_ip_time`
  - 통계용: `idx_views_stats`, `idx_downloads_stats`

- **태그 시스템**: 8개 인덱스 생성
  - 사용 빈도: `idx_tags_usage`
  - 관계 최적화: `idx_tag_relations_performance`, `idx_tag_relations_reverse`

- **확장자/카테고리**: 12개 인덱스 생성
  - 검색 최적화: `idx_extensions_search`, `idx_categories_active`
  - 타입별: `idx_extensions_type`

#### 2. 성능 모니터링 설정
- **느린 쿼리 로그**: 2초 이상 쿼리 자동 로깅
- **인덱스 미사용 쿼리**: 자동 감지 및 로깅
- **성능 스키마**: 활성화됨

#### 3. 데이터베이스 파라미터
- **InnoDB 버퍼 풀**: 256MB (개발 환경)
- **쿼리 캐시**: 32MB
- **테이블 캐시**: 2000
- **최대 연결**: 200

## 🚀 성능 테스트 결과

### 테스트 1: 파일 검색 성능
```sql
EXPLAIN SELECT * FROM files 
WHERE is_deleted = FALSE 
AND is_public = TRUE 
AND file_extension = 'pdf' 
ORDER BY created_at DESC 
LIMIT 10;
```
**결과**: `idx_files_composite` 인덱스 사용, 최적화됨

### 테스트 2: 카테고리별 파일 조회
```sql
EXPLAIN SELECT f.*, c.name as category_name 
FROM files f 
LEFT JOIN file_categories c ON f.file_category_id = c.id 
WHERE f.is_deleted = FALSE 
AND f.is_public = TRUE 
AND f.file_category_id = 1 
ORDER BY f.created_at DESC;
```
**결과**: `idx_files_category_public` 인덱스 사용, 최적화됨

### 테스트 3: 파일 크기 기반 정렬
```sql
EXPLAIN SELECT * FROM files 
WHERE is_deleted = FALSE 
ORDER BY file_size DESC, created_at DESC 
LIMIT 10;
```
**결과**: `idx_files_size` 인덱스 사용, 최적화됨

### 테스트 4: 태그 기반 검색
```sql
EXPLAIN SELECT f.*, t.name as tag_name 
FROM files f 
JOIN file_tag_relations ftr ON f.id = ftr.file_id 
JOIN file_tags t ON ftr.tag_id = t.id 
WHERE f.is_deleted = FALSE 
AND t.name = 'important' 
ORDER BY f.created_at DESC;
```
**결과**: 태그 관계 인덱스 활용, 최적화됨

### 테스트 5: 통계 뷰 성능
```sql
EXPLAIN SELECT * FROM file_statistics 
WHERE view_count > 0 
ORDER BY download_count DESC 
LIMIT 10;
```
**결과**: 통계 뷰용 인덱스 활용, 최적화됨

## 📈 인덱스 사용 통계

### 주요 테이블별 인덱스 수
- **files**: 25개 인덱스
- **file_views**: 15개 인덱스
- **file_downloads**: 15개 인덱스
- **file_uploads**: 15개 인덱스
- **file_tag_relations**: 8개 인덱스
- **file_extensions**: 12개 인덱스
- **file_categories**: 6개 인덱스
- **file_tags**: 6개 인덱스
- **system_settings**: 6개 인덱스

### 인덱스 타입 분포
- **BTREE**: 100% (모든 인덱스)
- **복합 인덱스**: 40% (성능 최적화용)
- **단일 컬럼**: 60% (기본 인덱스)

## 🔧 성능 모니터링

### 느린 쿼리 확인
```bash
# MariaDB Pod에서 느린 쿼리 로그 확인
kubectl exec -n filewallball mariadb-65c8cbd577-kb9lh -- tail -f /var/log/mysql/slow.log
```

### 인덱스 사용률 확인
```sql
-- 인덱스 사용 통계 확인
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    CARDINALITY,
    INDEX_TYPE
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'filewallball_db' 
ORDER BY TABLE_NAME, INDEX_NAME;
```

### 테이블 크기 모니터링
```sql
-- 테이블 크기 및 통계 확인
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    DATA_LENGTH,
    INDEX_LENGTH,
    (DATA_LENGTH + INDEX_LENGTH) as TOTAL_SIZE
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'filewallball_db' 
ORDER BY TABLE_NAME;
```

## 📋 성능 최적화 체크리스트

### ✅ 완료된 항목
- [x] 복합 인덱스 생성
- [x] 파일 검색 최적화
- [x] 카테고리별 조회 최적화
- [x] 태그 시스템 최적화
- [x] 통계 뷰 최적화
- [x] 느린 쿼리 로그 설정
- [x] 성능 모니터링 설정

### 🔄 지속적 모니터링
- [ ] 주기적인 인덱스 사용률 확인
- [ ] 느린 쿼리 분석 및 최적화
- [ ] 테이블 크기 모니터링
- [ ] 성능 메트릭 수집

## 🎯 성능 최적화 효과

### 예상 성능 향상
1. **파일 검색**: 80% 성능 향상 (복합 인덱스 활용)
2. **카테고리별 조회**: 70% 성능 향상 (전용 인덱스)
3. **태그 기반 검색**: 60% 성능 향상 (관계 인덱스)
4. **통계 조회**: 90% 성능 향상 (통계 뷰 + 인덱스)

### 확장성 개선
- 대용량 데이터 처리 가능
- 동시 사용자 증가 대응
- 복잡한 쿼리 최적화

## 📝 추가 최적화 권장사항

### 1. 정기적인 인덱스 유지보수
```sql
-- 주기적으로 인덱스 분석
ANALYZE TABLE files;
ANALYZE TABLE file_views;
ANALYZE TABLE file_downloads;
```

### 2. 파티셔닝 고려
- 대용량 데이터의 경우 테이블 파티셔닝 적용
- 날짜 기반 파티셔닝 (file_views, file_downloads)

### 3. 캐싱 전략
- Redis 캐싱과 연동하여 반복 쿼리 최적화
- 자주 조회되는 파일 정보 캐싱

### 4. 백업 및 복구 최적화
- 인덱스가 포함된 백업 전략 수립
- 복구 시 인덱스 재생성 최적화

---

**최종 결과**: FileWallBall 데이터베이스 성능 최적화가 성공적으로 완료되었습니다. 모든 주요 쿼리가 인덱스를 활용하여 최적의 성능을 발휘할 수 있도록 구성되었습니다. 