"""
Comprehensive test suite for Circuit Breaker implementation.

Tests cover:
- State transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure threshold enforcement
- Success threshold for recovery
- Exponential backoff
- Context manager usage
- Decorator usage
- Metrics tracking
- Thread safety
- Edge cases

Author: @ECLIPSE (Testing & Verification)
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch

from engined.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    circuit_breaker,
)


@pytest.fixture
def cb_config():
    """Standard test configuration with low thresholds."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=0.1,  # Short timeout for fast tests
        timeout_max=1.0,
        timeout_multiplier=2.0,
    )


@pytest.fixture
def circuit_breaker_instance(cb_config):
    """Fresh circuit breaker instance for each test."""
    return CircuitBreaker(name="test_cb", config=cb_config)


class TestCircuitBreakerStateTransitions:
    """Test state machine transitions."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker_instance):
        """Circuit breaker should start in CLOSED state."""
        assert circuit_breaker_instance.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_transition_to_open_after_failures(self, circuit_breaker_instance):
        """Should transition to OPEN after failure threshold."""
        cb = circuit_breaker_instance

        # Create failing function
        async def failing_func():
            raise ValueError("Simulated failure")

        # Trigger failures
        for i in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Should be OPEN now
        assert cb.get_state() == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(self, circuit_breaker_instance):
        """Should transition to HALF_OPEN after timeout expires."""
        cb = circuit_breaker_instance

        # Trigger circuit to OPEN
        async def failing_func():
            raise ValueError("Failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Next call should transition to HALF_OPEN
        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_transition_to_closed_after_successes(self, circuit_breaker_instance):
        """Should transition to CLOSED after success threshold in HALF_OPEN."""
        cb = circuit_breaker_instance

        # Open the circuit
        async def failing_func():
            raise ValueError("Failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Succeed enough times to close
        async def success_func():
            return "success"

        await cb.call(success_func)  # First success -> HALF_OPEN
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN

        await cb.call(success_func)  # Second success -> CLOSED
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_returns_to_open_on_failure(self, circuit_breaker_instance):
        """HALF_OPEN should return to OPEN immediately on failure."""
        cb = circuit_breaker_instance

        # Open the circuit
        async def failing_func():
            raise ValueError("Failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Wait and transition to HALF_OPEN
        await asyncio.sleep(0.15)

        async def success_func():
            return "success"

        await cb.call(success_func)  # Transition to HALF_OPEN

        # Fail in HALF_OPEN
        with pytest.raises(ValueError):
            await cb.call(failing_func)

        # Should be back to OPEN
        assert cb.get_state() == CircuitBreakerState.OPEN


class TestCircuitBreakerRejection:
    """Test request rejection when circuit is OPEN."""

    @pytest.mark.asyncio
    async def test_rejects_calls_when_open(self, circuit_breaker_instance):
        """Should reject calls and raise CircuitBreakerOpenError when OPEN."""
        cb = circuit_breaker_instance

        # Open the circuit
        async def failing_func():
            raise ValueError("Failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Try to call - should be rejected
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(failing_func)

        assert "is OPEN" in str(exc_info.value)
        assert cb.metrics.rejected_calls == 1

    @pytest.mark.asyncio
    async def test_multiple_rejections_increment_metric(self, circuit_breaker_instance):
        """Multiple rejected calls should increment rejection counter."""
        cb = circuit_breaker_instance

        # Open the circuit
        async def failing_func():
            raise ValueError("Failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Multiple rejections
        for _ in range(5):
            with pytest.raises(CircuitBreakerOpenError):
                await cb.call(failing_func)

        assert cb.metrics.rejected_calls == 5


class TestCircuitBreakerContextManager:
    """Test context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_success(self, circuit_breaker_instance):
        """Context manager should handle successful operations."""
        cb = circuit_breaker_instance

        async with cb:
            result = "success"

        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.metrics.successful_calls == 1

    @pytest.mark.asyncio
    async def test_context_manager_failure(self, circuit_breaker_instance):
        """Context manager should handle failures and re-raise."""
        cb = circuit_breaker_instance

        for _ in range(3):
            with pytest.raises(ValueError):
                async with cb:
                    raise ValueError("Test failure")

        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.metrics.failed_calls == 3

    @pytest.mark.asyncio
    async def test_context_manager_rejects_when_open(self, circuit_breaker_instance):
        """Context manager should reject entry when circuit is OPEN."""
        cb = circuit_breaker_instance

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                async with cb:
                    raise ValueError("Failure")

        # Should reject context entry
        with pytest.raises(CircuitBreakerOpenError):
            async with cb:
                pass


