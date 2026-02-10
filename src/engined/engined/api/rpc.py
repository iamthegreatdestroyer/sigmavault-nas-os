"""
JSON-RPC Endpoints

Provides JSON-RPC 2.0 endpoints for the Go API to communicate with the Python engine.
"""

import base64
import platform
import time
from datetime import UTC, datetime
from typing import Any

import psutil
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] | None = None
    id: str | int | None = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Any = None
    error: dict[str, Any] | None = None
    id: str | int | None = None


# In-memory storage for compression jobs (would be database in production)
_compression_jobs: dict[str, dict[str, Any]] = {}

# Global compression bridge and job queue
_compression_bridge = None
_compression_queue = None


async def get_compression_bridge():
    """Get or create the compression bridge singleton."""
    global _compression_bridge
    if _compression_bridge is None:
        from engined.compression import CompressionBridge, CompressionConfig
        _compression_bridge = CompressionBridge(CompressionConfig())
        await _compression_bridge.initialize()
    return _compression_bridge


async def get_compression_queue():
    """Get or create the compression job queue singleton."""
    global _compression_queue
    if _compression_queue is None:
        from engined.compression import CompressionJobQueue
        bridge = await get_compression_bridge()
        _compression_queue = CompressionJobQueue(bridge, max_concurrent=4)
    return _compression_queue


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
        elif method == "health.check":
            result = {"status": "healthy"}
        elif method == "agents.list":
            result = await handle_agents_list(request, params)
        elif method == "agents.status":
            result = await handle_agents_status(request)
        elif method == "compression.jobs.list":
            result = handle_compression_jobs_list(params)
        elif method == "compression.jobs.get":
            result = handle_compression_job_get(params)
        # New compression methods
        elif method == "compression.compress.data":
            result = await handle_compress_data(params)
        elif method == "compression.compress.file":
            result = await handle_compress_file(params)
        elif method == "compression.decompress.data":
            result = await handle_decompress_data(params)
        elif method == "compression.decompress.file":
            result = await handle_decompress_file(params)
        elif method == "compression.queue.submit":
            result = await handle_queue_submit(params)
        elif method == "compression.queue.status":
            result = await handle_queue_status(params)
        elif method == "compression.queue.running":
            result = await handle_queue_running(params)
        elif method == "compression.queue.cancel":
            result = await handle_queue_cancel(params)
        elif method == "compression.config.get":
            result = await handle_get_compression_config()
        elif method == "compression.config.set":
            result = await handle_set_compression_config(params)
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


def handle_system_status() -> dict[str, Any]:
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
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def handle_agents_list(request: Request, params: dict[str, Any]) -> dict[str, Any]:
    """Handle agents.list RPC call - returns list of all agents."""
    from engined.agents.swarm import AgentSwarm

    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)

    if not swarm or not swarm.is_initialized:
        # Return agent definitions even if swarm not initialized
        from engined.agents.swarm import AGENT_DEFINITIONS, AgentStatus
        now = datetime.now(UTC)
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


async def handle_agents_status(request: Request) -> dict[str, Any]:
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


def handle_compression_jobs_list(params: dict[str, Any]) -> dict[str, Any]:
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


def handle_compression_job_get(params: dict[str, Any]) -> dict[str, Any]:
    """Handle compression.jobs.get RPC call."""
    job_id = params.get("job_id")

    if not job_id:
        raise ValueError("job_id parameter required")

    job = _compression_jobs.get(job_id)
    if not job:
        raise ValueError(f"Compression job {job_id} not found")

    return job


# =============================================================================
# New Compression RPC Handlers
# =============================================================================


