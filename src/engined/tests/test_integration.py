"""
Integration Tests for Circuit Breaker, Health Checks, and RPC Layer

Tests realistic failure scenarios including:
- Network timeouts
- Service unavailability
- Database connection loss
- Load testing
- Auto-healing validation
- Cross-component integration
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Dict

# Import components under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engined.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreakerOpenError
)
from engined.core.health import (
    HealthCheckManager,
    HealthCheckConfig,
    HealthStatus,
    ComponentType
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def circuit_breaker():
    """Create circuit breaker with fast failure for testing."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=0.5,  # Fast timeout for testing
        timeout_max=5.0  # Max timeout for testing
    )
    return CircuitBreaker("test_service", config)


@pytest.fixture
def health_manager():
    """Create health check manager for testing."""
    return HealthCheckManager(check_interval=1.0)


@pytest.fixture
async def mock_rpc_service():
    """Mock RPC service with configurable behavior."""
    class MockRPCService:
        def __init__(self):
            self.call_count = 0
            self.failure_mode = None  # 'timeout', 'unavailable', 'intermittent'
            self.failure_count = 0
            self.failure_threshold = 0
            
        async def call(self, method: str, params: dict = None):
            """Simulate RPC call with various failure modes."""
            self.call_count += 1
            
            if self.failure_mode == 'timeout':
                await asyncio.sleep(2.0)  # Simulate timeout
                raise TimeoutError(f"RPC timeout calling {method}")
                
            elif self.failure_mode == 'unavailable':
                raise ConnectionError("Service unavailable")
                
            elif self.failure_mode == 'intermittent':
                if self.call_count <= self.failure_threshold:
                    self.failure_count += 1
                    raise ConnectionError(f"Intermittent failure {self.call_count}")
                # After threshold, succeed
                return {"status": "success", "data": f"Response for {method}"}
                
            # Normal success
            return {"status": "success", "data": f"Response for {method}"}
            
        def reset(self):
            """Reset service state."""
            self.call_count = 0
            self.failure_count = 0
            
    return MockRPCService()


@pytest.fixture
async def mock_database():
    """Mock database with connection management."""
    class MockDatabase:
        def __init__(self):
            self.connected = True
            self.query_count = 0
            self.connection_attempts = 0
            
        async def query(self, sql: str):
            """Execute query."""
            if not self.connected:
                raise ConnectionError("Database not connected")
            self.query_count += 1
            return {"rows": 10, "query": sql}
            
        def disconnect(self):
            """Simulate connection loss."""
            self.connected = False
            
        async def reconnect(self):
            """Simulate reconnection."""
            self.connection_attempts += 1
            await asyncio.sleep(0.1)  # Simulate connection time
            self.connected = True
            
    return MockDatabase()


# ============================================================================
# Integration Test: Network Timeout Scenarios
# ============================================================================

class TestNetworkTimeoutScenarios:
    """Test circuit breaker behavior under network timeout conditions."""
    
    @pytest.mark.asyncio
    async def test_timeout_opens_circuit(self, circuit_breaker, mock_rpc_service):
        """Test that repeated timeouts open the circuit."""
        mock_rpc_service.failure_mode = 'timeout'
        
        # First 3 calls should timeout and count as failures
        for i in range(3):
            with pytest.raises((TimeoutError, CircuitBreakerOpenError)):
                async with circuit_breaker:
                    await asyncio.wait_for(
                        mock_rpc_service.call("test_method"),
                        timeout=0.5
                    )
        
        # Circuit should now be OPEN
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.metrics.failed_calls == 3
        
        # Next call should be rejected immediately
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            async with circuit_breaker:
                await mock_rpc_service.call("test_method")
        
        # Check that error message contains expected text
        assert "OPEN" in str(exc_info.value)
        assert circuit_breaker.metrics.rejected_calls == 1
    
    @pytest.mark.asyncio
    async def test_timeout_recovery_after_service_restoration(
        self, circuit_breaker, mock_rpc_service
    ):
        """Test recovery after service timeout is resolved."""
        # Open circuit with timeouts
        mock_rpc_service.failure_mode = 'timeout'
        for i in range(3):
            try:
                async with circuit_breaker:
                    await asyncio.wait_for(
                        mock_rpc_service.call("test_method"),
                        timeout=0.5
                    )
            except (TimeoutError, CircuitBreakerOpenError):
                pass
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Wait for timeout to transition to HALF_OPEN
        await asyncio.sleep(0.6)
        
        # Service is now healthy
        mock_rpc_service.failure_mode = None
        
        # Should transition to HALF_OPEN and succeed
        result = None
        async with circuit_breaker:
            result = await mock_rpc_service.call("recovery_test")
        
        assert result['status'] == 'success'
        
        # One more success should close circuit
        async with circuit_breaker:
            result = await mock_rpc_service.call("recovery_test_2")
        
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert result['status'] == 'success'


