# MSYS2 GTK4 Setup Guide for Phase 2.2

**Date:** February 9, 2026  
**Goal:** Set up GTK4 development environment in MSYS2 for SigmaVault Desktop UI

---

## 📋 Overview

You've chosen the MSYS2 path. This guide will get GTK4, libadwaita, and PyGObject working on Windows using MSYS2's MinGW64 environment.

**Time Estimate:** 10-20 minutes (depending on initial setup and download speeds)

---

## ✅ What You'll Get

After this setup:

- ✅ GTK4 development libraries installed
- ✅ libadwaita framework available
- ✅ Python with PyGObject working
- ✅ Desktop app can launch and run on Windows
- ✅ Phase 2.2 Day 1 can complete on schedule

---

## 🚀 Quick Start (4 Steps)

### Step 1: Open File Explorer to Setup Scripts

```
Navigate to: S:\sigmavault-nas-os\
Look for:
  - SETUP_MSYS2_GTK4.bat (Windows batch file)
  - SETUP_MSYS2_GTK4.sh (Setup script)
```

### Step 2: Run the Setup Script

**Option A: Automated (Recommended)**

```
1. Double-click: SETUP_MSYS2_GTK4.bat
2. Wait for terminal to complete
3. Files will be set up automatically
```

**Option B: Manual (If automated fails)**

```
1. Open: S:\msys64\mingw64.exe (MSYS2 MinGW64 terminal)
2. Run: bash /mnt/s/sigmavault-nas-os/SETUP_MSYS2_GTK4.sh
3. Wait for completion
```

### Step 3: Verify Installation

After setup completes, in the same terminal:

```bash
cd /mnt/s/sigmavault-nas-os/src/desktop-ui
source .venv/Scripts/activate
python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('✅ GTK4 works!')"
```

Expected output: `✅ GTK4 works!`

### Step 4: Launch Desktop App

```bash
cd /mnt/s/sigmavault-nas-os/src/desktop-ui
source .venv/Scripts/activate
python main.py
```

Expected result: GTK4 window opens with 7-page navigation

---

## 🔍 What Each Script Does

### SETUP_MSYS2_GTK4.sh (Main Setup)

**Runs these steps in order:**

1. **Update MSYS2 package manager**

   ```bash
   pacman -Sy --noconfirm
   ```

   - Ensures we have latest package list

2. **Install GTK4 and dependencies**

   ```bash
   pacman -S --noconfirm \
       mingw-w64-x86_64-gtk4 \
       mingw-w64-x86_64-libadwaita \
       mingw-w64-x86_64-gobject-introspection \
       mingw-w64-x86_64-pkg-config \
       mingw-w64-x86_64-python \
       mingw-w64-x86_64-python-pip
   ```

   - `gtk4` — Core GTK4 library
   - `libadwaita` — GNOME design toolkit
   - `gobject-introspection` — Python bindings support
   - `pkg-config` — Package configuration tool
   - `python` — Python interpreter
   - `python-pip` — Package installer

3. **Verify GTK4 installed**

   ```bash
   pkg-config --modversion gtk4
   ```

   - Shows GTK4 version if successful

4. **Navigate to desktop-ui**

   ```bash
   cd /mnt/s/sigmavault-nas-os/src/desktop-ui
   ```

5. **Create Python virtual environment**

   ```bash
   python -m venv .venv
   ```

   - Isolates Python packages per-project

6. **Install dependencies**

   ```bash
   pip install -e .
   ```

   - Installs PyGObject (and pydantic, aiohttp, python-dateutil)
   - `-e` flag enables development mode

7. **Test imports**
   ```bash
   python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk, Adw; print('✅ Success!')"
   ```

---

## 🎯 What's Different from Windows Native Python

| Aspect           | Windows Python    | MSYS2 MinGW64       |
| ---------------- | ----------------- | ------------------- |
| **GTK4 Support** | ❌ None           | ✅ Full             |
| **libadwaita**   | ❌ None           | ✅ Full             |
| **Build Tools**  | ❌ Optional       | ✅ Always included  |
| **PyGObject**    | 🔴 Fails to build | ✅ Builds perfectly |
| **Path Style**   | `S:\folder`       | `/mnt/s/folder`     |
| **Shell**        | cmd/PowerShell    | bash                |

**Key Insight:** MSYS2 MinGW64 is a complete Linux-like environment on Windows, with all the GTK4 development tools that GNOME expects.

---

## ⚠️ Important Notes

### About Python Paths

In MSYS2 MinGW64:

- Windows path: `S:\sigmavault-nas-os\src\desktop-ui`
- Becomes: `/mnt/s/sigmavault-nas-os/src/desktop-ui`

This is transparent — you can use either format and they mean the same thing.

### Virtual Environment Activation

In MSYS2 (bash shell):

```bash
# Don't use: . .venv\Scripts\activate  (Windows style)

# Do use: source .venv/Scripts/activate  (bash style)
```

### Running the App

The GTK4 window will open on your Windows desktop even though it's running in MSYS2. This is normal and expected!

---

