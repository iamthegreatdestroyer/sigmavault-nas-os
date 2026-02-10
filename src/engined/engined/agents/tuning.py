"""
Self-Tuning System for Elite Agent Collective.

Implements adaptive parameter optimization based on memory insights and
performance metrics. The system learns from past task executions to
automatically tune scheduler, recovery, and agent parameters.

Features:
- Performance-based parameter adjustment
- Memory-informed optimization
- Gradient-free optimization (evolutionary strategies)
- Safe parameter boundaries
- Rollback on degradation
"""

from __future__ import annotations

import asyncio
import logging
import random
import statistics
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TuningStrategy(str, Enum):
    """Strategies for parameter tuning."""
    GRADIENT_FREE = "gradient_free"   # Evolutionary, no gradients needed
    BAYESIAN = "bayesian"              # Bayesian optimization
    ADAPTIVE = "adaptive"              # Rule-based adaptive
    MANUAL = "manual"                  # Manual tuning only


class ParameterType(str, Enum):
    """Types of tunable parameters."""
    CONTINUOUS = "continuous"  # Float values
    DISCRETE = "discrete"      # Integer values
    CATEGORICAL = "categorical"  # Enum/choice values


@dataclass
class TunableParameter:
    """A parameter that can be tuned by the self-tuning system."""
    name: str
    param_type: ParameterType
    current_value: Any
    default_value: Any
    min_value: float | None = None
    max_value: float | None = None
    choices: list[Any] | None = None  # For categorical
    step_size: float = 0.1  # For gradient-free optimization
    description: str = ""

    def get_neighbor(self) -> Any:
        """Get a neighboring value for exploration."""
        if self.param_type == ParameterType.CONTINUOUS:
            delta = random.gauss(0, self.step_size * (self.max_value - self.min_value))
            new_value = self.current_value + delta
            return max(self.min_value, min(self.max_value, new_value))
        elif self.param_type == ParameterType.DISCRETE:
            delta = random.choice([-1, 0, 1])
            new_value = int(self.current_value + delta)
            if self.min_value is not None and self.max_value is not None:
                return max(int(self.min_value), min(int(self.max_value), new_value))
            return new_value
        elif self.param_type == ParameterType.CATEGORICAL:
            if self.choices:
                return random.choice(self.choices)
        return self.current_value

    def validate(self, value: Any) -> bool:
        """Validate a value is within bounds."""
        if self.param_type == ParameterType.CONTINUOUS:
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
            return True
        elif self.param_type == ParameterType.DISCRETE:
            if not isinstance(value, int):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
            return True
        elif self.param_type == ParameterType.CATEGORICAL:
            return value in (self.choices or [])
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.param_type.value,
            "current_value": self.current_value,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "choices": self.choices,
            "description": self.description,
        }


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time."""
    timestamp: datetime
    parameters: dict[str, Any]
    metrics: dict[str, float]
    score: float  # Composite performance score


@dataclass
class TuningSession:
    """A tuning session with exploration results."""
    session_id: str
    started_at: datetime
    ended_at: datetime | None = None
    baseline_score: float = 0.0
    best_score: float = 0.0
    best_params: dict[str, Any] = field(default_factory=dict)
    iterations: int = 0
    improvements: int = 0


class PerformanceTracker:
    """
    Tracks performance metrics over time for tuning decisions.
    
    Uses sliding windows and statistical analysis to determine
    if parameter changes improved or degraded performance.
    """

    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._metrics: dict[str, deque] = {}
        self._snapshots: deque = deque(maxlen=1000)

    def record_metric(self, name: str, value: float) -> None:
        """Record a metric value."""
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=self._window_size)
        self._metrics[name].append(value)

    def record_snapshot(
        self,
        parameters: dict[str, Any],
        metrics: dict[str, float],
        score: float,
    ) -> None:
        """Record a performance snapshot."""
        self._snapshots.append(PerformanceSnapshot(
            timestamp=datetime.now(),
            parameters=parameters.copy(),
            metrics=metrics.copy(),
            score=score,
        ))

    def get_recent_average(self, metric_name: str) -> float | None:
        """Get recent average for a metric."""
        values = self._metrics.get(metric_name)
        if not values or len(values) < 2:
            return None
        return statistics.mean(values)

    def get_trend(self, metric_name: str) -> float | None:
        """
        Get trend direction for a metric.
        
        Returns positive for improving, negative for degrading.
        """
        values = self._metrics.get(metric_name)
        if not values or len(values) < 10:
            return None

        # Compare recent half to older half
        midpoint = len(values) // 2
        older = list(values)[:midpoint]
        recent = list(values)[midpoint:]

        if not older or not recent:
            return None

        older_avg = statistics.mean(older)
        recent_avg = statistics.mean(recent)

        if older_avg == 0:
            return 0.0

        return (recent_avg - older_avg) / abs(older_avg)

    def is_improving(self, metric_name: str, higher_is_better: bool = True) -> bool:
        """Check if a metric is trending in the desired direction."""
        trend = self.get_trend(metric_name)
        if trend is None:
            return False
        if higher_is_better:
            return trend > 0.05  # 5% improvement threshold
        else:
            return trend < -0.05  # 5% reduction threshold

    def compute_score(
        self,
        weights: dict[str, float] | None = None,
        higher_is_better: dict[str, bool] | None = None,
    ) -> float:
        """
        Compute composite performance score.
        
        Uses weighted combination of normalized metrics.
        """
        if not weights:
            weights = {
                "success_rate": 1.0,
                "avg_latency_ms": -0.5,  # Lower is better
                "throughput": 0.8,
                "error_rate": -1.0,  # Lower is better
            }

        if not higher_is_better:
            higher_is_better = {
                "success_rate": True,
                "avg_latency_ms": False,
                "throughput": True,
                "error_rate": False,
            }

        score = 0.0
        total_weight = 0.0

        for metric, weight in weights.items():
            avg = self.get_recent_average(metric)
            if avg is not None:
                # Normalize: positive contribution for higher_is_better
                contribution = avg if higher_is_better.get(metric, True) else (1 / (1 + avg))
                score += abs(weight) * contribution
                total_weight += abs(weight)

        return score / total_weight if total_weight > 0 else 0.0


class SelfTuner:
    """
    Self-tuning system for adaptive parameter optimization.
    
    Uses evolutionary strategies and memory insights to automatically
    tune system parameters for optimal performance.
    """

    def __init__(
        self,
        strategy: TuningStrategy = TuningStrategy.GRADIENT_FREE,
        exploration_rate: float = 0.1,
        min_samples_before_tuning: int = 50,
        tuning_interval: float = 300.0,  # 5 minutes
        rollback_threshold: float = 0.9,  # Rollback if score drops below 90%
    ) -> None:
        self._strategy = strategy
        self._exploration_rate = exploration_rate
        self._min_samples = min_samples_before_tuning
        self._tuning_interval = tuning_interval
        self._rollback_threshold = rollback_threshold

        self._parameters: dict[str, TunableParameter] = {}
        self._tracker = PerformanceTracker()
        self._current_session: TuningSession | None = None
        self._sessions: list[TuningSession] = []
        self._best_known: dict[str, Any] = {}
        self._best_score: float = 0.0

        self._running = False
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        # Callbacks for applying parameter changes
        self._apply_callbacks: dict[str, Callable[[str, Any], None]] = {}

        # Initialize default tunable parameters
        self._init_default_parameters()

    def _init_default_parameters(self) -> None:
        """Initialize default tunable parameters for the autonomy system."""
        # Scheduler parameters
        self.register_parameter(TunableParameter(
            name="scheduler.max_workers",
            param_type=ParameterType.DISCRETE,
            current_value=10,
            default_value=10,
            min_value=2,
            max_value=50,
            description="Maximum concurrent worker tasks",
        ))
        self.register_parameter(TunableParameter(
            name="scheduler.rate_limit",
            param_type=ParameterType.CONTINUOUS,
            current_value=100.0,
            default_value=100.0,
            min_value=10.0,
            max_value=1000.0,
            step_size=0.1,
            description="Task dispatch rate limit per second",
        ))
        self.register_parameter(TunableParameter(
            name="scheduler.queue_size",
            param_type=ParameterType.DISCRETE,
            current_value=1000,
            default_value=1000,
            min_value=100,
            max_value=10000,
            description="Maximum task queue size",
        ))

        # Recovery parameters
        self.register_parameter(TunableParameter(
            name="recovery.health_check_interval",
            param_type=ParameterType.CONTINUOUS,
            current_value=30.0,
            default_value=30.0,
            min_value=5.0,
            max_value=300.0,
            step_size=0.1,
            description="Health check interval in seconds",
        ))
        self.register_parameter(TunableParameter(
            name="recovery.restart_cooldown",
            param_type=ParameterType.CONTINUOUS,
            current_value=60.0,
            default_value=60.0,
            min_value=10.0,
            max_value=600.0,
            step_size=0.1,
            description="Cooldown between restart attempts",
        ))
        self.register_parameter(TunableParameter(
            name="recovery.max_restart_attempts",
            param_type=ParameterType.DISCRETE,
            current_value=3,
            default_value=3,
            min_value=1,
            max_value=10,
            description="Maximum restart attempts before circuit breaker",
        ))

        # Memory parameters
        self.register_parameter(TunableParameter(
            name="memory.consolidation_interval",
            param_type=ParameterType.CONTINUOUS,
            current_value=300.0,
            default_value=300.0,
            min_value=60.0,
            max_value=3600.0,
            step_size=0.1,
            description="Memory consolidation interval in seconds",
        ))
        self.register_parameter(TunableParameter(
            name="memory.decay_interval",
            param_type=ParameterType.CONTINUOUS,
            current_value=3600.0,
            default_value=3600.0,
            min_value=300.0,
            max_value=86400.0,
            step_size=0.1,
            description="Memory decay interval in seconds",
        ))

    def register_parameter(self, param: TunableParameter) -> None:
        """Register a tunable parameter."""
        self._parameters[param.name] = param
        if param.name not in self._best_known:
            self._best_known[param.name] = param.current_value

    def register_apply_callback(
        self,
        param_name: str,
        callback: Callable[[str, Any], None],
    ) -> None:
        """Register callback to apply parameter changes."""
        self._apply_callbacks[param_name] = callback

    def record_task_completion(
        self,
        success: bool,
        latency_ms: float,
        task_type: str = "general",
    ) -> None:
        """Record a task completion for performance tracking."""
        self._tracker.record_metric("success_rate", 1.0 if success else 0.0)
        self._tracker.record_metric("avg_latency_ms", latency_ms)
        self._tracker.record_metric("throughput", 1.0)  # Count
        if not success:
            self._tracker.record_metric("error_rate", 1.0)
        else:
            self._tracker.record_metric("error_rate", 0.0)

    def record_metric(self, name: str, value: float) -> None:
        """Record arbitrary metric for tuning decisions."""
        self._tracker.record_metric(name, value)

    async def start(self) -> None:
        """Start the self-tuning background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._tuning_loop())
        logger.info("SelfTuner started with %s strategy", self._strategy.value)

    async def stop(self) -> None:
        """Stop the self-tuning background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SelfTuner stopped")

    async def _tuning_loop(self) -> None:
        """Background loop for periodic tuning."""
        while self._running:
            await asyncio.sleep(self._tuning_interval)

            async with self._lock:
                # Check if we have enough samples
                success_values = self._tracker._metrics.get("success_rate")
                if not success_values or len(success_values) < self._min_samples:
                    continue

                # Compute current score
                current_score = self._tracker.compute_score()

                # Record snapshot
                current_params = self._get_current_params()
                self._tracker.record_snapshot(
                    parameters=current_params,
                    metrics=self._get_current_metrics(),
                    score=current_score,
                )

                # Check if we need to rollback
                if self._best_score > 0 and current_score < self._rollback_threshold * self._best_score:
                    await self._rollback_to_best()
                    continue

                # Update best if improved
                if current_score > self._best_score:
                    self._best_score = current_score
                    self._best_known = current_params.copy()
                    if self._current_session:
                        self._current_session.best_score = current_score
                        self._current_session.best_params = current_params.copy()
                        self._current_session.improvements += 1

                # Explore new parameters
                if self._strategy == TuningStrategy.GRADIENT_FREE:
                    await self._gradient_free_step()
                elif self._strategy == TuningStrategy.ADAPTIVE:
                    await self._adaptive_step()

    def _get_current_params(self) -> dict[str, Any]:
        """Get current parameter values."""
        return {name: p.current_value for name, p in self._parameters.items()}

    def _get_current_metrics(self) -> dict[str, float]:
        """Get current average metrics."""
        result = {}
        for name in ["success_rate", "avg_latency_ms", "throughput", "error_rate"]:
            avg = self._tracker.get_recent_average(name)
            if avg is not None:
                result[name] = avg
        return result

    async def _gradient_free_step(self) -> None:
        """Perform one step of gradient-free optimization."""
        if random.random() > self._exploration_rate:
            return  # Exploit current best

        # Pick random parameter to explore
        param_name = random.choice(list(self._parameters.keys()))
        param = self._parameters[param_name]

        # Generate neighbor
        new_value = param.get_neighbor()
        if param.validate(new_value) and new_value != param.current_value:
            old_value = param.current_value
            param.current_value = new_value

            # Apply change via callback if registered
            if param_name in self._apply_callbacks:
                try:
                    self._apply_callbacks[param_name](param_name, new_value)
                except Exception as e:
                    logger.error(f"Failed to apply parameter {param_name}: {e}")
                    param.current_value = old_value
                    return

            logger.debug(f"Tuned {param_name}: {old_value} -> {new_value}")

            if self._current_session:
                self._current_session.iterations += 1

    async def _adaptive_step(self) -> None:
        """Perform rule-based adaptive tuning."""
        # Example: If error rate is high, reduce rate limit
        error_trend = self._tracker.get_trend("error_rate")
        if error_trend is not None and error_trend > 0.1:
            rate_param = self._parameters.get("scheduler.rate_limit")
            if rate_param:
                new_rate = max(rate_param.min_value, rate_param.current_value * 0.9)
                rate_param.current_value = new_rate
                logger.info(f"Adaptive: Reduced rate_limit to {new_rate} due to high error rate")

        # If latency is high, increase workers
        latency_trend = self._tracker.get_trend("avg_latency_ms")
        if latency_trend is not None and latency_trend > 0.2:
            workers_param = self._parameters.get("scheduler.max_workers")
            if workers_param:
                new_workers = min(workers_param.max_value, workers_param.current_value + 1)
                workers_param.current_value = int(new_workers)
                logger.info(f"Adaptive: Increased max_workers to {new_workers} due to high latency")

    async def _rollback_to_best(self) -> None:
        """Rollback all parameters to best known values."""
        logger.warning("Performance degraded, rolling back to best known parameters")
        for name, value in self._best_known.items():
            if name in self._parameters:
                self._parameters[name].current_value = value
                if name in self._apply_callbacks:
                    try:
                        self._apply_callbacks[name](name, value)
                    except Exception as e:
                        logger.error(f"Failed to rollback {name}: {e}")

    async def start_session(self) -> str:
        """Start a new tuning session."""
        async with self._lock:
            session_id = f"tune_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._current_session = TuningSession(
                session_id=session_id,
                started_at=datetime.now(),
                baseline_score=self._tracker.compute_score(),
            )
            logger.info(f"Started tuning session: {session_id}")
            return session_id

    async def end_session(self) -> TuningSession | None:
        """End current tuning session."""
        async with self._lock:
            if not self._current_session:
                return None
            self._current_session.ended_at = datetime.now()
            self._current_session.best_score = self._best_score
            self._current_session.best_params = self._best_known.copy()
            self._sessions.append(self._current_session)
            session = self._current_session
            self._current_session = None
            logger.info(
                f"Ended tuning session: {session.session_id}, "
                f"iterations={session.iterations}, improvements={session.improvements}"
            )
            return session

    def get_parameter(self, name: str) -> TunableParameter | None:
        """Get a tunable parameter by name."""
        return self._parameters.get(name)

    def set_parameter(self, name: str, value: Any) -> bool:
        """Manually set a parameter value."""
        param = self._parameters.get(name)
        if not param:
            return False
        if not param.validate(value):
            return False
        param.current_value = value
        if name in self._apply_callbacks:
            try:
                self._apply_callbacks[name](name, value)
            except Exception as e:
                logger.error(f"Failed to apply {name}: {e}")
        return True

    def get_metrics(self) -> dict[str, Any]:
        """Get tuning system metrics."""
        return {
            "strategy": self._strategy.value,
            "is_running": self._running,
            "parameters_count": len(self._parameters),
            "best_score": self._best_score,
            "current_score": self._tracker.compute_score(),
            "sessions_completed": len(self._sessions),
            "current_session": self._current_session.session_id if self._current_session else None,
            "exploration_rate": self._exploration_rate,
        }

    def get_all_parameters(self) -> dict[str, dict[str, Any]]:
        """Get all tunable parameters with their current values."""
        return {name: p.to_dict() for name, p in self._parameters.items()}


# Global tuner instance
_tuner: SelfTuner | None = None


async def init_tuning_system(
    strategy: TuningStrategy = TuningStrategy.GRADIENT_FREE,
    exploration_rate: float = 0.1,
    tuning_interval: float = 300.0,
) -> SelfTuner:
    """Initialize the global self-tuning system."""
    global _tuner
    if _tuner is None:
        _tuner = SelfTuner(
            strategy=strategy,
            exploration_rate=exploration_rate,
            tuning_interval=tuning_interval,
        )
        await _tuner.start()
        logger.info("Self-tuning system initialized")
    return _tuner


async def shutdown_tuning_system() -> None:
    """Shutdown the global self-tuning system."""
    global _tuner
    if _tuner:
        await _tuner.stop()
        _tuner = None
        logger.info("Self-tuning system shutdown")


def get_tuner() -> SelfTuner | None:
    """Get the global tuner instance."""
    return _tuner
