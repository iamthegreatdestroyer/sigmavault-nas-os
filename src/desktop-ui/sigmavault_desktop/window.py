"""Main application window for SigmaVault Native UI.

Implements ViewStack-based navigation with Dashboard and Jobs views,
connected to the Go API via SigmaVaultAPIClient.
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Adwaita, Gio, GLib, Gtk

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.api.models import CompressionJob
from sigmavault_desktop.views.agents_view import AgentsView
from sigmavault_desktop.views.dashboard_view import DashboardView
from sigmavault_desktop.views.job_detail_view import JobDetailView
from sigmavault_desktop.views.jobs_view import JobsListView
from sigmavault_desktop.views.storage_view import StorageView
from sigmavault_desktop.views.system_settings_view import SystemSettingsView

logger = logging.getLogger(__name__)


class MainWindow(Adwaita.ApplicationWindow):
    """Main application window with ViewStack navigation.

    Architecture:
        ┌───────────────────────────────────────────────┐
        │  HeaderBar                                    │
        │  [Menu ☰]  [ViewSwitcher: Dashboard | Jobs]  │
        │            [Refresh 🔄]                       │
        ├───────────────────────────────────────────────┤
        │  ViewStack                                    │
        │  ┌─ dashboard ──────────────────────────────┐ │
        │  │  DashboardView (stats + recent jobs)     │ │
        │  └──────────────────────────────────────────┘ │
        │  ┌─ jobs ───────────────────────────────────┐ │
        │  │  NavigationView                          │ │
        │  │  ├─ JobsListView (filterable list)       │ │
        │  │  └─ JobDetailView (pushed on click)      │ │
        │  └──────────────────────────────────────────┘ │
        └───────────────────────────────────────────────┘
    """

    def __init__(
        self,
        application: "Adwaita.Application",
        api_client: Optional[SigmaVaultAPIClient] = None,
    ):
        """Initialize main window.

        Args:
            application: The Adwaita application
            api_client: Shared API client (creates default if None)
        """
        super().__init__(application=application)

        # API client (shared across views)
        self._api_client = api_client or SigmaVaultAPIClient()

        # Set window properties
        self.set_title("SigmaVault")
        self.set_default_size(1200, 800)
        self.set_icon_name("drive-multidisk-symbolic")

        # Build the full UI
        self._build_ui()

        # Start auto-refresh on visible views
        self._dashboard_view.start_auto_refresh()

        # Connect close signal
        self.connect("close-request", self._on_close)

    def _build_ui(self) -> None:
        """Build the main window UI structure."""
        # ── Top-level ToolbarView ────────────────────────────────
        toolbar_view = Adwaita.ToolbarView()

        # ── Header Bar ───────────────────────────────────────────
        header_bar = Adwaita.HeaderBar()

        # View switcher (center of header)
        self._view_stack = Adwaita.ViewStack()
        view_switcher = Adwaita.ViewSwitcher()
        view_switcher.set_stack(self._view_stack)
        view_switcher.set_policy(Adwaita.ViewSwitcherPolicy.WIDE)
        header_bar.set_title_widget(view_switcher)

        # Refresh button (end of header)
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh all data (Ctrl+R)")
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        header_bar.pack_end(refresh_btn)

        # Menu button (end of header)
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_tooltip_text("Main menu")

        # Build menu model
        menu = Gio.Menu()
        menu.append("About SigmaVault", "app.about")
        menu.append("Keyboard Shortcuts", "win.show-help-overlay")
        menu.append("Quit", "app.quit")
        menu_btn.set_menu_model(menu)
        header_bar.pack_end(menu_btn)

        toolbar_view.add_top_bar(header_bar)

        # ── Build Views ──────────────────────────────────────────

        # Dashboard view
        self._dashboard_view = DashboardView(self._api_client)
        self._view_stack.add_titled_with_icon(
            self._dashboard_view,
            "dashboard",
            "Dashboard",
            "user-home-symbolic",
        )

        # Jobs view (wrapped in NavigationView for drill-down)
        self._jobs_nav = Adwaita.NavigationView()

        self._jobs_list_view = JobsListView(
            api_client=self._api_client,
            on_job_selected=self._on_job_selected,
        )
        self._jobs_nav.push(self._jobs_list_view)

        self._view_stack.add_titled_with_icon(
            self._jobs_nav,
            "jobs",
            "Jobs",
            "view-list-symbolic",
        )

        # Storage view (disks, pools, datasets, shares)
        self._storage_view = StorageView(self._api_client)
        self._view_stack.add_titled_with_icon(
            self._storage_view,
            "storage",
            "Storage",
            "drive-multidisk-symbolic",
        )

        # Agents view (Elite Agent Collective monitoring)
        self._agents_view = AgentsView(self._api_client)
        self._view_stack.add_titled_with_icon(
            self._agents_view,
            "agents",
            "Agents",
            "system-run-symbolic",
        )

        # System Settings view (network, services, notifications)
        self._system_view = SystemSettingsView(self._api_client)
        self._view_stack.add_titled_with_icon(
            self._system_view,
            "settings",
            "Settings",
            "preferences-system-symbolic",
        )

        # Listen for view changes to manage auto-refresh
        self._view_stack.connect("notify::visible-child-name", self._on_view_changed)

        # ── Bottom: ViewSwitcherBar for narrow widths ────────────
        view_switcher_bar = Adwaita.ViewSwitcherBar()
        view_switcher_bar.set_stack(self._view_stack)
        toolbar_view.add_bottom_bar(view_switcher_bar)

        # Connect breakpoint for responsive layout
        # When window is narrow, hide top switcher and show bottom bar
        breakpoint_ = Adwaita.Breakpoint()
        breakpoint_.set_condition(Adwaita.BreakpointCondition.parse("max-width: 550sp"))
        breakpoint_.add_setter(view_switcher, "visible", False)
        breakpoint_.add_setter(view_switcher_bar, "reveal", True)
        self.add_breakpoint(breakpoint_)

        # ── Keyboard shortcuts ───────────────────────────────────
        self._setup_shortcuts(application=self.get_application())

        self.set_content(toolbar_view)

    def _setup_shortcuts(self, application) -> None:
        """Register keyboard shortcuts.

        Args:
            application: The GtkApplication to register accels on
        """
        # Ctrl+R → Refresh
        refresh_action = Gio.SimpleAction.new("refresh", None)
        refresh_action.connect("activate", lambda *_: self._on_refresh_clicked(None))
        self.add_action(refresh_action)
        if application:
            application.set_accels_for_action("win.refresh", ["<Control>r"])

    # ── Signal Handlers ──────────────────────────────────────────

    def _on_refresh_clicked(self, _button) -> None:
        """Handle refresh button click."""
        logger.debug("Manual refresh triggered")
        self._dashboard_view.refresh()
        self._jobs_list_view.refresh()
        self._storage_view.start_refresh()
        self._agents_view.start_refresh()
        self._system_view.start_refresh()

    def _on_view_changed(self, stack: Adwaita.ViewStack, _pspec) -> None:
        """Handle view stack page change.

        Start/stop auto-refresh based on which view is visible.
        """
        visible = stack.get_visible_child_name()
        logger.debug(f"View changed to: {visible}")

        # Stop all auto-refresh timers
        self._dashboard_view.stop_auto_refresh()
        self._jobs_list_view.stop_auto_refresh()
        self._storage_view.stop_refresh()
        self._agents_view.stop_refresh()
        self._system_view.stop_refresh()

        # Start auto-refresh for the visible view
        if visible == "dashboard":
            self._dashboard_view.start_auto_refresh()
        elif visible == "jobs":
            self._jobs_list_view.start_auto_refresh()
        elif visible == "storage":
            self._storage_view.start_refresh()
        elif visible == "agents":
            self._agents_view.start_refresh()
        elif visible == "settings":
            self._system_view.start_refresh()

    def _on_job_selected(self, job: CompressionJob) -> None:
        """Handle job selection from jobs list - push detail view.

        Args:
            job: The selected compression job
        """
        logger.info(f"Navigating to job detail: {job.job_id}")
        detail_view = JobDetailView(job)
        self._jobs_nav.push(detail_view)

    def _on_close(self, _widget) -> bool:
        """Handle window close - cleanup timers.

        Returns:
            False to allow the close
        """
        logger.info("Closing main window - stopping auto-refresh")
        self._dashboard_view.stop_auto_refresh()
        self._jobs_list_view.stop_auto_refresh()
        self._storage_view.stop_refresh()
        self._agents_view.stop_refresh()
        self._system_view.stop_refresh()
        return False
