"""
Storage Page — ZFS pool management, disk inventory, datasets, shares.
"""

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib  # noqa: E402


class StoragePage(Gtk.Box):
    """ZFS pool/dataset management and disk health monitoring."""

    def __init__(self, api: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._api = api
        self._build_ui()
        GLib.idle_add(self._refresh_data)

    def _build_ui(self) -> None:
        # Tab-style view switcher: Disks | Pools | Datasets | Shares
        self._view_stack = Adw.ViewStack()

        # Disks tab
        self._disks_page = self._build_disks_tab()
        self._view_stack.add_titled_with_icon(
            self._disks_page, "disks", "Disks", "drive-harddisk-symbolic"
        )

        # Pools tab
        self._pools_page = self._build_pools_tab()
        self._view_stack.add_titled_with_icon(
            self._pools_page, "pools", "Pools", "drive-multidisk-symbolic"
        )

        # Datasets tab
        self._datasets_page = self._build_datasets_tab()
        self._view_stack.add_titled_with_icon(
            self._datasets_page, "datasets", "Datasets", "folder-symbolic"
        )

        # View switcher bar
        switcher = Adw.ViewSwitcherBar(stack=self._view_stack, reveal=True)

        self.append(self._view_stack)
        self.append(switcher)
        self._view_stack.set_vexpand(True)

    def _build_disks_tab(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp = Adw.Clamp(
            maximum_size=800, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16
        )
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)

        # Action toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        refresh_btn = Gtk.Button(label="Refresh", icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda _: self._refresh_data())
        gnome_disks_btn = Gtk.Button(label="Open GNOME Disks", icon_name="drive-harddisk-symbolic")
        gnome_disks_btn.connect("clicked", self._open_gnome_disks)
        toolbar.append(refresh_btn)
        toolbar.append(gnome_disks_btn)
        box.append(toolbar)

        self._disks_group = Adw.PreferencesGroup(
            title="Physical Disks",
            description="Detected storage devices with SMART health status",
        )
        box.append(self._disks_group)

        # Placeholder row
        self._disk_placeholder = Adw.ActionRow(
            title="Loading...",
            subtitle="Fetching disk inventory",
            icon_name="content-loading-symbolic",
        )
        self._disks_group.add(self._disk_placeholder)

        return scrolled

    def _build_pools_tab(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp = Adw.Clamp(
            maximum_size=800, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16
        )
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)

        # Action toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        create_btn = Gtk.Button(
            label="Create Pool", icon_name="list-add-symbolic", css_classes=["suggested-action"]
        )
        create_btn.connect("clicked", self._on_create_pool)
        refresh_btn = Gtk.Button(label="Refresh", icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda _: self._refresh_data())
        toolbar.append(create_btn)
        toolbar.append(refresh_btn)
        box.append(toolbar)

        self._pools_group = Adw.PreferencesGroup(
            title="ZFS Pools",
            description="Managed storage pools",
        )
        box.append(self._pools_group)

        self._pool_placeholder = Adw.ActionRow(
            title="No pools detected",
            subtitle="Create a pool to get started",
            icon_name="drive-multidisk-symbolic",
        )
        self._pools_group.add(self._pool_placeholder)

        return scrolled

    def _build_datasets_tab(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp = Adw.Clamp(
            maximum_size=800, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16
        )
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)

        self._datasets_group = Adw.PreferencesGroup(
            title="ZFS Datasets",
            description="Datasets within your pools",
        )
        box.append(self._datasets_group)

        self._dataset_placeholder = Adw.ActionRow(
            title="No datasets", subtitle="Create a pool first", icon_name="folder-symbolic"
        )
        self._datasets_group.add(self._dataset_placeholder)

        return scrolled

    def _refresh_data(self) -> bool:
        """Fetch disk and pool data from API."""
        try:
            disks = self._api.get_disks()
            if disks:
                # Clear old rows (except placeholder handled by replacing)
                self._disks_group.remove(self._disk_placeholder)
                for disk in disks:
                    row = Adw.ActionRow(
                        title=disk.get("name", "Unknown"),
                        subtitle=f"{disk.get('size', '?')} — {disk.get('health', 'unknown')}",
                        icon_name="drive-harddisk-symbolic",
                    )
                    self._disks_group.add(row)
        except Exception:
            pass

        try:
            pools = self._api.get_pools()
            if pools:
                self._pools_group.remove(self._pool_placeholder)
                for pool in pools:
                    row = Adw.ActionRow(
                        title=pool.get("name", "Unknown"),
                        subtitle=f"Health: {pool.get('health', '?')} — {pool.get('size', '?')}",
                        icon_name="drive-multidisk-symbolic",
                    )
                    # Add scrub button
                    scrub_btn = Gtk.Button(
                        icon_name="view-refresh-symbolic",
                        valign=Gtk.Align.CENTER,
                        tooltip_text="Start Scrub",
                    )
                    scrub_btn.connect("clicked", self._on_scrub_pool, pool.get("name"))
                    row.add_suffix(scrub_btn)
                    self._pools_group.add(row)
        except Exception:
            pass

        return False  # One-shot on idle

    def _on_create_pool(self, _button: Gtk.Button) -> None:
        """Open pool creation dialog (placeholder)."""
        dialog = Adw.AlertDialog(
            heading="Create ZFS Pool",
            body="Pool creation wizard is under development.\n\nUse the terminal for now:\n  sudo zpool create <name> <vdev>",
        )
        dialog.add_response("close", "Close")
        dialog.present(self.get_root())

    def _on_scrub_pool(self, _button: Gtk.Button, pool_name: str) -> None:
        """Initiate a scrub on the given pool."""
        try:
            self._api.scrub_pool(pool_name)
        except Exception:
            pass

    def _open_gnome_disks(self, _button: Gtk.Button) -> None:
        """Launch GNOME Disks application."""
        try:
            from gi.repository import Gio as _Gio

            app_info = _Gio.AppInfo.create_from_commandline(
                "gnome-disks", "GNOME Disks", _Gio.AppInfoCreateFlags.NONE
            )
            app_info.launch([], None)
        except Exception:
            pass
