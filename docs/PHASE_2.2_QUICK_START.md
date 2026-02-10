# Phase 2.2: Desktop App Shell - Development Guide

**Objective:** Build the GTK4+libadwaita desktop management application  
**Duration:** 5 days (Feb 10-14)  
**Owner:** @CANVAS (UI/UX) + @ARCHITECT (Architecture)  
**Status:** Ready to start

---

## Directory Structure

Create the following structure:

```
src/desktop-ui/
├── sigmavault_ui/
│   ├── __init__.py                  # Package init
│   ├── main.py                      # Entry point + App class
│   ├── config.py                    # Configuration + constants
│   ├── api_client.py                # HTTP client to Go API
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py           # Main window shell
│   │   ├── sidebar.py               # Navigation sidebar
│   │   ├── storage_panel.py         # Storage management
│   │   ├── agents_panel.py          # Agent dashboard
│   │   ├── compression_panel.py     # Compression UI
│   │   └── settings_panel.py        # App settings
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── pool_card.py             # ZFS pool display
│   │   ├── agent_status.py          # Agent status widget
│   │   └── compression_progress.py  # Progress indicator
│   ├── styles/
│   │   ├── __init__.py
│   │   └── custom.css               # Custom GTK4 styles
│   └── resources/
│       ├── sigmavault.desktop       # App launcher
│       └── icons/                   # Application icons
├── tests/
│   ├── test_ui.py                   # UI component tests
│   ├── test_api_client.py           # API client tests
│   └── test_integration.py          # Integration tests
├── setup.py                         # Installation script
├── pyproject.toml                   # Project metadata
└── README.md                        # Development guide
```

---

## Week 1 Breakdown

### Day 1 (Feb 10): Scaffolding & API Client

**Goal:** Set up project structure and API communication layer

```python
# src/desktop-ui/sigmavault_ui/main.py
import gi
gi.require_version("Gtk", "4")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib
import asyncio
import logging

from sigmavault_ui.api_client import SigmaVaultAPIClient
from sigmavault_ui.ui.main_window import SigmaVaultMainWindow
from sigmavault_ui.config import Config

logger = logging.getLogger(__name__)

class SigmaVaultApplication(Adw.Application):
    """Main SigmaVault Desktop Application."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = Config()
        self.api_client = SigmaVaultAPIClient(
            base_url=self.config.api_url,
            timeout=self.config.api_timeout
        )
        self.main_window = None

        # Register actions
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        self.connect("activate", self.do_activate)

    def do_activate(self, application):
        """Called when the application is activated."""
        if self.main_window is None:
            self.main_window = SigmaVaultMainWindow(
                application=self,
                api_client=self.api_client
            )

        self.main_window.present()

    def on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutWindow(
            transient_for=self.main_window,
            application_name="SigmaVault NAS OS",
            application_icon="sigmavault-nas",
            developer_name="SigmaVault Team",
            version="0.1.0",
            copyright="© 2026 SigmaVault Project",
            license_type=Gtk.License.AGPL_3_0,
            website="https://github.com/iamthegreatdestroyer/sigmavault-nas-os"
        )
        about.present()

def main(version=None):
    """Entry point for the application."""
    if version is None:
        from sigmavault_ui import __version__
        version = __version__

    app = SigmaVaultApplication(
        application_id="com.sigmavault.nas.app",
        flags=Gio.ApplicationFlags.FLAGS_NONE
    )
    return app.run(None)

if __name__ == "__main__":
    main()
```

**API Client:**

