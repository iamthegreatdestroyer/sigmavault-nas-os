# Immediate Action Plan - Feb 10 Start (Phase 2.2)

**Status:** Day 1 Foundation Fix Complete ✅  
**Next Phase:** Desktop App Shell (Phase 2.2)  
**Duration:** 5 days (Feb 10-14)  
**Ready to Start:** YES - All blockers resolved

---

## 🎯 Why We Start Now

**What's Done:**

- ✅ Architecture validated (C4 models, ADRs, sequence diagrams)
- ✅ Roadmap created (4-phase breakdown with metrics)
- ✅ Environments verified (Python 3.14.3, Go 1.24.13, Debian 13 ready)
- ✅ Dependencies locked (all 15 core dependencies verified)
- ✅ Blockers identified & resolved (submodule repos non-blocking via fallback)

**What's Blocking Phase 2.2 Start:** NOTHING ✅

**What's Blocking v1.0 Release:** Agent task implementations (Phase 2.4) - but that's 3 weeks away

---

## 📍 Monday Feb 10 - Day 1 (Desktop App Scaffold)

### Team: @CANVAS (UI/UX) + @ARCHITECT (Architecture)

### Deliverables

**By EOD Feb 10:**

1. ✅ `src/desktop-ui/` directory structure created
2. ✅ `SigmaVaultApplication` class working (GTK4 boilerplate)
3. ✅ `SigmaVaultAPIClient` functional (HTTP to Go API)
4. ✅ Basic main window displaying
5. ✅ Dev environment set up (`pip install -e ".[gui]"` working)

### Commands to Execute

```bash
# 1. Create project structure
cd s:\sigmavault-nas-os\src
mkdir desktop-ui
cd desktop-ui

# 2. Create directory scaffold
mkdir -p sigmavault_ui/{ui,widgets,styles,resources/icons}
mkdir -p tests
touch sigmavault_ui/__init__.py
touch tests/__init__.py

# 3. Create initial files
# See PHASE_2.2_QUICK_START.md for code samples

# 4. Set up dev environment
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install --upgrade pip
pip install pyproject-toml build
# Install GUI deps: PyGObject 3.48.0+, gtk-4, libadwaita-1

# 5. Test basic app
python -m sigmavault_ui.main
```

### Code to Create (Priority: Highest First)

**File 1:** `sigmavault_ui/main.py` (200 lines)

- GTK4 Application class
- Basic window setup
- Health check to API

**File 2:** `sigmavault_ui/api_client.py` (150 lines)

- Async HTTP client
- Methods: health_check(), get_pools(), get_agents(), submit_compression()

**File 3:** `sigmavault_ui/ui/main_window.py` (300 lines)

- Main window with sidebar + content stack
- 4 panel navigation buttons
- Basic styling

**File 4:** `setup.py` + `pyproject.toml` for installation

### Success Criteria (EOD Feb 10)

- [ ] App launches without errors
- [ ] Window displays (800x600 minimum)
- [ ] API health check passes
- [ ] Unit tests pass (>80% coverage for core)

---

## 📍 Tuesday Feb 11 - Day 2 (Window Shell)

### Deliverables

1. ✅ Main window rendering properly
2. ✅ Sidebar with 4 navigation items
3. ✅ Content stack switching between pages
4. ✅ Basic CSS styling applied

### Code to Create

- Complete `ui/main_window.py` with full window layout
- Add `ui/sidebar.py` for navigation logic
- Create `styles/custom.css` for GTK4 styling

### Success Criteria (EOD Feb 11)

- [ ] All 4 pages accessible via sidebar clicks
- [ ] Window resizable and responsive
- [ ] Sidebar visible and functional
- [ ] Basic styling applied (headings, spacing)

---

## 📍 Wednesday Feb 12 - Day 3 (GNOME Integration)

### Deliverables

1. ✅ `.desktop` launcher file created
2. ✅ App registered with GNOME
3. ✅ systemd service unit file
4. ✅ App installable via `pip install -e .`

### Files to Create

```
sigmavault_ui/resources/sigmavault.desktop
sigmavault_ui/resources/sigmavault.service (systemd)
INSTALL.md (installation instructions)
```

### Commands

```bash
# Test .desktop file
# xdg-open sigmavault.desktop (Linux)

# Test systemd service
# systemctl enable --user sigmavault.service
```

### Success Criteria (EOD Feb 12)

- [ ] App appears in GNOME app grid
- [ ] App launches from Activities menu
- [ ] systemd service file valid

---

## 📍 Thursday Feb 13 - Day 4 (Panel 1: Storage)

### Deliverables

1. ✅ Storage panel UI skeleton
2. ✅ Connect to `/api/storage/pools` endpoint
3. ✅ Display pool list (stub data if API not ready)

### Code to Create

