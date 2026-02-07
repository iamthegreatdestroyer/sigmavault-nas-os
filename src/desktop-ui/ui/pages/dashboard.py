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

        clamp = Adw.Clamp(maximum_size=900, margin_top=24, margin_bottom=24, margin_start=16, margin_end=16)
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

        for card in [self._agent_card, self._storage_card, self._compression_card, self._health_card]:
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

    def _make_summary_card(
        self, title: str, icon: str, value: str, subtitle: str
    ) -> dict:
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
        try:
            health = self._api.get_health()
            if health:
                # Agent card
                agents = health.get("agents", {})
                total = agents.get("total", 0)
                idle = agents.get("idle", total)
                busy = total - idle
                self._agent_card["value"].set_text(f"{total} Active")
                self._agent_card["subtitle"].set_text(
                    f"{busy} busy, {idle} idle" if busy > 0 else "All idle"
                )

                # System health
                status = health.get("status", "unknown")
                self._health_card["value"].set_text(status.title())
                uptime = health.get("uptime", "—")
                self._health_card["subtitle"].set_text(f"Uptime: {uptime}")
            else:
                self._agent_card["value"].set_text("Offline")
                self._agent_card["subtitle"].set_text("API not reachable")
                self._health_card["value"].set_text("Offline")
                self._health_card["subtitle"].set_text("—")
        except Exception as e:
            logger.warning("Dashboard refresh failed: %s", e)

        try:
            storage = self._api.get_storage_summary()
            if storage:
                total_tb = storage.get("total_bytes", 0) / (1024**4)
                free_tb = storage.get("free_bytes", 0) / (1024**4)
                self._storage_card["value"].set_text(f"{total_tb:.1f} TB")
                self._storage_card["subtitle"].set_text(f"{free_tb:.1f} TB free")
            else:
                self._storage_card["value"].set_text("—")
                self._storage_card["subtitle"].set_text("No data")
        except Exception:
            self._storage_card["value"].set_text("—")
            self._storage_card["subtitle"].set_text("No data")

        try:
            compression = self._api.get_compression_stats()
            if compression:
                jobs = compression.get("active_jobs", 0)
                ratio = compression.get("avg_ratio", 0)
                self._compression_card["value"].set_text(
                    f"{jobs} Jobs" if jobs > 0 else "Idle"
                )
                self._compression_card["subtitle"].set_text(
                    f"Avg ratio: {ratio:.1%}" if ratio else "No stats yet"
                )
            else:
                self._compression_card["value"].set_text("Idle")
                self._compression_card["subtitle"].set_text("No stats yet")
        except Exception:
            self._compression_card["value"].set_text("—")
            self._compression_card["subtitle"].set_text("No data")

        return True  # Keep refreshing
