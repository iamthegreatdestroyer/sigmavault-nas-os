"""
JSON-RPC Endpoints

Provides JSON-RPC 2.0 endpoints for the Go API to communicate with the Python engine.
"""

import platform
import time
from datetime import datetime, timezone
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] | None = None
    id: str | int | None = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Any = None
    error: Dict[str, Any] | None = None
    id: str | int | None = None


# In-memory storage for compression jobs (would be database in production)
_compression_jobs: Dict[str, Dict[str, Any]] = {}


@router.post("/rpc")
async def handle_rpc(
    request: Request,
    rpc_request: JSONRPCRequest,
) -> JSONRPCResponse:
    """Handle JSON-RPC 2.0 requests."""
    try:
        method = rpc_request.method
        params = rpc_request.params or {}
        
        if method == "system.status":
            result = handle_system_status()
        elif method == "agents.list":
            result = await handle_agents_list(request, params)
        elif method == "agents.status":
            result = await handle_agents_status(request)
        elif method == "compression.jobs.list":
            result = handle_compression_jobs_list(params)
        elif method == "compression.jobs.get":
            result = handle_compression_job_get(params)
        else:
            return JSONRPCResponse(
                error={"code": -32601, "message": f"Method not found: {method}"},
                id=rpc_request.id
            )

        return JSONRPCResponse(
            result=result,
            id=rpc_request.id
        )

    except Exception as e:
        return JSONRPCResponse(
            error={"code": -32603, "message": "Internal error", "data": str(e)},
            id=rpc_request.id
        )


def handle_system_status() -> Dict[str, Any]:
    """Handle system.status RPC call."""
    # Use non-blocking CPU check (returns 0.0 on first call, cached value after)
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0.0, 0.0, 0.0)

    return {
        "hostname": platform.node(),
        "platform": platform.system(),
        "uptime": int(time.time() - psutil.boot_time()),
        "cpu_usage": cpu_percent,
        "memory_usage": {
            "total": memory.total,
            "used": memory.used,
            "free": memory.free,
            "available": memory.available,
            "used_percent": memory.percent,
        },
        "disk_usage": [],
        "load_average": {
            "load1": load_avg[0],
            "load5": load_avg[1],
            "load15": load_avg[2],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def handle_agents_list(request: Request, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle agents.list RPC call - returns list of all agents."""
    from engined.agents.swarm import AgentSwarm
    
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    if not swarm or not swarm.is_initialized:
        # Return agent definitions even if swarm not initialized
        from engined.agents.swarm import AGENT_DEFINITIONS, AgentStatus
        now = datetime.now(timezone.utc)
        agents = []
        for i, agent_def in enumerate(AGENT_DEFINITIONS):
            agents.append({
                "agent_id": f"agent-{i+1:03d}",
                "name": agent_def["name"],
                "tier": agent_def["tier"].value,
                "specialty": agent_def["specialty"],
                "status": AgentStatus.OFFLINE.value,
                "tasks_completed": 0,
                "success_rate": 1.0,
                "avg_response_time_ms": 0.0,
                "memory_usage_mb": 0.0,
                "last_active": now.isoformat(),
            })
        return {
            "agents": agents,
            "total": len(agents),
            "swarm_initialized": False,
        }
    
    # Get agents from initialized swarm
    tier_filter = params.get("tier")
    status_filter = params.get("status")
    
    agents = swarm.list_agents()
    
    # Apply filters
    if tier_filter:
        agents = [a for a in agents if a.tier.value == tier_filter]
    if status_filter:
        agents = [a for a in agents if a.status.value == status_filter]
    
    return {
        "agents": [a.to_dict() for a in agents],
        "total": len(agents),
        "swarm_initialized": True,
    }


async def handle_agents_status(request: Request) -> Dict[str, Any]:
    """Handle agents.status RPC call - returns swarm status summary."""
    from engined.agents.swarm import AgentSwarm
    
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    if not swarm or not swarm.is_initialized:
        return {
            "total_agents": 40,
            "active_agents": 0,
            "idle_agents": 0,
            "busy_agents": 0,
            "error_agents": 0,
            "offline_agents": 40,
            "total_tasks_queued": 0,
            "total_tasks_completed": 0,
            "uptime_seconds": 0.0,
            "is_initialized": False,
        }
    
    return swarm.get_swarm_status()


def handle_compression_jobs_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle compression.jobs.list RPC call."""
    status_filter = params.get("status")
    limit = params.get("limit", 100)
    
    jobs = list(_compression_jobs.values())
    
    if status_filter:
        jobs = [j for j in jobs if j.get("status") == status_filter]
    
    # Sort by created_at descending
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    
    return {
        "jobs": jobs[:limit],
        "total": len(jobs),
    }


def handle_compression_job_get(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle compression.jobs.get RPC call."""
    job_id = params.get("job_id")
    
    if not job_id:
        raise ValueError("job_id parameter required")
    
    job = _compression_jobs.get(job_id)
    if not job:
        raise ValueError(f"Compression job {job_id} not found")
    
    return job