- `ui/storage_panel.py` (250+ lines)
- `widgets/pool_card.py` (100 lines)

### Success Criteria (EOD Feb 13)

- [ ] Storage panel displays
- [ ] Fetches and shows pools from API (or graceful fallback)
- [ ] Pool card components rendering

---

## 📍 Friday Feb 14 - Day 5 (Panel 2: Agents)

### Deliverables

1. ✅ Agents panel UI skeleton
2. ✅ WebSocket connection to agent stream
3. ✅ Display agent status updates

### Code to Create

- `ui/agents_panel.py` (250+ lines)
- `widgets/agent_status.py` (150 lines)
- WebSocket client integration

### Success Criteria (EOD Feb 14)

- [ ] Agents panel displays
- [ ] Shows agent names and status
- [ ] Updates via WebSocket stream (if API ready)

---

## 🎓 Code Reference

### GTK4 Boilerplate (Minimal Working Example)

```python
import gi
gi.require_version("Gtk", "4")
from gi.repository import Gtk, Adw

class MyApp(Adw.Application):
    def do_activate(self):
        window = Adw.ApplicationWindow(application=self)
        window.set_title("My App")
        window.set_default_size(800, 600)
        window.present()

app = MyApp()
app.run(None)
```

### API Client (Working Example)

```python
import httpx
import asyncio

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.client = httpx.AsyncClient(base_url=base_url)

    async def get_data(self, endpoint):
        response = await self.client.get(endpoint)
        return response.json()

async def main():
    client = APIClient()
    pools = await client.get_data("/api/storage/pools")
    print(pools)

asyncio.run(main())
```

---

## 📋 Prerequisites Checklist

Before starting Feb 10:

- [ ] Python 3.14.3+ installed and verified
- [ ] Go 1.24.13+ installed and verified
- [ ] Git submodules checked (expected: unavailable, OK)
- [ ] VS Code + Copilot agents available
- [ ] Go API server can start: `cd src/api; go run main.go`
- [ ] Python environment ready: `python --version` shows 3.14.3+

### If Any Prerequisites Fail

→ Reference [docs/FOUNDATION_FIX_DAY1_STATUS.md](docs/FOUNDATION_FIX_DAY1_STATUS.md) for troubleshooting

---

## 🚨 Critical Path Items

### MUST COMPLETE BY EOD FEB 14:

1. App launches without errors
2. Main window visible with 4 sidebar items
3. API client connects to health endpoint
4. All 4 panels accessible
5. Unit tests passing (>80%)

### NICE TO HAVE (Not critical for Phase 2.3):

- Full GNOME integration
- systemd service
- Production-grade error handling

### BLOCKERS FOR NEXT PHASE (Feb 15+):

- API server must have `/api/storage/pools` endpoint
- Go API server must be running on port 8000
- Python RPC engine must be running on port 9000

---

## 📊 Success Metrics

| Metric                | Target     | Threshold  |
| --------------------- | ---------- | ---------- |
| App launch time       | <2 seconds | <5 seconds |
| API response time     | <500ms     | <1000ms    |
| Unit test coverage    | 90%+       | 80%+       |
| Lines of code (phase) | 1500       | 1200       |
| Bugs found in testing | <5         | <10        |

---

## 📞 Checkpoint Meetings

- **Monday EOD:** Review Day 1 deliverables (app scaffolding)
- **Tuesday EOD:** Review Day 2 deliverables (window/sidebar)
- **Wednesday EOD:** Review Day 3 deliverables (GNOME integration)
- **Thursday EOD:** Review Day 4 deliverables (storage panel)
- **Friday EOD:** Review Day 5 deliverables + plan Phase 2.3

---

## 🔄 Handoff to Phase 2.3 (Feb 15+)

**When:** Monday Feb 15  
**Owner:** @ARCHITECT (Storage Systems)  
**Deliverable:** ZFS pool management backend

### What Phase 2.3 Needs from Phase 2.2:

1. Working desktop UI that connects to API
2. Storage panel ready for ZFS integration
3. API server accepting requests on port 8000

### What Phase 2.3 Will Provide:

1. `/api/storage/pools` endpoint (list pools)
2. `/api/storage/datasets` endpoint (list datasets)
3. `/api/storage/create` endpoint (create dataset)

---

## 🎯 Final Note

**This is achievable in 5 days because:**

1. ✅ All blockers removed
2. ✅ Dependencies verified
3. ✅ Architecture finalized
4. ✅ Code samples provided (PHASE_2.2_QUICK_START.md)
5. ✅ Team is ready

**Start time:** Monday Feb 10, 9:00 AM  
**Location:** Your favorite IDE

**Let's build something great.**

---

**Questions?** See [EXECUTIVE_STATUS_CURRENT.md](EXECUTIVE_STATUS_CURRENT.md) for context.
