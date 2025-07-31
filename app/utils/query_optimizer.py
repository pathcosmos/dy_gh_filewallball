"""
Query optimization utilities.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Query optimization and analysis tools."""

    def __init__(self, session: AsyncSession):
        """Initialize query optimizer."""
        self.session = session

    async def explain_query(self, query: str, params: Optional[Dict] = None) -> Dict:
        """Explain query execution plan."""
        try:
            # Add EXPLAIN to the query
            explain_query = f"EXPLAIN {query}"

            result = await self.session.execute(text(explain_query), params or {})

            plan = result.fetchall()

            return {
                "query": query,
                "params": params,
                "plan": [dict(row._mapping) for row in plan],
                "analysis": self._analyze_plan(plan),
            }
        except Exception as e:
            logger.error(f"Error explaining query: {e}")
            return {"query": query, "error": str(e)}

    def _analyze_plan(self, plan: List) -> Dict:
        """Analyze execution plan for optimization opportunities."""
        analysis = {
            "total_cost": 0,
            "has_index_scan": False,
            "has_seq_scan": False,
            "has_temp": False,
            "suggestions": [],
        }

        for row in plan:
            row_dict = dict(row._mapping)

            # Extract cost information
            if "Total Cost" in row_dict:
                try:
                    cost = float(row_dict["Total Cost"])
                    analysis["total_cost"] += cost
                except (ValueError, TypeError):
                    pass

            # Check scan types
            node_type = row_dict.get("Node Type", "").lower()

            if "index" in node_type:
                analysis["has_index_scan"] = True
            elif "seq" in node_type:
                analysis["has_seq_scan"] = True
                analysis["suggestions"].append(
                    "Consider adding an index to avoid sequential scan"
                )

            if "temp" in node_type:
                analysis["has_temp"] = True
                analysis["suggestions"].append(
                    "Query uses temporary tables - consider optimization"
                )

        # Add cost-based suggestions
        if analysis["total_cost"] > 1000:
            analysis["suggestions"].append(
                "High cost query - consider adding indexes or rewriting"
            )

        if not analysis["has_index_scan"] and analysis["has_seq_scan"]:
            analysis["suggestions"].append(
                "No index scans detected - review indexing strategy"
            )

        return analysis

    async def analyze_table_indexes(self, table_name: str) -> Dict:
        """Analyze table indexes."""
        try:
            # Get index information
            index_query = """
            SELECT
                indexname,
                indexdef,
                schemaname,
                tablename
            FROM pg_indexes
            WHERE tablename = :table_name
            ORDER BY indexname
            """

            result = await self.session.execute(
                text(index_query), {"table_name": table_name}
            )

            indexes = [dict(row._mapping) for row in result.fetchall()]

            # Get table statistics
            stats_query = """
            SELECT
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation
            FROM pg_stats
            WHERE tablename = :table_name
            ORDER BY attname
            """

            result = await self.session.execute(
                text(stats_query), {"table_name": table_name}
            )

            stats = [dict(row._mapping) for row in result.fetchall()]

            return {
                "table_name": table_name,
                "indexes": indexes,
                "statistics": stats,
                "recommendations": self._generate_index_recommendations(stats, indexes),
            }
        except Exception as e:
            logger.error(f"Error analyzing table indexes: {e}")
            return {"table_name": table_name, "error": str(e)}

    def _generate_index_recommendations(
        self, stats: List[Dict], indexes: List[Dict]
    ) -> List[str]:
        """Generate index recommendations based on statistics."""
        recommendations = []

        # Check for columns with high cardinality but no indexes
        indexed_columns = set()
        for index in indexes:
            # Extract column names from index definition
            indexdef = index.get("indexdef", "")
            # Simple parsing - this could be improved
            if "ON" in indexdef:
                parts = indexdef.split("ON")[1].split("(")
                if len(parts) > 1:
                    cols = parts[1].split(")")[0]
                    for col in cols.split(","):
                        indexed_columns.add(col.strip())

        for stat in stats:
            column = stat.get("attname", "")
            n_distinct = stat.get("n_distinct", 0)
            correlation = stat.get("correlation", 0)

            # Recommend indexes for high cardinality columns
            if (
                isinstance(n_distinct, (int, float))
                and n_distinct > 100
                and column not in indexed_columns
            ):
                recommendations.append(
                    f"Consider adding index on {column} (high cardinality: {n_distinct})"
                )

            # Recommend indexes for low correlation columns
            if (
                isinstance(correlation, (int, float))
                and abs(correlation) < 0.1
                and column not in indexed_columns
            ):
                recommendations.append(
                    f"Consider adding index on {column} (low correlation: {correlation})"
                )

        return recommendations

    async def get_slow_queries_analysis(self, limit: int = 10) -> Dict:
        """Analyze slow queries from database logs."""
        try:
            # This would typically query pg_stat_statements
            # For now, return a placeholder
            return {
                "message": "Slow query analysis requires pg_stat_statements extension",
                "suggestions": [
                    "Enable pg_stat_statements extension for detailed query analysis",
                    "Monitor query execution times in application logs",
                    "Use EXPLAIN ANALYZE for specific slow queries",
                ],
            }
        except Exception as e:
            logger.error(f"Error analyzing slow queries: {e}")
            return {"error": str(e)}

    async def suggest_indexes(
        self, table_name: str, query_patterns: List[str]
    ) -> List[str]:
        """Suggest indexes based on query patterns."""
        suggestions = []

        for pattern in query_patterns:
            pattern_upper = pattern.upper()

            # Simple pattern matching for common query types
            if "WHERE" in pattern_upper:
                # Extract WHERE conditions
                where_part = pattern_upper.split("WHERE")[1].split("ORDER BY")[0]

                # Look for equality conditions
                if "=" in where_part:
                    suggestions.append(
                        f"Consider index on columns used in WHERE = conditions"
                    )

                # Look for range conditions
                if any(op in where_part for op in ["<", ">", "<=", ">="]):
                    suggestions.append(
                        f"Consider index on columns used in range conditions"
                    )

            if "ORDER BY" in pattern_upper:
                suggestions.append(
                    f"Consider index on ORDER BY columns for better sorting performance"
                )

            if "GROUP BY" in pattern_upper:
                suggestions.append(
                    f"Consider index on GROUP BY columns for better aggregation performance"
                )

        return list(set(suggestions))  # Remove duplicates


async def optimize_query(
    session: AsyncSession, query: str, params: Optional[Dict] = None
) -> Dict:
    """Convenience function to optimize a single query."""
    optimizer = QueryOptimizer(session)
    return await optimizer.explain_query(query, params)
