"""
Status Indicator Widget — Colored dot with label for status bar.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


class StatusIndicator(Gtk.Box):
    """Compact status dot + label for the window status bar."""

    STATUS_CSS = {
        "online": "success",
        "offline": "error",
        "degraded": "warning",
        "unknown": "dim-label",
    }

    STATUS_ICONS = {
        "online": "emblem-ok-symbolic",
        "offline": "process-stop-symbolic",
        "degraded": "dialog-warning-symbolic",
        "unknown": "dialog-question-symbolic",
    }

    def __init__(self, label: str = "Service", status: str = "unknown") -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self._icon = Gtk.Image(
            icon_name=self.STATUS_ICONS.get(status, "dialog-question-symbolic"),
            pixel_size=12,
            css_classes=[self.STATUS_CSS.get(status, "dim-label")],
        )
        self.append(self._icon)

        self._label = Gtk.Label(
            label=label,
            css_classes=["caption"],
        )
        self.append(self._label)

        self._status_label = Gtk.Label(
            label=status,
            css_classes=["caption", self.STATUS_CSS.get(status, "dim-label")],
        )
        self.append(self._status_label)

    def set_status(self, status: str) -> None:
        """Update the status indicator."""
        css = self.STATUS_CSS.get(status, "dim-label")
        icon = self.STATUS_ICONS.get(status, "dialog-question-symbolic")

        self._icon.set_from_icon_name(icon)
        self._icon.set_css_classes([css])
        self._status_label.set_text(status)
        self._status_label.set_css_classes(["caption", css])
