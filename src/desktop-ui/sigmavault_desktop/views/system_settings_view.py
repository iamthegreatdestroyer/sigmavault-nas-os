"""System settings and management view.

Displays system configuration and provides management controls:
- Network interfaces with IP addresses and traffic stats
- System services with status and controls
- Notifications with filtering
- System actions (reboot, shutdown)
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Gtk, Adwaita, GLib

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.utils.formatting import format_bytes
from sigmavault_desktop.utils.async_helpers import run_async, schedule_repeated

logger = logging.getLogger(__name__)


class SystemSettingsView(Gtk.Box):
    """Main system settings view with tabbed interface."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize system settings view.

        Args:
            api_client: API client instance
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._api_client = api_client
        self._refresh_timer_id: Optional[int] = None

        # Tab view for different settings sections
        self._tab_view = Adwaita.TabView()
        self._tab_bar = Adwaita.TabBar(view=self._tab_view)

        self.append(self._tab_bar)
        self.append(self._tab_view)

        # Create pages for each section
        self._network_page = NetworkPage(api_client)
        self._services_page = ServicesPage(api_client)
        self._notifications_page = NotificationsPage(api_client)
        self._system_page = SystemActionsPage(api_client)

        # Add tabs
        self._tab_view.append(self._network_page).set_title("Network")
        self._tab_view.append(self._services_page).set_title("Services")
        self._tab_view.append(self._notifications_page).set_title("Notifications")
        self._tab_view.append(self._system_page).set_title("System")

        # Start auto-refresh
        self.start_refresh()

    def start_refresh(self) -> None:
        """Start auto-refresh timer (10s interval for system settings)."""
        if self._refresh_timer_id:
            return
        self._refresh_timer_id = schedule_repeated(10000, self._refresh_all)
        self._refresh_all()

    def stop_refresh(self) -> None:
        """Stop auto-refresh timer."""
        if self._refresh_timer_id:
            GLib.Source.remove(self._refresh_timer_id)
            self._refresh_timer_id = None

    def _refresh_all(self) -> None:
        """Refresh all tabs (except system actions which are manual)."""
        self._network_page.refresh()
        self._services_page.refresh()
        self._notifications_page.refresh()


# ─── Network Page ────────────────────────────────────────────────


