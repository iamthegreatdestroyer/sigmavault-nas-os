\*\*# SigmaVault NAS OS — Next Steps Master Action Plan v4

**Date:** February 7, 2026
**Author:** Project Audit & Planning Session
**Scope:** Personal-use development — desktop-first, GNOME-native approach
**Previous Plans:** v1 (Feb 2) → v3 (Feb 7, audit-grounded) → **v4 (desktop pivot)**
**Key Change:** Web UI phase eliminated — replaced with native GNOME desktop integration

---

## What Changed: v3 → v4 [REF:WC-000]

The v3 plan called for building a React 19 + Tailwind 4 web dashboard (`[REF:PH1-004]`). That was wrong. SigmaVault NAS OS is a **desktop operating system** running GNOME on Debian, not a web appliance. The management interface should be native to the desktop environment.

**Removed:**

- `src/webui/` (React 19 + TypeScript + TailwindCSS)
- All Vite build tooling, pnpm dependencies, browser-based dashboard
- `sigmavault-webui.service` (nginx serving React)
- Web UI CI/CD build jobs

**Added:**

- `src/desktop-ui/` (GTK4 + libadwaita + PyGObject)
- Native GNOME integration via Nautilus, GNOME Disks, system tray
- Desktop notifications for agent events
- `.desktop` launcher file for app grid integration

**Impact on Timeline:**

- Net time savings: ~3-5 days (GNOME provides file manager, disk tools, system monitor for free)
- Reduced dependencies: No Node.js, no pnpm, no browser runtime
- Simpler deployment: Single Python package instead of bundled SPA + nginx

---

## Audit Summary: Where Things Actually Stand [REF:AS-001]

### What's Built & Working

| Component                              | Status                   | Notes                                                                                                               |
| -------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| **Go API Server** (`src/api/`)         | ✅ Scaffolded & compiles | Fiber-based, handlers for agents/compression/storage/health/system, WebSocket hub, circuit breaker, auth middleware |
| **Python RPC Engine** (`src/engined/`) | ✅ Scaffolded & runs     | FastAPI + aiohttp hybrid, gRPC server, 40-agent swarm (simulated), agent registry, scheduler, recovery              |
| **Agent Swarm** (40 agents)            | ⚠️ Simulated only        | All 40 defined with tiers/specialties, task queue works, but `_execute_task` is a 0.1s sleep stub                   |
| **Elite Agent Collective** (10 core)   | ⚠️ Stub implementations  | BaseAgent lifecycle works, registry works, API integration works. No real AI logic.                                 |
| **Compression Bridge**                 | ⚠️ Falls back to zlib    | Designed to import EliteSigma-NAS, but submodules not cloned — uses `StubCompressionEngine`                         |
| **WebSocket Hub**                      | ✅ Functional            | Event system, circuit breaker, handler                                                                              |
| **CI/CD Pipeline** (`ci.yml`)          | ✅ Well-structured       | 5-stage pipeline: test → security → build → docker → release. Multi-arch.                                           |
| **GitHub Agents** (40 `.agent.md`)     | ✅ Complete              | Rich Copilot agent definitions for all 40 agents                                                                    |
| **Live-Build ISO Config**              | ⚠️ Minimal               | Package list exists, auto/config exists, but no desktop environment, no hooks, no installer                         |
| **Git Submodules**                     | ❌ Not cloned            | `.gitmodules` references 3 repos but `submodules/` directory doesn't exist locally                                  |
| **Documentation**                      | ✅ Extensive             | 30+ docs covering phases, reports, protocols                                                                        |

### What's Aspirational (Not Yet Real)

- 90%+ AI compression (currently zlib fallback)
- Quantum-resistant encryption (referenced, nothing implemented)
- PhantomMesh VPN (submodule not cloned, no integration code)
- MNEMONIC memory (stubs exist, no real retrieval/storage)
- Self-healing systems (circuit breaker only)
- Bootable ISO (config exists, never built)
- Any actual NAS functionality (no ZFS/storage management code)
- **Any user interface at all** (Web UI was empty shell; now replaced by desktop approach)

### Critical Gap Analysis

| Gap                              | Impact                                    | Effort                                  |
| -------------------------------- | ----------------------------------------- | --------------------------------------- |
| **No management UI**             | Can't interact with NAS-specific features | MEDIUM — GTK panel + GNOME integration  |
| **Submodules not initialized**   | Compression/VPN/Agents are stubs          | LOW — `git submodule update --init`     |
| **Agent tasks are no-ops**       | Core value proposition doesn't work       | HIGH — need real task implementations   |
| **No actual storage management** | It's a "NAS OS" that can't manage storage | HIGH — fundamental feature gap          |
| **No GNOME desktop in ISO**      | Can't boot to a usable desktop            | MEDIUM — live-build package list update |
| **ISO never built**              | Can't install/distribute                  | MEDIUM — live-build config needs work   |

---

## Strategic Reset: Desktop-First Philosophy [REF:SP-002]

### Core Philosophy

```
v1:  "Production-ready autonomous system by Q3 2026"
v3:  "Bootable, usable personal NAS with real AI features by April 2026"
v4:  "Bootable GNOME desktop that IS a NAS, with native AI-powered management"
```

### What "Desktop NAS OS" Actually Means

SigmaVault is not a headless NAS appliance with a web admin panel. It's a **full Debian desktop** that happens to have deeply integrated NAS capabilities. Think of it like how Ubuntu Desktop includes "Files" (Nautilus) — SigmaVault includes an AI-powered storage management panel as a first-class desktop application.

**GNOME provides for free:**

- **Nautilus** → File browsing, drag-and-drop, network shares
- **GNOME Disks** → Physical disk management, SMART monitoring
- **GNOME System Monitor** → CPU/RAM/process monitoring
- **Settings** → Network, users, power, displays
- **GNOME Files** → SMB/NFS browsing via GVfs
- **Desktop notifications** → Alert infrastructure
- **D-Bus** → Inter-process communication
- **GLib/Gio** → System integration APIs

**SigmaVault needs to build:**

- **SigmaVault Settings** → GTK4 app for ZFS pools, compression, agents, shares, VPN
- **System tray indicator** → Quick status and actions
- **Desktop notifications** → Agent events, compression results, disk health
- **Systemd services** → Auto-start API + engine on boot

