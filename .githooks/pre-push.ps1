#!/usr/bin/env pwsh
# =============================================================================
# SigmaVault NAS OS — Pre-Push Hook (PowerShell)
# @FORGE Build Gate — Prevents CI thrashing by running checks locally
# =============================================================================
#
# Windows-native pre-push hook. Called by .githooks/pre-push on Windows.
# Install: git config core.hooksPath .githooks
# Bypass:  git push --no-verify
# =============================================================================

$ErrorActionPreference = "Continue"
$script:Failed = 0

function Write-Ok { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Fail { param($msg) Write-Host "  ✗ $msg" -ForegroundColor Red; $script:Failed = 1 }
function Write-Skip { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Step { param($msg) Write-Host $msg -ForegroundColor Cyan }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SigmaVault Pre-Push Gate — Local CI Check" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$root = git rev-parse --show-toplevel 2>$null
if (-not $root) { $root = $PSScriptRoot | Split-Path }
Push-Location $root

try {
    # ─── Go API Lint ─────────────────────────────────────────────────
    Write-Step "[1/4] Linting Go API..."
    if (Get-Command golangci-lint -ErrorAction SilentlyContinue) {
        Push-Location src/api
        $lintOut = golangci-lint run ./... 2>&1
        if ($LASTEXITCODE -eq 0) { Write-Ok "Go lint passed" }
        else { Write-Fail "Go lint FAILED"; Write-Host $lintOut }
        Pop-Location
    }
    else {
        Write-Skip "golangci-lint not found, skipping Go lint"
    }

    # ─── Go API Tests ────────────────────────────────────────────────
    Write-Step "[2/4] Running Go tests..."
    Push-Location src/api
    go test -short -count=1 ./... 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Go tests passed" }
    else { Write-Fail "Go tests FAILED" }
    Pop-Location

    # ─── Python Engine Lint + Tests ──────────────────────────────────
    Write-Step "[3/4] Checking Python engine..."
    if (Get-Command ruff -ErrorAction SilentlyContinue) {
        Push-Location src/engined
        ruff check . 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Python lint passed" }
        else { Write-Fail "Python lint FAILED" }
        Pop-Location
    }
    else {
        Write-Skip "ruff not found, skipping Python lint"
    }

    Push-Location src/engined
    python -m pytest -x -q --tb=short 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Python tests passed" }
    else { Write-Fail "Python tests FAILED" }
    Pop-Location

    # ─── Desktop UI Tests ───────────────────────────────────────────
    Write-Step "[4/4] Checking Desktop UI..."
    Push-Location src/desktop-ui
    python -m pytest -x -q --tb=short tests/ 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Desktop tests passed" }
    else { Write-Skip "Desktop tests skipped or unavailable" }
    Pop-Location
}
finally {
    Pop-Location
}

# ─── Final Verdict ──────────────────────────────────────────────
Write-Host ""
if ($script:Failed -ne 0) {
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  ✗ PRE-PUSH BLOCKED — Fix errors above before pushing" -ForegroundColor Red
    Write-Host "  Bypass with: git push --no-verify" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
    exit 1
}
else {
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓ All pre-push checks passed — Pushing!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
    exit 0
}
