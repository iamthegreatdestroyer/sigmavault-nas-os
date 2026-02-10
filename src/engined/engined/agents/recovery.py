"""
SigmaVault Agent Recovery System

Self-healing agent recovery with circuit breakers, health monitoring, and auto-restart.
Part of the Elite Agent Collective autonomy framework.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engined.agents.swarm import Agent, AgentSwarm

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for an individual agent.
    
    Prevents cascading failures by temporarily stopping requests to failing agents.
    """
    agent_id: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    half_open_max_calls: int = 3

    # State tracking
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    half_open_calls: int = 0

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self._close()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset consecutive failures

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._open()

    def can_execute(self) -> bool:
        """Check if operations are allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self._half_open()
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return False

    def _open(self) -> None:
        """Open the circuit (stop allowing requests)."""
        self.state = CircuitState.OPEN
        self.half_open_calls = 0
        self.success_count = 0
        logger.warning(f"Circuit breaker OPENED for agent {self.agent_id}")
        # Emit event asynchronously
        self._emit_circuit_event("open")

    def _half_open(self) -> None:
        """Move to half-open state (allow limited testing)."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
        logger.info(f"Circuit breaker HALF-OPEN for agent {self.agent_id}")

    def _close(self) -> None:
        """Close the circuit (resume normal operation)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0
        logger.info(f"Circuit breaker CLOSED for agent {self.agent_id}")
        # Emit event asynchronously
        self._emit_circuit_event("closed")

    def _emit_circuit_event(self, event_type: str) -> None:
        """Emit circuit breaker event to event bridge."""
        try:
            from engined.agents.events import get_event_bridge
            bridge = get_event_bridge()
            if bridge:
                import asyncio
                if event_type == "open":
                    asyncio.create_task(
                        bridge.on_circuit_breaker_open(self.agent_id, self.failure_count)
                    )
                elif event_type == "closed":
                    asyncio.create_task(
                        bridge.on_circuit_breaker_closed(self.agent_id)
                    )
        except Exception:
            pass  # Don't fail on event emission errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for monitoring."""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


class HealthCalculator:
    """
    Calculates agent health scores based on multiple factors.
    
    Health Score (0-100) is computed from:
    - Success rate (40% weight)
    - Response time (30% weight)
    - Circuit breaker state (20% weight)
    - Uptime (10% weight)
    """

    # Thresholds for scoring
    RESPONSE_TIME_EXCELLENT_MS = 50
    RESPONSE_TIME_GOOD_MS = 200
    RESPONSE_TIME_ACCEPTABLE_MS = 1000

    @staticmethod
    def calculate(
        agent: Agent,
        circuit: CircuitBreaker,
        uptime_seconds: float,
    ) -> float:
        """Calculate health score for an agent."""
        # Success rate score (0-40 points)
        success_score = agent.success_rate * 40

        # Response time score (0-30 points)
        avg_ms = agent.avg_response_time_ms
        if avg_ms <= HealthCalculator.RESPONSE_TIME_EXCELLENT_MS:
            response_score = 30
        elif avg_ms <= HealthCalculator.RESPONSE_TIME_GOOD_MS:
            response_score = 25
        elif avg_ms <= HealthCalculator.RESPONSE_TIME_ACCEPTABLE_MS:
            response_score = 15
        else:
            response_score = max(0, 10 - (avg_ms - 1000) / 500)

        # Circuit breaker score (0-20 points)
        if circuit.state == CircuitState.CLOSED:
            circuit_score = 20
        elif circuit.state == CircuitState.HALF_OPEN:
            circuit_score = 10
        else:  # OPEN
            circuit_score = 0

        # Uptime score (0-10 points)
        # Full score after 1 hour of uptime
        uptime_hours = uptime_seconds / 3600
        uptime_score = min(10, uptime_hours * 10)

        total = success_score + response_score + circuit_score + uptime_score
        return round(min(100, max(0, total)), 1)