# ============================================================================
# Integration Test: Service Unavailability
# ============================================================================

class TestServiceUnavailability:
    """Test handling of service unavailability scenarios."""
    
    @pytest.mark.asyncio
    async def test_service_unavailable_with_auto_healing(
        self, health_manager, mock_rpc_service
    ):
        """Test health check detects unavailability and attempts healing."""
        service_healthy = False
        heal_attempts = []
        
        async def check_service_health():
            """Health check for RPC service."""
            from engined.core.health import HealthCheckResult, HealthStatus, ComponentType
            if not service_healthy:
                return HealthCheckResult(
                    component="rpc_service",
                    component_type=ComponentType.CUSTOM,
                    status=HealthStatus.UNHEALTHY,
                    message="Service unavailable"
                )
            return HealthCheckResult(
                component="rpc_service",
                component_type=ComponentType.CUSTOM,
                status=HealthStatus.HEALTHY,
                message="Service available"
            )
        
        async def heal_service():
            """Auto-heal function to restart service."""
            nonlocal service_healthy
            heal_attempts.append(time.time())
            await asyncio.sleep(0.1)  # Simulate restart
            service_healthy = True
        
        # Register health check with auto-healing
        health_manager.register_check(HealthCheckConfig(
            name="rpc_service",
            component_type=ComponentType.CUSTOM,
            check_fn=check_service_health,
            interval=1.0,
            timeout=2.0,
            auto_heal=True,
            heal_fn=heal_service
        ))
        
        # Start health monitoring
        await health_manager.start()
        
        # Wait for health check to detect failure and heal
        # First check happens immediately, second at t=1.0s, so wait >2s for healing
        await asyncio.sleep(2.5)
        
        # Verify healing was attempted
        assert len(heal_attempts) >= 1
        assert service_healthy is True
        
        # Get health status
        status = await health_manager.get_system_health()
        assert status.overall_status == HealthStatus.HEALTHY
        
        await health_manager.stop()
    
    @pytest.mark.asyncio
    async def test_intermittent_failures_with_circuit_breaker(
        self, circuit_breaker, mock_rpc_service
    ):
        """Test handling of intermittent failures."""
        # Configure intermittent failures: fail first 2 calls, then succeed
        mock_rpc_service.failure_mode = 'intermittent'
        mock_rpc_service.failure_threshold = 2
        
        results = []
        
        # Make calls through circuit breaker
        for i in range(5):
            try:
                async with circuit_breaker:
                    result = await mock_rpc_service.call(f"method_{i}")
                    results.append(('success', result))
            except CircuitBreakerOpenError:
                results.append(('rejected', None))
            except ConnectionError:
                results.append(('failed', None))
            
            await asyncio.sleep(0.1)
        
        # First 2 should fail, 3rd should fail (threshold reached, opens)
        # 4th should be rejected (circuit open)
        # After timeout, should transition to half-open and succeed
        
        assert circuit_breaker.metrics.failed_calls >= 2
        assert circuit_breaker.metrics.successful_calls >= 1


# ============================================================================
# Integration Test: Database Connection Loss
# ============================================================================

