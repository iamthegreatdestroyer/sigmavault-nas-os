"""API module for SigmaVault desktop UI."""

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.api.models import (
    Agent,
    AgentMetrics,
    APIResponse,
    CompressionJob,
    NetworkInterface,
    StorageDataset,
    StorageDisk,
    StoragePool,
    StorageShare,
    SystemNotification,
    SystemService,
    SystemStatus,
)

__all__ = [
    "SigmaVaultAPIClient",
    "CompressionJob",
    "SystemStatus",
    "APIResponse",
    "StorageDisk",
    "StoragePool",
    "StorageDataset",
    "StorageShare",
    "Agent",
    "AgentMetrics",
    "NetworkInterface",
    "SystemService",
    "SystemNotification",
]
