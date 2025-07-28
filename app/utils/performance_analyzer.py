"""
Database Performance Analyzer and Query Optimization Utilities
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """데이터베이스 성능 분석 및 쿼리 최적화 도구"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.engine = db_session.bind
    
    @contextmanager
    def measure_query_time(self, query_name: str = "Query"):
        """쿼리 실행 시간 측정 컨텍스트 매니저"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = (time.time() - start_time) * 1000  # ms
            logger.info(f"{query_name} 실행 시간: {execution_time:.2f}ms")
    
    def analyze_query_plan(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """쿼리 실행 계획 분석"""
        try:
            explain_query = f"EXPLAIN FORMAT=JSON {query}"
            result = self.db_session.execute(text(explain_query), params or {})
            plan = result.fetchone()
            
            if plan and hasattr(plan, '__getitem__'):
                return {
                    'query': query,
                    'params': params,
                    'execution_plan': plan[0] if isinstance(plan[0], dict) else plan,
                    'analyzed_at': time.time()
                }
            return {'error': '실행 계획을 가져올 수 없습니다.'}
            
        except SQLAlchemyError as e:
            logger.error(f"쿼리 실행 계획 분석 실패: {e}")
            return {'error': str(e)}
    
    def check_index_usage(self, table_name: str) -> List[Dict[str, Any]]:
        """테이블의 인덱스 사용 현황 확인"""
        try:
            query = """
            SELECT 
                INDEX_NAME,
                COLUMN_NAME,
                SEQ_IN_INDEX,
                CARDINALITY,
                SUB_PART,
                PACKED,
                NULLABLE,
                INDEX_TYPE
            FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = :table_name
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """
            
            result = self.db_session.execute(text(query), {'table_name': table_name})
            indexes = []
            
            for row in result:
                indexes.append({
                    'index_name': row[0],
                    'column_name': row[1],
                    'sequence': row[2],
                    'cardinality': row[3],
                    'sub_part': row[4],
                    'packed': row[5],
                    'nullable': row[6],
                    'index_type': row[7]
                })
            
            return indexes
            
        except SQLAlchemyError as e:
            logger.error(f"인덱스 사용 현황 확인 실패: {e}")
            return []
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """슬로우 쿼리 로그 조회 (MariaDB slow query log 기반)"""
        try:
            # MariaDB slow query log 확인
            query = """
            SELECT 
                start_time,
                query_time,
                lock_time,
                rows_sent,
                rows_examined,
                sql_text
            FROM mysql.slow_log 
            WHERE start_time > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY query_time DESC 
            LIMIT :limit
            """
            
            result = self.db_session.execute(text(query), {'limit': limit})
            slow_queries = []
            
            for row in result:
                slow_queries.append({
                    'start_time': row[0],
                    'query_time': row[1],
                    'lock_time': row[2],
                    'rows_sent': row[3],
                    'rows_examined': row[4],
                    'sql_text': row[5]
                })
            
            return slow_queries
            
        except SQLAlchemyError as e:
            logger.warning(f"슬로우 쿼리 로그 조회 실패 (slow query log가 활성화되지 않음): {e}")
            return []
    
    def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """테이블 통계 정보 조회"""
        try:
            query = """
            SELECT 
                TABLE_ROWS,
                AVG_ROW_LENGTH,
                DATA_LENGTH,
                MAX_DATA_LENGTH,
                INDEX_LENGTH,
                AUTO_INCREMENT,
                CREATE_TIME,
                UPDATE_TIME,
                CHECK_TIME
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = :table_name
            """
            
            result = self.db_session.execute(text(query), {'table_name': table_name})
            row = result.fetchone()
            
            if row:
                return {
                    'table_name': table_name,
                    'table_rows': row[0],
                    'avg_row_length': row[1],
                    'data_length': row[2],
                    'max_data_length': row[3],
                    'index_length': row[4],
                    'auto_increment': row[5],
                    'create_time': row[6],
                    'update_time': row[7],
                    'check_time': row[8]
                }
            
            return {}
            
        except SQLAlchemyError as e:
            logger.error(f"테이블 통계 조회 실패: {e}")
            return {}
    
    def optimize_table(self, table_name: str) -> bool:
        """테이블 최적화 실행"""
        try:
            query = f"OPTIMIZE TABLE {table_name}"
            self.db_session.execute(text(query))
            self.db_session.commit()
            logger.info(f"테이블 {table_name} 최적화 완료")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"테이블 최적화 실패: {e}")
            self.db_session.rollback()
            return False
    
    def analyze_index_efficiency(self, table_name: str) -> List[Dict[str, Any]]:
        """인덱스 효율성 분석"""
        try:
            query = """
            SELECT 
                INDEX_NAME,
                CARDINALITY,
                SUB_PART,
                PACKED,
                NULLABLE,
                INDEX_TYPE,
                COMMENT
            FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = :table_name
            GROUP BY INDEX_NAME
            ORDER BY CARDINALITY DESC
            """
            
            result = self.db_session.execute(text(query), {'table_name': table_name})
            efficiency = []
            
            for row in result:
                efficiency.append({
                    'index_name': row[0],
                    'cardinality': row[1],
                    'selectivity': self._calculate_selectivity(row[1], table_name),
                    'sub_part': row[2],
                    'packed': row[3],
                    'nullable': row[4],
                    'index_type': row[5],
                    'comment': row[6]
                })
            
            return efficiency
            
        except SQLAlchemyError as e:
            logger.error(f"인덱스 효율성 분석 실패: {e}")
            return []
    
    def _calculate_selectivity(self, cardinality: int, table_name: str) -> float:
        """인덱스 선택도 계산"""
        try:
            stats = self.get_table_statistics(table_name)
            if stats and stats.get('table_rows', 0) > 0:
                return cardinality / stats['table_rows']
            return 0.0
        except:
            return 0.0
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """전체 성능 리포트 생성"""
        tables = ['files', 'file_views', 'file_downloads', 'file_uploads', 
                 'file_tags', 'file_tag_relations', 'file_categories']
        
        report = {
            'generated_at': time.time(),
            'tables': {},
            'recommendations': []
        }
        
        for table in tables:
            report['tables'][table] = {
                'statistics': self.get_table_statistics(table),
                'indexes': self.check_index_usage(table),
                'index_efficiency': self.analyze_index_efficiency(table)
            }
        
        # 성능 개선 권장사항 생성
        report['recommendations'] = self._generate_recommendations(report['tables'])
        
        return report
    
    def _generate_recommendations(self, tables_data: Dict) -> List[str]:
        """성능 개선 권장사항 생성"""
        recommendations = []
        
        for table_name, data in tables_data.items():
            stats = data.get('statistics', {})
            indexes = data.get('indexes', [])
            
            # 테이블 크기 기반 권장사항
            if stats.get('table_rows', 0) > 1000000:
                recommendations.append(f"{table_name}: 대용량 테이블 - 파티셔닝 고려")
            
            # 인덱스 기반 권장사항
            index_count = len(set(idx['index_name'] for idx in indexes))
            if index_count > 10:
                recommendations.append(f"{table_name}: 인덱스가 많음 - 불필요한 인덱스 제거 고려")
            
            # 카디널리티 기반 권장사항
            for idx in indexes:
                if idx.get('cardinality', 0) < 10:
                    recommendations.append(f"{table_name}.{idx['index_name']}: 낮은 카디널리티 - 인덱스 제거 고려")
        
        return recommendations


class QueryOptimizer:
    """쿼리 최적화 도구"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.analyzer = PerformanceAnalyzer(db_session)
    
    def optimize_file_search_query(self, 
                                 extension: Optional[str] = None,
                                 category_id: Optional[int] = None,
                                 is_public: Optional[bool] = None,
                                 limit: int = 100) -> str:
        """파일 검색 쿼리 최적화"""
        
        base_query = """
        SELECT f.*, c.name as category_name
        FROM files f
        LEFT JOIN file_categories c ON f.file_category_id = c.id
        WHERE f.is_deleted = FALSE
        """
        
        params = {}
        conditions = []
        
        if extension:
            conditions.append("f.file_extension = :extension")
            params['extension'] = extension
        
        if category_id is not None:
            conditions.append("f.file_category_id = :category_id")
            params['category_id'] = category_id
        
        if is_public is not None:
            conditions.append("f.is_public = :is_public")
            params['is_public'] = is_public
        
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        base_query += " ORDER BY f.created_at DESC LIMIT :limit"
        params['limit'] = limit
        
        # 인덱스 힌트 추가
        if extension and category_id is not None:
            base_query = base_query.replace(
                "FROM files f",
                "FROM files f USE INDEX (ix_files_extension_size_created, ix_files_category_deleted_created)"
            )
        elif extension:
            base_query = base_query.replace(
                "FROM files f",
                "FROM files f USE INDEX (ix_files_extension_size_created)"
            )
        
        return base_query, params
    
    def optimize_tag_search_query(self, tag_names: List[str], limit: int = 100) -> Tuple[str, Dict]:
        """태그 기반 파일 검색 쿼리 최적화"""
        
        query = """
        SELECT DISTINCT f.*, c.name as category_name
        FROM files f
        LEFT JOIN file_categories c ON f.file_category_id = c.id
        INNER JOIN file_tag_relations ftr ON f.id = ftr.file_id
        INNER JOIN file_tags ft ON ftr.tag_id = ft.id
        WHERE f.is_deleted = FALSE
        AND ft.tag_name IN :tag_names
        AND ft.is_active = TRUE
        ORDER BY f.created_at DESC
        LIMIT :limit
        """
        
        params = {
            'tag_names': tuple(tag_names),
            'limit': limit
        }
        
        return query, params
    
    def optimize_statistics_query(self, days: int = 30) -> Tuple[str, Dict]:
        """통계 쿼리 최적화"""
        
        query = """
        SELECT 
            DATE(f.created_at) as upload_date,
            COUNT(*) as upload_count,
            SUM(f.file_size) as total_size,
            AVG(f.file_size) as avg_size
        FROM files f
        WHERE f.created_at >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        AND f.is_deleted = FALSE
        GROUP BY DATE(f.created_at)
        ORDER BY upload_date DESC
        """
        
        params = {'days': days}
        
        return query, params 