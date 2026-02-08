"""DashboardView - main overview page showing system and compression stats.

Displays:
- System resource gauges (CPU, Memory, Disk)
- Compression overview cards (Active jobs, Total savings, Throughput)
- Recent compression jobs list
"""

import logging
from typing import Optional, List

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Gtk, Adwaita, GLib

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.api.models import CompressionJob, SystemStatus
from sigmavault_desktop.utils.formatting import (
    format_bytes,
    format_percent,
)
from sigmavault_desktop.utils.async_helpers import run_async
from sigmavault_desktop.widgets.stat_card import StatCard
from sigmavault_desktop.widgets.job_row import JobRow

logger = logging.getLogger(__name__)

# Auto-refresh interval in milliseconds (5 seconds)
REFRESH_INTERVAL_MS = 5000


class DashboardView(Gtk.Box):
    """Dashboard overview page.

    Layout:
        ┌────────────────────────────────────┐
        │  SYSTEM RESOURCES                  │
        │  [CPU %] [Memory %] [Disk %]       │
        ├────────────────────────────────────┤
        │  COMPRESSION                       │
        │  [Active] [Total Jobs] [Savings]   │
        ├────────────────────────────────────┤
        │  RECENT JOBS                       │
        │  [job row 1]                       │
        │  [job row 2]                       │
        │  [job row 3]                       │
        │  ...                               │
        └────────────────────────────────────┘
    """

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize dashboard view.

        Args:
            api_client: Shared API client instance
        """
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        self._api_client = api_client
        self._refresh_source_id: Optional[int] = None

        # Build the scrollable content
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dashboard UI components."""
        # Scrolled window to contain everything
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Main content container with margins
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )
        content.set_halign(Gtk.Align.CENTER)
        content.set_size_request(600, -1)  # Min width

        # ── Section 1: System Resources ──────────────────────────
        sys_header = Gtk.Label(label="System Resources")
        sys_header.add_css_class("title-4")
        sys_header.set_halign(Gtk.Align.START)
        content.append(sys_header)

        sys_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            homogeneous=True,
        )

        self._cpu_card = StatCard(
            title="CPU",
            icon_name="speedometer-symbolic",
            value="—",
            subtitle="Loading…",
        )
        sys_row.append(self._cpu_card)

        self._mem_card = StatCard(
            title="Memory",
            icon_name="drive-harddisk-symbolic",
            value="—",
            subtitle="Loading…",
        )
        sys_row.append(self._mem_card)

        self._disk_card = StatCard(
            title="Disk",
            icon_name="drive-multidisk-symbolic",
            value="—",
            subtitle="Loading…",
        )
        sys_row.append(self._disk_card)

        content.append(sys_row)

        # ── Section 2: Compression Stats ─────────────────────────
        comp_header = Gtk.Label(label="Compression")
        comp_header.add_css_class("title-4")
        comp_header.set_halign(Gtk.Align.START)
        content.append(comp_header)

        comp_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            homogeneous=True,
        )

        self._active_jobs_card = StatCard(
            title="Active Jobs",
            icon_name="media-playback-start-symbolic",
            value="0",
            subtitle="Loading…",
        )
        comp_row.append(self._active_jobs_card)

        self._total_jobs_card = StatCard(
            title="Total Jobs",
            icon_name="view-list-symbolic",
            value="0",
            subtitle="Loading…",
        )
        comp_row.append(self._total_jobs_card)

        self._savings_card = StatCard(
            title="Total Savings",
            icon_name="emblem-ok-symbolic",
            value="—",
            subtitle="Loading…",
        )
        comp_row.append(self._savings_card)

        content.append(comp_row)

        # ── Section 3: Recent Jobs ───────────────────────────────
        jobs_header_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        jobs_header = Gtk.Label(label="Recent Jobs")
        jobs_header.add_css_class("title-4")
        jobs_header.set_halign(Gtk.Align.START)
        jobs_header.set_hexpand(True)
        jobs_header_row.append(jobs_header)

        content.append(jobs_header_row)

        # Jobs list group
        self._jobs_group = Adwaita.PreferencesGroup()
        content.append(self._jobs_group)

        # Empty state placeholder
        self._empty_label = Gtk.Label(
            label="No compression jobs yet. Start a job from the CLI or API."
        )
        self._empty_label.add_css_class("dim-label")
        self._empty_label.set_margin_top(24)
        self._empty_label.set_margin_bottom(24)
        content.append(self._empty_label)

        # Clamp to reasonable width
        clamp = Adwaita.Clamp()
        clamp.set_maximum_size(900)
        clamp.set_tightening_threshold(700)
        clamp.set_child(content)

        scrolled.set_child(clamp)
        self.append(scrolled)

    def start_auto_refresh(self) -> None:
        """Start automatic data refresh timer."""
        if self._refresh_source_id is not None:
            return  # Already running

        # Immediate first fetch
        self.refresh()

        # Schedule periodic refresh
        self._refresh_source_id = GLib.timeout_add(REFRESH_INTERVAL_MS, self._on_refresh_tick)
        logger.debug("Dashboard auto-refresh started")

    def stop_auto_refresh(self) -> None:
        """Stop the auto-refresh timer."""
        if self._refresh_source_id is not None:
            GLib.source_remove(self._refresh_source_id)
            self._refresh_source_id = None
            logger.debug("Dashboard auto-refresh stopped")

    def _on_refresh_tick(self) -> bool:
        """Timer callback for periodic refresh.

        Returns:
            True to keep the timer running
        """
        self.refresh()
        return True  # GLib.SOURCE_CONTINUE

    def refresh(self) -> None:
        """Trigger async data refresh from API."""
        self._fetch_system_status()
        self._fetch_recent_jobs()

    # ── Async Data Fetching ──────────────────────────────────────

    def _fetch_system_status(self) -> None:
        """Fetch system status from API."""

        async def _do_fetch():
            async with SigmaVaultAPIClient(base_url=self._api_client.base_url) as client:
                return await client.get_system_status()

        run_async(
            _do_fetch(),
            callback=self._on_status_received,
            error_callback=self._on_fetch_error,
        )

    def _fetch_recent_jobs(self) -> None:
        """Fetch recent compression jobs from API."""

        async def _do_fetch():
            async with SigmaVaultAPIClient(base_url=self._api_client.base_url) as client:
                return await client.get_compression_jobs(limit=5)

        run_async(
            _do_fetch(),
            callback=self._on_jobs_received,
            error_callback=self._on_fetch_error,
        )

    # ── UI Update Callbacks (run on main thread) ─────────────────

    def _on_status_received(self, status: Optional[SystemStatus]) -> None:
        """Update stat cards with system status data.

        Args:
            status: System status from API, or None on failure
        """
        if status is None:
            self._cpu_card.set_value("Offline")
            self._cpu_card.set_subtitle("API unavailable")
            self._cpu_card.set_value_css_class("error")
            self._mem_card.set_value("—")
            self._disk_card.set_value("—")
            self._active_jobs_card.set_value("—")
            self._total_jobs_card.set_value("—")
            return

        # CPU
        self._cpu_card.set_value(format_percent(status.cpu_percent))
        self._cpu_card.set_subtitle("utilization")
        cpu_class = (
            "error"
            if status.cpu_percent > 90
            else ("warning" if status.cpu_percent > 70 else "success")
        )
        self._cpu_card.set_value_css_class(cpu_class)

        # Memory
        self._mem_card.set_value(format_percent(status.memory_percent))
        self._mem_card.set_subtitle("utilization")
        mem_class = (
            "error"
            if status.memory_percent > 90
            else ("warning" if status.memory_percent > 70 else "success")
        )
        self._mem_card.set_value_css_class(mem_class)

        # Disk
        self._disk_card.set_value(format_percent(status.disk_percent))
        disk_used = format_bytes(status.disk_used_bytes)
        disk_total = format_bytes(status.disk_total_bytes)
        self._disk_card.set_subtitle(f"{disk_used} / {disk_total}")
        disk_class = (
            "error"
            if status.disk_percent > 90
            else ("warning" if status.disk_percent > 80 else "success")
        )
        self._disk_card.set_value_css_class(disk_class)

        # Active / Total jobs
        self._active_jobs_card.set_value(str(status.active_jobs))
        self._active_jobs_card.set_subtitle("currently running")
        if status.active_jobs > 0:
            self._active_jobs_card.set_value_css_class("accent")
        else:
            self._active_jobs_card.set_value_css_class("")

        self._total_jobs_card.set_value(str(status.total_jobs))
        self._total_jobs_card.set_subtitle("all time")

    def _on_jobs_received(self, jobs: List[CompressionJob]) -> None:
        """Update recent jobs list.

        Args:
            jobs: List of recent compression jobs
        """
        # Clear existing rows from the group
        # AdwPreferencesGroup doesn't have a clear method,
        # so we remove children from its internal list box
        while True:
            child = self._jobs_group.get_first_child()
            if child is None:
                break
            # Walk to find the listbox inside the group
            self._jobs_group.remove(child)

        if not jobs:
            self._empty_label.set_visible(True)
            self._savings_card.set_value("—")
            self._savings_card.set_subtitle("no data yet")
            return

        self._empty_label.set_visible(False)

        # Calculate total savings across all returned jobs
        total_saved = sum(j.savings_bytes for j in jobs)
        self._savings_card.set_value(format_bytes(total_saved))
        self._savings_card.set_subtitle(f"from {len(jobs)} recent job(s)")
        if total_saved > 0:
            self._savings_card.set_value_css_class("success")

        # Add job rows
        for job in jobs[:5]:
            row = JobRow(job)
            row.connect("activated", self._on_job_row_activated)
            self._jobs_group.add(row)

    def _on_job_row_activated(self, row: JobRow) -> None:
        """Handle click on a job row.

        Args:
            row: The activated job row
        """
        logger.info(f"Dashboard job clicked: {row.job_id}")
        # Emit signal or callback to parent to navigate to job detail
        # This will be wired by MainWindow

    def _on_fetch_error(self, error: Exception) -> None:
        """Handle API fetch errors.

        Args:
            error: The exception that occurred
        """
        logger.warning(f"Dashboard fetch error: {error}")
        self._cpu_card.set_value("Error")
        self._cpu_card.set_subtitle(str(error)[:40])
        self._cpu_card.set_value_css_class("error")
