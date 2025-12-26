"""Circuit Breaker implementation for external API fault tolerance.

Implements the Circuit Breaker pattern to prevent cascading failures when
external services (Gmail API, Outlook API, Gemini) are unavailable.
"""

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Callable, Optional, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit Breaker for external service calls.
    
    States:
    - CLOSED: Normal operation. Failures are counted.
    - OPEN: After fail_max failures, circuit opens. All calls fail fast.
    - HALF_OPEN: After reset_timeout, one test call is allowed.
    
    Usage:
        gmail_breaker = CircuitBreaker(
            name="gmail",
            fail_max=5,
            reset_timeout=300,  # 5 minutes
            exclude=[TokenRefreshError]
        )
        
        @gmail_breaker
        def call_gmail_api():
            ...
    """
    
    def __init__(
        self,
        name: str,
        fail_max: int = 5,
        reset_timeout: int = 300,
        exclude: Optional[list[Type[Exception]]] = None,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit (for logging)
            fail_max: Number of failures before opening circuit
            reset_timeout: Seconds before attempting to close circuit
            exclude: Exception types that don't count as failures
        """
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.exclude = exclude or []
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, updating if needed."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if reset timeout has passed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.reset_timeout:
                        logger.info(f"[CircuitBreaker:{self.name}] Transitioning to HALF_OPEN after {elapsed:.0f}s")
                        self._state = CircuitState.HALF_OPEN
            return self._state
    
    def _record_success(self):
        """Record a successful call."""
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"[CircuitBreaker:{self.name}] Success in HALF_OPEN, closing circuit")
                self._state = CircuitState.CLOSED
    
    def _record_failure(self, exception: Exception):
        """Record a failed call."""
        # Check if this exception type should be excluded
        for exc_type in self.exclude:
            if isinstance(exception, exc_type):
                logger.debug(f"[CircuitBreaker:{self.name}] Excluding {type(exception).__name__} from failure count")
                return
        
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failed during test, reopen circuit
                logger.warning(f"[CircuitBreaker:{self.name}] Failed in HALF_OPEN, reopening circuit")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.fail_max:
                logger.warning(
                    f"[CircuitBreaker:{self.name}] Opening circuit after {self._failure_count} failures"
                )
                self._state = CircuitState.OPEN
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_state = self.state
            
            if current_state == CircuitState.OPEN:
                remaining = self.reset_timeout - (time.time() - (self._last_failure_time or 0))
                logger.warning(
                    f"[CircuitBreaker:{self.name}] Circuit OPEN, blocking call. "
                    f"Reset in {remaining:.0f}s"
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Service unavailable. Retry in {remaining:.0f}s."
                )
            
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure(e)
                raise
        
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs):
        """Call function with circuit breaker protection."""
        return self(func)(*args, **kwargs)
    
    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            logger.info(f"[CircuitBreaker:{self.name}] Manually reset to CLOSED")
    
    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "fail_max": self.fail_max,
            "last_failure": (
                datetime.fromtimestamp(self._last_failure_time, tz=timezone.utc).isoformat()
                if self._last_failure_time else None
            ),
            "reset_timeout": self.reset_timeout,
        }


# Pre-configured circuit breakers for external services
gmail_circuit_breaker = CircuitBreaker(
    name="gmail_api",
    fail_max=5,
    reset_timeout=300,  # 5 minutes
)

outlook_circuit_breaker = CircuitBreaker(
    name="outlook_api",
    fail_max=5,
    reset_timeout=300,
)

gemini_circuit_breaker = CircuitBreaker(
    name="gemini_api",
    fail_max=10,  # Higher threshold for AI calls
    reset_timeout=180,  # 3 minutes
)
