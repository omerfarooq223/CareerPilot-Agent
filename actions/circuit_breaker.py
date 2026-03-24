"""Circuit Breaker pattern implementation for external API calls."""

import time
import threading
from enum import Enum
from typing import Callable, Any, Optional
from loguru import logger

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        with self._lock:
            self._before_call()
            
            if self.state == CircuitState.OPEN:
                raise Exception(f"Circuit breaker '{self.name}' is OPEN. Request rejected.")

        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                self._on_success()
            return result
        except self.expected_exceptions as e:
            with self._lock:
                self._on_failure(e)
            raise

    def _before_call(self):
        if self.state == CircuitState.OPEN and self.last_failure_time:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}' moving to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.success(f"Circuit breaker '{self.name}' closing after successful test call")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def _on_failure(self, exception: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(f"Circuit breaker '{self.name}' failure {self.failure_count}/{self.failure_threshold}: {exception}")
        
        if self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit breaker '{self.name}' moving to OPEN state")
            self.state = CircuitState.OPEN

def circuit_breaker(name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
    """Decorator version of the circuit breaker."""
    cb = CircuitBreaker(name, failure_threshold, recovery_timeout)
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        return wrapper
    return decorator