class TestCircuitBreakerDecorator:
    """Test decorator functionality."""

    @pytest.mark.asyncio
    async def test_decorator_basic_usage(self):
        """Decorator should wrap function with circuit breaker."""
        call_count = 0

        @circuit_breaker("test_decorator", CircuitBreakerConfig(failure_threshold=2, timeout=0.1))
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 1

        # Access attached circuit breaker
        cb = test_func.circuit_breaker
        assert cb.metrics.successful_calls == 1

    @pytest.mark.asyncio
    async def test_decorator_with_failures(self):
        """Decorator should open circuit after failures."""

        @circuit_breaker("test_decorator_fail", CircuitBreakerConfig(failure_threshold=2, timeout=0.1))
        async def failing_func():
            raise ValueError("Failure")

        # Trigger failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Should reject next call
        with pytest.raises(CircuitBreakerOpenError):
            await failing_func()


class TestCircuitBreakerMetrics:
    """Test metrics tracking."""

    @pytest.mark.asyncio
    async def test_tracks_total_calls(self, circuit_breaker_instance):
        """Should track total number of calls."""
        cb = circuit_breaker_instance

        async def func():
            return "success"

        for _ in range(5):
            await cb.call(func)

        assert cb.metrics.total_calls == 5

    @pytest.mark.asyncio
    async def test_tracks_successful_calls(self, circuit_breaker_instance):
        """Should track successful calls."""
        cb = circuit_breaker_instance

        async def func():
            return "success"

        for _ in range(3):
            await cb.call(func)

        assert cb.metrics.successful_calls == 3
        assert cb.metrics.failed_calls == 0

    @pytest.mark.asyncio
    async def test_tracks_failed_calls(self, circuit_breaker_instance):
        """Should track failed calls."""
        cb = circuit_breaker_instance

        async def failing_func():
            raise ValueError("Failure")

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.metrics.failed_calls == 2
        assert cb.metrics.successful_calls == 0

    @pytest.mark.asyncio
    async def test_tracks_state_transitions(self, circuit_breaker_instance):
        """Should track state transitions in metrics."""
        cb = circuit_breaker_instance

        # Cause CLOSED -> OPEN transition
        async def failing_func():
            raise ValueError("Failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Check transition recorded
        assert "closed_to_open" in cb.metrics.state_transitions
        assert cb.metrics.state_transitions["closed_to_open"] == 1

    @pytest.mark.asyncio
    async def test_tracks_last_failure_time(self, circuit_breaker_instance):
        """Should track timestamp of last failure."""
        cb = circuit_breaker_instance

        async def failing_func():
            raise ValueError("Failure")

        before = time.time()
        with pytest.raises(ValueError):
            await cb.call(failing_func)
        after = time.time()

        assert cb.metrics.last_failure_time is not None
        assert before <= cb.metrics.last_failure_time <= after


class TestCircuitBreakerExponentialBackoff:
    """Test exponential backoff behavior."""

    @pytest.mark.asyncio
    async def test_timeout_increases_exponentially(self, circuit_breaker_instance):
        """Timeout should increase with each failure cycle."""
        cb = circuit_breaker_instance
        initial_timeout = cb.config.timeout

        async def failing_func():
            raise ValueError("Failure")

        # First failure cycle
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        first_timeout = cb.current_timeout
        assert first_timeout == initial_timeout * cb.config.timeout_multiplier

        # Wait and fail again
        await asyncio.sleep(initial_timeout * 1.1)

        # Try to recover but fail
        with pytest.raises(ValueError):
            await cb.call(failing_func)

        second_timeout = cb.current_timeout
        assert second_timeout == first_timeout * cb.config.timeout_multiplier

    @pytest.mark.asyncio
    async def test_timeout_respects_maximum(self):
        """Timeout should not exceed configured maximum."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout=1.0,
            timeout_max=5.0,
            timeout_multiplier=10.0,
        )
        cb = CircuitBreaker("test_max_timeout", config)

        async def failing_func():
            raise ValueError("Failure")

        # Multiple failure cycles
        for cycle in range(5):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

            # Wait for timeout
            await asyncio.sleep(cb.current_timeout + 0.1)

        # Timeout should be capped at maximum
        assert cb.current_timeout <= config.timeout_max

    @pytest.mark.asyncio
    async def test_timeout_resets_on_recovery(self, circuit_breaker_instance):
        """Timeout should reset to initial value when circuit closes."""
        cb = circuit_breaker_instance
        initial_timeout = cb.config.timeout

        async def failing_func():
            raise ValueError("Failure")

        async def success_func():
            return "success"

        # Open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Wait and recover
        await asyncio.sleep(0.15)
        await cb.call(success_func)  # HALF_OPEN
        await cb.call(success_func)  # CLOSED

        # Timeout should be reset
        assert cb.current_timeout == initial_timeout


class TestCircuitBreakerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_manual_reset(self, circuit_breaker_instance):
        """Manual reset should force circuit to CLOSED state."""
        cb = circuit_breaker_instance

        # Open circuit
        async def failing_func():
            raise ValueError("Failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Manual reset
        cb.reset()
        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """Circuit breaker should handle concurrent calls safely."""
        cb = CircuitBreaker(
            "concurrent_test",
            CircuitBreakerConfig(failure_threshold=10, timeout=0.1),
        )

        call_count = 0
        lock = asyncio.Lock()

        async def concurrent_func():
            nonlocal call_count
            async with lock:
                call_count += 1
            await asyncio.sleep(0.01)
            return "success"

        # Execute concurrent calls
        tasks = [cb.call(concurrent_func) for _ in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        assert call_count == 20
        assert cb.metrics.total_calls == 20

    @pytest.mark.asyncio
    async def test_expected_exception_filter(self):
        """Should only count specific exception types as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout=0.1,
            expected_exception=ValueError,
        )
        cb = CircuitBreaker("filtered_cb", config)

        # ValueError should count
        async def value_error_func():
            raise ValueError("Counted failure")

        with pytest.raises(ValueError):
            await cb.call(value_error_func)

        assert cb.failure_count == 1

        # TypeError should NOT count
        async def type_error_func():
            raise TypeError("Not counted")

        with pytest.raises(TypeError):
            await cb.call(type_error_func)

        # Failure count should not increase
        assert cb.failure_count == 1

    @pytest.mark.asyncio
    async def test_large_failure_threshold(self):
        """Circuit with large threshold should tolerate many failures."""
        config = CircuitBreakerConfig(failure_threshold=100)
        cb = CircuitBreaker("large_threshold", config)

        async def failing_func():
            raise ValueError("Failure")

        # 10 failures should not open circuit (threshold is 100)
        for _ in range(10):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Should still be closed
        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.failure_count == 10