class TestDatabaseConnectionLoss:
    """Test circuit breaker protection for database operations."""
    
    @pytest.mark.asyncio
    async def test_database_connection_loss_and_recovery(
        self, circuit_breaker, mock_database
    ):
        """Test database connection loss with circuit breaker protection."""
        # First query should succeed
        async with circuit_breaker:
            result = await mock_database.query("SELECT * FROM users")
            assert result['rows'] == 10
        
        # Simulate connection loss
        mock_database.disconnect()
        
        # Next 3 queries should fail
        for i in range(3):
            try:
                async with circuit_breaker:
                    await mock_database.query(f"SELECT * FROM table_{i}")
            except (ConnectionError, CircuitBreakerOpenError):
                pass  # Expected
        
        # Circuit should be OPEN
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Reconnect database
        await mock_database.reconnect()
        assert mock_database.connected is True
        
        # Wait for circuit timeout
        await asyncio.sleep(0.6)
        
        # Should transition to HALF_OPEN and succeed
        async with circuit_breaker:
            result = await mock_database.query("SELECT 1")
            assert result['rows'] == 10
    
    @pytest.mark.asyncio
    async def test_database_auto_healing_integration(
        self, health_manager, mock_database
    ):
        """Test automatic database reconnection via health checks."""
        async def check_database():
            """Check database connectivity."""
            from engined.core.health import HealthCheckResult, HealthStatus, ComponentType
            try:
                await mock_database.query("SELECT 1")
                return HealthCheckResult(
                    component="database",
                    component_type=ComponentType.DATABASE,
                    status=HealthStatus.HEALTHY,
                    message="Database connected"
                )
            except ConnectionError:
                return HealthCheckResult(
                    component="database",
                    component_type=ComponentType.DATABASE,
                    status=HealthStatus.UNHEALTHY,
                    message="Database not connected"
                )
        
        async def heal_database():
            """Auto-reconnect database."""
            await mock_database.reconnect()
        
        health_manager.register_check(HealthCheckConfig(
            name="database",
            component_type=ComponentType.DATABASE,
            check_fn=check_database,
            interval=1.0,
            timeout=2.0,
            auto_heal=True,
            heal_fn=heal_database
        ))
        
        await health_manager.start()
        
        # Simulate connection loss
        mock_database.disconnect()
        
        # Wait for health check to detect and heal (need >2 check cycles)
        await asyncio.sleep(3.0)
        
        # Database should be reconnected
        assert mock_database.connected is True
        assert mock_database.connection_attempts >= 1
        
        await health_manager.stop()


# ============================================================================
# Integration Test: Load Testing
# ============================================================================

