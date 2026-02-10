# Desktop UI Launch Guide - MSYS2 Setup

**Status:** ✅ Script Ready | ⏳ MSYS2 Installation Required  
**Date:** February 10, 2026

---

## 🎯 Quick Start (3 Commands)

```powershell
# 1. Install MSYS2 (one-time setup)
winget install MSYS2.MSYS2

# 2. Install GTK4 packages (run in MSYS2 UCRT64 terminal)
.\scripts\launch-desktop-msys2.ps1 -Install

# 3. Launch Desktop UI
.\scripts\launch-desktop-msys2.ps1
```

**Total Time:** ~10-15 minutes (first time)

---

## 📋 Detailed Setup

### Step 1: Install MSYS2

**Option A: Using winget (Recommended)**

```powershell
winget install MSYS2.MSYS2
```

**Option B: Manual Download**

1. Download from: https://www.msys2.org/
2. Run installer (accept default location: `C:\msys64`)
3. Complete installation wizard

**Verify Installation:**

```powershell
Test-Path C:\msys64\ucrt64.exe  # Should return: True
```

---

### Step 2: Install Required Packages

**Option A: Automatic Installation (Recommended)**

```powershell
.\scripts\launch-desktop-msys2.ps1 -Install
```

This will install:

- `mingw-w64-ucrt-x86_64-python` - Python 3.11+
- `mingw-w64-ucrt-x86_64-python-gobject` - PyGObject (GTK bindings)
- `mingw-w64-ucrt-x86_64-gtk4` - GTK4 libraries
- `mingw-w64-ucrt-x86_64-libadwaita` - libadwaita UI toolkit

**Option B: Manual Installation**

```bash
# Open MSYS2 UCRT64 terminal (Start Menu → MSYS2 → MSYS2 UCRT64)
pacman -Syu  # Update package database
pacman -S mingw-w64-ucrt-x86_64-python \
          mingw-w64-ucrt-x86_64-python-gobject \
          mingw-w64-ucrt-x86_64-gtk4 \
          mingw-w64-ucrt-x86_64-libadwaita
```

**Verify Installation:**

```powershell
.\scripts\launch-desktop-msys2.ps1 -Check
```

Expected output:

```
✅ MSYS2 found at: C:\msys64
✅ Found: mingw-w64-ucrt-x86_64-python
✅ Found: mingw-w64-ucrt-x86_64-python-gobject
✅ Found: mingw-w64-ucrt-x86_64-gtk4
✅ Found: mingw-w64-ucrt-x86_64-libadwaita
✅ All required packages installed
✅ All prerequisites satisfied!
```

---

### Step 3: Launch Desktop UI

**Basic Launch:**

```powershell
.\scripts\launch-desktop-msys2.ps1
```

**Custom API Endpoint:**

```powershell
.\scripts\launch-desktop-msys2.ps1 -ApiUrl "http://192.168.1.100:12080/api/v1"
```

**Custom MSYS2 Location:**

```powershell
.\scripts\launch-desktop-msys2.ps1 -MSYS2Path "D:\msys64"
```

---

## ✅ Prerequisites Check

Before launching, ensure:

### 1. Services Running

```powershell
# Check if Engine and API are running
netstat -ano | Select-String ":5000"   # Python Engine
netstat -ano | Select-String ":12080"  # Go API

# Start services if needed
.\scripts\dev-environment-setup.ps1 -Quick
```

### 2. API Health Check

```powershell
Invoke-WebRequest http://127.0.0.1:12080/api/v1/health
```

Expected: `200 OK`

---

## 🚀 Usage Examples

### Development Workflow (Daily)

```powershell
# 1. Start backend services
.\scripts\dev-environment-setup.ps1 -Quick

# 2. Launch Desktop UI
.\scripts\launch-desktop-msys2.ps1

# 3. When done, stop services
.\scripts\dev-environment-setup.ps1 -Kill
```

### Testing Different API Endpoints

```powershell
# Local development
.\scripts\launch-desktop-msys2.ps1 -ApiUrl "http://127.0.0.1:12080/api/v1"

# Remote server
.\scripts\launch-desktop-msys2.ps1 -ApiUrl "http://192.168.1.50:12080/api/v1"

# Custom port
.\scripts\launch-desktop-msys2.ps1 -ApiUrl "http://localhost:8080/api/v1"
```

### Troubleshooting

```powershell
# Check all prerequisites
.\scripts\launch-desktop-msys2.ps1 -Check

# Reinstall packages
.\scripts\launch-desktop-msys2.ps1 -Install

# View detailed error messages
.\scripts\launch-desktop-msys2.ps1 -Verbose
```

---

## 🔧 Script Parameters

| Parameter    | Type   | Default                       | Description              |
| ------------ | ------ | ----------------------------- | ------------------------ |
| `-ApiUrl`    | String | http://127.0.0.1:12080/api/v1 | API endpoint URL         |
| `-MSYS2Path` | String | C:\msys64                     | MSYS2 installation path  |
| `-Check`     | Switch | -                             | Check prerequisites only |
| `-Install`   | Switch | -                             | Install missing packages |

---

## 📊 What Happens When You Launch

