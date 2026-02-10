"""
Unit tests for the Agent Swarm module.

Tests cover:
- Agent initialization and status
- Task creation and processing
- Swarm health metrics
- Agent selection algorithms
"""

import asyncio
from datetime import UTC, datetime

import pytest

from engined.agents.swarm import (
    AGENT_DEFINITIONS,
    Agent,
    AgentStatus,
    AgentSwarm,
    AgentTier,
    Task,
)

# ==============================================================================
# Agent Tests
# ==============================================================================


class TestAgent:
    """Tests for the Agent dataclass."""

    def test_agent_creation_defaults(self):
        """Test agent is created with correct defaults."""
        agent = Agent(
            agent_id="test-001",
            name="TENSOR",
            tier=AgentTier.CORE,
            specialty="Testing",
        )

        assert agent.agent_id == "test-001"
        assert agent.name == "TENSOR"
        assert agent.tier == AgentTier.CORE
        assert agent.specialty == "Testing"
        assert agent.status == AgentStatus.OFFLINE
        assert agent.tasks_completed == 0
        assert agent.tasks_failed == 0
        assert agent.current_task_id is None

    def test_agent_success_rate_no_tasks(self):
        """Test success rate is 1.0 when no tasks completed."""
        agent = Agent(
            agent_id="test-001",
            name="TEST",
            tier=AgentTier.CORE,
            specialty="Testing",
        )
        assert agent.success_rate == 1.0

    def test_agent_success_rate_with_tasks(self):
        """Test success rate calculation with completed and failed tasks."""
        agent = Agent(
            agent_id="test-001",
            name="TEST",
            tier=AgentTier.CORE,
            specialty="Testing",
            tasks_completed=80,
            tasks_failed=20,
        )
        assert agent.success_rate == 0.8

    def test_agent_success_rate_all_failed(self):
        """Test success rate is 0 when all tasks failed."""
        agent = Agent(
            agent_id="test-001",
            name="TEST",
            tier=AgentTier.CORE,
            specialty="Testing",
            tasks_completed=0,
            tasks_failed=10,
        )
        assert agent.success_rate == 0.0

    def test_agent_update_response_time(self):
        """Test response time averaging."""
        agent = Agent(
            agent_id="test-001",
            name="TEST",
            tier=AgentTier.CORE,
            specialty="Testing",
        )

        agent.update_response_time(100.0)
        assert agent.avg_response_time_ms == 100.0

        agent.update_response_time(200.0)
        assert agent.avg_response_time_ms == 150.0

        agent.update_response_time(300.0)
        assert agent.avg_response_time_ms == 200.0

    def test_agent_response_time_limit(self):
        """Test that response times are limited to last 100 measurements."""
        agent = Agent(
            agent_id="test-001",
            name="TEST",
            tier=AgentTier.CORE,
            specialty="Testing",
        )

        # Add 110 measurements of 10ms
        for _ in range(110):
            agent.update_response_time(10.0)

        # Should only keep last 100
        assert len(agent._response_times) == 100
        assert agent.avg_response_time_ms == 10.0

    def test_agent_to_dict(self):
        """Test agent dictionary serialization."""
        agent = Agent(
            agent_id="test-001",
            name="TENSOR",
            tier=AgentTier.CORE,
            specialty="Deep learning",
            status=AgentStatus.IDLE,
            tasks_completed=100,
            tasks_failed=5,
            avg_response_time_ms=50.0,
        )

        data = agent.to_dict()

        assert data["agent_id"] == "test-001"
        assert data["name"] == "TENSOR"
        assert data["tier"] == "core"
        assert data["specialty"] == "Deep learning"
        assert data["status"] == "idle"
        assert data["tasks_completed"] == 100
        assert data["avg_response_time_ms"] == 50.0
        assert "success_rate" in data

    def test_agent_to_dict_with_last_active(self):
        """Test agent serialization with last_active timestamp."""
        now = datetime.now(UTC)
        agent = Agent(
            agent_id="test-001",
            name="TEST",
            tier=AgentTier.CORE,
            specialty="Testing",
            last_active=now,
        )

        data = agent.to_dict()
        assert data["last_active"] == now.isoformat()


