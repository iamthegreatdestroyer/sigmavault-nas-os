"""
Agents Page — 40 agent cards with status, tier, task assignment.
"""

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import logging

from gi.repository import Adw, GLib, Gtk  # noqa: E402

logger = logging.getLogger("sigmavault.agents")

# Agent tier colors for visual grouping
TIER_LABELS = {
    1: "Foundational",
    2: "Specialist",
    3: "Innovator",
    4: "Meta",
    5: "Domain",
    6: "Emerging Tech",
    7: "Human-Centric",
    8: "Enterprise",
}


class AgentsPage(Gtk.Box):
    """Agent swarm management: view status, assign tasks, see results."""

    def __init__(self, api: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._api = api
        self._agent_rows: dict[str, Adw.ActionRow] = {}
        self._build_ui()
        GLib.idle_add(self._refresh_agents)
        GLib.timeout_add_seconds(10, self._refresh_agents)

    def _build_ui(self) -> None:
        # Search bar
        search_bar = Gtk.SearchBar()
        self._search_entry = Gtk.SearchEntry(placeholder_text="Search agents...")
        self._search_entry.connect("search-changed", self._on_search_changed)
        search_bar.set_child(self._search_entry)
        search_bar.set_search_mode(True)
        self.append(search_bar)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(scrolled)

        clamp = Adw.Clamp(
            maximum_size=900, margin_top=8, margin_bottom=16, margin_start=16, margin_end=16
        )
        scrolled.set_child(clamp)

        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(self._content)

        # Summary bar
        self._summary_label = Gtk.Label(
            label="Loading agent swarm...",
            css_classes=["dim-label"],
            xalign=0,
            margin_top=8,
        )
        self._content.append(self._summary_label)

        # Agent groups by tier
        self._tier_groups: dict[int, Adw.PreferencesGroup] = {}

    def _ensure_tier_group(self, tier: int) -> Adw.PreferencesGroup:
        """Get or create a PreferencesGroup for the given tier."""
        if tier not in self._tier_groups:
            label = TIER_LABELS.get(tier, f"Tier {tier}")
            group = Adw.PreferencesGroup(title=f"Tier {tier} — {label}")
            self._tier_groups[tier] = group
            self._content.append(group)
        return self._tier_groups[tier]

    def _refresh_agents(self) -> bool:
        """Fetch agent list from API and populate cards."""
        try:
            agents = self._api.get_agents()
            if not agents:
                return True

            total = len(agents)
            busy = sum(1 for a in agents if a.get("status") == "busy")
            idle = total - busy
            self._summary_label.set_text(f"{total} agents — {busy} busy, {idle} idle")

            for agent in agents:
                name = agent.get("name", "Unknown")
                tier = agent.get("tier", 1)
                status = agent.get("status", "idle")
                specialty = agent.get("specialty", "")
                tasks_completed = agent.get("tasks_completed", 0)

                if name in self._agent_rows:
                    # Update existing row
                    row = self._agent_rows[name]
                    row.set_subtitle(f"{specialty} — {status} — {tasks_completed} tasks")
                else:
                    # Create new row
                    group = self._ensure_tier_group(tier)
                    row = Adw.ActionRow(
                        title=name,
                        subtitle=f"{specialty} — {status} — {tasks_completed} tasks",
                        icon_name="system-run-symbolic",
                        activatable=True,
                    )
                    row.agent_name = name  # type: ignore[attr-defined]
                    row.connect("activated", self._on_agent_clicked)

                    # Status indicator suffix
                    status_icon = Gtk.Image(
                        icon_name=(
                            "media-record-symbolic"
                            if status == "idle"
                            else "media-playback-start-symbolic"
                        ),
                        css_classes=["success" if status == "idle" else "warning"],
                        tooltip_text=status,
                    )
                    row.add_suffix(status_icon)
                    row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))

                    group.add(row)
                    self._agent_rows[name] = row

        except Exception as e:
            logger.warning("Agent refresh failed: %s", e)

        return True

    def _on_agent_clicked(self, row: Adw.ActionRow) -> None:
        """Show agent detail dialog with task assignment."""
        agent_name = row.agent_name  # type: ignore[attr-defined]
        dialog = Adw.AlertDialog(
            heading=agent_name,
            body=f"Assign a task to {agent_name}.\n\nPre-built tasks will appear here based on agent specialty.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("health", "Check Health")
        dialog.set_response_appearance("health", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_task_response, agent_name)
        dialog.present(self.get_root())

    def _on_task_response(self, dialog: Adw.AlertDialog, response: str, agent_name: str) -> None:
        if response == "health":
            logger.info("Assigning health check to %s", agent_name)
            try:
                self._api.assign_agent_task(agent_name, {"type": "health_check"})
            except Exception as e:
                logger.error("Task assignment failed: %s", e)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Filter agent rows by search text."""
        query = entry.get_text().lower()
        for name, row in self._agent_rows.items():
            visible = query in name.lower() if query else True
            row.set_visible(visible)
