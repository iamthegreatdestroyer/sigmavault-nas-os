"""SigmaVault Desktop UI utilities.

Formatting helpers and async-to-GTK bridge functions.
"""

from sigmavault_desktop.utils.formatting import (
    format_bytes,
    format_duration,
    format_percent,
    format_ratio,
    format_throughput,
    status_to_css_class,
    status_to_icon,
)

# async_helpers requires GTK (gi) — only import where available
try:
    from sigmavault_desktop.utils.async_helpers import (
        idle_add,
        run_async,
        schedule_repeated,
    )
except ImportError:
    # Running on a system without GTK (Windows dev, CI, etc.)
    run_async = None  # type: ignore
    schedule_repeated = None  # type: ignore
    idle_add = None  # type: ignore

__all__ = [
    "format_bytes",
    "format_duration",
    "format_percent",
    "format_ratio",
    "format_throughput",
    "status_to_icon",
    "status_to_css_class",
    "run_async",
    "schedule_repeated",
    "idle_add",
]
