# SigmaVault Native UI - GNOME Desktop Application

Native GNOME desktop application for managing compression jobs, monitoring storage, and viewing system status in SigmaVault NAS.

## Features (Planned)

✅ **Phase 3b.1** (CURRENT)

- Desktop application scaffold
- GTK4 + libadwaita UI framework
- API client for Go backend
- Main window with header bar
- Data models for compression jobs and system status

🔄 **Phase 3b.2** (Next)

- Dashboard view with system metrics
- Compression jobs history view
- Real-time status updates
- Storage information display

🔄 **Phase 3b.3**

- Job details modal
- Job actions and statistics
- Real-time progress tracking

🔄 **Phase 3b.4**

- Settings/preferences
- Export functionality
- Desktop notifications
- Keyboard shortcuts

## Requirements

- Python 3.10+
- PyGObject 3.46.0+
- libadwaita 1.4.0+ (GNOME 44+)
- aiohttp 3.9.0+
- pydantic 2.0.0+

### On Ubuntu/Debian

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adwaita-1 libadwaita-1-dev
```

### On Fedora

```bash
sudo dnf install python3-gobject python3-gobject-devel \
  gtk4-devel libadwaita-devel
```

## Installation

```bash
cd src/desktop-ui
pip install -e .
```

## Running

### Using entry point

```bash
sigmavault-nativeui
```

### Using Python module

```bash
python -m sigmavault_desktop
```

## Development

### Install development dependencies

```bash
cd src/desktop-ui
pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/ -v
```

### Code formatting

```bash
black sigmavault_desktop/
isort sigmavault_desktop/
```

### Type checking

```bash
mypy sigmavault_desktop/
```

## Project Structure

```
src/desktop-ui/
├── sigmavault_desktop/
│   ├── __init__.py                 # Package init
│   ├── __main__.py                 # Entry point
│   ├── app.py                      # Main application (GTK app)
│   ├── window.py                   # Main window (UI)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py               # Go API client (aiohttp)
│   │   └── models.py               # Data models (CompressionJob, SystemStatus)
│   ├── views/                      # (Phase 3b.2)
│   │   ├── __init__.py
│   │   ├── dashboard.py            # Home/overview
│   │   ├── compression_jobs.py     # Job history
│   │   ├── job_details.py          # Job details
│   │   ├── system_status.py        # System metrics
│   │   └── storage.py              # Storage pools
│   ├── widgets/                    # (Phase 3b.2)
│   │   ├── __init__.py
│   │   ├── job_card.py             # Job display card
│   │   ├── metrics_chart.py        # Performance charts
│   │   ├── progress_bar.py         # Job progress
│   │   └── sidebar.py              # Navigation sidebar
│   ├── utils/                      # (Phase 3b.4)
│   │   ├── __init__.py
│   │   ├── config.py               # Configuration
│   │   ├── logger.py               # Logging
│   │   └── formatters.py           # Data formatting
│   └── resources/                  # (Phase 3b.2+)
│       ├── ui.xml                  # UI definitions
│       ├── style.css               # Styling
│       └── icons/                  # Icons
├── pyproject.toml                  # Package metadata and dependencies
├── setup.py                        # (optional, for compatibility)
├── sigmavault-nativeui.desktop     # Desktop launcher
└── README.md                       # This file
```

## Architecture

### API Client (Implemented)

The `SigmaVaultAPIClient` communicates with the Go API backend:

```python
async with SigmaVaultAPIClient() as client:
    jobs = await client.get_compression_jobs(limit=50)
    job = await client.get_compression_job("job-001")
    status = await client.get_system_status()
```

### Data Models (Implemented)

```python
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
    disk_total_bytes: int
    active_jobs: int
    total_jobs: int
```

## Development Timeline

- **Phase 3b.1** (CURRENT): Foundation & Setup - 4 hours ✅ IN PROGRESS
- **Phase 3b.2**: Core Views - 8 hours
- **Phase 3b.3**: Job Details & Actions - 6 hours
- **Phase 3b.4**: Polish & Features - 4 hours

**Total**: ~22 hours (3 calendar days)

## Testing

Tests are located in `tests/` directory (to be created in Phase 3b.4):

- Unit tests for API client
- Integration tests for views
- UI interaction tests

## Contributing

1. Follow PEP 8 style guide
2. Format code with Black
3. Type hints required
4. Write tests for new functionality
5. Update documentation

## License

Apache 2.0 - See LICENSE file for details

## References

- [GTK4 Documentation](https://docs.gtk.org/gtk4/)
- [libadwaita Documentation](https://gnome.pages.gitlab.gnome.org/libadwaita/)
- [PyGObject Documentation](https://pygobject.readthedocs.io/)
- [GNOME Human Interface Guidelines](https://developer.gnome.org/hig/)
