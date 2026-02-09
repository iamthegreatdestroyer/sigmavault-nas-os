"""Main application class for SigmaVault Native UI.

Manages the Adwaita application lifecycle, API client, and window creation.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Adwaita, Gdk, Gio, Gtk

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.window import MainWindow

# Resolve path to bundled stylesheet
_STYLE_CSS = Path(__file__).parent / "data" / "style.css"

logger = logging.getLogger(__name__)

# Default API endpoint
DEFAULT_API_URL = "http://localhost:12080"


class Application(Adwaita.Application):
    """Main GNOME application.

    Manages lifecycle:
    1. startup → register actions, create API client
    2. activate → create/present MainWindow
    3. shutdown → close API client
    """

    def __init__(self, api_url: str = DEFAULT_API_URL):
        """Initialize the application.

        Args:
            api_url: Base URL for the Go API
        """
        super().__init__(
            application_id="com.sigmavault.desktop", flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )

        self._api_url = api_url
        self._api_client = SigmaVaultAPIClient(base_url=api_url)

        self.connect("activate", self.on_activate)
        self.connect("startup", self.on_startup)
        self.connect("shutdown", self.on_shutdown)

    def on_startup(self, app: "Application") -> None:
        """Handle application startup - register actions and shortcuts.

        Args:
            app: The application instance
        """
        logger.info(f"Application startup (API: {self._api_url})")

        # About action
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        # Quit action (Ctrl+Q)
        action_quit = Gio.SimpleAction.new("quit", None)
        action_quit.connect("activate", self.on_quit)
        self.add_action(action_quit)
        self.set_accels_for_action("app.quit", ["<Control>q"])

        # Load custom stylesheet
        self._load_css()

    def on_activate(self, app: "Application") -> None:
        """Handle activation - create or present the main window.

        Args:
            app: The application instance
        """
        logger.info("Application activate")

        window = app.get_active_window()
        if window is None:
            window = MainWindow(app, api_client=self._api_client)
        window.present()

    # ── CSS Loading ────────────────────────────────────────────────

    def _load_css(self) -> None:
        """Load the custom stylesheet and apply it to the default display."""
        if not _STYLE_CSS.exists():
            logger.warning(f"Stylesheet not found: {_STYLE_CSS}")
            return

        provider = Gtk.CssProvider()
        provider.load_from_path(str(_STYLE_CSS))

        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            logger.info(f"Custom stylesheet loaded: {_STYLE_CSS.name}")
        else:
            logger.warning("No default display — CSS not applied")

    def on_shutdown(self, app: "Application") -> None:
        """Handle shutdown - cleanup resources.

        Args:
            app: The application instance
        """
        logger.info("Application shutdown - cleaning up")
        # aiohttp session cleanup is handled by context managers
        # in each async call, so no explicit close needed here

    def on_about(self, action: Gio.SimpleAction, param) -> None:
        """Show about dialog.

        Args:
            action: The action
            param: Parameters
        """
        dialog = Adwaita.AboutWindow(
            transient_for=self.get_active_window(),
            application_name="SigmaVault",
            version="0.2.0",
            copyright="Copyright 2026 SigmaVault Contributors",
            license_type=Gtk.License.APACHE_2_0,
            comments="Native GNOME desktop UI for SigmaVault NAS compression management",
            website="https://github.com/iamthegreatdestroyer/sigmavault-nas-os",
            issue_url="https://github.com/iamthegreatdestroyer/sigmavault-nas-os/issues",
            developers=["SigmaVault Contributors"],
            application_icon="drive-multidisk-symbolic",
        )
        dialog.present()

    def on_quit(self, action: Gio.SimpleAction, param) -> None:
        """Quit the application.

        Args:
            action: The action
            param: Parameters
        """
        self.quit()

    def run(self, argv: Optional[list] = None) -> int:
        """Run the application.

        Args:
            argv: Command-line arguments

        Returns:
            Application exit code
        """
        return super().run(argv)
