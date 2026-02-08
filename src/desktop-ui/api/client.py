"""
SigmaVault API Client — HTTP client for the Go API server (:3000).

Thread-safe synchronous client using urllib (no external deps).
Uses GLib.idle_add() pattern for GTK thread safety.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Optional

logger = logging.getLogger("sigmavault.api.client")

DEFAULT_API_URL = "http://localhost:12080"
DEFAULT_TIMEOUT = 5  # seconds


class SigmaVaultAPIClient:
    """Synchronous HTTP client for the SigmaVault Go API.

    All methods return parsed JSON dicts or None on failure.
    Designed to be called from GLib.idle_add or background threads.
    """

    def __init__(self, base_url: str = DEFAULT_API_URL, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token: Optional[str] = None

    # ─── Configuration ──────────────────────────────────────────

    def set_base_url(self, url: str) -> None:
        self._base_url = url.rstrip("/")

    def set_token(self, token: str) -> None:
        self._token = token

    # ─── Low-level HTTP ─────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
    ) -> Optional[dict]:
        """Make an HTTP request and return parsed JSON."""
        url = f"{self._base_url}{path}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        data = json.dumps(body).encode("utf-8") if body else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            logger.warning("HTTP %s %s → %d %s", method, path, e.code, e.reason)
            return None
        except urllib.error.URLError as e:
            logger.debug("URL error %s %s → %s", method, path, e.reason)
            return None
        except Exception as e:
            logger.debug("Request failed %s %s → %s", method, path, e)
            return None

    def _get(self, path: str) -> Optional[dict]:
        return self._request("GET", path)

    def _post(self, path: str, body: Optional[dict] = None) -> Optional[dict]:
        return self._request("POST", path, body)

    def _put(self, path: str, body: Optional[dict] = None) -> Optional[dict]:
        return self._request("PUT", path, body)

    def _delete(self, path: str) -> Optional[dict]:
        return self._request("DELETE", path)

    # ─── Health ─────────────────────────────────────────────────

    def get_health(self) -> Optional[dict]:
        """GET /api/v1/health — Basic health check."""
        return self._get("/api/v1/health")

    def get_system_status(self) -> Optional[dict]:
        """GET /api/v1/system/status — System status with uptime, CPU, memory."""
        return self._get("/api/v1/system/status")

    def get_info(self) -> Optional[dict]:
        """GET /api/v1/info — System information."""
        return self._get("/api/v1/info")

    # ─── Storage ────────────────────────────────────────────────

    def get_disks(self) -> Optional[dict]:
        """GET /api/v1/storage/disks — List physical disks with SMART status."""
        return self._get("/api/v1/storage/disks")

    def get_pools(self) -> Optional[dict]:
        """GET /api/v1/storage/pools — ZFS pool list with summary."""
        return self._get("/api/v1/storage/pools")

    def get_pool(self, pool_id: str) -> Optional[dict]:
        """GET /api/v1/storage/pools/:id — Get specific pool."""
        return self._get(f"/api/v1/storage/pools/{pool_id}")

    def get_datasets(self) -> Optional[dict]:
        """GET /api/v1/storage/datasets — List ZFS datasets."""
        return self._get("/api/v1/storage/datasets")

    def get_shares(self) -> Optional[dict]:
        """GET /api/v1/storage/shares — Network shares list."""
        return self._get("/api/v1/storage/shares")

    def create_pool(self, pool_data: dict) -> Optional[dict]:
        """POST /api/v1/storage/pools — Create ZFS pool."""
        return self._post("/api/v1/storage/pools", pool_data)

    def create_share(self, share_data: dict) -> Optional[dict]:
        """POST /api/v1/storage/shares — Create network share."""
        return self._post("/api/v1/storage/shares", share_data)

    # ─── Compression ────────────────────────────────────────────

    def get_compression_queue(self) -> Optional[dict]:
        """GET /api/v1/compression/queue — Compression queue stats."""
        return self._get("/api/v1/compression/queue")

    def get_compression_jobs(self) -> Optional[dict]:
        """GET /api/v1/compression/jobs — Active compression jobs."""
        return self._get("/api/v1/compression/jobs")

    def get_compression_stats(self) -> Optional[dict]:
        """GET /api/v1/compression/stats — Compression statistics and history."""
        return self._get("/api/v1/compression/stats")

    def compress_file(
        self, path: str, algorithm: str = "auto", level: int = 6
    ) -> Optional[dict]:
        """POST /api/v1/compression/jobs — Submit compression job."""
        return self._post(
            "/api/v1/compression/jobs",
            {"path": path, "algorithm": algorithm, "level": level},
        )

    def compress_file_v2(self, path: str, algorithm: str = "zstd") -> Optional[dict]:
        """POST /api/v1/compression/file — Submit file compression."""
        return self._post("/api/v1/compression/file", {"path": path, "algorithm": algorithm})

    # ─── Agents ─────────────────────────────────────────────────

    def get_agents(self) -> Optional[dict]:
        """GET /api/v1/agents — All agents with status and counts."""
        return self._get("/api/v1/agents")

    def get_agent(self, name: str) -> Optional[dict]:
        """GET /api/v1/agents/{name} — Single agent detail."""
        return self._get(f"/api/v1/agents/{name}")

    def get_agent_metrics(self, agent_id: str) -> Optional[dict]:
        """GET /api/v1/agents/:id/metrics — Agent performance metrics."""
        return self._get(f"/api/v1/agents/{agent_id}/metrics")

    # ─── System ─────────────────────────────────────────────────

    def get_services(self) -> Optional[dict]:
        """GET /api/v1/system/services — List system services."""
        return self._get("/api/v1/system/services")

    def restart_service(self, service_id: str) -> Optional[dict]:
        """POST /api/v1/system/services/:id/restart — Restart service."""
        return self._post(f"/api/v1/system/services/{service_id}/restart")
