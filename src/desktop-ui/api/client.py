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

DEFAULT_API_URL = "http://localhost:3000"
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
        """GET /api/v1/health — System health including agent counts."""
        return self._get("/api/v1/health")

    # ─── Storage ────────────────────────────────────────────────

    def get_storage_summary(self) -> Optional[dict]:
        """GET /api/v1/storage — Storage capacity summary."""
        return self._get("/api/v1/storage")

    def get_disks(self) -> Optional[list]:
        """GET /api/v1/storage/disks — Physical disk inventory."""
        resp = self._get("/api/v1/storage/disks")
        return resp.get("disks", []) if resp else None

    def get_pools(self) -> Optional[list]:
        """GET /api/v1/storage/pools — ZFS pool list."""
        resp = self._get("/api/v1/storage/pools")
        return resp.get("pools", []) if resp else None

    def scrub_pool(self, pool_name: str) -> Optional[dict]:
        """POST /api/v1/storage/pools/{name}/scrub — Initiate scrub."""
        return self._post(f"/api/v1/storage/pools/{pool_name}/scrub")

    # ─── Compression ────────────────────────────────────────────

    def get_compression_stats(self) -> Optional[dict]:
        """GET /api/v1/compression/stats — Compression statistics."""
        return self._get("/api/v1/compression/stats")

    def compress_file(
        self, path: str, algorithm: str = "auto", level: int = 6
    ) -> Optional[dict]:
        """POST /api/v1/compression/jobs — Submit compression job."""
        return self._post(
            "/api/v1/compression/jobs",
            {"path": path, "algorithm": algorithm, "level": level},
        )

    def get_compression_jobs(self) -> Optional[list]:
        """GET /api/v1/compression/jobs — Active compression jobs."""
        resp = self._get("/api/v1/compression/jobs")
        return resp.get("jobs", []) if resp else None

    # ─── Agents ─────────────────────────────────────────────────

    def get_agents(self) -> Optional[list]:
        """GET /api/v1/agents — All agents with status."""
        resp = self._get("/api/v1/agents")
        return resp.get("agents", []) if resp else None

    def get_agent(self, name: str) -> Optional[dict]:
        """GET /api/v1/agents/{name} — Single agent detail."""
        return self._get(f"/api/v1/agents/{name}")

    def assign_agent_task(self, agent_name: str, task: dict) -> Optional[dict]:
        """POST /api/v1/agents/{name}/tasks — Assign task to agent."""
        return self._post(f"/api/v1/agents/{agent_name}/tasks", task)

    # ─── Shares ─────────────────────────────────────────────────

    def get_shares(self) -> Optional[list]:
        """GET /api/v1/shares — Network shares."""
        resp = self._get("/api/v1/shares")
        return resp.get("shares", []) if resp else None

    def create_share(self, share: dict) -> Optional[dict]:
        """POST /api/v1/shares — Create a network share."""
        return self._post("/api/v1/shares", share)

    # ─── System ─────────────────────────────────────────────────

    def get_system_info(self) -> Optional[dict]:
        """GET /api/v1/system — System information."""
        return self._get("/api/v1/system")

    def restart_service(self, service_name: str) -> Optional[dict]:
        """POST /api/v1/system/services/{name}/restart — Restart service."""
        return self._post(f"/api/v1/system/services/{service_name}/restart")
