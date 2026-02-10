#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SigmaVault NAS OS - Development Environment Setup and Service Launcher
.DESCRIPTION
    One-command setup for Python Engine, Go API, and Desktop GTK4 UI.
    Supports full installation or quick startup of all services.
.PARAMETER Full
    Perform full setup including dependency installation
.PARAMETER Quick
    Quick start (assumes dependencies already installed)
.PARAMETER Service
    Start only specific service: 'engine', 'api', 'desktop', or 'all' (default)
.PARAMETER Kill
    Kill all running services and clean up
.EXAMPLE
    .\dev-environment-setup.ps1 -Full
    Full setup with dependency installation
.EXAMPLE
    .\dev-environment-setup.ps1 -Quick
    Quick start all services
.EXAMPLE
    .\dev-environment-setup.ps1 -Service engine
    Start only Python Engine
.EXAMPLE
    .\dev-environment-setup.ps1 -Kill
    Kill all running services
#>

param(
    [switch]$Full,
    [switch]$Quick,
    [switch]$Kill,
    [ValidateSet('all', 'engine', 'api', 'desktop')]
    [string]$Service = 'all'
)

# Color output functions
function Write-Success { param([string]$Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param([string]$Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param([string]$Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error-Custom { param([string]$Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Step { param([string]$Message) Write-Host "🔹 $Message" -ForegroundColor Blue }

# Banner
$banner = @"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███████╗██╗ ██████╗ ███╗   ███╗ █████╗ ██╗   ██╗        ║
║   ██╔════╝██║██╔════╝ ████╗ ████║██╔══██╗██║   ██║        ║
║   ███████╗██║██║  ███╗██╔████╔██║███████║██║   ██║        ║
║   ╚════██║██║██║   ██║██║╚██╔╝██║██╔══██║██║   ██║        ║
║   ███████║██║╚██████╔╝██║ ╚═╝ ██║██║  ██║╚██████╔╝        ║
║   ╚══════╝╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝         ║
║                                                              ║
║   SigmaVault NAS OS - Development Environment Setup         ║
║   Elite Agent Collective | Autonomous Development           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"@

Write-Host $banner -ForegroundColor Cyan

# Project root
$ProjectRoot = "S:\sigmavault-nas-os"
$EngineDir = Join-Path $ProjectRoot "src\engined"
$ApiDir = Join-Path $ProjectRoot "src\api"
$DesktopDir = Join-Path $ProjectRoot "src\desktop-ui"
$VenvPath = Join-Path $ProjectRoot ".venv"

# ============================================================================
# KILL SERVICES
# ============================================================================
if ($Kill) {
    Write-Info "Stopping all SigmaVault services..."
    
    # Kill Python processes
    Write-Step "Killing Python Engine processes..."
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -like "*sigmavault*" -or $_.CommandLine -like "*engined*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Kill Go API processes
    Write-Step "Killing Go API processes..."
    Get-Process sigmavault-api -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Kill Desktop UI processes
    Write-Step "Killing Desktop UI processes..."
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*desktop-ui*" -or $_.CommandLine -like "*sigma_vault*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Start-Sleep -Seconds 2
    
    # Verify ports are free
    $ports = @(5000, 12080)
    foreach ($port in $ports) {
        $listener = netstat -ano | Select-String ":$port " | Select-String "LISTENING"
        if ($listener) {
            Write-Warning "Port $port still in use"
        }
        else {
            Write-Success "Port $port is free"
        }
    }
    
    Write-Success "All services stopped"
    exit 0
}

# ============================================================================
# FULL SETUP
# ============================================================================
if ($Full) {
    Write-Info "Starting FULL development environment setup..."
    
    # Check Python version
    Write-Step "Checking Python version..."
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -notmatch "Python 3\.(1[1-9]|[2-9]\d)") {
        Write-Error-Custom "Python 3.11+ required. Found: $pythonVersion"
        exit 1
    }
    Write-Success "Python version: $pythonVersion"
    
    # Create virtual environment
    if (-not (Test-Path $VenvPath)) {
        Write-Step "Creating Python virtual environment..."
        python -m venv $VenvPath
        Write-Success "Virtual environment created at $VenvPath"
    }
    else {
        Write-Info "Virtual environment already exists"
    }
    
    # Activate venv
    Write-Step "Activating virtual environment..."
    & "$VenvPath\Scripts\Activate.ps1"
    Write-Success "Virtual environment activated"
    
    # Install Python Engine dependencies
    Write-Step "Installing Python Engine dependencies..."
    Set-Location $EngineDir
    pip install --upgrade pip setuptools wheel -q
    pip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to install Engine dependencies"
        exit 1
    }
    Write-Success "Engine dependencies installed"
    
    # Install Desktop UI dependencies (if requirements exist)
    if (Test-Path "$DesktopDir\requirements.txt") {
        Write-Step "Installing Desktop UI dependencies..."
        Set-Location $DesktopDir
        pip install -r requirements.txt -q
        Write-Success "Desktop UI dependencies installed"
    }
    
    # Check Go version
    Write-Step "Checking Go version..."
    $goVersion = go version 2>&1
    if ($goVersion -notmatch "go1\.(2[0-9]|[3-9]\d)") {
        Write-Error-Custom "Go 1.20+ required. Found: $goVersion"
        exit 1
    }
    Write-Success "Go version: $goVersion"
    
    # Install Go API dependencies
    Write-Step "Installing Go API dependencies..."
    Set-Location $ApiDir
    go mod download
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to download Go dependencies"
        exit 1
    }
    Write-Success "Go dependencies downloaded"
    
    # Build Go API
    Write-Step "Building Go API..."
    go build -o sigmavault-api.exe main.go
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to build Go API"
        exit 1
    }
    Write-Success "Go API built successfully: sigmavault-api.exe"
    
    Set-Location $ProjectRoot
    Write-Success "Full setup complete!"
    Write-Info "Run with -Quick flag to start services"
    exit 0
}

# ============================================================================
# SERVICE STARTUP
# ============================================================================
if ($Quick -or $Service -ne 'all') {
    Write-Info "Starting SigmaVault services..."
    
    # Ensure venv is activated
    if (-not $env:VIRTUAL_ENV) {
        Write-Step "Activating virtual environment..."
        & "$VenvPath\Scripts\Activate.ps1"
    }
    
    # Kill existing processes
    Write-Step "Cleaning up existing processes..."
    Get-Process python, sigmavault-api -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # Function to wait for service
    function Wait-ForService {
        param([string]$Url, [string]$ServiceName, [int]$TimeoutSeconds = 30)
        
        $elapsed = 0
        while ($elapsed -lt $TimeoutSeconds) {
            try {
                $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Success "$ServiceName is ready!"
                    return $true
                }
            }
            catch {
                # Still starting...
            }
            Start-Sleep -Seconds 2
            $elapsed += 2
            Write-Host "." -NoNewline
        }
        Write-Host ""
        Write-Warning "$ServiceName did not respond within $TimeoutSeconds seconds"
        return $false
    }
    
    # Start Python Engine
    if ($Service -eq 'all' -or $Service -eq 'engine') {
        Write-Step "Starting Python Engine on port 5000..."
        Set-Location $EngineDir
        
        $env:SIGMAVAULT_PORT = '5000'
        $engineJob = Start-Job -ScriptBlock {
            param($EngineDir, $VenvPath)
            Set-Location $EngineDir
            & "$VenvPath\Scripts\python.exe" -m engined
        } -ArgumentList $EngineDir, $VenvPath
        
        Start-Sleep -Seconds 3
        Write-Success "Engine started (Job ID: $($engineJob.Id))"
        
        # Wait for Engine to be ready
        Write-Step "Waiting for Engine to initialize..."
        if (Wait-ForService "http://127.0.0.1:5000/health/status" "Engine") {
            # Test RPC endpoint
            try {
                $body = '{"jsonrpc":"2.0","method":"health.check","id":1}'
                $rpcResponse = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/v1/rpc" `
                    -Method POST -ContentType "application/json" -Body $body `
                    -UseBasicParsing -TimeoutSec 5
                Write-Success "Engine RPC endpoint verified"
            }
            catch {
                Write-Warning "Engine RPC test failed: $_"
            }
        }
    }
    
    # Start Go API
    if ($Service -eq 'all' -or $Service -eq 'api') {
        Write-Step "Starting Go API on port 12080..."
        Set-Location $ApiDir
        
        if (-not (Test-Path "sigmavault-api.exe")) {
            Write-Error-Custom "sigmavault-api.exe not found. Run with -Full flag first."
            exit 1
        }
        
        $env:SIGMAVAULT_ENV = 'development'
        $env:SIGMAVAULT_RPC_URL = 'http://127.0.0.1:5000/api/v1'
        $env:PORT = '12080'
        
        $apiJob = Start-Job -ScriptBlock {
            param($ApiDir)
            Set-Location $ApiDir
            .\sigmavault-api.exe
        } -ArgumentList $ApiDir
        
        Start-Sleep -Seconds 3
        Write-Success "Go API started (Job ID: $($apiJob.Id))"
        
        # Wait for API to be ready
        Write-Step "Waiting for API to initialize..."
        if (Wait-ForService "http://127.0.0.1:12080/api/v1/health" "API") {
            # Test system status endpoint
            try {
                $statusResponse = Invoke-WebRequest -Uri "http://127.0.0.1:12080/api/v1/system/status" `
                    -UseBasicParsing -TimeoutSec 5
                Write-Success "API system status endpoint verified"
            }
            catch {
                Write-Warning "API status test failed: $_"
            }
        }
    }
    
    # Start Desktop UI
    if ($Service -eq 'all' -or $Service -eq 'desktop') {
        Write-Step "Starting Desktop UI..."
        Set-Location $DesktopDir
        
        $env:SIGMAVAULT_API_URL = 'http://127.0.0.1:12080/api/v1'
        
        $desktopJob = Start-Job -ScriptBlock {
            param($DesktopDir, $VenvPath)
            Set-Location $DesktopDir
            & "$VenvPath\Scripts\python.exe" -m sigma_vault.main
        } -ArgumentList $DesktopDir, $VenvPath
        
        Write-Success "Desktop UI started (Job ID: $($desktopJob.Id))"
        Write-Info "GTK4 window should appear shortly..."
    }
    
    Set-Location $ProjectRoot
    
    # Show running services
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🚀 Services Running" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    
    if ($Service -eq 'all' -or $Service -eq 'engine') {
        Write-Host "  🐍 Engine:   http://127.0.0.1:5000" -ForegroundColor Yellow
        Write-Host "              http://127.0.0.1:5000/health/status" -ForegroundColor Gray
        Write-Host "              http://127.0.0.1:5000/api/v1/rpc" -ForegroundColor Gray
    }
    
    if ($Service -eq 'all' -or $Service -eq 'api') {
        Write-Host "  🔌 API:      http://127.0.0.1:12080" -ForegroundColor Yellow
        Write-Host "              http://127.0.0.1:12080/api/v1/health" -ForegroundColor Gray
        Write-Host "              http://127.0.0.1:12080/api/v1/system/status" -ForegroundColor Gray
        Write-Host "              ws://127.0.0.1:12080/ws/events" -ForegroundColor Gray
    }
    
    if ($Service -eq 'all' -or $Service -eq 'desktop') {
        Write-Host "  🖥️  Desktop:  GTK4 Application Window" -ForegroundColor Yellow
    }
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Show job management commands
    Write-Info "Job Management Commands:"
    Write-Host "  Get-Job                    # View running jobs" -ForegroundColor Gray
    Write-Host "  Receive-Job -Id <id>       # View job output" -ForegroundColor Gray
    Write-Host "  Stop-Job -Id <id>          # Stop specific job" -ForegroundColor Gray
    Write-Host "  .\dev-environment-setup.ps1 -Kill   # Stop all services" -ForegroundColor Gray
    Write-Host ""
    
    Write-Success "All services started successfully!"
    Write-Info "Press Ctrl+C to return to shell (services continue in background)"
    
    exit 0
}

# ============================================================================
# DEFAULT: Show usage
# ============================================================================
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  .\dev-environment-setup.ps1 -Full          # Full setup with dependencies"
Write-Host "  .\dev-environment-setup.ps1 -Quick         # Quick start all services"
Write-Host "  .\dev-environment-setup.ps1 -Service api   # Start only API"
Write-Host "  .\dev-environment-setup.ps1 -Kill          # Stop all services"
Write-Host ""
Write-Info "Use -Full for first-time setup, then -Quick for daily development"