class AgentRecovery:
    """
    Manages agent recovery and self-healing.
    
    Features:
    - Automatic restart of failed agents
    - Circuit breakers for cascading failure prevention
    - Health monitoring and scoring
    - Retry with exponential backoff
    """

    def __init__(
        self,
        swarm: AgentSwarm,
        check_interval: float = 5.0,
        max_restart_attempts: int = 3,
        restart_cooldown: float = 60.0,
    ):
        self.swarm = swarm
        self.check_interval = check_interval
        self.max_restart_attempts = max_restart_attempts
        self.restart_cooldown = restart_cooldown

        # Circuit breakers per agent
        self.circuits: dict[str, CircuitBreaker] = {}

        # Restart tracking
        self._restart_attempts: dict[str, int] = {}
        self._last_restart_time: dict[str, float] = {}

        # Health scores cache
        self._health_scores: dict[str, float] = {}

        # Monitor task
        self._monitor_task: asyncio.Task | None = None
        self._running = False

        logger.info(
            f"AgentRecovery initialized: check_interval={check_interval}s, "
            f"max_restarts={max_restart_attempts}"
        )

    def get_circuit(self, agent_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for an agent."""
        if agent_id not in self.circuits:
            self.circuits[agent_id] = CircuitBreaker(agent_id=agent_id)
        return self.circuits[agent_id]

    def record_success(self, agent_id: str) -> None:
        """Record successful task completion for an agent."""
        circuit = self.get_circuit(agent_id)
        circuit.record_success()

        # Reset restart attempts on success
        self._restart_attempts[agent_id] = 0

    def record_failure(self, agent_id: str) -> None:
        """Record task failure for an agent."""
        circuit = self.get_circuit(agent_id)
        circuit.record_failure()

    def can_assign_task(self, agent_id: str) -> bool:
        """Check if tasks can be assigned to an agent."""
        circuit = self.get_circuit(agent_id)
        return circuit.can_execute()

    def get_health_score(self, agent_id: str) -> float:
        """Get cached health score for an agent."""
        return self._health_scores.get(agent_id, 100.0)

    def get_all_health_scores(self) -> dict[str, float]:
        """Get all agent health scores."""
        return dict(self._health_scores)

    async def start_monitoring(self) -> None:
        """Start the health monitoring loop."""
        if self._running:
            logger.warning("Recovery monitoring already running")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Agent recovery monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the health monitoring loop."""
        if not self._running:
            return

        self._running = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Agent recovery monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        logger.debug("Recovery monitor loop started")

        while self._running:
            try:
                await self._check_all_agents()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.check_interval)

        logger.debug("Recovery monitor loop stopped")

    async def _check_all_agents(self) -> None:
        """Check health of all agents and attempt recovery if needed."""
        from engined.agents.swarm import AgentStatus

        for agent_id, agent in self.swarm.agents.items():
            # Calculate health score
            circuit = self.get_circuit(agent_id)
            health = HealthCalculator.calculate(
                agent=agent,
                circuit=circuit,
                uptime_seconds=self.swarm.uptime_seconds,
            )
            self._health_scores[agent_id] = health

            # Check if agent needs recovery
            if agent.status == AgentStatus.ERROR or (agent.status == AgentStatus.OFFLINE and self.swarm.is_initialized):
                await self._attempt_recovery(agent_id)
            elif health < 30 and circuit.state == CircuitState.OPEN:
                # Low health with open circuit - consider restart
                await self._attempt_recovery(agent_id)

    async def _attempt_recovery(self, agent_id: str) -> bool:
        """
        Attempt to recover a failed agent.
        
        Returns True if recovery was successful.
        """
        from engined.agents.swarm import AgentStatus

        agent = self.swarm.agents.get(agent_id)
        if not agent:
            return False

        # Check restart cooldown
        last_restart = self._last_restart_time.get(agent_id, 0)
        if (time.time() - last_restart) < self.restart_cooldown:
            logger.debug(f"Agent {agent_id} in restart cooldown")
            return False

        # Check restart attempts
        attempts = self._restart_attempts.get(agent_id, 0)
        if attempts >= self.max_restart_attempts:
            logger.warning(
                f"Agent {agent_id} exceeded max restart attempts ({attempts})"
            )
            return False

        # Attempt restart
        logger.info(f"Attempting recovery of agent {agent_id} (attempt {attempts + 1})")

        # Emit recovery started event
        await self._emit_recovery_event("started", agent_id, attempts + 1)

        try:
            # Reset agent state
            agent.status = AgentStatus.IDLE
            agent.current_task_id = None

            # Reset circuit breaker
            circuit = self.get_circuit(agent_id)
            circuit._close()

            # Track restart
            self._restart_attempts[agent_id] = attempts + 1
            self._last_restart_time[agent_id] = time.time()

            # Emit recovery success event
            await self._emit_recovery_event("success", agent_id)

            logger.info(f"Agent {agent_id} recovered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to recover agent {agent_id}: {e}")
            agent.status = AgentStatus.ERROR

            # Emit recovery failed event
            await self._emit_recovery_event("failed", agent_id, error=str(e))

            return False

    async def _emit_recovery_event(
        self,
        event_type: str,
        agent_id: str,
        attempt: int = 0,
        error: str = "",
    ) -> None:
        """Emit recovery event to event bridge."""
        try:
            from engined.agents.events import get_event_bridge
            bridge = get_event_bridge()
            if bridge:
                if event_type == "started":
                    await bridge.on_recovery_started(agent_id, attempt)
                elif event_type == "success":
                    await bridge.on_recovery_success(agent_id)
                elif event_type == "failed":
                    await bridge.on_recovery_failed(agent_id, error)
        except Exception:
            pass  # Don't fail on event emission errors

    def get_status(self) -> dict[str, Any]:
        """Get recovery system status."""
        circuit_states = {
            agent_id: circuit.state.value
            for agent_id, circuit in self.circuits.items()
        }

        open_circuits = sum(
            1 for c in self.circuits.values() if c.state == CircuitState.OPEN
        )

        return {
            "monitoring_active": self._running,
            "total_circuits": len(self.circuits),
            "open_circuits": open_circuits,
            "circuit_states": circuit_states,
            "restart_attempts": dict(self._restart_attempts),
            "health_scores": self._health_scores,
            "agents_below_50_health": sum(
                1 for h in self._health_scores.values() if h < 50
            ),
        }


