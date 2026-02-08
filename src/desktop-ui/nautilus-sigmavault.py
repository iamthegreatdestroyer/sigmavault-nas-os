"""
Nautilus Extension — Right-click "Compress with SigmaVault" in Files.

Install to: ~/.local/share/nautilus-python/extensions/
Or system-wide: /usr/share/nautilus-python/extensions/

Communicates via D-Bus to the running SigmaVault Settings application.
"""

import logging
import os

import gi

gi.require_version("Nautilus", "4.0")  # Nautilus 43+ (GNOME 43+/GTK4)
gi.require_version("GObject", "2.0")
from gi.repository import Nautilus, GObject, Gio, GLib  # noqa: E402

logger = logging.getLogger("sigmavault.nautilus")


class SigmaVaultNautilusExtension(GObject.GObject, Nautilus.MenuProvider):
    """Nautilus extension adding 'Compress with SigmaVault' to the context menu."""

    COMPRESSIBLE_MIMES = {
        "application/octet-stream",
        "application/zip",
        "application/x-tar",
        "application/gzip",
        "text/plain",
        "text/csv",
        "image/png",
        "image/jpeg",
        "video/mp4",
        "application/json",
        "application/xml",
    }

    def get_file_items(self, files: list) -> list:
        """Called by Nautilus to get context menu items for selected files."""
        if not files:
            return []

        # Filter: only real files (not directories)
        real_files = [f for f in files if f.get_uri_scheme() == "file" and not f.is_directory()]
        if not real_files:
            return []

        # Create menu item
        item = Nautilus.MenuItem(
            name="SigmaVaultExtension::Compress",
            label="Compress with SigmaVault",
            tip="Compress selected files using SigmaVault AI engine",
            icon="package-x-generic-symbolic",
        )
        item.connect("activate", self._on_compress, real_files)

        return [item]

    def get_background_items(self, current_folder) -> list:
        """Background (right-click in empty space) menu items."""
        return []  # No background items for now

    def _on_compress(self, _menu_item, files: list) -> None:
        """Handle the 'Compress with SigmaVault' click via D-Bus."""
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

            for f in files:
                path = f.get_location().get_path()
                if not path:
                    continue

                logger.info("Requesting SigmaVault compression: %s", path)

                bus.call_sync(
                    "com.sigmavault.Settings",
                    "/com/sigmavault/Settings",
                    "com.sigmavault.Settings",
                    "CompressFile",
                    GLib.Variant("(ss)", (path, "auto")),
                    GLib.VariantType("(s)"),
                    Gio.DBusCallFlags.NONE,
                    5000,  # 5 second timeout
                    None,
                )

        except Exception as e:
            logger.error("SigmaVault D-Bus call failed: %s", e)
            # Fallback: Show a notification that SigmaVault isn't running
            try:
                notification = Gio.Notification.new("SigmaVault")
                notification.set_body(
                    "SigmaVault Settings is not running.\n" "Start it from the application menu."
                )
                app = Gio.Application.get_default()
                if app:
                    app.send_notification("sigmavault-error", notification)
            except Exception:
                pass
