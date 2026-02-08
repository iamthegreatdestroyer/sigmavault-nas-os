# =============================================================================
# SigmaVault NAS OS — Development Environment Bootstrap (Windows/PowerShell)
# =============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SigmaVault NAS OS — Dev Bootstrap" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

function Write-Info { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Blue }
function Write-Ok { param($msg) Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }

# ─── Check Python ──────────────────────────────────────────────
Write-Info "Checking Python..."
try {
    $pyVer = python --version 2>&1
    Write-Ok "Python found: $pyVer"
}
catch {
    Write-Warn "Python not found. Install Python 3.11+ from python.org"
}

# ─── Check Go ──────────────────────────────────────────────────
Write-Info "Checking Go..."
try {
    $goVer = go version 2>&1
    Write-Ok "Go found: $goVer"
}
catch {
    Write-Warn "Go not found. Install Go 1.21+ from go.dev"
}

# ─── Create venv ───────────────────────────────────────────────
Write-Info "Setting up Python virtual environment..."
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Ok "Created .venv"
}
else {
    Write-Ok ".venv already exists"
}

# ─── Activate venv ─────────────────────────────────────────────
& .\.venv\Scripts\Activate.ps1
pip install --upgrade pip -q

# ─── Install engine deps ──────────────────────────────────────
Write-Info "Installing Python engine dependencies..."
if (Test-Path "src\engined\requirements-test.txt") {
    pip install -r src\engined\requirements-test.txt -q 2>$null
    Write-Ok "Engine dependencies installed"
}

# ─── Install dev tools ────────────────────────────────────────
Write-Info "Installing dev tools..."
pip install ruff mypy pytest pytest-cov pytest-asyncio -q
Write-Ok "Dev tools installed"

# ─── Notes for GTK4 on Windows ────────────────────────────────
Write-Warn "GTK4 + libadwaita: Full desktop UI requires Linux (Debian 13)."
Write-Host "  Windows dev: Use API client + engine tests only." -ForegroundColor Gray
Write-Host "  For GTK testing: Use WSL2 with Debian or test on target machine." -ForegroundColor Gray

# ─── Summary ──────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Bootstrap Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  make dev     # Show development commands"
Write-Host ""
Write-Host "Build Go API:"
Write-Host "  make build-api"
Write-Host ""
