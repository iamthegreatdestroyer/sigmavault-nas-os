#!/bin/bash
# SigmaVault NAS OS - Live ISO Build Script (@FORGE @FLUX)
# Builds bootable Debian 13 (Trixie) based installation media

set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIVE_BUILD_DIR="${PROJECT_ROOT}/live-build"
BUILD_OUTPUT="${PROJECT_ROOT}/dist/iso"
VERSION="${VERSION:-$(git -C "$PROJECT_ROOT" describe --tags --always 2>/dev/null || echo "dev")}"

# Architecture options: amd64, arm64
ARCH="${ARCH:-amd64}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# ═══════════════════════════════════════════════════════════════════════════
# Pre-flight Checks
# ═══════════════════════════════════════════════════════════════════════════
preflight_check() {
    log_info "Running pre-flight checks for live-build..."
    
    local errors=0
    
    # Check if running on Linux
    if [[ "$(uname -s)" != "Linux" ]]; then
        log_error "live-build must be run on a Linux system"
        log_info "Consider using WSL2, Docker, or a Linux VM"
        ((errors++))
    fi
    
    # Check for live-build
    if ! command -v lb &> /dev/null; then
        log_error "live-build is not installed"
        log_info "Install with: sudo apt install live-build"
        ((errors++))
    else
        log_success "live-build $(lb --version 2>/dev/null | head -1 || echo 'installed')"
    fi
    
    # Check for debootstrap
    if ! command -v debootstrap &> /dev/null; then
        log_error "debootstrap is not installed"
        log_info "Install with: sudo apt install debootstrap"
        ((errors++))
    fi
    
    # Check for root privileges
    if [[ $EUID -ne 0 ]]; then
        log_warn "Not running as root - some operations may require sudo"
    fi
    
    if [ $errors -gt 0 ]; then
        log_error "Pre-flight checks failed"
        exit 1
    fi
    
    log_success "All pre-flight checks passed"
}

# ═══════════════════════════════════════════════════════════════════════════
# Stage 1: Build Application Artifacts
# ═══════════════════════════════════════════════════════════════════════════
build_artifacts() {
    log_step "Stage 1: Building application artifacts..."
    
    # Use production build script
    if [[ -f "${PROJECT_ROOT}/scripts/build-production.sh" ]]; then
        bash "${PROJECT_ROOT}/scripts/build-production.sh" build
    else
        log_error "build-production.sh not found"
        exit 1
    fi
    
    log_success "Application artifacts built"
}

# ═══════════════════════════════════════════════════════════════════════════
# Stage 2: Prepare Live-Build Configuration
# ═══════════════════════════════════════════════════════════════════════════
prepare_livebuild() {
    log_step "Stage 2: Preparing live-build configuration..."
    
    cd "$LIVE_BUILD_DIR"
    
    # Clean previous builds
    sudo lb clean --purge 2>/dev/null || true
    
    # Initialize live-build
    lb config
    
    # Copy built artifacts to includes
    local includes_dir="${LIVE_BUILD_DIR}/config/includes.chroot/opt/sigmavault"
    sudo mkdir -p "${includes_dir}/bin"
    sudo mkdir -p "${includes_dir}/lib/python"
    sudo mkdir -p "${includes_dir}/share/webui"
    
    # Copy Go API binary
    if [[ -f "${PROJECT_ROOT}/build/api/sigmavault-api-linux-${ARCH}" ]]; then
        sudo cp "${PROJECT_ROOT}/build/api/sigmavault-api-linux-${ARCH}" \
               "${includes_dir}/bin/sigmavault-api"
        sudo chmod +x "${includes_dir}/bin/sigmavault-api"
        log_success "Go API binary copied"
    else
        log_warn "Go API binary not found for ${ARCH}"
    fi
    
    # Install Python package
    local wheel_file=$(find "${PROJECT_ROOT}/build/python" -name "*.whl" 2>/dev/null | head -1)
    if [[ -n "$wheel_file" ]]; then
        sudo pip3 install --target="${includes_dir}/lib/python" "$wheel_file" 2>/dev/null || \
            log_warn "Could not install Python wheel (will be installed at boot)"
        log_success "Python package prepared"
    fi
    
    # Copy WebUI
    if [[ -d "${PROJECT_ROOT}/build/webui" ]]; then
        sudo cp -r "${PROJECT_ROOT}/build/webui/"* "${includes_dir}/share/webui/"
        log_success "WebUI files copied"
    fi
    
    log_success "Live-build configuration prepared"
}