class NetworkPage(Adwaita.PreferencesPage):
    """Page showing network interface information."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize network page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        self._group = Adwaita.PreferencesGroup(title="Network Interfaces")
        self.add(self._group)

        self._spinner = Gtk.Spinner(spinning=False)
        self._group.add(self._spinner)

    def refresh(self) -> None:
        """Fetch and display network interfaces."""
        self._spinner.set_spinning(True)
        run_async(self._fetch_interfaces)

    async def _fetch_interfaces(self) -> None:
        """Fetch network interface data from API."""
        try:
            interfaces = await self._api_client.get_network_interfaces()
            self._update_ui(interfaces)
        except Exception as e:
            logger.error(f"Failed to fetch network interfaces: {e}")
        finally:
            self._spinner.set_spinning(False)

    def _update_ui(self, interfaces) -> None:
        """Update UI with network interface data.

        Args:
            interfaces: List of NetworkInterface objects
        """
        while child := self._group.get_first_child():
            if child != self._spinner:
                self._group.remove(child)
            else:
                break

        for iface in interfaces:
            status_icon = "🔗" if iface.status == "up" else "⊗"

            row = Adwaita.ExpanderRow(
                title=f"{status_icon} {iface.name}",
                subtitle=f"{iface.address}/{iface.netmask}",
            )

            # Status badge
            status_class = "success" if iface.status == "up" else "dim-label"
            status_badge = Gtk.Label(label=iface.status.upper())
            status_badge.add_css_class(status_class)
            status_badge.add_css_class("caption")
            row.add_suffix(status_badge)

            # Add detail rows
            mac_row = Adwaita.ActionRow(
                title="MAC Address",
                subtitle=iface.mac_address,
            )
            row.add_row(mac_row)

            mtu_row = Adwaita.ActionRow(
                title="MTU",
                subtitle=str(iface.mtu),
            )
            row.add_row(mtu_row)

            traffic_row = Adwaita.ActionRow(
                title="Traffic",
                subtitle=f"RX: {format_bytes(iface.rx_bytes)} • TX: {format_bytes(iface.tx_bytes)}",
            )
            row.add_row(traffic_row)

            self._group.add(row)


# ─── Services Page ───────────────────────────────────────────────


class ServicesPage(Adwaita.PreferencesPage):
    """Page showing system service status."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize services page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        self._group = Adwaita.PreferencesGroup(title="System Services")
        self.add(self._group)

        self._spinner = Gtk.Spinner(spinning=False)
        self._group.add(self._spinner)

    def refresh(self) -> None:
        """Fetch and display service information."""
        self._spinner.set_spinning(True)
        run_async(self._fetch_services)

    async def _fetch_services(self) -> None:
        """Fetch service data from API."""
        try:
            services = await self._api_client.get_services()
            self._update_ui(services)
        except Exception as e:
            logger.error(f"Failed to fetch services: {e}")
        finally:
            self._spinner.set_spinning(False)

    def _update_ui(self, services) -> None:
        """Update UI with service data.

        Args:
            services: List of SystemService objects
        """
        while child := self._group.get_first_child():
            if child != self._spinner:
                self._group.remove(child)
            else:
                break

        for service in services:
            # Status icon
            status_icons = {
                "running": "▶",
                "stopped": "⏸",
                "failed": "✗",
            }
            status_icon = status_icons.get(service.status, "?")

            # Uptime formatting
            uptime_str = (
                f"{service.uptime_seconds // 3600}h {(service.uptime_seconds % 3600) // 60}m"
                if service.uptime_seconds
                else "—"
            )

            row = Adwaita.ActionRow(
                title=f"{status_icon} {service.name}",
                subtitle=f"{service.description or 'System service'} • Uptime: {uptime_str}",
            )

            # Status badge
            status_class = {
                "running": "success",
                "stopped": "warning",
                "failed": "error",
            }.get(service.status, "dim-label")

            status_badge = Gtk.Label(label=service.status.upper())
            status_badge.add_css_class(status_class)
            status_badge.add_css_class("caption")
            row.add_suffix(status_badge)

            self._group.add(row)


# ─── Notifications Page ──────────────────────────────────────────


