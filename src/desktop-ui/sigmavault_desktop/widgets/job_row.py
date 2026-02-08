"""JobRow widget - displays a compression job summary in a list.

Used in both the Dashboard (recent jobs) and the Jobs list view.
Follows GNOME HIG list row patterns with Adwaita.ActionRow styling.
"""

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
    status_to_icon,
    status_to_css_class,
)


class JobRow(Adwaita.ActionRow):
    """A list row displaying a compression job summary.

    Layout:
        ┌─[status icon]──────────────────────────────[ratio]──[>]─┐
        │  Job abc123...         method: zstd-ultra │ 6.7:1       │
        │  2.3 GB → 350 MB      elapsed: 12m 5s    │ savings: 85%│
        └─────────────────────────────────────────────────────────┘
    """

    def __init__(self, job: CompressionJob):
        """Initialize job row.

        Args:
            job: The compression job to display
        """
        super().__init__()

        self._job = job

        # Title: job ID (truncated) + method
        title = f"{job.job_id[:12]}…" if len(job.job_id) > 12 else job.job_id
        self.set_title(title)

        # Subtitle: size info + timing
        original = format_bytes(job.original_size)
        compressed = format_bytes(job.compressed_size)
        elapsed = format_duration(job.elapsed_seconds)
        self.set_subtitle(f"{original} → {compressed}  ·  {elapsed}  ·  {job.method}")

        # Status icon (prefix)
        status_icon = Gtk.Image.new_from_icon_name(status_to_icon(job.status))
        status_icon.set_pixel_size(24)
        css_class = status_to_css_class(job.status)
        if css_class:
            status_icon.add_css_class(css_class)
        self.add_prefix(status_icon)

        # Ratio + savings badge (suffix)
        stats_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            valign=Gtk.Align.CENTER,
        )

        ratio_label = Gtk.Label(label=format_ratio(job.compression_ratio))
        ratio_label.add_css_class("heading")
        stats_box.append(ratio_label)

        savings_label = Gtk.Label(label=f"↓ {format_percent(job.savings_percent, 1)}")
        savings_label.add_css_class("caption")
        savings_label.add_css_class("dim-label")
        stats_box.append(savings_label)

        self.add_suffix(stats_box)

        # Navigation chevron
        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        self.add_suffix(chevron)

        # Make activatable (clickable)
        self.set_activatable(True)

    @property
    def job(self) -> CompressionJob:
        """Get the compression job for this row."""
        return self._job

    @property
    def job_id(self) -> str:
        """Get the job ID."""
        return self._job.job_id
