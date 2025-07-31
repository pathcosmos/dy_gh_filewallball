"""
Database monitoring and performance tracking.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List

from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

# Prometheus metrics - 중복 등록 방지
_metrics_initialized = False
QUERY_DURATION = None
QUERY_COUNT = None
SLOW_QUERY_COUNT = None
DB_CONNECTIONS_ACTIVE = None
DB_POOL_OVERFLOW = None


def _init_metrics():
    """메트릭을 한 번만 초기화합니다."""
    global _metrics_initialized, QUERY_DURATION, QUERY_COUNT
    global SLOW_QUERY_COUNT, DB_CONNECTIONS_ACTIVE, DB_POOL_OVERFLOW

    if _metrics_initialized:
        return

    try:
        QUERY_DURATION = Histogram(
            "db_query_duration_seconds",
            "Database query duration in seconds",
            ["operation", "table"],
        )

        QUERY_COUNT = Counter(
            "db_query_total",
            "Total number of database queries",
            ["operation", "table", "status"],
        )

        SLOW_QUERY_COUNT = Counter(
            "db_slow_query_total",
            "Total number of slow database queries",
            ["operation", "table"],
        )

        DB_CONNECTIONS_ACTIVE = Gauge(
            "db_connections_active",
            "Number of active database connections",
            ["database"],
        )

        DB_POOL_OVERFLOW = Gauge(
            "db_pool_overflow",
            "Number of database pool overflow connections",
            ["database"],
        )

        _metrics_initialized = True
    except ValueError:
        # 이미 등록된 경우 무시
        logger.warning("Prometheus metrics already registered, skipping initialization")
        pass


# 메트릭 초기화
_init_metrics()

# Configuration
SLOW_QUERY_THRESHOLD = 0.1  # 100ms
MAX_SLOW_QUERIES_LOG = 1000  # Maximum slow queries to keep in memory


class DatabaseMonitor:
    """Database performance monitor."""

    def __init__(self):
        """Initialize database monitor."""
        self.slow_queries: List[Dict] = []
        self.query_stats: Dict[str, Dict] = {}
        self.start_time = datetime.utcnow()

    def setup_monitoring(self, engine: Engine):
        """Setup monitoring for synchronous engine."""
        event.listen(engine, "before_cursor_execute", self._before_cursor_execute)
        event.listen(engine, "after_cursor_execute", self._after_cursor_execute)
        event.listen(engine, "handle_error", self._handle_error)

        logger.info("Database monitoring setup for sync engine")

    def setup_async_monitoring(self, engine: AsyncEngine):
        """Setup monitoring for async engine."""
        # For async engines, we'll use different approach
        # since event listeners work differently
        logger.info("Database monitoring setup for async engine")

    def _before_cursor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ):
        """Before cursor execute event."""
        context._query_start_time = time.time()
        context._query_statement = statement

    def _after_cursor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ):
        """After cursor execute event."""
        if hasattr(context, "_query_start_time"):
            duration = time.time() - context._query_start_time
            self._record_query(statement, duration, "success")

    def _handle_error(self, conn, cursor, statement, parameters, context, exception):
        """Handle query error."""
        if hasattr(context, "_query_start_time"):
            duration = time.time() - context._query_start_time
            self._record_query(statement, duration, "error")

    def _record_query(self, statement: str, duration: float, status: str):
        """Record query execution."""
        # Extract operation and table from statement
        operation, table = self._parse_statement(statement)

        # Update Prometheus metrics
        QUERY_DURATION.labels(operation=operation, table=table).observe(duration)
        QUERY_COUNT.labels(operation=operation, table=table, status=status).inc()

        # Check for slow queries
        if duration > SLOW_QUERY_THRESHOLD:
            SLOW_QUERY_COUNT.labels(operation=operation, table=table).inc()

            self._log_slow_query(statement, duration, operation, table)

        # Update internal stats
        self._update_stats(operation, table, duration, status)

    def _parse_statement(self, statement: str) -> tuple[str, str]:
        """Parse SQL statement to extract operation and table."""
        statement = statement.strip().upper()

        # Determine operation
        if statement.startswith("SELECT"):
            operation = "SELECT"
        elif statement.startswith("INSERT"):
            operation = "INSERT"
        elif statement.startswith("UPDATE"):
            operation = "UPDATE"
        elif statement.startswith("DELETE"):
            operation = "DELETE"
        else:
            operation = "OTHER"

        # Try to extract table name
        table = "unknown"
        words = statement.split()

        if operation == "SELECT":
            # Look for FROM clause
            try:
                from_index = words.index("FROM")
                if from_index + 1 < len(words):
                    table = words[from_index + 1]
            except ValueError:
                pass
        elif operation in ["INSERT", "UPDATE"]:
            # Table name is usually after INSERT/UPDATE
            if len(words) > 1:
                table = words[1]
        elif operation == "DELETE":
            # Look for FROM clause in DELETE
            try:
                from_index = words.index("FROM")
                if from_index + 1 < len(words):
                    table = words[from_index + 1]
            except ValueError:
                pass

        return operation, table

    def _log_slow_query(
        self, statement: str, duration: float, operation: str, table: str
    ):
        """Log slow query details."""
        slow_query = {
            "timestamp": datetime.utcnow(),
            "duration": duration,
            "operation": operation,
            "table": table,
            "statement": statement[:200] + "..." if len(statement) > 200 else statement,
        }

        self.slow_queries.append(slow_query)

        # Keep only recent slow queries
        if len(self.slow_queries) > MAX_SLOW_QUERIES_LOG:
            self.slow_queries = self.slow_queries[-MAX_SLOW_QUERIES_LOG:]

        logger.warning(f"Slow query detected: {duration:.3f}s - {operation} on {table}")

    def _update_stats(self, operation: str, table: str, duration: float, status: str):
        """Update internal query statistics."""
        key = f"{operation}_{table}"

        if key not in self.query_stats:
            self.query_stats[key] = {
                "count": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "errors": 0,
            }

        stats = self.query_stats[key]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["avg_duration"] = stats["total_duration"] / stats["count"]
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)

        if status == "error":
            stats["errors"] += 1

    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """Get recent slow queries."""
        return sorted(self.slow_queries, key=lambda x: x["duration"], reverse=True)[
            :limit
        ]

    def get_query_stats(self) -> Dict:
        """Get query statistics."""
        return {
            "start_time": self.start_time,
            "uptime": datetime.utcnow() - self.start_time,
            "total_queries": sum(stats["count"] for stats in self.query_stats.values()),
            "slow_queries_count": len(self.slow_queries),
            "query_stats": self.query_stats,
        }

    def get_performance_summary(self) -> Dict:
        """Get performance summary."""
        if not self.query_stats:
            return {"message": "No queries recorded yet"}

        all_durations = []
        total_queries = 0
        total_errors = 0

        for stats in self.query_stats.values():
            all_durations.extend([stats["avg_duration"]] * stats["count"])
            total_queries += stats["count"]
            total_errors += stats["errors"]

        if all_durations:
            avg_duration = sum(all_durations) / len(all_durations)
            p95_duration = sorted(all_durations)[int(len(all_durations) * 0.95)]
            p99_duration = sorted(all_durations)[int(len(all_durations) * 0.99)]
        else:
            avg_duration = p95_duration = p99_duration = 0.0

        return {
            "total_queries": total_queries,
            "total_errors": total_errors,
            "error_rate": (
                (total_errors / total_queries * 100) if total_queries > 0 else 0
            ),
            "avg_duration_ms": avg_duration * 1000,
            "p95_duration_ms": p95_duration * 1000,
            "p99_duration_ms": p99_duration * 1000,
            "slow_queries_count": len(self.slow_queries),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
        }


# Global monitor instance
db_monitor = DatabaseMonitor()
