"""
Minimal RPC Server for Integration Tests

This is a lightweight server that only includes the compression RPC endpoints
needed for integration testing. It doesn't require all the heavy ML dependencies.
"""

import asyncio
import base64
import json
import platform
import time
import zlib
from datetime import UTC, datetime
from typing import Any

from aiohttp import web

# In-memory storage for compression jobs
_compression_jobs: dict[str, dict[str, Any]] = {}
_job_counter = 0


def generate_job_id() -> str:
    """Generate a unique job ID."""
    global _job_counter
    _job_counter += 1
    return f"job-{_job_counter:06d}"


def compress_data(data: bytes, level: str = "balanced") -> tuple[bytes, dict]:
    """Compress data using zlib with configurable level."""
    level_map = {
        "fast": 1,
        "balanced": 6,
        "maximum": 9,
    }
    zlib_level = level_map.get(level, 6)

    start_time = time.time()
    compressed = zlib.compress(data, level=zlib_level)
    elapsed = (time.time() - start_time) * 1000  # ms

    original_size = len(data)
    compressed_size = len(compressed)
    ratio = compressed_size / original_size if original_size > 0 else 1.0

    return compressed, {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "ratio": ratio,
        "algorithm": "zlib",
        "level": level,
        "duration_ms": elapsed,
    }


def decompress_data(data: bytes) -> tuple[bytes, dict]:
    """Decompress zlib data."""
    start_time = time.time()
    decompressed = zlib.decompress(data)
    elapsed = (time.time() - start_time) * 1000  # ms

    return decompressed, {
        "compressed_size": len(data),
        "decompressed_size": len(decompressed),
        "duration_ms": elapsed,
    }


