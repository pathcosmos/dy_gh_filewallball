# Database Helpers 사용 가이드

이 문서는 `app/utils/database_helpers.py`에 구현된 데이터베이스 헬퍼 함수들의 사용법을 설명합니다.

## 개요

`DatabaseHelpers` 클래스는 파일 관리, 태그 관리, 통계 조회, 배치 처리 등 데이터베이스 작업을 위한 고급 헬퍼 함수들을 제공합니다.

## 기본 사용법

```python
from app.utils.database_helpers import DatabaseHelpers
from app.database import get_db

# 데이터베이스 세션 가져오기
db_session = next(get_db())
helpers = DatabaseHelpers(db_session)

# 헬퍼 함수 사용
files, total = helpers.search_files(query="document")
```

## 주요 기능

### 1. 파일 관리

#### 파일 생성 및 메타데이터 설정
```python
file_data = {
    'original_filename': 'document.pdf',
    'stored_filename': 'doc_uuid.pdf',
    'file_extension': 'pdf',
    'mime_type': 'application/pdf',
    'file_size': 1024000,
    'storage_path': '/storage/documents/doc_uuid.pdf'
}

# 파일 생성 (UUID 자동 생성)
file_info = helpers.create_file_with_metadata(
    file_data, 
    tags=['document', 'pdf', 'important']
)

# 파일 해시로 중복 검색
existing_file = helpers.find_file_by_hash("sha256_hash")
if existing_file:
    print(f"중복 파일 발견: {existing_file.original_filename}")
```

#### 고급 파일 검색
```python
# 기본 검색
files, total = helpers.search_files(query="report")

# 복합 조건 검색
files, total = helpers.search_files(
    query="document",
    extension="pdf",
    category_id=1,
    tags=["important", "urgent"],
    is_public=True,
    min_size=1024,
    max_size=10485760,  # 10MB
    date_from=datetime(2024, 1, 1),
    date_to=datetime(2024, 12, 31),
    limit=50,
    offset=0,
    order_by="file_size",
    order_direction="desc"
)

# 관계 데이터와 함께 조회
file_with_relations = helpers.get_file_with_relations("file_uuid")
if file_with_relations:
    print(f"카테고리: {file_with_relations.category.name}")
    print(f"태그: {[tag.tag_name for tag in file_with_relations.tags]}")
```

### 2. 태그 관리

#### 태그 추가/제거
```python
# 태그 일괄 추가
success = helpers.add_tags_to_file(
    file_id=1, 
    tag_names=["document", "pdf", "important"]
)

# 태그 제거
success = helpers.remove_tags_from_file(
    file_id=1, 
    tag_names=["old_tag"]
)

# 태그로 파일 검색
files = helpers.get_files_by_tags(["important", "urgent"], limit=20)

# 인기 태그 조회
popular_tags = helpers.get_popular_tags(limit=10)
for tag in popular_tags:
    print(f"{tag['tag_name']}: {tag['file_count']}개 파일")
```

### 3. 통계 및 분석

#### 파일 통계 조회
```python
stats = helpers.get_file_statistics()

print(f"전체 파일 수: {stats['total_files']}")
print(f"전체 크기: {format_file_size(stats['total_size'])}")

print("카테고리별 통계:")
for category in stats['category_stats']:
    print(f"  {category['name']}: {category['file_count']}개")

print("확장자별 통계:")
for ext in stats['extension_stats']:
    print(f"  {ext['extension']}: {ext['file_count']}개")
```

#### 업로드 트렌드
```python
# 최근 30일 업로드 트렌드
trends = helpers.get_upload_trends(days=30)

for trend in trends:
    print(f"{trend['date']}: {trend['upload_count']}개 업로드")
```

#### 파일 활동 통계
```python
activity = helpers.get_file_activity_stats("file_uuid", days=30)

print(f"조회 수: {activity['view_count']}")
print(f"다운로드 수: {activity['download_count']}")

print("최근 조회:")
for view in activity['recent_views']:
    print(f"  {view.created_at}: {view.viewer_ip}")
```

### 4. 배치 처리

