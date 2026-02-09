"""Storage management view — disks, pools, datasets, and shares.

Displays comprehensive storage information with multiple tabs for:
- Disks: Physical devices with health and SMART status
- Pools: ZFS pools with health and usage
- Datasets: ZFS filesystems with quotas and compression
- Shares: Network shares (SMB/NFS) with connection counts
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Adwaita, Gtk

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.utils.async_helpers import run_async, schedule_repeated
from sigmavault_desktop.utils.formatting import format_bytes, format_percent

logger = logging.getLogger(__name__)


class StorageView(Gtk.Box):
    """Main storage view with tabbed interface."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize storage view.

        Args:
            api_client: API client instance
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._api_client = api_client
        self._refresh_timer_id: Optional[int] = None

        # Tab view for different storage sections
        self._tab_view = Adwaita.TabView()
        self._tab_bar = Adwaita.TabBar(view=self._tab_view)

        self.append(self._tab_bar)
        self.append(self._tab_view)

        # Create pages for each storage type
        self._disks_page = DisksPage(api_client)
        self._pools_page = PoolsPage(api_client)
        self._datasets_page = DatasetsPage(api_client)
        self._shares_page = SharesPage(api_client)

        # Add tabs
        self._tab_view.append(self._disks_page).set_title("Disks")
        self._tab_view.append(self._pools_page).set_title("Pools")
        self._tab_view.append(self._datasets_page).set_title("Datasets")
        self._tab_view.append(self._shares_page).set_title("Shares")

        # Start auto-refresh
        self.start_refresh()

    def start_refresh(self) -> None:
        """Start auto-refresh timer (20s interval for storage)."""
        if self._refresh_timer_id:
            return
        self._refresh_timer_id = schedule_repeated(20000, self._refresh_all)
        self._refresh_all()

    def stop_refresh(self) -> None:
        """Stop auto-refresh timer."""
        if self._refresh_timer_id:
            from gi.repository import GLib

            GLib.Source.remove(self._refresh_timer_id)
            self._refresh_timer_id = None

    def _refresh_all(self) -> None:
        """Refresh all tabs."""
        self._disks_page.refresh()
        self._pools_page.refresh()
        self._datasets_page.refresh()
        self._shares_page.refresh()


# ─── Disks Page ──────────────────────────────────────────────────


class DisksPage(Adwaita.PreferencesPage):
    """Page showing physical disk information."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize disks page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        # Container group
        self._group = Adwaita.PreferencesGroup(title="Physical Disks")
        self.add(self._group)

        # Loading indicator
        self._spinner = Gtk.Spinner(spinning=False)
        self._group.add(self._spinner)

    def refresh(self) -> None:
        """Fetch and display disk information."""
        self._spinner.set_spinning(True)
        run_async(self._fetch_disks)

    async def _fetch_disks(self) -> None:
        """Fetch disk data from API."""
        try:
            disks = await self._api_client.get_storage_disks()
            self._update_ui(disks)
        except Exception as e:
            logger.error(f"Failed to fetch disks: {e}")
        finally:
            self._spinner.set_spinning(False)

    def _update_ui(self, disks) -> None:
        """Update UI with disk data.

        Args:
            disks: List of StorageDisk objects
        """
        # Clear existing rows (except spinner)
        while child := self._group.get_first_child():
            if child != self._spinner:
                self._group.remove(child)
            else:
                break

        for disk in disks:
            row = Adwaita.ActionRow(
                title=f"{disk.model or 'Unknown Model'}",
                subtitle=f"{disk.device} • {format_bytes(disk.size_bytes)}",
            )

            # Status icon
            status_class = "success" if disk.status == "healthy" else "warning"
            status_box = Gtk.Box(spacing=6)
            status_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
            status_icon.add_css_class(status_class)
            status_box.append(status_icon)

            # Temperature if available
            if disk.temperature_celsius:
                temp_label = Gtk.Label(label=f"{disk.temperature_celsius}°C")
                temp_label.add_css_class("caption")
                temp_label.add_css_class("dim-label")
                status_box.append(temp_label)

            row.add_suffix(status_box)
            self._group.add(row)


# ─── Pools Page ──────────────────────────────────────────────────


class PoolsPage(Adwaita.PreferencesPage):
    """Page showing storage pool information."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize pools page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        self._group = Adwaita.PreferencesGroup(title="Storage Pools")
        self.add(self._group)

        self._spinner = Gtk.Spinner(spinning=False)
        self._group.add(self._spinner)

    def refresh(self) -> None:
        """Fetch and display pool information."""
        self._spinner.set_spinning(True)
        run_async(self._fetch_pools)

    async def _fetch_pools(self) -> None:
        """Fetch pool data from API."""
        try:
            pools = await self._api_client.get_storage_pools()
            self._update_ui(pools)
        except Exception as e:
            logger.error(f"Failed to fetch pools: {e}")
        finally:
            self._spinner.set_spinning(False)

    def _update_ui(self, pools) -> None:
        """Update UI with pool data.

        Args:
            pools: List of StoragePool objects
        """
        while child := self._group.get_first_child():
            if child != self._spinner:
                self._group.remove(child)
            else:
                break

        for pool in pools:
            # Title with pool name and health
            health_icon = "✓" if pool.health == "ONLINE" else "⚠"

            row = Adwaita.ExpanderRow(
                title=f"{health_icon} {pool.name}",
                subtitle=f"{format_bytes(pool.used_bytes)} / {format_bytes(pool.size_bytes)} ({format_percent(pool.usage_percent)} used)",
            )

            # Health indicator
            health_class = "success" if pool.health == "ONLINE" else "warning"
            health_badge = Gtk.Label(label=pool.health)
            health_badge.add_css_class(health_class)
            health_badge.add_css_class("heading")
            row.add_suffix(health_badge)

            # Add detail rows
            if pool.compression_ratio > 1.0:
                comp_row = Adwaita.ActionRow(
                    title="Compression Ratio",
                    subtitle=f"{pool.compression_ratio:.2f}:1",
                )
                row.add_row(comp_row)

            if pool.dedup_ratio > 1.0:
                dedup_row = Adwaita.ActionRow(
                    title="Deduplication Ratio",
                    subtitle=f"{pool.dedup_ratio:.2f}:1",
                )
                row.add_row(dedup_row)

            self._group.add(row)


