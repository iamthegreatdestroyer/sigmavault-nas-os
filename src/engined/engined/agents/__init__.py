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
    # Core infrastructure
    'BaseAgent',
    'AgentState',
    'AgentCapability',
    'AgentTask',
    'TaskResult',
    'TaskPriority',
    'AgentRegistry',
    # Agent tiers
    'TIER_1_AGENTS',
    'TIER_2_AGENTS',
    # Legacy swarm
    'AgentSwarm',
    'TaskScheduler',
    'AgentRecovery',
    'CircuitBreaker',
    'CircuitState',
    # Events
    'EventEmitter',
    'EventType',
    'Event',
    'AgentEventBridge',
    'configure_event_system',
    'shutdown_event_system',
    'get_event_emitter',
    'get_event_bridge',
    'MemoryStore',
    'MemoryType',
    'MemoryPriority',
    'MemoryEntry',
    'AgentMemory',
    'init_memory_system',
    'shutdown_memory_system',
    'get_memory_store',
    'get_agent_memory',
    'SelfTuner',
    'TuningStrategy',
    'TunableParameter',
    'ParameterType',
    'PerformanceTracker',
    'init_tuning_system',
    'shutdown_tuning_system',
    'get_tuner',
]
