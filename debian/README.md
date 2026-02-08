# Debian Packaging for SigmaVault Desktop

This directory contains Debian packaging files for creating `.deb` packages of SigmaVault Desktop UI.

## Files

- **control**: Package metadata, dependencies, and description
- **rules**: Build rules (Makefile for debhelper)
- **changelog**: Version history in Debian format
- **compat**: Debhelper compatibility level (13)
- **source/format**: Source package format (3.0 quilt)
- **sigmavault-desktop.sh**: Launcher script installed to `/usr/bin/sigmavault-desktop`

## Prerequisites

Install build dependencies:

```bash
# Debian/Ubuntu
sudo apt install debhelper dh-python python3-all python3-setuptools

# For testing the package
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adwaita-1 python3-aiohttp
```

## Building

From the repository root:

```bash
# Build the package
dpkg-buildpackage -us -uc -b

# Or using debuild
debuild -us -uc -b

# The .deb file will be created in the parent directory
ls ../sigmavault-desktop_*.deb
```

## Installing

```bash
# Install the package
sudo dpkg -i ../sigmavault-desktop_0.1.0-1_all.deb

# Fix any missing dependencies
sudo apt --fix-broken install
```

## Testing

After installation:

```bash
# Run from command line
sigmavault-desktop

# Or launch from application menu
```

## Uninstalling

```bash
sudo apt remove sigmavault-desktop
```

## Integration with live-build

To include in the SigmaVault NAS OS ISO:

1. Build the .deb package
2. Copy to `live-build/config/packages.chroot/`
3. Or add to a local repository in `live-build/config/archives/`

Example for live-build integration:

```bash
# Build the package
dpkg-buildpackage -us -uc -b

# Copy to live-build packages directory
cp ../sigmavault-desktop_0.1.0-1_all.deb live-build/config/packages.chroot/
```

Then rebuild the ISO with:

```bash
cd live-build
sudo lb build
```

## Package Contents

The installed package provides:

- `/usr/bin/sigmavault-desktop` - Launcher script
- `/usr/lib/python3/dist-packages/sigmavault_desktop/` - Python application
- `/usr/share/applications/com.sigmavault.desktop.desktop` - Desktop entry
- `/usr/share/metainfo/com.sigmavault.desktop.metainfo.xml` - AppStream metadata
- `/usr/share/icons/hicolor/scalable/apps/com.sigmavault.desktop.svg` - Icon
- `/usr/share/sigmavault-desktop/style.css` - Stylesheet
- `/usr/share/doc/sigmavault-desktop/` - Documentation

## Dependencies

Runtime dependencies (automatically installed):

- python3 (>= 3.11)
- python3-gi (>= 3.42.0)
- gir1.2-gtk-4.0 (>= 4.10.0)
- gir1.2-adwaita-1 (>= 1.4.0)
- python3-aiohttp (>= 3.9.0)

Recommended (not required but suggested):

- sigmavault-api - Go API backend
- sigmavault-engined - Python RPC engine

## Notes

- The package is architecture-independent (`Architecture: all`)
- Follows Debian Policy 4.6.2
- Uses debhelper compatibility level 13
- PyGObject and GTK bindings are system dependencies
- Tests are skipped during package build (require GTK runtime)

## TODO

- [ ] Test package build on clean Debian/Ubuntu system
- [ ] Verify integration with live-build ISO
- [ ] Add systemd service file for backend dependencies
- [ ] Create separate packages for API and engine if needed
- [ ] Set up local apt repository for SigmaVault packages
