"""
Agent Event Emitter System

Provides real-time event emission for agent lifecycle, task scheduling,
and recovery operations. Events are sent to connected WebSocket clients
via the Go API gateway.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Coroutine

import structlog

if TYPE_CHECKING:
    from engined.agents.swarm import AgentSwarm
    from engined.agents.scheduler import TaskScheduler
    from engined.agents.recovery import AgentRecovery

logger = structlog.get_logger(__name__)


class EventType(str, Enum):
    """Event types matching Go WebSocket hub types."""
    
    # Agent lifecycle events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_RESTARTED = "agent.restarted"
    AGENT_HEALTH_CHECK = "agent.health_check"
    AGENT_STATUS = "agent.status"
    
    # Task events
    AGENT_TASK_ASSIGNED = "agent.task_assigned"
    AGENT_TASK_COMPLETED = "agent.task_completed"
    AGENT_TASK_FAILED = "agent.task_failed"
    TASK_QUEUED = "task.queued"
    TASK_DISPATCHED = "task.dispatched"
    
    # Scheduler events
    SCHEDULER_METRICS = "scheduler.metrics"
    
    # Recovery events
    CIRCUIT_BREAKER_OPEN = "circuit_breaker.open"
    CIRCUIT_BREAKER_CLOSED = "circuit_breaker.closed"
    AGENT_RECOVERY_STARTED = "agent.recovery_started"
    AGENT_RECOVERY_SUCCESS = "agent.recovery_success"
    AGENT_RECOVERY_FAILED = "agent.recovery_failed"
    DEAD_LETTER_QUEUED = "dead_letter.queued"
    
    # System events
    SYSTEM_STATUS = "system.status"
    COMPRESSION_UPDATE = "compression.update"


@dataclass
class Event:
    """Represents an event to be emitted."""
    
    event_type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: f"evt-{int(time.time() * 1000)}")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "type": self.event_type.value,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps(self.to_dict())


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventEmitter:
    """
    Central event emitter for agent system events.
    
    Manages event subscriptions and broadcasts events to registered handlers.
    Designed to integrate with WebSocket broadcasting via Go API.
    """
    
    def __init__(self, buffer_size: int = 1000) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
        self._event_buffer: asyncio.Queue[Event] = asyncio.Queue(maxsize=buffer_size)
        self._running = False
        self._processor_task: asyncio.Task | None = None
        self._metrics = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "handlers_called": 0,
            "handler_errors": 0,
        }
        
    async def start(self) -> None:
        """Start the event processor."""
        if self._running:
            return
            
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event emitter started")
    
    async def stop(self) -> None:
        """Stop the event processor."""
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
                
        logger.info(
            "Event emitter stopped",
            events_emitted=self._metrics["events_emitted"],
            events_processed=self._metrics["events_processed"],
        )
    
    def subscribe(
        self, 
        event_type: EventType | None, 
        handler: EventHandler
    ) -> Callable[[], None]:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type to subscribe to, or None for all events.
            handler: Async function to call when event occurs.
            
        Returns:
            Unsubscribe function.
        """
        if event_type is None:
            self._global_handlers.append(handler)
            return lambda: self._global_handlers.remove(handler)
        
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            
        self._handlers[event_type].append(handler)
        return lambda: self._handlers[event_type].remove(handler)
    
    async def emit(self, event: Event) -> bool:
        """
        Emit an event to be processed.
        
        Args:
            event: Event to emit.
            
        Returns:
            True if event was queued, False if dropped.
        """
        self._metrics["events_emitted"] += 1
        
        try:
            self._event_buffer.put_nowait(event)
            return True
        except asyncio.QueueFull:
            self._metrics["events_dropped"] += 1
            logger.warning(
                "Event dropped - buffer full",
                event_type=event.event_type.value,
            )
            return False
    
    async def emit_now(
        self, 
        event_type: EventType, 
        data: dict[str, Any]
    ) -> None:
        """
        Emit an event immediately without buffering.
        
        Use for critical events that must be processed synchronously.
        """
        event = Event(event_type=event_type, data=data)
        await self._dispatch_event(event)
    
    async def _process_events(self) -> None:
        """Process events from the buffer."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_buffer.get(),
                    timeout=1.0
                )
                await self._dispatch_event(event)
                self._metrics["events_processed"] += 1
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Error processing event", error=str(e))
    
    async def _dispatch_event(self, event: Event) -> None:
        """Dispatch event to all subscribed handlers."""
        handlers = list(self._global_handlers)
        
        if event.event_type in self._handlers:
            handlers.extend(self._handlers[event.event_type])
        
        for handler in handlers:
            try:
                await handler(event)
                self._metrics["handlers_called"] += 1
            except Exception as e:
                self._metrics["handler_errors"] += 1
                logger.error(
                    "Handler error",
                    event_type=event.event_type.value,
                    error=str(e),
                )
    
    def get_metrics(self) -> dict[str, int]:
        """Get event emitter metrics."""
        return dict(self._metrics)


class AgentEventBridge:
    """
    Bridges agent system events to the event emitter.
    
    Integrates with AgentSwarm, TaskScheduler, and AgentRecovery
    to capture and emit relevant events.
    """
    
    def __init__(
        self,
        emitter: EventEmitter,
        swarm: AgentSwarm | None = None,
        scheduler: TaskScheduler | None = None,
        recovery: AgentRecovery | None = None,
    ) -> None:
        self.emitter = emitter
        self.swarm = swarm
        self.scheduler = scheduler
        self.recovery = recovery
        self._health_check_task: asyncio.Task | None = None
        self._metrics_task: asyncio.Task | None = None
        self._running = False
    
    async def start(
        self, 
        health_interval: float = 30.0,
        metrics_interval: float = 10.0,
    ) -> None:
        """Start the event bridge with periodic emitters."""
        if self._running:
            return
            
        self._running = True
        
        self._health_check_task = asyncio.create_task(
            self._emit_health_checks(health_interval)
        )
        self._metrics_task = asyncio.create_task(
            self._emit_scheduler_metrics(metrics_interval)
        )
        
        logger.info("Agent event bridge started")
    
    async def stop(self) -> None:
        """Stop the event bridge."""
        self._running = False
        
        for task in [self._health_check_task, self._metrics_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Agent event bridge stopped")
    
    async def _emit_health_checks(self, interval: float) -> None:
        """Periodically emit agent health check events."""
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                if not self.swarm:
                    continue
                
                # Get agent health status
                for agent in self.swarm.agents.values():
                    health_data = {
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "status": agent.status.value if hasattr(agent.status, 'value') else str(agent.status),
                        "health_score": getattr(agent, 'health_score', 100),
                        "success_rate": agent.success_rate,
                        "avg_response_time_ms": agent.avg_response_time * 1000,
                        "tasks_completed": agent.tasks_completed,
                        "uptime_seconds": (
                            datetime.now(timezone.utc) - agent.started_at
                        ).total_seconds() if agent.started_at else 0,
                    }
                    
                    await self.emitter.emit(Event(
                        event_type=EventType.AGENT_HEALTH_CHECK,
                        data=health_data,
                    ))
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error emitting health checks", error=str(e))
    
    async def _emit_scheduler_metrics(self, interval: float) -> None:
        """Periodically emit scheduler metrics."""
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                if not self.scheduler:
                    continue
                
                metrics = self.scheduler.get_metrics()
                
                await self.emitter.emit(Event(
                    event_type=EventType.SCHEDULER_METRICS,
                    data=metrics,
                ))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error emitting scheduler metrics", error=str(e))
    
    # Event emission methods for external callers
    
    async def on_agent_started(self, agent_name: str, agent_id: str) -> None:
        """Emit agent started event."""
        await self.emitter.emit(Event(
            event_type=EventType.AGENT_STARTED,
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_agent_stopped(
        self, 
        agent_name: str, 
        agent_id: str, 
        reason: str = "normal"
    ) -> None:
        """Emit agent stopped event."""
        await self.emitter.emit(Event(
            event_type=EventType.AGENT_STOPPED,
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_agent_restarted(
        self, 
        agent_name: str, 
        agent_id: str,
        restart_count: int,
    ) -> None:
        """Emit agent restarted event."""
        await self.emitter.emit(Event(
            event_type=EventType.AGENT_RESTARTED,
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "restart_count": restart_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_task_assigned(
        self, 
        task_id: str,
        task_type: str,
        agent_name: str,
        priority: str,
    ) -> None:
        """Emit task assigned event."""
        await self.emitter.emit(Event(
            event_type=EventType.AGENT_TASK_ASSIGNED,
            data={
                "task_id": task_id,
                "task_type": task_type,
                "agent_name": agent_name,
                "priority": priority,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_task_completed(
        self,
        task_id: str,
        agent_name: str,
        duration_ms: float,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Emit task completed event."""
        await self.emitter.emit(Event(
            event_type=EventType.AGENT_TASK_COMPLETED,
            data={
                "task_id": task_id,
                "agent_name": agent_name,
                "duration_ms": duration_ms,
                "result": result or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_task_failed(
        self,
        task_id: str,
        agent_name: str,
        error: str,
        will_retry: bool = False,
    ) -> None:
        """Emit task failed event."""
        await self.emitter.emit(Event(
            event_type=EventType.AGENT_TASK_FAILED,
            data={
                "task_id": task_id,
                "agent_name": agent_name,
                "error": error,
                "will_retry": will_retry,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_circuit_breaker_open(
        self, 
        agent_name: str, 
        failure_count: int
    ) -> None:
        """Emit circuit breaker open event."""
        await self.emitter.emit_now(
            EventType.CIRCUIT_BREAKER_OPEN,
            {
                "agent_name": agent_name,
                "failure_count": failure_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    
    async def on_circuit_breaker_closed(self, agent_name: str) -> None:
        """Emit circuit breaker closed event."""
        await self.emitter.emit(Event(
            event_type=EventType.CIRCUIT_BREAKER_CLOSED,
            data={
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_recovery_started(
        self, 
        agent_name: str, 
        attempt: int
    ) -> None:
        """Emit recovery started event."""
        await self.emitter.emit_now(
            EventType.AGENT_RECOVERY_STARTED,
            {
                "agent_name": agent_name,
                "attempt": attempt,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    
    async def on_recovery_success(self, agent_name: str) -> None:
        """Emit recovery success event."""
        await self.emitter.emit(Event(
            event_type=EventType.AGENT_RECOVERY_SUCCESS,
            data={
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))
    
    async def on_recovery_failed(
        self, 
        agent_name: str, 
        error: str
    ) -> None:
        """Emit recovery failed event."""
        await self.emitter.emit_now(
            EventType.AGENT_RECOVERY_FAILED,
            {
                "agent_name": agent_name,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    
    async def on_dead_letter_queued(
        self,
        task_id: str,
        task_type: str,
        error: str,
        attempts: int,
    ) -> None:
        """Emit dead letter queued event."""
        await self.emitter.emit(Event(
            event_type=EventType.DEAD_LETTER_QUEUED,
            data={
                "task_id": task_id,
                "task_type": task_type,
                "error": error,
                "attempts": attempts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))


# Global event emitter instance
_global_emitter: EventEmitter | None = None
_global_bridge: AgentEventBridge | None = None


def get_event_emitter() -> EventEmitter:
    """Get or create the global event emitter."""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = EventEmitter()
    return _global_emitter


def get_event_bridge() -> AgentEventBridge | None:
    """Get the global event bridge if configured."""
    return _global_bridge


async def configure_event_system(
    swarm: AgentSwarm | None = None,
    scheduler: TaskScheduler | None = None,
    recovery: AgentRecovery | None = None,
) -> tuple[EventEmitter, AgentEventBridge]:
    """
    Configure and start the event system.
    
    Args:
        swarm: Agent swarm for health monitoring.
        scheduler: Task scheduler for metrics.
        recovery: Recovery system for status events.
        
    Returns:
        Tuple of (EventEmitter, AgentEventBridge).
    """
    global _global_emitter, _global_bridge
    
    emitter = get_event_emitter()
    await emitter.start()
    
    bridge = AgentEventBridge(
        emitter=emitter,
        swarm=swarm,
        scheduler=scheduler,
        recovery=recovery,
    )
    await bridge.start()
    
    _global_bridge = bridge
    
    logger.info("Event system configured and started")
    
    return emitter, bridge


async def shutdown_event_system() -> None:
    """Shutdown the event system."""
    global _global_emitter, _global_bridge
    
    if _global_bridge:
        await _global_bridge.stop()
        _global_bridge = None
    
    if _global_emitter:
        await _global_emitter.stop()
        _global_emitter = None
    
    logger.info("Event system shutdown complete")
