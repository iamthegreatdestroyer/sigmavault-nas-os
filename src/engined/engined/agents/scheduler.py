"""
SigmaVault Agent Task Scheduler

Priority-based task scheduling with intelligent agent routing and load balancing.
Part of the Elite Agent Collective autonomy framework.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from engined.agents.swarm import Agent, AgentSwarm, Task

logger = logging.getLogger(__name__)


class TaskPriority(IntEnum):
    """Task priority levels (lower number = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 10
    BACKGROUND = 20


@dataclass(order=True)
class PriorityTask:
    """Wrapper for priority queue ordering."""
    priority: int
    timestamp: float = field(compare=True)
    task_id: str = field(compare=False)
    
    def __init__(self, task_id: str, priority: int):
        self.task_id = task_id
        self.priority = priority
        self.timestamp = time.time()


class TaskRouter:
    """
    Routes tasks to the most suitable agent based on task type and agent capabilities.
    
    Implements intelligent routing with:
    - Task type to agent specialty matching
    - Load balancing across available agents
    - Fallback to any idle agent
    """
    
    # Task type to preferred agent names mapping
    TASK_ROUTING_TABLE: Dict[str, List[str]] = {
        # Compression tasks → Core agents
        "compression": ["TENSOR", "VELOCITY", "AXIOM", "DELTA", "WAVE", "NEXUS"],
        "compression.neural": ["TENSOR", "AXIOM", "PRISM"],
        "compression.fast": ["VELOCITY", "SPARK", "PULSE"],
        "compression.adaptive": ["FLUX", "NEXUS", "DELTA"],
        
        # Encryption tasks → Security agents
        "encryption": ["CIPHER", "QUANTUM", "VAULT", "SHIELD"],
        "encryption.quantum": ["QUANTUM", "CIPHER"],
        "encryption.keys": ["VAULT", "GUARDIAN"],
        "encryption.verify": ["SHIELD", "FORTRESS"],
        
        # Storage tasks → Storage agents
        "storage": ["ARCHITECT", "LATTICE", "PHOTON", "ATLAS"],
        "storage.zfs": ["LATTICE", "ARCHITECT"],
        "storage.io": ["PHOTON", "STREAM"],
        "storage.mapping": ["ATLAS", "BEACON"],
        
        # Analysis tasks → Analytics agents
        "analysis": ["PRISM", "VERTEX", "ORACLE", "CHRONICLE"],
        "analysis.pattern": ["PRISM", "TENSOR"],
        "analysis.graph": ["VERTEX", "NEXUS"],
        "analysis.predict": ["ORACLE", "PRISM"],
        
        # Security tasks → Security agents
        "security": ["FORTRESS", "SENTINEL", "GUARDIAN", "AEGIS", "PHANTOM"],
        "security.threat": ["SENTINEL", "ORACLE"],
        "security.access": ["GUARDIAN", "AEGIS"],
        "security.erase": ["PHANTOM", "SHIELD"],
        
        # Network tasks → Integration agents
        "network": ["SYNAPSE", "BRIDGE", "RELAY", "MESH", "CRYPTO"],
        "network.mesh": ["MESH", "RELAY"],
        "network.protocol": ["BRIDGE", "SYNAPSE"],
        "network.encrypt": ["CRYPTO", "CIPHER"],
    }
    
    def __init__(self, swarm: "AgentSwarm"):
        self.swarm = swarm
    
    def route(self, task_type: str) -> Optional["Agent"]:
        """
        Find the best agent for a task type.
        
        Strategy:
        1. Try exact task type match
        2. Try parent task type (e.g., "compression" for "compression.neural")
        3. Fall back to any idle agent with load balancing
        """
        from engined.agents.swarm import AgentStatus
        
        # Get preferred agents for this task type
        preferred = self._get_preferred_agents(task_type)
        
        # Try preferred agents first
        for agent_name in preferred:
            agent = self.swarm.get_agent_by_name(agent_name)
            if agent and agent.status == AgentStatus.IDLE:
                logger.debug(f"Routed task type '{task_type}' to preferred agent {agent_name}")
                return agent
        
        # Fall back to any idle agent with load balancing
        idle_agents = self.swarm.list_agents(status=AgentStatus.IDLE)
        if idle_agents:
            # Select agent with fewest completed tasks (load balancing)
            agent = min(idle_agents, key=lambda a: a.tasks_completed)
            logger.debug(f"Routed task type '{task_type}' to fallback agent {agent.name}")
            return agent
        
        logger.warning(f"No available agent for task type '{task_type}'")
        return None
    
    def _get_preferred_agents(self, task_type: str) -> List[str]:
        """Get list of preferred agents for a task type."""
        # Try exact match
        if task_type in self.TASK_ROUTING_TABLE:
            return self.TASK_ROUTING_TABLE[task_type]
        
        # Try parent type (e.g., "compression" for "compression.neural")
        if "." in task_type:
            parent_type = task_type.split(".")[0]
            if parent_type in self.TASK_ROUTING_TABLE:
                return self.TASK_ROUTING_TABLE[parent_type]
        
        return []


class TaskScheduler:
    """
    Advanced task scheduler with priority queue, rate limiting, and metrics.
    
    Features:
    - Priority-based scheduling (critical > high > normal > low > background)
    - Rate limiting to prevent task flooding
    - Task timeout handling
    - Metrics collection for monitoring
    """
    
    def __init__(
        self,
        swarm: "AgentSwarm",
        max_concurrent: int = 40,
        rate_limit_per_second: float = 100.0,
    ):
        self.swarm = swarm
        self.router = TaskRouter(swarm)
        self.max_concurrent = max_concurrent
        self.rate_limit_per_second = rate_limit_per_second
        
        # Priority queue (min-heap, lower priority number = higher priority)
        self._queue: List[PriorityTask] = []
        self._queue_lock = asyncio.Lock()
        
        # Rate limiting
        self._last_dispatch_time = 0.0
        self._min_dispatch_interval = 1.0 / rate_limit_per_second
        
        # Metrics
        self._tasks_scheduled = 0
        self._tasks_dispatched = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._total_wait_time_ms = 0.0
        
        # Workers
        self._workers: List[asyncio.Task] = []
        self._running = False
        
        logger.info(
            f"TaskScheduler initialized: max_concurrent={max_concurrent}, "
            f"rate_limit={rate_limit_per_second}/s"
        )
    
    async def start(self, num_workers: int = 4) -> None:
        """Start the scheduler workers."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        
        for i in range(num_workers):
            worker = asyncio.create_task(
                self._worker_loop(f"scheduler-worker-{i+1}")
            )
            self._workers.append(worker)
        
        logger.info(f"TaskScheduler started with {num_workers} workers")
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all workers
        for worker in self._workers:
            if not worker.done():
                worker.cancel()
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        logger.info("TaskScheduler stopped")
    
    async def schedule(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = TaskPriority.NORMAL,
    ) -> str:
        """
        Schedule a task for execution.
        
        Returns the assigned agent name or "queued" if no agent immediately available.
        """
        # Create task in swarm
        agent_name = await self.swarm.assign_task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
        )
        
        # Add to priority queue for scheduling
        priority_task = PriorityTask(task_id, priority)
        
        async with self._queue_lock:
            heapq.heappush(self._queue, priority_task)
            self._tasks_scheduled += 1
        
        logger.debug(
            f"Task {task_id} scheduled: type={task_type}, priority={priority}, "
            f"agent={agent_name or 'pending'}"
        )
        
        return agent_name or "queued"
    
    async def _worker_loop(self, worker_name: str) -> None:
        """Worker loop that processes tasks from the priority queue."""
        logger.debug(f"Worker {worker_name} started")
        
        while self._running:
            try:
                # Get next task from priority queue
                priority_task = await self._dequeue()
                
                if priority_task is None:
                    # Queue empty, wait a bit
                    await asyncio.sleep(0.01)
                    continue
                
                # Rate limiting
                await self._rate_limit()
                
                # Get the actual task
                task = self.swarm.tasks.get(priority_task.task_id)
                if not task:
                    logger.warning(f"Task {priority_task.task_id} not found in swarm")
                    continue
                
                # Route to best agent
                agent = self.router.route(task.task_type)
                if agent:
                    task.assigned_agent = agent.name
                    self._tasks_dispatched += 1
                    
                    # Track wait time
                    wait_time = (time.time() - priority_task.timestamp) * 1000
                    self._total_wait_time_ms += wait_time
                    
                    # Emit task assigned event
                    await self._emit_task_event(
                        "assigned",
                        task.task_id,
                        task.task_type,
                        agent.name,
                        priority_task.priority,
                    )
                    
                    logger.debug(
                        f"Worker {worker_name} dispatched task {task.task_id} "
                        f"to agent {agent.name} (wait={wait_time:.1f}ms)"
                    )
                else:
                    # Re-queue task if no agent available
                    async with self._queue_lock:
                        heapq.heappush(self._queue, priority_task)
                    await asyncio.sleep(0.1)  # Back off if no agents available
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(0.1)
        
        logger.debug(f"Worker {worker_name} stopped")
    
    async def _dequeue(self) -> Optional[PriorityTask]:
        """Dequeue the highest priority task."""
        async with self._queue_lock:
            if self._queue:
                return heapq.heappop(self._queue)
        return None
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting between dispatches."""
        now = time.time()
        elapsed = now - self._last_dispatch_time
        
        if elapsed < self._min_dispatch_interval:
            await asyncio.sleep(self._min_dispatch_interval - elapsed)
        
        self._last_dispatch_time = time.time()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get scheduler metrics."""
        avg_wait_time = 0.0
        if self._tasks_dispatched > 0:
            avg_wait_time = self._total_wait_time_ms / self._tasks_dispatched
        
        return {
            "queue_size": len(self._queue),
            "tasks_scheduled": self._tasks_scheduled,
            "tasks_dispatched": self._tasks_dispatched,
            "tasks_completed": self._tasks_completed,
            "tasks_failed": self._tasks_failed,
            "avg_wait_time_ms": round(avg_wait_time, 2),
            "workers_active": len(self._workers),
            "is_running": self._running,
        }
    
    def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed (called by task processor)."""
        self._tasks_completed += 1
        # Emit completion event asynchronously
        self._emit_completion_event(task_id, success=True)
    
    def mark_failed(self, task_id: str) -> None:
        """Mark a task as failed (called by task processor)."""
        self._tasks_failed += 1
        # Emit failure event asynchronously
        self._emit_completion_event(task_id, success=False)
    
    async def _emit_task_event(
        self,
        event_type: str,
        task_id: str,
        task_type: str,
        agent_name: str,
        priority: int,
    ) -> None:
        """Emit task event to event bridge."""
        try:
            from engined.agents.events import get_event_bridge
            bridge = get_event_bridge()
            if bridge and event_type == "assigned":
                priority_name = self._priority_to_name(priority)
                await bridge.on_task_assigned(task_id, task_type, agent_name, priority_name)
        except Exception:
            pass  # Don't fail on event emission errors
    
    def _emit_completion_event(self, task_id: str, success: bool) -> None:
        """Emit task completion/failure event."""
        try:
            import asyncio
            from engined.agents.events import get_event_bridge
            bridge = get_event_bridge()
            if bridge:
                task = self.swarm.tasks.get(task_id)
                agent_name = task.assigned_agent if task else "unknown"
                if success:
                    asyncio.create_task(
                        bridge.on_task_completed(task_id, agent_name, 0)
                    )
                else:
                    asyncio.create_task(
                        bridge.on_task_failed(task_id, agent_name, "Task failed", False)
                    )
        except Exception:
            pass  # Don't fail on event emission errors
    
    @staticmethod
    def _priority_to_name(priority: int) -> str:
        """Convert priority number to name."""
        if priority <= TaskPriority.CRITICAL:
            return "critical"
        elif priority <= TaskPriority.HIGH:
            return "high"
        elif priority <= TaskPriority.NORMAL:
            return "normal"
        elif priority <= TaskPriority.LOW:
            return "low"
        return "background"
