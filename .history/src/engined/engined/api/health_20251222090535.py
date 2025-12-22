"""
Health Check Endpoints

Provides liveness and readiness probes for Kubernetes/container orchestration,
plus detailed status information for monitoring.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from engined.agents.swarm import AgentSwarm

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(description="Overall health status")
    timestamp: str = Field(description="ISO 8601 timestamp")
    version: str = Field(description="Engine version")
    uptime_seconds: float = Field(description="Uptime in seconds")


class ReadinessStatus(BaseModel):
    """Readiness check response model."""

    ready: bool = Field(description="Whether the engine is ready to serve requests")
    checks: dict[str, bool] = Field(description="Individual component check results")


class DetailedStatus(BaseModel):
    """Detailed engine status model."""

    status: str
    version: str
    environment: str
    timestamp: str
    uptime_seconds: float
    agents: dict[str, int | str]
    compression: dict[str, str | int]
    encryption: dict[str, str | bool]
    resources: dict[str, float]


# Track startup time for uptime calculation
_startup_time: datetime | None = None


def get_startup_time() -> datetime:
    """Get or set startup time."""
    global _startup_time
    if _startup_time is None:
        _startup_time = datetime.now(timezone.utc)
    return _startup_time


@router.get("/live", response_model=HealthStatus)
async def liveness_probe() -> HealthStatus:
    """
    Liveness probe endpoint.
    
    Returns 200 if the application is running. Used by Kubernetes
    to determine if the container should be restarted.
    """
    startup = get_startup_time()
    now = datetime.now(timezone.utc)
    
    return HealthStatus(
        status="alive",
        timestamp=now.isoformat(),
        version="0.1.0",
        uptime_seconds=(now - startup).total_seconds(),
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_probe(request: Request) -> ReadinessStatus:
    """
    Readiness probe endpoint.
    
    Returns 200 if the application is ready to serve traffic.
    Checks all critical dependencies before returning ready.
    """
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    checks = {
        "swarm_initialized": swarm is not None and swarm.is_initialized,
        "agents_available": swarm is not None and swarm.available_agents > 0,
    }
    
    all_ready = all(checks.values())
    
    return ReadinessStatus(
        ready=all_ready,
        checks=checks,
    )


@router.get("/status", response_model=DetailedStatus)
async def detailed_status(request: Request) -> DetailedStatus:
    """
    Detailed engine status endpoint.
    
    Returns comprehensive status information about all engine components
    including agent swarm, compression, encryption, and resource usage.
    """
    startup = get_startup_time()
    now = datetime.now(timezone.utc)
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    settings = getattr(request.app.state, "settings", None)
    
    # Agent status
    agent_info = {
        "total": 40,
        "available": swarm.available_agents if swarm else 0,
        "busy": swarm.busy_agents if swarm else 0,
        "status": "operational" if swarm and swarm.is_initialized else "initializing",
    }
    
    # Compression status
    compression_info = {
        "default_algorithm": settings.compression_default_algorithm if settings else "zstd",
        "level": settings.compression_level if settings else 3,
        "threads": settings.compression_threads if settings else 4,
    }
    
    # Encryption status
    encryption_info = {
        "algorithm": settings.encryption_algorithm if settings else "aes-256-gcm",
        "quantum_safe": settings.quantum_safe_encryption if settings else True,
    }
    
    # Resource usage (placeholder - would be actual metrics in production)
    import psutil
    process = psutil.Process()
    
    resource_info = {
        "cpu_percent": process.cpu_percent(),
        "memory_mb": process.memory_info().rss / (1024 * 1024),
        "open_files": len(process.open_files()),
    }
    
    return DetailedStatus(
        status="operational" if swarm and swarm.is_initialized else "initializing",
        version="0.1.0",
        environment=settings.environment if settings else "unknown",
        timestamp=now.isoformat(),
        uptime_seconds=(now - startup).total_seconds(),
        agents=agent_info,
        compression=compression_info,
        encryption=encryption_info,
        resources=resource_info,
    )
