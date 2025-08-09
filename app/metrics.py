"""
Metrics collection - 단순화된 버전 (Prometheus 메트릭 대신 로깅)
"""

from app.utils.logging_config import get_logger
import time

logger = get_logger(__name__)


class MockCounter:
    def __init__(self, name):
        self.name = name
    
    def inc(self, value=1):
        logger.debug(f"Counter {self.name} incremented by {value}")


class MockGauge:
    def __init__(self, name):
        self.name = name
    
    def set(self, value):
        logger.debug(f"Gauge {self.name} set to {value}")
    
    def inc(self, value=1):
        logger.debug(f"Gauge {self.name} incremented by {value}")
    
    def dec(self, value=1):
        logger.debug(f"Gauge {self.name} decremented by {value}")


class MockHistogram:
    def __init__(self, name):
        self.name = name
    
    def observe(self, value):
        logger.debug(f"Histogram {self.name} observed {value}")
    
    def time(self):
        return MockTimer(self)


class MockTimer:
    def __init__(self, histogram):
        self.histogram = histogram
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.histogram.observe(duration)


# Mock metrics (단순한 로깅으로 대체)
active_connections_gauge = MockGauge("active_connections")
cache_hit_counter = MockCounter("cache_hits")
cache_miss_counter = MockCounter("cache_misses")
error_rate_counter = MockCounter("error_rate")
file_download_counter = MockCounter("file_downloads")
file_processing_duration = MockHistogram("file_processing_duration")
file_upload_counter = MockCounter("file_uploads")
file_upload_duration = MockHistogram("file_upload_duration")
file_upload_error_counter = MockCounter("file_upload_errors")