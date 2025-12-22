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
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from engined.config import Settings, get_settings
from engined.api.health import router as health_router
from engined.api.compression import router as compression_router
from engined.api.encryption import router as encryption_router
from engined.api.agents import router as agents_router
from engined.rpc.server import create_grpc_server
from engined.agents.swarm import AgentSwarm

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
        self.grpc_server: grpc.aio.Server | None = None
        self._shutdown_event: asyncio.Event = asyncio.Event()

    async def initialize(self, settings: Settings) -> None:
        """Initialize engine components."""
        self.settings = settings
        
        logger.info("Initializing agent swarm", num_agents=40)
        self.swarm = AgentSwarm(settings)
        await self.swarm.initialize()
        
        logger.info("Initializing gRPC server", port=settings.grpc_port)
        self.grpc_server = await create_grpc_server(settings, self.swarm)
        await self.grpc_server.start()
        
        logger.info("Engine initialization complete")

    async def shutdown(self) -> None:
        """Gracefully shutdown engine components."""
        logger.info("Shutting down engine...")
        
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
    
    logger.info(
        "Starting SigmaVault Engine",
        version="0.1.0",
        environment=settings.environment,
        grpc_port=settings.grpc_port,
    )
    
    await engine_state.initialize(settings)
    
    # Store swarm in app state for route access
    app.state.swarm = engine_state.swarm
    app.state.settings = settings
    
    yield
    
    await engine_state.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
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
        lifespan=lifespan,
    )
    
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
    
    return app


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    def handle_signal(signum: int, frame: object) -> None:
        logger.info("Received shutdown signal", signal=signal.Signals(signum).name)
        engine_state.request_shutdown()
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)


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
    
    uvicorn.run(
        "engined.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        workers=settings.workers if settings.environment == "production" else 1,
        log_level=settings.log_level.lower(),
        access_log=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
