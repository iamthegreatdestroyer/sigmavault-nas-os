"""
Settings Page — Application preferences, service control, about.
"""

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import logging
import subprocess

from gi.repository import Adw, Gtk  # noqa: E402

logger = logging.getLogger("sigmavault.settings")


class SettingsPage(Gtk.Box):
    """App preferences: API endpoint, notification settings, service control."""

    def __init__(self, api: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._api = api
        self._build_ui()

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(scrolled)

        clamp = Adw.Clamp(
            maximum_size=800, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16
        )
        scrolled.set_child(clamp)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)

        # ── API Connection ──
        api_group = Adw.PreferencesGroup(
            title="API Connection",
            description="Configure the Go API server connection",
        )
        content.append(api_group)

        self._api_url_row = Adw.EntryRow(
            title="API URL",
            text="http://localhost:12080",
        )
        api_group.add(self._api_url_row)

        self._ws_url_row = Adw.EntryRow(
            title="WebSocket URL",
            text="ws://localhost:12080/ws",
        )
        api_group.add(self._ws_url_row)

        test_btn_row = Adw.ActionRow(
            title="Test Connection",
            subtitle="Verify API server is reachable",
            activatable=True,
        )
        test_btn_row.connect("activated", self._on_test_connection)
        test_btn_row.add_suffix(Gtk.Image(icon_name="network-transmit-receive-symbolic"))
        api_group.add(test_btn_row)

        # ── Compression Defaults ──
        compress_group = Adw.PreferencesGroup(
            title="Compression Defaults",
            description="Default settings for compression jobs",
        )
        content.append(compress_group)

        default_algo = Adw.ComboRow(title="Default Algorithm")
        default_algo.set_model(Gtk.StringList.new(["Auto", "zstd", "zlib", "lz4", "brotli"]))
        default_algo.set_selected(0)
        compress_group.add(default_algo)

        default_level = Adw.SpinRow.new_with_range(1, 22, 1)
        default_level.set_title("Default Level")
        default_level.set_value(6)
        compress_group.add(default_level)

        # ── Notifications ──
        notif_group = Adw.PreferencesGroup(
            title="Notifications",
            description="Configure desktop notifications for SigmaVault events",
        )
        content.append(notif_group)

        self._notif_compression = Adw.SwitchRow(
            title="Compression Complete",
            subtitle="Notify when a compression job finishes",
            active=True,
        )
        notif_group.add(self._notif_compression)

        self._notif_agent = Adw.SwitchRow(
            title="Agent Task Complete",
            subtitle="Notify when an agent finishes a task",
            active=True,
        )
        notif_group.add(self._notif_agent)

        self._notif_disk = Adw.SwitchRow(
            title="Disk Health Warnings",
            subtitle="Notify on SMART health warnings",
            active=True,
        )
        notif_group.add(self._notif_disk)

        # ── Service Control ──
        service_group = Adw.PreferencesGroup(
            title="Service Control",
            description="Manage SigmaVault background services",
        )
        content.append(service_group)

        api_service = Adw.ActionRow(
            title="sigmavault-api.service",
            subtitle="Go API Server",
            icon_name="network-server-symbolic",
            activatable=True,
        )
        api_restart_btn = Gtk.Button(
            label="Restart", valign=Gtk.Align.CENTER, css_classes=["destructive-action"]
        )
        api_restart_btn.connect("clicked", lambda _: self._restart_service("sigmavault-api"))
        api_service.add_suffix(api_restart_btn)
        service_group.add(api_service)

        engine_service = Adw.ActionRow(
            title="sigmavault-engine.service",
            subtitle="Python RPC Engine",
            icon_name="system-run-symbolic",
            activatable=True,
        )
        engine_restart_btn = Gtk.Button(
            label="Restart", valign=Gtk.Align.CENTER, css_classes=["destructive-action"]
        )
        engine_restart_btn.connect("clicked", lambda _: self._restart_service("sigmavault-engine"))
        engine_service.add_suffix(engine_restart_btn)
        service_group.add(engine_service)

    def _on_test_connection(self, _row: Adw.ActionRow) -> None:
        """Test API connection."""
        health = self._api.get_health()
        dialog = Adw.AlertDialog(
            heading="Connection Test",
            body="✅ API server is reachable!" if health else "❌ API server is not reachable.",
        )
        dialog.add_response("close", "Close")
        dialog.present(self.get_root())

    def _restart_service(self, service_name: str) -> None:
        """Restart a systemd service (requires polkit authorization)."""
        try:
            subprocess.run(
                ["systemctl", "restart", service_name],
                check=True,
                timeout=10,
            )
            logger.info("Restarted service: %s", service_name)
        except Exception as e:
            logger.error("Failed to restart %s: %s", service_name, e)
            dialog = Adw.AlertDialog(
                heading="Service Restart Failed",
                body=f"Could not restart {service_name}.\n\n{e}",
            )
            dialog.add_response("close", "Close")
            dialog.present(self.get_root())
