#!/usr/bin/env python3
"""
Database Performance Test Script
대용량 데이터셋으로 쿼리 성능을 측정하고 최적화 결과를 검증합니다.
"""

import sys
import os
import time
import random
import string
from typing import List, Dict, Any
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.orm_models import Base, FileInfo, FileCategory, FileTag, FileTagRelation
from app.utils.performance_analyzer import PerformanceAnalyzer, QueryOptimizer


class PerformanceTester:
    """데이터베이스 성능 테스트 클래스"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db_session = self.SessionLocal()
        self.analyzer = PerformanceAnalyzer(self.db_session)
        self.optimizer = QueryOptimizer(self.db_session)
    
    def generate_test_data(self, file_count: int = 10000) -> None:
        """테스트용 대용량 데이터 생성"""
        print(f"테스트 데이터 생성 중... ({file_count:,}개 파일)")
        
        # 카테고리 생성
        categories = self._create_categories()
        tags = self._create_tags()
        
        # 파일 데이터 생성
        extensions = ['pdf', 'doc', 'txt', 'jpg', 'png', 'mp4', 'zip', 'xlsx']
        mime_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'mp4': 'video/mp4',
            'zip': 'application/zip',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        batch_size = 1000
        for i in range(0, file_count, batch_size):
            batch_files = []
            current_batch_size = min(batch_size, file_count - i)
            
            for j in range(current_batch_size):
                extension = random.choice(extensions)
                file_size = random.randint(1024, 100 * 1024 * 1024)  # 1KB ~ 100MB
                
                file_info = FileInfo(
                    original_filename=f"test_file_{i+j}_{extension}.{extension}",
                    stored_filename=f"stored_{i+j}_{extension}.{extension}",
                    file_extension=extension,
                    mime_type=mime_types[extension],
                    file_size=file_size,
                    file_hash=f"hash_{i+j}_{random.randint(1000, 9999)}",
                    storage_path=f"/uploads/{extension}/{i+j}.{extension}",
                    file_category_id=random.choice(categories).id,
                    is_public=random.choice([True, False]),
                    is_deleted=False,
                    created_at=datetime.now() - timedelta(days=random.randint(0, 365))
                )
                batch_files.append(file_info)
            
            self.db_session.add_all(batch_files)
            self.db_session.commit()
            
            # 태그 관계 생성
            self._create_tag_relations(batch_files, tags)
            
            print(f"진행률: {min(i + batch_size, file_count):,}/{file_count:,}")
        
        print("테스트 데이터 생성 완료!")
    
    def _create_categories(self) -> List[FileCategory]:
        """테스트용 카테고리 생성"""
        categories = [
            FileCategory(name="문서", description="문서 파일들"),
            FileCategory(name="이미지", description="이미지 파일들"),
            FileCategory(name="비디오", description="비디오 파일들"),
            FileCategory(name="압축파일", description="압축 파일들"),
            FileCategory(name="스프레드시트", description="스프레드시트 파일들")
        ]
        
        for category in categories:
            existing = self.db_session.query(FileCategory).filter(
                FileCategory.name == category.name
            ).first()
            if not existing:
                self.db_session.add(category)
        
        self.db_session.commit()
        return self.db_session.query(FileCategory).all()
    
    def _create_tags(self) -> List[FileTag]:
        """테스트용 태그 생성"""
        tag_names = ["중요", "임시", "백업", "최종", "검토", "승인", "거부", "대기", "완료", "진행중"]
        tags = []
        
        for tag_name in tag_names:
            existing = self.db_session.query(FileTag).filter(
                FileTag.tag_name == tag_name
            ).first()
            if not existing:
                tag = FileTag(tag_name=tag_name, tag_color=f"#{random.randint(0, 0xFFFFFF):06x}")
                self.db_session.add(tag)
                tags.append(tag)
            else:
                tags.append(existing)
        
        self.db_session.commit()
        return tags
    
    def _create_tag_relations(self, files: List[FileInfo], tags: List[FileTag]) -> None:
        """파일-태그 관계 생성"""
        for file_info in files:
            # 각 파일에 1-3개의 랜덤 태그 추가
            num_tags = random.randint(1, 3)
            selected_tags = random.sample(tags, num_tags)
            
            for tag in selected_tags:
                relation = FileTagRelation(file_id=file_info.id, tag_id=tag.id)
                self.db_session.add(relation)
        
        self.db_session.commit()
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """성능 테스트 실행"""
        print("\n=== 성능 테스트 시작 ===")
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }
        
        # 1. 기본 파일 조회 테스트
        test_results['tests']['basic_file_query'] = self._test_basic_file_query()
        
        # 2. 확장자별 파일 검색 테스트
        test_results['tests']['extension_search'] = self._test_extension_search()
        
        # 3. 카테고리별 파일 검색 테스트
        test_results['tests']['category_search'] = self._test_category_search()
        
        # 4. 태그 기반 파일 검색 테스트
        test_results['tests']['tag_search'] = self._test_tag_search()
        
        # 5. 복합 조건 검색 테스트
        test_results['tests']['complex_search'] = self._test_complex_search()
        
        # 6. 통계 쿼리 테스트
        test_results['tests']['statistics_query'] = self._test_statistics_query()
        
        return test_results
    
    def _test_basic_file_query(self) -> Dict[str, Any]:
        """기본 파일 조회 테스트"""
        print("1. 기본 파일 조회 테스트...")
        
        query = "SELECT * FROM files WHERE is_deleted = FALSE ORDER BY created_at DESC LIMIT 100"
        
        start_time = time.time()
        result = self.db_session.execute(text(query))
        files = result.fetchall()
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'query': query,
            'execution_time_ms': execution_time,
            'result_count': len(files),
            'query_plan': self.analyzer.analyze_query_plan(query)
        }
    
    def _test_extension_search(self) -> Dict[str, Any]:
        """확장자별 파일 검색 테스트"""
        print("2. 확장자별 파일 검색 테스트...")
        
        query, params = self.optimizer.optimize_file_search_query(
            extension='pdf', limit=100
        )
        
        start_time = time.time()
        result = self.db_session.execute(text(query), params)
        files = result.fetchall()
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'query': query,
            'params': params,
            'execution_time_ms': execution_time,
            'result_count': len(files),
            'query_plan': self.analyzer.analyze_query_plan(query, params)
        }
    
    def _test_category_search(self) -> Dict[str, Any]:
        """카테고리별 파일 검색 테스트"""
        print("3. 카테고리별 파일 검색 테스트...")
        
        # 첫 번째 카테고리 ID 가져오기
        category = self.db_session.query(FileCategory).first()
        if not category:
            return {'error': '카테고리가 없습니다.'}
        
        query, params = self.optimizer.optimize_file_search_query(
            category_id=category.id, limit=100
        )
        
        start_time = time.time()
        result = self.db_session.execute(text(query), params)
        files = result.fetchall()
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'query': query,
            'params': params,
            'execution_time_ms': execution_time,
            'result_count': len(files),
            'query_plan': self.analyzer.analyze_query_plan(query, params)
        }
    
    def _test_tag_search(self) -> Dict[str, Any]:
        """태그 기반 파일 검색 테스트"""
        print("4. 태그 기반 파일 검색 테스트...")
        
        # 첫 번째 태그 가져오기
        tag = self.db_session.query(FileTag).first()
        if not tag:
            return {'error': '태그가 없습니다.'}
        
        query, params = self.optimizer.optimize_tag_search_query(
            tag_names=[tag.tag_name], limit=100
        )
        
        start_time = time.time()
        result = self.db_session.execute(text(query), params)
        files = result.fetchall()
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'query': query,
            'params': params,
            'execution_time_ms': execution_time,
            'result_count': len(files),
            'query_plan': self.analyzer.analyze_query_plan(query, params)
        }
    
    def _test_complex_search(self) -> Dict[str, Any]:
        """복합 조건 검색 테스트"""
        print("5. 복합 조건 검색 테스트...")
        
        query, params = self.optimizer.optimize_file_search_query(
            extension='pdf',
            is_public=True,
            limit=100
        )
        
        start_time = time.time()
        result = self.db_session.execute(text(query), params)
        files = result.fetchall()
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'query': query,
            'params': params,
            'execution_time_ms': execution_time,
            'result_count': len(files),
            'query_plan': self.analyzer.analyze_query_plan(query, params)
        }
    
    def _test_statistics_query(self) -> Dict[str, Any]:
        """통계 쿼리 테스트"""
        print("6. 통계 쿼리 테스트...")
        
        query, params = self.optimizer.optimize_statistics_query(days=30)
        
        start_time = time.time()
        result = self.db_session.execute(text(query), params)
        stats = result.fetchall()
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'query': query,
            'params': params,
            'execution_time_ms': execution_time,
            'result_count': len(stats),
            'query_plan': self.analyzer.analyze_query_plan(query, params)
        }
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        print("\n=== 성능 리포트 생성 중... ===")
        
        report = self.analyzer.generate_performance_report()
        
        # 테이블별 통계 출력
        print("\n--- 테이블별 통계 ---")
        for table_name, data in report['tables'].items():
            stats = data.get('statistics', {})
            if stats:
                print(f"{table_name}: {stats.get('table_rows', 0):,}행, "
                      f"데이터 크기: {stats.get('data_length', 0):,}바이트, "
                      f"인덱스 크기: {stats.get('index_length', 0):,}바이트")
        
        # 권장사항 출력
        if report.get('recommendations'):
            print("\n--- 성능 개선 권장사항 ---")
            for rec in report['recommendations']:
                print(f"- {rec}")
        
        return report
    
    def cleanup(self):
        """리소스 정리"""
        self.db_session.close()


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터베이스 성능 테스트')
    parser.add_argument('--db-url', required=True, help='데이터베이스 연결 URL')
    parser.add_argument('--file-count', type=int, default=10000, help='생성할 테스트 파일 수')
    parser.add_argument('--skip-data-generation', action='store_true', help='데이터 생성 건너뛰기')
    parser.add_argument('--output-file', help='결과를 저장할 JSON 파일')
    
    args = parser.parse_args()
    
    tester = PerformanceTester(args.db_url)
    
    try:
        if not args.skip_data_generation:
            tester.generate_test_data(args.file_count)
        
        # 성능 테스트 실행
        test_results = tester.run_performance_tests()
        
        # 성능 리포트 생성
        performance_report = tester.generate_performance_report()
        
        # 결과 출력
        print("\n=== 테스트 결과 요약 ===")
        for test_name, result in test_results['tests'].items():
            if 'error' not in result:
                print(f"{test_name}: {result['execution_time_ms']:.2f}ms "
                      f"({result['result_count']}개 결과)")
            else:
                print(f"{test_name}: {result['error']}")
        
        # 결과 저장
        if args.output_file:
            import json
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_results': test_results,
                    'performance_report': performance_report
                }, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n결과가 {args.output_file}에 저장되었습니다.")
    
    finally:
        tester.cleanup()


if __name__ == '__main__':
    main() 