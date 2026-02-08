"""API module for SigmaVault desktop UI."""

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.api.models import (
    CompressionJob,
    SystemStatus,
    APIResponse,
    StorageDisk,
    StoragePool,
    StorageDataset,
    StorageShare,
    Agent,
    AgentMetrics,
    NetworkInterface,
    SystemService,
    SystemNotification,
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
