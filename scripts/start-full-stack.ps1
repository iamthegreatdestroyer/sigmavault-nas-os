#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the complete SigmaVault stack for testing (Option A)
    
.DESCRIPTION
    Launches:
    1. Python RPC Engine (engined daemon) on port 5000
    2. Go API Server on port 12080
    3. Desktop UI (GTK4 application)
    
.EXAMPLE
    .\scripts\start-full-stack.ps1
#>

param(
    [switch]$NoUI,  # Don't launch the UI (just start services)
    [switch]$NoEngine,  # Don't start the RPC engine (use existing)
    [switch]$NoAPI,  # Don't start the API (use existing)
    [int]$APIPort = 12080,
    [int]$EnginePort = 5000
)

$ErrorActionPreference = "Continue"
$VerbosePreference = "Continue"

# Colors for output
function Write-Ok { Write-Host -ForegroundColor Green "✓ $args" }
function Write-Warn { Write-Host -ForegroundColor Yellow "⚠ $args" }
function Write-Err { Write-Host -ForegroundColor Red "✗ $args" }
function Write-Info { Write-Host -ForegroundColor Cyan "ℹ $args" }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SigmaVault Full Stack Startup (Option A)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Verify we're in the right directory
if (-not (Test-Path "src/api/main.go" -PathType Leaf)) {
    Write-Err "Not in sigmavault-nas-os root directory"
    exit 1
}

Write-Info "Stack components:"
Write-Info "  1. Python RPC Engine → http://localhost:$EnginePort"
Write-Info "  2. Go API Server → http://localhost:$APIPort"
Write-Info "  3. Desktop UI (GTK4)"
Write-Info ""

# ─────────────────────────────────────────────────────────────────
# Python RPC Engine
# ─────────────────────────────────────────────────────────────────

if ($NoEngine) {
    Write-Info "Skipping engine startup (assuming already running)"
}
else {
    Write-Info "Starting Python RPC Engine..."
    
    # Activate venv if not already activated
    if (-not (Get-Command "pip" -ErrorAction SilentlyContinue)) {
        if (Test-Path ".venv/Scripts/Activate.ps1") {
            & ".venv/Scripts/Activate.ps1"
            Write-Ok "Virtual environment activated"
        }
        else {
            Write-Warn "No virtual environment found, trying system Python"
        }
    }
    
    # Start engine in background
    $engineProcess = Start-Process `
        -FilePath "python" `
        -ArgumentList "src/engined/engined/main.py" `
        -WorkingDirectory "." `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput "engine-stdout.log" `
        -RedirectStandardError "engine-stderr.log"
    
    Write-Ok "Engine started (PID: $($engineProcess.Id))"
    Write-Info "  Logs: engine-stdout.log, engine-stderr.log"
    
    # Wait for engine to start
    Write-Info "  Waiting for engine to be ready..."
    $engineReady = $false
    $maxRetries = 30
    
    for ($i = 0; $i -lt $maxRetries; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $response = curl.exe -s "http://localhost:$EnginePort/health" 2>$null
            if ($response) {
                Write-Ok "Engine is ready (health check passed)"
                $engineReady = $true
                break
            }
        }
        catch {
            # Engine not ready yet
        }
    }
    
    if (-not $engineReady) {
        Write-Warn "Engine may not be fully ready (health check timed out after 15s)"
        Write-Warn "Check engine-stdout.log and engine-stderr.log for details"
        Write-Warn "Proceeding anyway - check logs if API calls fail"
    }
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────
# Go API Server
# ─────────────────────────────────────────────────────────────────

if ($NoAPI) {
    Write-Info "Skipping API startup (assuming already running)"
}
else {
    Write-Info "Starting Go API Server..."
    
    # Check if port is already in use
    $portInUse = netstat -ano 2>$null | Select-String ":$APIPort " | Select-String "LISTENING"
    if ($portInUse) {
        Write-Warn "Port $APIPort is already in use"
        Write-Info "  Checking if it's the right process..."
        # Try to contact the API
        try {
            $health = curl.exe -s "http://localhost:$APIPort/api/v1/health" 2>$null | ConvertFrom-Json
            if ($health.status -eq "healthy") {
                Write-Ok "Existing API server is responsive"
                $NoAPI = $true
            }
            else {
                Write-Err "Port $APIPort in use but appears to be wrong service"
                Write-Info "Kill the process or use -APIPort to specify a different port"
                exit 1
            }
        }
        catch {
            Write-Err "Port $APIPort in use but not responding to API calls"
            Write-Info "Kill the process or use -APIPort to specify a different port"
            exit 1
        }
    }
    
    if (-not $NoAPI) {
        # Set environment for dev mode (auth bypass)
        $env:SIGMAVAULT_ENV = "development"
        $env:SIGMAVAULT_RPC_ENGINE_URL = "http://localhost:$EnginePort"
        
        # Start API in background
        $apiProcess = Start-Process `
            -FilePath "go" `
            -ArgumentList "run", "main.go", "-port", $APIPort `
            -WorkingDirectory "src/api" `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput "api-stdout.log" `
            -RedirectStandardError "api-stderr.log"
        
        Write-Ok "API Server started (PID: $($apiProcess.Id))"
        Write-Info "  Logs: api-stdout.log, api-stderr.log"
        Write-Info "  Dev Mode: SIGMAVAULT_ENV=development (auth bypass enabled)"
        
        # Wait for API to start
        Write-Info "  Waiting for API to be ready..."
        $apiReady = $false
        $maxRetries = 30
        
        for ($i = 0; $i -lt $maxRetries; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $response = curl.exe -s "http://localhost:$APIPort/api/v1/health" 2>$null | ConvertFrom-Json
                if ($response.status -eq "healthy") {
                    Write-Ok "API Server is ready"
                    $apiReady = $true
                    break
                }
            }
            catch {
                # API not ready yet
            }
        }
        
        if (-not $apiReady) {
            Write-Warn "API may not be fully ready (health check timed out after 15s)"
            Write-Warn "Check api-stdout.log and api-stderr.log for details"
            Write-Warn "Proceeding anyway - check logs if UI fails to connect"
        }
    }
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────
# Desktop UI
# ─────────────────────────────────────────────────────────────────

if ($NoUI) {
    Write-Ok "Full stack running (services started successfully)"
    Write-Info "To launch the desktop UI manually, run:"
    Write-Info "  cd src/desktop-ui && python main.py"
    Write-Host ""
    Write-Info "Services are running in the background with logs:"
    Write-Info "  Engine: engine-stdout.log, engine-stderr.log"
    Write-Info "  API: api-stdout.log, api-stderr.log"
}
else {
    Write-Host ""
    Write-Info "Launching Desktop UI..."
    Write-Info "  The UI window should open in a moment..."
    Write-Info "  Dashboard will show live API data with 10-second auto-refresh"
    
    # Launch desktop UI
    Start-Process `
        -FilePath "python" `
        -ArgumentList "main.py" `
        -WorkingDirectory "src/desktop-ui" `
        -PassThru `
        -NoNewWindow
    
    Write-Ok "Desktop UI launched"
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Option A: Full Stack Test STARTED" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
