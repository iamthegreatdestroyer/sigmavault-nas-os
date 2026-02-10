"""
Elite Agent Collective API Endpoints

FastAPI router for managing the 40-agent Elite Agent Collective.
Provides endpoints for agent discovery, status monitoring, and task submission.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel, Field

from engined.agents.base import AgentTask, TaskPriority
from engined.agents.registry import AgentRegistry
from engined.agents.tier1 import TIER_1_AGENTS
from engined.agents.tier2 import TIER_2_AGENTS

router = APIRouter(prefix="/elite-agents", tags=["elite-agents"])

# Global registry (initialized during app startup)
_registry: AgentRegistry | None = None


async def get_registry() -> AgentRegistry:
    """Get the global agent registry."""
    if _registry is None:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent registry not initialized"
        )
    return _registry


async def initialize_registry() -> AgentRegistry:
    """
    Initialize the Elite Agent Collective registry.
    Called during FastAPI app startup.
    """
    global _registry
    _registry = AgentRegistry()

    # Register Tier 1 agents
    for agent_class in TIER_1_AGENTS:
        agent = agent_class()
        await _registry.register_agent(agent)

    # Register Tier 2 agents
    for agent_class in TIER_2_AGENTS:
        agent = agent_class()
        await _registry.register_agent(agent)

    # Initialize all agents
    await _registry.initialize_all()

    return _registry


async def shutdown_registry() -> None:
    """
    Shutdown the Elite Agent Collective registry.
    Called during FastAPI app shutdown.
    """
    global _registry
    if _registry:
        await _registry.shutdown_all()
        _registry = None


# ===== Pydantic Models =====

class AgentStatusResponse(BaseModel):
    """Agent status information."""

    agent_id: str
    state: str
    tier: int
    domains: list[str]
    skills: list[str]
    task_count: int
    success_count: int
    error_count: int
    success_rate: float
    avg_execution_time: float
    current_task_id: str | None = None


class AgentListResponse(BaseModel):
    """Response for listing agents."""

    total: int
    agents: list[dict[str, Any]]


class RegistryStatusResponse(BaseModel):
    """Overall registry status."""

    total_agents: int
    initialized: bool
    agents_by_state: dict[str, int]
    agents_by_tier: dict[int, int]  # tier as int key
    aggregate_metrics: dict[str, Any]  # nested metrics


class TaskSubmitRequest(BaseModel):
    """Request to submit a task to an agent."""

    task_type: str = Field(..., description="Type of task to execute")
    payload: dict[str, Any] = Field(..., description="Task payload data")
    priority: str = Field(default="MEDIUM", description="Task priority (CRITICAL, HIGH, MEDIUM, LOW)")
    timeout: int = Field(default=300, description="Task timeout in seconds")


class TaskSubmitResponse(BaseModel):
    """Response from task submission."""

    task_id: str
    agent_id: str
    status: str


# ===== Endpoints =====

@router.get("/", response_model=AgentListResponse)
async def list_agents(
    tier: int | None = None,
    state: str | None = None,
    domain: str | None = None
) -> AgentListResponse:
    """
    List all agents in the Elite Agent Collective.
    
    Query parameters:
    - tier: Filter by tier (1, 2, 3, 4)
    - state: Filter by state (stub, idle, busy, error, shutdown)
    - domain: Filter by domain expertise
    """
    registry = await get_registry()

    agents = registry.list_agents(tier=tier, state=state, domain=domain)

    return AgentListResponse(
        total=len(agents),
        agents=agents
    )


@router.get("/registry/status", response_model=RegistryStatusResponse)
async def get_registry_status() -> RegistryStatusResponse:
    """Get overall registry status and aggregate metrics."""
    registry = await get_registry()

    status_data = registry.get_registry_status()

    return RegistryStatusResponse(**status_data)


@router.get("/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(agent_id: str) -> AgentStatusResponse:
    """
    Get detailed status for a specific agent.
    
    Parameters:
    - agent_id: Agent identifier (e.g., "APEX-01", "CIPHER-02")
    """
    registry = await get_registry()

    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    status_data = agent.get_status()
    capability = agent.capability

    return AgentStatusResponse(
        agent_id=status_data["agent_id"],
        state=status_data["state"],
        tier=capability.tier,
        domains=capability.domains,
        skills=capability.skills,
        task_count=status_data["metrics"]["task_count"],
        success_count=status_data["metrics"]["success_count"],
        error_count=status_data["metrics"]["error_count"],
        success_rate=status_data["metrics"]["success_rate"],
        avg_execution_time=status_data["metrics"]["avg_execution_time"],
        current_task_id=status_data["current_task"]  # Fixed: "current_task" not "current_task_id"
    )


@router.post("/{agent_id}/task", response_model=TaskSubmitResponse)
async def submit_task(agent_id: str, request: TaskSubmitRequest) -> TaskSubmitResponse:
    """
    Submit a task to a specific agent.
    
    Parameters:
    - agent_id: Target agent identifier
    
    Request body:
    - task_type: Type of task (e.g., "code_review", "system_design")
    - payload: Task-specific data
    - priority: Task priority (CRITICAL, HIGH, MEDIUM, LOW)
    - timeout: Timeout in seconds
    """
    registry = await get_registry()

    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Check agent state
    status_data = agent.get_status()
    if status_data["state"] not in ["idle", "busy"]:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent {agent_id} is not available (state: {status_data['state']})"
        )

    # Convert priority string to enum
    try:
        priority_enum = TaskPriority[request.priority.upper()]
    except KeyError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority: {request.priority}. Must be CRITICAL, HIGH, MEDIUM, or LOW"
        )

    # Create task
    task_id = str(uuid.uuid4())
    task = AgentTask(
        task_id=task_id,
        task_type=request.task_type,
        payload=request.payload,
        priority=priority_enum,
        timeout=request.timeout
    )

    # Submit task
    success = await registry.dispatch_task(agent_id, task)

    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task to agent {agent_id}"
        )

    return TaskSubmitResponse(
        task_id=task_id,
        agent_id=agent_id,
        status="submitted"
    )


@router.get("/tier/{tier_number}", response_model=AgentListResponse)
async def list_agents_by_tier(tier_number: int) -> AgentListResponse:
    """
    List all agents in a specific tier.
    
    Parameters:
    - tier_number: Tier number (1=Foundational, 2=Specialist, 3=Innovator, 4=Meta)
    """
    if tier_number not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Tier must be 1, 2, 3, or 4"
        )

    registry = await get_registry()
    agents = registry.get_agents_by_tier(tier_number)

    agents_data = []
    for agent in agents:
        status = agent.get_status()
        agents_data.append({
            "agent_id": status["agent_id"],
            "state": status["state"],
            "tier": agent.capability.tier,
            "domains": agent.capability.domains,
            "success_rate": status["metrics"]["success_rate"]
        })

    return AgentListResponse(
        total=len(agents_data),
        agents=agents_data
    )


@router.get("/domain/{domain_name}", response_model=AgentListResponse)
async def list_agents_by_domain(domain_name: str) -> AgentListResponse:
    """
    List all agents with expertise in a specific domain.
    
    Parameters:
    - domain_name: Domain expertise (e.g., "software_engineering", "cryptography")
    """
    registry = await get_registry()
    agents = registry.get_agents_by_domain(domain_name)

    agents_data = []
    for agent in agents:
        status = agent.get_status()
        agents_data.append({
            "agent_id": status["agent_id"],
            "state": status["state"],
            "tier": agent.capability.tier,
            "domains": agent.capability.domains,
            "success_rate": status["metrics"]["success_rate"]
        })

    return AgentListResponse(
        total=len(agents_data),
        agents=agents_data
    )


@router.get("/skill/{skill_name}", response_model=AgentListResponse)
async def list_agents_by_skill(skill_name: str) -> AgentListResponse:
    """
    List all agents with a specific skill.
    
    Parameters:
    - skill_name: Skill name (e.g., "production_code", "encryption", "kubernetes")
    """
    registry = await get_registry()
    agents = registry.find_agents_by_skill(skill_name)

    agents_data = []
    for agent in agents:
        status = agent.get_status()
        agents_data.append({
            "agent_id": status["agent_id"],
            "state": status["state"],
            "tier": agent.capability.tier,
            "skills": agent.capability.skills,
            "success_rate": status["metrics"]["success_rate"]
        })

    return AgentListResponse(
        total=len(agents_data),
        agents=agents_data
    )