class TestCircuitBreakerIntegration:
    """Integration tests simulating real-world scenarios."""

    @pytest.mark.asyncio
    async def test_database_connection_scenario(self):
        """Simulate database connection with intermittent failures."""
        cb = CircuitBreaker(
            "database",
            CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=0.1,
            ),
        )

        failure_count = 0
        success_after = 4  # Succeed after 4 calls

        async def db_query():
            nonlocal failure_count
            failure_count += 1
            if failure_count < success_after:
                raise ConnectionError("Database unavailable")
            return {"id": 1, "data": "result"}

        # First 3 calls fail -> circuit opens
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cb.call(db_query)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Calls are rejected while circuit is open
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(db_query)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Circuit tries to recover (HALF_OPEN)
        result = await cb.call(db_query)
        assert result == {"id": 1, "data": "result"}
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN

        # Another success closes circuit
        result = await cb.call(db_query)
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_api_rate_limiting_scenario(self):
        """Simulate external API with rate limiting."""
        cb = CircuitBreaker(
            "external_api",
            CircuitBreakerConfig(failure_threshold=5, timeout=0.2),
        )

        call_count = 0
        rate_limit = 3

        async def api_call():
            nonlocal call_count
            call_count += 1
            if call_count > rate_limit:
                raise Exception("Rate limit exceeded")
            return {"status": "ok"}

        # First 3 calls succeed
        for _ in range(3):
            result = await cb.call(api_call)
            assert result == {"status": "ok"}

        # Next calls hit rate limit
        for _ in range(5):
            with pytest.raises(Exception):
                await cb.call(api_call)

        # Circuit should be open
        assert cb.get_state() == CircuitBreakerState.OPEN

        # Reset call count (simulating rate limit reset)
        call_count = 0

        # Wait for circuit timeout
        await asyncio.sleep(0.25)

        # Should recover
        result = await cb.call(api_call)
        assert result == {"status": "ok"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=engined.core.circuit_breaker", "--cov-report=term-missing"])
