# Phase 2.2 Day 1 Launch - Feb 10, 2026

**Status:** 🟢 READY TO START NOW  
**Phase:** Desktop App Shell (GTK4 + libadwaita)  
**Duration:** 5 days (Feb 10-14)  
**Sprint Goal:** Functional desktop app connected to Go API

---

## 🚀 Current State Assessment

### What Already Exists ✅

- ✅ `src/desktop-ui/` fully scaffolded
- ✅ GTK4 Application class (Adw.Application)
- ✅ Main window with navigation sidebar
- ✅ API client (async httpx/aiohttp wrapper)
- ✅ Page system (Dashboard, Storage, Compression, Agents, Shares, Network, Settings)
- ✅ Widget framework
- ✅ pyproject.toml with dependencies
- ✅ Tests infrastructure

### What Needs Immediate Attention 🟡

- 🟡 Verify Go API is running on port 12080
- 🟡 Test API client connection
- 🟡 Wire pages to actual API methods
- 🟡 Add health status indicator
- 🟡 Create first-run dialog

### What's Not Blocking Phase 2.2 🟢

- ✅ Ryzanstein integration (deferred to Phase 4B)
- ✅ Agent task implementations (currently stubs, ok for UI dev)
- ✅ Compression backend (Phase 2.4)

---

## 📋 Day 1 Immediate Tasks (By EOD Feb 10)

### Task 1: Verify Environment ⏱️ 15 minutes

```powershell
# Check Python environment
python --version
# Expected: Python 3.14.3 or higher

# Check venv
python -m venv --help
# Expected: works

# Check GTK4 + libadwaita
python -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); print('✅ GTK4 + libadwaita available')"

# Check Go API (should be running from previous work)
curl http://localhost:12080/api/v1/health
# Expected: {"status":"healthy","timestamp":"2026-02-10T..."}

# Check project venv
cd s:\sigmavault-nas-os\src\desktop-ui
.venv\Scripts\activate
pip list | grep -E "PyGObject|aiohttp"
```

### Task 2: Start Go API Backend ⏱️ 5 minutes

```powershell
# Terminal 1: Start Go API
cd s:\sigmavault-nas-os\src\api
$env:SIGMAVAULT_ENV='development'
$env:RPC_ENGINE_URL='http://localhost:5000'
go run main.go

# Expected output:
# [INFO] Listening on :12080
# [DEBUG] RPC client connected to localhost:5000
# [DEBUG] Circuit breaker active
```

### Task 3: Test API Client Connection ⏱️ 10 minutes

```powershell
# Terminal 2: Test from desktop-ui directory
cd s:\sigmavault-nas-os\src\desktop-ui
.venv\Scripts\activate

# Run connection test
python -c "
import asyncio
from sigmavault_desktop.api.client import SigmaVaultAPIClient

async def test():
    async with SigmaVaultAPIClient() as client:
        result = await client.health_check()
        print(f'Health check: {result}')

asyncio.run(test())
"

# Expected: Health check: APIResponse(success=True, data={'status': 'healthy', ...}, ...)
```

### Task 4: Launch Desktop App ⏱️ 5 minutes

```powershell
# Terminal 3: Launch app
cd s:\sigmavault-nas-os\src\desktop-ui
python main.py

# Expected output:
# [INFO] SigmaVault Settings started (GTK4 + libadwaita)
# App window appears (1100x700)
# Status indicator shows "Connected" in top bar
```

### Task 5: Verify UI Navigation ⏱️ 10 minutes

- [ ] App window opens without errors
- [ ] Sidebar shows all 7 pages: Dashboard, Storage, Compression, Agents, Shares, Network, Settings
- [ ] Click each page button - page content changes
- [ ] Top status bar shows API connection status
- [ ] Quit button (⌘+Q or menu) closes cleanly

---

## ✅ Day 1 Success Criteria

**MUST HAVE:**

- [ ] App launches without GTK/Adwaita errors
- [ ] Window displays at 1100x700+ resolution
- [ ] API connection returns 200 (health check)
- [ ] Navigation between pages works
- [ ] Status indicator shows "Connected" to API

**SHOULD HAVE:**

- [ ] All 7 pages navigate correctly
- [ ] No console errors
- [ ] App quits cleanly

**NICE TO HAVE:**

- [ ] First page (Dashboard) shows mock data
- [ ] App icon appears in taskbar/Activities

---

## 📊 Architecture Quick Reference

### Current Setup

