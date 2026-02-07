"""
Network Page — VPN status, WireGuard configuration, peer management.
"""

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402


class NetworkPage(Gtk.Box):
    """VPN management: WireGuard status, peers, config generation."""

    def __init__(self, api: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._api = api
        self._build_ui()

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(scrolled)

        clamp = Adw.Clamp(maximum_size=800, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        scrolled.set_child(clamp)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)

        # VPN status
        vpn_group = Adw.PreferencesGroup(
            title="WireGuard VPN",
            description="Secure remote access to your NAS",
        )
        content.append(vpn_group)

        self._vpn_toggle = Adw.SwitchRow(
            title="VPN Server",
            subtitle="Enable WireGuard VPN server",
            icon_name="network-vpn-symbolic",
        )
        self._vpn_toggle.connect("notify::active", self._on_vpn_toggled)
        vpn_group.add(self._vpn_toggle)

        self._vpn_status_row = Adw.ActionRow(
            title="Status",
            subtitle="Not configured",
            icon_name="network-offline-symbolic",
        )
        vpn_group.add(self._vpn_status_row)

        # Peers
        peers_group = Adw.PreferencesGroup(
            title="Connected Peers",
            description="Devices connected via WireGuard",
        )
        content.append(peers_group)

        add_peer_btn = Gtk.Button(label="Add Peer", icon_name="list-add-symbolic", css_classes=["suggested-action"])
        add_peer_btn.connect("clicked", self._on_add_peer)

        self._no_peers_row = Adw.ActionRow(
            title="No peers configured",
            subtitle="Add a peer to enable remote access",
            icon_name="network-server-symbolic",
        )
        peers_group.add(self._no_peers_row)

        # Traffic stats
        stats_group = Adw.PreferencesGroup(title="Traffic Statistics")
        content.append(stats_group)

        self._rx_row = Adw.ActionRow(
            title="Received", subtitle="—", icon_name="go-down-symbolic"
        )
        stats_group.add(self._rx_row)

        self._tx_row = Adw.ActionRow(
            title="Transmitted", subtitle="—", icon_name="go-up-symbolic"
        )
        stats_group.add(self._tx_row)

        # Phase 6 notice
        notice = Adw.StatusPage(
            title="Coming in Phase 6",
            description="Full VPN management with QR code peer configuration\nwill be implemented in the VPN & Remote Access phase.",
            icon_name="network-vpn-symbolic",
        )
        notice.set_vexpand(False)
        content.append(notice)

    def _on_vpn_toggled(self, row: Adw.SwitchRow, _param) -> None:
        """Toggle VPN server."""
        active = row.get_active()
        self._vpn_status_row.set_subtitle("Active" if active else "Inactive")
        self._vpn_status_row.set_icon_name(
            "network-vpn-symbolic" if active else "network-offline-symbolic"
        )

    def _on_add_peer(self, _button: Gtk.Button) -> None:
        """Add VPN peer dialog."""
        dialog = Adw.AlertDialog(
            heading="Add VPN Peer",
            body="Peer configuration with QR code generation\nwill be available in Phase 6.",
        )
        dialog.add_response("close", "Close")
        dialog.present(self.get_root())
