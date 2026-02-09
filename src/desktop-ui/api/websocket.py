"""
SigmaVault WebSocket Client — Real-time event stream from Go API.

Runs in a background thread and dispatches events to GTK main loop
via GLib.idle_add() for thread-safe UI updates.
"""

import json
import logging
import threading
import time
from typing import Any, Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib  # noqa: E402

logger = logging.getLogger("sigmavault.api.websocket")

DEFAULT_WS_URL = "ws://localhost:3000/ws"
RECONNECT_DELAY = 5  # seconds


class SigmaVaultWebSocket:
    """WebSocket client for real-time events from the Go API.

    Uses the built-in `http.client` + raw sockets for WebSocket framing
    (minimal implementation, no external deps). For production, consider
    using the `websockets` library.

    Events are dispatched to registered callbacks on the GTK main thread.
    """

    def __init__(self, url: str = DEFAULT_WS_URL) -> None:
        self._url = url
        self._callbacks: dict[str, list[Callable]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._socket = None

    # ─── Public API ─────────────────────────────────────────────

    def connect(self) -> None:
        """Start the WebSocket connection in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ws-client")
        self._thread.start()

    def disconnect(self) -> None:
        """Stop the WebSocket connection."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=3)

    def on(self, event_type: str, callback: Callable[[dict], None]) -> None:
        """Register a callback for a specific event type.

        Callbacks are invoked on the GTK main thread (via GLib.idle_add).
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def send(self, message: dict) -> None:
        """Send a JSON message to the WebSocket server."""
        if self._socket:
            try:
                raw = json.dumps(message).encode("utf-8")
                self._ws_send_frame(raw)
            except Exception as e:
                logger.warning("WebSocket send failed: %s", e)

    # ─── Internal Loop ──────────────────────────────────────────

    def _run_loop(self) -> None:
        """Background thread: connect, read frames, dispatch events."""
        while self._running:
            try:
                self._do_connect()
                while self._running and self._socket:
                    data = self._ws_read_frame()
                    if data is None:
                        break
                    self._dispatch(data)
            except Exception as e:
                logger.debug("WebSocket error: %s", e)
            finally:
                self._cleanup()

            if self._running:
                logger.info("WebSocket reconnecting in %ds...", RECONNECT_DELAY)
                time.sleep(RECONNECT_DELAY)

    def _do_connect(self) -> None:
        """Perform WebSocket handshake over raw TCP socket."""
        import base64
        import hashlib
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(self._url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 80
        path = parsed.path or "/"

        sock = socket.create_connection((host, port), timeout=10)
        self._socket = sock

        # WebSocket upgrade handshake
        key = base64.b64encode(b"sigmavault-ws-key!").decode()
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        sock.sendall(handshake.encode())

        # Read response (skip headers)
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket handshake failed")
            response += chunk

        if b"101" not in response.split(b"\r\n")[0]:
            raise ConnectionError(f"WebSocket upgrade rejected: {response[:200]}")

        logger.info("WebSocket connected to %s", self._url)
        self._dispatch_event("connected", {})

    def _ws_read_frame(self) -> Optional[str]:
        """Read a single WebSocket text frame (simplified, no masking)."""
        if not self._socket:
            return None
        try:
            header = self._socket.recv(2)
            if len(header) < 2:
                return None

            opcode = header[0] & 0x0F
            if opcode == 0x8:  # Close
                return None

            length = header[1] & 0x7F
            if length == 126:
                ext = self._socket.recv(2)
                length = int.from_bytes(ext, "big")
            elif length == 127:
                ext = self._socket.recv(8)
                length = int.from_bytes(ext, "big")

            payload = b""
            while len(payload) < length:
                chunk = self._socket.recv(length - len(payload))
                if not chunk:
                    return None
                payload += chunk

            return payload.decode("utf-8")
        except Exception:
            return None

    def _ws_send_frame(self, data: bytes) -> None:
        """Send a masked WebSocket text frame."""
        import os

        frame = bytearray()
        frame.append(0x81)  # FIN + text opcode

        length = len(data)
        if length < 126:
            frame.append(0x80 | length)  # MASK bit set
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(length.to_bytes(2, "big"))
        else:
            frame.append(0x80 | 127)
            frame.extend(length.to_bytes(8, "big"))

        mask = os.urandom(4)
        frame.extend(mask)
        frame.extend(bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

        self._socket.sendall(frame)

    def _cleanup(self) -> None:
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    # ─── Event Dispatch ─────────────────────────────────────────

    def _dispatch(self, raw: str) -> None:
        """Parse JSON message and dispatch to registered callbacks."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.debug("Non-JSON WebSocket frame: %s", raw[:100])
            return

        event_type = msg.get("type", "unknown")
        self._dispatch_event(event_type, msg)

    def _dispatch_event(self, event_type: str, data: dict) -> None:
        """Dispatch event to callbacks on the GTK main thread."""
        callbacks = self._callbacks.get(event_type, []) + self._callbacks.get("*", [])
        for cb in callbacks:
            GLib.idle_add(cb, data)
