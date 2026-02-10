"""
Unit tests for the Agent Recovery module.

Tests cover:
- Circuit breaker state management
- Circuit state transitions
- Agent recovery monitoring

ACTUAL API (discovered via introspection):
- AgentRecovery: start_monitoring/stop_monitoring (sync), record_success, record_failure, get_circuit
- CircuitBreaker: to_dict, can_execute, record_success, record_failure (no reset method)
"""

from unittest.mock import MagicMock

import pytest

from engined.agents.recovery import (
    AgentRecovery,
    CircuitBreaker,
    CircuitState,
)


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_circuit_states_defined(self):
        """Test all circuit states are defined."""
        assert CircuitState.CLOSED is not None
        assert CircuitState.OPEN is not None
        assert CircuitState.HALF_OPEN is not None

    def test_circuit_state_values(self):
        """Test circuit state values."""
        states = {CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN}
        assert len(states) == 3


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.fixture
    def circuit(self):
        """Create a circuit breaker for testing.
        
        CircuitBreaker(agent_id, failure_threshold=5, recovery_timeout=30.0,
                       half_open_max_calls=3)
        """
        return CircuitBreaker(
            agent_id="test-agent",
            failure_threshold=3,
            recovery_timeout=30.0,
            half_open_max_calls=1
        )

    def test_circuit_initial_state(self, circuit):
        """Test circuit starts in closed state."""
        assert circuit.state == CircuitState.CLOSED

    def test_circuit_agent_id(self, circuit):
        """Test circuit has agent_id."""
        assert circuit.agent_id == "test-agent"

    def test_record_success(self, circuit):
        """Test recording a success."""
        circuit.record_success()
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    def test_record_failure_below_threshold(self, circuit):
        """Test failures below threshold keep circuit closed."""
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.failure_count == 2
        assert circuit.state == CircuitState.CLOSED

    def test_record_failure_at_threshold(self, circuit):
        """Test circuit opens at failure threshold."""
        for _ in range(3):
            circuit.record_failure()
        assert circuit.state == CircuitState.OPEN

    def test_circuit_to_dict(self, circuit):
        """Test circuit serializes to dictionary."""
        d = circuit.to_dict()
        assert "state" in d
        assert "failure_count" in d
        assert "agent_id" in d
        assert d["state"] == "closed"
        assert d["agent_id"] == "test-agent"

    def test_circuit_can_execute_when_closed(self, circuit):
        """Test can execute when circuit is closed."""
        assert circuit.can_execute() is True

    def test_circuit_cannot_execute_when_open(self, circuit):
        """Test cannot execute when circuit is open."""
        for _ in range(3):
            circuit.record_failure()
        assert circuit.state == CircuitState.OPEN
        assert circuit.can_execute() is False

    def test_success_resets_failure_count(self, circuit):
        """Test success resets failure count."""
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.failure_count == 2
        circuit.record_success()
        assert circuit.failure_count == 0


class TestAgentRecovery:
    """Tests for AgentRecovery class.
    
    AgentRecovery(swarm, check_interval=5.0, max_restart_attempts=3, restart_cooldown=60.0)
    Methods: start_monitoring (ASYNC), stop_monitoring (ASYNC), record_success, record_failure, 
             get_circuit, get_status, get_health_score, get_all_health_scores, can_assign_task
    """

    @pytest.fixture
    def mock_swarm(self):
        """Create a mock AgentSwarm for testing."""
        swarm = MagicMock()
        swarm.get_agents = MagicMock(return_value={"agent-001": MagicMock()})
        return swarm

    @pytest.fixture
    async def recovery(self, mock_swarm):
        """Create an agent recovery manager for testing."""
        recovery = AgentRecovery(
            swarm=mock_swarm,
            check_interval=1.0,
            max_restart_attempts=3,
        )
        await recovery.start_monitoring()
        yield recovery
        await recovery.stop_monitoring()

    def test_recovery_creation(self, mock_swarm):
        """Test recovery manager is created."""
        recovery = AgentRecovery(swarm=mock_swarm)
        assert recovery is not None

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, mock_swarm):
        """Test monitoring can start and stop."""
        recovery = AgentRecovery(swarm=mock_swarm)
        await recovery.start_monitoring()
        await recovery.stop_monitoring()
        # Should not raise

    @pytest.mark.asyncio
    async def test_get_circuit(self, recovery):
        """Test getting circuit breaker for agent."""
        circuit = recovery.get_circuit("agent-001")
        assert circuit is not None
        assert isinstance(circuit, CircuitBreaker)

    @pytest.mark.asyncio
    async def test_record_success(self, recovery):
        """Test recording agent success."""
        recovery.record_success("agent-001")
        circuit = recovery.get_circuit("agent-001")
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_record_failure(self, recovery):
        """Test recording agent failure."""
        recovery.record_failure("agent-001")
        circuit = recovery.get_circuit("agent-001")
        assert circuit.failure_count == 1

    @pytest.mark.asyncio
    async def test_get_status(self, recovery):
        """Test get_status returns correct structure."""
        status = recovery.get_status()
        assert "monitoring_active" in status
        assert "total_circuits" in status
        assert "open_circuits" in status
        assert "circuit_states" in status

    @pytest.mark.asyncio
    async def test_get_health_score(self, recovery):
        """Test getting health score for agent."""
        score = recovery.get_health_score("agent-001")
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_get_all_health_scores(self, recovery):
        """Test getting all health scores."""
        scores = recovery.get_all_health_scores()
        assert isinstance(scores, dict)

    @pytest.mark.asyncio
    async def test_can_assign_task(self, recovery):
        """Test checking if task can be assigned to agent."""
        # Should return True for healthy agent with closed circuit
        result = recovery.can_assign_task("agent-001")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_multiple_failures_opens_circuit(self, recovery):
        """Test multiple failures opens the circuit."""
        # Default failure_threshold is 5
        for _ in range(5):
            recovery.record_failure("agent-001")
        circuit = recovery.get_circuit("agent-001")
        assert circuit.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_state_tracking(self, recovery):
        """Test circuit states are tracked in status."""
        status = recovery.get_status()
        circuit_states = status.get("circuit_states", {})
        assert isinstance(circuit_states, dict)
