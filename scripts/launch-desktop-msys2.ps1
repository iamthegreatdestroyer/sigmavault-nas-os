#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch SigmaVault Desktop UI via MSYS2 UCRT64 environment

.DESCRIPTION
    PowerShell wrapper that automatically launches the GTK4-based Desktop UI
    through MSYS2 UCRT64, handling all environment setup and path conversions.
    
    Prerequisites:
    - MSYS2 installed (default: S:\msys64)
    - UCRT64 packages: python, python-gobject, gtk4, libadwaita
    
.PARAMETER ApiUrl
    API endpoint URL (default: http://127.0.0.1:12080/api/v1)

.PARAMETER MSYS2Path
    MSYS2 installation path (default: S:\msys64)

.PARAMETER Check
    Check prerequisites only, don't launch

.PARAMETER Install
    Install missing MSYS2 packages interactively

.EXAMPLE
    .\launch-desktop-msys2.ps1
    Launch Desktop UI with default settings

.EXAMPLE
    .\launch-desktop-msys2.ps1 -ApiUrl "http://192.168.1.100:12080/api/v1"
    Launch with custom API endpoint

.EXAMPLE
    .\launch-desktop-msys2.ps1 -Check
    Check prerequisites without launching

.EXAMPLE
    .\launch-desktop-msys2.ps1 -Install
    Install missing packages interactively

.NOTES
    Author: Elite Agent Collective (@CANVAS + @FLUX + @BRIDGE)
    Project: SigmaVault NAS OS
    Phase: 2.2 - Three-Service Integration
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ApiUrl = "http://127.0.0.1:12080/api/v1",
    
    [Parameter(Mandatory = $false)]
    [string]$MSYS2Path = "S:\msys64",
    
    [Parameter(Mandatory = $false)]
    [switch]$Check,
    
    [Parameter(Mandatory = $false)]
    [switch]$Install
)

# Error handling
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Color output functions
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Failure { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Step { param($Message) Write-Host "📋 $Message" -ForegroundColor Magenta }

# Banner
function Show-Banner {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║                                                           ║" -ForegroundColor Blue
    Write-Host "║           SigmaVault NAS OS - Desktop UI Launcher         ║" -ForegroundColor Blue
    Write-Host "║                  MSYS2 GTK4 Environment                   ║" -ForegroundColor Blue
    Write-Host "║                                                           ║" -ForegroundColor Blue
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

# Get project root
function Get-ProjectRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return Split-Path -Parent $scriptDir
}

# Convert Windows path to MSYS2 path
function ConvertTo-MSYS2Path {
    param([string]$WindowsPath)
    
    $normalized = $WindowsPath -replace '\\', '/'
    
    # Handle drive letters (C:\ -> /c/, S:\ -> /s/)
    if ($normalized -match '^([A-Za-z]):(.*)$') {
        $drive = $matches[1].ToLower()
        $rest = $matches[2]
        return "/$drive$rest"
    }
    
    return $normalized
}

# Check if MSYS2 is installed
function Test-MSYS2Installation {
    Write-Step "Checking MSYS2 installation..."
    
    if (-not (Test-Path $MSYS2Path)) {
        Write-Failure "MSYS2 not found at: $MSYS2Path"
        Write-Info "Please install MSYS2 from: https://www.msys2.org/"
        Write-Info "Or use winget: winget install MSYS2.MSYS2"
        return $false
    }
    
    $ucrt64Exe = Join-Path $MSYS2Path "ucrt64.exe"
    if (-not (Test-Path $ucrt64Exe)) {
        Write-Failure "MSYS2 UCRT64 not found at: $ucrt64Exe"
        Write-Info "Please reinstall MSYS2 with default configuration"
        return $false
    }
    
    Write-Success "MSYS2 found at: $MSYS2Path"
    return $true
}

# Check if required MSYS2 packages are installed
function Test-MSYS2Packages {
    Write-Step "Checking required MSYS2 packages..."
    
    $requiredPackages = @(
        "mingw-w64-ucrt-x86_64-python",
        "mingw-w64-ucrt-x86_64-python-gobject",
        "mingw-w64-ucrt-x86_64-gtk4",
        "mingw-w64-ucrt-x86_64-libadwaita"
    )
    
    $bashExe = Join-Path $MSYS2Path "usr\bin\bash.exe"
    $missingPackages = @()
    
    foreach ($package in $requiredPackages) {
        $env:MSYSTEM = 'UCRT64'
        $env:CHERE_INVOKING = '1'
        $checkCmd = "pacman -Q $package"
        $result = & $bashExe -lc $checkCmd 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            $missingPackages += $package
            Write-Warning "Missing: $package"
        }
        else {
            Write-Success "Found: $package"
        }
    }
    
    if ($missingPackages.Count -gt 0) {
        Write-Failure "Missing $($missingPackages.Count) required package(s)"
        Write-Info ""
        Write-Info "To install missing packages, run MSYS2 UCRT64 terminal:"
        Write-Host "  pacman -Syu" -ForegroundColor Yellow
        foreach ($pkg in $missingPackages) {
            Write-Host "  pacman -S $pkg" -ForegroundColor Yellow
        }
        Write-Info ""
        Write-Info "Or use the -Install flag: .\launch-desktop-msys2.ps1 -Install"
        return $false
    }
    
    Write-Success "All required packages installed"
    return $true
}

