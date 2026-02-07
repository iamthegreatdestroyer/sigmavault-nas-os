"""
SigmaVault Engine Configuration

Environment-based configuration with Pydantic Settings.
Supports loading from .env files and environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="SIGMAVAULT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # FastAPI Server
    host: str = Field(
        default="127.0.0.1",
        description="FastAPI server host",
    )
    port: int = Field(
        default=8001,
        ge=1024,
        le=65535,
        description="FastAPI server port",
    )
    workers: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of worker processes (production only)",
    )

    # gRPC Server
    grpc_host: str = Field(
        default="127.0.0.1",
        description="gRPC server host",
    )
    grpc_port: int = Field(
        default=9003,
        ge=1024,
        le=65535,
        description="gRPC server port",
    )
    grpc_max_workers: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum gRPC worker threads",
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://sigmavault:sigmavault@localhost:5432/sigmavault",
        description="PostgreSQL connection URL",
    )

    # Agent Swarm Configuration
    agent_pool_size: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Number of AI agents in the swarm",
    )
    agent_memory_limit_mb: int = Field(
        default=512,
        ge=128,
        le=8192,
        description="Memory limit per agent in MB",
    )
    agent_timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Agent task timeout in seconds",
    )

    # Compression Settings
    compression_default_algorithm: Literal["zstd", "lz4", "brotli"] = Field(
        default="zstd",
        description="Default compression algorithm",
    )
    compression_level: int = Field(
        default=3,
        ge=1,
        le=22,
        description="Default compression level",
    )
    compression_threads: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of compression threads",
    )

    # Encryption Settings
    encryption_algorithm: Literal["aes-256-gcm", "chacha20-poly1305", "kyber"] = Field(
        default="aes-256-gcm",
        description="Default encryption algorithm",
    )
    encryption_key_rotation_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Key rotation period in days",
    )
    quantum_safe_encryption: bool = Field(
        default=True,
        description="Enable quantum-safe encryption (Kyber/Dilithium)",
    )

    # Storage Paths
    data_dir: Path = Field(
        default=Path("/var/lib/sigmavault"),
        description="Base data directory",
    )
    cache_dir: Path = Field(
        default=Path("/var/cache/sigmavault"),
        description="Cache directory",
    )
    log_dir: Path = Field(
        default=Path("/var/log/sigmavault"),
        description="Log directory",
    )

    # Observability
    enable_telemetry: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OpenTelemetry collector endpoint",
    )
    metrics_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Prometheus metrics port",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("data_dir", "cache_dir", "log_dir", mode="before")
    @classmethod
    def parse_path(cls, v: str | Path) -> Path:
        """Convert string paths to Path objects."""
        return Path(v) if isinstance(v, str) else v


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def get_development_settings() -> Settings:
    """Get development settings for testing."""
    return Settings(
        environment="development",
        debug=True,
        log_level="DEBUG",
        data_dir=Path("./data"),
        cache_dir=Path("./cache"),
        log_dir=Path("./logs"),
    )
