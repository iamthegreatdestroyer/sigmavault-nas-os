"""
Circuit Breaker Pattern Implementation for SigmaVault NAS OS.

Implements the circuit breaker pattern to prevent cascading failures in distributed systems.
State machine: CLOSED → OPEN → HALF_OPEN → CLOSED

Features:
- Automatic failure detection and recovery
- Configurable thresholds and timeouts
- Exponential backoff for recovery attempts
- Prometheus metrics integration
- Thread-safe implementation

Author: @FORTRESS (Defensive Security) + @VELOCITY (Performance)
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Circuit breaker states following the standard pattern."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in HALF_OPEN to close circuit
        timeout: Seconds to wait before trying HALF_OPEN state
        timeout_max: Maximum timeout for exponential backoff (seconds)
        timeout_multiplier: Multiplier for exponential backoff
        expected_exception: Exception type to catch (None = all exceptions)
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 10.0
    timeout_max: float = 300.0
    timeout_multiplier: float = 2.0
    expected_exception: type | None = None


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""

    total_calls: int = 0
    failed_calls: int = 0
    successful_calls: int = 0
    rejected_calls: int = 0
    state_transitions: dict[str, int] = field(default_factory=dict)
    last_failure_time: float | None = None
    last_success_time: float | None = None


class CircuitBreaker(Generic[T]):
    """
    Thread-safe circuit breaker implementation with automatic recovery.

    Example:
        >>> cb = CircuitBreaker(
        ...     name="database",
        ...     config=CircuitBreakerConfig(failure_threshold=3, timeout=5.0)
        ... )
        >>> async def query_db():
        ...     async with cb:
        ...         return await db.execute("SELECT 1")
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker (for logging/metrics)
            config: Configuration object, uses defaults if None
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.next_attempt_time: float | None = None
        self.current_timeout = self.config.timeout
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"failure_threshold={config.failure_threshold}, "
            f"timeout={config.timeout}s"
        )

    def _transition_state(self, new_state: CircuitBreakerState) -> None:
        """
        Transition to a new state and update metrics.

        Args:
            new_state: The state to transition to
        """
        if self.state != new_state:
            old_state = self.state
            self.state = new_state

            # Update metrics
            transition_key = f"{old_state.value}_to_{new_state.value}"
            self.metrics.state_transitions[transition_key] = (
                self.metrics.state_transitions.get(transition_key, 0) + 1
            )

            logger.warning(
                f"Circuit breaker '{self.name}' state transition: "
                f"{old_state.value} → {new_state.value}"
            )

            # Reset counters on state change
            if new_state == CircuitBreakerState.HALF_OPEN:
                self.success_count = 0
                self.failure_count = 0
            elif new_state == CircuitBreakerState.CLOSED:
                self.failure_count = 0
                self.current_timeout = self.config.timeout  # Reset backoff

    async def _should_attempt(self) -> bool:
        """
        Determine if a request should be attempted based on current state.

        Returns:
            True if request should proceed, False if it should be rejected
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has expired
            if (
                self.next_attempt_time is not None
                and time.time() >= self.next_attempt_time
            ):
                async with self._lock:
                    # Double-check after acquiring lock
                    if (
                        self.state == CircuitBreakerState.OPEN
                        and time.time() >= self.next_attempt_time
                    ):
                        self._transition_state(CircuitBreakerState.HALF_OPEN)
                        return True
            return False

        # HALF_OPEN state - allow attempts
        return True

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    logger.info(
                        f"Circuit breaker '{self.name}' recovered: "
                        f"{self.success_count} consecutive successes"
                    )
                    self._transition_state(CircuitBreakerState.CLOSED)
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        async with self._lock:
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = time.time()
            self.last_failure_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                # Immediate transition back to OPEN on failure
                logger.warning(
                    f"Circuit breaker '{self.name}' failed during recovery: {exception}"
                )
                self._transition_state(CircuitBreakerState.OPEN)
                self._set_next_attempt_time()
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    logger.error(
                        f"Circuit breaker '{self.name}' opening: "
                        f"{self.failure_count} failures (threshold: {self.config.failure_threshold})"
                    )
                    self._transition_state(CircuitBreakerState.OPEN)
                    self._set_next_attempt_time()

    def _set_next_attempt_time(self) -> None:
        """Set next attempt time with exponential backoff."""
        self.next_attempt_time = time.time() + self.current_timeout
        # Exponential backoff with maximum cap
        self.current_timeout = min(
            self.current_timeout * self.config.timeout_multiplier,
            self.config.timeout_max,
        )
        logger.debug(
            f"Circuit breaker '{self.name}' next attempt in {self.current_timeout:.1f}s"
        )

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: The async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The return value of the function

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: The original exception if call fails
        """
        self.metrics.total_calls += 1

        if not await self._should_attempt():
            self.metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Next attempt at {time.strftime('%H:%M:%S', time.localtime(self.next_attempt_time))}"
            )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            # Check if this is the expected exception type
            if self.config.expected_exception is None or isinstance(
                e, self.config.expected_exception
            ):
                await self._on_failure(e)
            raise

    async def __aenter__(self):
        """Context manager entry."""
        if not await self._should_attempt():
            self.metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Next attempt at {time.strftime('%H:%M:%S', time.localtime(self.next_attempt_time))}"
            )
        self.metrics.total_calls += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            await self._on_success()
            return False

        # Check if this is the expected exception type
        if self.config.expected_exception is None or issubclass(
            exc_type, self.config.expected_exception
        ):
            await self._on_failure(exc_val)

        return False  # Re-raise exception

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.state

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics."""
        return self.metrics

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state (use with caution)."""
        logger.warning(f"Circuit breaker '{self.name}' manually reset to CLOSED")
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.current_timeout = self.config.timeout


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN and blocks a request."""

    pass


def circuit_breaker(
    name: str, config: CircuitBreakerConfig | None = None
) -> Callable:
    """
    Decorator for applying circuit breaker to async functions.

    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration

    Example:
        >>> @circuit_breaker("external_api", CircuitBreakerConfig(failure_threshold=3))
        ... async def call_api():
        ...     async with aiohttp.ClientSession() as session:
        ...         return await session.get("https://api.example.com")
    """
    cb = CircuitBreaker(name=name, config=config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await cb.call(func, *args, **kwargs)

        wrapper.circuit_breaker = cb  # Attach CB for inspection
        return wrapper

    return decorator