# Install missing MSYS2 packages
function Install-MSYS2Packages {
    Write-Step "Installing required MSYS2 packages..."
    
    $bashExe = Join-Path $MSYS2Path "usr\bin\bash.exe"
    
    Write-Info "This will:"
    Write-Info "  1. Update MSYS2 package database"
    Write-Info "  2. Install Python + GTK4 + PyGObject"
    Write-Info "  3. Install libadwaita"
    Write-Info ""
    
    $confirm = Read-Host "Continue? (Y/N)"
    if ($confirm -notmatch '^[Yy]') {
        Write-Warning "Installation cancelled"
        return $false
    }
    
    $env:MSYSTEM = 'UCRT64'
    $env:CHERE_INVOKING = '1'
    
    Write-Step "Updating package database..."
    & $bashExe -lc "pacman -Sy --noconfirm"
    
    Write-Step "Installing packages..."
    $packages = "mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-python-gobject mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-libadwaita"
    & $bashExe -lc "pacman -S --noconfirm $packages"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Packages installed successfully"
        return $true
    }
    else {
        Write-Failure "Package installation failed"
        return $false
    }
}

# Check API availability
function Test-ApiAvailability {
    param([string]$Url)
    
    Write-Step "Checking API availability..."
    
    # Extract base URL without path
    $baseUrl = if ($Url -match '^(https?://[^/]+)') { $matches[1] } else { $Url }
    $healthUrl = "$baseUrl/api/v1/health"
    
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -Method GET -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        
        if ($response.StatusCode -eq 200) {
            Write-Success "API available at: $baseUrl"
            return $true
        }
    }
    catch {
        Write-Warning "API not available at: $baseUrl"
        Write-Info "Make sure the Go API is running on port 12080"
        Write-Info "Start it with: .\scripts\dev-environment-setup.ps1 -Service api"
        return $false
    }
    
    return $false
}

# Launch Desktop UI
function Start-DesktopUI {
    param(
        [string]$ProjectRoot,
        [string]$ApiUrl
    )
    
    Write-Step "Launching Desktop UI..."
    
    # Convert Windows path to MSYS2 path
    $desktopPath = Join-Path $ProjectRoot "src\desktop-ui"
    $msys2DesktopPath = ConvertTo-MSYS2Path $desktopPath
    
    Write-Info "Desktop UI path: $desktopPath"
    Write-Info "MSYS2 path: $msys2DesktopPath"
    Write-Info "API URL: $ApiUrl"
    Write-Info ""
    
    # Build MSYS2 command
    $bashExe = Join-Path $MSYS2Path "usr\bin\bash.exe"
    $command = "cd '$msys2DesktopPath' && export SIGMAVAULT_API_URL='$ApiUrl' && python main.py"
    
    Write-Step "Starting GTK4 application..."
    Write-Info "Press Ctrl+C to stop the application"
    Write-Info ""
    
    # Set MSYS2 environment and launch in UCRT64 bash
    $env:MSYSTEM = 'UCRT64'
    $env:CHERE_INVOKING = '1'
    & $bashExe -lc $command
    
    $exitCode = $LASTEXITCODE
    Write-Info ""
    
    if ($exitCode -eq 0) {
        Write-Success "Desktop UI exited normally"
    }
    else {
        Write-Warning "Desktop UI exited with code: $exitCode"
    }
    
    return $exitCode
}

# Main execution
function Main {
    Show-Banner
    
    # Get project root
    $projectRoot = Get-ProjectRoot
    Write-Info "Project root: $projectRoot"
    Write-Info ""
    
    # Check MSYS2 installation
    if (-not (Test-MSYS2Installation)) {
        exit 1
    }
    
    # Check or install packages
    if ($Install) {
        if (-not (Install-MSYS2Packages)) {
            exit 1
        }
    }
    
    if (-not (Test-MSYS2Packages)) {
        exit 1
    }
    
    # If -Check flag, stop here
    if ($Check) {
        Write-Info ""
        Write-Success "All prerequisites satisfied!"
        Write-Info "Ready to launch Desktop UI"
        exit 0
    }
    
    # Check API availability (warning only)
    Test-ApiAvailability -Url $ApiUrl | Out-Null
    
    Write-Info ""
    Write-Info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Info ""
    
    # Launch Desktop UI
    $exitCode = Start-DesktopUI -ProjectRoot $projectRoot -ApiUrl $ApiUrl
    
    exit $exitCode
}

# Run main function
try {
    Main
}
catch {
    Write-Failure "Unexpected error: $_"
    Write-Info "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}
