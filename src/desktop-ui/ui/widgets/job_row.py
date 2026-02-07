"""
Job Row Widget — Compression job entry for list display.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402


class JobRow(Adw.ActionRow):
    """A row representing an active or completed compression job."""

    def __init__(
        self,
        filename: str = "unknown",
        status: str = "queued",
        progress: float = 0.0,
        algorithm: str = "auto",
        original_size: int = 0,
        compressed_size: int = 0,
    ) -> None:
        icon_map = {
            "queued": "content-loading-symbolic",
            "running": "media-playback-start-symbolic",
            "completed": "emblem-ok-symbolic",
            "failed": "dialog-error-symbolic",
        }
        icon_name = icon_map.get(status, "content-loading-symbolic")

        ratio = ""
        if original_size > 0 and compressed_size > 0:
            r = 1 - (compressed_size / original_size)
            ratio = f" — {r:.1%} reduction"

        super().__init__(
            title=filename,
            subtitle=f"{status.title()} | {algorithm}{ratio}",
            icon_name=icon_name,
        )

        if status == "running":
            progress_bar = Gtk.ProgressBar(
                fraction=progress,
                valign=Gtk.Align.CENTER,
                css_classes=["osd"],
            )
            progress_bar.set_size_request(120, -1)
            self.add_suffix(progress_bar)
        elif status == "completed":
            check = Gtk.Image(
                icon_name="emblem-ok-symbolic",
                css_classes=["success"],
                valign=Gtk.Align.CENTER,
            )
            self.add_suffix(check)
        elif status == "failed":
            err = Gtk.Image(
                icon_name="dialog-error-symbolic",
                css_classes=["error"],
                valign=Gtk.Align.CENTER,
            )
            self.add_suffix(err)

    def update_progress(self, progress: float) -> None:
        """Update progress bar fraction (if running)."""
        # The progress bar is added as a suffix; walk children to find it
        child = self.get_first_child()
        while child:
            if isinstance(child, Gtk.ProgressBar):
                child.set_fraction(progress)
                break
            child = child.get_next_sibling()