# ─── Datasets Page ───────────────────────────────────────────────


class DatasetsPage(Adwaita.PreferencesPage):
    """Page showing dataset/filesystem information."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize datasets page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        self._group = Adwaita.PreferencesGroup(title="Datasets & Filesystems")
        self.add(self._group)

        self._spinner = Gtk.Spinner(spinning=False)
        self._group.add(self._spinner)

    def refresh(self) -> None:
        """Fetch and display dataset information."""
        self._spinner.set_spinning(True)
        run_async(self._fetch_datasets)

    async def _fetch_datasets(self) -> None:
        """Fetch dataset data from API."""
        try:
            datasets = await self._api_client.get_storage_datasets()
            self._update_ui(datasets)
        except Exception as e:
            logger.error(f"Failed to fetch datasets: {e}")
        finally:
            self._spinner.set_spinning(False)

    def _update_ui(self, datasets) -> None:
        """Update UI with dataset data.

        Args:
            datasets: List of StorageDataset objects
        """
        while child := self._group.get_first_child():
            if child != self._spinner:
                self._group.remove(child)
            else:
                break

        for ds in datasets:
            mount_status = "📁" if ds.mounted else "⊗"

            row = Adwaita.ActionRow(
                title=f"{mount_status} {ds.name}",
                subtitle=f"{ds.pool} • {format_bytes(ds.used_bytes)} used • {ds.compression}",
            )

            # Usage percentage badge
            usage_class = (
                "error"
                if ds.usage_percent > 90
                else "warning" if ds.usage_percent > 70 else "success"
            )
            usage_label = Gtk.Label(label=format_percent(ds.usage_percent))
            usage_label.add_css_class(usage_class)
            usage_label.add_css_class("heading")
            row.add_suffix(usage_label)

            self._group.add(row)


# ─── Shares Page ─────────────────────────────────────────────────


class SharesPage(Adwaita.PreferencesPage):
    """Page showing network share information."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize shares page.

        Args:
            api_client: API client instance
        """
        super().__init__()
        self._api_client = api_client

        self._group = Adwaita.PreferencesGroup(title="Network Shares")
        self.add(self._group)

        self._spinner = Gtk.Spinner(spinning=False)
        self._group.add(self._spinner)

    def refresh(self) -> None:
        """Fetch and display share information."""
        self._spinner.set_spinning(True)
        run_async(self._fetch_shares)

    async def _fetch_shares(self) -> None:
        """Fetch share data from API."""
        try:
            shares = await self._api_client.get_storage_shares()
            self._update_ui(shares)
        except Exception as e:
            logger.error(f"Failed to fetch shares: {e}")
        finally:
            self._spinner.set_spinning(False)

    def _update_ui(self, shares) -> None:
        """Update UI with share data.

        Args:
            shares: List of StorageShare objects
        """
        while child := self._group.get_first_child():
            if child != self._spinner:
                self._group.remove(child)
            else:
                break

        for share in shares:
            protocol_icon = {"smb": "📂", "nfs": "🗂", "iscsi": "💾"}.get(share.protocol, "📁")
            status_icon = "✓" if share.enabled else "⊗"

            subtitle_parts = [share.protocol.upper(), share.path]
            if share.connections > 0:
                subtitle_parts.append(f"{share.connections} connections")

            row = Adwaita.ActionRow(
                title=f"{protocol_icon} {status_icon} {share.name}",
                subtitle=" • ".join(subtitle_parts),
            )

            # Access mode badge
            access_text = "RO" if share.read_only else "RW"
            access_label = Gtk.Label(label=access_text)
            access_label.add_css_class("caption")
            access_label.add_css_class("dim-label")
            row.add_suffix(access_label)

            self._group.add(row)
