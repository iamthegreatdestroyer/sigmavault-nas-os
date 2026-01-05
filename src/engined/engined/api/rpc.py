"""
JSON-RPC Endpoints

Provides JSON-RPC 2.0 endpoints for the Go API to communicate with the Python engine.
"""

import platform
import time
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


@router.post("/rpc")
async def handle_rpc(
    request: Request,
    rpc_request: JSONRPCRequest,
) -> JSONRPCResponse:
    """Handle JSON-RPC 2.0 requests."""
    try:
        if rpc_request.method == "system.status":
            result = handle_system_status()
        else:
            return JSONRPCResponse(
                error={"code": -32601, "message": f"Method not found: {rpc_request.method}"},
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
    cpu_percent = psutil.cpu_percent(interval=1)
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
        "timestamp": time.time(),
    }