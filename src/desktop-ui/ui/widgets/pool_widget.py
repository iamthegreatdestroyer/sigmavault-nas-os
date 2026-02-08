"""
Pool Widget — ZFS pool capacity bar with health status.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk  # noqa: E402


class PoolWidget(Gtk.Frame):
    """ZFS pool card with capacity bar and health status."""

    def __init__(
        self,
        name: str = "tank",
        health: str = "ONLINE",
        total_bytes: int = 0,
        used_bytes: int = 0,
    ) -> None:
        super().__init__(css_classes=["card"])

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        self.set_child(box)

        # Header: pool name + health badge
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(header)

        header.append(Gtk.Image(icon_name="drive-multidisk-symbolic", pixel_size=24))
        header.append(Gtk.Label(label=name, css_classes=["heading"], xalign=0, hexpand=True))

        health_class = "success" if health == "ONLINE" else "error"
        self._health_label = Gtk.Label(label=health, css_classes=[health_class, "caption"])
        header.append(self._health_label)

        # Capacity progress bar
        fraction = (used_bytes / total_bytes) if total_bytes > 0 else 0
        self._progress = Gtk.ProgressBar(fraction=fraction, show_text=True)
        used_gb = used_bytes / (1024**3)
        total_gb = total_bytes / (1024**3)
        self._progress.set_text(f"{used_gb:.1f} / {total_gb:.1f} GB ({fraction:.0%})")
        box.append(self._progress)

    def update(self, health: str, total_bytes: int, used_bytes: int) -> None:
        """Update pool health and capacity display."""
        health_class = "success" if health == "ONLINE" else "error"
        self._health_label.set_text(health)
        self._health_label.set_css_classes([health_class, "caption"])

        fraction = (used_bytes / total_bytes) if total_bytes > 0 else 0
        self._progress.set_fraction(fraction)
        used_gb = used_bytes / (1024**3)
        total_gb = total_bytes / (1024**3)
        self._progress.set_text(f"{used_gb:.1f} / {total_gb:.1f} GB ({fraction:.0%})")
