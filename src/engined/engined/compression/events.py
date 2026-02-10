"""
Copyright 2025 Stephen Bilodeau. All Rights Reserved.
SigmaVault NAS OS - Compression Event Emitter

Event emitter for compression operations, integrating with the 
WebSocket event system for real-time progress streaming.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CompressionEventType(Enum):
    """Types of compression events."""
    # Job lifecycle events
    JOB_QUEUED = "compression.job.queued"
    JOB_STARTED = "compression.job.started"
    JOB_PROGRESS = "compression.job.progress"
    JOB_COMPLETED = "compression.job.completed"
    JOB_FAILED = "compression.job.failed"
    JOB_CANCELLED = "compression.job.cancelled"

    # Engine events
    ENGINE_INITIALIZED = "compression.engine.initialized"
    ENGINE_ERROR = "compression.engine.error"

    # Stats events
    STATS_UPDATED = "compression.stats.updated"

    # Codebook events
    CODEBOOK_UPDATED = "compression.codebook.updated"
    CODEBOOK_OPTIMIZED = "compression.codebook.optimized"


@dataclass
class CompressionEvent:
    """
    Represents a compression event.
    
    Events are emitted for real-time monitoring and WebSocket streaming.
    """
    event_type: CompressionEventType
    job_id: str | None
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.event_type.value,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }

    def to_websocket_message(self) -> dict[str, Any]:
        """
        Format event for WebSocket transmission.
        
        Compatible with the existing WebSocket event hub.
        """
        return {
            "type": "compression_event",
            "event": self.event_type.value,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.data,
        }


# Type alias for event handlers
EventHandler = Callable[[CompressionEvent], Awaitable[None]]


class CompressionEventEmitter:
    """
    Event emitter for compression operations.
    
    Features:
    - Async event handlers
    - Event filtering by type
    - Integration with WebSocket hub
    - Event history with retention
    """

    def __init__(self, history_size: int = 1000):
        """
        Initialize event emitter.
        
        Args:
            history_size: Maximum number of events to retain in history.
        """
        self._handlers: dict[CompressionEventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
        self._history: list[CompressionEvent] = []
        self._history_size = history_size
        self._subscribed_jobs: set[str] = set()
        self._lock = asyncio.Lock()

    def on(
        self,
        event_type: CompressionEventType,
        handler: EventHandler,
    ) -> None:
        """
        Register handler for specific event type.
        
        Args:
            event_type: Event type to listen for.
            handler: Async callback function.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def on_all(self, handler: EventHandler) -> None:
        """
        Register handler for all events.
        
        Args:
            handler: Async callback function.
        """
        self._global_handlers.append(handler)

    def off(
        self,
        event_type: CompressionEventType,
        handler: EventHandler,
    ) -> None:
        """Remove handler for specific event type."""
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    def off_all(self, handler: EventHandler) -> None:
        """Remove global handler."""
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)

    def subscribe_job(self, job_id: str) -> None:
        """
        Subscribe to events for a specific job.
        
        When subscribed, events for this job will be tracked
        and available via get_job_events().
        """
        self._subscribed_jobs.add(job_id)

    def unsubscribe_job(self, job_id: str) -> None:
        """Unsubscribe from job events."""
        self._subscribed_jobs.discard(job_id)

    async def emit(
        self,
        event_type: CompressionEventType,
        job_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit an event.
        
        Args:
            event_type: Type of event.
            job_id: Associated job ID (if applicable).
            data: Event data payload.
        """
        event = CompressionEvent(
            event_type=event_type,
            job_id=job_id,
            timestamp=datetime.now(),
            data=data or {},
        )

        # Add to history
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]

        # Call type-specific handlers
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

        # Call global handlers
        for handler in self._global_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Global event handler error: {e}")

        logger.debug(f"Event emitted: {event_type.value} (job={job_id})")

    async def emit_job_queued(
        self,
        job_id: str,
        job_type: str,
        priority: str,
        input_path: str | None = None,
        input_size: int = 0,
    ) -> None:
        """Emit job queued event."""
        await self.emit(
            CompressionEventType.JOB_QUEUED,
            job_id,
            {
                "job_type": job_type,
                "priority": priority,
                "input_path": input_path,
                "input_size": input_size,
            },
        )

    async def emit_job_started(
        self,
        job_id: str,
        job_type: str,
        input_size: int = 0,
    ) -> None:
        """Emit job started event."""
        await self.emit(
            CompressionEventType.JOB_STARTED,
            job_id,
            {
                "job_type": job_type,
                "input_size": input_size,
            },
        )

    async def emit_job_progress(
        self,
        job_id: str,
        progress: float,
        bytes_processed: int,
        bytes_total: int,
        current_ratio: float,
        phase: str,
        eta_seconds: float = 0.0,
    ) -> None:
        """Emit job progress event."""
        await self.emit(
            CompressionEventType.JOB_PROGRESS,
            job_id,
            {
                "progress": progress,
                "bytes_processed": bytes_processed,
                "bytes_total": bytes_total,
                "current_ratio": current_ratio,
                "phase": phase,
                "eta_seconds": eta_seconds,
            },
        )

    async def emit_job_completed(
        self,
        job_id: str,
        original_size: int,
        compressed_size: int,
        compression_ratio: float,
        elapsed_seconds: float,
        output_path: str | None = None,
    ) -> None:
        """Emit job completed event."""
        await self.emit(
            CompressionEventType.JOB_COMPLETED,
            job_id,
            {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "elapsed_seconds": elapsed_seconds,
                "output_path": output_path,
            },
        )

    async def emit_job_failed(
        self,
        job_id: str,
        error: str,
        elapsed_seconds: float = 0.0,
    ) -> None:
        """Emit job failed event."""
        await self.emit(
            CompressionEventType.JOB_FAILED,
            job_id,
            {
                "error": error,
                "elapsed_seconds": elapsed_seconds,
            },
        )

    async def emit_job_cancelled(
        self,
        job_id: str,
        reason: str = "user_request",
    ) -> None:
        """Emit job cancelled event."""
        await self.emit(
            CompressionEventType.JOB_CANCELLED,
            job_id,
            {
                "reason": reason,
            },
        )

    async def emit_engine_initialized(
        self,
        engine_type: str,
        codebook_size: int = 0,
    ) -> None:
        """Emit engine initialized event."""
        await self.emit(
            CompressionEventType.ENGINE_INITIALIZED,
            None,
            {
                "engine_type": engine_type,
                "codebook_size": codebook_size,
            },
        )

    async def emit_engine_error(
        self,
        error: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Emit engine error event."""
        await self.emit(
            CompressionEventType.ENGINE_ERROR,
            None,
            {
                "error": error,
                "details": details or {},
            },
        )

    async def emit_stats_updated(
        self,
        total_jobs: int,
        pending: int,
        running: int,
        completed: int,
        failed: int,
        total_bytes_compressed: int = 0,
        average_ratio: float = 0.0,
    ) -> None:
        """Emit stats updated event."""
        await self.emit(
            CompressionEventType.STATS_UPDATED,
            None,
            {
                "total_jobs": total_jobs,
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "total_bytes_compressed": total_bytes_compressed,
                "average_ratio": average_ratio,
            },
        )

    def get_history(
        self,
        event_type: CompressionEventType | None = None,
        job_id: str | None = None,
        limit: int = 100,
    ) -> list[CompressionEvent]:
        """
        Get event history.
        
        Args:
            event_type: Filter by event type.
            job_id: Filter by job ID.
            limit: Maximum events to return.
            
        Returns:
            List of matching events (most recent first).
        """
        events = list(self._history)

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if job_id:
            events = [e for e in events if e.job_id == job_id]

        # Return most recent first
        events.reverse()
        return events[:limit]

    def get_job_events(self, job_id: str) -> list[CompressionEvent]:
        """Get all events for a specific job."""
        return self.get_history(job_id=job_id, limit=1000)

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Global event emitter instance
_global_emitter: CompressionEventEmitter | None = None


def get_compression_emitter() -> CompressionEventEmitter:
    """Get the global compression event emitter."""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = CompressionEventEmitter()
    return _global_emitter


def set_compression_emitter(emitter: CompressionEventEmitter) -> None:
    """Set the global compression event emitter."""
    global _global_emitter
    _global_emitter = emitter


class WebSocketEventBridge:
    """
    Bridge between compression events and WebSocket hub.
    
    Forwards compression events to the WebSocket system
    for real-time client updates.
    """

    def __init__(
        self,
        emitter: CompressionEventEmitter,
        websocket_send: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        """
        Initialize WebSocket bridge.
        
        Args:
            emitter: Compression event emitter.
            websocket_send: Async function to send WebSocket messages.
        """
        self.emitter = emitter
        self.websocket_send = websocket_send
        self._connected = False

    async def connect(self) -> None:
        """Connect to event emitter and start forwarding."""
        if self._connected:
            return

        self.emitter.on_all(self._forward_event)
        self._connected = True
        logger.info("WebSocketEventBridge connected")

    async def disconnect(self) -> None:
        """Disconnect from event emitter."""
        if not self._connected:
            return

        self.emitter.off_all(self._forward_event)
        self._connected = False
        logger.info("WebSocketEventBridge disconnected")

    async def _forward_event(self, event: CompressionEvent) -> None:
        """Forward event to WebSocket."""
        if self.websocket_send is None:
            return

        try:
            message = event.to_websocket_message()
            await self.websocket_send(message)
        except Exception as e:
            logger.error(f"WebSocket forward error: {e}")

    def set_websocket_send(
        self,
        send_fn: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Set the WebSocket send function."""
        self.websocket_send = send_fn
