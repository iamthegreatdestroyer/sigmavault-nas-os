#!/usr/bin/env bash
# =============================================================================
# SigmaVault NAS OS — Development Environment Bootstrap (Linux/macOS)
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

echo "============================================"
echo "  SigmaVault NAS OS — Dev Bootstrap"
echo "============================================"
echo ""

# ─── Check Python 3.11+ ────────────────────────────────────────
info "Checking Python..."
if command -v python3 &> /dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        ok "Python $PY_VER found"
    else
        warn "Python $PY_VER found, 3.11+ recommended"
    fi
else
    fail "Python3 not found. Install python3 (3.11+)."
fi

# ─── Check Go 1.21+ ────────────────────────────────────────────
info "Checking Go..."
if command -v go &> /dev/null; then
    GO_VER=$(go version | grep -oP 'go\K[0-9]+\.[0-9]+')
    ok "Go $GO_VER found"
else
    warn "Go not found. Install Go 1.21+ for API development."
fi

# ─── Check GTK4 + libadwaita ───────────────────────────────────
info "Checking GTK4 + libadwaita..."
if python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1')" 2>/dev/null; then
    ok "GTK4 + libadwaita available"
else
    warn "GTK4/libadwaita not found. Install system packages:"
    echo "  Debian/Ubuntu:  sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-dev"
    echo "  Fedora:         sudo dnf install python3-gobject gtk4-devel libadwaita-devel"
    echo "  Arch:           sudo pacman -S python-gobject gtk4 libadwaita"
fi

# ─── Create Python venv ────────────────────────────────────────
info "Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Created .venv"
else
    ok ".venv already exists"
fi

source .venv/bin/activate
pip install --upgrade pip -q

# ─── Install Python engine deps ────────────────────────────────
info "Installing Python engine dependencies..."
if [ -f "src/engined/pyproject.toml" ]; then
    pip install -e "src/engined[dev]" -q 2>/dev/null || pip install -r src/engined/requirements-test.txt -q
    ok "Engine dependencies installed"
fi

# ─── Install dev tools ─────────────────────────────────────────
info "Installing dev tools..."
pip install ruff mypy pytest pytest-cov pytest-asyncio -q
ok "Dev tools installed"

# ─── Check Nautilus Python ──────────────────────────────────────
info "Checking Nautilus Python extension support..."
if python3 -c "import gi; gi.require_version('Nautilus', '4.0')" 2>/dev/null; then
    ok "Nautilus Python extension support available"
else
    warn "Nautilus extension support not found. Install: python3-nautilus"
fi

# ─── Summary ────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Bootstrap Complete!"
echo "============================================"
echo ""
echo "Quick Start:"
echo "  source .venv/bin/activate"
echo "  make dev     # Show development commands"
echo ""
echo "Run the desktop app:"
echo "  make run-desktop"
echo ""
echo "Build all components:"
echo "  make build"
echo ""
