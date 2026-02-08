# Phase 3b: Dashboard UI Development - Action Plan

**Status**: ✅ READY TO START  
**Date**: February 7, 2026  
**Prerequisite**: Phase 3a (API Infrastructure) ✅ COMPLETE & TESTED

---

## 📋 Phase 3b Overview

**Objective**: Create native GNOME desktop UI for compression job management and system monitoring

**Approach**: GTK4 + libadwaita (GNOME native) instead of web dashboard

**Timeline**: 2-3 days of implementation

---

## Why GNOME Desktop Instead of Web UI

### Advantages of Native Desktop

| Aspect               | Web UI (Previous)              | GNOME Desktop (New)             |
| -------------------- | ------------------------------ | ------------------------------- |
| **Dependencies**     | Node.js, npm/pnpm, Vite, nginx | Python + GTK4 (system packages) |
| **File Integration** | Limited to browser APIs        | Full Nautilus integration       |
| **Disk Management**  | Custom implementation needed   | GNOME Disks integration         |
| **System Tray**      | Websockets + polling           | Native notifications            |
| **Deployment**       | SPA bundle + web server        | Single Python package           |
| **Performance**      | Browser overhead               | Native speed                    |

### What GNOME Provides for Free

- ✅ **Nautilus** (file manager) - browse compressed storage
- ✅ **GNOME Disks** - disk monitoring and management
- ✅ **System Monitor** - CPU/RAM tracking
- ✅ **Settings** - network and system configuration
- ✅ **Notification daemon** - alerts for compression jobs
- ✅ **App launcher** - desktop .desktop file
- ✅ **Dark/light theme** - system-wide preference

---

## 🏗️ Architecture Design

### Desktop Application Structure

```
src/desktop-ui/
├── sigmavault_desktop/
│   ├── __init__.py
│   ├── __main__.py                 # Entry point
│   ├── app.py                      # Main application window
│   ├── window.py                   # Main window UI
│   ├── views/
│   │   ├── dashboard.py            # Home/overview
│   │   ├── compression_jobs.py     # Job history
│   │   ├── job_details.py          # Job details
│   │   ├── system_status.py        # System metrics
│   │   └── storage.py              # Storage pools
│   ├── widgets/
│   │   ├── job_card.py             # Job display card
│   │   ├── metrics_chart.py        # Performance charts
│   │   ├── progress_bar.py         # Job progress
│   │   └── sidebar.py              # Navigation sidebar
│   ├── api/
│   │   ├── client.py               # Go API client
│   │   └── models.py               # Data classes
│   ├── utils/
│   │   ├── config.py               # Configuration
│   │   ├── logger.py               # Logging
│   │   └── formatters.py           # Data formatting
│   └── resources/
│       ├── ui.xml                  # libadwaita UI definitions
│       ├── style.css               # Custom styling
│       └── icons/                  # App icons
├── pyproject.toml
└── README.md
```

### Data Model

```python
# models.py
@dataclass
class CompressionJob:
    job_id: str
    status: str  # completed, failed, running, queued
    original_size: int
    compressed_size: int
    compression_ratio: float
    elapsed_seconds: float
    method: str
    data_type: str
    created_at: str  # ISO 8601
    error: str

@dataclass
class SystemStatus:
    cpu_percent: float
    memory_percent: float
    disk_usage: Dict[str, float]
    active_jobs: int
    total_jobs: int
```

---

## 🚀 Implementation Phases

### Phase 3b.1: Foundation & Setup (Day 1)

**Deliverables**:

1. Project structure created
2. Dependencies installed (PyGObject, libadwaita)
3. API client implemented
4. Basic window scaffold
5. Desktop .desktop file

**Key Files**:

- pyproject.toml - Define dependencies
- sigmavault_desktop/**main**.py - Entry point
- sigmavault_desktop/app.py - Application
- sigmavault_desktop/api/client.py - API wrapper
- sigmavault-nativeui.desktop - Desktop launcher

### Phase 3b.2: Core Views (Day 1-2)

**Deliverables**:

1. Dashboard view (home/overview)
2. Compression jobs list view
3. System status display
4. Storage information view

**Features**:

- Real-time metrics (CPU, RAM, Disk)
- Job listing with pagination
- Status indicators
- Auto-refresh every 5 seconds

### Phase 3b.3: Job Details & Actions (Day 2)

**Deliverables**:

1. Job details modal
2. Compression statistics display
3. Job actions (view, delete)
4. Real-time job progress

**Features**:

- Full job metadata
- Performance calculations
- Action buttons
- Real-time updates

### Phase 3b.4: Polish & Features (Day 3)

**Deliverables**:

1. Preferences/settings window
2. Export job history (CSV)
3. System notifications
4. Keyboard shortcuts

**Features**:

- Settings persistence
- Export functionality
- Desktop notifications
- Keyboard shortcuts

---

## 📦 Dependencies

```toml
[project]
dependencies = [
    "PyGObject>=3.46.0",        # GTK4 bindings
    "libadwaita>=1.4.0",         # GNOME design
    "aiohttp>=3.9.0",            # Async HTTP
    "pydantic>=2.0.0",           # Data validation
]
```

---

## 🧪 Testing Strategy

- Unit tests for API client
- Integration tests for views
- Manual UI testing
- Performance testing

---

## 📋 Implementation Checklist

- [ ] Create project structure
- [ ] Create pyproject.toml
- [ ] Create API client
- [ ] Create window scaffold
- [ ] Create dashboard view
- [ ] Create jobs view
- [ ] Create details modal
- [ ] Add settings/preferences
- [ ] Add export functionality
- [ ] Add notifications
- [ ] Polish UI/UX
- [ ] Test all features

---

## 🎯 Success Criteria

✅ Desktop application launches  
✅ Dashboard shows system metrics  
✅ Jobs view lists all compression jobs  
✅ Real-time updates work  
✅ Settings persist  
✅ Follows GNOME guidelines  
✅ All views responsive

---

## 🚀 Ready to Start?

Would you like me to:

1. **Create the project structure** and initial files?
2. **Implement Phase 3b.1** (Foundation & Setup)?
3. **Jump to Phase 3b.2** (Core Views)?

Let's build a beautiful GNOME desktop app! 🎉
