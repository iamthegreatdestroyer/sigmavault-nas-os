#!/bin/bash
set -e

echo "==========================================="
echo "  SigmaVault NAS OS - Build Script"
echo "==========================================="
echo "Target Architecture: ${TARGET_ARCH:-amd64}"
echo ""

# Build packages
echo "[1/3] Building Debian packages..."
cd packages
for pkg in */; do
    if [ -d "$pkg/debian" ]; then
        echo "  → Building $pkg"
        cd "$pkg"
        dpkg-buildpackage -us -uc -b
        cd ..
    fi
done
cd ..

# Copy packages to live-build
echo ""
echo "[2/3] Copying packages to live-build..."
mkdir -p live-build/config/packages.chroot/
cp packages/*.deb live-build/config/packages.chroot/ 2>/dev/null || echo "  No .deb files found yet"

# Build ISO
echo ""
echo "[3/3] Building ISO image..."
cd live-build
lb clean --purge 2>/dev/null || true
lb config
lb build

echo ""
echo "==========================================="
echo "  Build Complete!"
echo "==========================================="
ls -lh *.iso 2>/dev/null || echo "ISO not found - check build logs"
