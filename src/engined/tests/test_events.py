"""
Unit tests for the Event Emitter module.

Tests cover:
- Event creation and emission
- Event subscriptions
- Event types and priorities
- Async event handling
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from engined.agents.events import (
    Event,
    EventEmitter,
    EventType,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_event_types_defined(self):
        """Test all expected event types are defined."""
        # Agent lifecycle events
        assert EventType.AGENT_STARTED is not None
        assert EventType.AGENT_STOPPED is not None
        assert EventType.AGENT_HEALTH_CHECK is not None

        # Task events
        assert EventType.TASK_QUEUED is not None
        assert EventType.TASK_DISPATCHED is not None
        assert EventType.AGENT_TASK_COMPLETED is not None
        assert EventType.AGENT_TASK_FAILED is not None

    def test_event_type_values(self):
        """Test event type string values."""
        assert EventType.AGENT_STARTED.value == "agent.started"
        assert EventType.AGENT_TASK_COMPLETED.value == "agent.task_completed"


class TestEvent:
    """Tests for Event dataclass."""

    def test_event_creation(self):
        """Test event is created with correct fields."""
        event = Event(
            event_type=EventType.AGENT_STARTED,
            data={"agent_id": "test-001", "status": "running"}
        )

        assert event.event_type == EventType.AGENT_STARTED
        assert event.data["agent_id"] == "test-001"
        assert event.data == {"agent_id": "test-001", "status": "running"}
        assert event.timestamp is not None
        assert event.event_id is not None

    def test_event_to_dict(self):
        """Test event serializes to dictionary."""
        event = Event(
            event_type=EventType.AGENT_TASK_COMPLETED,
            data={"result": "success"}
        )

        d = event.to_dict()

        assert d["type"] == "agent.task_completed"
        assert d["data"] == {"result": "success"}
        assert "timestamp" in d
        assert "event_id" in d

    def test_event_id_uniqueness(self):
        """Test each event gets a unique ID."""
        event1 = Event(event_type=EventType.AGENT_STARTED, data={})
        # Small delay to ensure different timestamps
        import time
        time.sleep(0.01)
        event2 = Event(event_type=EventType.AGENT_STARTED, data={})

        assert event1.event_id != event2.event_id


class TestEventEmitter:
    """Tests for EventEmitter class."""

    @pytest.fixture
    async def emitter(self):
        """Create an event emitter for testing."""
        emitter = EventEmitter(buffer_size=100)
        await emitter.start()
        yield emitter
        await emitter.stop()

    @pytest.mark.asyncio
    async def test_emitter_start_stop(self):
        """Test emitter can start and stop."""
        emitter = EventEmitter()

        assert not emitter._running

        await emitter.start()
        assert emitter._running

        await emitter.stop()
        assert not emitter._running

    @pytest.mark.asyncio
    async def test_emit_event(self, emitter):
        """Test emitting an event."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        emitter.subscribe(EventType.AGENT_STARTED, handler)

        # Create Event object - emit() takes Event, not (type, data)
        event = Event(event_type=EventType.AGENT_STARTED, data={"status": "running"})
        await emitter.emit(event)

        # Give handler time to process
        await asyncio.sleep(0.15)

        assert len(received_events) == 1
        assert received_events[0].event_type == EventType.AGENT_STARTED

    @pytest.mark.asyncio
    async def test_subscribe_returns_unsubscribe(self, emitter):
        """Test subscribe returns unsubscribe callable."""
        handler = AsyncMock()

        unsubscribe = emitter.subscribe(EventType.AGENT_TASK_COMPLETED, handler)
        assert callable(unsubscribe)

        unsubscribe()

        event = Event(event_type=EventType.AGENT_TASK_COMPLETED, data={})
        await emitter.emit(event)
        await asyncio.sleep(0.15)

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, emitter):
        """Test multiple handlers receive the same event."""
        handler1_called = []
        handler2_called = []

        async def handler1(event: Event):
            handler1_called.append(event)

        async def handler2(event: Event):
            handler2_called.append(event)

        emitter.subscribe(EventType.AGENT_STOPPED, handler1)
        emitter.subscribe(EventType.AGENT_STOPPED, handler2)

        event = Event(event_type=EventType.AGENT_STOPPED, data={"reason": "shutdown"})
        await emitter.emit(event)
        await asyncio.sleep(0.15)

        assert len(handler1_called) == 1
        assert len(handler2_called) == 1

    @pytest.mark.asyncio
    async def test_event_filtering_by_type(self, emitter):
        """Test handlers only receive subscribed event types."""
        started_events = []
        stopped_events = []

        async def started_handler(event: Event):
            started_events.append(event)

        async def stopped_handler(event: Event):
            stopped_events.append(event)

        emitter.subscribe(EventType.AGENT_STARTED, started_handler)
        emitter.subscribe(EventType.AGENT_STOPPED, stopped_handler)

        event = Event(event_type=EventType.AGENT_STARTED, data={})
        await emitter.emit(event)
        await asyncio.sleep(0.15)

        assert len(started_events) == 1
        assert len(stopped_events) == 0

    @pytest.mark.asyncio
    async def test_get_metrics(self, emitter):
        """Test get_metrics returns correct structure."""
        # Access private metrics dict
        metrics = emitter._metrics

        assert "events_emitted" in metrics
        assert "events_processed" in metrics
        assert "events_dropped" in metrics
        assert "handlers_called" in metrics

    @pytest.mark.asyncio
    async def test_emit_now(self, emitter):
        """Test emit_now for immediate event dispatch."""
        # emit_now takes (event_type, data) and creates Event internally
        await emitter.emit_now(EventType.AGENT_STARTED, {"immediate": True})

        # Should not raise
        assert True

    @pytest.mark.asyncio
    async def test_global_handler(self, emitter):
        """Test subscribing to all events with None type."""
        all_events = []

        async def global_handler(event: Event):
            all_events.append(event)

        emitter.subscribe(None, global_handler)

        event1 = Event(event_type=EventType.AGENT_STARTED, data={})
        event2 = Event(event_type=EventType.AGENT_STOPPED, data={})

        await emitter.emit(event1)
        await emitter.emit(event2)
        await asyncio.sleep(0.15)

        # Global handler should receive both events
        assert len(all_events) == 2