```
Go API (port 12080)
    │
    └──→ SigmaVaultAPIClient (aiohttp wrapper)
           │
           └──→ Desktop App (GTK4 + libadwaita)
                  │
                  ├── Window (main)
                  ├── Pages
                  │   ├── Dashboard
                  │   ├── Storage
                  │   ├── Compression
                  │   ├── Agents
                  │   ├── Shares
                  │   ├── Network
                  │   └── Settings
                  └── Status Indicators
```

### Key Files

- **Entry:** `main.py` → Creates Adw.Application
- **Window:** `ui/window.py` → 7-page navigation
- **API:** `sigmavault_desktop/api/client.py` → Async HTTP wrapper
- **Pages:** `ui/pages/*.py` → Individual page content

---

## 🔧 Troubleshooting

### "GTK4/Adwaita not found"

```powershell
# Install GTK4 + libadwaita
sudo apt install libgtk-4-1 libadwaita-1-0 gir1.2-gtk-4 gir1.2-adwaita-1

# Or: pip install PyGObject (should auto-detect system libs)
pip install --upgrade PyGObject
```

### "Cannot connect to API on port 12080"

```powershell
# Verify Go API is running
netstat -ano | findstr :12080

# If not running, start it:
cd s:\sigmavault-nas-os\src\api
go run main.go
```

### "ImportError: cannot import name 'SigmaVaultWindow'"

```powershell
# Verify ui/window.py exists and imports are correct
python -c "from ui.window import SigmaVaultWindow; print('✅ Import successful')"

# If error, check PYTHONPATH:
cd s:\sigmavault-nas-os\src\desktop-ui
$env:PYTHONPATH = $PWD
python main.py
```

---

## 📅 Day 2-5 Preview (This Week)

| Day                | Focus                               | Deliverable                            |
| ------------------ | ----------------------------------- | -------------------------------------- |
| **Day 1 (Feb 10)** | App scaffold + API connection       | Functioning GTK4 app connecting to API |
| **Day 2 (Feb 11)** | Dashboard page + mock data          | Dashboard shows system stats           |
| **Day 3 (Feb 12)** | Storage page interface              | ZFS pool display (mock data)           |
| **Day 4 (Feb 13)** | Compression page UI                 | Compression workflow mockup            |
| **Day 5 (Feb 14)** | Polish + launch.desktop integration | App appears in GNOME Activities        |

---

## 🎯 Phase 2.2 Overall Goal

By **Feb 14 EOD**, SigmaVault desktop app should:

1. ✅ Launch from GNOME Activities
2. ✅ Connect to Go API
3. ✅ Display placeholder content for all 7 main pages
4. ✅ Navigate between pages smoothly
5. ✅ Show connection status

**NOT required for Phase 2.2:**

- ❌ Real data from API (wired in Phase 2.3)
- ❌ Compression operations (Phase 2.4)
- ❌ Agent implementations (Phase 2.4)
- ❌ Desktop shortcuts/GNOME integration (Phase 2.5)

---

## 📝 Handoff Notes

**For @CANVAS (UI/UX Lead):**

- Scaffold already complete ✅
- Focus on: Page content, styling, user flow through pages
- Use libadwaita widgets (Adw.ViewStack, Adw.NavigationSplitView)
- Keep in mind: Mobile responsiveness NOT needed for Phase 2.2

**For @ARCHITECT (Architecture Lead):**

- Verify API wiring is correct
- Ensure pages follow MVC pattern (Model→View→Controller)
- Page controllers should call `api_client` methods
- Document page data contracts (what each page receives from API)

**For Integration (Next):**

- Once Phase 2.2 completes, Phase 2.3 (Storage Management) wire real API calls
- Agent tasks stub replacement happens Phase 2.4

---

## 🚀 Launch Checklist

**30 minutes before start:**

- [ ] Go API running on :12080 ✅
- [ ] Desktop UI venv activated ✅
- [ ] Python 3.14.3+ confirmed ✅
- [ ] GTK4 + libadwaita available ✅
- [ ] Terminals ready (API, Desktop, Testing) ✅

**GO TIME:**

- [ ] Start Go API
- [ ] Run `python main.py` from desktop-ui/
- [ ] Verify window appears
- [ ] Click through all pages
- [ ] Test quit action

**After Day 1:**

- [ ] Document any issues found
- [ ] Prepare Day 2 design mockups
- [ ] Identify additional dependencies needed

---

**Phase 2.2 is now LIVE. Begin execution immediately.** ✅
