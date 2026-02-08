"""Agent swarm monitoring view — Elite Agent Collective status.

Displays comprehensive agent information:
- Agent swarm overview with aggregate metrics
- Individual agent status cards (TIER 1-4: 40 agents)
- Real-time performance metrics
- Specialization and capabilities
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adwaita", "1")

from gi.repository import Gtk, Adwaita, GLib

from sigmavault_desktop.api.client import SigmaVaultAPIClient
from sigmavault_desktop.widgets.stat_card import StatCard
from sigmavault_desktop.utils.formatting import format_percent
from sigmavault_desktop.utils.async_helpers import run_async, schedule_repeated

logger = logging.getLogger(__name__)


class AgentsView(Gtk.Box):
    """Main agents view with swarm overview and agent list."""

    def __init__(self, api_client: SigmaVaultAPIClient):
        """Initialize agents view.

        Args:
            api_client: API client instance
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self._api_client = api_client
        self._refresh_timer_id: Optional[int] = None

        # Header
        header = Gtk.Label(label="Elite Agent Collective")
        header.add_css_class("title-1")
        header.set_halign(Gtk.Align.START)
        self.append(header)

        # Swarm metrics cards
        self._metrics_grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=12,
            column_homogeneous=True,
        )
        self.append(self._metrics_grid)

        self._total_agents_card = StatCard(
            "system-run-symbolic", "Total Agents", "—", "Active in swarm"
        )
        self._active_agents_card = StatCard(
            "starred-symbolic", "Active", "—", "Currently processing"
        )
        self._success_rate_card = StatCard(
            "emblem-ok-symbolic", "Success Rate", "—", "Task completion"
        )
        self._avg_response_card = StatCard("alarm-symbolic", "Avg Response", "—", "Response time")

        self._metrics_grid.attach(self._total_agents_card, 0, 0, 1, 1)
        self._metrics_grid.attach(self._active_agents_card, 1, 0, 1, 1)
        self._metrics_grid.attach(self._success_rate_card, 2, 0, 1, 1)
        self._metrics_grid.attach(self._avg_response_card, 3, 0, 1, 1)

        # Agent list header
        list_header = Gtk.Label(label="Agent List")
        list_header.add_css_class("title-3")
        list_header.set_halign(Gtk.Align.START)
        list_header.set_margin_top(12)
        self.append(list_header)

        # Scrollable agent list
        scrolled = Gtk.ScrolledWindow(
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        self.append(scrolled)

        self._agent_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._agent_list.add_css_class("boxed-list")
        scrolled.set_child(self._agent_list)

        # Start auto-refresh (fast for agents: 5s)
        self.start_refresh()

    def start_refresh(self) -> None:
        """Start auto-refresh timer (5s interval for real-time monitoring)."""
        if self._refresh_timer_id:
            return
        self._refresh_timer_id = schedule_repeated(5000, self._refresh_data)
        self._refresh_data()

    def stop_refresh(self) -> None:
        """Stop auto-refresh timer."""
        if self._refresh_timer_id:
            GLib.Source.remove(self._refresh_timer_id)
            self._refresh_timer_id = None

    def _refresh_data(self) -> None:
        """Fetch and update agent data."""
        run_async(self._fetch_agents)

    async def _fetch_agents(self) -> None:
        """Fetch agent data from API."""
        try:
            agents = await self._api_client.get_agents()
            self._update_ui(agents)
        except Exception as e:
            logger.error(f"Failed to fetch agents: {e}")

    def _update_ui(self, agents) -> None:
        """Update UI with agent data.

        Args:
            agents: List of Agent objects
        """
        if not agents:
            self._total_agents_card.set_value("0")
            self._active_agents_card.set_value("0")
            self._success_rate_card.set_value("—")
            self._avg_response_card.set_value("—")
            return

        # Calculate aggregate metrics
        total = len(agents)
        active = sum(1 for a in agents if a.is_active)

        # Average metrics from agent metrics
        total_completed = sum(a.metrics.tasks_completed for a in agents if a.metrics)
        total_failed = sum(a.metrics.tasks_failed for a in agents if a.metrics)
        total_tasks = total_completed + total_failed
        success_rate = (total_completed / total_tasks * 100) if total_tasks > 0 else 0

        avg_response = (
            sum(a.metrics.avg_response_time_ms for a in agents if a.metrics) / total
            if total > 0
            else 0
        )

        # Update stat cards
        self._total_agents_card.set_value(str(total))
        self._active_agents_card.set_value(str(active))
        self._active_agents_card.set_value_css_class("success" if active > 0 else "dim-label")

        self._success_rate_card.set_value(format_percent(success_rate))
        self._success_rate_card.set_value_css_class(
            "success" if success_rate >= 95 else "warning" if success_rate >= 80 else "error"
        )

        self._avg_response_card.set_value(f"{avg_response:.0f} ms")
        self._avg_response_card.set_value_css_class(
            "success" if avg_response < 100 else "warning" if avg_response < 500 else "error"
        )

        # Update agent list
        self._update_agent_list(agents)

    def _update_agent_list(self, agents) -> None:
        """Update the agent list with current agents.

        Args:
            agents: List of Agent objects
        """
        # Clear existing rows
        while child := self._agent_list.get_first_child():
            self._agent_list.remove(child)

        # Sort by tier then name
        agents_sorted = sorted(agents, key=lambda a: (a.tier, a.name))

        for agent in agents_sorted:
            row = AgentRow(agent)
            self._agent_list.append(row)


class AgentRow(Adwaita.ExpanderRow):
    """Single agent row with expandable metrics."""

    def __init__(self, agent):
        """Initialize agent row.

        Args:
            agent: Agent object
        """
        # Status icon
        status_icons = {
            "active": "✓",
            "idle": "○",
            "error": "✗",
            "offline": "⊗",
        }
        status_icon = status_icons.get(agent.status, "?")

        # Title: CODENAME (Tier X)
        title = f"{status_icon} {agent.name} (Tier {agent.tier})"

        # Subtitle: specialty
        subtitle = agent.specialty

        super().__init__(title=title, subtitle=subtitle)

        # Status badge
        status_class = {
            "active": "success",
            "idle": "dim-label",
            "error": "error",
            "offline": "warning",
        }.get(agent.status, "dim-label")

        status_badge = Gtk.Label(label=agent.status.upper())
        status_badge.add_css_class(status_class)
        status_badge.add_css_class("caption")
        self.add_suffix(status_badge)

        # Add metrics rows if available
        if agent.metrics:
            self._add_metrics_rows(agent.metrics)

    def _add_metrics_rows(self, metrics) -> None:
        """Add expandable rows for agent metrics.

        Args:
            metrics: AgentMetrics object
        """
        # Tasks row
        tasks_row = Adwaita.ActionRow(
            title="Tasks",
            subtitle=f"{metrics.tasks_completed} completed, {metrics.tasks_failed} failed",
        )
        success_label = Gtk.Label(label=f"{format_percent(metrics.success_rate)} success")
        success_label.add_css_class("caption")
        success_label.add_css_class("success" if metrics.success_rate >= 95 else "warning")
        tasks_row.add_suffix(success_label)
        self.add_row(tasks_row)

        # Performance row
        perf_row = Adwaita.ActionRow(
            title="Performance",
            subtitle=f"{metrics.avg_response_time_ms:.0f} ms avg response",
        )
        self.add_row(perf_row)

        # Resources row
        resources_row = Adwaita.ActionRow(
            title="Resources",
            subtitle=f"CPU: {format_percent(metrics.cpu_usage_percent)}, Memory: {metrics.memory_usage_mb:.0f} MB",
        )
        self.add_row(resources_row)
