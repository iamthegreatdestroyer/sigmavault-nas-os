"""Async helpers for bridging asyncio with GTK's GLib main loop.

GTK4 runs a GLib main loop on the UI thread. All UI updates MUST happen
on that thread. This module provides utilities to run async operations
on background threads and deliver results back to the UI thread safely.
"""

import asyncio
import logging
import threading
from typing import Any, Callable, Coroutine, Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib

logger = logging.getLogger(__name__)


def run_async(
    coro: Coroutine,
    callback: Optional[Callable[[Any], None]] = None,
    error_callback: Optional[Callable[[Exception], None]] = None,
) -> None:
    """Run an async coroutine from the GTK main loop.

    Executes the coroutine on a background thread with its own event loop.
    When complete, delivers the result (or error) back to the GTK main
    thread via GLib.idle_add.

    Args:
        coro: The async coroutine to execute
        callback: Called on main thread with the result on success
        error_callback: Called on main thread with the exception on failure

    Example:
        async def fetch_data():
            async with SigmaVaultAPIClient() as client:
                return await client.get_system_status()

        def on_data(status):
            label.set_text(f"CPU: {status.cpu_percent}%")

        def on_error(err):
            label.set_text(f"Error: {err}")

        run_async(fetch_data(), callback=on_data, error_callback=on_error)
    """

    def _thread_target():
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(coro)
            if callback:
                GLib.idle_add(callback, result)
        except Exception as e:
            logger.error(f"Async operation failed: {e}", exc_info=True)
            if error_callback:
                GLib.idle_add(error_callback, e)
        finally:
            loop.close()

    thread = threading.Thread(target=_thread_target, daemon=True)
    thread.start()


def schedule_repeated(
    interval_ms: int,
    callback: Callable[[], bool],
) -> int:
    """Schedule a callback to run repeatedly on the GTK main loop.

    Args:
        interval_ms: Interval between calls in milliseconds
        callback: Function to call. Return True to continue, False to stop.

    Returns:
        Source ID that can be used with GLib.source_remove() to cancel

    Example:
        def refresh_status():
            run_async(fetch_status(), callback=update_ui)
            return True  # Keep repeating

        source_id = schedule_repeated(5000, refresh_status)
        # Later: GLib.source_remove(source_id)
    """
    return GLib.timeout_add(interval_ms, callback)


def idle_add(callback: Callable, *args) -> int:
    """Schedule a callback on the GTK main thread.

    Thin wrapper around GLib.idle_add for consistency.

    Args:
        callback: Function to call on the main thread
        *args: Arguments to pass to callback

    Returns:
        Source ID
    """
    return GLib.idle_add(callback, *args)