## 🐛 Troubleshooting

### Problem: "pacman not found"

**Solution:** You need to be in MSYS2 MinGW64 terminal, not Windows PowerShell. Open: `S:\msys64\mingw64.exe`

### Problem: "bash: SETUP_MSYS2_GTK4.sh not found"

**Solution:** Make sure you're in the right directory:

```bash
cd /mnt/s/sigmavault-nas-os
bash SETUP_MSYS2_GTK4.sh
```

### Problem: "ModuleNotFoundError: No module named 'gi'"

**Solution:** You must activate the venv first:

```bash
source .venv/Scripts/activate
python main.py
```

### Problem: GTK4 window won't open

**Solution:** Make sure you're running in MSYS2 MinGW64 (not native Windows Python). Check:

```bash
which python
# Should show: /mingw64/bin/python
```

### Problem: "Setup is taking too long"

**Solution:** First time pacman downloads can take 5-15 minutes. Be patient! Subsequent runs are much faster.

---

## ✅ Verification Checklist

After running the setup script, verify each step:

```bash
# 1. GTK4 is available
pkg-config --modversion gtk4
# Expected: 4.x.x

# 2. libadwaita is available
pkg-config --modversion libadwaita-1
# Expected: 1.x.x

# 3. Python virtual environment exists
ls -la /mnt/s/sigmavault-nas-os/src/desktop-ui/.venv/Scripts/python.exe
# Expected: File should exist

# 4. PyGObject imports work
source .venv/Scripts/activate
python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk, Adw; print('✅ All imports successful!')"
# Expected: ✅ All imports successful!

# 5. Main app can import
python -c "from sigmavault_desktop.__main__ import main; print('✅ App imports work!')"
# Expected: ✅ App imports work!
```

---

## 🎬 Next Steps After Setup

### Option 1: Quick Test (5 min)

```bash
cd /mnt/s/sigmavault-nas-os/src/desktop-ui
source .venv/Scripts/activate
python main.py
```

**You should see:**

- GTK4 window opens
- Window title: "SigmaVault Settings"
- 7 pages available in navigation
- Status bar showing "Not Connected"

### Option 2: Run Tests (10 min)

```bash
cd /mnt/s/sigmavault-nas-os/src/desktop-ui
source .venv/Scripts/activate
python -m pytest tests/ -v
```

### Option 3: Test API Connection (5 min)

Ensure Go API is still running, then:

```bash
cd /mnt/s/sigmavault-nas-os/src/desktop-ui
source .venv/Scripts/activate
python -c "
import asyncio
from sigmavault_desktop.api.client import SigmaVaultAPIClient

async def test():
    async with SigmaVaultAPIClient() as client:
        resp = await client._request('GET', '/api/v1/health')
        print(f'API Response: {resp}')

asyncio.run(test())
"
```

---

## 📍 Keyboard Shortcuts (Once App Runs)

- **<Ctrl+Q>** — Quit application
- **<Alt+Left>** — Navigate to previous page
- **<Alt+Right>** — Navigate to next page

---

## 💾 Important Locations

| Item               | Location                                          | Notes             |
| ------------------ | ------------------------------------------------- | ----------------- |
| MSYS2 Install      | `S:\msys64\`                                      | Already installed |
| MinGW64 Terminal   | `S:\msys64\mingw64.exe`                           | Click to open     |
| Venv (after setup) | `/mnt/s/sigmavault-nas-os/src/desktop-ui/.venv/`  | Auto-created      |
| Main App Code      | `/mnt/s/sigmavault-nas-os/src/desktop-ui/main.py` | Entry point       |
| Setup Log          | Console output                                    | Watch for errors  |

---

## 🚀 Ready to Begin?

**Choose your path:**

### Path A: Run Automated Setup (Recommended)

```powershell
# In PowerShell or click SETUP_MSYS2_GTK4.bat
S:\sigmavault-nas-os\SETUP_MSYS2_GTK4.bat
```

### Path B: Run Manual Setup

```bash
# In MSYS2 MinGW64 (S:\msys64\mingw64.exe)
bash /mnt/s/sigmavault-nas-os/SETUP_MSYS2_GTK4.sh
```

---

## 📊 Expected Timeline

| Step                 | Time          | Status      |
| -------------------- | ------------- | ----------- |
| 1. Open script       | 1 min         | Quick       |
| 2. pacman update     | 2-3 min       | Automatic   |
| 3. Install packages  | 5-10 min      | Downloading |
| 4. Install PyGObject | 2-3 min       | Compiling   |
| 5. Verify imports    | 1 min         | Testing     |
| **Total**            | **10-18 min** | ✅ Done!    |

After setup completes, app launches in < 5 seconds.

---

## ✨ What You'll Have After This

- ✅ **GTK4 + libadwaita** fully functional on Windows
- ✅ **PyGObject** working perfectly
- ✅ **Desktop app** ready to run
- ✅ **Phase 2.2** can proceed on schedule
- ✅ **Full GNOME development environment** on Windows

---

**Begin setup now! Follow the "Quick Start" section above.** 🚀