### Priority Stack (What matters for personal use)

1. **Can I boot it?** → GNOME desktop with SigmaVault pre-installed
2. **Can I manage storage?** → ZFS management via native GTK app
3. **Can I compress files?** → Right-click compress, AI-powered
4. **Can agents do anything?** → Real tasks triggered from desktop app
5. **Can I access it remotely?** → VPN + optional SSH

---

## Phase 0: Foundation Fix (1-2 Days) [REF:PH0-003]

**Goal:** Fix broken foundations so everything builds on solid ground.
**Automation:** 100% — all scriptable commands.

### 0.1 Clone Submodules

```bash
cd S:\sigmavault-nas-os
git submodule update --init --recursive
```

### 0.2 Verify Python Environment

```bash
cd src/engined
pip install -e ".[test]" --break-system-packages
python -m pytest tests/ -v
```

### 0.3 Verify Go Build

```bash
cd src/api
go mod tidy
go build -o sigmavault-api .
go test ./... -v -short
```

### 0.4 Remove Dead Web UI Scaffolding

```bash
# Archive the empty webui directory (keep for reference, remove from active dev)
git rm -r src/webui/
git commit -m "Remove empty web UI scaffolding — replaced by desktop integration (v4 plan)"
```

### 0.5 Create Desktop UI Directory Structure

```bash
mkdir -p src/desktop-ui/{ui/pages,ui/widgets,api,resources}
touch src/desktop-ui/{__init__.py,main.py,sigmavault-settings.desktop}
```

### 0.6 Bootstrap Script

Create `scripts/bootstrap.sh` / `scripts/bootstrap.ps1`:

```bash
#!/bin/bash
set -e
echo "=== SigmaVault Bootstrap ==="
git submodule update --init --recursive
cd src/engined && pip install -e ".[test]" && cd ../..
cd src/api && go mod tidy && go build -o sigmavault-api . && cd ../..
pip install pygobject --break-system-packages  # GTK4 bindings
echo "=== Bootstrap Complete ==="
```

**Success criteria:** All components build. Submodules exist. Desktop UI directory structure ready.

---

## Phase 1: Desktop Management Application (1-2 Weeks) [REF:PH1-004-R]

**Goal:** Build a native GTK4 SigmaVault Settings application that integrates with GNOME.
**Automation:** 60% — GTK boilerplate automatable, UI polish requires iteration.
**Technology:** Python 3 + PyGObject + GTK4 + libadwaita

### Why GTK4 + Python (Not Go)

- The Python RPC engine already exists — the desktop app can share code and directly import agent/compression modules
- PyGObject is mature, well-documented, and the standard for GNOME app development
- libadwaita provides modern GNOME design language (adaptive layouts, header bars, preference pages)
- Faster iteration than Go + gotk4 (which has fewer examples and rougher edges)
- GTK Inspector for live debugging

### 1.1 Application Architecture

```
src/desktop-ui/
├── main.py                          # Application entry point (Adw.Application)
├── sigmavault-settings.desktop      # .desktop launcher for GNOME app grid
├── com.sigmavault.Settings.gschema.xml  # GSettings schema
├── ui/
│   ├── window.py                    # Main application window (Adw.ApplicationWindow)
│   ├── pages/
│   │   ├── dashboard.py             # Overview: agent summary, storage capacity, system health
│   │   ├── storage.py               # ZFS pools, datasets, disks, SMART data
│   │   ├── compression.py           # Compression jobs, settings, file type strategies
│   │   ├── agents.py                # 40 agent cards with status, task assignment
│   │   ├── shares.py                # SMB/NFS share management
│   │   ├── network.py               # VPN status, peer management (Phase 6)
│   │   └── settings.py              # App preferences, service control
│   └── widgets/
│       ├── agent_card.py            # Single agent status widget (Adw.ActionRow style)
│       ├── pool_widget.py           # ZFS pool capacity bar + health indicator
│       ├── job_row.py               # Compression job progress row
│       ├── metric_gauge.py          # CPU/RAM/Disk circular gauge
│       └── status_indicator.py      # Service online/offline dot
├── api/
│   ├── client.py                    # HTTP client for Go API (aiohttp or requests)
│   ├── websocket.py                 # WebSocket client for real-time events
│   └── dbus_service.py              # D-Bus interface for system tray + notifications
├── resources/
│   ├── icons/                       # App icons (scalable SVG)
│   ├── sigmavault.gresource.xml     # GResource bundle definition
│   └── style.css                    # Custom GTK CSS overrides (if any)
└── meson.build                      # Build system (standard for GNOME apps)
```

### 1.2 Main Window Layout

Using libadwaita's `Adw.NavigationSplitView` (sidebar + content pattern):

```
┌─────────────────────────────────────────────────────┐
│  SigmaVault Settings                    ─  □  ✕     │
├──────────────┬──────────────────────────────────────┤
│              │                                       │
│  Dashboard   │   [Active Page Content]               │
│  Storage     │                                       │
│  Compression │   For Dashboard:                      │
│  Agents      │   ┌─────────┐ ┌─────────┐            │
│  Shares      │   │ Agents  │ │ Storage │            │
│  Network     │   │ 38 idle │ │ 2.1 TB  │            │
│  Settings    │   │  2 busy │ │ free    │            │
│              │   └─────────┘ └─────────┘            │
│              │                                       │
│              │   ┌─────────────────────┐            │
│              │   │ Recent Compression  │            │
│              │   │ ████████░░ 82%     │            │
│              │   └─────────────────────┘            │
│              │                                       │
├──────────────┴──────────────────────────────────────┤
│  ● API Connected  ● Engine Running  40 agents idle  │
└─────────────────────────────────────────────────────┘
```

### 1.3 Key Integration Points

**Go API Communication:**

- The GTK app is a client of the same REST/WebSocket endpoints the web UI would have used
- `GET /health`, `GET /api/v1/agents`, `POST /api/v1/agents/:id/task`, etc.
- Use Python `requests` (sync) or `aiohttp` (async with GLib main loop integration)

**WebSocket for Real-Time:**

