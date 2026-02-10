# TODAY'S TASKS - Monday Feb 10, 2026 (Phase 2.2 Day 1)

**Status:** 🚀 PHASE 2.2 LIVE  
**Sprint:** Desktop App Shell (5 days)  
**Today's Goal:** App launches, connects to API, navigates between 7 pages

---

## ⏱️ IMMEDIATE ACTIONS (Next 2 Hours)

### Action 1: Verify Go API Ready (5 min)

```powershell
# Terminal 1: Check API is running
curl http://localhost:12080/api/v1/health

# Expected: HTTP 200 + {"status":"healthy",...}
# If not running, start it:
cd s:\sigmavault-nas-os\src\api
go run main.go
```

### Action 2: Activate Desktop UI Environment (5 min)

```powershell
# Terminal 2: Setup desktop-ui env
cd s:\sigmavault-nas-os\src\desktop-ui
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip setuptools
pip install -e .
```

### Action 3: Verify GTK4 + libadwaita (10 min)

```powershell
# Test GTK4/Adwaita availability
python -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); print('✅ Ready')"

# If error: install deps
pip install PyGObject --upgrade
```

### Action 4: Launch Desktop App (5 min)

```powershell
# Terminal 3: Run app
cd s:\sigmavault-nas-os\src\desktop-ui
.venv\Scripts\activate
python main.py

# Expected:
# - Window opens (1100x700)
# - Sidebar shows 7 pages
# - Status bar green = "Connected"
# - No errors
```

### Action 5: Verify Full Workflow (10 min)

- [ ] Click menu → Dashboard (page loads)
- [ ] Click Storage (page changes, no errors)
- [ ] Click Compression (page changes)
- [ ] Click Agents (page changes)
- [ ] Click Shares (page changes)
- [ ] Click Network (page changes)
- [ ] Click Settings (page changes)
- [ ] Press Ctrl+Q (app quits cleanly)

---

## 📊 By EOD Today (Feb 10)

**Success Criteria (ALL MUST BE TRUE):**

- [ ] Go API running on :12080
- [ ] Desktop app launches without errors
- [ ] Window displays 1100x700+ resolution
- [ ] 7 pages navigate correctly
- [ ] Status indicator shows "Connected"
- [ ] App quits cleanly
- [ ] No GTK import errors in console

**If ALL ✅, Phase 2.2 Day 1 = SUCCESS**

---

## 🔧 Troubleshooting Quick Fixes

### "ModuleNotFoundError: No module named 'gi'"

```powershell
pip install PyGObject --upgrade --force-reinstall
```

### "ImportError: Libadwaita not found"

```powershell
# Ensure libadwaita system package is installed
# Or update PyGObject
pip install PyGObject --upgrade
```

### "Cannot connect to API on :12080"

```powershell
# Check if API is running
netstat -ano | findstr :12080

# If not, start it
cd s:\sigmavault-nas-os\src\api
$env:SIGMAVAULT_ENV='development'
$env:RPC_ENGINE_URL='http://localhost:5000'
go run main.go
```

### "Window doesn't appear / blank screen"

```powershell
# Try with GTK debug
$env:GTK_DEBUG='all'
python main.py 2>&1 | tail -20
```

---

## 📝 Documentation to Review

**Before Starting:**

1. [PHASE_2.2_LAUNCH.md](PHASE_2.2_DAY1_LAUNCH.md) - Full Day 1 guide
2. [PHASE_2.2_SPRINT_PLAN.md](docs/PHASE_2.2_SPRINT_PLAN.md) - 5-day breakdown
3. [PHASE_2.2_QUICK_START.md](docs/PHASE_2.2_QUICK_START.md) - Code samples

**After Day 1:**

1. Day 2 preparation (Dashboard page design)
2. Phase 2.3 preview (Storage API wiring)

---

## 💬 Questions / Blockers?

**If Go API won't start:**

```powershell
cd s:\sigmavault-nas-os\src\api
go mod tidy
go mod download
go run main.go
```

**If desktop app won't launch:**

```powershell
# Check imports
python -c "from sigmavault_desktop.app import SigmaVaultApplication; print('✅')"

# Check window
python -c "from ui.window import SigmaVaultWindow; print('✅')"

# Full traceback
python main.py 2>&1
```

**If pages don't navigate:**

- Check `ui/window.py` line 100+ for page definitions
- Ensure all 7 pages are imported
- Check sidebar button click handlers

---

## 🎯 Next Checkpoint

**Tomorrow (Feb 11, 9 AM):**

- [ ] Dashboard page has 5+ status cards
- [ ] Mock data source working
- [ ] Status updates when page is clicked
- [ ] No errors

---

**START NOW. Phase 2.2 is LIVE.** 🚀
