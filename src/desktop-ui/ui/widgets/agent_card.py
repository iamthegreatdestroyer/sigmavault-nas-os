"""
Agent Card Widget — Compact card for agent identity + status.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk  # noqa: E402


class AgentCard(Gtk.Frame):
    """Compact card showing agent name, tier, status, and task count."""

    def __init__(
        self,
        name: str = "Agent",
        tier: int = 1,
        status: str = "idle",
        specialty: str = "",
        tasks_completed: int = 0,
    ) -> None:
        super().__init__(css_classes=["card"])
        self._name = name
        self._tier = tier
        self._status = status

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        self.set_child(box)

        # Header row: icon + name + status dot
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(header)

        icon = Gtk.Image(icon_name="system-run-symbolic", pixel_size=20)
        header.append(icon)

        self._name_label = Gtk.Label(label=name, css_classes=["heading"], xalign=0, hexpand=True)
        header.append(self._name_label)

        self._status_dot = Gtk.Image(
            icon_name="media-record-symbolic",
            pixel_size=12,
            css_classes=["success" if status == "idle" else "warning"],
            tooltip_text=status,
        )
        header.append(self._status_dot)

        # Tier badge
        self._tier_label = Gtk.Label(
            label=f"Tier {tier}",
            css_classes=["dim-label", "caption"],
            xalign=0,
        )
        box.append(self._tier_label)

        # Specialty
        if specialty:
            self._specialty_label = Gtk.Label(
                label=specialty,
                css_classes=["dim-label"],
                xalign=0,
                wrap=True,
            )
            box.append(self._specialty_label)

        # Task count
        self._task_label = Gtk.Label(
            label=f"{tasks_completed} tasks completed",
            css_classes=["dim-label", "caption"],
            xalign=0,
        )
        box.append(self._task_label)

    def set_status(self, status: str) -> None:
        """Update the agent status indicator."""
        self._status = status
        self._status_dot.set_tooltip_text(status)
        if status == "idle":
            self._status_dot.set_css_classes(["success"])
        elif status == "busy":
            self._status_dot.set_css_classes(["warning"])
        else:
            self._status_dot.set_css_classes(["dim-label"])

    def set_tasks_completed(self, count: int) -> None:
        self._task_label.set_text(f"{count} tasks completed")