async def handle_compress_data(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.compress.data RPC call.
    
    Compress raw data (base64 encoded) synchronously.
    
    Params:
        data: base64 encoded data to compress
        level: compression level (fast, balanced, maximum, adaptive)
        job_id: optional job ID for tracking
    
    Returns:
        job_id, original_size, compressed_size, ratio, data (base64)
    """
    from engined.compression import CompressionLevel

    data_b64 = params.get("data")
    if data_b64 is None:
        raise ValueError("data parameter required (base64 encoded)")

    try:
        data = base64.b64decode(data_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {e}")

    level_str = params.get("level", "balanced")
    level_map = {
        "fast": CompressionLevel.FAST,
        "balanced": CompressionLevel.BALANCED,
        "maximum": CompressionLevel.MAXIMUM,
        "adaptive": CompressionLevel.ADAPTIVE,
    }
    level = level_map.get(level_str, CompressionLevel.BALANCED)

    job_id = params.get("job_id")

    bridge = await get_compression_bridge()

    # Update config if level changed
    if bridge.config.level != level:
        from engined.compression import CompressionConfig
        bridge.config = CompressionConfig(level=level)

    result = await bridge.compress_data(data, job_id=job_id)

    # Store in jobs registry
    _compression_jobs[result.job_id] = {
        "job_id": result.job_id,
        "status": "completed" if result.success else "failed",
        "original_size": result.original_size,
        "compressed_size": result.compressed_size,
        "compression_ratio": result.compression_ratio,
        "elapsed_seconds": result.elapsed_seconds,
        "method": result.method,
        "data_type": result.data_type,
        "created_at": datetime.now(UTC).isoformat(),
        "error": result.error,
    }

    return {
        "job_id": result.job_id,
        "success": result.success,
        "original_size": result.original_size,
        "compressed_size": result.compressed_size,
        "compression_ratio": result.compression_ratio,
        "elapsed_seconds": result.elapsed_seconds,
        "method": result.method,
        "data_type": result.data_type,
        "checksum": result.checksum,
        "data": base64.b64encode(result.compressed_data).decode() if result.compressed_data else None,
        "error": result.error,
    }


async def handle_compress_file(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.compress.file RPC call.
    
    Compress a file on the filesystem.
    
    Params:
        source_path: path to file to compress
        dest_path: optional destination path
        level: compression level
        job_id: optional job ID
    
    Returns:
        job_id, paths, sizes, ratio
    """
    from pathlib import Path

    from engined.compression import CompressionLevel

    source_path = params.get("source_path")
    if not source_path:
        raise ValueError("source_path parameter required")

    source = Path(source_path)
    if not source.exists():
        raise ValueError(f"Source file does not exist: {source_path}")

    dest_path = params.get("dest_path")
    level_str = params.get("level", "balanced")
    job_id = params.get("job_id")

    level_map = {
        "fast": CompressionLevel.FAST,
        "balanced": CompressionLevel.BALANCED,
        "maximum": CompressionLevel.MAXIMUM,
        "adaptive": CompressionLevel.ADAPTIVE,
    }
    level = level_map.get(level_str, CompressionLevel.BALANCED)

    bridge = await get_compression_bridge()

    # Update config if level changed
    if bridge.config.level != level:
        from engined.compression import CompressionConfig
        bridge.config = CompressionConfig(level=level)

    result = await bridge.compress_file(source, dest_path, job_id=job_id)

    # Store in jobs registry
    _compression_jobs[result.job_id] = {
        "job_id": result.job_id,
        "status": "completed" if result.success else "failed",
        "source_path": source_path,
        "dest_path": dest_path,
        "original_size": result.original_size,
        "compressed_size": result.compressed_size,
        "compression_ratio": result.compression_ratio,
        "elapsed_seconds": result.elapsed_seconds,
        "method": result.method,
        "created_at": datetime.now(UTC).isoformat(),
        "error": result.error,
    }

    return {
        "job_id": result.job_id,
        "success": result.success,
        "source_path": source_path,
        "dest_path": dest_path,
        "original_size": result.original_size,
        "compressed_size": result.compressed_size,
        "compression_ratio": result.compression_ratio,
        "elapsed_seconds": result.elapsed_seconds,
        "method": result.method,
        "checksum": result.checksum,
        "error": result.error,
    }


async def handle_decompress_data(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.decompress.data RPC call.
    
    Decompress raw data (base64 encoded).
    
    Params:
        data: base64 encoded compressed data
        job_id: optional job ID
    
    Returns:
        job_id, sizes, decompressed data (base64)
    """
    data_b64 = params.get("data")
    if data_b64 is None:
        raise ValueError("data parameter required (base64 encoded)")

    try:
        data = base64.b64decode(data_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {e}")

    job_id = params.get("job_id")

    bridge = await get_compression_bridge()
    result = await bridge.decompress_data(data, job_id=job_id)

    return {
        "job_id": result.job_id,
        "success": result.success,
        "compressed_size": result.original_size,
        "decompressed_size": result.compressed_size,  # In decompress, this is output size
        "elapsed_seconds": result.elapsed_seconds,
        "checksum": result.checksum,
        "data": base64.b64encode(result.compressed_data).decode() if result.compressed_data else None,
        "error": result.error,
    }


async def handle_decompress_file(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.decompress.file RPC call.
    
    Decompress a file on the filesystem.
    
    Params:
        source_path: path to compressed file
        dest_path: optional destination path
        job_id: optional job ID
    
    Returns:
        job_id, paths, sizes
    """
    from pathlib import Path

    source_path = params.get("source_path")
    if not source_path:
        raise ValueError("source_path parameter required")

    source = Path(source_path)
    if not source.exists():
        raise ValueError(f"Source file does not exist: {source_path}")

    dest_path = params.get("dest_path")
    job_id = params.get("job_id")

    bridge = await get_compression_bridge()
    result = await bridge.decompress_file(source, dest_path, job_id=job_id)

    return {
        "job_id": result.job_id,
        "success": result.success,
        "source_path": source_path,
        "dest_path": dest_path,
        "compressed_size": result.original_size,
        "decompressed_size": result.compressed_size,
        "elapsed_seconds": result.elapsed_seconds,
        "checksum": result.checksum,
        "error": result.error,
    }


async def handle_queue_submit(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.queue.submit RPC call.
    
    Submit a compression job to the async queue.
    
    Params:
        type: "compress_file", "compress_data", "decompress_file", "decompress_data"
        source_path or data: input
        dest_path: optional output path
        priority: low, normal, high, critical
        level: compression level
    
    Returns:
        job_id, status
    """
    from engined.compression import JobPriority, JobType

    job_type_str = params.get("type", "compress_data")
    type_map = {
        "compress_file": JobType.COMPRESS_FILE,
        "compress_data": JobType.COMPRESS_DATA,
        "decompress_file": JobType.DECOMPRESS_FILE,
        "decompress_data": JobType.DECOMPRESS_DATA,
    }
    job_type = type_map.get(job_type_str)
    if not job_type:
        raise ValueError(f"Invalid job type: {job_type_str}")

    priority_str = params.get("priority", "normal")
    priority_map = {
        "low": JobPriority.LOW,
        "normal": JobPriority.NORMAL,
        "high": JobPriority.HIGH,
        "critical": JobPriority.CRITICAL,
    }
    priority = priority_map.get(priority_str, JobPriority.NORMAL)

    queue = await get_compression_queue()

    # Determine if this is a compress or decompress operation
    is_compress = job_type in (JobType.COMPRESS_FILE, JobType.COMPRESS_DATA)

    if job_type in (JobType.COMPRESS_FILE, JobType.DECOMPRESS_FILE):
        source_path = params.get("source_path")
        if not source_path:
            raise ValueError("source_path required for file operations")

        dest_path = params.get("dest_path")

        job = await queue.submit_file(
            input_path=source_path,
            output_path=dest_path,
            compress=is_compress,
            priority=priority,
        )
    else:
        data_b64 = params.get("data")
        if not data_b64:
            raise ValueError("data required for data operations (base64)")

        data = base64.b64decode(data_b64)

        job = await queue.submit_data(
            data=data,
            compress=is_compress,
            priority=priority,
        )

    return {
        "job_id": job.id,
        "status": job.status.value,
        "priority": job.priority.name.lower(),
        "job_type": job.job_type.value,
        "created_at": job.created_at.isoformat(),
    }


async def handle_queue_status(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.queue.status RPC call.
    
    Get status of a queued job or all jobs.
    
    Params:
        job_id: optional specific job ID
    
    Returns:
        Job status or queue summary
    """
    job_id = params.get("job_id")
    queue = await get_compression_queue()

    if job_id:
        job = queue.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        return {
            "job_id": job.id,
            "status": job.status.value,
            "priority": job.priority.name.lower(),
            "job_type": job.job_type.value,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }
    else:
        stats = queue.get_stats()
        return stats


async def handle_queue_running(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.queue.running RPC call.
    
    Get all running and pending jobs with detailed progress information.
    Optimized for WebSocket progress streaming.
    
    Params:
        include_pending: include pending jobs (default: True)
        limit: max jobs to return (default: 50)
    
    Returns:
        List of jobs with detailed progress data
    """
    from engined.compression import JobStatus

    queue = await get_compression_queue()
    include_pending = params.get("include_pending", True)
    limit = params.get("limit", 50)

    # Get running jobs
    running_jobs = queue.get_jobs(status=JobStatus.RUNNING, limit=limit)

    # Optionally include pending
    pending_jobs = []
    if include_pending:
        pending_jobs = queue.get_jobs(status=JobStatus.PENDING, limit=limit)

    # Combine and limit
    all_jobs = running_jobs + pending_jobs
    all_jobs = all_jobs[:limit]

    # Convert to progress-optimized format
    jobs_data = []
    for job in all_jobs:
        job_data = {
            "job_id": job.id,
            "status": job.status.value,
            "job_type": job.job_type.value,
            "priority": job.priority.name.lower(),
            "progress": job.progress,
            "phase": job.phase,
            "bytes_processed": job.bytes_processed,
            "bytes_total": job.bytes_total,
            "current_ratio": job.current_ratio,
            "elapsed_seconds": job.elapsed_seconds,
            "eta_seconds": job.eta_seconds,
            "input_path": job.input_path,
            "output_path": job.output_path,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "user_id": job.user_id,
            "tags": job.tags,
        }
        jobs_data.append(job_data)

    stats = queue.get_stats()

    return {
        "jobs": jobs_data,
        "total_running": stats["running"],
        "total_pending": stats["pending"],
        "total_jobs": stats["total_jobs"],
    }


async def handle_queue_cancel(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.queue.cancel RPC call.
    
    Cancel a queued job.
    
    Params:
        job_id: job to cancel
    
    Returns:
        success status
    """
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id required")

    queue = await get_compression_queue()
    success = queue.cancel_job(job_id)

    return {
        "job_id": job_id,
        "cancelled": success,
    }


async def handle_get_compression_config() -> dict[str, Any]:
    """
    Handle compression.config.get RPC call.
    
    Get current compression configuration.
    """
    bridge = await get_compression_bridge()

    engine_type = "semantic" if bridge._engine is not None else "stub"

    return {
        "level": bridge.config.level.value,
        "chunk_size": bridge.config.chunk_size,
        "use_semantic": bridge.config.use_semantic,
        "lossless": bridge.config.lossless,
        "engine": engine_type,
    }


async def handle_set_compression_config(params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle compression.config.set RPC call.
    
    Update compression configuration.
    
    Params:
        level: compression level
        chunk_size: bytes per chunk
        use_semantic: enable semantic compression
        lossless: require lossless compression
    """
    from engined.compression import CompressionConfig, CompressionLevel

    bridge = await get_compression_bridge()

    level_str = params.get("level", bridge.config.level.value)
    level_map = {
        "fast": CompressionLevel.FAST,
        "balanced": CompressionLevel.BALANCED,
        "maximum": CompressionLevel.MAXIMUM,
        "adaptive": CompressionLevel.ADAPTIVE,
    }
    level = level_map.get(level_str, bridge.config.level)

    new_config = CompressionConfig(
        level=level,
        chunk_size=params.get("chunk_size", bridge.config.chunk_size),
        use_semantic=params.get("use_semantic", bridge.config.use_semantic),
        lossless=params.get("lossless", bridge.config.lossless),
    )

    bridge.config = new_config

    return {
        "success": True,
        "level": new_config.level.value,
        "chunk_size": new_config.chunk_size,
        "use_semantic": new_config.use_semantic,
        "lossless": new_config.lossless,
    }
