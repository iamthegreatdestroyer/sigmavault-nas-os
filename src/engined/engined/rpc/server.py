"""
SigmaVault RPC Server - gRPC Service Implementation

Provides gRPC services for the Go API to communicate with the Python engine.
"""

import asyncio
import logging
import platform
import time

logger = logging.getLogger(__name__)

try:
    from grpc import aio as grpc_aio

    from .system_pb2 import GetSystemStatusResponse, MemoryUsage
    from .system_pb2_grpc import (
        SystemServiceServicer,
        add_SystemServiceServicer_to_server,
    )
    _GRPC_AVAILABLE = True
except ImportError:
    _GRPC_AVAILABLE = False
    logger.warning("grpcio not available, falling back to mock gRPC server")


class _SigmaVaultServicer:
    """Real gRPC servicer implementing SystemService."""

    def __init__(self, swarm=None):
        self._swarm = swarm
        self._start_time = time.monotonic()

    async def GetSystemStatus(self, _request, _context):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            vm = psutil.virtual_memory()
            load = list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [0.0, 0.0, 0.0]
            mem = MemoryUsage(
                used=vm.used,
                total=vm.total,
                used_percent=vm.percent,
            )
        except Exception:
            cpu = 0.0
            mem = MemoryUsage(used=0, total=0, used_percent=0.0)
            load = [0.0, 0.0, 0.0]

        uptime = int(time.monotonic() - self._start_time)
        hostname = platform.node()

        return GetSystemStatusResponse(
            hostname=hostname,
            uptime=uptime,
            cpu_usage=cpu,
            memory_usage=mem,
            load_average=load,
        )


# Mix-in the generated servicer base when grpcio is available
if _GRPC_AVAILABLE:
    class SigmaVaultServicer(SystemServiceServicer, _SigmaVaultServicer):
        pass
else:
    SigmaVaultServicer = _SigmaVaultServicer


async def create_grpc_server(_settings=None, _swarm=None):
    """Create and configure the gRPC server."""
    if not _GRPC_AVAILABLE:
        return _MockServer()

    server = grpc_aio.server()
    add_SystemServiceServicer_to_server(SigmaVaultServicer(_swarm), server)
    port = getattr(_settings, "rpc_port", 50051) if _settings else 50051
    server.add_insecure_port(f"[::]:{port}")
    logger.info("gRPC server configured on port %d", port)
    return server


class _MockServer:
    """Fallback mock when grpcio is not installed."""

    def __init__(self):
        self._running = False

    async def start(self):
        self._running = True
        logger.info("Mock gRPC server started (grpcio not available)")

    async def stop(self, grace: int = 0):
        if self._running:
            logger.info("Mock gRPC server stopping (grace=%d)", grace)
            self._running = False
            await asyncio.sleep(0)

    async def wait_for_termination(self):
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return
