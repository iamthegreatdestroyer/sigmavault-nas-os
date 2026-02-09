"""API client for communicating with SigmaVault Go API."""

import logging
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, ValidationError

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

logger = logging.getLogger(__name__)


class SigmaVaultAPIClient:
    """Client for interacting with the SigmaVault API."""

    def __init__(self, base_url: str = "http://localhost:12080", timeout: int = 10):
        """Initialize API client.

        Args:
            base_url: Base URL for the API (default: localhost:12080)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        """Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments to pass to aiohttp

        Returns:
            APIResponse with result or error
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.request(method, url, **kwargs) as response:
                data = await response.json()

                if response.status == 200:
                    return APIResponse(success=True, data=data, status_code=response.status)
                else:
                    error = data.get("error", f"HTTP {response.status}")
                    return APIResponse(success=False, error=error, status_code=response.status)

        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            return APIResponse(success=False, error=str(e), status_code=0)
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            return APIResponse(success=False, error="Invalid response format", status_code=0)

    async def get_compression_jobs(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[CompressionJob]:
        """Get list of compression jobs.

        Args:
            status: Filter by status (completed, failed, running, queued)
            limit: Maximum number of jobs to return

        Returns:
            List of CompressionJob objects
        """
        params = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status

        response = await self._request("GET", "/api/v1/compression/jobs", params=params)

        if not response.success:
            logger.warning(f"Failed to get compression jobs: {response.error}")
            return []

        try:
            jobs_data = response.data.get("jobs", [])
            jobs = [CompressionJob(**job) for job in jobs_data]
            return sorted(jobs, key=lambda j: j.created_at, reverse=True)
        except (KeyError, ValidationError) as e:
            logger.error(f"Error parsing compression jobs: {e}")
            return []

    async def get_compression_job(self, job_id: str) -> Optional[CompressionJob]:
        """Get details of a specific compression job.

        Args:
            job_id: ID of the job

        Returns:
            CompressionJob object or None if not found
        """
        response = await self._request("GET", f"/api/v1/compression/jobs/{job_id}")

        if not response.success:
            logger.warning(f"Failed to get job {job_id}: {response.error}")
            return None

        try:
            job_data = response.data.get("job")
            return CompressionJob(**job_data)
        except (KeyError, ValidationError, TypeError) as e:
            logger.error(f"Error parsing job {job_id}: {e}")
            return None

    async def get_system_status(self) -> Optional[SystemStatus]:
        """Get current system status.

        Returns:
            SystemStatus object or None if request fails
        """
        response = await self._request("GET", "/api/v1/system/status")

        if not response.success:
            logger.warning(f"Failed to get system status: {response.error}")
            return None

        try:
            status_data = response.data.get("status", {})
            return SystemStatus(
                cpu_percent=status_data.get("cpu_percent", 0.0),
                memory_percent=status_data.get("memory_percent", 0.0),
                disk_total_bytes=status_data.get("disk_total_bytes", 0),
                disk_used_bytes=status_data.get("disk_used_bytes", 0),
                disk_available_bytes=status_data.get("disk_available_bytes", 0),
                active_jobs=status_data.get("active_jobs", 0),
                total_jobs=status_data.get("total_jobs", 0),
            )
        except (KeyError, ValidationError, TypeError) as e:
            logger.error(f"Error parsing system status: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if API is healthy.

        Returns:
            True if API is responding, False otherwise
        """
        response = await self._request("GET", "/api/v1/health")
        return response.success

    # ─── Storage Endpoints ───────────────────────────────────────────

    async def get_storage_disks(self) -> List[StorageDisk]:
        """Get list of storage disks.

        Returns:
            List of StorageDisk objects
        """
        response = await self._request("GET", "/api/v1/storage/disks")

        if not response.success:
            logger.warning(f"Failed to get disks: {response.error}")
            return []

        try:
            disks_data = response.data.get("disks", [])
            return [StorageDisk(**disk) for disk in disks_data]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing disks: {e}")
            return []

    async def get_storage_pools(self) -> List[StoragePool]:
        """Get list of storage pools.

        Returns:
            List of StoragePool objects
        """
        response = await self._request("GET", "/api/v1/storage/pools")

        if not response.success:
            logger.warning(f"Failed to get pools: {response.error}")
            return []

        try:
            pools_data = response.data.get("pools", [])
            return [StoragePool(**pool) for pool in pools_data]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing pools: {e}")
            return []

    async def get_storage_datasets(self, pool: Optional[str] = None) -> List[StorageDataset]:
        """Get list of storage datasets.

        Args:
            pool: Optional pool name filter

        Returns:
            List of StorageDataset objects
        """
        params = {}
        if pool:
            params["pool"] = pool

        response = await self._request("GET", "/api/v1/storage/datasets", params=params)

        if not response.success:
            logger.warning(f"Failed to get datasets: {response.error}")
            return []

        try:
            datasets_data = response.data.get("datasets", [])
            return [StorageDataset(**ds) for ds in datasets_data]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing datasets: {e}")
            return []

    async def get_storage_shares(self) -> List[StorageShare]:
        """Get list of network shares.

        Returns:
            List of StorageShare objects
        """
        response = await self._request("GET", "/api/v1/storage/shares")

        if not response.success:
            logger.warning(f"Failed to get shares: {response.error}")
            return []

        try:
            shares_data = response.data.get("shares", [])
            return [StorageShare(**share) for share in shares_data]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing shares: {e}")
            return []

    # ─── Agent Endpoints ─────────────────────────────────────────────

    async def get_agents(self) -> List[Agent]:
        """Get list of AI agents.

        Returns:
            List of Agent objects
        """
        response = await self._request("GET", "/api/v1/agents")

        if not response.success:
            logger.warning(f"Failed to get agents: {response.error}")
            return []

        try:
            agents_data = response.data.get("agents", [])
            agents = []
            for agent_data in agents_data:
                # Parse metrics if present
                metrics_data = agent_data.get("metrics")
                if metrics_data:
                    agent_data["metrics"] = AgentMetrics(**metrics_data)
                agents.append(Agent(**agent_data))
            return agents
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing agents: {e}")
            return []

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get details of a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent object or None
        """
        response = await self._request("GET", f"/api/v1/agents/{agent_id}")

        if not response.success:
            logger.warning(f"Failed to get agent {agent_id}: {response.error}")
            return None

        try:
            agent_data = response.data.get("agent", {})
            metrics_data = agent_data.get("metrics")
            if metrics_data:
                agent_data["metrics"] = AgentMetrics(**metrics_data)
            return Agent(**agent_data)
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing agent {agent_id}: {e}")
            return None

    async def get_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentMetrics object or None
        """
        response = await self._request("GET", f"/api/v1/agents/{agent_id}/metrics")

        if not response.success:
            logger.warning(f"Failed to get agent metrics {agent_id}: {response.error}")
            return None

        try:
            metrics_data = response.data.get("metrics", {})
            return AgentMetrics(**metrics_data)
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing agent metrics {agent_id}: {e}")
            return None

    # ─── System Endpoints ────────────────────────────────────────────

    async def get_network_interfaces(self) -> List[NetworkInterface]:
        """Get list of network interfaces.

        Returns:
            List of NetworkInterface objects
        """
        response = await self._request("GET", "/api/v1/system/network")

        if not response.success:
            logger.warning(f"Failed to get network interfaces: {response.error}")
            return []

        try:
            interfaces_data = response.data.get("interfaces", [])
            return [NetworkInterface(**iface) for iface in interfaces_data]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing network interfaces: {e}")
            return []

    async def get_services(self) -> List[SystemService]:
        """Get list of system services.

        Returns:
            List of SystemService objects
        """
        response = await self._request("GET", "/api/v1/system/services")

        if not response.success:
            logger.warning(f"Failed to get services: {response.error}")
            return []

        try:
            services_data = response.data.get("services", [])
            return [SystemService(**svc) for svc in services_data]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing services: {e}")
            return []

    async def get_notifications(self, unread_only: bool = False) -> List[SystemNotification]:
        """Get system notifications.

        Args:
            unread_only: Only return unread notifications

        Returns:
            List of SystemNotification objects
        """
        params = {}
        if unread_only:
            params["unread"] = "true"

        response = await self._request("GET", "/api/v1/system/notifications", params=params)

        if not response.success:
            logger.warning(f"Failed to get notifications: {response.error}")
            return []

        try:
            notifications_data = response.data.get("notifications", [])
            return [SystemNotification(**notif) for notif in notifications_data]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing notifications: {e}")
            return []

    async def reboot_system(self) -> bool:
        """Request system reboot.

        Returns:
            True if request successful
        """
        response = await self._request("POST", "/api/v1/system/reboot")
        return response.success

    async def shutdown_system(self) -> bool:
        """Request system shutdown.

        Returns:
            True if request successful
        """
        response = await self._request("POST", "/api/v1/system/shutdown")
        return response.success