class NotificationsPage(Adwaita.PreferencesPage):
    """Page showing system notifications."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize notifications page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        # Filter controls
        filter_group = Adwaita.PreferencesGroup(title="Filters")
        self.add(filter_group)

        filter_row = Adwaita.ActionRow(title="Show unread only")
        self._unread_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self._unread_switch.connect("notify::active", self._on_filter_changed)
        filter_row.add_suffix(self._unread_switch)
        filter_group.add(filter_row)

        # Notifications list
        self._group = Adwaita.PreferencesGroup(title="Notifications")
        self.add(self._group)

        self._spinner = Gtk.Spinner(spinning=False)
        self._group.add(self._spinner)

    def _on_filter_changed(self, *args) -> None:
        """Handle filter change."""
        self.refresh()

    def refresh(self) -> None:
        """Fetch and display notifications."""
        self._spinner.set_spinning(True)
        run_async(self._fetch_notifications)

    async def _fetch_notifications(self) -> None:
        """Fetch notification data from API."""
        try:
            unread_only = self._unread_switch.get_active()
            notifications = await self._api_client.get_notifications(unread_only=unread_only)
            self._update_ui(notifications)
        except Exception as e:
            logger.error(f"Failed to fetch notifications: {e}")
        finally:
            self._spinner.set_spinning(False)

    def _update_ui(self, notifications) -> None:
        """Update UI with notification data.

        Args:
            notifications: List of SystemNotification objects
        """
        while child := self._group.get_first_child():
            if child != self._spinner:
                self._group.remove(child)
            else:
                break

        if not notifications:
            empty_label = Gtk.Label(label="No notifications")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self._group.add(empty_label)
            return

        for notif in notifications:
            # Level icon
            level_icons = {
                "info": "ℹ",
                "warning": "⚠",
                "error": "✗",
                "critical": "🔥",
            }
            level_icon = level_icons.get(notif.level, "•")

            read_status = "" if notif.read else "🔵 "

            row = Adwaita.ActionRow(
                title=f"{read_status}{level_icon} {notif.message}",
                subtitle=f"{notif.source} • {notif.timestamp}",
            )

            # Level badge
            level_class = {
                "info": "success",
                "warning": "warning",
                "error": "error",
                "critical": "error",
            }.get(notif.level, "dim-label")

            level_badge = Gtk.Label(label=notif.level.upper())
            level_badge.add_css_class(level_class)
            level_badge.add_css_class("caption")
            row.add_suffix(level_badge)

            self._group.add(row)


# ─── System Actions Page ─────────────────────────────────────────


class SystemActionsPage(Adwaita.PreferencesPage):
    """Page with system actions (reboot, shutdown)."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize system actions page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        # Warning banner
        banner_group = Adwaita.PreferencesGroup()
        self.add(banner_group)

        warning_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
        )
        warning_box.set_margin_top(12)
        warning_box.set_margin_bottom(12)
        warning_box.set_margin_start(12)
        warning_box.set_margin_end(12)
        warning_box.add_css_class("card")
        warning_box.add_css_class("warning")

        warning_label = Gtk.Label(
            label="⚠ System Actions",
            xalign=0,
        )
        warning_label.add_css_class("title-3")
        warning_box.append(warning_label)

        warning_desc = Gtk.Label(
            label="These actions will affect the entire system. Active jobs and connections will be interrupted.",
            xalign=0,
            wrap=True,
        )
        warning_desc.add_css_class("dim-label")
        warning_box.append(warning_desc)

        banner_group.add(warning_box)

        # Actions group
        actions_group = Adwaita.PreferencesGroup(title="System Control")
        self.add(actions_group)

        # Reboot action
        reboot_row = Adwaita.ActionRow(
            title="Reboot System",
            subtitle="Restart the system (requires confirmation)",
        )
        reboot_button = Gtk.Button(label="Reboot", valign=Gtk.Align.CENTER)
        reboot_button.add_css_class("suggested-action")
        reboot_button.connect("clicked", self._on_reboot_clicked)
        reboot_row.add_suffix(reboot_button)
        actions_group.add(reboot_row)

        # Shutdown action
        shutdown_row = Adwaita.ActionRow(
            title="Shutdown System",
            subtitle="Power off the system (requires confirmation)",
        )
        shutdown_button = Gtk.Button(label="Shutdown", valign=Gtk.Align.CENTER)
        shutdown_button.add_css_class("destructive-action")
        shutdown_button.connect("clicked", self._on_shutdown_clicked)
        shutdown_row.add_suffix(shutdown_button)
        actions_group.add(shutdown_row)

    def _on_reboot_clicked(self, button: Gtk.Button) -> None:
        """Handle reboot button click."""
        dialog = Adwaita.MessageDialog.new(
            self.get_root(),
            "Confirm Reboot",
            "Are you sure you want to reboot the system?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reboot", "Reboot")
        dialog.set_response_appearance("reboot", Adwaita.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_reboot_response)
        dialog.present()

    def _on_reboot_response(self, dialog: Adwaita.MessageDialog, response: str) -> None:
        """Handle reboot confirmation response."""
        if response == "reboot":
            run_async(self._do_reboot)

    async def _do_reboot(self) -> None:
        """Execute reboot command."""
        try:
            success = await self._api_client.reboot_system()
            if success:
                logger.info("Reboot command sent successfully")
            else:
                logger.error("Reboot command failed")
        except Exception as e:
            logger.error(f"Failed to reboot system: {e}")

    def _on_shutdown_clicked(self, button: Gtk.Button) -> None:
        """Handle shutdown button click."""
        dialog = Adwaita.MessageDialog.new(
            self.get_root(),
            "Confirm Shutdown",
            "Are you sure you want to shut down the system?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("shutdown", "Shutdown")
        dialog.set_response_appearance("shutdown", Adwaita.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_shutdown_response)
        dialog.present()

    def _on_shutdown_response(self, dialog: Adwaita.MessageDialog, response: str) -> None:
        """Handle shutdown confirmation response."""
        if response == "shutdown":
            run_async(self._do_shutdown)

    async def _do_shutdown(self) -> None:
        """Execute shutdown command."""
        try:
            success = await self._api_client.shutdown_system()
            if success:
                logger.info("Shutdown command sent successfully")
            else:
                logger.error("Shutdown command failed")
        except Exception as e:
            logger.error(f"Failed to shutdown system: {e}")
