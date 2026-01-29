#!/bin/bash
# SigmaVault NAS OS - Production Build Script (@FORGE)
# Automated build orchestration for all components

set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════
VERSION="${VERSION:-$(git describe --tags --always 2>/dev/null || echo "dev")}"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BUILD_DIR="build"
DIST_DIR="dist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ═══════════════════════════════════════════════════════════════════════════
# Pre-flight Checks
# ═══════════════════════════════════════════════════════════════════════════
preflight_check() {
    log_info "Running pre-flight checks..."
    
    local errors=0
    
    # Check Go
    if ! command -v go &> /dev/null; then
        log_error "Go is not installed"
        ((errors++))
    else
        log_success "Go $(go version | awk '{print $3}')"
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        ((errors++))
    else
        log_success "Python $(python3 --version | awk '{print $2}')"
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_warn "Node.js not installed - WebUI build will be skipped"
    else
        log_success "Node.js $(node --version)"
    fi
    
    # Check pnpm
    if ! command -v pnpm &> /dev/null; then
        log_warn "pnpm not installed - attempting npm fallback for WebUI"
    fi
    
    if [ $errors -gt 0 ]; then
        log_error "Pre-flight checks failed with $errors errors"
        exit 1
    fi
    
    log_success "All pre-flight checks passed"
}

# ═══════════════════════════════════════════════════════════════════════════
# Test Execution (@ECLIPSE)
# ═══════════════════════════════════════════════════════════════════════════
run_tests() {
    log_info "Running test suites..."
    
    # Python tests
    log_info "Running Python tests..."
    cd src/engined
    if python3 -m pytest --tb=short -q; then
        log_success "Python tests passed"
    else
        log_error "Python tests failed"
        exit 1
    fi
    cd ../..
    
    # Go tests
    log_info "Running Go tests..."
    cd src/api
    if go test -v -race ./...; then
        log_success "Go tests passed"
    else
        log_error "Go tests failed"
        exit 1
    fi
    cd ../..
    
    log_success "All tests passed"
}

# ═══════════════════════════════════════════════════════════════════════════
# Build Go API (@FORGE)
# ═══════════════════════════════════════════════════════════════════════════
build_go_api() {
    log_info "Building Go API..."
    
    mkdir -p "$BUILD_DIR/api"
    cd src/api
    
    local ldflags="-s -w -X main.version=${VERSION} -X main.buildDate=${BUILD_DATE}"
    
    # Build for Linux AMD64
    log_info "Building for linux/amd64..."
    GOOS=linux GOARCH=amd64 CGO_ENABLED=0 \
        go build -ldflags="$ldflags" -o "../../${BUILD_DIR}/api/sigmavault-api-linux-amd64" .
    
    # Build for Linux ARM64
    log_info "Building for linux/arm64..."
    GOOS=linux GOARCH=arm64 CGO_ENABLED=0 \
        go build -ldflags="$ldflags" -o "../../${BUILD_DIR}/api/sigmavault-api-linux-arm64" .
    
    cd ../..
    
    log_success "Go API built successfully"
}

# ═══════════════════════════════════════════════════════════════════════════
# Build Python Package (@FORGE)
# ═══════════════════════════════════════════════════════════════════════════
build_python_package() {
    log_info "Building Python package..."
    
    mkdir -p "$BUILD_DIR/python"
    cd src/engined
    
    # Install build dependencies
    python3 -m pip install build wheel --quiet
    
    # Build wheel
    python3 -m build --wheel --outdir "../../${BUILD_DIR}/python"
    
    cd ../..
    
    log_success "Python package built successfully"
}

