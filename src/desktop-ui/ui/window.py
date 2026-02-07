"""
SigmaVault Settings — Main Application Window

Uses Adw.NavigationSplitView for sidebar + content layout.
Sidebar lists pages; content area hosts the active page.
"""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib, Gio  # noqa: E402

from ui.pages.dashboard import DashboardPage
from ui.pages.storage import StoragePage
from ui.pages.compression import CompressionPage
from ui.pages.agents import AgentsPage
from ui.pages.shares import SharesPage
from ui.pages.network import NetworkPage
from ui.pages.settings import SettingsPage
from ui.widgets.status_indicator import StatusIndicator
from api.client import SigmaVaultAPIClient

logger = logging.getLogger("sigmavault.window")


# Page definition: (id, label, icon_name)
PAGES = [
    ("dashboard", "Dashboard", "view-dashboard-symbolic"),
    ("storage", "Storage", "drive-harddisk-symbolic"),
    ("compression", "Compression", "package-x-generic-symbolic"),
    ("agents", "Agents", "system-run-symbolic"),
    ("shares", "Shares", "folder-remote-symbolic"),
    ("network", "Network", "network-server-symbolic"),
    ("settings", "Settings", "preferences-system-symbolic"),
]


class SigmaVaultWindow(Adw.ApplicationWindow):
    """Main application window with sidebar navigation."""

    def __init__(self, **kwargs) -> None:
        super().__init__(
            default_width=1100,
            default_height=700,
            title="SigmaVault Settings",
            **kwargs,
        )

        # API client (shared by all pages)
        self._api = SigmaVaultAPIClient()

        # Page instances (lazy-loaded on first navigation)
        self._page_widgets: dict[str, Gtk.Widget] = {}

        self._build_ui()
        self._setup_status_polling()

        # Navigate to dashboard by default
        self.navigate_to("dashboard")

    # ─── UI Construction ────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construct the full window layout."""
        # Main layout: header bar + content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header bar with menu
        header = Adw.HeaderBar()
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_button.set_menu_model(self._build_app_menu())
        header.pack_end(menu_button)
        main_box.append(header)

        # Navigation split view: sidebar + content
        self._split_view = Adw.NavigationSplitView()
        main_box.append(self._split_view)

        # ── Sidebar ──────────────────────────────────────────────
        sidebar_page = Adw.NavigationPage(title="SigmaVault")
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_page.set_child(sidebar_box)

        # Sidebar list
        self._sidebar_list = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.SINGLE,
            css_classes=["navigation-sidebar"],
        )
        self._sidebar_list.connect("row-selected", self._on_sidebar_row_selected)

        for page_id, label, icon_name in PAGES:
            row = Gtk.ListBoxRow()
            row.page_id = page_id  # type: ignore[attr-defined]
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            icon = Gtk.Image(icon_name=icon_name)
            lbl = Gtk.Label(label=label, xalign=0, hexpand=True)
            hbox.append(icon)
            hbox.append(lbl)
            row.set_child(hbox)
            self._sidebar_list.append(row)

        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vexpand=True,
        )
        scrolled.set_child(self._sidebar_list)
        sidebar_box.append(scrolled)

        self._split_view.set_sidebar(sidebar_page)

        # ── Content area ────────────────────────────────────────
        self._content_page = Adw.NavigationPage(title="Dashboard")
        self._content_stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=200,
        )
        self._content_page.set_child(self._content_stack)
        self._split_view.set_content(self._content_page)

        # ── Status bar at the bottom ────────────────────────────
        self._status_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=16,
            css_classes=["toolbar"],
        )
        self._status_bar.set_margin_start(12)
        self._status_bar.set_margin_end(12)
        self._status_bar.set_margin_top(4)
        self._status_bar.set_margin_bottom(4)

        self._api_indicator = StatusIndicator(label="API", status="unknown")
        self._engine_indicator = StatusIndicator(label="Engine", status="unknown")
        self._agent_label = Gtk.Label(label="— agents", css_classes=["dim-label"])

        self._status_bar.append(self._api_indicator)
        self._status_bar.append(self._engine_indicator)
        spacer = Gtk.Box(hexpand=True)
        self._status_bar.append(spacer)
        self._status_bar.append(self._agent_label)

        main_box.append(Gtk.Separator())
        main_box.append(self._status_bar)

    def _build_app_menu(self) -> Gio.Menu:
        """Build the hamburger menu model."""
        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("About SigmaVault", "app.about")
        menu.append("Quit", "app.quit")
        return menu

    # ─── Navigation ─────────────────────────────────────────────

    def navigate_to(self, page_id: str) -> None:
        """Switch the content area to the given page."""
        # Ensure the page widget exists
        if page_id not in self._page_widgets:
            self._page_widgets[page_id] = self._create_page(page_id)
            self._content_stack.add_named(self._page_widgets[page_id], page_id)

        self._content_stack.set_visible_child_name(page_id)

        # Update title
        for pid, label, _ in PAGES:
            if pid == page_id:
                self._content_page.set_title(label)
                break

        # Select the correct sidebar row (without re-triggering signal)
        for i, (pid, _, _) in enumerate(PAGES):
            if pid == page_id:
                row = self._sidebar_list.get_row_at_index(i)
                if row and self._sidebar_list.get_selected_row() != row:
                    self._sidebar_list.select_row(row)
                break

        logger.info("Navigated to page: %s", page_id)

    def _on_sidebar_row_selected(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if row is not None:
            self.navigate_to(row.page_id)  # type: ignore[attr-defined]

    def _create_page(self, page_id: str) -> Gtk.Widget:
        """Instantiate the page widget for the given ID."""
        page_map = {
            "dashboard": lambda: DashboardPage(api=self._api),
            "storage": lambda: StoragePage(api=self._api),
            "compression": lambda: CompressionPage(api=self._api),
            "agents": lambda: AgentsPage(api=self._api),
            "shares": lambda: SharesPage(api=self._api),
            "network": lambda: NetworkPage(api=self._api),
            "settings": lambda: SettingsPage(api=self._api),
        }
        factory = page_map.get(page_id)
        if factory:
            return factory()
        # Fallback: empty placeholder
        return Adw.StatusPage(
            title=page_id.title(),
            description="This page is under construction.",
            icon_name="dialog-information-symbolic",
        )

    # ─── Status Polling ─────────────────────────────────────────

    def _setup_status_polling(self) -> None:
        """Poll API health every 5 seconds to update status bar."""
        GLib.timeout_add_seconds(5, self._poll_status)
        # Also poll immediately
        GLib.idle_add(self._poll_status)

    def _poll_status(self) -> bool:
        """Fetch health from Go API and update indicators."""
        try:
            health = self._api.get_health()
            if health:
                self._api_indicator.set_status("online")
                engine_status = health.get("engine", "unknown")
                self._engine_indicator.set_status(
                    "online" if engine_status == "connected" else "offline"
                )
                agent_count = health.get("agents", {}).get("total", 0)
                idle_count = health.get("agents", {}).get("idle", agent_count)
                busy_count = agent_count - idle_count
                if busy_count > 0:
                    self._agent_label.set_text(
                        f"{agent_count} agents ({busy_count} busy)"
                    )
                else:
                    self._agent_label.set_text(f"{agent_count} agents idle")
            else:
                self._api_indicator.set_status("offline")
                self._engine_indicator.set_status("unknown")
                self._agent_label.set_text("— agents")
        except Exception:
            self._api_indicator.set_status("offline")
            self._engine_indicator.set_status("unknown")
            self._agent_label.set_text("— agents")

        return True  # Keep polling
