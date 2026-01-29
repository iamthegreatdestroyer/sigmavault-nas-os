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
from .job_queue import (
    CompressionJob,
    CompressionJobQueue,
    JobStatus,
    JobPriority,
    JobType,
)
from .events import (
    CompressionEventEmitter,
    CompressionEvent,
    CompressionEventType,
    WebSocketEventBridge,
    get_compression_emitter,
    set_compression_emitter,
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
