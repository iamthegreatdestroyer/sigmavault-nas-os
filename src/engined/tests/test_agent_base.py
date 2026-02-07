"""
Unit tests for Elite Agent Collective base infrastructure.

Tests agent lifecycle, task execution, and registry operations.
"""

import pytest
import asyncio
from engined.agents.base import (
    BaseAgent,
    AgentState,
    AgentCapability,
    AgentTask,
    TaskResult,
    TaskPriority,
)
from engined.agents.registry import AgentRegistry


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, agent_id: str = "MOCK-01"):
        capability = AgentCapability(
            name="MOCK",
            tier=1,
            domains=["testing"],
            skills=["unit_tests"],
            description="Mock agent for testing"
        )
        super().__init__(agent_id=agent_id, capability=capability)
        self.executed_tasks = []

    async def execute_task(self, task: AgentTask) -> TaskResult:
        """Execute task with mock behavior."""
        self.executed_tasks.append(task.task_id)
        
        # Simulate processing
        await asyncio.sleep(0.01)
        
        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={"result": f"Processed {task.task_type}"}
        )


class FailingAgent(BaseAgent):
    """Agent that always fails for testing error handling."""

    def __init__(self):
        capability = AgentCapability(
            name="FAILING",
            tier=1,
            domains=["testing"],
            skills=["errors"],
            description="Agent that fails"
        )
        super().__init__(agent_id="FAIL-01", capability=capability)

    async def execute_task(self, task: AgentTask) -> TaskResult:
        """Always raise exception."""
        raise ValueError("Intentional failure for testing")


@pytest.mark.asyncio
class TestBaseAgent:
    """Test suite for BaseAgent class."""

    async def test_agent_initialization(self):
        """Test agent initialization."""
        agent = MockAgent()
        
        # Should start in STUB state
        assert agent.state == AgentState.STUB
        assert agent.task_count == 0
        
        # Initialize
        success = await agent.initialize()
        assert success is True
        assert agent.state == AgentState.IDLE

    async def test_agent_double_initialization(self):
        """Test that agent can't be initialized twice."""
        agent = MockAgent()
        
        await agent.initialize()
        assert agent.state == AgentState.IDLE
        
        # Second initialization should fail
        success = await agent.initialize()
        assert success is False

    async def test_task_execution(self):
        """Test successful task execution."""
        agent = MockAgent()
        await agent.initialize()
        
        task = AgentTask(
            task_id="task-001",
            task_type="test_task",
            payload={"data": "test"}
        )
        
        # Submit task
        submitted = await agent.submit_task(task)
        assert submitted is True
        
        # Start agent loop in background
        loop_task = asyncio.create_task(agent.run())
        
        # Wait for task to complete
        await asyncio.sleep(0.1)
        
        # Shutdown
        await agent.shutdown()
        await loop_task
        
        # Verify task was executed
        assert task.task_id in agent.executed_tasks
        assert agent.task_count == 1
        assert agent.success_count == 1

    async def test_task_timeout(self):
        """Test task timeout handling."""
        
        class SlowAgent(MockAgent):
            async def execute_task(self, task: AgentTask) -> TaskResult:
                await asyncio.sleep(10)  # Longer than timeout
                return TaskResult(
                    task_id=task.task_id,
                    success=True,
                    output={}
                )
        
        agent = SlowAgent()
        await agent.initialize()
        
        task = AgentTask(
            task_id="task-002",
            task_type="slow_task",
            payload={},
            timeout=0.1  # Short timeout
        )
        
        result = await agent._execute_with_lifecycle(task)
        
        # Should fail with timeout
        assert result.success is False
        assert "timed out" in result.error.lower()
        assert agent.error_count == 1

    async def test_task_exception_handling(self):
        """Test exception handling during task execution."""
        agent = FailingAgent()
        await agent.initialize()
        
        task = AgentTask(
            task_id="task-003",
            task_type="failing_task",
            payload={}
        )
        
        result = await agent._execute_with_lifecycle(task)
        
        # Should fail with exception
        assert result.success is False
        assert result.error is not None
        assert agent.error_count == 1

    async def test_agent_status(self):
        """Test agent status reporting."""
        agent = MockAgent()
        await agent.initialize()
        
        status = agent.get_status()
        
        assert status["agent_id"] == "MOCK-01"
        assert status["state"] == "idle"
        assert status["tier"] == 1
        assert "testing" in status["domains"]
        assert status["metrics"]["total_tasks"] == 0

    async def test_agent_shutdown(self):
        """Test graceful agent shutdown."""
        agent = MockAgent()
        await agent.initialize()
        
        await agent.shutdown()
        
        assert agent.state == AgentState.SHUTDOWN