```python
# src/desktop-ui/sigmavault_ui/api_client.py
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SigmaVaultAPIClient:
    """Async HTTP client for SigmaVault API."""

    def __init__(self, base_url: str = "http://localhost:8000",
                 timeout: float = 10.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"X-Client": "sigmavault-desktop-ui"}
        )

    async def health_check(self) -> bool:
        """Check if API server is healthy."""
        try:
            response = await self.client.get("/api/health")
            return response.is_success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_pools(self) -> list:
        """Get list of ZFS pools."""
        try:
            response = await self.client.get("/api/storage/pools")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get pools: {e}")
            return []

    async def get_agents(self) -> Dict[str, Any]:
        """Get agent swarm status."""
        try:
            response = await self.client.get("/api/agents/status")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get agents: {e}")
            return {"status": "unavailable", "agents": []}

    async def submit_compression(self, file_id: str, strategy: str) -> str:
        """Submit file for compression."""
        try:
            response = await self.client.post(
                "/api/compression/submit",
                json={"file_id": file_id, "strategy": strategy}
            )
            return response.json()["job_id"]
        except Exception as e:
            logger.error(f"Failed to submit compression: {e}")
            return None

    async def close(self):
        """Close the client."""
        await self.client.aclose()
```

**Deliverables Day 1:**

- ✅ Project structure in place
- ✅ Main App class working
- ✅ API client connecting to backend
- ✅ Health check functional
- ✅ Tests passing

---

### Day 2 (Feb 11): Main Window & Sidebar

**Goal:** Build GTK4 main window with navigation

```python
# src/desktop-ui/sigmavault_ui/ui/main_window.py
import gi
gi.require_version("Gtk", "4")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio
import logging

logger = logging.getLogger(__name__)

class SigmaVaultMainWindow(Adw.ApplicationWindow):
    """Main SigmaVault application window."""

    def __init__(self, application, api_client, **kwargs):
        super().__init__(**kwargs)
        self.set_application(application)
        self.api_client = api_client

        # Title and size
        self.set_title("SigmaVault NAS OS")
        self.set_default_size(1200, 800)

        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_content(self.main_box)

        # Build UI
        self._build_sidebar()
        self._build_content_area()
        self._apply_styles()
        self.set_current_page("storage")

    def _build_sidebar(self):
        """Build navigation sidebar."""
        sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0
        )
        sidebar.set_size_request(250, -1)
        sidebar.add_css_class("sidebar")

        # Logo/header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        header.set_margin_top(20)
        header.set_margin_start(20)
        header.set_margin_end(20)

        logo = Gtk.Label(label="🛡️ SigmaVault")
        logo.add_css_class("title-3")
        header.append(logo)

        status = Gtk.Label(label="v0.1.0")
        status.add_css_class("subtitle")
        header.append(status)

        sidebar.append(header)

        # Navigation items
        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        nav_box.set_margin_top(30)
        nav_box.set_margin_start(12)
        nav_box.set_margin_end(12)

        pages = [
            ("storage", "💾 Storage", "Manage ZFS pools"),
            ("agents", "🤖 Agents", "Agent dashboard"),
            ("compression", "📦 Compression", "File compression"),
            ("settings", "⚙️ Settings", "Application settings"),
        ]

        for page_id, title, subtitle in pages:
            btn = self._create_nav_button(page_id, title, subtitle)
            nav_box.append(btn)

        sidebar.append(nav_box)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar.append(spacer)

        # System info footer
        footer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )
        footer.set_margin_bottom(20)
        footer.set_margin_start(12)
        footer.set_margin_end(12)

        status_label = Gtk.Label(label="System: Ready")
        status_label.add_css_class("caption")
        footer.append(status_label)

        sidebar.append(footer)
        self.main_box.append(sidebar)

    def _create_nav_button(self, page_id: str, title: str, subtitle: str):
        """Create navigation button."""
        btn = Gtk.Button()
        btn.set_size_request(-1, 80)
        btn.add_css_class("nav-item")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        label = Gtk.Label(label=title)
        label.add_css_class("heading")
        box.append(label)

        desc = Gtk.Label(label=subtitle)
        desc.add_css_class("caption")
        box.append(desc)

        btn.set_child(box)
        btn.connect("clicked", self._on_nav_clicked, page_id)

        return btn

    def _build_content_area(self):
        """Build main content area."""
        self.content_stack = Gtk.Stack()
        self.content_stack.set_hexpand(True)
        self.content_stack.set_vexpand(True)

        # Placeholder pages
        for page in ["storage", "agents", "compression", "settings"]:
            placeholder = Gtk.Label(label=f"[{page.title()} Panel]")
            placeholder.add_css_class("title-2")
            self.content_stack.add_named(placeholder, page)

        self.main_box.append(self.content_stack)

    def _on_nav_clicked(self, button, page_id):
        """Handle navigation button click."""
        self.set_current_page(page_id)

    def set_current_page(self, page_id: str):
        """Switch to specified page."""
        self.content_stack.set_visible_child_name(page_id)

    def _apply_styles(self):
        """Apply custom styles."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/com/sigmavault/nas/styles.css")

        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
```

