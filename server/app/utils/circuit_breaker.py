"""Circuit Breaker implementation for external API fault tolerance.

Implements the Circuit Breaker pattern to prevent cascading failures when
external services (Gmail API, Outlook API, Gemini) are unavailable.

Supports two modes:
- Redis-based (distributed): State shared across all workers/processes
- In-memory (fallback): Per-process state when Redis is unavailable
"""

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Callable, Optional, Type

from config.settings import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


def _get_redis() -> Optional[object]:
    """Get Redis client, returning None if unavailable."""
    try:
        from app import redis_client
        if redis_client:
            redis_client.ping()
            return redis_client
    except Exception:
        pass
    return None


class CircuitBreaker:
    """
    Distributed Circuit Breaker for external service calls.

    Uses Redis for cross-worker state coordination. Falls back to
    in-memory state if Redis is unavailable.

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
        self._redis_key = f"{settings.circuit_breaker_redis_prefix}{name}"

        # In-memory fallback state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()

    def _get_redis_state(self) -> Optional[dict]:
        """Read circuit breaker state from Redis."""
        redis_conn = _get_redis()
        if not redis_conn:
            return None
        try:
            data = redis_conn.get(self._redis_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"[CircuitBreaker:{self.name}] Redis read failed: {e}")
            return None

    def _set_redis_state(self, state: str, failure_count: int, last_failure_time: Optional[float]) -> bool:
        """Write circuit breaker state to Redis."""
        redis_conn = _get_redis()
        if not redis_conn:
            return False
        try:
            data = json.dumps({
                "state": state,
                "failure_count": failure_count,
                "last_failure_time": last_failure_time,
            })
            # TTL: keep state for 2x reset_timeout to allow natural expiry
            redis_conn.set(self._redis_key, data, ex=self.reset_timeout * 2)
            return True
        except Exception as e:
            logger.debug(f"[CircuitBreaker:{self.name}] Redis write failed: {e}")
            return False

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, updating if needed."""
        # Try Redis first
        redis_state = self._get_redis_state()
        if redis_state:
            current = CircuitState(redis_state["state"])
            last_failure = redis_state.get("last_failure_time")

            if current == CircuitState.OPEN and last_failure:
                elapsed = time.time() - last_failure
                if elapsed >= self.reset_timeout:
                    logger.info(
                        f"[CircuitBreaker:{self.name}] Transitioning to HALF_OPEN "
                        f"after {elapsed:.0f}s (Redis)"
                    )
                    self._set_redis_state(
                        CircuitState.HALF_OPEN.value,
                        redis_state["failure_count"],
                        last_failure,
                    )
                    return CircuitState.HALF_OPEN
            return current

        # Fallback to in-memory
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.reset_timeout:
                        logger.info(
                            f"[CircuitBreaker:{self.name}] Transitioning to HALF_OPEN "
                            f"after {elapsed:.0f}s (in-memory)"
                        )
                        self._state = CircuitState.HALF_OPEN
            return self._state

    def _record_success(self):
        """Record a successful call."""
        # Try Redis
        redis_state = self._get_redis_state()
        if redis_state:
            current = CircuitState(redis_state["state"])
            if current == CircuitState.HALF_OPEN:
                logger.info(f"[CircuitBreaker:{self.name}] Success in HALF_OPEN, closing circuit (Redis)")
            self._set_redis_state(CircuitState.CLOSED.value, 0, None)
            return

        # Fallback to in-memory
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
                logger.debug(
                    f"[CircuitBreaker:{self.name}] Excluding "
                    f"{type(exception).__name__} from failure count"
                )
                return

        now = time.time()

        # Try Redis
        redis_state = self._get_redis_state()
        if redis_state is not None:
            current = CircuitState(redis_state["state"])
            failure_count = redis_state.get("failure_count", 0) + 1

            if current == CircuitState.HALF_OPEN:
                logger.warning(
                    f"[CircuitBreaker:{self.name}] Failed in HALF_OPEN, "
                    f"reopening circuit (Redis)"
                )
                self._set_redis_state(CircuitState.OPEN.value, failure_count, now)
            elif failure_count >= self.fail_max:
                logger.warning(
                    f"[CircuitBreaker:{self.name}] Opening circuit after "
                    f"{failure_count} failures (Redis)"
                )
                self._set_redis_state(CircuitState.OPEN.value, failure_count, now)
            else:
                self._set_redis_state(current.value, failure_count, now)
            return

        # No Redis state found — initialize from in-memory or fresh
        # Fallback to in-memory
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = now

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"[CircuitBreaker:{self.name}] Failed in HALF_OPEN, reopening circuit"
                )
                self._state = CircuitState.OPEN
                # Also try to persist to Redis for other workers
                self._set_redis_state(CircuitState.OPEN.value, self._failure_count, now)
            elif self._failure_count >= self.fail_max:
                logger.warning(
                    f"[CircuitBreaker:{self.name}] Opening circuit after "
                    f"{self._failure_count} failures"
                )
                self._state = CircuitState.OPEN
                self._set_redis_state(CircuitState.OPEN.value, self._failure_count, now)

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_state = self.state

            if current_state == CircuitState.OPEN:
                # Calculate remaining time from either Redis or in-memory
                redis_state = self._get_redis_state()
                if redis_state and redis_state.get("last_failure_time"):
                    remaining = self.reset_timeout - (time.time() - redis_state["last_failure_time"])
                else:
                    remaining = self.reset_timeout - (time.time() - (self._last_failure_time or 0))

                logger.warning(
                    f"[CircuitBreaker:{self.name}] Circuit OPEN, blocking call. "
                    f"Reset in {max(remaining, 0):.0f}s"
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Service unavailable. Retry in {max(remaining, 0):.0f}s."
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
        # Reset Redis
        self._set_redis_state(CircuitState.CLOSED.value, 0, None)

        # Reset in-memory
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            logger.info(f"[CircuitBreaker:{self.name}] Manually reset to CLOSED")

    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        # Prefer Redis state
        redis_state = self._get_redis_state()
        if redis_state:
            last_failure = redis_state.get("last_failure_time")
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": redis_state.get("failure_count", 0),
                "fail_max": self.fail_max,
                "last_failure": (
                    datetime.fromtimestamp(last_failure, tz=timezone.utc).isoformat()
                    if last_failure else None
                ),
                "reset_timeout": self.reset_timeout,
                "backend": "redis",
            }

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
            "backend": "in_memory",
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
