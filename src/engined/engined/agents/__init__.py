"""
SigmaVault Agents Package

Contains AI agent implementations and swarm management.
"""

# Core infrastructure
from .base import (
    BaseAgent,
    AgentState,
    AgentCapability,
    AgentTask,
    TaskResult,
    TaskPriority,
)
from .registry import AgentRegistry

# Agent tiers
from .tier1 import TIER_1_AGENTS
from .tier2 import TIER_2_AGENTS

# Legacy swarm management
from .swarm import AgentSwarm
from .scheduler import TaskScheduler
from .recovery import AgentRecovery, CircuitBreaker, CircuitState
from .events import (
    EventEmitter, 
    EventType, 
    Event,
    AgentEventBridge,
    configure_event_system,
    shutdown_event_system,
    get_event_emitter,
    get_event_bridge,
)
from .memory import (
    MemoryStore,
    MemoryType,
    MemoryPriority,
    MemoryEntry,
    AgentMemory,
    init_memory_system,
    shutdown_memory_system,
    get_memory_store,
    get_agent_memory,
)
from .tuning import (
    SelfTuner,
    TuningStrategy,
    TunableParameter,
    ParameterType,
    PerformanceTracker,
    init_tuning_system,
    shutdown_tuning_system,
    get_tuner,
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