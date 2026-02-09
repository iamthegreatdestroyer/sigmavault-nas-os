"""
Metric Gauge Widget — Circular or arc gauge for numeric values.
"""

import math

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402


class MetricGauge(Gtk.DrawingArea):
    """Arc gauge showing a value between 0 and max with a label."""

    def __init__(
        self,
        label: str = "Metric",
        value: float = 0.0,
        max_value: float = 100.0,
        unit: str = "%",
        size: int = 100,
    ) -> None:
        super().__init__()
        self._label = label
        self._value = value
        self._max_value = max_value
        self._unit = unit

        self.set_content_width(size)
        self.set_content_height(size)
        self.set_draw_func(self._draw)

    def _draw(self, _area, cr, width, height) -> None:
        """Render the arc gauge with cairo."""
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 6
        line_width = 8

        # Background arc (full)
        cr.set_line_width(line_width)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.2)
        start_angle = 0.75 * math.pi
        end_angle = 2.25 * math.pi
        cr.arc(cx, cy, radius, start_angle, end_angle)
        cr.stroke()

        # Value arc
        fraction = min(self._value / self._max_value, 1.0) if self._max_value > 0 else 0
        value_end = start_angle + fraction * (end_angle - start_angle)

        # Color based on fraction: green → yellow → red
        if fraction < 0.6:
            cr.set_source_rgba(0.3, 0.8, 0.3, 0.9)
        elif fraction < 0.85:
            cr.set_source_rgba(0.9, 0.7, 0.1, 0.9)
        else:
            cr.set_source_rgba(0.9, 0.2, 0.2, 0.9)

        cr.arc(cx, cy, radius, start_angle, value_end)
        cr.stroke()

        # Center text: value
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.select_font_face("Sans", 0, 1)  # NORMAL, BOLD
        cr.set_font_size(radius * 0.4)
        text = f"{self._value:.0f}{self._unit}"
        extents = cr.text_extents(text)
        cr.move_to(cx - extents.width / 2, cy + extents.height / 4)
        cr.show_text(text)

        # Label below
        cr.set_font_size(radius * 0.22)
        cr.set_source_rgba(1, 1, 1, 0.5)
        extents = cr.text_extents(self._label)
        cr.move_to(cx - extents.width / 2, cy + radius * 0.55)
        cr.show_text(self._label)

    def set_value(self, value: float) -> None:
        self._value = value
        self.queue_draw()

    def set_max_value(self, max_value: float) -> None:
        self._max_value = max_value
        self.queue_draw()
