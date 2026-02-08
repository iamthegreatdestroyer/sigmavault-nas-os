"""Unit tests for sigmavault_desktop.utils.formatting module.

These are pure Python tests — no GTK dependencies required.
Run with: python -m pytest test_formatting.py -v
"""

import pytest
from sigmavault_desktop.utils.formatting import (
    format_bytes,
    format_duration,
    format_percent,
    format_ratio,
    format_throughput,
    status_to_icon,
    status_to_css_class,
)

# ─── format_bytes ─────────────────────────────────────────────────────


class TestFormatBytes:
    """Test human-readable byte formatting."""

    def test_zero(self):
        assert format_bytes(0) == "0 B"

    def test_bytes(self):
        assert format_bytes(512) == "512 B"

    def test_kilobytes(self):
        result = format_bytes(1024)
        assert result == "1.00 KB"

    def test_megabytes(self):
        result = format_bytes(1_500_000)
        assert "MB" in result
        assert result == "1.43 MB"

    def test_gigabytes(self):
        result = format_bytes(2_500_000_000)
        assert "GB" in result
        assert result == "2.33 GB"

    def test_terabytes(self):
        result = format_bytes(5_000_000_000_000)
        assert "TB" in result

    def test_none(self):
        assert format_bytes(None) == "\u2014"

    def test_negative(self):
        # Negative bytes don't divide down (while loop condition fails)
        result = format_bytes(-1024)
        assert "B" in result

    def test_large_value(self):
        result = format_bytes(1_000_000_000_000_000)
        assert "PB" in result or "TB" in result


# ─── format_duration ──────────────────────────────────────────────────


class TestFormatDuration:
    """Test human-readable duration formatting."""

    def test_zero(self):
        assert format_duration(0) == "0s"

    def test_seconds_only(self):
        assert format_duration(45) == "45s"

    def test_minutes_and_seconds(self):
        result = format_duration(125)
        assert "2m" in result
        assert "5s" in result

    def test_hours_minutes_seconds(self):
        result = format_duration(3661)
        assert "1h" in result
        assert "1m" in result
        assert "1s" in result

    def test_none(self):
        assert format_duration(None) == "—"

    def test_fractional_seconds(self):
        result = format_duration(0.5)
        # 0.5 > 0 but int(0.5 % 60) = 0, so returns "0s"
        assert result == "0s"

    def test_large_duration(self):
        result = format_duration(86400)  # 24 hours
        assert "24h" in result


# ─── format_percent ───────────────────────────────────────────────────


class TestFormatPercent:
    """Test percentage formatting."""

    def test_zero(self):
        assert format_percent(0) == "0.0%"

    def test_hundred(self):
        assert format_percent(100) == "100.0%"

    def test_decimal_precision(self):
        result = format_percent(85.678, decimals=1)
        assert result == "85.7%"

    def test_two_decimals(self):
        result = format_percent(85.678, decimals=2)
        assert result == "85.68%"

    def test_none(self):
        assert format_percent(None) == "\u2014"

    def test_small_value(self):
        result = format_percent(0.1)
        assert "%" in result


# ─── format_ratio ─────────────────────────────────────────────────────


class TestFormatRatio:
    """Test compression ratio formatting.

    Note: format_ratio treats ratio as compressed/original fraction.
    A ratio of 0.15 means 15% of original → 6.7:1 compression.
    A ratio >= 1.0 means no savings.
    """

    def test_no_compression(self):
        assert format_ratio(1.0) == "1:1 (no savings)"

    def test_good_compression(self):
        # 0.15 ratio → 1/0.15 = 6.67:1
        assert format_ratio(0.15) == "6.7:1"

    def test_none(self):
        assert format_ratio(None) == "\u2014"

    def test_zero(self):
        assert format_ratio(0) == "N/A"

    def test_half_compression(self):
        # 0.5 ratio → 2.0:1
        assert format_ratio(0.5) == "2.0:1"

    def test_extreme_compression(self):
        # 0.01 ratio → 100.0:1
        result = format_ratio(0.01)
        assert ":1" in result


# ─── format_throughput ────────────────────────────────────────────────


class TestFormatThroughput:
    """Test throughput formatting."""

    def test_normal(self):
        result = format_throughput(125.3)
        assert result == "125.3 MB/s"

    def test_zero(self):
        assert format_throughput(0) == "0 MB/s"

    def test_none(self):
        assert format_throughput(None) == "\u2014"

    def test_small_value(self):
        # 0.5 MB/s < 1 MB/s → converted to KB/s
        result = format_throughput(0.5)
        assert "KB/s" in result


# ─── status_to_icon ───────────────────────────────────────────────────


class TestStatusToIcon:
    """Test status to GTK icon name mapping."""

    def test_completed(self):
        result = status_to_icon("completed")
        assert "check" in result or "success" in result or "emblem" in result

    def test_running(self):
        result = status_to_icon("running")
        assert isinstance(result, str) and len(result) > 0

    def test_failed(self):
        result = status_to_icon("failed")
        assert isinstance(result, str) and len(result) > 0

    def test_queued(self):
        result = status_to_icon("queued")
        assert isinstance(result, str) and len(result) > 0

    def test_unknown_status(self):
        result = status_to_icon("banana")
        assert isinstance(result, str)  # Should return a default

    def test_none(self):
        result = status_to_icon(None)
        assert isinstance(result, str)


# ─── status_to_css_class ─────────────────────────────────────────────


class TestStatusToCssClass:
    """Test status to CSS class mapping."""

    def test_completed(self):
        result = status_to_css_class("completed")
        assert result == "success"

    def test_failed(self):
        result = status_to_css_class("failed")
        assert result == "error"

    def test_running(self):
        result = status_to_css_class("running")
        assert result == "accent"

    def test_queued(self):
        result = status_to_css_class("queued")
        assert result in ("dim-label", "warning")

    def test_unknown(self):
        result = status_to_css_class("mystery")
        assert isinstance(result, str)


# ─── Edge cases & robustness ─────────────────────────────────────────


class TestEdgeCases:
    """Cross-cutting edge case tests."""

    def test_format_bytes_exact_boundaries(self):
        """Test at exact KB/MB/GB boundaries."""
        assert "1.00 KB" == format_bytes(1024)
        assert "1.00 MB" == format_bytes(1024**2)
        assert "1.00 GB" == format_bytes(1024**3)
        assert "1.00 TB" == format_bytes(1024**4)

    def test_format_duration_boundary(self):
        """Test at exact time boundaries."""
        assert format_duration(60) == "1m 0s" or "1m" in format_duration(60)
        assert "1h" in format_duration(3600)

    def test_all_formatters_handle_none(self):
        """Every formatter should return '—' for None."""
        assert format_bytes(None) == "—"
        assert format_duration(None) == "—"
        assert format_percent(None) == "—"
        assert format_ratio(None) == "—"
        assert format_throughput(None) == "—"

    def test_all_status_values(self):
        """Ensure all known job statuses map correctly."""
        statuses = ["completed", "running", "queued", "failed", "cancelled"]
        for s in statuses:
            icon = status_to_icon(s)
            css = status_to_css_class(s)
            assert isinstance(icon, str), f"Icon for '{s}' should be str"
            assert isinstance(css, str), f"CSS for '{s}' should be str"
