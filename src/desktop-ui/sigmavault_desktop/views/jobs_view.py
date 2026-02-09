"""JobsListView - scrollable, filterable list of all compression jobs.

Root page of the Jobs navigation stack. Supports status filtering
and navigates to JobDetailView on row activation.
"""

import logging
from typing import Callable, List, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Adwaita, GLib, Gtk

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.api.models import CompressionJob
from sigmavault_desktop.utils.async_helpers import run_async
from sigmavault_desktop.widgets.job_row import JobRow

logger = logging.getLogger(__name__)

# All valid status filter options
STATUS_FILTERS = ["all", "running", "queued", "completed", "failed"]

# Auto-refresh interval (10 seconds for the full list)
REFRESH_INTERVAL_MS = 10_000


class JobsListView(Adwaita.NavigationPage):
    """Filterable list of compression jobs.

    Layout:
        ┌────────────────────────────────────┐
        │  [Status ▼ all]  [🔄 Refresh]     │
        ├────────────────────────────────────┤
        │  [job row 1]                       │
        │  [job row 2]                       │
        │  [job row 3]                       │
        │  ...                               │
        ├────────────────────────────────────┤
        │  Showing 42 jobs                   │
        └────────────────────────────────────┘
    """

    def __init__(
        self,
        api_client: SigmaVaultAPIClient,
        on_job_selected: Optional[Callable[[CompressionJob], None]] = None,
    ):
        """Initialize jobs list view.

        Args:
            api_client: Shared API client instance
            on_job_selected: Callback when a job is clicked
        """
        super().__init__(title="All Jobs", tag="jobs-list")

        self._api_client = api_client
        self._on_job_selected = on_job_selected
        self._current_filter: str = "all"
        self._refresh_source_id: Optional[int] = None
        self._all_jobs: List[CompressionJob] = []

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the jobs list UI."""
        # Top-level toolbar view
        toolbar_view = Adwaita.ToolbarView()

        # ── Top bar: filter + refresh ────────────────────────────
        top_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )

        # Status filter dropdown
        filter_label = Gtk.Label(label="Status:")
        filter_label.add_css_class("dim-label")
        top_bar.append(filter_label)

        self._filter_dropdown = Gtk.DropDown.new_from_strings(STATUS_FILTERS)
        self._filter_dropdown.set_selected(0)
        self._filter_dropdown.connect("notify::selected", self._on_filter_changed)
        top_bar.append(self._filter_dropdown)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_bar.append(spacer)

        # Job count label
        self._count_label = Gtk.Label(label="Loading…")
        self._count_label.add_css_class("dim-label")
        self._count_label.add_css_class("caption")
        top_bar.append(self._count_label)

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh jobs")
        refresh_btn.connect("clicked", lambda _: self.refresh())
        top_bar.append(refresh_btn)

        toolbar_view.add_top_bar(top_bar)

        # ── Main content: scrollable job list ────────────────────
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Clamp for readability
        clamp = Adwaita.Clamp()
        clamp.set_maximum_size(900)
        clamp.set_tightening_threshold(700)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            margin_top=12,
            margin_bottom=24,
            margin_start=12,
            margin_end=12,
        )

        # Jobs preference group (uses Adwaita list styling)
        self._jobs_group = Adwaita.PreferencesGroup()
        content.append(self._jobs_group)

        # Empty state
        self._empty_status = Adwaita.StatusPage()
        self._empty_status.set_icon_name("folder-symbolic")
        self._empty_status.set_title("No Jobs Found")
        self._empty_status.set_description(
            "No compression jobs match the current filter. " "Start a job via the CLI or REST API."
        )
        self._empty_status.set_visible(False)
        content.append(self._empty_status)

        # Loading spinner
        self._spinner = Gtk.Spinner()
        self._spinner.set_size_request(32, 32)
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_margin_top(48)
        self._spinner.set_spinning(True)
        content.append(self._spinner)

        clamp.set_child(content)
        scrolled.set_child(clamp)
        toolbar_view.set_content(scrolled)

        self.set_child(toolbar_view)

    def start_auto_refresh(self) -> None:
        """Start periodic job list refresh."""
        if self._refresh_source_id is not None:
            return

        self.refresh()
        self._refresh_source_id = GLib.timeout_add(REFRESH_INTERVAL_MS, self._on_refresh_tick)
        logger.debug("Jobs list auto-refresh started")

    def stop_auto_refresh(self) -> None:
        """Stop periodic refresh."""
        if self._refresh_source_id is not None:
            GLib.source_remove(self._refresh_source_id)
            self._refresh_source_id = None
            logger.debug("Jobs list auto-refresh stopped")

    def _on_refresh_tick(self) -> bool:
        """Timer callback."""
        self.refresh()
        return True

    def refresh(self) -> None:
        """Fetch jobs from API with current filter."""
        status_filter = None if self._current_filter == "all" else self._current_filter

        async def _do_fetch():
            async with SigmaVaultAPIClient(base_url=self._api_client.base_url) as client:
                return await client.get_compression_jobs(
                    status=status_filter,
                    limit=200,
                )

        run_async(
            _do_fetch(),
            callback=self._on_jobs_received,
            error_callback=self._on_fetch_error,
        )

    # ── Callbacks ────────────────────────────────────────────────

    def _on_filter_changed(self, dropdown: Gtk.DropDown, _pspec) -> None:
        """Handle filter dropdown selection change."""
        selected = dropdown.get_selected()
        self._current_filter = STATUS_FILTERS[selected]
        logger.debug(f"Filter changed to: {self._current_filter}")
        self.refresh()

    def _on_jobs_received(self, jobs: List[CompressionJob]) -> None:
        """Update the job list with received data."""
        self._spinner.set_spinning(False)
        self._spinner.set_visible(False)

        self._all_jobs = jobs

        # Clear existing rows
        while True:
            child = self._jobs_group.get_first_child()
            if child is None:
                break
            self._jobs_group.remove(child)

        if not jobs:
            self._empty_status.set_visible(True)
            self._jobs_group.set_visible(False)
            self._count_label.set_label("0 jobs")
            return

        self._empty_status.set_visible(False)
        self._jobs_group.set_visible(True)
        self._count_label.set_label(f"{len(jobs)} job(s)")

        for job in jobs:
            row = JobRow(job)
            row.connect("activated", self._on_row_activated)
            self._jobs_group.add(row)

    def _on_row_activated(self, row: JobRow) -> None:
        """Handle job row click - navigate to detail."""
        logger.info(f"Job selected: {row.job_id}")
        if self._on_job_selected:
            self._on_job_selected(row.job)

    def _on_fetch_error(self, error: Exception) -> None:
        """Handle API errors."""
        self._spinner.set_spinning(False)
        self._spinner.set_visible(False)

        logger.warning(f"Jobs fetch error: {error}")
        self._empty_status.set_title("Connection Error")
        self._empty_status.set_description(str(error)[:200])
        self._empty_status.set_icon_name("network-error-symbolic")
        self._empty_status.set_visible(True)
        self._jobs_group.set_visible(False)
        self._count_label.set_label("Error")
