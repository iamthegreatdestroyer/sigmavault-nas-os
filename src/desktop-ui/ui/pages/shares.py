"""
Shares Page — SMB/NFS share management.
"""

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib  # noqa: E402


class SharesPage(Gtk.Box):
    """Network share management (SMB/NFS)."""

    def __init__(self, api: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._api = api
        self._build_ui()
        GLib.idle_add(self._refresh_shares)

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(scrolled)

        clamp = Adw.Clamp(
            maximum_size=800, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16
        )
        scrolled.set_child(clamp)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_btn = Gtk.Button(
            label="Add Share", icon_name="list-add-symbolic", css_classes=["suggested-action"]
        )
        add_btn.connect("clicked", self._on_add_share)
        refresh_btn = Gtk.Button(label="Refresh", icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda _: self._refresh_shares())
        toolbar.append(add_btn)
        toolbar.append(refresh_btn)
        content.append(toolbar)

        # SMB shares
        self._smb_group = Adw.PreferencesGroup(
            title="SMB Shares",
            description="Samba file shares accessible via Windows/macOS/Linux",
        )
        content.append(self._smb_group)

        self._smb_placeholder = Adw.ActionRow(
            title="No SMB shares configured",
            subtitle="Add a share to make files accessible over the network",
            icon_name="folder-remote-symbolic",
        )
        self._smb_group.add(self._smb_placeholder)

        # NFS shares
        self._nfs_group = Adw.PreferencesGroup(
            title="NFS Exports",
            description="NFS exports for Linux/Unix clients",
        )
        content.append(self._nfs_group)

        self._nfs_placeholder = Adw.ActionRow(
            title="No NFS exports configured",
            subtitle="Configure NFS exports for Linux clients",
            icon_name="folder-remote-symbolic",
        )
        self._nfs_group.add(self._nfs_placeholder)

    def _refresh_shares(self) -> bool:
        """Fetch shares from API."""
        try:
            shares = self._api.get_shares()
            if shares:
                for share in shares:
                    stype = share.get("type", "smb")
                    group = self._smb_group if stype == "smb" else self._nfs_group
                    row = Adw.ActionRow(
                        title=share.get("name", "Unknown"),
                        subtitle=share.get("path", "—"),
                        icon_name="folder-remote-symbolic",
                    )
                    group.add(row)
        except Exception:
            pass
        return False

    def _on_add_share(self, _button: Gtk.Button) -> None:
        """Open share creation dialog."""
        dialog = Adw.AlertDialog(
            heading="Create Network Share",
            body="Share creation wizard is under development.\n\nUse samba configuration for now.",
        )
        dialog.add_response("close", "Close")
        dialog.present(self.get_root())