class TestLoadScenarios:
    """Test circuit breaker and health checks under load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_through_circuit_breaker(
        self, circuit_breaker, mock_rpc_service
    ):
        """Test circuit breaker handles concurrent requests correctly."""
        async def make_request(request_id: int):
            """Make single request through circuit breaker."""
            try:
                async with circuit_breaker:
                    result = await mock_rpc_service.call(f"method_{request_id}")
                    return ('success', request_id, result)
            except CircuitBreakerOpenError:
                return ('rejected', request_id, None)
            except Exception as e:
                return ('error', request_id, str(e))
        
        # Send 50 concurrent requests
        tasks = [make_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successes = [r for r in results if r[0] == 'success']
        rejections = [r for r in results if r[0] == 'rejected']
        errors = [r for r in results if r[0] == 'error']
        
        # All requests should succeed (service is healthy)
        assert len(successes) == 50
        assert len(rejections) == 0
        assert len(errors) == 0
        assert mock_rpc_service.call_count == 50
    
    @pytest.mark.asyncio
    async def test_load_with_partial_failures(
        self, circuit_breaker, mock_rpc_service
    ):
        """Test circuit breaker under load with intermittent failures."""
        # Configure intermittent failures (only first 2 fail, less than CB threshold of 3)
        mock_rpc_service.failure_mode = 'intermittent'
        mock_rpc_service.failure_threshold = 2  # First 2 fail, rest succeed
        
        async def make_request(request_id: int):
            """Make request with retry logic."""
            for attempt in range(3):
                try:
                    async with circuit_breaker:
                        result = await mock_rpc_service.call(f"method_{request_id}")
                        return ('success', request_id)
                except CircuitBreakerOpenError:
                    return ('rejected', request_id)
                except ConnectionError:
                    if attempt == 2:
                        return ('failed', request_id)
                    await asyncio.sleep(0.1)
        
        # Send 30 requests
        tasks = [make_request(i) for i in range(30)]
        results = await asyncio.gather(*tasks)
        
        successes = [r for r in results if r[0] == 'success']
        rejections = [r for r in results if r[0] == 'rejected']
        failures = [r for r in results if r[0] == 'failed']
        
        # Some should succeed (after threshold), some should fail
        assert len(successes) > 0
        assert circuit_breaker.metrics.total_calls > 0


# ============================================================================
# Integration Test: Cross-Component Integration
# ============================================================================

class TestCrossComponentIntegration:
    """Test integration between circuit breaker, health checks, and metrics."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_in_health_checks(
        self, health_manager, circuit_breaker
    ):
        """Test health checks can monitor circuit breaker state."""
        async def check_circuit_breaker_health():
            """Check if circuit breaker is healthy."""
            from engined.core.health import HealthCheckResult, HealthStatus, ComponentType
            if circuit_breaker.state == CircuitBreakerState.OPEN:
                raise RuntimeError("Circuit breaker is OPEN")
            
            metrics = circuit_breaker.get_metrics()
            failure_rate = (
                metrics.failed_calls / metrics.total_calls
                if metrics.total_calls > 0 else 0
            )
            
            if failure_rate > 0.5:
                raise RuntimeError(f"High failure rate: {failure_rate:.2%}")
            
            return HealthCheckResult(
                component="circuit_breaker",
                component_type=ComponentType.CIRCUIT_BREAKER,
                status=HealthStatus.HEALTHY,
                message=f"Circuit breaker {circuit_breaker.state.value}, failure rate: {failure_rate:.2%}"
            )
        
        health_manager.register_check(HealthCheckConfig(
            name="circuit_breaker",
            component_type=ComponentType.CIRCUIT_BREAKER,
            check_fn=check_circuit_breaker_health,
            interval=1.0,
            timeout=2.0
        ))
        
        await health_manager.start()
        await asyncio.sleep(1.5)
        
        status = await health_manager.get_system_health()
        assert 'circuit_breaker' in status.components
        
        cb_status = status.components['circuit_breaker']
        assert cb_status.status == HealthStatus.HEALTHY
        
        await health_manager.stop()
    
    @pytest.mark.asyncio
    async def test_end_to_end_failure_and_recovery(
        self, health_manager, circuit_breaker, mock_rpc_service
    ):
        """Test complete failure and recovery flow across all components."""
        recovery_events = []
        
        async def make_protected_call():
            """Make RPC call protected by circuit breaker."""
            async with circuit_breaker:
                return await mock_rpc_service.call("test_method")
        
        async def check_rpc_health():
            """Health check for RPC service."""
            from engined.core.health import HealthCheckResult, HealthStatus, ComponentType
            try:
                await make_protected_call()
                return HealthCheckResult(
                    component="rpc_service",
                    component_type=ComponentType.GRPC_SERVER,
                    status=HealthStatus.HEALTHY,
                    message="RPC service available"
                )
            except CircuitBreakerOpenError:
                return HealthCheckResult(
                    component="rpc_service",
                    component_type=ComponentType.GRPC_SERVER,
                    status=HealthStatus.UNHEALTHY,
                    message="Circuit breaker protecting service"
                )
            except Exception as e:
                return HealthCheckResult(
                    component="rpc_service",
                    component_type=ComponentType.GRPC_SERVER,
                    status=HealthStatus.UNHEALTHY,
                    message=f"RPC call failed: {e}"
                )
        
        async def heal_rpc():
            """Healing function to reset service."""
            mock_rpc_service.failure_mode = None
            recovery_events.append(('heal_attempted', time.time()))
        
        # Register health check
        health_manager.register_check(HealthCheckConfig(
            name="rpc_service",
            component_type=ComponentType.CUSTOM,
            check_fn=check_rpc_health,
            interval=1.0,
            timeout=2.0,
            auto_heal=True,
            heal_fn=heal_rpc
        ))
        
        await health_manager.start()
        
        # Phase 1: Service is healthy
        await asyncio.sleep(1.5)
        status = await health_manager.get_system_health()
        assert status.overall_status == HealthStatus.HEALTHY
        
        # Phase 2: Introduce failures to open circuit
        mock_rpc_service.failure_mode = 'unavailable'
        
        for i in range(3):
            try:
                await make_protected_call()
            except (ConnectionError, CircuitBreakerOpenError):
                pass
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Phase 3: Health check detects failure and heals
        await asyncio.sleep(2.0)
        
        # Healing should have been attempted
        assert len(recovery_events) >= 1
        
        # Phase 4: Wait for circuit to transition to HALF_OPEN
        await asyncio.sleep(1.0)
        
        # Phase 5: Service should recover
        await asyncio.sleep(1.5)
        final_status = await health_manager.get_system_health()
        
        # Circuit should eventually close as service is healthy
        assert circuit_breaker.state in [
            CircuitBreakerState.HALF_OPEN,
            CircuitBreakerState.CLOSED
        ]
        
        await health_manager.stop()


