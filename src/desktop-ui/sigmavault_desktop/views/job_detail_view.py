"""JobDetailView - detailed view of a single compression job.

Pushed onto the NavigationView stack when a job row is activated.
Shows full metadata, progress (if running), and error details (if failed).
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Gtk, Adwaita

from sigmavault_desktop.api.models import CompressionJob
from sigmavault_desktop.utils.formatting import (
    format_bytes,
    format_duration,
    format_percent,
    format_ratio,
    format_throughput,
    status_to_icon,
    status_to_css_class,
)

logger = logging.getLogger(__name__)


class JobDetailView(Adwaita.NavigationPage):
    """Detailed view for a single compression job.

    Layout:
        ┌────────────────────────────────────┐
        │  ← Back     Job abc123...          │
        ├────────────────────────────────────┤
        │  STATUS BANNER                     │
        │  [✓ Completed] / [⚠ Failed] / ... │
        ├────────────────────────────────────┤
        │  FILE INFORMATION                  │
        │  Original Size:  2.34 GB           │
        │  Compressed:     350 MB            │
        │  Ratio:          6.7:1             │
        │  Savings:        85.0%             │
        ├────────────────────────────────────┤
        │  PROCESSING                        │
        │  Method:         zstd-ultra        │
        │  Data Type:      binary            │
        │  Elapsed:        12m 5s            │
        │  Throughput:     32.1 MB/s         │
        ├────────────────────────────────────┤
        │  METADATA                          │
        │  Job ID:         abc123def456...   │
        │  Created:        2025-01-15 14:30  │
        ├────────────────────────────────────┤
        │  ERROR (if failed)                 │
        │  Decompressor exited with code 1   │
        └────────────────────────────────────┘
    """

    def __init__(self, job: CompressionJob):
        """Initialize job detail view.

        Args:
            job: The compression job to display
        """
        title = f"Job {job.job_id[:12]}…" if len(job.job_id) > 12 else f"Job {job.job_id}"
        super().__init__(title=title, tag=f"job-{job.job_id}")

        self._job = job
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the detail UI."""
        job = self._job

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Content with clamp
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )

        clamp = Adwaita.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_tightening_threshold(500)

        # ── Status Banner ────────────────────────────────────────
        status_banner = self._build_status_banner(job)
        content.append(status_banner)

        # ── File Information Group ───────────────────────────────
        file_group = Adwaita.PreferencesGroup()
        file_group.set_title("File Information")

        file_group.add(
            self._make_row(
                "Original Size",
                format_bytes(job.original_size),
                icon="document-open-symbolic",
            )
        )
        file_group.add(
            self._make_row(
                "Compressed Size",
                format_bytes(job.compressed_size),
                icon="package-x-generic-symbolic",
            )
        )
        file_group.add(
            self._make_row(
                "Compression Ratio",
                format_ratio(job.compression_ratio),
                icon="zoom-in-symbolic",
            )
        )
        file_group.add(
            self._make_row(
                "Space Savings",
                f"{format_percent(job.savings_percent)} ({format_bytes(job.savings_bytes)})",
                icon="emblem-ok-symbolic",
            )
        )

        content.append(file_group)

        # ── Processing Group ─────────────────────────────────────
        proc_group = Adwaita.PreferencesGroup()
        proc_group.set_title("Processing")

        proc_group.add(
            self._make_row(
                "Method",
                job.method,
                icon="applications-engineering-symbolic",
            )
        )
        proc_group.add(
            self._make_row(
                "Data Type",
                job.data_type,
                icon="text-x-generic-symbolic",
            )
        )
        proc_group.add(
            self._make_row(
                "Elapsed Time",
                format_duration(job.elapsed_seconds),
                icon="preferences-system-time-symbolic",
            )
        )
        proc_group.add(
            self._make_row(
                "Throughput",
                format_throughput(job.throughput_mbps),
                icon="network-transmit-symbolic",
            )
        )

        content.append(proc_group)

        # ── Metadata Group ───────────────────────────────────────
        meta_group = Adwaita.PreferencesGroup()
        meta_group.set_title("Metadata")

        meta_group.add(self._make_row("Job ID", job.job_id))
        meta_group.add(self._make_row("Created", job.created_at))
        meta_group.add(self._make_row("Status", job.status.capitalize()))

        content.append(meta_group)

        # ── Error Group (only if failed) ─────────────────────────
        if job.is_failed and job.error:
            error_group = Adwaita.PreferencesGroup()
            error_group.set_title("Error Details")

            error_row = Adwaita.ActionRow()
            error_row.set_title("Error Message")
            error_row.set_subtitle(job.error)
            error_row.add_css_class("error")

            error_icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
            error_icon.add_css_class("error")
            error_row.add_prefix(error_icon)

            error_group.add(error_row)
            content.append(error_group)

        # ── Progress bar (if running) ────────────────────────────
        if job.is_running:
            progress_group = Adwaita.PreferencesGroup()
            progress_group.set_title("Progress")

            progress_bar = Gtk.ProgressBar()
            progress_bar.set_show_text(True)
            progress_bar.set_text("Processing…")
            progress_bar.pulse()  # Indeterminate
            progress_bar.set_margin_top(8)
            progress_bar.set_margin_bottom(8)
            progress_bar.set_margin_start(16)
            progress_bar.set_margin_end(16)

            progress_group.add(progress_bar)
            content.append(progress_group)

        clamp.set_child(content)
        scrolled.set_child(clamp)
        self.set_child(scrolled)

    def _build_status_banner(self, job: CompressionJob) -> Gtk.Box:
        """Build the status banner at the top.

        Args:
            job: The compression job

        Returns:
            GTK Box containing the status banner
        """
        banner = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=8,
            margin_bottom=8,
            margin_start=16,
            margin_end=16,
            halign=Gtk.Align.CENTER,
        )
        banner.add_css_class("card")

        icon = Gtk.Image.new_from_icon_name(status_to_icon(job.status))
        icon.set_pixel_size(32)
        css_class = status_to_css_class(job.status)
        if css_class:
            icon.add_css_class(css_class)
        banner.append(icon)

        status_text = Gtk.Label(label=job.status.upper())
        status_text.add_css_class("title-2")
        if css_class:
            status_text.add_css_class(css_class)
        banner.append(status_text)

        return banner

    @staticmethod
    def _make_row(
        title: str,
        value: str,
        icon: str = "",
    ) -> Adwaita.ActionRow:
        """Create an info row for the detail view.

        Args:
            title: Row title/label
            value: Row value
            icon: Optional icon name

        Returns:
            Configured ActionRow
        """
        row = Adwaita.ActionRow()
        row.set_title(title)
        row.set_subtitle(value)

        if icon:
            img = Gtk.Image.new_from_icon_name(icon)
            img.add_css_class("dim-label")
            row.add_prefix(img)

        # Selectable value label at end
        value_label = Gtk.Label(label=value)
        value_label.set_selectable(True)
        value_label.add_css_class("heading")
        row.add_suffix(value_label)

        return row

    @property
    def job(self) -> CompressionJob:
        """Get the job displayed by this view."""
        return self._job