#### 대량 파일 삽입
```python
files_data = [
    {
        'original_filename': 'file1.txt',
        'stored_filename': 'file1_uuid.txt',
        'file_extension': 'txt',
        'mime_type': 'text/plain',
        'file_size': 1024,
        'storage_path': '/storage/file1.txt'
    },
    # ... 더 많은 파일들
]

success_count, error_count = helpers.bulk_insert_files(files_data)
print(f"성공: {success_count}, 실패: {error_count}")
```

#### 대량 파일 업데이트
```python
updates = [
    {
        'file_uuid': 'uuid1',
        'is_public': False,
        'file_category_id': 2
    },
    # ... 더 많은 업데이트들
]

success_count, error_count = helpers.bulk_update_files(updates)
```

### 5. 시스템 설정 관리

```python
# 설정 저장
helpers.set_system_setting(
    key="max_file_size",
    value=10485760,  # 10MB
    setting_type="integer",
    description="최대 파일 업로드 크기"
)

helpers.set_system_setting(
    key="allowed_extensions",
    value=["pdf", "doc", "txt"],
    setting_type="json",
    description="허용된 파일 확장자"
)

# 설정 조회
max_size = helpers.get_system_setting("max_file_size", default=5242880)
allowed_exts = helpers.get_system_setting("allowed_extensions", default=[])
```

### 6. 유틸리티 함수

#### 트랜잭션 컨텍스트 매니저
```python
try:
    with helpers.transaction() as session:
        # 여러 데이터베이스 작업 수행
        file1 = FileInfo(...)
        session.add(file1)
        
        file2 = FileInfo(...)
        session.add(file2)
        
        # 성공 시 자동 커밋
except Exception as e:
    # 실패 시 자동 롤백
    print(f"트랜잭션 실패: {e}")
```

#### 로그 정리
```python
# 90일 이상 된 로그 정리
deleted_count = helpers.cleanup_old_logs(days=90)
print(f"{deleted_count}개의 오래된 로그 삭제됨")
```

#### 데이터베이스 크기 정보
```python
size_info = helpers.get_database_size_info()

for table, info in size_info.items():
    print(f"{table}:")
    print(f"  행 수: {info['rows']}")
    print(f"  데이터 크기: {format_file_size(info['data_size'])}")
    print(f"  인덱스 크기: {format_file_size(info['index_size'])}")
    print(f"  총 크기: {format_file_size(info['total_size'])}")
```

## 편의 함수들

### UUID 생성
```python
from app.utils.database_helpers import generate_file_uuid

file_uuid = generate_file_uuid()
print(f"생성된 UUID: {file_uuid}")
```

### 파일 해시 계산
```python
from app.utils.database_helpers import calculate_file_hash

with open('file.txt', 'rb') as f:
    content = f.read()
    file_hash = calculate_file_hash(content)
    print(f"파일 해시: {file_hash}")
```

### 파일 크기 포맷팅
```python
from app.utils.database_helpers import format_file_size

print(format_file_size(1024))        # "1.0 KB"
print(format_file_size(1048576))     # "1.0 MB"
print(format_file_size(1073741824))  # "1.0 GB"
```

## 에러 처리

모든 헬퍼 함수는 적절한 예외 처리를 포함하고 있습니다:

```python
try:
    file_info = helpers.create_file_with_metadata(file_data)
    if file_info is None:
        print("파일 생성 실패")
except Exception as e:
    print(f"예외 발생: {e}")
```

## 성능 최적화 팁

1. **대량 처리**: `bulk_insert_files`와 `bulk_update_files` 사용
2. **인덱스 활용**: 검색 조건에 맞는 인덱스가 있는지 확인
3. **페이지네이션**: 대량 데이터 조회 시 `limit`과 `offset` 사용
4. **관계 로딩**: `get_file_with_relations`로 N+1 쿼리 문제 방지
5. **로그 정리**: 정기적으로 `cleanup_old_logs` 실행

## 테스트

헬퍼 함수들의 단위 테스트는 `tests/test_database_helpers.py`에 포함되어 있습니다:

```bash
# 테스트 실행
pytest tests/test_database_helpers.py -v

# 통합 테스트 (실제 DB 필요)
pytest tests/test_database_helpers.py -m integration
``` 