@pytest.mark.asyncio
class TestAgentRegistry:
    """Test suite for AgentRegistry class."""

    async def test_agent_registration(self):
        """Test agent registration."""
        registry = AgentRegistry()
        agent = MockAgent()
        
        success = await registry.register_agent(agent)
        assert success is True
        assert len(registry) == 1
        assert "MOCK-01" in registry

    async def test_duplicate_registration(self):
        """Test that duplicate registration is rejected."""
        registry = AgentRegistry()
        agent = MockAgent()
        
        await registry.register_agent(agent)
        
        # Try to register again
        success = await registry.register_agent(agent)
        assert success is False
        assert len(registry) == 1

    async def test_agent_unregistration(self):
        """Test agent unregistration."""
        registry = AgentRegistry()
        agent = MockAgent()
        
        await registry.register_agent(agent)
        await agent.initialize()
        
        success = await registry.unregister_agent("MOCK-01")
        assert success is True
        assert len(registry) == 0

    async def test_initialize_all(self):
        """Test batch initialization of agents."""
        registry = AgentRegistry()
        
        # Register multiple agents
        for i in range(3):
            agent = MockAgent(agent_id=f"MOCK-{i:02d}")
            await registry.register_agent(agent)
        
        # Initialize all
        results = await registry.initialize_all()
        
        assert len(results) == 3
        assert all(results.values())  # All should succeed

    async def test_shutdown_all(self):
        """Test batch shutdown of agents."""
        registry = AgentRegistry()
        
        # Register and initialize agents
        for i in range(3):
            agent = MockAgent(agent_id=f"MOCK-{i:02d}")
            await registry.register_agent(agent)
        
        await registry.initialize_all()
        
        # Shutdown all
        await registry.shutdown_all()
        
        # Verify all agents are shutdown
        for agent in registry._agents.values():
            assert agent.state == AgentState.SHUTDOWN

    async def test_list_agents(self):
        """Test listing agents with filters."""
        registry = AgentRegistry()
        
        # Register agents with different tiers
        agent1 = MockAgent(agent_id="TIER1-01")
        agent1.capability.tier = 1
        
        agent2 = MockAgent(agent_id="TIER2-01")
        agent2.capability.tier = 2
        
        await registry.register_agent(agent1)
        await registry.register_agent(agent2)
        await registry.initialize_all()
        
        # List all
        all_agents = registry.list_agents()
        assert len(all_agents) == 2
        
        # List by tier
        tier1_agents = registry.list_agents(tier=1)
        assert len(tier1_agents) == 1
        assert tier1_agents[0]["agent_id"] == "TIER1-01"

    async def test_get_agent(self):
        """Test getting agent by ID."""
        registry = AgentRegistry()
        agent = MockAgent()
        
        await registry.register_agent(agent)
        
        retrieved = registry.get_agent("MOCK-01")
        assert retrieved is agent
        
        not_found = registry.get_agent("NONEXISTENT")
        assert not_found is None

    async def test_dispatch_task(self):
        """Test task dispatch to agent."""
        registry = AgentRegistry()
        agent = MockAgent()
        
        await registry.register_agent(agent)
        await agent.initialize()
        
        task = AgentTask(
            task_id="task-004",
            task_type="test",
            payload={}
        )
        
        success = await registry.dispatch_task("MOCK-01", task)
        assert success is True

    async def test_registry_status(self):
        """Test registry status reporting."""
        registry = AgentRegistry()
        
        # Register agents
        agent1 = MockAgent(agent_id="MOCK-01")
        agent1.capability.tier = 1
        
        agent2 = MockAgent(agent_id="MOCK-02")
        agent2.capability.tier = 2
        
        await registry.register_agent(agent1)
        await registry.register_agent(agent2)
        await registry.initialize_all()
        
        status = registry.get_registry_status()
        
        assert status["total_agents"] == 2
        assert status["initialized"] is True
        assert status["agents_by_tier"][1] == 1
        assert status["agents_by_tier"][2] == 1
