"""Data models for SigmaVault compression jobs and system status."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class CompressionJob:
    """Represents a compression job from the RPC engine."""

    job_id: str
    status: str  # completed, failed, running, queued
    original_size: int
    compressed_size: int
    compression_ratio: float
    elapsed_seconds: float
    method: str
    data_type: str
    created_at: str  # ISO 8601
    error: str = ""

    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == "failed"

    @property
    def is_running(self) -> bool:
        """Check if job is running."""
        return self.status == "running"

    @property
    def savings_bytes(self) -> int:
        """Calculate bytes saved."""
        return self.original_size - self.compressed_size

    @property
    def savings_percent(self) -> float:
        """Calculate savings as percentage."""
        if self.original_size == 0:
            return 0.0
        return (self.savings_bytes / self.original_size) * 100

    @property
    def throughput_mbps(self) -> float:
        """Calculate throughput in MB/s."""
        if self.elapsed_seconds == 0:
            return 0.0
        bytes_per_second = self.original_size / self.elapsed_seconds
        return bytes_per_second / (1024 * 1024)


@dataclass
class SystemStatus:
    """Represents current system status."""

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_total_bytes: int = 0
    disk_used_bytes: int = 0
    disk_available_bytes: int = 0
    active_jobs: int = 0
    total_jobs: int = 0
    uptime_seconds: float = 0.0

    @property
    def disk_percent(self) -> float:
        """Calculate disk usage percentage."""
        if self.disk_total_bytes == 0:
            return 0.0
        return (self.disk_used_bytes / self.disk_total_bytes) * 100

    @property
    def disk_available_gb(self) -> float:
        """Get available disk space in GB."""
        return self.disk_available_bytes / (1024**3)

    @property
    def disk_used_gb(self) -> float:
        """Get used disk space in GB."""
        return self.disk_used_bytes / (1024**3)

    @property
    def disk_total_gb(self) -> float:
        """Get total disk space in GB."""
        return self.disk_total_bytes / (1024**3)


@dataclass
class APIResponse:
    """Wrapper for API responses with error handling."""

    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    status_code: int = 200


# ─── Storage Models ──────────────────────────────────────────────


@dataclass
class StorageDisk:
    """Represents a physical disk/device."""

    device: str
    model: str
    serial: str
    size_bytes: int
    mount_point: Optional[str] = None
    filesystem: Optional[str] = None
    status: str = "unknown"
    temperature_celsius: Optional[int] = None
    smart_status: Optional[str] = None

    @property
    def size_gb(self) -> float:
        """Size in GB."""
        return self.size_bytes / (1024**3)


@dataclass
class StoragePool:
    """Represents a ZFS/storage pool."""

    name: str
    size_bytes: int
    used_bytes: int
    available_bytes: int
    health: str  # ONLINE, DEGRADED, FAULTED
    compression_ratio: float = 1.0
    dedup_ratio: float = 1.0
    vdevs: list = field(default_factory=list)

    @property
    def usage_percent(self) -> float:
        """Usage percentage."""
        if self.size_bytes == 0:
            return 0.0
        return (self.used_bytes / self.size_bytes) * 100

    @property
    def available_gb(self) -> float:
        """Available space in GB."""
        return self.available_bytes / (1024**3)


@dataclass
class StorageDataset:
    """Represents a ZFS dataset/filesystem."""

    name: str
    pool: str
    size_bytes: int
    used_bytes: int
    available_bytes: int
    compression: str
    mounted: bool
    mount_point: Optional[str] = None
    quota_bytes: Optional[int] = None

    @property
    def usage_percent(self) -> float:
        """Usage percentage."""
        if self.quota_bytes and self.quota_bytes > 0:
            return (self.used_bytes / self.quota_bytes) * 100
        if self.size_bytes == 0:
            return 0.0
        return (self.used_bytes / self.size_bytes) * 100


@dataclass
class StorageShare:
    """Represents a network share (SMB/NFS)."""

    name: str
    protocol: str  # smb, nfs, iscsi
    path: str
    enabled: bool
    read_only: bool = False
    guest_access: bool = False
    connections: int = 0
    description: str = ""


# ─── Agent Models ────────────────────────────────────────────────


@dataclass
class AgentMetrics:
    """Metrics for an AI agent."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_response_time_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    last_active: Optional[str] = None  # ISO 8601

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return (self.tasks_completed / total) * 100


@dataclass
class Agent:
    """Represents an AI agent in the swarm."""

    agent_id: str
    name: str
    specialty: str
    status: str  # active, idle, error, offline
    tier: int
    description: str = ""
    capabilities: list = field(default_factory=list)
    metrics: Optional[AgentMetrics] = None

    @property
    def is_active(self) -> bool:
        """Check if agent is active."""
        return self.status == "active"


# ─── System Models ───────────────────────────────────────────────


@dataclass
class NetworkInterface:
    """Represents a network interface."""

    name: str
    address: str
    netmask: str
    status: str  # up, down
    mtu: int = 1500
    mac_address: Optional[str] = None
    rx_bytes: int = 0
    tx_bytes: int = 0

    @property
    def rx_gb(self) -> float:
        """Received data in GB."""
        return self.rx_bytes / (1024**3)

    @property
    def tx_gb(self) -> float:
        """Transmitted data in GB."""
        return self.tx_bytes / (1024**3)


@dataclass
class SystemService:
    """Represents a system service."""

    name: str
    status: str  # running, stopped, failed
    enabled: bool
    description: str = ""
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = None


@dataclass
class SystemNotification:
    """Represents a system notification/alert."""

    id: str
    level: str  # info, warning, error, critical
    message: str
    timestamp: str  # ISO 8601
    source: str = "system"
    read: bool = False
    action_url: Optional[str] = None
