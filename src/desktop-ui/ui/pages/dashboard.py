"""
Dashboard Page — System overview with agent summary, storage capacity, and health.
"""

import logging
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib  # noqa: E402

logger = logging.getLogger("sigmavault.dashboard")


class DashboardPage(Gtk.Box):
    """Overview page: agent summary, storage capacity, system health, recent activity."""

    def __init__(self, api: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._api = api
        self._build_ui()
        GLib.idle_add(self._refresh_data)
        GLib.timeout_add_seconds(10, self._refresh_data)

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(scrolled)

        clamp = Adw.Clamp(
            maximum_size=900, margin_top=24, margin_bottom=24, margin_start=16, margin_end=16
        )
        scrolled.set_child(clamp)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)

        # ── Welcome banner ──
        banner = Adw.StatusPage(
            title="SigmaVault NAS OS",
            description="AI-Powered Storage Management — 40 Agent Swarm",
            icon_name="drive-harddisk-symbolic",
        )
        banner.set_vexpand(False)
        content.append(banner)

        # ── Summary cards row ──
        cards_row = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            max_children_per_line=4,
            min_children_per_line=2,
            column_spacing=16,
            row_spacing=16,
            homogeneous=True,
        )
        content.append(cards_row)

        self._agent_card = self._make_summary_card(
            "Agents", "system-run-symbolic", "Loading...", "—"
        )
        self._storage_card = self._make_summary_card(
            "Storage", "drive-harddisk-symbolic", "Loading...", "—"
        )
        self._compression_card = self._make_summary_card(
            "Compression", "package-x-generic-symbolic", "Loading...", "—"
        )
        self._health_card = self._make_summary_card(
            "System", "computer-symbolic", "Loading...", "—"
        )

        for card in [
            self._agent_card,
            self._storage_card,
            self._compression_card,
            self._health_card,
        ]:
            cards_row.append(card["widget"])

        # ── Recent activity ──
        activity_group = Adw.PreferencesGroup(title="Recent Activity")
        content.append(activity_group)

        self._activity_rows: list[Adw.ActionRow] = []
        for _ in range(5):
            row = Adw.ActionRow(title="—", subtitle="Waiting for data...")
            row.set_activatable(False)
            activity_group.add(row)
            self._activity_rows.append(row)

    def _make_summary_card(self, title: str, icon: str, value: str, subtitle: str) -> dict:
        """Create a summary card widget. Returns dict with widget + value/subtitle labels."""
        frame = Gtk.Frame(css_classes=["card"])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.set_child(box)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.append(Gtk.Image(icon_name=icon, pixel_size=24))
        header.append(Gtk.Label(label=title, css_classes=["heading"], hexpand=True, xalign=0))
        box.append(header)

        value_label = Gtk.Label(label=value, css_classes=["title-1"], xalign=0)
        box.append(value_label)

        sub_label = Gtk.Label(label=subtitle, css_classes=["dim-label"], xalign=0)
        box.append(sub_label)

        return {"widget": frame, "value": value_label, "subtitle": sub_label}

    def _refresh_data(self) -> bool:
        """Fetch data from API and update dashboard cards."""
        # ── Agents data ──
        try:
            agents_data = self._api.get_agents()
            if agents_data:
                total = agents_data.get("count", 0)
                active = agents_data.get("active_count", 0)
                idle = agents_data.get("idle_count", 0)
                self._agent_card["value"].set_text(f"{total} Total")
                self._agent_card["subtitle"].set_text(
                    f"{active} active, {idle} idle" if active > 0 else "All idle"
                )
            else:
                self._agent_card["value"].set_text("Offline")
                self._agent_card["subtitle"].set_text("API not reachable")
        except Exception as e:
            logger.warning("Failed to fetch agents: %s", e)
            self._agent_card["value"].set_text("Error")
            self._agent_card["subtitle"].set_text("—")

        # ── System status ──
        try:
            system = self._api.get_system_status()
            if system:
                uptime_sec = system.get("uptime", 0)
                uptime_hours = uptime_sec // 3600
                uptime_days = uptime_hours // 24
                uptime_str = (
                    f"{uptime_days}d {uptime_hours % 24}h"
                    if uptime_days > 0
                    else f"{uptime_hours}h"
                )

                cpu_pct = system.get("cpu_usage", 0)
                mem_pct = system.get("memory_use_pct", 0)

                self._health_card["value"].set_text(f"{cpu_pct:.0f}% CPU")
                self._health_card["subtitle"].set_text(f"Uptime: {uptime_str}, Mem: {mem_pct:.0f}%")
            else:
                self._health_card["value"].set_text("Offline")
                self._health_card["subtitle"].set_text("—")
        except Exception as e:
            logger.debug("Failed to fetch system status: %s", e)
            self._health_card["value"].set_text("—")
            self._health_card["subtitle"].set_text("No data")

        # ── Storage data ──
        try:
            pools = self._api.get_pools()
            if pools and "pools" in pools:
                pool_list = pools["pools"]
                if pool_list:
                    # Sum up capacity across all pools
                    total_bytes = sum(p.get("size", 0) for p in pool_list)
                    free_bytes = sum(p.get("free", 0) for p in pool_list)
                    total_tb = total_bytes / (1024**4)
                    free_tb = free_bytes / (1024**4)
                    self._storage_card["value"].set_text(f"{total_tb:.1f} TB")
                    self._storage_card["subtitle"].set_text(f"{free_tb:.1f} TB free")
                else:
                    self._storage_card["value"].set_text("No Pools")
                    self._storage_card["subtitle"].set_text("Create a pool")
            else:
                self._storage_card["value"].set_text("—")
                self._storage_card["subtitle"].set_text("No data")
        except Exception as e:
            logger.debug("Failed to fetch storage: %s", e)
            self._storage_card["value"].set_text("—")
            self._storage_card["subtitle"].set_text("No data")

        # ── Compression data ──
        try:
            jobs = self._api.get_compression_jobs()
            if jobs and "jobs" in jobs:
                job_list = jobs["jobs"]
                active = sum(1 for j in job_list if j.get("status") == "running")
                completed = sum(1 for j in job_list if j.get("status") == "completed")

                if active > 0:
                    self._compression_card["value"].set_text(f"{active} Running")
                    self._compression_card["subtitle"].set_text(f"{completed} completed")
                elif completed > 0:
                    self._compression_card["value"].set_text("Idle")
                    self._compression_card["subtitle"].set_text(f"{completed} total")
                else:
                    self._compression_card["value"].set_text("Idle")
                    self._compression_card["subtitle"].set_text("No jobs yet")
            else:
                self._compression_card["value"].set_text("Idle")
                self._compression_card["subtitle"].set_text("No jobs yet")
        except Exception as e:
            logger.debug("Failed to fetch compression: %s", e)
            self._compression_card["value"].set_text("—")
            self._compression_card["subtitle"].set_text("No data")

        return True  # Keep refreshing
