"""
Compression Page — Job queue, compression settings, file type strategies.
"""

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib, Gdk  # noqa: E402

import logging

logger = logging.getLogger("sigmavault.compression")


class CompressionPage(Gtk.Box):
    """Compression management: submit jobs, view queue, configure strategies."""

    def __init__(self, api: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._api = api
        self._build_ui()
        GLib.timeout_add_seconds(5, self._refresh_jobs)

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(scrolled)

        clamp = Adw.Clamp(maximum_size=800, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        scrolled.set_child(clamp)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)

        # ── Quick compress action ──
        action_group = Adw.PreferencesGroup(
            title="Quick Compress",
            description="Select files to compress using the AI-powered engine",
        )
        content.append(action_group)

        # File chooser row
        file_row = Adw.ActionRow(
            title="Select Files",
            subtitle="Choose files or folders to compress",
            icon_name="document-open-symbolic",
            activatable=True,
        )
        file_row.connect("activated", self._on_select_files)
        file_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        action_group.add(file_row)

        # Algorithm selection
        algo_row = Adw.ComboRow(
            title="Algorithm",
            subtitle="Compression algorithm to use",
            icon_name="preferences-system-symbolic",
        )
        algo_model = Gtk.StringList.new(["Auto (AI-Selected)", "zstd", "zlib", "lz4", "brotli"])
        algo_row.set_model(algo_model)
        algo_row.set_selected(0)
        self._algo_row = algo_row
        action_group.add(algo_row)

        # Level selection
        level_row = Adw.SpinRow.new_with_range(1, 22, 1)
        level_row.set_title("Compression Level")
        level_row.set_subtitle("Higher = better ratio, slower")
        level_row.set_value(6)
        self._level_row = level_row
        action_group.add(level_row)

        # ── Active jobs ──
        self._jobs_group = Adw.PreferencesGroup(
            title="Active Jobs",
            description="Currently running compression tasks",
        )
        content.append(self._jobs_group)

        self._no_jobs_row = Adw.ActionRow(
            title="No active jobs",
            subtitle="Submit a compression request to get started",
            icon_name="emblem-ok-symbolic",
        )
        self._jobs_group.add(self._no_jobs_row)

        # ── Statistics ──
        stats_group = Adw.PreferencesGroup(
            title="Statistics",
            description="Historical compression performance",
        )
        content.append(stats_group)

        self._total_saved_row = Adw.ActionRow(
            title="Total Space Saved",
            subtitle="Calculating...",
            icon_name="emblem-documents-symbolic",
        )
        stats_group.add(self._total_saved_row)

        self._avg_ratio_row = Adw.ActionRow(
            title="Average Ratio",
            subtitle="Calculating...",
            icon_name="accessories-calculator-symbolic",
        )
        stats_group.add(self._avg_ratio_row)

        self._jobs_completed_row = Adw.ActionRow(
            title="Jobs Completed",
            subtitle="Calculating...",
            icon_name="emblem-default-symbolic",
        )
        stats_group.add(self._jobs_completed_row)

    def _on_select_files(self, _row: Adw.ActionRow) -> None:
        """Open native file chooser and submit compression job."""
        dialog = Gtk.FileDialog(title="Select Files to Compress")
        dialog.open_multiple(self.get_root(), None, self._on_files_selected)

    def _on_files_selected(self, dialog: Gtk.FileDialog, result) -> None:
        """Handle file selection result."""
        try:
            files = dialog.open_multiple_finish(result)
            if files:
                algo_idx = self._algo_row.get_selected()
                algos = ["auto", "zstd", "zlib", "lz4", "brotli"]
                algo = algos[algo_idx] if algo_idx < len(algos) else "auto"
                level = int(self._level_row.get_value())

                for i in range(files.get_n_items()):
                    gfile = files.get_item(i)
                    path = gfile.get_path()
                    if path:
                        logger.info("Submitting compression: %s (algo=%s, level=%d)", path, algo, level)
                        try:
                            self._api.compress_file(path, algorithm=algo, level=level)
                        except Exception as e:
                            logger.error("Compression submit failed: %s", e)

                self._refresh_jobs()
        except Exception as e:
            logger.warning("File selection cancelled or failed: %s", e)

    def _refresh_jobs(self) -> bool:
        """Fetch active compression jobs from API."""
        try:
            stats = self._api.get_compression_stats()
            if stats:
                saved = stats.get("total_saved_bytes", 0)
                ratio = stats.get("avg_ratio", 0)
                completed = stats.get("completed_jobs", 0)

                if saved > 1024**3:
                    self._total_saved_row.set_subtitle(f"{saved / 1024**3:.2f} GB")
                elif saved > 1024**2:
                    self._total_saved_row.set_subtitle(f"{saved / 1024**2:.1f} MB")
                else:
                    self._total_saved_row.set_subtitle(f"{saved} bytes")

                self._avg_ratio_row.set_subtitle(f"{ratio:.1%}" if ratio else "No data")
                self._jobs_completed_row.set_subtitle(str(completed))
        except Exception:
            pass
        return True