class RetryStrategy:
    """
    Retry strategy with exponential backoff.
    
    Used for task retry when agent processing fails.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    async def execute_with_retry(
        self,
        operation: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Execute an operation with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Operation failed after {self.max_retries + 1} attempts: {e}"
                    )

        raise last_exception


class DeadLetterQueue:
    """
    Dead letter queue for tasks that failed all retry attempts.
    
    Allows manual inspection and replay of failed tasks.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def add(
        self,
        task_id: str,
        task_type: str,
        payload: dict[str, Any],
        error: str,
        retry_count: int,
    ) -> None:
        """Add a failed task to the dead letter queue."""
        async with self._lock:
            entry = {
                "task_id": task_id,
                "task_type": task_type,
                "payload": payload,
                "error": error,
                "retry_count": retry_count,
                "failed_at": datetime.now(UTC).isoformat(),
            }

            self._queue.append(entry)

            # Trim if over max size (remove oldest)
            if len(self._queue) > self.max_size:
                self._queue = self._queue[-self.max_size:]

            logger.info(f"Task {task_id} added to dead letter queue: {error}")

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all entries in the dead letter queue."""
        async with self._lock:
            return list(self._queue)

    async def remove(self, task_id: str) -> bool:
        """Remove a task from the dead letter queue."""
        async with self._lock:
            for i, entry in enumerate(self._queue):
                if entry["task_id"] == task_id:
                    self._queue.pop(i)
                    return True
        return False

    async def clear(self) -> int:
        """Clear all entries and return count removed."""
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    def size(self) -> int:
        """Get current queue size."""
        return len(self._queue)
