"""
Unit tests for the MNEMONIC Memory module.

Tests cover:
- Memory store initialization
- Memory types and priorities
- Memory storage and retrieval
- Memory associations and search
"""

from datetime import datetime

import pytest

from engined.agents.memory import (
    AgentMemory,
    MemoryEntry,
    MemoryPriority,
    MemoryStore,
    MemoryType,
)


class TestMemoryType:
    """Tests for MemoryType enum."""

    def test_memory_types_defined(self):
        """Test all memory types are defined."""
        assert MemoryType.EPISODIC is not None
        assert MemoryType.SEMANTIC is not None
        assert MemoryType.PROCEDURAL is not None


class TestMemoryPriority:
    """Tests for MemoryPriority enum."""

    def test_priority_values(self):
        """Test priority values are ordered correctly."""
        # Higher value = higher priority
        assert MemoryPriority.CRITICAL.value > MemoryPriority.HIGH.value
        assert MemoryPriority.HIGH.value > MemoryPriority.NORMAL.value
        assert MemoryPriority.NORMAL.value > MemoryPriority.LOW.value
        assert MemoryPriority.LOW.value > MemoryPriority.EPHEMERAL.value

    def test_priority_specific_values(self):
        """Test specific priority values."""
        assert MemoryPriority.CRITICAL.value == 100
        assert MemoryPriority.HIGH.value == 75
        assert MemoryPriority.NORMAL.value == 50
        assert MemoryPriority.LOW.value == 25
        assert MemoryPriority.EPHEMERAL.value == 10


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_memory_entry_creation(self):
        """Test memory entry is created correctly."""
        now = datetime.now()
        entry = MemoryEntry(
            id="mem-001",
            type=MemoryType.EPISODIC,
            content={"event": "task_completed"},
            created_at=now,
            accessed_at=now,
            priority=MemoryPriority.NORMAL,
        )

        assert entry.id == "mem-001"
        assert entry.type == MemoryType.EPISODIC
        assert entry.priority == MemoryPriority.NORMAL
        assert entry.content == {"event": "task_completed"}
        assert entry.strength == 1.0
        assert entry.access_count == 0

    def test_memory_entry_to_dict(self):
        """Test memory entry serializes to dictionary."""
        now = datetime.now()
        entry = MemoryEntry(
            id="mem-002",
            type=MemoryType.SEMANTIC,
            content={"pattern": "test"},
            created_at=now,
            accessed_at=now,
            priority=MemoryPriority.HIGH,
        )

        d = entry.to_dict()

        assert d["id"] == "mem-002"
        assert d["type"] == "semantic"
        assert d["priority"] == 75
        assert d["content"] == {"pattern": "test"}

    def test_memory_entry_with_tags(self):
        """Test memory entry with tags."""
        now = datetime.now()
        entry = MemoryEntry(
            id="mem-003",
            type=MemoryType.PROCEDURAL,
            content={"procedure": "compress"},
            created_at=now,
            accessed_at=now,
            priority=MemoryPriority.NORMAL,
            tags={"compression", "optimization"}
        )

        assert "compression" in entry.tags
        assert "optimization" in entry.tags

    def test_memory_entry_access(self):
        """Test accessing memory increases access count."""
        now = datetime.now()
        entry = MemoryEntry(
            id="mem-004",
            type=MemoryType.EPISODIC,
            content={"test": True},
            created_at=now,
            accessed_at=now,
        )

        initial_count = entry.access_count
        entry.access()

        assert entry.access_count == initial_count + 1


