"""
SigmaVault Agent Swarm

Manages the collective of 40 specialized AI agents for intelligent operations.
The Elite Agent Collective provides AI-powered compression, quantum-resistant 
encryption, and intelligent storage management.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentTier(str, Enum):
    """Agent tier classification."""
    CORE = "core"
    SPECIALIST = "specialist"
    SUPPORT = "support"


class AgentStatus(str, Enum):
    """Agent operational status."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class Agent:
    """Represents a single AI agent in the swarm."""
    agent_id: str
    name: str
    tier: AgentTier
    specialty: str
    status: AgentStatus = AgentStatus.OFFLINE
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_task_id: Optional[str] = None
    avg_response_time_ms: float = 0.0
    memory_usage_mb: float = 128.0
    last_active: Optional[datetime] = None
    _response_times: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 1.0
        return self.tasks_completed / total

    def update_response_time(self, time_ms: float) -> None:
        """Update average response time with new measurement."""
        self._response_times.append(time_ms)
        # Keep last 100 measurements
        if len(self._response_times) > 100:
            self._response_times = self._response_times[-100:]
        self.avg_response_time_ms = sum(self._response_times) / len(self._response_times)

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for API responses."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "tier": self.tier.value,
            "specialty": self.specialty,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "success_rate": self.success_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }


@dataclass
class Task:
    """Represents a task submitted to the swarm."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int
    status: str = "queued"
    assigned_agent: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


# 40-Agent Collective Definition
AGENT_DEFINITIONS = [
    # Tier 1: Core Compression Agents (1-10)
    {"name": "TENSOR", "tier": AgentTier.CORE, "specialty": "Deep learning compression models"},
    {"name": "VELOCITY", "tier": AgentTier.CORE, "specialty": "Performance optimization"},
    {"name": "AXIOM", "tier": AgentTier.CORE, "specialty": "Mathematical compression analysis"},
    {"name": "PRISM", "tier": AgentTier.CORE, "specialty": "Data pattern recognition"},
    {"name": "FLUX", "tier": AgentTier.CORE, "specialty": "Adaptive algorithm selection"},
    {"name": "DELTA", "tier": AgentTier.CORE, "specialty": "Differential compression"},
    {"name": "SPARK", "tier": AgentTier.CORE, "specialty": "GPU-accelerated processing"},
    {"name": "WAVE", "tier": AgentTier.CORE, "specialty": "Signal processing compression"},
    {"name": "NEXUS", "tier": AgentTier.CORE, "specialty": "Cross-domain optimization"},
    {"name": "PULSE", "tier": AgentTier.CORE, "specialty": "Real-time compression"},
    
    # Tier 2: Security & Encryption Agents (11-20)
    {"name": "CIPHER", "tier": AgentTier.SPECIALIST, "specialty": "Cryptographic operations"},
    {"name": "FORTRESS", "tier": AgentTier.SPECIALIST, "specialty": "Security hardening"},
    {"name": "QUANTUM", "tier": AgentTier.SPECIALIST, "specialty": "Post-quantum cryptography"},
    {"name": "SENTINEL", "tier": AgentTier.SPECIALIST, "specialty": "Threat detection"},
    {"name": "VAULT", "tier": AgentTier.SPECIALIST, "specialty": "Key management"},
    {"name": "SHIELD", "tier": AgentTier.SPECIALIST, "specialty": "Data integrity verification"},
    {"name": "GUARDIAN", "tier": AgentTier.SPECIALIST, "specialty": "Access control"},
    {"name": "PHANTOM", "tier": AgentTier.SPECIALIST, "specialty": "Secure erasure"},
    {"name": "AEGIS", "tier": AgentTier.SPECIALIST, "specialty": "Defense coordination"},
    {"name": "ORACLE", "tier": AgentTier.SPECIALIST, "specialty": "Security prediction"},
    
    # Tier 3: Storage & Analytics Agents (21-30)
    {"name": "ARCHITECT", "tier": AgentTier.SPECIALIST, "specialty": "Storage architecture"},
    {"name": "LATTICE", "tier": AgentTier.SPECIALIST, "specialty": "ZFS optimization"},
    {"name": "STREAM", "tier": AgentTier.SPECIALIST, "specialty": "Data streaming"},
    {"name": "VERTEX", "tier": AgentTier.SPECIALIST, "specialty": "Graph analytics"},
    {"name": "SENTRY", "tier": AgentTier.SPECIALIST, "specialty": "Storage monitoring"},
    {"name": "FORGE", "tier": AgentTier.SPECIALIST, "specialty": "Data transformation"},
    {"name": "PHOTON", "tier": AgentTier.SPECIALIST, "specialty": "High-speed I/O"},
    {"name": "ATLAS", "tier": AgentTier.SPECIALIST, "specialty": "Storage mapping"},
    {"name": "CHRONICLE", "tier": AgentTier.SPECIALIST, "specialty": "Audit logging"},
    {"name": "BEACON", "tier": AgentTier.SPECIALIST, "specialty": "Discovery services"},
    
    # Tier 4: Network & Integration Agents (31-40)
    {"name": "SYNAPSE", "tier": AgentTier.SUPPORT, "specialty": "API orchestration"},
    {"name": "CRYPTO", "tier": AgentTier.SUPPORT, "specialty": "Network encryption"},
    {"name": "BRIDGE", "tier": AgentTier.SUPPORT, "specialty": "Protocol translation"},
    {"name": "RELAY", "tier": AgentTier.SUPPORT, "specialty": "Message routing"},
    {"name": "MIRROR", "tier": AgentTier.SUPPORT, "specialty": "Replication services"},
    {"name": "MESH", "tier": AgentTier.SUPPORT, "specialty": "PhantomMesh integration"},
    {"name": "HARBOR", "tier": AgentTier.SUPPORT, "specialty": "Connection pooling"},
    {"name": "CONDUIT", "tier": AgentTier.SUPPORT, "specialty": "Data pipeline"},
    {"name": "HELIX", "tier": AgentTier.SUPPORT, "specialty": "Federation services"},
    {"name": "OMNISCIENT", "tier": AgentTier.SUPPORT, "specialty": "Swarm coordination"},
]


class AgentSwarm:
    """
    Manages the collective of 40 specialized AI agents.
    
    The Elite Agent Collective provides:
    - AI-powered compression (90%+ efficiency)
    - Quantum-resistant encryption
    - Intelligent storage management
    - Real-time analytics
    """

    def __init__(self, settings=None):
        self.settings = settings
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.Queue[str] = asyncio.Queue()
        self._active_workers: List[asyncio.Task] = []
        self._is_initialized: bool = False
        self._start_time: Optional[float] = None
        self._completed_tasks: int = 0
        self._lock = asyncio.Lock()
        logger.info("AgentSwarm instance created")

    @property
    def is_initialized(self) -> bool:
        """Check if swarm is initialized and running."""
        return self._is_initialized

    @property
    def uptime_seconds(self) -> float:
        """Get swarm uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def available_agents(self) -> int:
        """Count of idle agents ready for work."""
        return sum(1 for a in self.agents.values() if a.status == AgentStatus.IDLE)

    @property
    def busy_agents(self) -> int:
        """Count of agents currently processing tasks."""
        return sum(1 for a in self.agents.values() if a.status == AgentStatus.BUSY)

    @property
    def queued_tasks(self) -> int:
        """Count of tasks waiting in queue."""
        return self.task_queue.qsize()

    @property
    def completed_tasks(self) -> int:
        """Total completed tasks."""
        return self._completed_tasks

    async def initialize(self) -> None:
        """Initialize the agent swarm with all 40 agents."""
        logger.info("Initializing Elite Agent Collective (40-agent swarm)...")
        
        # Create all 40 agents
        now = datetime.now(timezone.utc)
        for i, agent_def in enumerate(AGENT_DEFINITIONS):
            agent_id = f"agent-{i+1:03d}"
            agent = Agent(
                agent_id=agent_id,
                name=agent_def["name"],
                tier=agent_def["tier"],
                specialty=agent_def["specialty"],
                status=AgentStatus.IDLE,
                last_active=now,
            )
            self.agents[agent_id] = agent
            logger.debug(f"Created agent {agent_id}: {agent.name} ({agent.tier.value})")

        self._start_time = time.time()
        self._is_initialized = True
        
        logger.info(f"Elite Agent Collective initialized: {len(self.agents)} agents active")
        logger.info(f"  - Core agents: {sum(1 for a in self.agents.values() if a.tier == AgentTier.CORE)}")
        logger.info(f"  - Specialist agents: {sum(1 for a in self.agents.values() if a.tier == AgentTier.SPECIALIST)}")
        logger.info(f"  - Support agents: {sum(1 for a in self.agents.values() if a.tier == AgentTier.SUPPORT)}")
        
        await self.start()

    async def start(self) -> None:
        """Start the agent swarm task processors."""
        logger.info("Starting agent swarm workers...")
        
        # Start worker tasks (one per 10 agents for load distribution)
        for i in range(4):
            worker = asyncio.create_task(self._task_worker(f"worker-{i+1}"))
            self._active_workers.append(worker)
        
        logger.info(f"Agent swarm started with {len(self._active_workers)} workers")

    async def stop(self) -> None:
        """Stop the agent swarm gracefully."""
        logger.info("Stopping agent swarm...")

        # Cancel all active workers
        for worker in self._active_workers:
            if not worker.done():
                worker.cancel()

        # Wait for workers to complete
        if self._active_workers:
            await asyncio.gather(*self._active_workers, return_exceptions=True)
        
        # Set all agents to offline
        for agent in self.agents.values():
            agent.status = AgentStatus.OFFLINE

        self._is_initialized = False
        self._active_workers.clear()
        logger.info("Agent swarm stopped")

    async def shutdown(self) -> None:
        """Shutdown wrapper for stop() - backwards compatibility."""
        await self.stop()

    def get_agent_count(self) -> int:
        """Get the number of registered agents."""
        return len(self.agents)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        for agent in self.agents.values():
            if agent.name.upper() == name.upper():
                return agent
        return None

    def list_agents(
        self,
        tier: Optional[AgentTier] = None,
        status: Optional[AgentStatus] = None,
    ) -> List[Agent]:
        """List agents with optional filtering."""
        agents = list(self.agents.values())
        
        if tier is not None:
            agents = [a for a in agents if a.tier == tier]
        if status is not None:
            agents = [a for a in agents if a.status == status]
        
        return agents

    def get_swarm_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status."""
        return {
            "total_agents": len(self.agents),
            "active_agents": self.available_agents + self.busy_agents,
            "idle_agents": self.available_agents,
            "busy_agents": self.busy_agents,
            "error_agents": sum(1 for a in self.agents.values() if a.status == AgentStatus.ERROR),
            "offline_agents": sum(1 for a in self.agents.values() if a.status == AgentStatus.OFFLINE),
            "total_tasks_queued": self.queued_tasks,
            "total_tasks_completed": self._completed_tasks,
            "uptime_seconds": self.uptime_seconds,
            "is_initialized": self._is_initialized,
        }

    async def assign_task(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
    ) -> Optional[str]:
        """
        Assign a task to the most suitable agent.
        
        Returns the assigned agent name or None if no agent available.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent swarm not initialized")

        # Create task
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
        )
        
        # Select best agent based on task type
        agent = self._select_agent_for_task(task_type)
        if agent:
            task.assigned_agent = agent.name
            
        async with self._lock:
            self.tasks[task_id] = task
            await self.task_queue.put(task_id)
        
        logger.info(f"Task {task_id} queued (type={task_type}, priority={priority}, agent={task.assigned_agent})")
        return task.assigned_agent

    def _select_agent_for_task(self, task_type: str) -> Optional[Agent]:
        """Select the most suitable idle agent for a task type."""
        # Map task types to preferred agents
        task_agent_map = {
            "compression": ["TENSOR", "VELOCITY", "AXIOM", "DELTA", "WAVE"],
            "encryption": ["CIPHER", "QUANTUM", "VAULT", "SHIELD"],
            "storage": ["ARCHITECT", "LATTICE", "PHOTON", "ATLAS"],
            "analysis": ["PRISM", "VERTEX", "ORACLE", "CHRONICLE"],
            "network": ["SYNAPSE", "BRIDGE", "RELAY", "MESH"],
            "security": ["FORTRESS", "SENTINEL", "GUARDIAN", "AEGIS"],
        }
        
        preferred_agents = task_agent_map.get(task_type, [])
        
        # Try preferred agents first
        for agent_name in preferred_agents:
            agent = self.get_agent_by_name(agent_name)
            if agent and agent.status == AgentStatus.IDLE:
                return agent
        
        # Fall back to any idle agent
        idle_agents = [a for a in self.agents.values() if a.status == AgentStatus.IDLE]
        if idle_agents:
            # Prefer agents with fewer completed tasks (load balancing)
            return min(idle_agents, key=lambda a: a.tasks_completed)
        
        return None

    async def _task_worker(self, worker_name: str) -> None:
        """Worker coroutine that processes tasks from the queue."""
        logger.debug(f"Task worker {worker_name} started")
        
        while True:
            try:
                # Get next task from queue
                task_id = await self.task_queue.get()
                task = self.tasks.get(task_id)
                
                if not task:
                    continue
                
                # Find available agent
                agent = (
                    self.get_agent_by_name(task.assigned_agent)
                    if task.assigned_agent
                    else self._select_agent_for_task(task.task_type)
                )
                
                if not agent or agent.status != AgentStatus.IDLE:
                    # Re-queue if no agent available
                    await self.task_queue.put(task_id)
                    await asyncio.sleep(0.1)
                    continue
                
                # Execute task
                await self._execute_task(task, agent)
                
            except asyncio.CancelledError:
                logger.debug(f"Task worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Task worker {worker_name} error: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task: Task, agent: Agent) -> None:
        """Execute a task with the assigned agent."""
        start_time = time.time()
        
        try:
            # Mark agent as busy
            agent.status = AgentStatus.BUSY
            agent.current_task_id = task.task_id
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            task.assigned_agent = agent.name
            
            logger.info(f"Agent {agent.name} executing task {task.task_id}")
            
            # Simulate task execution (in real implementation, this would call actual AI models)
            await asyncio.sleep(0.1)  # Minimal delay for simulation
            
            # Mark task complete
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.result = {"status": "success", "agent": agent.name}
            
            # Update agent stats
            agent.tasks_completed += 1
            agent.update_response_time((time.time() - start_time) * 1000)
            agent.last_active = datetime.now(timezone.utc)
            
            async with self._lock:
                self._completed_tasks += 1
            
            logger.info(f"Task {task.task_id} completed by {agent.name}")
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            agent.tasks_failed += 1
            logger.error(f"Task {task.task_id} failed: {e}")
        
        finally:
            agent.status = AgentStatus.IDLE
            agent.current_task_id = None

    async def execute_task(self, agent_type: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using the specified agent type.
        
        Legacy compatibility method.
        """
        task_id = str(uuid.uuid4())
        assigned = await self.assign_task(
            task_id=task_id,
            task_type=agent_type,
            payload=task,
        )
        
        if not assigned:
            return {"status": "queued", "task_id": task_id, "message": "No agent immediately available"}
        
        return {"status": "assigned", "task_id": task_id, "agent": assigned}