# ============================================================================
# Integration Test: Metrics Validation
# ============================================================================

class TestMetricsValidation:
    """Test that metrics are correctly tracked across components."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_accuracy(self, circuit_breaker):
        """Test circuit breaker metrics are accurate under various conditions."""
        mock_fn = AsyncMock()
        
        # Track expected values
        expected_total = 0
        expected_success = 0
        expected_failed = 0
        expected_rejected = 0
        
        # Make successful calls
        for i in range(10):
            mock_fn.return_value = f"success_{i}"
            async with circuit_breaker:
                await mock_fn()
            expected_total += 1
            expected_success += 1
        
        metrics = circuit_breaker.get_metrics()
        assert metrics.total_calls == expected_total
        assert metrics.successful_calls == expected_success
        
        # Make failing calls to open circuit
        mock_fn.side_effect = ConnectionError("Service down")
        for i in range(3):
            try:
                async with circuit_breaker:
                    await mock_fn()
            except (ConnectionError, CircuitBreakerOpenError):
                pass
            expected_total += 1
            expected_failed += 1
        
        # Circuit should be OPEN
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Try calls that will be rejected
        for i in range(5):
            try:
                async with circuit_breaker:
                    await mock_fn()
            except CircuitBreakerOpenError:
                expected_rejected += 1
        
        # Validate final metrics
        final_metrics = circuit_breaker.get_metrics()
        assert final_metrics.total_calls == expected_total
        assert final_metrics.successful_calls == expected_success
        assert final_metrics.failed_calls == expected_failed
        assert final_metrics.rejected_calls == expected_rejected
    
    @pytest.mark.asyncio
    async def test_health_check_metrics_tracking(self, health_manager):
        """Test health check metrics are tracked correctly."""
        check_count = 0
        
        async def tracked_check():
            """Health check that tracks invocations."""
            from engined.core.health import HealthCheckResult, HealthStatus, ComponentType
            nonlocal check_count
            check_count += 1
            return HealthCheckResult(
                component="tracked_check",
                component_type=ComponentType.CUSTOM,
                status=HealthStatus.HEALTHY,
                message=f"Check #{check_count}"
            )
        
        health_manager.register_check(HealthCheckConfig(
            name="tracked_check",
            component_type=ComponentType.CUSTOM,
            check_fn=tracked_check,
            interval=0.5,
            timeout=2.0
        ))
        
        await health_manager.start()
        await asyncio.sleep(2.5)
        await health_manager.stop()
        
        # Should have run approximately 5 times (2.5s / 0.5s interval)
        assert check_count >= 3
        
        status = await health_manager.get_system_health()
        assert 'tracked_check' in status.components


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestPerformanceBenchmarks:
    """Benchmark performance of integrated components."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_overhead(self, circuit_breaker):
        """Measure circuit breaker overhead on successful calls."""
        async def fast_operation():
            """Simulated fast operation."""
            return "success"
        
        # Warmup
        for _ in range(10):
            async with circuit_breaker:
                await fast_operation()
        
        # Benchmark
        iterations = 1000
        start_time = time.perf_counter()
        
        for _ in range(iterations):
            async with circuit_breaker:
                await fast_operation()
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_overhead = (total_time / iterations) * 1000  # Convert to ms
        
        # Circuit breaker overhead should be < 1ms per call
        assert avg_overhead < 1.0, f"Overhead too high: {avg_overhead:.3f}ms"
        
        print(f"\nCircuit breaker overhead: {avg_overhead:.3f}ms per call")
    
    @pytest.mark.asyncio
    async def test_health_check_parallel_execution(self, health_manager):
        """Test health checks run in parallel efficiently."""
        check_times = []
        
        async def slow_check(duration: float):
            """Health check with configurable duration."""
            start = time.perf_counter()
            await asyncio.sleep(duration)
            end = time.perf_counter()
            check_times.append(end - start)
            return {"duration": duration}
        
        # Register 5 checks, each taking 0.5s
        for i in range(5):
            health_manager.register_check(HealthCheckConfig(
                name=f"slow_check_{i}",
                component_type=ComponentType.CUSTOM,
                check_fn=lambda d=0.5: slow_check(d),
                interval=10.0,  # Don't auto-repeat
                timeout=2.0
            ))
        
        # Run all checks
        start_time = time.perf_counter()
        await health_manager.run_all_checks()
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        
        # If run in parallel, total time should be ~0.5s
        # If sequential, would be ~2.5s (5 * 0.5s)
        assert total_time < 1.0, f"Not parallel: {total_time:.2f}s"
        print(f"\n5 parallel health checks completed in: {total_time:.3f}s")


