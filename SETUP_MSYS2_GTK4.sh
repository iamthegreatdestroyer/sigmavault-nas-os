#!/bin/bash
# MSYS2 GTK4 Development Environment Setup
# This script installs all required packages for desktop-ui development

set -e  # Exit on error

# Initialize MinGW64 environment
export PATH="/mingw64/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PKG_CONFIG_PATH="/mingw64/lib/pkgconfig:/mingw64/share/pkgconfig"

echo "=== MSYS2 GTK4 Setup for SigmaVault Desktop UI ==="
echo ""
echo "Step 1: Update package manager..."
pacman -Sy --noconfirm

echo ""
echo "Step 2: Install GTK4 and libadwaita development packages..."
pacman -S --noconfirm \
    mingw-w64-x86_64-gtk4 \
    mingw-w64-x86_64-libadwaita \
    mingw-w64-x86_64-gobject-introspection \
    mingw-w64-x86_64-pkg-config \
    mingw-w64-x86_64-python \
    mingw-w64-x86_64-python-pip \
    mingw-w64-x86_64-toolchain \
    mingw-w64-x86_64-cmake \
    mingw-w64-x86_64-ninja \
    mingw-w64-x86_64-meson \
    mingw-w64-x86_64-rust

echo ""
echo "Step 3: Verify GTK4 installation..."
pkg-config --modversion gtk4
echo "✅ GTK4 found: $(pkg-config --modversion gtk4)"

echo ""
echo "Step 4: Navigate to desktop-ui directory..."
cd /s/sigmavault-nas-os/src/desktop-ui || exit 1

echo ""
echo "Step 5: Create Python virtual environment..."
python -m venv .venv

echo ""
echo "Step 6: Activate virtual environment..."
source .venv/Scripts/activate

echo ""
echo "Step 7: Install Python dependencies including PyGObject..."
# Skip pip upgrade in MSYS2 context, just install packages directly
pip install -e . --no-cache-dir

echo ""
echo "Step 8: Verify PyGObject installation..."
python -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); from gi.repository import Gtk, Adw; print('✅ PyGObject, GTK4, and libadwaita imports successful!')"

echo ""
echo "=== SETUP COMPLETE ==="
echo ""
echo "To run the desktop app:"
echo "  1. Open MSYS2 MinGW64 terminal (S:\\msys64\\mingw64.exe)"
echo "  2. cd /s/sigmavault-nas-os/src/desktop-ui"
echo "  3. source .venv/Scripts/activate"
echo "  4. python main.py"
echo ""