async def handle_rpc(request: web.Request) -> web.Response:
    """Handle JSON-RPC 2.0 requests."""
    try:
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {}) or {}
        request_id = body.get("id")

        result = None
        error = None

        if method == "system.status":
            result = {
                "hostname": platform.node(),
                "platform": platform.system(),
                "uptime": 0,
                "cpu_usage": 0.0,
                "memory_usage": {"total": 0, "used": 0, "free": 0, "available": 0, "used_percent": 0.0},
                "disk_usage": [],
                "load_average": {"load1": 0.0, "load5": 0.0, "load15": 0.0},
                "timestamp": datetime.now(UTC).isoformat(),
            }

        elif method == "compression.compress.data":
            # Validate input
            data_b64 = params.get("data")
            if not data_b64:
                error = {"code": -32602, "message": "Invalid params: 'data' is required"}
            else:
                try:
                    data = base64.b64decode(data_b64)
                    level = params.get("level", "balanced")
                    compressed, stats = compress_data(data, level)

                    # Calculate compression ratio (ratio of space saved)
                    # 0.7 = 70% compression = only 30% of original size remains
                    compression_ratio = 1.0 - (stats["compressed_size"] / stats["original_size"]) if stats["original_size"] > 0 else 0.0

                    result = {
                        "job_id": generate_job_id(),
                        "success": True,
                        "data": base64.b64encode(compressed).decode('utf-8'),
                        "original_size": stats["original_size"],
                        "compressed_size": stats["compressed_size"],
                        "compression_ratio": compression_ratio,
                        "algorithm": stats["algorithm"],
                        "elapsed_seconds": stats["duration_ms"] / 1000.0,
                    }
                except Exception as e:
                    error = {"code": -32603, "message": f"Compression error: {e!s}"}

        elif method == "compression.decompress.data":
            data_b64 = params.get("data")
            if not data_b64:
                error = {"code": -32602, "message": "Invalid params: 'data' is required"}
            else:
                try:
                    data = base64.b64decode(data_b64)
                    decompressed, stats = decompress_data(data)
                    result = {
                        "job_id": generate_job_id(),
                        "success": True,
                        "data": base64.b64encode(decompressed).decode('utf-8'),
                        "compressed_size": stats["compressed_size"],
                        "decompressed_size": stats["decompressed_size"],
                        "elapsed_seconds": stats["duration_ms"] / 1000.0,
                    }
                except Exception as e:
                    error = {"code": -32603, "message": f"Decompression error: {e!s}"}

        elif method == "compression.queue.submit":
            job_id = generate_job_id()
            source_path = params.get("source_path", "")
            dest_path = params.get("dest_path", "")
            level = params.get("level", "balanced")
            priority = params.get("priority", "normal")
            job_type = params.get("job_type", "compress_data")

            # Create job record
            now = datetime.now(UTC)
            _compression_jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "priority": priority,
                "job_type": job_type,
                "progress": 0.0,
                "source_path": source_path,
                "dest_path": dest_path,
                "level": level,
                "created_at": now.isoformat(),
                "started_at": None,
                "completed_at": None,
                "error": None,
                "stats": None,
            }

            # Simulate async job processing (start immediately for testing)
            _compression_jobs[job_id]["status"] = "running"
            _compression_jobs[job_id]["started_at"] = now.isoformat()
            _compression_jobs[job_id]["progress"] = 50.0

            result = {
                "job_id": job_id,
                "status": "queued",
                "priority": priority,
                "job_type": job_type,
                "created_at": now.isoformat(),
            }

        elif method == "compression.queue.status":
            job_id = params.get("job_id", "")
            job = _compression_jobs.get(job_id)
            if not job:
                error = {"code": -32602, "message": f"Job not found: {job_id}"}
            else:
                # Simulate progress for running jobs
                if job["status"] == "running":
                    job["progress"] = min(job["progress"] + 10.0, 100.0)
                    if job["progress"] >= 100.0:
                        job["status"] = "completed"
                        job["completed_at"] = datetime.now(UTC).isoformat()
                        job["stats"] = {
                            "original_size": 1024,
                            "compressed_size": 300,
                            "ratio": 0.29,
                            "duration_ms": 50.0,
                        }
                result = {
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "priority": job.get("priority", "normal"),
                    "job_type": job.get("job_type", "compress_data"),
                    "progress": job["progress"],
                    "created_at": job["created_at"],
                    "started_at": job.get("started_at"),
                    "completed_at": job.get("completed_at"),
                    "error": job.get("error"),
                }

        elif method == "compression.queue.running":
            running = []
            pending = []
            for j in _compression_jobs.values():
                if j["status"] == "running":
                    running.append({
                        "job_id": j["job_id"],
                        "status": j["status"],
                        "job_type": j.get("job_type", "compress_data"),
                        "priority": j.get("priority", "normal"),
                        "progress": j["progress"] / 100.0,  # Normalize to 0-1
                        "phase": "compressing",
                        "bytes_processed": 512,
                        "bytes_total": 1024,
                        "current_ratio": 0.7,
                        "eta_seconds": 0.5,
                    })
                elif j["status"] == "queued":
                    pending.append(j)

            result = {
                "jobs": running,
                "total_running": len(running),
                "total_pending": len(pending),
                "total_jobs": len(_compression_jobs),
            }

        elif method == "compression.queue.cancel":
            job_id = params.get("job_id", "")
            job = _compression_jobs.get(job_id)
            if not job:
                error = {"code": -32602, "message": f"Job not found: {job_id}"}
            elif job["status"] in ("completed", "failed", "cancelled"):
                error = {"code": -32602, "message": f"Job cannot be cancelled: {job['status']}"}
            else:
                job["status"] = "cancelled"
                job["completed_at"] = datetime.now(UTC).isoformat()
                result = {"job_id": job_id, "status": "cancelled"}

        elif method == "compression.jobs.list":
            # Return list of all jobs with filtering
            status_filter = params.get("status")
            limit = params.get("limit", 100)
            offset = params.get("offset", 0)

            jobs_list = list(_compression_jobs.values())

            if status_filter:
                jobs_list = [j for j in jobs_list if j["status"] == status_filter]

            # Apply pagination
            jobs_list = jobs_list[offset:offset + limit]

            result = {
                "jobs": [{
                    "job_id": j["job_id"],
                    "status": j["status"],
                    "priority": j.get("priority", "normal"),
                    "job_type": j.get("job_type", "compress_data"),
                    "progress": j.get("progress", 0.0),
                    "created_at": j["created_at"],
                    "started_at": j.get("started_at"),
                    "completed_at": j.get("completed_at"),
                } for j in jobs_list],
                "total": len(_compression_jobs),
                "limit": limit,
                "offset": offset,
            }

        elif method == "compression.config.get":
            result = {
                "default_algorithm": "zlib",
                "default_level": "balanced",
                "max_concurrent_jobs": 4,
                "chunk_size": 65536,
            }

        elif method == "compression.config.set":
            result = {
                "success": True,
                "message": "Configuration updated",
            }

        # ==============================
        # Agent Methods
        # ==============================
        elif method == "agents.list":
            tier_filter = params.get("tier") if params else None

            # Generate 40 agents (matching test expectations)
            agent_names = [
                "APEX", "CIPHER", "ARCHITECT", "AXIOM", "VELOCITY",
                "QUANTUM", "TENSOR", "FORTRESS", "NEURAL", "CRYPTO",
                "FLUX", "PRISM", "SYNAPSE", "CORE", "HELIX",
                "VANGUARD", "ECLIPSE", "NEXUS", "GENESIS", "OMNISCIENT",
                "ATLAS", "FORGE", "SENTRY", "VERTEX", "STREAM",
                "PHOTON", "LATTICE", "MORPH", "PHANTOM", "ORBIT",
                "CANVAS", "LINGUA", "SCRIBE", "MENTOR", "BRIDGE",
                "AEGIS", "LEDGER", "PULSE", "ARBITER", "ORACLE",
            ]

            tier_map = {
                "APEX": "core", "CIPHER": "core", "ARCHITECT": "core", "AXIOM": "core", "VELOCITY": "core",
                "QUANTUM": "specialist", "TENSOR": "specialist", "FORTRESS": "specialist", "NEURAL": "specialist",
                "CRYPTO": "specialist", "FLUX": "specialist", "PRISM": "specialist", "SYNAPSE": "specialist",
                "CORE": "specialist", "HELIX": "specialist", "VANGUARD": "specialist", "ECLIPSE": "specialist",
                "NEXUS": "specialist", "GENESIS": "specialist", "OMNISCIENT": "specialist",
                "ATLAS": "support", "FORGE": "support", "SENTRY": "support", "VERTEX": "support", "STREAM": "support",
                "PHOTON": "support", "LATTICE": "support", "MORPH": "support", "PHANTOM": "support", "ORBIT": "support",
                "CANVAS": "support", "LINGUA": "support", "SCRIBE": "support", "MENTOR": "support", "BRIDGE": "support",
                "AEGIS": "support", "LEDGER": "support", "PULSE": "support", "ARBITER": "support", "ORACLE": "support",
            }

            agents = []
            for i, name in enumerate(agent_names):
                tier = tier_map.get(name, "support")
                if tier_filter and tier != tier_filter:
                    continue
                agents.append({
                    "agent_id": f"agent-{i+1:04d}",
                    "name": name,
                    "tier": tier,
                    "specialty": f"{name.lower()} operations",
                    "status": "idle",
                    "load": 0.0,
                })

            result = {
                "agents": agents,
                "total": len(agents) if tier_filter else 40,
                "swarm_initialized": True,
            }

        elif method == "agents.status":
            result = {
                "total_agents": 40,
                "active_agents": 40,
                "idle_agents": 40,
                "busy_agents": 0,
                "is_initialized": True,
                "uptime_seconds": 3600.0,
            }

        else:
            error = {"code": -32601, "message": f"Method not found: {method}"}

        response = {
            "jsonrpc": "2.0",
            "id": request_id,
        }
        if error:
            response["error"] = error
        else:
            response["result"] = result

        return web.json_response(response)

    except json.JSONDecodeError:
        return web.json_response({
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Parse error"},
            "id": None,
        })
    except Exception as e:
        return web.json_response({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"Internal error: {e!s}"},
            "id": body.get("id") if 'body' in dir() else None,
        })


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    })


async def main():
    """Start the test RPC server."""
    app = web.Application()
    app.router.add_post('/api/v1/rpc', handle_rpc)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8102)
    await site.start()

    print("=" * 60)
    print("Test RPC Server started")
    print("=" * 60)
    print("RPC Endpoint: http://localhost:8102/api/v1/rpc")
    print("Health Check: http://localhost:8102/health")
    print("=" * 60)
    print("Supported methods:")
    print("  - system.status")
    print("  - compression.compress.data")
    print("  - compression.decompress.data")
    print("  - compression.queue.submit")
    print("  - compression.queue.status")
    print("  - compression.queue.running")
    print("  - compression.queue.cancel")
    print("  - compression.config.get")
    print("  - compression.config.set")
    print("=" * 60)

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