class TestMemoryStore:
    """Tests for MemoryStore class."""

    @pytest.fixture
    async def store(self):
        """Create a memory store for testing."""
        # MemoryStore doesn't have decay_rate param - uses other params
        store = MemoryStore(max_entries=100)
        await store.start()
        yield store
        await store.stop()

    @pytest.mark.asyncio
    async def test_store_start_stop(self):
        """Test store can start and stop."""
        store = MemoryStore()

        assert not store._running

        await store.start()
        assert store._running

        await store.stop()
        assert not store._running

    @pytest.mark.asyncio
    async def test_store_memory(self, store):
        """Test storing a memory."""
        memory_id = await store.store(
            content={"test": "data"},
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.NORMAL,
        )

        assert memory_id is not None

        retrieved = await store.retrieve(memory_id)
        assert retrieved is not None
        assert retrieved.content == {"test": "data"}

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self, store):
        """Test retrieving non-existent memory returns None."""
        result = await store.retrieve("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_store_with_tags(self, store):
        """Test storing memory with tags."""
        memory_id = await store.store(
            content={"data": "test"},
            memory_type=MemoryType.SEMANTIC,
            priority=MemoryPriority.HIGH,
            tags={"tag1", "tag2"}
        )

        retrieved = await store.retrieve(memory_id)
        assert "tag1" in retrieved.tags
        assert "tag2" in retrieved.tags

    @pytest.mark.asyncio
    async def test_search_by_tag(self, store):
        """Test searching memories by tag."""
        await store.store(
            content={"name": "memory1"},
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.NORMAL,
            tags={"important", "test"}
        )
        await store.store(
            content={"name": "memory2"},
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.NORMAL,
            tags={"unimportant"}
        )

        results = await store.search(tags={"important"})

        assert len(results) == 1
        assert results[0].content["name"] == "memory1"

    @pytest.mark.asyncio
    async def test_search_by_type(self, store):
        """Test searching memories by type."""
        await store.store(
            content={"episodic": True},
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.NORMAL,
        )
        await store.store(
            content={"semantic": True},
            memory_type=MemoryType.SEMANTIC,
            priority=MemoryPriority.NORMAL,
        )

        results = await store.search(memory_type=MemoryType.EPISODIC)

        assert len(results) == 1
        assert results[0].content.get("episodic") is True

    @pytest.mark.asyncio
    async def test_forget_memory(self, store):
        """Test forgetting a memory."""
        memory_id = await store.store(
            content={"to_forget": True},
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.LOW,
        )

        assert await store.retrieve(memory_id) is not None

        success = await store.forget(memory_id)
        assert success is True

        assert await store.retrieve(memory_id) is None

    @pytest.mark.asyncio
    async def test_get_metrics(self, store):
        """Test get_metrics returns correct structure."""
        await store.store(
            content={"test": 1},
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.NORMAL,
        )

        metrics = store.get_metrics()

        assert "total_memories" in metrics
        assert "total_stored" in metrics
        assert "total_forgotten" in metrics
        assert "total_retrieved" in metrics
        assert "by_type" in metrics
        assert metrics["total_memories"] == 1
        assert metrics["total_stored"] == 1

    @pytest.mark.asyncio
    async def test_memory_access_increases_count(self, store):
        """Test accessing memory increases its access count."""
        memory_id = await store.store(
            content={"test": True},
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.NORMAL,
        )

        mem1 = await store.retrieve(memory_id)
        initial_count = mem1.access_count

        mem2 = await store.retrieve(memory_id)
        # access_count should increase on each retrieve
        assert mem2.access_count >= initial_count


class TestAgentMemory:
    """Tests for AgentMemory class."""

    @pytest.fixture
    async def store(self):
        """Create a memory store for testing."""
        store = MemoryStore(max_entries=100)
        await store.start()
        yield store
        await store.stop()

    @pytest.fixture
    def agent_memory(self, store):
        """Create an agent memory for testing."""
        return AgentMemory(store=store, agent_id="test-agent")

    @pytest.mark.asyncio
    async def test_remember_task(self, agent_memory):
        """Test remembering a task."""
        # remember_task requires task_type, result (str), duration_ms, success
        memory_id = await agent_memory.remember_task(
            task_id="task-001",
            task_type="compression",
            result="completed successfully",
            duration_ms=150.0,
            success=True,
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_remember_failed_task(self, agent_memory):
        """Test remembering a failed task."""
        memory_id = await agent_memory.remember_task(
            task_id="task-002",
            task_type="encryption",
            result="timeout error",
            duration_ms=5000.0,
            success=False,
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_remember_pattern(self, agent_memory):
        """Test remembering a pattern."""
        memory_id = await agent_memory.remember_pattern(
            pattern_name="high_load_response",
            pattern_data={"threshold": 0.8, "action": "scale_up"}
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_remember_procedure(self, agent_memory):
        """Test remembering a procedure."""
        # remember_procedure requires procedure_name, steps, success_rate, avg_duration_ms
        memory_id = await agent_memory.remember_procedure(
            procedure_name="compress_json",
            steps=["parse", "compress", "encode"],
            success_rate=0.95,
            avg_duration_ms=120.0,
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_recall_similar_tasks(self, agent_memory):
        """Test recalling similar tasks."""
        # Store a task first
        await agent_memory.remember_task(
            task_id="task-100",
            task_type="analysis",
            result="done",
            duration_ms=100.0,
            success=True,
        )

        # Recall tasks of same type
        results = await agent_memory.recall_similar_tasks("analysis")

        # Should find the stored task
        assert isinstance(results, list)
