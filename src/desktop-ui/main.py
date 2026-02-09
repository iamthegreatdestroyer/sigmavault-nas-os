#!/usr/bin/env python3
"""
SigmaVault Settings — Application Entry Point

Launch with:
    python main.py
    GTK_DEBUG=interactive python main.py  # With GTK Inspector
"""

import logging
import signal
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib  # noqa: E402

from ui.window import SigmaVaultWindow  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sigmavault")


class SigmaVaultApplication(Adw.Application):
    """Main GTK4 + libadwaita application for SigmaVault NAS management."""

    def __init__(self) -> None:
        super().__init__(
            application_id="com.sigmavault.Settings",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.set_resource_base_path("/com/sigmavault/Settings")
        self._window: SigmaVaultWindow | None = None

    def do_activate(self) -> None:
        """Called when the application is activated."""
        if not self._window:
            self._window = SigmaVaultWindow(application=self)
        self._window.present()

    def do_startup(self) -> None:
        """Called when the application starts up — register actions & shortcuts."""
        Adw.Application.do_startup(self)
        self._create_actions()
        logger.info("SigmaVault Settings started (GTK4 + libadwaita)")

    def _create_actions(self) -> None:
        """Register application-level actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<primary>q"])

        # About dialog
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Preferences
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        self.add_action(prefs_action)
        self.set_accels_for_action("app.preferences", ["<primary>comma"])

    def _on_about(self, _action: Gio.SimpleAction, _param: None) -> None:
        """Show the About dialog."""
        about = Adw.AboutDialog(
            application_name="SigmaVault Settings",
            application_icon="com.sigmavault.Settings",
            developer_name="SigmaVault Project",
            version="0.1.0",
            developers=["SigmaVault Contributors"],
            copyright="© 2025-2026 SigmaVault Project",
            license_type=Adw.License.GPL_3_0,
            comments="AI-Powered NAS Management for GNOME Desktop",
            website="https://github.com/iamthegreatdestroyer/sigmavault-nas-os",
            issue_url="https://github.com/iamthegreatdestroyer/sigmavault-nas-os/issues",
        )
        about.present(self._window)

    def _on_preferences(self, _action: Gio.SimpleAction, _param: None) -> None:
        """Open preferences — navigates to Settings page in-app."""
        if self._window:
            self._window.navigate_to("settings")


def main() -> int:
    """Application entry point."""
    # Allow Ctrl+C to kill the GTK app
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = SigmaVaultApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
