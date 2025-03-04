"""Monitoring utilities for tracking API calls and performance metrics."""
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import json
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@dataclass
class APIMetrics:
    """Metrics for API calls."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latencies: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.successful_calls / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def average_latency(self) -> float:
        """Calculate average latency."""
        return self.total_latency / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def p95_latency(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

class MetricsRegistry:
    """Registry to track metrics for different components."""
    _instance = None
    
    def __init__(self):
        self.metrics: Dict[str, APIMetrics] = defaultdict(APIMetrics)
        self.start_time = time.time()
        
    @asynccontextmanager
    async def track_operation(self, operation_name: str):
        """Async context manager to track operation metrics."""
        start_time = time.time()
        success = True
        error_type = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_type = e.__class__.__name__
            raise
        finally:
            latency = time.time() - start_time
            self.record_api_call(operation_name, success, latency, error_type)
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MetricsRegistry()
        return cls._instance
    
    def record_api_call(self, 
                       component: str, 
                       success: bool, 
                       latency: float, 
                       error_type: Optional[str] = None):
        """Record an API call."""
        metrics = self.metrics[component]
        metrics.total_calls += 1
        metrics.total_latency += latency
        metrics.latencies.append(latency)
        
        if success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1
            if error_type:
                metrics.error_counts[error_type] += 1
    
    def get_metrics(self, component: str) -> Dict[str, Any]:
        """Get metrics for a component."""
        metrics = self.metrics[component]
        return {
            "total_calls": metrics.total_calls,
            "success_rate": metrics.success_rate,
            "avg_latency": metrics.average_latency,
            "p95_latency": metrics.p95_latency,
            "error_counts": dict(metrics.error_counts)
        }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all components."""
        return {
            component: self.get_metrics(component)
            for component in self.metrics
        }

def with_metrics(component: str):
    """Decorator to track metrics for a function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            registry = MetricsRegistry.get_instance()
            
            try:
                result = func(*args, **kwargs)
                latency = time.time() - start_time
                registry.record_api_call(component, True, latency)
                return result
            except Exception as e:
                latency = time.time() - start_time
                registry.record_api_call(
                    component, 
                    False, 
                    latency, 
                    error_type=e.__class__.__name__
                )
                raise
        return wrapper
    return decorator

# Structured logging
class StructuredLogger:
    """Logger that outputs structured JSON logs."""
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
    
    def _log(self, level: str, message: str, **kwargs):
        """Log a message with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            **kwargs
        }
        self.logger.log(
            getattr(logging, level.upper()),
            json.dumps(log_data)
        )
    
    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)