**Deliverables Day 2:**

- ✅ Main window with proper sizing
- ✅ Sidebar with navigation
- ✅ Content stack for page switching
- ✅ Basic styling applied
- ✅ All four main pages accessible

---

### Day 3 (Feb 12): Desktop Integration & Launcher

**Goal:** Make app integrateintegrate with GNOME, created installer

```python
# Create .desktop launcher
# src/desktop-ui/sigmavault_ui/resources/sigmavault.desktop

[Desktop Entry]
Version=1.0
Type=Application
Name=SigmaVault NAS OS
Comment=Personal AI-powered network storage management
Icon=sigmavault-nas
Exec=sigmavault-ui
Terminal=false
Categories=System;Utility;
Keywords=storage;nas;compression;ai;
```

**Deliverables Day 3:**

- ✅ `.desktop` file for app launcher
- ✅ App appears in GNOME app grid
- ✅ Installation script (setup.py)
- ✅ systemd service unit for auto-start
- ✅ Desktop notifications working

---

### Day 4-5 (Feb 13-14): Panels 1 & 2

**Goal:** Implement first two functional panels (Storage, Agents - stub versions)

```python
# src/desktop-ui/sigmavault_ui/ui/storage_panel.py
# src/desktop-ui/sigmavault_ui/ui/agents_panel.py
```

**Deliverables Week 1:**

- ✅ Complete desktop app shell
- ✅ API communication working
- ✅ All 4 panels accessible (stubs)
- ✅ App launcher in GNOME app grid
- ✅ 100% test coverage for core components
- ✅ Ready for Phase 2.3 (storage management wiring)

---

## Technical Requirements

### Dependencies

```
# pyproject.toml [project.optional-dependencies]
gui = [
    "PyGObject>=3.48.0",
    "pygobject-stubs>=1.0.0",
]
```

### System GTK4 Libraries

```bash
# On Debian/Ubuntu
sudo apt install -y \
    libgtk-4-dev \
    libadwaita-1-dev \
    libglib2.0-dev \
    gobject-introspection \
    libgirepository1.0-dev
```

### Running the App

```bash
cd src/desktop-ui
pip install -e ".[gui]"
sigmoid-ui  # Or: python -m sigmavault_ui.main
```

---

## Testing Strategy

```python
# tests/test_ui.py
import pytest
from sigmavault_ui.main import SigmaVaultApplication

@pytest.mark.asyncio
async def test_app_initialization():
    """Test that app initializes without errors."""
    app = SigmaVaultApplication()
    assert app is not None

@pytest.mark.asyncio
async def test_api_connection():
    """Test API client connects to backend."""
    client = SigmaVaultAPIClient()
    is_healthy = await client.health_check()
    # Will be True if server running, False otherwise

@pytest.mark.asyncio
async def test_get_pools():
    """Test fetching ZFS pools."""
    client = SigmaVaultAPIClient()
    pools = await client.get_pools()
    assert isinstance(pools, list)
```

---

## Success Criteria

✅ **Week 1 (Phase 2.2) Complete When:**

1. App launches without errors
2. API health check passes
3. All 4 main panels accessible via sidebar navigation
4. `.desktop` launcher works in GNOME app grid
5. systemd service auto-starts on boot
6. All unit tests pass (>90% coverage)
7. Documentation updated

---

## Next Week (Phase 2.3) Preview

- Wire Storage Panel to actual ZFS operations
- Implement pool creation/deletion
- Add compression UI to File Manager context menu
- Agent dashboard shows live agent status

---

**Ready to start?** Execute Phase 2.2 development starting Feb 10.