# ==============================================================================
# Task Tests
# ==============================================================================


class TestTask:
    """Tests for the Task dataclass."""

    def test_task_creation_defaults(self):
        """Test task is created with correct defaults."""
        task = Task(
            task_id="task-001",
            task_type="compression",
            payload={"file": "test.txt"},
            priority=1,
        )

        assert task.task_id == "task-001"
        assert task.task_type == "compression"
        assert task.payload == {"file": "test.txt"}
        assert task.priority == 1
        assert task.status == "queued"
        assert task.assigned_agent is None
        assert task.result is None
        assert task.error is None

    def test_task_timestamps(self):
        """Test task timestamp fields."""
        task = Task(
            task_id="task-001",
            task_type="test",
            payload={},
            priority=5,
        )

        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None


# ==============================================================================
# AgentTier & AgentStatus Tests
# ==============================================================================


class TestEnums:
    """Tests for enum types."""

    def test_agent_tier_values(self):
        """Test AgentTier enum values."""
        assert AgentTier.CORE.value == "core"
        assert AgentTier.SPECIALIST.value == "specialist"
        assert AgentTier.SUPPORT.value == "support"

    def test_agent_status_values(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.OFFLINE.value == "offline"


# ==============================================================================
# Agent Definitions Tests
# ==============================================================================


class TestAgentDefinitions:
    """Tests for the 40-agent collective definitions."""

    def test_agent_count(self):
        """Test that exactly 40 agents are defined."""
        assert len(AGENT_DEFINITIONS) == 40

    def test_agent_tiers_distribution(self):
        """Test tier distribution across agents."""
        tier_counts = {"core": 0, "specialist": 0, "support": 0}

        for agent_def in AGENT_DEFINITIONS:
            tier_counts[agent_def["tier"].value] += 1

        assert tier_counts["core"] == 10
        assert tier_counts["specialist"] == 20
        assert tier_counts["support"] == 10

    def test_all_agents_have_required_fields(self):
        """Test all agent definitions have required fields."""
        for agent_def in AGENT_DEFINITIONS:
            assert "name" in agent_def
            assert "tier" in agent_def
            assert "specialty" in agent_def
            assert isinstance(agent_def["tier"], AgentTier)

    def test_unique_agent_names(self):
        """Test all agent names are unique."""
        names = [a["name"] for a in AGENT_DEFINITIONS]
        assert len(names) == len(set(names))

    def test_core_agents(self):
        """Test core tier agents are defined correctly."""
        core_agents = [a for a in AGENT_DEFINITIONS if a["tier"] == AgentTier.CORE]
        core_names = {a["name"] for a in core_agents}

        expected_core = {"TENSOR", "VELOCITY", "AXIOM", "PRISM", "FLUX",
                        "DELTA", "SPARK", "WAVE", "NEXUS", "PULSE"}
        assert core_names == expected_core


# ==============================================================================
# AgentSwarm Tests
# ==============================================================================


class TestAgentSwarm:
    """Tests for the AgentSwarm class."""

    def test_swarm_creation(self):
        """Test swarm is created with correct defaults."""
        swarm = AgentSwarm()

        assert swarm.agents == {}
        assert swarm.tasks == {}
        assert not swarm.is_initialized
        assert swarm.uptime_seconds == 0.0

    @pytest.mark.asyncio
    async def test_swarm_initialize(self):
        """Test swarm initialization creates all agents."""
        swarm = AgentSwarm()
        await swarm.initialize()

        assert swarm.is_initialized
        assert len(swarm.agents) == 40
        assert swarm.uptime_seconds > 0

    @pytest.mark.asyncio
    async def test_swarm_agent_status_after_init(self):
        """Test all agents are idle after initialization."""
        swarm = AgentSwarm()
        await swarm.initialize()

        for agent in swarm.agents.values():
            assert agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_swarm_available_agents(self):
        """Test available_agents property."""
        swarm = AgentSwarm()
        await swarm.initialize()

        assert swarm.available_agents == 40
        assert swarm.busy_agents == 0

    @pytest.mark.asyncio
    async def test_swarm_shutdown(self):
        """Test swarm shutdown."""
        swarm = AgentSwarm()
        await swarm.initialize()

        assert swarm.is_initialized

        await swarm.shutdown()

        assert not swarm.is_initialized

    @pytest.mark.asyncio
    async def test_swarm_get_status(self):
        """Test get_swarm_status returns correct information."""
        swarm = AgentSwarm()
        await swarm.initialize()

        status = swarm.get_swarm_status()

        assert status["total_agents"] == 40
        assert status["idle_agents"] == 40
        assert status["busy_agents"] == 0
        assert "uptime_seconds" in status

        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_swarm_get_agent(self):
        """Test get_agent returns correct agent."""
        swarm = AgentSwarm()
        await swarm.initialize()

        # Get any agent
        agent_id = list(swarm.agents.keys())[0]
        agent = swarm.get_agent(agent_id)

        assert agent is not None
        assert agent.agent_id == agent_id

    @pytest.mark.asyncio
    async def test_swarm_get_agent_not_found(self):
        """Test get_agent returns None for unknown agent."""
        swarm = AgentSwarm()
        await swarm.initialize()

        agent = swarm.get_agent("nonexistent-agent")

        assert agent is None

    @pytest.mark.asyncio
    async def test_swarm_list_agents(self):
        """Test list_agents returns all agents."""
        swarm = AgentSwarm()
        await swarm.initialize()

        agents = swarm.list_agents()

        assert len(agents) == 40
        assert all(isinstance(a, Agent) for a in agents)

        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_swarm_list_agents_by_tier(self):
        """Test list_agents filters by tier."""
        swarm = AgentSwarm()
        await swarm.initialize()

        core_agents = swarm.list_agents(tier=AgentTier.CORE)

        assert len(core_agents) == 10
        assert all(a.tier == AgentTier.CORE for a in core_agents)

        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_swarm_assign_task(self):
        """Test task assignment."""
        swarm = AgentSwarm()
        await swarm.initialize()

        agent_name = await swarm.assign_task(
            task_id="task-001",
            task_type="compression",
            payload={"file": "test.txt"},
            priority=5,
        )

        # Task should be created and potentially assigned
        assert "task-001" in swarm.tasks

        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_swarm_task_in_tasks_dict(self):
        """Test task is stored in tasks dict after assignment."""
        swarm = AgentSwarm()
        await swarm.initialize()

        await swarm.assign_task(
            task_id="task-002",
            task_type="test",
            payload={},
            priority=1,
        )

        task = swarm.tasks.get("task-002")

        assert task is not None
        assert task.task_id == "task-002"

        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_swarm_task_not_found(self):
        """Test tasks dict returns None for unknown task."""
        swarm = AgentSwarm()
        await swarm.initialize()

        task = swarm.tasks.get("nonexistent-task")

        assert task is None

        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_swarm_status_contains_health_info(self):
        """Test swarm status contains health information."""
        swarm = AgentSwarm()
        await swarm.initialize()

        status = swarm.get_swarm_status()

        # All agents idle = healthy
        assert status["idle_agents"] == 40
        assert status["busy_agents"] == 0
        assert status["error_agents"] == 0

        await swarm.shutdown()


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestSwarmIntegration:
    """Integration tests for AgentSwarm."""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self):
        """Test complete task assignment and processing."""
        swarm = AgentSwarm()
        await swarm.initialize()

        # Assign task
        await swarm.assign_task(
            task_id="lifecycle-001",
            task_type="compression",
            payload={"data": "test"},
            priority=10,
        )

        # Task should exist
        task = swarm.tasks.get("lifecycle-001")
        assert task is not None
        assert task.status in ["queued", "running", "completed"]

        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_task_assignment(self):
        """Test assigning multiple tasks concurrently."""
        swarm = AgentSwarm()
        await swarm.initialize()

        # Assign 10 tasks concurrently
        await asyncio.gather(*[
            swarm.assign_task(
                task_id=f"concurrent-{i}",
                task_type="test",
                payload={"index": i},
                priority=i,
            )
            for i in range(10)
        ])

        # All tasks should be created
        assert len([k for k in swarm.tasks.keys() if k.startswith("concurrent-")]) == 10

        await swarm.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
