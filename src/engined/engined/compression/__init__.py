"""
Copyright 2025 Stephen Bilodeau. All Rights Reserved.
SigmaVault NAS OS - Compression Module

Provides AI-powered compression through integration with EliteSigma-NAS.

Components:
- CompressionBridge: Interface to EliteSigma-NAS compression engine
- CompressionJobQueue: Async job queue with priority scheduling
- CompressionEventEmitter: Real-time event streaming for WebSocket
"""

from .bridge import (
    CompressionBridge,
    CompressionConfig,
    CompressionLevel,
    CompressionProgress,
    CompressionResult,
    StubCompressionEngine,
)
from .events import (
    CompressionEvent,
    CompressionEventEmitter,
    CompressionEventType,
    WebSocketEventBridge,
    get_compression_emitter,
    set_compression_emitter,
)
from .job_queue import (
    CompressionJob,
    CompressionJobQueue,
    JobPriority,
    JobStatus,
    JobType,
)

__all__ = [
    # Bridge
    "CompressionBridge",
    "CompressionConfig",
    "CompressionLevel",
    "CompressionProgress",
    "CompressionResult",
    "StubCompressionEngine",
    # Job Queue
    "CompressionJob",
    "CompressionJobQueue",
    "JobStatus",
    "JobPriority",
    "JobType",
    # Events
    "CompressionEventEmitter",
    "CompressionEvent",
    "CompressionEventType",
    "WebSocketEventBridge",
    "get_compression_emitter",
    "set_compression_emitter",
]
