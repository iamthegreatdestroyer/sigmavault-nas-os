#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SigmaVault Development Environment — Idempotent Startup
    @FLUX DevOps Automation

.DESCRIPTION
    Single-command development startup that:
    1. Kills any zombie processes on target ports
    2. Loads .env.development configuration
    3. Starts Python RPC engine with health check
    4. Starts Go API server with health check
    5. Reports final status

.PARAMETER SkipEngine
    Skip Python engine startup (use existing instance)

.PARAMETER SkipAPI
    Skip Go API startup (use existing instance)

.PARAMETER APIPort
    Go API port (default: from .env.development or 12080)

.PARAMETER EnginePort
    Python engine port (default: from .env.development or 5000)

.PARAMETER Kill
    Just kill all SigmaVault processes and exit

.EXAMPLE
    .\scripts\dev-start.ps1              # Start everything
    .\scripts\dev-start.ps1 -Kill        # Kill all processes
    .\scripts\dev-start.ps1 -SkipEngine  # API only (engine already running)
#>

param(
    [switch]$SkipEngine,
    [switch]$SkipAPI,
    [switch]$Kill,
    [int]$APIPort = 0,
    [int]$EnginePort = 0
)

$ErrorActionPreference = "Continue"

# ─── Helpers ────────────────────────────────────────────────────
function Write-Ok { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "  ✗ $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  ℹ $msg" -ForegroundColor Cyan }
function Write-Step { param($n, $msg) Write-Host "[$n] $msg" -ForegroundColor Cyan }

function Test-Port {
    param([int]$Port)
    $listener = netstat -ano 2>$null | Select-String ":$Port\s" | Select-String "LISTENING"
    return ($null -ne $listener)
}

function Wait-ForHealth {
    param([string]$Url, [string]$Name, [int]$Timeout = 30)
    $elapsed = 0
    while ($elapsed -lt $Timeout) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Ok "$Name is healthy (${elapsed}s)"
                return $true
            }
        }
        catch { }
        Start-Sleep -Seconds 2
        $elapsed += 2
        Write-Host "    Waiting for $Name... (${elapsed}s/$($Timeout)s)" -ForegroundColor DarkGray
    }
    Write-Err "$Name failed to start within ${Timeout}s"
    return $false
}

# ─── Resolve Project Root ───────────────────────────────────────
$ProjectRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $ProjectRoot) { $ProjectRoot = Split-Path $PSScriptRoot }
Push-Location $ProjectRoot

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SigmaVault Development Environment Startup" -ForegroundColor Cyan
Write-Host "  Root: $ProjectRoot" -ForegroundColor DarkGray
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ─── Load configs/development.env ────────────────────────────────
$envFile = Join-Path $ProjectRoot "configs" "development.env"
if (Test-Path $envFile) {
    Write-Info "Loading configs/development.env..."
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $val = $parts[1].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
            }
        }
    }
    Write-Ok "Environment loaded from configs/development.env"
}
else {
    Write-Warn "configs/development.env not found — using defaults"
}

# Apply overrides / defaults
if ($EnginePort -eq 0) { $EnginePort = [int]($env:SIGMAVAULT_PORT ?? 5000) }
if ($APIPort -eq 0) { $APIPort = [int]($env:PORT ?? 12080) }

$env:SIGMAVAULT_PORT = $EnginePort.ToString()
$env:PORT = $APIPort.ToString()
$env:SIGMAVAULT_ENV = $env:SIGMAVAULT_ENV ?? "development"
$env:SIGMAVAULT_RPC_URL = $env:SIGMAVAULT_RPC_URL ?? "http://127.0.0.1:$EnginePort/api/v1"

# ─── Step 1: Kill Zombie Processes ──────────────────────────────
Write-Step "1/4" "Cleaning up existing processes..."

# Kill Go API processes
Get-Process sigmavault-api -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill Python engine processes on target port
$pythonProcs = Get-NetTCPConnection -LocalPort $EnginePort -ErrorAction SilentlyContinue |
Where-Object State -eq "Listen" |
Select-Object -ExpandProperty OwningProcess -Unique

foreach ($pid in $pythonProcs) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

# Kill any API process on target port
$apiProcs = Get-NetTCPConnection -LocalPort $APIPort -ErrorAction SilentlyContinue |
Where-Object State -eq "Listen" |
Select-Object -ExpandProperty OwningProcess -Unique

foreach ($pid in $apiProcs) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

