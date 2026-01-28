"""
SigmaVault Engine Daemon - Main Entry Point

This module initializes and runs the SigmaVault RPC engine, which provides:
- FastAPI REST endpoints for the Go API to call
- gRPC services for high-performance agent communication
- 40-agent AI swarm orchestration
- Quantum-resistant encryption services
- Adaptive compression engine
"""

from __future__ import annotations

import asyncio
import signal
import sys
from concurrent import futures
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator

import grpc
import structlog
from aiohttp import web
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from engined.config import Settings, get_settings
from engined.api.health import router as health_router
from engined.api.compression import router as compression_router
from engined.api.encryption import router as encryption_router
from engined.api.agents import router as agents_router
from engined.api.rpc import router as rpc_router
from engined.rpc.server import create_grpc_server
from engined.agents.swarm import AgentSwarm
from engined.agents.scheduler import TaskScheduler
from engined.agents.recovery import AgentRecovery
from engined.agents.events import configure_event_system, shutdown_event_system
from engined.agents.memory import init_memory_system, shutdown_memory_system
from engined.agents.tuning import init_tuning_system, shutdown_tuning_system, TuningStrategy

if TYPE_CHECKING:
    from engined.agents.swarm import AgentSwarm

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class EngineState:
    """Global state container for the engine."""

    def __init__(self) -> None:
        self.settings: Settings | None = None
        self.swarm: AgentSwarm | None = None
        self.scheduler: TaskScheduler | None = None
        self.recovery: AgentRecovery | None = None
        self.grpc_server: grpc.aio.Server | None = None
        self._shutdown_event: asyncio.Event = asyncio.Event()

    async def initialize(self, settings: Settings) -> None:
        """Initialize engine components."""
        self.settings = settings
        
        logger.info("Initializing agent swarm", num_agents=40)
        self.swarm = AgentSwarm(settings)
        await self.swarm.initialize()
        
        logger.info("Initializing task scheduler")
        self.scheduler = TaskScheduler(
            swarm=self.swarm,
            max_workers=10,
            rate_limit=100.0
        )
        await self.scheduler.start()
        
        logger.info("Initializing agent recovery system")
        self.recovery = AgentRecovery(
            swarm=self.swarm,
            max_restart_attempts=3,
            restart_cooldown=60.0
        )
        await self.recovery.start_monitoring(check_interval=30.0)
        
        logger.info("Initializing event system for real-time WebSocket events")
        await configure_event_system(
            swarm=self.swarm,
            scheduler=self.scheduler,
            recovery=self.recovery,
        )
        
        logger.info("Initializing MNEMONIC memory system")
        await init_memory_system(
            max_entries=10000,
            consolidation_interval=300.0,  # 5 minutes
            decay_interval=3600.0,  # 1 hour
        )
        
        logger.info("Initializing self-tuning system")
        await init_tuning_system(
            strategy=TuningStrategy.GRADIENT_FREE,
            exploration_rate=0.1,
            tuning_interval=300.0,  # 5 minutes
        )
        
        logger.info("Initializing gRPC server", port=settings.grpc_port)
        self.grpc_server = await create_grpc_server(settings, self.swarm)
        await self.grpc_server.start()
        
        logger.info("Engine initialization complete")

    async def shutdown(self) -> None:
        """Gracefully shutdown engine components."""
        logger.info("Shutting down engine...")
        
        # Shutdown event system first to stop emitting events
        await shutdown_event_system()
        logger.info("Event system stopped")
        
        # Shutdown memory system
        await shutdown_memory_system()
        logger.info("MNEMONIC memory system stopped")
        
        # Shutdown tuning system
        await shutdown_tuning_system()
        logger.info("Self-tuning system stopped")
        
        if self.recovery:
            await self.recovery.stop_monitoring()
            logger.info("Agent recovery stopped")
        
        if self.scheduler:
            await self.scheduler.stop()
            logger.info("Task scheduler stopped")
        
        if self.grpc_server:
            await self.grpc_server.stop(grace=5)
            logger.info("gRPC server stopped")
        
        if self.swarm:
            await self.swarm.shutdown()
            logger.info("Agent swarm shutdown complete")
        
        self._shutdown_event.set()
        logger.info("Engine shutdown complete")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        asyncio.create_task(self.shutdown())


