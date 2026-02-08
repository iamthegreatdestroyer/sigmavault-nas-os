# SigmaVault Desktop Flatpak Packaging

This directory contains files for packaging SigmaVault Desktop as a Flatpak application.

## Files

- **com.sigmavault.desktop.yml**: Flatpak manifest file defining the build process
- **sigmavault-desktop**: Launcher script that runs the Python application
- **com.sigmavault.desktop.desktop**: XDG desktop entry (to be created)
- **com.sigmavault.desktop.metainfo.xml**: AppStream metadata (to be created)
- **icons/**: Application icons in various formats and sizes (to be created)

## Prerequisites

Install Flatpak and flatpak-builder:

```bash
# Debian/Ubuntu
sudo apt install flatpak flatpak-builder

# Arch
sudo pacman -S flatpak flatpak-builder

# Fedora
sudo dnf install flatpak flatpak-builder
```

Add Flathub repository (provides GNOME runtime):

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

Install GNOME Platform runtime and SDK:

```bash
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
```

## Building

From the repository root:

```bash
# Build and install locally (user installation)
flatpak-builder build-dir flatpak/com.sigmavault.desktop.yml --force-clean --install --user

# Or build to a repository
flatpak-builder --repo=repo build-dir flatpak/com.sigmavault.desktop.yml --force-clean

# Create a bundle for distribution
flatpak build-bundle repo sigmavault-desktop.flatpak com.sigmavault.desktop
```

## Running

After installation:

```bash
flatpak run com.sigmavault.desktop
```

## Testing

Run with verbose output:

```bash
flatpak run --log-session-bus --log-system-bus com.sigmavault.desktop
```

Run with shell access for debugging:

```bash
flatpak run --command=sh com.sigmavault.desktop
```

## Notes

- The application requires network access to connect to the SigmaVault API backend (localhost:12080)
- Currently configured for GNOME Platform 47 (GTK 4 + libadwaita 1)
- Python 3.12 is provided by the GNOME SDK
- PyGObject bindings are included in the runtime

## TODO

- [ ] Create desktop file (com.sigmavault.desktop.desktop)
- [ ] Create AppStream metadata (com.sigmavault.desktop.metainfo.xml)
- [ ] Create application icons (SVG + PNG sizes)
- [ ] Update dependency checksums for production builds
- [ ] Test on clean Flatpak environment
- [ ] Submit to Flathub (optional)
