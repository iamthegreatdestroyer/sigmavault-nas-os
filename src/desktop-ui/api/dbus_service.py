"""
SigmaVault D-Bus Service — Expose compression/agent actions over D-Bus.

Allows Nautilus extensions and other desktop components to trigger
SigmaVault operations without direct API calls.

Bus name: com.sigmavault.Settings
Object path: /com/sigmavault/Settings
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib  # noqa: E402

logger = logging.getLogger("sigmavault.api.dbus")

DBUS_XML = """
<node>
  <interface name="com.sigmavault.Settings">
    <method name="CompressFile">
      <arg direction="in" name="path" type="s"/>
      <arg direction="in" name="algorithm" type="s"/>
      <arg direction="out" name="job_id" type="s"/>
    </method>
    <method name="GetHealth">
      <arg direction="out" name="result" type="s"/>
    </method>
    <method name="ShowPage">
      <arg direction="in" name="page_id" type="s"/>
    </method>
    <signal name="JobCompleted">
      <arg name="job_id" type="s"/>
      <arg name="status" type="s"/>
    </signal>
    <signal name="AgentStatusChanged">
      <arg name="agent_name" type="s"/>
      <arg name="new_status" type="s"/>
    </signal>
  </interface>
</node>
"""


class SigmaVaultDBusService:
    """D-Bus service for desktop integration."""

    def __init__(self, app, api_client) -> None:
        self._app = app
        self._api = api_client
        self._registration_id: Optional[int] = None
        self._bus_id: Optional[int] = None

    def register(self) -> None:
        """Register the D-Bus service on the session bus."""
        self._bus_id = Gio.bus_own_name(
            Gio.BusType.SESSION,
            "com.sigmavault.Settings",
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            self._on_name_acquired,
            self._on_name_lost,
        )

    def unregister(self) -> None:
        """Release the D-Bus name."""
        if self._bus_id:
            Gio.bus_unown_name(self._bus_id)
            self._bus_id = None

    def emit_job_completed(self, connection: Gio.DBusConnection, job_id: str, status: str) -> None:
        """Emit JobCompleted signal."""
        try:
            connection.emit_signal(
                None,
                "/com/sigmavault/Settings",
                "com.sigmavault.Settings",
                "JobCompleted",
                GLib.Variant("(ss)", (job_id, status)),
            )
        except Exception as e:
            logger.warning("Failed to emit D-Bus signal: %s", e)

    # ─── Bus Callbacks ──────────────────────────────────────────

    def _on_bus_acquired(self, connection: Gio.DBusConnection, name: str) -> None:
        """Register the object when bus is acquired."""
        node_info = Gio.DBusNodeInfo.new_for_xml(DBUS_XML)
        self._registration_id = connection.register_object(
            "/com/sigmavault/Settings",
            node_info.interfaces[0],
            self._on_method_call,
            None,
            None,
        )
        logger.info("D-Bus object registered: %s", name)

    def _on_name_acquired(self, _connection: Gio.DBusConnection, name: str) -> None:
        logger.info("D-Bus name acquired: %s", name)

    def _on_name_lost(self, _connection: Gio.DBusConnection, name: str) -> None:
        logger.warning("D-Bus name lost: %s", name)

    def _on_method_call(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _object_path: str,
        _interface_name: str,
        method_name: str,
        parameters: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        """Handle incoming D-Bus method calls."""
        try:
            if method_name == "CompressFile":
                path = parameters.get_child_value(0).get_string()
                algorithm = parameters.get_child_value(1).get_string()
                result = self._api.compress_file(path, algorithm=algorithm or "auto")
                job_id = result.get("job_id", "") if result else ""
                invocation.return_value(GLib.Variant("(s)", (job_id,)))

            elif method_name == "GetHealth":
                import json

                health = self._api.get_health()
                invocation.return_value(GLib.Variant("(s)", (json.dumps(health or {}),)))

            elif method_name == "ShowPage":
                page_id = parameters.get_child_value(0).get_string()
                # Navigate the main window to the requested page
                for win in self._app.get_windows():
                    if hasattr(win, "navigate_to"):
                        win.navigate_to(page_id)
                        win.present()
                        break
                invocation.return_value(None)

            else:
                invocation.return_error_literal(
                    Gio.dbus_error_quark(),
                    Gio.DBusError.UNKNOWN_METHOD,
                    f"Unknown method: {method_name}",
                )
        except Exception as e:
            logger.error("D-Bus method %s failed: %s", method_name, e)
            invocation.return_error_literal(
                Gio.dbus_error_quark(),
                Gio.DBusError.FAILED,
                str(e),
            )
