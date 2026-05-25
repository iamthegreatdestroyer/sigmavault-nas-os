"""
SigmaVault Agents Package

Contains AI agent implementations and swarm management.
"""

# Core infrastructure
from .base import (
    AgentCapability,
    AgentState,
    AgentTask,
    BaseAgent,
    TaskPriority,
    TaskResult,
)
from .events import (
    AgentEventBridge,
    Event,
    EventEmitter,
    EventType,
    configure_event_system,
    get_event_bridge,
    get_event_emitter,
    shutdown_event_system,
)
from .memory import (
    AgentMemory,
    MemoryEntry,
    MemoryPriority,
    MemoryStore,
    MemoryType,
    get_agent_memory,
    get_memory_store,
    init_memory_system,
    shutdown_memory_system,
)
from .recovery import AgentRecovery, CircuitBreaker, CircuitState
from .registry import AgentRegistry
from .scheduler import TaskScheduler

# Legacy swarm management
from .swarm import AgentSwarm

# Agent tiers
from .tier1 import TIER_1_AGENTS
from .tier2 import TIER_2_AGENTS
from .tuning import (
    ParameterType,
    PerformanceTracker,
    SelfTuner,
    TunableParameter,
    TuningStrategy,
    get_tuner,
    init_tuning_system,
    shutdown_tuning_system,
)

__all__ = [
    # Agent tiers
    'TIER_1_AGENTS',
    'TIER_2_AGENTS',
    'AgentCapability',
    'AgentEventBridge',
    'AgentMemory',
    'AgentRecovery',
    'AgentRegistry',
    'AgentState',
    # Legacy swarm
    'AgentSwarm',
    'AgentTask',
    # Core infrastructure
    'BaseAgent',
    'CircuitBreaker',
    'CircuitState',
    'Event',
    # Events
    'EventEmitter',
    'EventType',
    'MemoryEntry',
    'MemoryPriority',
    'MemoryStore',
    'MemoryType',
    'ParameterType',
    'PerformanceTracker',
    'SelfTuner',
    'TaskPriority',
    'TaskResult',
    'TaskScheduler',
    'TunableParameter',
    'TuningStrategy',
    'configure_event_system',
    'get_agent_memory',
    'get_event_bridge',
    'get_event_emitter',
    'get_memory_store',
    'get_tuner',
    'init_memory_system',
    'init_tuning_system',
    'shutdown_event_system',
    'shutdown_memory_system',
    'shutdown_tuning_system',
]