- Connect to `ws://localhost:3000/ws` for live agent status, compression progress, disk events
- Bridge WebSocket events to GTK via `GLib.idle_add()` to update UI on main thread

**Desktop Notifications:**

- `Gio.Notification` for GNOME notification center integration
- Events: compression complete, agent task finished, disk health warning, scrub complete
- Actions on notifications: "View Results", "Open Storage", "Dismiss"

**System Tray / Panel Indicator:**

- `libappindicator3` or GNOME Shell extension for persistent status
- Shows: swarm status (idle/busy), active compression jobs, quick actions
- Menu: Start/Stop Services, Open Settings, Quick Compress

**GSettings:**

- Persist user preferences: default compression level, auto-scrub schedule, notification preferences
- Schema installed to `/usr/share/glib-2.0/schemas/`

### 1.4 Desktop File & Installation

`sigmavault-settings.desktop`:

```ini
[Desktop Entry]
Name=SigmaVault Settings
Comment=AI-Powered NAS Management
Exec=sigmavault-settings
Icon=com.sigmavault.Settings
Type=Application
Categories=System;Settings;
Keywords=NAS;Storage;ZFS;Compression;
```

Installed to `/usr/share/applications/` — appears in GNOME app grid and Activities search.

### 1.5 Nautilus Integration (Right-Click Compress)

Create a Nautilus extension (`python3-nautilus`) that adds:

- Right-click → "Compress with SigmaVault" on any file/folder
- Submits compression job to Go API
- Shows desktop notification on completion

```python
# nautilus-sigmavault.py → /usr/share/nautilus-python/extensions/
from gi.repository import Nautilus, GObject
import requests

class SigmaVaultExtension(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, files):
        item = Nautilus.MenuItem(name="SigmaVault::Compress",
                                label="Compress with SigmaVault",
                                tip="AI-powered compression")
        item.connect("activate", self._compress, files)
        return [item]

    def _compress(self, menu, files):
        for f in files:
            path = f.get_location().get_path()
            requests.post("http://localhost:3000/api/v1/compression/compress",
                         json={"path": path})
```

### 1.6 Development Workflow

```bash
# Run in development mode (hot reload with GTK Inspector)
cd src/desktop-ui
GTK_DEBUG=interactive python main.py

# The Go API and Python engine must be running:
cd src/api && ./sigmavault-api &
cd src/engined && python -m engined.main &
```

### Automation Strategy

Use Copilot Agent Mode:

```
@CANVAS Create the GTK4 + libadwaita SigmaVault Settings application.
Use PyGObject with Adw.NavigationSplitView for sidebar layout.
Connect to Go API at localhost:3000. Pages: Dashboard, Storage, Compression, Agents.
```

**Success criteria:**

- Launch "SigmaVault Settings" from GNOME app grid
- Dashboard shows live agent status from Go API
- Sidebar navigation works across all pages
- Desktop notification fires on test event

---

## Phase 2: Real Storage Management (1-2 Weeks) [REF:PH2-005]

**Goal:** Make it actually manage NAS storage — the core purpose of the project.
**Automation:** 60% — ZFS commands are scriptable, GTK pages need design.

### 2.1 Storage Backend (Go API)

Add real storage management to `src/api/internal/handlers/storage.go`:

```
Endpoints:
  GET  /api/v1/storage/disks                  → List physical disks (lsblk/smartctl)
  GET  /api/v1/storage/pools                  → List ZFS pools
  POST /api/v1/storage/pools                  → Create ZFS pool
  DEL  /api/v1/storage/pools/:name            → Destroy pool
  GET  /api/v1/storage/pools/:name/datasets   → List datasets
  POST /api/v1/storage/pools/:name/datasets   → Create dataset
  GET  /api/v1/storage/pools/:name/status     → Pool health/scrub status
  POST /api/v1/storage/pools/:name/scrub      → Initiate scrub
  GET  /api/v1/storage/shares                 → List SMB/NFS shares
  POST /api/v1/storage/shares                 → Create share
```

Implementation: Shell out to `zpool`, `zfs`, `smbcontrol`, etc. with structured JSON output parsing.

### 2.2 Desktop Storage Page

The Storage page in SigmaVault Settings replaces what would have been a web dashboard:

- **Disks tab:** Visual disk inventory with SMART health indicators (Adw.PreferencesGroup)
- **Pools tab:** ZFS pool management — create/destroy/scrub with confirmation dialogs
- **Datasets tab:** Browse datasets, set properties (compression, quota, mountpoint)
- **Shares tab:** SMB/NFS share management with Adw.EntryRow for config

**GNOME Disks Integration:**

- For physical disk operations (partitioning, formatting), launch GNOME Disks via `Gio.AppInfo`
- SigmaVault handles only ZFS-layer operations (pools, datasets, shares)
- This avoids duplicating what GNOME already does well

### 2.3 File Management

Nautilus handles file browsing natively. SigmaVault enhances it:

- ZFS datasets mounted to `/srv/sigmavault/` appear in Nautilus sidebar via bookmark
- SMB/NFS shares visible via GVfs (GNOME's virtual filesystem layer)
- Right-click compression (Phase 1 Nautilus extension) works on any file

**No custom file browser needed** — this is a major scope reduction from the web UI approach.

**Success criteria:** Can create a ZFS pool, create a dataset, see it in Nautilus, upload a file via drag-and-drop.

---

## Phase 3: Real Compression Integration (1 Week) [REF:PH3-006]

**Goal:** Connect EliteSigma-NAS compression engine for real AI-powered compression.
**Automation:** 85% — mostly wiring existing code.

### 3.1 Activate Submodule Integration

Once submodules are cloned (Phase 0), the `CompressionBridge` in `src/engined/engined/compression/bridge.py` should automatically find and import `nas_core.compression_engine`. If EliteSigma-NAS has real compression code, this is primarily a dependency resolution task.

### 3.2 Wire Compression to Desktop

Two entry points for users:

**1. Right-click in Nautilus** (from Phase 1 extension):

- Select file → Right-click → "Compress with SigmaVault"
- Nautilus extension POSTs to Go API
- Desktop notification on completion with "View" action

**2. Compression page in SigmaVault Settings:**

- Drag files onto the compression page
- Configure: algorithm, level, strategy per file type
- Job queue with progress bars (Adw.ActionRow with GtkProgressBar)
- Historical stats: ratio per file type, storage savings

### 3.3 Compression Pipeline

```
User action (Nautilus or Settings app)
  → POST /api/v1/compression/compress {path, options}
  → Go API enqueues job
  → Python engine runs CompressionBridge
  → WebSocket emits progress events
  → GTK app receives via websocket.py → GLib.idle_add() → updates UI
  → Gio.Notification on completion
```

### 3.4 Fallback Strategy

If EliteSigma-NAS isn't fully functional, enhance `StubCompressionEngine`:

- Add zstd (much better than zlib)
- Per-filetype strategy selection
- Log what the full engine _would_ do

**Success criteria:** Right-click a file in Nautilus → "Compress with SigmaVault" → see real compression happen → desktop notification with ratio.

---

## Phase 4: Agent Intelligence (2 Weeks) [REF:PH4-007]

**Goal:** Make at least 10 agents do real work.
**Automation:** 50% — requires designing actual agent behaviors.

### 4.1 Priority Agents to Implement

| Agent         | Real Task                  | Implementation                       |
| ------------- | -------------------------- | ------------------------------------ |
| **TENSOR**    | Run compression on files   | Call CompressionBridge               |
| **CIPHER**    | Encrypt/decrypt files      | Python `cryptography` lib            |
| **ARCHITECT** | Recommend ZFS pool configs | Rule engine based on disk count/type |
| **VELOCITY**  | Benchmark storage I/O      | Run `fio`, parse results             |
| **FORTRESS**  | Security audit             | Shell to `ss`, `find`, `ufw`         |
| **ORACLE**    | Predict disk failures      | Parse `smartctl`, rules-based        |
| **SENTRY**    | Monitor system resources   | Parse `/proc`, emit alerts           |
| **LATTICE**   | ZFS health monitoring      | `zpool status`, `zfs get`            |
| **SCRIBE**    | Generate system reports    | Aggregate data → markdown/PDF        |
| **FLUX**      | CI/CD status               | GitHub API integration               |

### 4.2 Agent Task Runner Refactor

Replace the simulated `_execute_task` in `swarm.py`:

```python
async def _execute_task(self, task: Task, agent: Agent) -> None:
    handler = self._task_handlers.get(agent.name)
    if handler:
        task.result = await handler(task.payload)
    else:
        task.result = {"status": "stub", "message": f"{agent.name} not yet implemented"}
```

### 4.3 Desktop Agent Interaction

The Agents page in SigmaVault Settings:

- Grid of 40 agent cards (Adw.ActionRow) showing name, tier, status, task count
- Click agent → detail view with "Assign Task" button
- Pre-built task templates: "Check disk health" (ORACLE), "Run security audit" (FORTRESS), "Benchmark I/O" (VELOCITY)
- Results displayed in-app with option to export as report
- Desktop notifications for completed tasks

**Success criteria:** Click ORACLE in Settings app → "Check Disk Health" → see real SMART analysis → desktop notification.

---

## Phase 4B: Ryzanstein LLM Integration (2-3 Weeks, Parallel with 4A) [REF:PH4B-007B]

**Goal:** Integrate Ryzanstein as native LLM engine, making SigmaVault the first NAS OS with built-in local AI.
**Context:** See `ryzanstein-integration-plan.md` for full architecture and rationale.
**Automation:** 60% — core integration scriptable, desktop features need design.
**Timeline:** Runs **in parallel** with Phase 4A since:

- Phase 4A: Wire agents to real system tasks (ZFS, smartctl, fio)
- Phase 4B: Wire agents to Ryzanstein for intelligent reasoning
- They converge when agents have both capabilities

### 4B.1 Core Integration (Week 1)

**Add Ryzanstein as 4th Submodule:**

```bash
git submodule add https://github.com/iamthegreatdestroyer/Ryzanstein.git submodules/ryzanstein
git submodule update --init --recursive
```

**Create systemd Service:**

```ini
# /etc/systemd/system/sigmavault-ryzan.service
[Unit]
Description=SigmaVault Ryzanstein LLM Engine
After=network.target sigmavault-engine.service
Wants=sigmavault-engine.service

[Service]
Type=notify
User=sigmavault
ExecStartPre=/opt/sigmavault/ryzan/detect-cpu.sh
ExecStart=/opt/sigmavault/ryzan/start.sh
Restart=on-failure
MemoryMax=70%
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```

**Create D-Bus Interface:**

```python
# src/ryzan-bridge/dbus_service.py
import dbus.service
import requests

class RyzanDBusService(dbus.service.Object):
    """D-Bus interface: org.sigmavault.Ryzan"""

    @dbus.service.method("org.sigmavault.Ryzan", in_signature='ss', out_signature='s')
    def Chat(self, model, messages):
        """Send chat request to Ryzanstein engine"""
        response = requests.post('http://localhost:8100/v1/chat/completions',
                                json={'model': model, 'messages': messages})
        return response.json()

    @dbus.service.method("org.sigmavault.Ryzan", out_signature='a{sv}')
    def GetStatus(self):
        """Get current model status and performance metrics"""
        return {'model': 'bitnet-7b', 'tokens_per_sec': 25.3, 'memory_mb': 3584}
```

**Create Unix Socket Bridge:**

```bash
# /run/sigmavault/ryzan.sock — zero-overhead local inference
socat UNIX-LISTEN:/run/sigmavault/ryzan.sock,fork TCP:localhost:8100
```

**Wire Python RPC Engine:**

```python
# src/engined/engined/llm/client.py
class RyzanClient:
    """OpenAI-compatible client for local Ryzanstein engine"""
    base_url = "http://localhost:8100/v1"

    async def chat(self, model: str, messages: list, tools: list = None):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/chat/completions",
                                   json={'model': model, 'messages': messages,
                                        'tools': tools}) as resp:
                return await resp.json()
```

**Auto-detect CPU on Boot:**

```bash
#!/bin/bash
# detect-cpu.sh — selects optimal model for hardware
CPU_MODEL=$(lscpu | grep "Model name")
TOTAL_RAM=$(free -g | awk '/Mem/{print $2}')
AVX512=$(lscpu | grep -c avx512)

if [ $TOTAL_RAM -lt 16 ]; then
    echo "draft-350m"  # Minimal: 350MB model
elif [ $TOTAL_RAM -lt 32 ]; then
    echo "bitnet-7b"   # Standard: 3.5GB model
elif [ $AVX512 -gt 0 ]; then
    echo "bitnet-7b+mamba"  # Full: multi-model routing
else
    echo "bitnet-7b"   # Fallback
fi
```

### 4B.2 Agent Backbone (Week 2)

**Replace Agent Stubs with Ryzanstein-Powered Execution:**

```python
# src/engined/engined/agents/swarm.py
from engined.llm.client import RyzanClient

class AgentSwarm:
    def __init__(self):
        self.ryzan = RyzanClient()
        self.agent_prompts = self._load_agent_prompts()

    async def _execute_task(self, task: Task, agent: Agent) -> None:
        # BEFORE: await asyncio.sleep(0.1)  # No-op stub
        # AFTER: Real LLM-powered execution
        system_prompt = self.agent_prompts.get(agent.name)
        response = await self.ryzan.chat(
            model="bitnet-7b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task.to_prompt()}
            ],
            tools=agent.available_tools  # MCP tool definitions
        )
        task.result = self._parse_agent_response(response)
```

**Create Agent-Specific System Prompts:**

```bash
# /etc/sigmavault/agent-prompts/ORACLE.txt
You are ORACLE, a predictive analytics specialist for NAS storage systems.
Given SMART data, disk usage trends, and historical failure patterns,
predict probability of disk failure and recommend preventive actions.
Always provide confidence scores and cite specific SMART attributes.
```

**Implement MCP Tool Definitions:**

```python
# Each agent exposes its capabilities as MCP tools
ORACLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_smart_data",
            "description": "Analyze SMART disk health data",
            "parameters": {
                "type": "object",
                "properties": {
                    "device": {"type": "string"},
                    "smart_data": {"type": "object"}
                }
            }
        }
    }
]
```

**Wire Task Results to WebSocket:**

```python
# When agent completes task, emit over WebSocket
await self.ws_hub.emit("agent_task_complete", {
    "agent": agent.name,
    "task_id": task.id,
    "result": task.result,
    "timestamp": time.time()
})
```

**Add LLM Status Widget to Dashboard:**

```python
# src/desktop-ui/ui/pages/dashboard.py
class DashboardPage(Adw.Bin):
    def _create_llm_status_card(self):
        """Shows current LLM model, memory usage, tokens/sec"""
        status = self._api.get_llm_status()  # GET /api/v1/llm/status
        card = Adw.ActionRow(
            title=f"Ryzanstein: {status['model']}",
            subtitle=f"{status['tokens_per_sec']:.1f} tok/s, {status['memory_mb']}MB"
        )
        return card
```

### 4B.3 Desktop Integration (Week 3)

**GNOME Shell Search Provider:**

```python
# /usr/share/gnome-shell/search-providers/sigmavault-ryzan.ini
[Shell Search Provider]
DesktopId=sigmavault-ryzan.desktop
BusName=org.sigmavault.Ryzan.SearchProvider
ObjectPath=/org/sigmavault/Ryzan/SearchProvider
Version=2
```

**Nautilus Right-Click Enhancement:**

```python
# Add to existing nautilus-sigmavault.py
def get_file_items(self, files):
    items = []
    # Existing compress action...

    # NEW: Ask Ryzanstein
    item = Nautilus.MenuItem(
        name="SigmaVault::AskRyzan",
        label="Ask Ryzanstein about this file",
        tip="Get AI insights about file type, security, optimization"
    )
    item.connect("activate", self._ask_ryzan, files)
    items.append(item)
    return items

def _ask_ryzan(self, menu, files):
    for f in files:
        path = f.get_location().get_path()
        # Send to Ryzanstein via D-Bus
        bus = dbus.SessionBus()
        ryzan = bus.get_object('org.sigmavault.Ryzan', '/org/sigmavault/Ryzan')
        response = ryzan.Chat('bitnet-7b', f'Analyze this file: {path}')
        # Show in desktop notification
        notification = Gio.Notification.new("Ryzanstein Analysis")
        notification.set_body(response)
        app.send_notification(None, notification)
```

**Settings App: "Chat with NAS" Panel:**

```python
# src/desktop-ui/ui/pages/chat.py
class ChatPage(Adw.NavigationPage):
    """Conversational interface to NAS management via Ryzanstein"""

    def __init__(self):
        self.chat_view = Gtk.ListView()  # Chat bubbles
        self.input_entry = Gtk.Entry(placeholder_text="Ask your NAS anything...")
        self.input_entry.connect("activate", self._send_message)

    def _send_message(self, entry):
        user_msg = entry.get_text()
        # Send to Ryzanstein
        response = self._api.chat_with_ryzan(user_msg)
        # Add to chat view
        self._add_chat_bubble(user_msg, is_user=True)
        self._add_chat_bubble(response, is_user=False)
        entry.set_text("")
```

**Desktop Notifications with Action Buttons:**

```python
# When agent completes task
notification = Gio.Notification.new(f"Agent {agent_name} Complete")
notification.set_body(result_summary)
notification.add_button("View Details", f"app.show-task::{task_id}")
notification.add_button("Export Report", f"app.export::{task_id}")
app.send_notification(None, notification)
```

**First-Boot Model Download Wizard:**

```python
# On first launch if no model found
dialog = Adw.MessageDialog.new(
    parent=window,
    heading="Enable Local AI?",
    body="Download Ryzanstein BitNet 7B model (3.5GB) for local AI-powered features?"
)
dialog.add_response("cancel", "Not Now")
dialog.add_response("download", "Download")
dialog.set_response_appearance("download", Adw.ResponseAppearance.SUGGESTED)
dialog.connect("response", self._handle_model_download)
```

### 4B.4 Resource Management

**cgroups v2 Limits:**

```ini
# Ryzanstein yields to file serving
sigmavault-ryzan.service:
  CPUQuota=80%  # drops to 30% under high I/O
  MemoryMax=70%

samba.service, nfs-server.service:
  CPUWeight=200  # high priority
```

**ZFS ARC Priority:**

```bash
# Ensure file cache gets 25% RAM before LLM
echo 25% > /sys/module/zfs/parameters/zfs_arc_max
```

### 4B.5 ISO Integration

**Add to Package List:**

```
# live-build/config/package-lists/sigmavault-core.list.chroot

# Ryzanstein LLM dependencies
python3-fastapi
python3-uvicorn
python3-aiohttp
python3-numpy
cmake
ninja-build
```

**Systemd Dependency Chain:**

```
sigmavault-engine.service → sigmavault-ryzan.service → sigmavault-api.service
```

### 4B.6 Natural Language NAS Management Examples

**GNOME Shell Search:**

```
User types: "ryzan: create mirrored pool from 4TB drives"
→ Ryzanstein interprets intent
→ Calls ARCHITECT agent
→ Executes: zpool create tank mirror /dev/sda /dev/sdb
→ Desktop notification: "Pool 'tank' created — 4TB mirrored, ONLINE"
```

**Conversational Admin:**

```
User (in Chat panel): "Set up Samba share for home office, read-write for me, read-only for guests"
Ryzan: "I'll create share 'home-office' at /srv/sigmavault/shares/home-office:
        • Your user: full read-write
        • Guest access: read-only
        Shall I proceed? [Create Share] [Modify] [Cancel]"
```

**Automated Alerts:**

```
Desktop Notification:
"⚠️ Drive /dev/sdc: elevated reallocated sectors (2→8 in 30 days).
 ORACLE estimates 73% failure probability within 6 months.
 Recommendation: Back up data, prepare replacement.
 [View Details] [Order Replacement] [Dismiss]"
```

### Integration Philosophy

**Why This Is "Built Into the OS" — Not Just Another Service:**

| Feature            | Typical LLM       | Ryzanstein in SigmaVault                      |
| ------------------ | ----------------- | --------------------------------------------- |
| Desktop shell      | ❌ Separate app   | ✅ GNOME Shell search provider                |
| File manager       | ❌ Upload via web | ✅ Nautilus right-click menu                  |
| Notifications      | ❌ Browser tab    | ✅ Native GNOME notifications                 |
| D-Bus              | ❌ HTTP only      | ✅ `org.sigmavault.Ryzan` service             |
| Unix socket        | ❌ TCP only       | ✅ Zero-overhead `/run/sigmavault/ryzan.sock` |
| Agent backbone     | ❌ Cloud API      | ✅ All 40 agents use LOCAL Ryzanstein         |
| Boot integration   | ❌ Manual start   | ✅ systemd service, auto-start                |
| Hardware detection | ❌ Generic        | ✅ Auto-detects CPU → loads optimal model     |

**Success criteria:**

- Type "ryzan: check disk health" in GNOME Shell → see analysis
- Right-click PDF in Nautilus → "Ask Ryzanstein" → get summary
- Chat with NAS in Settings app → create ZFS pool via conversation
- Desktop notification shows intelligent disk failure prediction
- All 40 agents use Ryzanstein for reasoning (no cloud API calls)

**See:** `ryzanstein-integration-plan.md` for complete architecture, competitive analysis, and risk mitigation.

---

## Phase 5: Bootable ISO with GNOME Desktop (1 Week) [REF:PH5-008]

**Goal:** Produce a bootable Debian ISO with GNOME and SigmaVault pre-installed.
**Automation:** 90% — GitHub Actions handles the build.

### 5.1 Enhance Live-Build Config

Current `live-build/` is minimal. Update `sigmavault-core.list.chroot`:

```
# GNOME Desktop Environment
task-gnome-desktop
gnome-shell
nautilus
gnome-disk-utility
gnome-system-monitor
gnome-terminal
gnome-text-editor

# SigmaVault Dependencies
python3-gi
python3-gi-cairo
gir1.2-adw-1
gir1.2-gtk-4.0
python3-requests
python3-aiohttp
python3-websockets
python3-nautilus

# Storage
zfsutils-linux
samba
nfs-kernel-server
smartmontools

# Development & Runtime
golang-go
python3-full
python3-pip
docker.io
git

# Networking
wireguard-tools
```

### 5.2 systemd Service Units

```
/etc/systemd/system/sigmavault-api.service     → Go API on :3000
/etc/systemd/system/sigmavault-engine.service   → Python RPC on :8000/:50051
```

**No web server needed** — the management interface is a native GTK app, not a web page. This eliminates the nginx dependency and the `sigmavault-webui.service` from the v3 plan.

### 5.3 Auto-Install SigmaVault Desktop App

Live-build hook script in `live-build/config/hooks/`:

```bash
#!/bin/bash
# Install SigmaVault Settings app
cp /path/to/sigmavault-settings.desktop /usr/share/applications/
cp -r /path/to/src/desktop-ui/ /opt/sigmavault/desktop-ui/
cp /path/to/nautilus-sigmavault.py /usr/share/nautilus-python/extensions/
# Install GSettings schema
cp com.sigmavault.Settings.gschema.xml /usr/share/glib-2.0/schemas/
glib-compile-schemas /usr/share/glib-2.0/schemas/

# Enable services
systemctl enable sigmavault-api
systemctl enable sigmavault-engine
```

### 5.4 First-Boot Experience

On first boot after installation:

1. GNOME initial setup (user, timezone, network — built-in)
2. SigmaVault first-run dialog (GTK): hostname, discover disks, suggest ZFS pool
3. Services start automatically via systemd
4. Desktop notification: "SigmaVault is ready — 40 agents standing by"

### 5.5 ISO Build in CI

Update GitHub Actions to:

1. Build Go API binary
2. Package Python engine
3. Package desktop UI (copy files, no build step needed for Python)
4. Copy all into live-build tree
5. Run `lb build`
6. Upload ISO as release artifact

**Success criteria:** ISO boots in VM → GNOME desktop loads → "SigmaVault Settings" in app grid → launches and shows agent dashboard.

---

## Phase 6: VPN & Remote Access (2 Weeks) [REF:PH6-009]

**Goal:** Access NAS remotely via WireGuard VPN.
**Automation:** 70% — WireGuard setup is scriptable, UI needs design.

### 6.1 Minimum Viable VPN (Personal Use)

No mesh needed for personal use:

- WireGuard server running on the NAS
- Generate client configs from SigmaVault Settings app
- QR code generation for mobile clients (via `qrencode` library)
- Auto-start on boot via systemd

### 6.2 Desktop Integration

Network page in SigmaVault Settings:

- VPN status: active/inactive toggle (Adw.SwitchRow)
- Connected peers list (Adw.ActionRow per peer)
- "Add Peer" button → generates config + QR code dialog
- Traffic stats per peer

### 6.3 PhantomMesh Integration

After Phase 0 submodule init, assess PhantomMesh-VPN capabilities and wire them into the Network page if useful. For personal use, raw WireGuard may be sufficient.

**Success criteria:** Connect to NAS from phone/laptop via WireGuard VPN. Generate config from desktop app.

---

## Automation Maximization Strategy [REF:AM-010]

### GitHub Actions (Revised for Desktop)

```yaml
# CI workflow — no web UI build jobs
on_push_to_any_branch:
  → lint (Go, Python)              # Removed: TypeScript/ESLint
  → unit tests (parallel: Go, Python)  # Removed: Vitest
  → build check (Go binary, Python package)

on_push_to_develop:
  → all above +
  → integration tests
  → security scan (Trivy + Semgrep)
  → build Docker image → push to GHCR

on_push_to_main:
  → all above +
  → build ISO (AMD64 + ARM64)      # Now includes GNOME desktop
  → create GitHub Release with ISO + binaries

on_tag_v*:
  → publish release as "latest"
```

### Makefile (Revised)

```makefile
.PHONY: dev test build iso clean

dev:        ## Start backend services + desktop app
	@echo "Starting SigmaVault development environment..."
	cd src/api && ./sigmavault-api &
	cd src/engined && python -m engined.main &
	cd src/desktop-ui && GTK_DEBUG=interactive python main.py
	@echo "API: localhost:3000  |  Engine: localhost:8000  |  Desktop UI: running"

test:       ## Run all tests
	cd src/api && go test ./... -v -short
	cd src/engined && python -m pytest tests/ -v

build:      ## Build all components
	cd src/api && CGO_ENABLED=0 go build -o sigmavault-api .
	cd src/engined && python -m build

iso:        ## Build bootable ISO (requires Debian + live-build)
	cd live-build && sudo lb clean && sudo lb config && sudo lb build

clean:      ## Clean build artifacts
	cd src/api && rm -f sigmavault-api
	cd src/engined && rm -rf dist/
```

### Docker Compose (Simplified)

```yaml
services:
  api:
    build: { context: src/api, dockerfile: Dockerfile }
    ports: ["3000:3000"]
    depends_on: [engine]

  engine:
    build: { context: src/engined, dockerfile: Dockerfile }
    ports: ["8000:8000", "50051:50051"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

# No webui service — desktop app runs natively on host
```

---

## Timeline Summary [REF:TL-011]

```
Phase 0 : Foundation Fix .................. 1-2 days
Phase 1 : Desktop Management App .......... 1-2 weeks     ← WAS: Web UI
Phase 2 : Storage Management .............. 1-2 weeks
Phase 3 : Real Compression ................ 1 week
Phase 4A: Agent Intelligence .............. 2 weeks       ← Real system tasks
Phase 4B: Ryzanstein LLM Integration ...... 2-3 weeks     ← Runs PARALLEL with 4A
Phase 5 : Bootable ISO (with GNOME) ....... 1 week        ← NOW includes desktop env
Phase 6 : VPN & Remote Access ............. 2 weeks
──────────────────────────────────────────────────────────
TOTAL: ~10-12 weeks to AI-native NAS OS (was 8-10, +2 weeks for LLM)

Note: Phase 4A and 4B run in parallel — 4A wires agents to system tasks,
      4B wires agents to Ryzanstein. They converge when agents have both.
```

### Milestone Checkpoints

| Week  | Milestone                                                      | Verification                             |
| ----- | -------------------------------------------------------------- | ---------------------------------------- |
| 0     | Submodules cloned (including Ryzanstein), all components build | `make test` passes                       |
| 1-2   | SigmaVault Settings app shows live agent data                  | Launch from GNOME app grid               |
| 3-4   | ZFS pool creation and file management works                    | End-to-end via Settings + Nautilus       |
| 5     | Real compression via right-click in Nautilus                   | Compress file → notification with ratio  |
| 6-7   | 5+ agents performing real tasks (Phase 4A)                     | Trigger from Settings app, see results   |
| 6-9   | Ryzanstein LLM integrated, agents use local AI (Phase 4B)      | Type "ryzan: check disk health" in Shell |
| 10    | ISO boots in VM with GNOME + SigmaVault + Ryzanstein           | VirtualBox/QEMU test                     |
| 11-12 | VPN access from external device                                | Phone connects via WireGuard             |

---

## Files to Create/Modify [REF:FI-012]

### New Files (Desktop Pivot)

| File                                                 | Purpose                                       | Phase |
| ---------------------------------------------------- | --------------------------------------------- | ----- |
| `src/desktop-ui/main.py`                             | GTK4 application entry point                  | 1     |
| `src/desktop-ui/ui/window.py`                        | Main window with sidebar navigation           | 1     |
| `src/desktop-ui/ui/pages/*.py`                       | Dashboard, Storage, Compression, Agents, etc. | 1     |
| `src/desktop-ui/ui/widgets/*.py`                     | Reusable GTK widgets                          | 1     |
| `src/desktop-ui/api/client.py`                       | HTTP client for Go API                        | 1     |
| `src/desktop-ui/api/websocket.py`                    | WebSocket client with GLib integration        | 1     |
| `src/desktop-ui/sigmavault-settings.desktop`         | GNOME app launcher                            | 1     |
| `src/desktop-ui/nautilus-sigmavault.py`              | Nautilus right-click extension                | 1     |
| `src/desktop-ui/com.sigmavault.Settings.gschema.xml` | GSettings schema                              | 1     |
| `scripts/bootstrap.sh`                               | One-command project setup                     | 0     |
| `scripts/bootstrap.ps1`                              | Windows dev version                           | 0     |
| `docker-compose.dev.yml`                             | Dev environment (backend only)                | 0     |

### Files to Remove

| File/Directory                  | Reason                                     |
| ------------------------------- | ------------------------------------------ |
| `src/webui/` (entire directory) | Empty React shell, replaced by desktop app |

### Existing Files to Modify

| File                                                          | Change                                         | Phase |
| ------------------------------------------------------------- | ---------------------------------------------- | ----- |
| `src/api/internal/handlers/storage.go`                        | Add real ZFS management                        | 2     |
| `src/engined/engined/agents/swarm.py`                         | Replace sleep stub with real task routing      | 4     |
| `src/engined/engined/compression/bridge.py`                   | Verify EliteSigma import path                  | 3     |
| `live-build/config/package-lists/sigmavault-core.list.chroot` | Add GNOME desktop + GTK deps                   | 5     |
| `.github/workflows/ci.yml`                                    | Remove webui build, add ISO build              | 5     |
| `Makefile`                                                    | Update dev/test/build targets (no pnpm)        | 0     |
| `README.md`                                                   | Update architecture diagram (desktop, not web) | 1     |

---

## What NOT to Do [REF:NT-013]

1. **Don't build a web UI.** The desktop IS the interface. GNOME provides file management, disk tools, and system monitoring for free.
2. **Don't plan for enterprise features.** No multi-tenancy, SSO, SLA monitoring. Personal use first.
3. **Don't build quantum cryptography.** Use standard AES-256-GCM.
4. **Don't implement neurosymbolic reasoning.** Focus on agents that do useful sysadmin tasks.
5. **Don't build a service mesh.** One machine, three services. Direct HTTP/gRPC is fine.
6. **Don't target 90%+ compression.** Get real compression working at any ratio first.
7. **Don't spend weeks on observability.** Basic structured logging is enough.
8. **Don't build a custom file browser.** Nautilus exists. Use it.
9. **Don't build a custom system monitor.** GNOME System Monitor exists. Use it.
10. **Don't build a custom disk manager.** GNOME Disks exists. Only build the ZFS-specific layer.

---

## Recommended First Session Actions [REF:FS-014]

1. **Run Phase 0** — Clone submodules, remove empty webui, verify builds (~30 min)
2. **Scaffold GTK app** — Create `main.py` with Adw.Application, sidebar window, empty pages (~2 hours with AI)
3. **Connect Dashboard to API** — Wire `api/client.py` to Go API, show agent status on dashboard page (~1 hour)
4. **Add desktop file** — Install `.desktop` launcher, verify it appears in app grid (~15 min)
5. **Test end-to-end** — Start API + engine + desktop app, see live agent data (~30 min)
6. **Commit & push** — First real desktop integration commit

That single session transforms the project from "invisible backend scaffolding" to "a native desktop application you can launch and interact with."

---

## Architecture Diagram (v4 — Desktop + Ryzanstein LLM) [REF:AD-015]

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GNOME Desktop Environment                         │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │   Nautilus    │  │ GNOME Shell  │  │    SigmaVault Settings       │  │
│  │ (file browse) │  │  Search      │  │    (GTK4 + libadwaita)       │  │
│  │ + right-click │  │  Provider    │  │                              │  │
│  │   compress    │  │ "ryzan: ..." │  │  Dashboard | Storage         │  │
│  │ + ask Ryzan   │  │              │  │  Compress  | Agents          │  │
│  │              │  │ GNOME Disks  │  │  Shares    | Chat with NAS   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────────────────┘  │
│         │                  │                   │                         │
│         │      REST + WebSocket + D-Bus        │                         │
│         └──────────────────┬───────────────────┘                         │
│                            │                                             │
├────────────────────────────┼─────────────────────────────────────────────┤
│                            ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                  Go API Server (:3000)                             │  │
│  │  REST endpoints | WebSocket hub | Auth | Rate limiting            │  │
│  │  /v1/llm/* → proxies to Ryzanstein                                │  │
│  └────────────────────┬──────────────────────────────────────────────┘  │
│                       │ gRPC (:50051)                                   │
│  ┌────────────────────┴──────────────────────────────────────────────┐  │
│  │               Python RPC Engine (:8000)                            │  │
│  │  Agent Swarm (40) | Compression Bridge | Task Scheduler           │  │
│  │  All agents now use Ryzanstein for intelligent reasoning          │  │
│  └────────────────────┬──────────────────────────────────────────────┘  │
│                       │                                                 │
│  ┌────────────────────┴──────────────────────────────────────────────┐  │
│  │            Ryzanstein LLM Engine (:8100) [NEW]                     │  │
│  │  BitNet b1.58 | Mamba SSM | RWKV | Token Recycling                │  │
│  │  D-Bus: org.sigmavault.Ryzan | Unix Socket: /run/sigmavault/ryzan │  │
│  │  CPU-first (AVX-512/VNNI) | OpenAI-compatible API                 │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                       │                                                 │
│  ┌────────────────────┴──────────────────────────────────────────────┐  │
│  │  EliteSigma-NAS  │  PhantomMesh-VPN  │  Elite Agents              │  │
│  │  (compression)    │  (WireGuard mesh)  │  (40 definitions)         │  │
│  │  Ryzanstein (LLM) [NEW]                                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Debian 13 (Trixie)                              │  │
│  │  ZFS | Samba | NFS | WireGuard | systemd | Docker | cgroups v2    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key Addition:** Ryzanstein LLM engine integrated as native systemd service with:

- D-Bus interface for desktop integration (GNOME Shell, Nautilus)
- Unix socket for zero-overhead local inference
- OpenAI-compatible API for agent consumption
- CPU-first architecture (no GPU required for NAS hardware)
- Auto-detection of CPU capabilities → optimal model selection

**Differentiation:** First NAS OS with built-in local LLM enabling natural language
management, AI-powered file operations, and intelligent agent reasoning—all without
cloud API calls.

---

_This plan (v4) supersedes v3 by replacing the React Web UI with native GNOME desktop integration. The backend architecture (Go API + Python engine + submodules) is unchanged. The interface philosophy shifts from "browser tab managing a NAS appliance" to "desktop OS with integrated NAS capabilities."_
\*\*
