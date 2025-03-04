"""Circuit breaker implementation for API calls."""
import time
from enum import Enum
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit is broken, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5  # Number of failures before opening circuit
    reset_timeout: int = 60     # Seconds to wait before attempting reset
    half_open_calls: int = 3    # Number of successful calls to close circuit
    
class CircuitBreaker:
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successful_half_open_calls = 0
        self.last_failure_time = 0
        self.error_timestamps = []
        
    def record_failure(self):
        """Record a failure and update circuit state."""
        current_time = time.time()
        self.failures += 1
        self.error_timestamps.append(current_time)
        
        # Remove old errors outside our window
        self.error_timestamps = [t for t in self.error_timestamps 
                               if current_time - t <= 60]  # 1 minute window
        
        if (self.state == CircuitState.CLOSED and 
            len(self.error_timestamps) >= self.config.failure_threshold):
            logger.warning(f"Circuit breaker {self.name} opening due to {self.failures} failures")
            self.state = CircuitState.OPEN
            self.last_failure_time = current_time
            
    def record_success(self):
        """Record a success and potentially update circuit state."""
        if self.state == CircuitState.HALF_OPEN:
            self.successful_half_open_calls += 1
            if self.successful_half_open_calls >= self.config.half_open_calls:
                logger.info(f"Circuit breaker {self.name} closing after {self.successful_half_open_calls} successful calls")
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.successful_half_open_calls = 0
                self.error_timestamps = []
                
    def should_allow_request(self) -> bool:
        """Determine if a request should be allowed based on circuit state."""
        current_time = time.time()
        
        if self.state == CircuitState.OPEN:
            if current_time - self.last_failure_time >= self.config.reset_timeout:
                logger.info(f"Circuit breaker {self.name} entering half-open state")
                self.state = CircuitState.HALF_OPEN
                self.successful_half_open_calls = 0
            else:
                return False
                
        return True

class CircuitBreakerRegistry:
    """Registry to manage multiple circuit breakers."""
    _instance = None
    _breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CircuitBreakerRegistry()
        return cls._instance
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": breaker.state.value,
                "failures": breaker.failures,
                "error_rate": len(breaker.error_timestamps) / 60.0  # errors per second
            }
            for name, breaker in self._breakers.items()
        }

def with_circuit_breaker(name: str, fallback_value: Any = None):
    """Decorator to wrap a function with circuit breaker logic."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            breaker = CircuitBreakerRegistry.get_instance().get_breaker(name)
            
            if not breaker.should_allow_request():
                logger.warning(f"Circuit breaker {name} is open, failing fast")
                return fallback_value
                
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                logger.error(f"Circuit breaker {name} recorded failure: {str(e)}")
                raise
                
        return wrapper
    return decorator
