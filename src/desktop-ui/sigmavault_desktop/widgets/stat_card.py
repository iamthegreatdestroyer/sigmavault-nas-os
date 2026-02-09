"""StatCard widget - displays a single statistic with title, value, and subtitle.

Used on the Dashboard to show CPU %, Memory %, Disk usage, Active jobs, etc.
Follows GNOME HIG card pattern with Adwaita styling.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Adwaita, Gtk


class StatCard(Gtk.Box):
    """A card widget displaying a labeled statistic.

    Layout:
        ┌──────────────────┐
        │  [icon]  Title   │
        │     VALUE        │
        │   subtitle       │
        └──────────────────┘
    """

    def __init__(
        self,
        title: str = "",
        value: str = "—",
        subtitle: str = "",
        icon_name: str = "",
    ):
        """Initialize stat card.

        Args:
            title: Card title (e.g., 'CPU Usage')
            value: Main value display (e.g., '45.2%')
            subtitle: Secondary info (e.g., '4 cores')
            icon_name: GTK icon name (e.g., 'speedometer-symbolic')
        """
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
            margin_top=16,
            margin_bottom=16,
            margin_start=16,
            margin_end=16,
            hexpand=True,
        )

        # Add card styling
        self.add_css_class("card")

        # Header row: icon + title
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_halign(Gtk.Align.CENTER)

        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(16)
            icon.add_css_class("dim-label")
            header.append(icon)

        self._title_label = Gtk.Label(label=title)
        self._title_label.add_css_class("dim-label")
        self._title_label.add_css_class("caption")
        header.append(self._title_label)

        self.append(header)

        # Value (large, bold)
        self._value_label = Gtk.Label(label=value)
        self._value_label.add_css_class("title-1")
        self._value_label.set_halign(Gtk.Align.CENTER)
        self.append(self._value_label)

        # Subtitle
        self._subtitle_label = Gtk.Label(label=subtitle)
        self._subtitle_label.add_css_class("dim-label")
        self._subtitle_label.add_css_class("caption")
        self._subtitle_label.set_halign(Gtk.Align.CENTER)
        self.append(self._subtitle_label)

    def set_value(self, value: str) -> None:
        """Update the displayed value.

        Args:
            value: New value string
        """
        self._value_label.set_label(value)

    def set_subtitle(self, subtitle: str) -> None:
        """Update the subtitle text.

        Args:
            subtitle: New subtitle string
        """
        self._subtitle_label.set_label(subtitle)

    def set_title(self, title: str) -> None:
        """Update the title text.

        Args:
            title: New title string
        """
        self._title_label.set_label(title)

    def set_value_css_class(self, css_class: str) -> None:
        """Set a CSS class on the value label for coloring.

        Args:
            css_class: CSS class name (e.g., 'success', 'error', 'accent')
        """
        # Remove previous status classes
        for cls in ("success", "error", "accent", "warning"):
            self._value_label.remove_css_class(cls)

        if css_class:
            self._value_label.add_css_class(css_class)