# ═══════════════════════════════════════════════════════════════════════════
# Build WebUI (@CANVAS)
# ═══════════════════════════════════════════════════════════════════════════
build_webui() {
    if ! command -v node &> /dev/null; then
        log_warn "Skipping WebUI build - Node.js not installed"
        return 0
    fi
    
    log_info "Building WebUI..."
    
    mkdir -p "$BUILD_DIR/webui"
    cd src/webui
    
    # Install dependencies
    if command -v pnpm &> /dev/null; then
        pnpm install --frozen-lockfile 2>/dev/null || pnpm install
    else
        npm install
    fi
    
    # Build production
    if command -v pnpm &> /dev/null; then
        pnpm build
    else
        npm run build
    fi
    
    # Copy to build dir
    cp -r dist/* "../../${BUILD_DIR}/webui/"
    
    cd ../..
    
    log_success "WebUI built successfully"
}

# ═══════════════════════════════════════════════════════════════════════════
# Package Distribution (@FLUX)
# ═══════════════════════════════════════════════════════════════════════════
package_distribution() {
    log_info "Creating distribution package..."
    
    mkdir -p "$DIST_DIR"
    
    # Create tarball
    local tarball="sigmavault-nas-os-${VERSION}.tar.gz"
    tar -czf "${DIST_DIR}/${tarball}" \
        -C "$BUILD_DIR" \
        api python webui 2>/dev/null || \
    tar -czf "${DIST_DIR}/${tarball}" \
        -C "$BUILD_DIR" \
        api python
    
    # Generate checksums
    cd "$DIST_DIR"
    sha256sum "$tarball" > SHA256SUMS.txt
    sha256sum ../build/api/* >> SHA256SUMS.txt 2>/dev/null || true
    sha256sum ../build/python/* >> SHA256SUMS.txt 2>/dev/null || true
    cd ..
    
    log_success "Distribution package created: ${DIST_DIR}/${tarball}"
}

# ═══════════════════════════════════════════════════════════════════════════
# Generate Release Notes
# ═══════════════════════════════════════════════════════════════════════════
generate_release_notes() {
    log_info "Generating release notes..."
    
    cat > "${DIST_DIR}/RELEASE_NOTES.md" << EOF
# SigmaVault NAS OS ${VERSION}

**Release Date:** $(date -u +"%Y-%m-%d")
**Build Date:** ${BUILD_DATE}

## Components

### Go API Server
- \`sigmavault-api-linux-amd64\` - AMD64 binary
- \`sigmavault-api-linux-arm64\` - ARM64 binary (Raspberry Pi 4/5)

### Python Engine
- \`engined-*.whl\` - Python wheel with RPC server, agent swarm, compression

### WebUI
- React 18 + TypeScript + TailwindCSS dashboard

## Features

- **ΣLANG Compression**: Semantic codebooks with transformer embeddings (10-50x on structured data)
- **Quantum-Resistant Security**: CRYSTALS-Kyber-768 + AES-256-GCM
- **40-Agent AI Swarm**: MNEMONIC memory system, 3-tier hierarchy
- **Alignment Safety**: ValueAlignmentChecker, ConstraintVerifier, immutable audit trails
- **Filesystem Support**: ZFS and Btrfs with automatic selection

## Installation

\`\`\`bash
# Extract release
tar -xzf sigmavault-nas-os-${VERSION}.tar.gz

# Install Python engine
pip install python/engined-*.whl

# Copy API binary
sudo cp api/sigmavault-api-linux-amd64 /usr/local/bin/sigmavault-api
sudo chmod +x /usr/local/bin/sigmavault-api

# Start services
sigmavault-api &
python -m engined.rpc.server &
\`\`\`

## Verification

\`\`\`bash
# Verify checksums
sha256sum -c SHA256SUMS.txt
\`\`\`

## Changelog

$(git log --oneline -20 2>/dev/null || echo "See GitHub releases for full changelog")
EOF

    log_success "Release notes generated"
}

# ═══════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════
main() {
    echo "═══════════════════════════════════════════════════════════════════"
    echo "  SigmaVault NAS OS - Production Build"
    echo "  Version: ${VERSION}"
    echo "═══════════════════════════════════════════════════════════════════"
    echo
    
    # Clean previous builds
    rm -rf "$BUILD_DIR" "$DIST_DIR"
    mkdir -p "$BUILD_DIR" "$DIST_DIR"
    
    # Execute build pipeline
    preflight_check
    
    case "${1:-all}" in
        test)
            run_tests
            ;;
        build)
            build_go_api
            build_python_package
            build_webui
            ;;
        package)
            package_distribution
            generate_release_notes
            ;;
        all)
            run_tests
            build_go_api
            build_python_package
            build_webui
            package_distribution
            generate_release_notes
            ;;
        *)
            echo "Usage: $0 {test|build|package|all}"
            exit 1
            ;;
    esac
    
    echo
    echo "═══════════════════════════════════════════════════════════════════"
    log_success "Production build completed successfully!"
    echo "═══════════════════════════════════════════════════════════════════"
}

main "$@"