# Global engine state
engine_state = EngineState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for startup/shutdown."""
    settings = get_settings()
    
    print("DEBUG: Starting lifespan")
    logger.info(
        "Starting SigmaVault Engine",
        version="0.1.0",
        environment=settings.environment,
        grpc_port=settings.grpc_port,
    )
    
    try:
        print("DEBUG: About to initialize engine state")
        await engine_state.initialize(settings)
        print("DEBUG: Engine state initialized successfully")
        logger.info("Engine state initialized successfully")
    except Exception as e:
        print(f"DEBUG: Failed to initialize engine state: {e}")
        logger.error("Failed to initialize engine state", error=str(e))
        raise
    
    # Store swarm in app state for route access
    app.state.swarm = engine_state.swarm
    app.state.scheduler = engine_state.scheduler
    app.state.recovery = engine_state.recovery
    app.state.settings = settings
    
    print("DEBUG: About to yield")
    yield
    
    print("DEBUG: Lifespan yielding, starting shutdown")
    logger.info("Lifespan yielding, starting shutdown")
    try:
        await engine_state.shutdown()
        print("DEBUG: Engine shutdown completed")
        logger.info("Engine shutdown completed")
    except Exception as e:
        print(f"DEBUG: Failed to shutdown engine: {e}")
        logger.error("Failed to shutdown engine", error=str(e))
        raise


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    print("DEBUG: create_app called")
    settings = get_settings()
    print(f"DEBUG: settings loaded: host={settings.host}, port={settings.port}")
    
    app = FastAPI(
        title="SigmaVault Engine API",
        description=(
            "AI-powered RPC engine for SigmaVault NAS OS. "
            "Provides compression, encryption, and agent orchestration services."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url="/redoc" if settings.environment == "development" else None,
        openapi_url="/openapi.json" if settings.environment == "development" else None,
        lifespan=lifespan,  # Enable lifespan for proper engine initialization
    )
    print("DEBUG: FastAPI app created")
    
    # CORS middleware - configured for Go API communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Mount Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    # Include routers
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(compression_router, prefix="/api/v1/compression", tags=["Compression"])
    app.include_router(encryption_router, prefix="/api/v1/encryption", tags=["Encryption"])
    app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(rpc_router, prefix="/api/v1", tags=["RPC"])
    
    # Debug: print all routes
    logger.info("Registered routes:")
    for route in app.routes:
        if hasattr(route, 'path'):
            methods = getattr(route, 'methods', 'MOUNT')
            logger.info(f"  {route.path} - {methods}")
        else:
            logger.info(f"  {route} - UNKNOWN")
    
    return app


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    def handle_signal(signum: int, frame: object) -> None:
        logger.info("Received shutdown signal", signal=signal.Signals(signum).name)
        engine_state.request_shutdown()
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)


async def run_server() -> None:
    """Run the aiohttp server with FastAPI app."""
    settings = get_settings()
    
    logger.info(
        "Starting SigmaVault Engine (aiohttp)",
        host=settings.host,
        port=settings.port,
        grpc_port=settings.grpc_port,
        environment=settings.environment,
    )
    
    # Create FastAPI app with lifespan
    fastapi_app = create_app()
    
    # Create wrapper for serving FastAPI via aiohttp
    async def handle_fastapi(request: web.Request) -> web.Response:
        """Proxy FastAPI requests through aiohttp."""
        # Build ASGI scope from aiohttp request
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "scheme": request.scheme,
            "path": request.path,
            "query_string": request.query_string.encode() if request.query_string else b"",
            "root_path": "",
            "headers": [(k.lower().encode(), v.encode()) for k, v in request.headers.items()],
            "server": (request.host.split(":")[0], int(request.host.split(":")[1]) if ":" in request.host else 80),
            "client": (request.remote, 0) if request.remote else ("unknown", 0),
            "state": {},
        }
        
        # Read request body
        body = await request.read()
        
        # Collect response
        response_started = False
        status = 200
        headers = []
        response_body = []
        
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}
        
        async def send(message):
            nonlocal response_started, status, headers
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response_body.append(message.get("body", b""))
        
        # Call FastAPI ASGI app
        await fastapi_app(scope, receive, send)
        
        # Build response
        return web.Response(
            status=status,
            headers={k.decode(): v.decode() for k, v in headers},
            body=b"".join(response_body)
        )
    
    # Create aiohttp application
    aiohttp_app = web.Application()
    
    # Mount FastAPI at all paths
    aiohttp_app.router.add_route('*', '/{path_info:.*}', handle_fastapi)
    
    # Create runner and start server
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, settings.host, settings.port)
    await site.start()
    
    logger.info(
        "Server started on aiohttp",
        host=settings.host,
        port=settings.port,
        url=f"http://{settings.host}:{settings.port}"
    )
    print(f"Server started on http://{settings.host}:{settings.port}")
    
    # Keep server running until shutdown requested
    try:
        await engine_state._shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error("Server error", error=str(e))
    finally:
        await runner.cleanup()
        logger.info("Server cleanup complete")


def main() -> None:
    """Main entry point for the SigmaVault engine daemon."""
    settings = get_settings()
    
    setup_signal_handlers()
    
    logger.info(
        "Starting SigmaVault Engine Daemon",
        host=settings.host,
        port=settings.port,
        grpc_port=settings.grpc_port,
        environment=settings.environment,
    )
    
    # Run the async server using aiohttp
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
