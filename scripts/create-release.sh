#!/usr/bin/env bash
# =============================================================================
# SigmaVault NAS OS - Release Package Generator
# @FORGE + @FLUX Collaboration
# =============================================================================
set -euo pipefail

# Configuration
VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
RELEASE_DIR="release-${VERSION}"
TIMESTAMP=$(date -u +%Y%m%d%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Header
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║           SigmaVault NAS OS - Release Package Generator                   ║"
echo "║                     Version: ${VERSION}                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# Stage 1: Prepare Release Directory
# =============================================================================
log_info "Stage 1/6: Preparing release directory..."

rm -rf "${RELEASE_DIR}"
mkdir -p "${RELEASE_DIR}"/{binaries/{linux-amd64,linux-arm64},packages,docs,configs}

log_success "Release directory created: ${RELEASE_DIR}"

# =============================================================================
# Stage 2: Build Binaries
# =============================================================================
log_info "Stage 2/6: Building production binaries..."

cd src/api

# Linux AMD64
log_info "Building linux-amd64..."
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags="-s -w -X main.Version=${VERSION}" -o "../../${RELEASE_DIR}/binaries/linux-amd64/sigmavault-api" .

# Linux ARM64
log_info "Building linux-arm64..."
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -ldflags="-s -w -X main.Version=${VERSION}" -o "../../${RELEASE_DIR}/binaries/linux-arm64/sigmavault-api" .

cd ../..
log_success "Go binaries built for linux-amd64 and linux-arm64"

# =============================================================================
# Stage 3: Package Python Engine
# =============================================================================
log_info "Stage 3/6: Packaging Python engine..."

cd src/engined

# Create distributable package
python -m pip wheel . -w "../../${RELEASE_DIR}/packages/" --no-deps 2>/dev/null || {
    log_warn "pip wheel failed, creating source archive..."
    tar -czf "../../${RELEASE_DIR}/packages/sigmavault-engined-${VERSION}.tar.gz" \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        .
}

cd ../..
log_success "Python engine packaged"

# =============================================================================
# Stage 4: Build WebUI
# =============================================================================
log_info "Stage 4/6: Building WebUI..."

cd src/webui

if command -v pnpm &>/dev/null; then
    pnpm install --frozen-lockfile 2>/dev/null || pnpm install
    pnpm build
    cp -r dist "../../${RELEASE_DIR}/webui"
elif command -v npm &>/dev/null; then
    npm ci 2>/dev/null || npm install
    npm run build
    cp -r dist "../../${RELEASE_DIR}/webui"
else
    log_warn "No Node.js package manager found, skipping WebUI build"
fi

cd ../..
log_success "WebUI built"

# =============================================================================
# Stage 5: Copy Documentation and Configs
# =============================================================================
log_info "Stage 5/6: Copying documentation and configs..."

# Documentation
cp README.md "${RELEASE_DIR}/docs/"
cp CHANGELOG.md "${RELEASE_DIR}/docs/"
cp docs/INSTALLATION.md "${RELEASE_DIR}/docs/"
cp -r docs/*.md "${RELEASE_DIR}/docs/" 2>/dev/null || true

# Systemd services
mkdir -p "${RELEASE_DIR}/configs/systemd"
cp -r live-build/config/includes.chroot/etc/systemd/system/*.service "${RELEASE_DIR}/configs/systemd/" 2>/dev/null || true

# Docker files
mkdir -p "${RELEASE_DIR}/configs/docker"
cp docker/Dockerfile.* "${RELEASE_DIR}/configs/docker/" 2>/dev/null || true

# Build scripts
mkdir -p "${RELEASE_DIR}/scripts"
cp scripts/*.sh "${RELEASE_DIR}/scripts/" 2>/dev/null || true

log_success "Documentation and configs copied"

# =============================================================================
# Stage 6: Generate Checksums and Archive
# =============================================================================
log_info "Stage 6/6: Generating checksums and final archive..."

cd "${RELEASE_DIR}"

# Generate checksums for all files
find . -type f ! -name "*.sha256" | while read -r file; do
    sha256sum "$file" >> "checksums.sha256"
done

cd ..

# Create final release archive
ARCHIVE_NAME="sigmavault-nas-os-${VERSION}-release.tar.gz"
tar -czf "${ARCHIVE_NAME}" "${RELEASE_DIR}"

# Generate archive checksum
sha256sum "${ARCHIVE_NAME}" > "${ARCHIVE_NAME}.sha256"

log_success "Release archive created: ${ARCHIVE_NAME}"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                    Release Package Complete!                              ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Version:    ${VERSION}                                                       ║"
echo "║  Archive:    ${ARCHIVE_NAME}                                 ║"
echo "║  Directory:  ${RELEASE_DIR}/                                              ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Contents:"
echo "  ├── binaries/"
echo "  │   ├── linux-amd64/sigmavault-api"
echo "  │   └── linux-arm64/sigmavault-api"
echo "  ├── packages/"
echo "  │   └── sigmavault-engined-${VERSION}.tar.gz"
echo "  ├── webui/"
echo "  ├── docs/"
echo "  ├── configs/"
echo "  │   ├── systemd/"
echo "  │   └── docker/"
echo "  ├── scripts/"
echo "  └── checksums.sha256"
echo ""

log_success "Release ${VERSION} ready for deployment!"