1. **Banner Display** - Shows SigmaVault branding
2. **Path Detection** - Finds project root automatically
3. **MSYS2 Verification** - Checks if MSYS2 installed
4. **Package Check** - Verifies GTK4 + PyGObject installed
5. **API Availability** - Tests if Go API is running (warning only)
6. **Path Conversion** - Converts `S:\` to `/s/` for MSYS2
7. **Environment Setup** - Sets `SIGMAVAULT_API_URL`
8. **GTK4 Launch** - Starts Desktop UI in MSYS2 UCRT64
9. **Window Opens** - GTK4 application window appears
10. **Live Connection** - Desktop connects to API for real-time data

---

## 🐛 Troubleshooting

### Issue: "MSYS2 not found"

**Solution:**

```powershell
# Install MSYS2
winget install MSYS2.MSYS2

# Or specify custom location
.\scripts\launch-desktop-msys2.ps1 -MSYS2Path "D:\msys64"
```

---

### Issue: "Missing package: python-gobject"

**Solution:**

```powershell
# Automatic install
.\scripts\launch-desktop-msys2.ps1 -Install

# Or manual
C:\msys64\ucrt64.exe
pacman -S mingw-w64-ucrt-x86_64-python-gobject
```

---

### Issue: "API not available"

**Solution:**

```powershell
# This is a WARNING, not a blocker
# Start the API first:
.\scripts\dev-environment-setup.ps1 -Service api

# Or start all services:
.\scripts\dev-environment-setup.ps1 -Quick
```

---

### Issue: "Window doesn't appear"

**Checklist:**

1. ✅ Run prerequisite check: `.\scripts\launch-desktop-msys2.ps1 -Check`
2. ✅ Check for error messages in terminal output
3. ✅ Verify GTK4 packages: `pacman -Q | grep gtk4`
4. ✅ Test MSYS2 Python: `C:\msys64\ucrt64.exe -c "python --version"`
5. ✅ Check Windows Defender/Firewall blocking

---

### Issue: "ImportError: gi module not found"

**Cause:** PyGObject not installed or wrong Python interpreter

**Solution:**

```bash
# In MSYS2 UCRT64 terminal
pacman -S mingw-w64-ucrt-x86_64-python-gobject

# Verify
python -c "import gi; print('PyGObject OK')"
```

---

## 🎨 Desktop UI Features

Once launched, you'll see:

### Main Window

- **Header Bar** - SigmaVault branding with navigation
- **Sidebar** - System overview, agents, settings
- **Content Area** - Dynamic views (dashboard, agents, logs)
- **Status Bar** - Connection status, real-time updates

### Live Data

- **System Metrics** - CPU, memory, disk (from Engine via API)
- **Agent Status** - All 40 agents with health indicators
- **Real-time Events** - WebSocket updates for system changes
- **Settings** - Configuration management

### Keyboard Shortcuts

- `Ctrl+Q` - Quit application
- `Ctrl+R` - Refresh data
- `Ctrl+,` - Open settings
- `F11` - Toggle fullscreen

---

## 🔄 Development Tips

### Fast Iteration Loop

```powershell
# Terminal 1: Keep services running
.\scripts\dev-environment-setup.ps1 -Quick

# Terminal 2: Launch/relaunch Desktop UI
.\scripts\launch-desktop-msys2.ps1
# (Ctrl+C to stop, up arrow + Enter to restart)
```

### Debug Mode

```powershell
# Set debug logging in Desktop UI
$env:SIGMAVAULT_LOG_LEVEL = 'DEBUG'
.\scripts\launch-desktop-msys2.ps1
```

### GTK Inspector (Developer Tools)

```bash
# In MSYS2 UCRT64 terminal
cd /s/sigmavault-nas-os/src/desktop-ui
export GTK_DEBUG=interactive
export SIGMAVAULT_API_URL='http://127.0.0.1:12080/api/v1'
python main.py
```

This opens GTK Inspector (like browser DevTools for GTK apps).

---

## 📚 Additional Resources

### MSYS2 Documentation

- **Official Site:** https://www.msys2.org/
- **Package Search:** https://packages.msys2.org/
- **Wiki:** https://www.msys2.org/wiki/

### GTK4 Documentation

- **GTK Docs:** https://docs.gtk.org/gtk4/
- **libadwaita:** https://gnome.pages.gitlab.gnome.org/libadwaita/
- **PyGObject:** https://pygobject.readthedocs.io/

### SigmaVault Docs

- **API Reference:** http://127.0.0.1:12080/api/docs (when API running)
- **RPC Protocol:** `docs/WEBSOCKET_PROTOCOL.md`
- **Architecture:** `PHASE_2.2_THREE_SERVICE_INTEGRATION_STATUS.md`

---

## ✨ Success Indicators

You'll know it's working when:

1. ✅ **No errors** in launcher output
2. ✅ **GTK4 window** appears with SigmaVault branding
3. ✅ **System metrics** display (CPU, memory, disk)
4. ✅ **Agent list** populates (40 agents)
5. ✅ **Status bar** shows "Connected" with green indicator
6. ✅ **Real-time updates** - metrics refresh every 5 seconds

---

## 🎉 Next Steps After Launch

Once Desktop UI is running:

1. **Explore Dashboard** - View system overview
2. **Check Agent Status** - Verify all 40 agents healthy
3. **Test Real-time Updates** - Watch metrics change
4. **WebSocket Connection** - Verify event stream working
5. **Settings Panel** - Configure UI preferences
6. **Run Integration Tests** - Verify Desktop ↔ API ↔ Engine flow

---

**Questions?** Check `PHASE_2.2_THREE_SERVICE_INTEGRATION_STATUS.md` for system status and troubleshooting.

**Script Location:** `scripts/launch-desktop-msys2.ps1`  
**Created by:** Elite Agent Collective (@CANVAS + @FLUX + @BRIDGE)  
**Last Updated:** February 10, 2026
