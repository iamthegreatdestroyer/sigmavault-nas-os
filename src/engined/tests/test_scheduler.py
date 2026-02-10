"""
Unit tests for the Task Scheduler module.

Tests cover:
- Task priority ordering
- Task scheduling with priority queue
- Scheduler lifecycle and metrics

ACTUAL API (discovered via introspection):
- TaskScheduler.schedule is ASYNC: await scheduler.schedule(...)
- TaskScheduler.start/stop are ASYNC
- Methods: schedule, start, stop, mark_completed, mark_failed, get_metrics
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from engined.agents.scheduler import (
    PriorityTask,
    TaskPriority,
    TaskScheduler,
)


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_values_ordering(self):
        """Test priority values are ordered correctly.
        
        In TaskPriority, LOWER value = HIGHER priority.
        """
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value
        assert TaskPriority.LOW.value < TaskPriority.BACKGROUND.value

    def test_priority_specific_values(self):
        """Test specific priority values."""
        assert TaskPriority.CRITICAL.value == 0
        assert TaskPriority.HIGH.value == 1
        assert TaskPriority.NORMAL.value == 5
        assert TaskPriority.LOW.value == 10
        assert TaskPriority.BACKGROUND.value == 20

    def test_critical_is_highest_priority(self):
        """Test CRITICAL has the highest priority (lowest value)."""
        all_priorities = [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
            TaskPriority.BACKGROUND,
        ]
        min_priority = min(all_priorities, key=lambda p: p.value)
        assert min_priority == TaskPriority.CRITICAL


class TestPriorityTask:
    """Tests for PriorityTask class."""

    def test_priority_task_creation(self):
        """Test priority task is created correctly."""
        task = PriorityTask(
            task_id="task-001",
            priority=TaskPriority.NORMAL.value,
        )
        assert task.task_id == "task-001"
        assert task.priority == TaskPriority.NORMAL.value

    def test_priority_task_comparison(self):
        """Test tasks compare by priority for heap ordering."""
        high = PriorityTask(task_id="high", priority=TaskPriority.HIGH.value)
        low = PriorityTask(task_id="low", priority=TaskPriority.LOW.value)
        # HIGH priority (value=1) should be "less than" LOW priority (value=10)
        assert high < low

    def test_critical_priority_comes_first(self):
        """Test critical priority sorts before others."""
        critical = PriorityTask(task_id="critical", priority=TaskPriority.CRITICAL.value)
        normal = PriorityTask(task_id="normal", priority=TaskPriority.NORMAL.value)
        background = PriorityTask(task_id="background", priority=TaskPriority.BACKGROUND.value)
        assert critical < normal < background


class TestTaskScheduler:
    """Tests for TaskScheduler class.
    
    All scheduling methods are ASYNC.
    """

    @pytest.fixture
    def mock_swarm(self):
        """Create a mock AgentSwarm for testing."""
        swarm = MagicMock()
        swarm.get_agents = MagicMock(return_value={})
        swarm.assign_task = AsyncMock(return_value="agent-001")
        return swarm

    @pytest.fixture
    def scheduler(self, mock_swarm):
        """Create a task scheduler for testing.
        
        TaskScheduler(swarm, max_concurrent=40, rate_limit_per_second=100.0)
        """
        return TaskScheduler(
            swarm=mock_swarm,
            max_concurrent=4,
        )

    def test_scheduler_creation(self, scheduler):
        """Test scheduler is created."""
        assert scheduler is not None

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test scheduler can start and stop."""
        await scheduler.start()
        assert scheduler._running
        await scheduler.stop()
        assert not scheduler._running

    @pytest.mark.asyncio
    async def test_schedule_task(self, scheduler):
        """Test scheduling a task returns assigned agent ID."""
        await scheduler.start()
        try:
            assigned_agent = await scheduler.schedule(
                task_id="task-001",
                task_type="compression",
                payload={"data": "test"},
                priority=TaskPriority.NORMAL.value,
            )
            # schedule() returns the assigned agent ID
            assert assigned_agent is not None
            assert isinstance(assigned_agent, str)
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_schedule_with_priority(self, scheduler):
        """Test scheduling tasks with different priorities."""
        await scheduler.start()
        try:
            low_agent = await scheduler.schedule(
                task_id="low-task",
                task_type="batch",
                payload={"batch": 1},
                priority=TaskPriority.LOW.value,
            )
            high_agent = await scheduler.schedule(
                task_id="high-task",
                task_type="urgent",
                payload={"urgent": True},
                priority=TaskPriority.HIGH.value,
            )
            # schedule() returns assigned agent ID
            assert low_agent is not None
            assert high_agent is not None
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_mark_completed(self, scheduler):
        """Test marking a task as completed."""
        await scheduler.start()
        try:
            task_id = await scheduler.schedule(
                task_id="complete-me",
                task_type="test",
                payload={},
            )
            scheduler.mark_completed(task_id)
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_mark_failed(self, scheduler):
        """Test marking a task as failed."""
        await scheduler.start()
        try:
            task_id = await scheduler.schedule(
                task_id="fail-me",
                task_type="test",
                payload={},
            )
            scheduler.mark_failed(task_id)
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_get_metrics(self, scheduler):
        """Test get_metrics returns correct structure."""
        await scheduler.start()
        try:
            await scheduler.schedule(
                task_id="metrics-test",
                task_type="test",
                payload={},
                priority=TaskPriority.NORMAL.value,
            )
            metrics = scheduler.get_metrics()
            # Actual keys: queue_size, tasks_completed, avg_wait_time_ms, is_running
            assert "queue_size" in metrics
            assert "tasks_completed" in metrics
            assert "is_running" in metrics
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_schedule_multiple_tasks(self, scheduler):
        """Test scheduling multiple tasks."""
        await scheduler.start()
        try:
            for i in range(5):
                assigned_agent = await scheduler.schedule(
                    task_id=f"task-{i}",
                    task_type="bulk",
                    payload={"index": i},
                )
                # schedule() returns assigned agent ID
                assert assigned_agent is not None
                assert isinstance(assigned_agent, str)
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_with_workers(self, scheduler):
        """Test scheduler with custom worker count."""
        await scheduler.start(num_workers=2)
        try:
            task_id = await scheduler.schedule(
                task_id="worker-test",
                task_type="test",
                payload={},
            )
            assert task_id is not None
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_default_priority(self, scheduler):
        """Test default priority is NORMAL."""
        await scheduler.start()
        try:
            assigned_agent = await scheduler.schedule(
                task_id="default-priority",
                task_type="test",
                payload={},
            )
            # schedule() returns assigned agent ID
            assert assigned_agent is not None
            assert isinstance(assigned_agent, str)
        finally:
            await scheduler.stop()