if (Test-Port $EnginePort) { Write-Warn "Port $EnginePort still in use" }
else { Write-Ok "Port $EnginePort is free" }

if (Test-Port $APIPort) { Write-Warn "Port $APIPort still in use" }
else { Write-Ok "Port $APIPort is free" }

# If -Kill flag, stop here
if ($Kill) {
    Write-Host ""
    Write-Ok "All SigmaVault processes killed. Ports freed."
    Pop-Location
    exit 0
}

# ─── Step 2: Activate Python venv ──────────────────────────────
Write-Step "2/4" "Activating Python virtual environment..."
$venvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
    Write-Ok "Virtual environment activated"
}
else {
    Write-Warn "No .venv found — using system Python"
}

# ─── Step 3: Start Python RPC Engine ───────────────────────────
if ($SkipEngine) {
    Write-Info "Skipping engine startup (-SkipEngine)"
}
else {
    Write-Step "3/4" "Starting Python RPC Engine on :$EnginePort..."
    
    $engineArgs = @("-m", "engined")
    $engineProc = Start-Process `
        -FilePath "python" `
        -ArgumentList $engineArgs `
        -WorkingDirectory (Join-Path $ProjectRoot "src\engined") `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput (Join-Path $ProjectRoot "engine-stdout.log") `
        -RedirectStandardError (Join-Path $ProjectRoot "engine-stderr.log")

    Write-Info "Engine PID: $($engineProc.Id)"

    # Health check — try JSON-RPC health endpoint
    $engineHealthy = Wait-ForHealth `
        -Url "http://127.0.0.1:$EnginePort/api/v1/rpc" `
        -Name "Python Engine" `
        -Timeout 20

    if (-not $engineHealthy) {
        Write-Err "Engine failed to start. Check engine-stderr.log"
        Write-Host (Get-Content "engine-stderr.log" -Tail 10 | Out-String) -ForegroundColor Red
    }
}

# ─── Step 4: Start Go API Server ───────────────────────────────
if ($SkipAPI) {
    Write-Info "Skipping API startup (-SkipAPI)"
}
else {
    Write-Step "4/4" "Starting Go API Server on :$APIPort..."

    # Build first if needed
    $apiExe = Join-Path $ProjectRoot "src\api\sigmavault-api.exe"
    if (-not (Test-Path $apiExe)) {
        Write-Info "Building API binary..."
        Push-Location (Join-Path $ProjectRoot "src\api")
        go build -o sigmavault-api.exe . 2>&1
        Pop-Location
    }

    $apiProc = Start-Process `
        -FilePath $apiExe `
        -WorkingDirectory (Join-Path $ProjectRoot "src\api") `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput (Join-Path $ProjectRoot "api-stdout.log") `
        -RedirectStandardError (Join-Path $ProjectRoot "api-stderr.log")

    Write-Info "API PID: $($apiProc.Id)"

    $apiHealthy = Wait-ForHealth `
        -Url "http://127.0.0.1:$APIPort/api/v1/health" `
        -Name "Go API" `
        -Timeout 15

    if (-not $apiHealthy) {
        Write-Err "API failed to start. Check api-stderr.log"
        Write-Host (Get-Content "api-stderr.log" -Tail 10 | Out-String) -ForegroundColor Red
    }
}

# ─── Final Status ──────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SigmaVault Development Stack Status" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

$status = @()
if (-not $SkipEngine) {
    $eUp = Test-Port $EnginePort
    $eStatus = if ($eUp) { "✓ RUNNING" } else { "✗ DOWN" }
    $eColor = if ($eUp) { "Green" } else { "Red" }
    Write-Host "  Python Engine : $eStatus  → http://127.0.0.1:$EnginePort" -ForegroundColor $eColor
}
if (-not $SkipAPI) {
    $aUp = Test-Port $APIPort
    $aStatus = if ($aUp) { "✓ RUNNING" } else { "✗ DOWN" }
    $aColor = if ($aUp) { "Green" } else { "Red" }
    Write-Host "  Go API Server : $aStatus  → http://127.0.0.1:$APIPort" -ForegroundColor $aColor
}

Write-Host ""
Write-Host "  Logs:" -ForegroundColor DarkGray
Write-Host "    Engine: engine-stdout.log / engine-stderr.log" -ForegroundColor DarkGray
Write-Host "    API:    api-stdout.log / api-stderr.log" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To stop: .\scripts\dev-start.ps1 -Kill" -ForegroundColor DarkGray
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Pop-Location