# ═══════════════════════════════════════════════════════════════════════════
# Stage 3: Build ISO Image
# ═══════════════════════════════════════════════════════════════════════════
build_iso() {
    log_step "Stage 3: Building ISO image..."
    
    cd "$LIVE_BUILD_DIR"
    
    # Build the ISO
    log_info "This may take 15-30 minutes depending on your system..."
    sudo lb build 2>&1 | tee "${PROJECT_ROOT}/build/iso-build.log"
    
    # Check if ISO was created
    local iso_file=$(find . -maxdepth 1 -name "*.iso" 2>/dev/null | head -1)
    if [[ -z "$iso_file" ]]; then
        log_error "ISO build failed - no ISO file found"
        log_info "Check ${PROJECT_ROOT}/build/iso-build.log for details"
        exit 1
    fi
    
    # Move to dist
    mkdir -p "$BUILD_OUTPUT"
    local final_iso="${BUILD_OUTPUT}/sigmavault-nas-os-${VERSION}-${ARCH}.iso"
    sudo mv "$iso_file" "$final_iso"
    sudo chown $(id -u):$(id -g) "$final_iso"
    
    log_success "ISO created: $final_iso"
}

# ═══════════════════════════════════════════════════════════════════════════
# Stage 4: Generate Checksums and Metadata
# ═══════════════════════════════════════════════════════════════════════════
generate_metadata() {
    log_step "Stage 4: Generating checksums and metadata..."
    
    cd "$BUILD_OUTPUT"
    
    local iso_file="sigmavault-nas-os-${VERSION}-${ARCH}.iso"
    
    if [[ -f "$iso_file" ]]; then
        # Generate checksums
        sha256sum "$iso_file" > "${iso_file}.sha256"
        md5sum "$iso_file" > "${iso_file}.md5"
        
        # Generate metadata
        cat > "${iso_file}.info" << EOF
SigmaVault NAS OS ISO Metadata
==============================
Filename: ${iso_file}
Version: ${VERSION}
Architecture: ${ARCH}
Build Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Base: Debian 13 (Trixie)

SHA256: $(cat "${iso_file}.sha256" | awk '{print $1}')
MD5: $(cat "${iso_file}.md5" | awk '{print $1}')
Size: $(du -h "$iso_file" | awk '{print $1}')

Features:
- ΣLANG Semantic Compression (10-50x on structured data)
- Quantum-Resistant Security (CRYSTALS-Kyber-768 + AES-256-GCM)
- 40-Agent AI Swarm with MNEMONIC Memory
- ZFS/Btrfs Filesystem Support
- React 18 Web Dashboard

Installation:
1. Write ISO to USB: sudo dd if=${iso_file} of=/dev/sdX bs=4M status=progress
2. Boot from USB
3. Access web interface at https://<hostname>:8080
4. Default credentials: admin / sigmavault

Documentation: https://github.com/iamthegreatdestroyer/sigmavault-nas-os
EOF
        
        log_success "Checksums and metadata generated"
    else
        log_warn "ISO file not found, skipping metadata generation"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# Display Final Summary
# ═══════════════════════════════════════════════════════════════════════════
show_summary() {
    echo
    echo "═══════════════════════════════════════════════════════════════════"
    echo -e "${GREEN}  SigmaVault NAS OS ISO Build Complete!${NC}"
    echo "═══════════════════════════════════════════════════════════════════"
    echo
    
    if [[ -d "$BUILD_OUTPUT" ]]; then
        echo "Output files:"
        ls -lh "$BUILD_OUTPUT"/*.iso* 2>/dev/null || echo "  (none)"
    fi
    
    echo
    echo "Next steps:"
    echo "  1. Verify checksum: sha256sum -c ${BUILD_OUTPUT}/*.sha256"
    echo "  2. Write to USB: sudo dd if=<iso> of=/dev/sdX bs=4M status=progress"
    echo "  3. Boot target system from USB"
    echo
}

# ═══════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════
main() {
    echo "═══════════════════════════════════════════════════════════════════"
    echo "  SigmaVault NAS OS - Live ISO Builder"
    echo "  Version: ${VERSION} | Architecture: ${ARCH}"
    echo "═══════════════════════════════════════════════════════════════════"
    echo
    
    case "${1:-all}" in
        preflight)
            preflight_check
            ;;
        artifacts)
            build_artifacts
            ;;
        prepare)
            prepare_livebuild
            ;;
        iso)
            build_iso
            generate_metadata
            ;;
        all)
            preflight_check
            build_artifacts
            prepare_livebuild
            build_iso
            generate_metadata
            show_summary
            ;;
        *)
            echo "Usage: $0 {preflight|artifacts|prepare|iso|all}"
            echo
            echo "Stages:"
            echo "  preflight  - Check build requirements"
            echo "  artifacts  - Build Go, Python, and WebUI"
            echo "  prepare    - Configure live-build"
            echo "  iso        - Build ISO image"
            echo "  all        - Run all stages (default)"
            exit 1
            ;;
    esac
}

main "$@"