# ============================================================================
# Summary Test
# ============================================================================

@pytest.mark.asyncio
async def test_integration_suite_summary():
    """Summary test to validate all integration components work together."""
    # Create components
    cb = CircuitBreaker("integration_test", CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=1.0
    ))
    
    hm = HealthCheckManager(check_interval=1.0)
    
    # Register circuit breaker health check
    async def check_cb():
        from engined.core.health import HealthCheckResult, HealthStatus, ComponentType
        if cb.state == CircuitBreakerState.OPEN:
            raise RuntimeError("Circuit is open")
        return HealthCheckResult(
            component="circuit_breaker",
            component_type=ComponentType.CIRCUIT_BREAKER,
            status=HealthStatus.HEALTHY,
            message=f"Circuit breaker {cb.state.value}"
        )
    
    hm.register_check(HealthCheckConfig(
        name="circuit_breaker",
        component_type=ComponentType.CIRCUIT_BREAKER,
        check_fn=check_cb,
        interval=1.0,
        timeout=2.0
    ))
    
    await hm.start()
    
    # Wait for health check to run at least once
    await asyncio.sleep(1.5)
    
    # Make some successful calls
    mock = AsyncMock(return_value="success")
    for _ in range(5):
        async with cb:
            await mock()
    
    # Check health
    status = await hm.get_system_health()
    assert status.overall_status == HealthStatus.HEALTHY
    assert cb.metrics.successful_calls == 5
    
    await hm.stop()
    
    print("\n" + "="*60)
    print("INTEGRATION TEST SUITE SUMMARY")
    print("="*60)
    print(f"Circuit Breaker Metrics:")
    print(f"  Total Calls: {cb.metrics.total_calls}")
    print(f"  Successful: {cb.metrics.successful_calls}")
    print(f"  Failed: {cb.metrics.failed_calls}")
    print(f"  Rejected: {cb.metrics.rejected_calls}")
    print(f"  Current State: {cb.state.value}")
    print(f"\nHealth Status:")
    print(f"  Overall: {status.overall_status}")
    print(f"  Health Score: {status.health_score:.1f}/100")
    print(f"  Components Checked: {len(status.components)}")
    print("="*60)
    print("✅ ALL INTEGRATION TESTS READY")
    print("="*60)
