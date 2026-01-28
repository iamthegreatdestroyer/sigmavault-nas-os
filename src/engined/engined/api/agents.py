"""
Agent Management API Endpoints

Provides REST API for managing the 40-agent AI swarm.
Allows querying agent status, submitting tasks, and monitoring performance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from engined.agents.swarm import AgentSwarm

router = APIRouter()


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


class AgentInfo(BaseModel):
    """Agent information model."""

    agent_id: str = Field(description="Unique agent identifier")
    name: str = Field(description="Agent name")
    tier: AgentTier = Field(description="Agent tier")
    status: AgentStatus = Field(description="Current status")
    specialty: str = Field(description="Agent specialization")
    tasks_completed: int = Field(description="Total tasks completed")
    success_rate: float = Field(description="Success rate (0-1)")
    avg_response_time_ms: float = Field(description="Average response time")
    memory_usage_mb: float = Field(description="Memory usage in MB")
    last_active: str = Field(description="Last activity timestamp")


class SwarmStatus(BaseModel):
    """Agent swarm status model."""

    total_agents: int
    active_agents: int
    idle_agents: int
    busy_agents: int
    error_agents: int
    total_tasks_queued: int
    total_tasks_completed: int
    uptime_seconds: float


class TaskRequest(BaseModel):
    """Request to submit a task to the swarm."""

    task_type: str = Field(description="Type of task (compression, encryption, analysis)")
    payload: dict = Field(description="Task-specific payload")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=low, 10=high)")
    timeout_seconds: int = Field(default=300, ge=30, le=3600, description="Task timeout")


class TaskResponse(BaseModel):
    """Response from task submission."""

    task_id: str
    status: str
    assigned_agent: str | None
    estimated_completion_seconds: int | None
    created_at: str


# Agent definitions based on Master Execution Prompt
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


@router.get("/", response_model=list[AgentInfo])
async def list_agents(
    request: Request,
    tier: AgentTier | None = None,
    status_filter: AgentStatus | None = None,
) -> list[AgentInfo]:
    """
    List all agents in the swarm.
    
    Optionally filter by tier or status.
    """
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    agents = []
    now = datetime.now(timezone.utc)
    
    for i, agent_def in enumerate(AGENT_DEFINITIONS):
        agent_info = AgentInfo(
            agent_id=f"agent-{i+1:03d}",
            name=agent_def["name"],
            tier=agent_def["tier"],
            status=AgentStatus.IDLE if swarm and swarm.is_initialized else AgentStatus.OFFLINE,
            specialty=agent_def["specialty"],
            tasks_completed=0,
            success_rate=1.0,
            avg_response_time_ms=50.0,
            memory_usage_mb=128.0,
            last_active=now.isoformat(),
        )
        
        if tier and agent_info.tier != tier:
            continue
        if status_filter and agent_info.status != status_filter:
            continue
        
        agents.append(agent_info)
    
    return agents


@router.get("/status", response_model=SwarmStatus)
async def get_swarm_status(request: Request) -> SwarmStatus:
    """Get overall swarm status and statistics."""
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    if swarm and swarm.is_initialized:
        return SwarmStatus(
            total_agents=40,
            active_agents=swarm.available_agents + swarm.busy_agents,
            idle_agents=swarm.available_agents,
            busy_agents=swarm.busy_agents,
            error_agents=0,
            total_tasks_queued=swarm.queued_tasks,
            total_tasks_completed=swarm.completed_tasks,
            uptime_seconds=swarm.uptime_seconds,
        )
    
    return SwarmStatus(
        total_agents=40,
        active_agents=0,
        idle_agents=0,
        busy_agents=0,
        error_agents=0,
        total_tasks_queued=0,
        total_tasks_completed=0,
        uptime_seconds=0.0,
    )


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(request: Request, agent_id: str) -> AgentInfo:
    """Get details of a specific agent."""
    # Parse agent index from ID
    try:
        index = int(agent_id.split("-")[-1]) - 1
        if index < 0 or index >= len(AGENT_DEFINITIONS):
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    agent_def = AGENT_DEFINITIONS[index]
    now = datetime.now(timezone.utc)
    
    return AgentInfo(
        agent_id=agent_id,
        name=agent_def["name"],
        tier=agent_def["tier"],
        status=AgentStatus.IDLE if swarm and swarm.is_initialized else AgentStatus.OFFLINE,
        specialty=agent_def["specialty"],
        tasks_completed=0,
        success_rate=1.0,
        avg_response_time_ms=50.0,
        memory_usage_mb=128.0,
        last_active=now.isoformat(),
    )


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_task(
    request: Request,
    task_request: TaskRequest,
) -> TaskResponse:
    """
    Submit a task to the agent swarm.
    
    The swarm coordinator will assign the task to the most suitable agent
    based on task type, agent availability, and specialization.
    """
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    if not swarm or not swarm.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent swarm not ready",
        )
    
    import uuid
    
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Submit to swarm (actual implementation would queue the task)
    assigned_agent = await swarm.assign_task(
        task_id=task_id,
        task_type=task_request.task_type,
        payload=task_request.payload,
        priority=task_request.priority,
    )
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        assigned_agent=assigned_agent,
        estimated_completion_seconds=task_request.timeout_seconds // 2,
        created_at=now.isoformat(),
    )


@router.get("/tiers/{tier}", response_model=list[AgentInfo])
async def get_agents_by_tier(request: Request, tier: AgentTier) -> list[AgentInfo]:
    """Get all agents of a specific tier."""
    return await list_agents(request, tier=tier)


@router.get("/specialties")
async def list_specialties() -> dict:
    """List all agent specialties grouped by tier."""
    specialties: dict[str, list[dict[str, str]]] = {
        "core": [],
        "specialist": [],
        "support": [],
    }
    
    for agent_def in AGENT_DEFINITIONS:
        tier_key = agent_def["tier"].value
        specialties[tier_key].append({
            "name": agent_def["name"],
            "specialty": agent_def["specialty"],
        })
    
    return specialties


class DispatchRequest(BaseModel):
    """Request to dispatch a task via the scheduler."""
    
    task_type: str = Field(description="Type of task (compression, encryption, analysis, storage, network)")
    payload: dict = Field(description="Task-specific payload")
    priority: str = Field(default="NORMAL", description="Task priority: CRITICAL, HIGH, NORMAL, LOW, BACKGROUND")
    callback_url: str | None = Field(default=None, description="URL to POST results to")


class DispatchResponse(BaseModel):
    """Response from task dispatch."""
    
    task_id: str
    status: str
    routed_agents: list[str]
    priority: str
    estimated_wait_ms: int
    queued_at: str


class SchedulerMetrics(BaseModel):
    """Scheduler performance metrics."""
    
    tasks_scheduled: int
    tasks_completed: int
    tasks_failed: int
    avg_wait_time_ms: float
    avg_execution_time_ms: float
    active_workers: int
    queue_depth: int
    rate_limit_per_second: float


class RecoveryStatus(BaseModel):
    """Agent recovery system status."""
    
    is_monitoring: bool
    agents_healthy: int
    agents_degraded: int
    agents_failed: int
    total_restarts: int
    circuit_breakers_open: int
    dead_letter_queue_size: int


@router.post("/dispatch", response_model=DispatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def dispatch_task(
    request: Request,
    dispatch_request: DispatchRequest,
) -> DispatchResponse:
    """
    Dispatch a task to the agent swarm via the intelligent scheduler.
    
    The scheduler routes tasks to the most suitable agents based on:
    - Task type and agent specialization
    - Current agent load and availability
    - Priority and queue depth
    - Agent health and circuit breaker state
    """
    from engined.agents.scheduler import TaskScheduler, TaskPriority
    import uuid
    
    scheduler: TaskScheduler | None = getattr(request.app.state, "scheduler", None)
    
    if not scheduler or not scheduler._running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task scheduler not ready",
        )
    
    # Parse priority
    try:
        priority = TaskPriority[dispatch_request.priority.upper()]
    except KeyError:
        priority = TaskPriority.NORMAL
    
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Schedule the task
    await scheduler.schedule(
        task_id=task_id,
        task_type=dispatch_request.task_type,
        payload=dispatch_request.payload,
        priority=priority,
        callback_url=dispatch_request.callback_url,
    )
    
    # Get routed agents for this task type
    routed_agents = scheduler.router.route(dispatch_request.task_type)
    
    return DispatchResponse(
        task_id=task_id,
        status="scheduled",
        routed_agents=routed_agents,
        priority=priority.name,
        estimated_wait_ms=int(scheduler._queue.qsize() * 50),  # rough estimate
        queued_at=now.isoformat(),
    )


@router.get("/scheduler/metrics", response_model=SchedulerMetrics)
async def get_scheduler_metrics(request: Request) -> SchedulerMetrics:
    """Get task scheduler performance metrics."""
    from engined.agents.scheduler import TaskScheduler
    
    scheduler: TaskScheduler | None = getattr(request.app.state, "scheduler", None)
    
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task scheduler not initialized",
        )
    
    metrics = scheduler.get_metrics()
    
    return SchedulerMetrics(
        tasks_scheduled=metrics.get("tasks_scheduled", 0),
        tasks_completed=metrics.get("tasks_completed", 0),
        tasks_failed=metrics.get("tasks_failed", 0),
        avg_wait_time_ms=metrics.get("avg_wait_time_ms", 0.0),
        avg_execution_time_ms=metrics.get("avg_execution_time_ms", 0.0),
        active_workers=metrics.get("active_workers", 0),
        queue_depth=metrics.get("queue_depth", 0),
        rate_limit_per_second=metrics.get("rate_limit", 100.0),
    )


@router.get("/recovery/status", response_model=RecoveryStatus)
async def get_recovery_status(request: Request) -> RecoveryStatus:
    """Get agent recovery system status."""
    from engined.agents.recovery import AgentRecovery
    
    recovery: AgentRecovery | None = getattr(request.app.state, "recovery", None)
    
    if not recovery:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recovery system not initialized",
        )
    
    status_data = recovery.get_status()
    
    return RecoveryStatus(
        is_monitoring=status_data.get("is_monitoring", False),
        agents_healthy=status_data.get("agents_healthy", 0),
        agents_degraded=status_data.get("agents_degraded", 0),
        agents_failed=status_data.get("agents_failed", 0),
        total_restarts=status_data.get("total_restarts", 0),
        circuit_breakers_open=status_data.get("circuit_breakers_open", 0),
        dead_letter_queue_size=status_data.get("dead_letter_queue_size", 0),
    )


@router.post("/recovery/restart/{agent_name}")
async def restart_agent(request: Request, agent_name: str) -> dict:
    """Manually trigger agent restart."""
    from engined.agents.recovery import AgentRecovery
    
    recovery: AgentRecovery | None = getattr(request.app.state, "recovery", None)
    
    if not recovery:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recovery system not initialized",
        )
    
    success = await recovery.restart_agent(agent_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart agent {agent_name}",
        )
    
    return {"status": "restarted", "agent": agent_name}
