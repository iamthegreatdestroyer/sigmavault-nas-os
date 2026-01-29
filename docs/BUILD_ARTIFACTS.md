# SigmaVault NAS OS - Building Production Artifacts

This guide explains how to build the **downloadable production bundle** and **bootable ISO**.

---

## 🚀 Quick Start: Use GitHub Actions (Recommended)

The easiest way to build artifacts is through GitHub Actions.

### Option 1: Automatic Builds (On Tag Push)

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

This automatically triggers:

- ✅ **Release Bundle** (`sigmavault-nas-os-1.0.0.tar.gz`)
- ✅ **Bootable ISO** (`sigmavault-nas-os-1.0.0-amd64.iso`)
- ✅ **Docker Image** (pushed to GitHub Container Registry)

### Option 2: Manual Build (Workflow Dispatch)

1. Go to **Actions** tab in GitHub repository
2. Select **"Build SigmaVault NAS OS ISO"** workflow
3. Click **"Run workflow"**
4. Enter version (e.g., `1.0.0`) and architecture (`amd64` or `arm64`)
5. Click **"Run workflow"**

Download artifacts from the workflow run's **Artifacts** section.

---

## 📦 Production Bundle Contents

The release bundle (`sigmavault-nas-os-X.X.X.tar.gz`) contains:

```
sigmavault-nas-os-1.0.0/
├── bin/
│   ├── sigmavault-api-linux-amd64    # Go API binary (x86_64)
│   └── sigmavault-api-linux-arm64    # Go API binary (ARM64)
├── lib/
│   └── engined-1.0.0-py3-none-any.whl  # Python engine
├── webui/
│   └── [React dashboard build]
├── docs/
│   └── INSTALLATION.md
├── configs/
│   └── production.env.example
├── systemd/
│   ├── sigmavault-api.service
│   ├── sigmavault-engined.service
│   └── sigmavault-webui.service
├── install.sh                        # Automated installer
├── README.md
├── CHANGELOG.md
├── VERSION
└── SHA256SUMS
```

### Installing from Bundle

```bash
# Download and extract
wget https://github.com/iamthegreatdestroyer/sigmavault-nas-os/releases/download/v1.0.0/sigmavault-nas-os-1.0.0.tar.gz
tar -xzvf sigmavault-nas-os-1.0.0.tar.gz
cd sigmavault-nas-os-1.0.0

# Run installer
sudo ./install.sh

# Configure
sudo nano /etc/sigmavault/config.env
# Set SIGMAVAULT_JWT_SECRET=$(openssl rand -hex 32)

# Start services
sudo systemctl enable --now sigmavault-api sigmavault-engined
```

---

## 💿 Bootable ISO

The ISO (`sigmavault-nas-os-X.X.X-amd64.iso`) is a Debian 13 (Trixie) live system with:

- SigmaVault NAS OS pre-installed
- Auto-starting services
- Web dashboard accessible on boot

### Creating Bootable USB

**Linux:**

```bash
sudo dd if=sigmavault-nas-os-1.0.0-amd64.iso of=/dev/sdX bs=4M status=progress
sync
```

**Windows (using Rufus):**

1. Download [Rufus](https://rufus.ie/)
2. Select the ISO file
3. Select target USB drive
4. Click **Start**

**macOS:**

```bash
# Find USB device
diskutil list
# Unmount
diskutil unmountDisk /dev/diskN
# Write ISO
sudo dd if=sigmavault-nas-os-1.0.0-amd64.iso of=/dev/rdiskN bs=4m
```

### Booting & Installing

1. Boot from USB (F12/Del/F2 for boot menu)
2. Select **"SigmaVault NAS OS Live"**
3. System boots into live environment
4. Access dashboard: `http://[IP-ADDRESS]:12080`
5. For persistent installation, use included Calamares installer

---

## 🛠️ Local Build (WSL/Linux)

### Prerequisites

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install -y \
  golang-1.21 \
  python3 python3-pip python3-venv \
  nodejs npm \
  live-build debootstrap squashfs-tools xorriso \
  isolinux syslinux-efi grub-pc-bin grub-efi-amd64-bin
```

### Build Release Bundle

```bash
cd sigmavault-nas-os
./scripts/build-production.sh
```

Output: `dist/sigmavault-nas-os-1.0.0.tar.gz`

### Build Bootable ISO

```bash
cd sigmavault-nas-os
./scripts/build-iso.sh
```

Output: `live-build/sigmavault-nas-os-1.0.0-amd64.iso`

---

## 🔐 Verifying Downloads

Always verify checksums:

```bash
# Verify bundle
sha256sum -c sigmavault-nas-os-1.0.0.tar.gz.sha256

# Verify ISO
sha256sum -c sigmavault-nas-os-1.0.0-amd64.iso.sha256
```

---

## 📋 Build Matrix

| Component     | Source         | Output                               |
| ------------- | -------------- | ------------------------------------ |
| Go API        | `src/api/`     | `sigmavault-api-linux-{amd64,arm64}` |
| Python Engine | `src/engined/` | `engined-*.whl`                      |
| WebUI         | `src/webui/`   | `dist/` (React build)                |
| ISO           | `live-build/`  | `*.iso`                              |

---

## 🎯 Supported Architectures

| Architecture | CPU Examples                  | Status          |
| ------------ | ----------------------------- | --------------- |
| `amd64`      | Intel/AMD x86_64              | ✅ Full support |
| `arm64`      | Raspberry Pi 4/5, Apple M1/M2 | ✅ Full support |

---

## ❓ Troubleshooting

### ISO Build Fails

- Ensure you're running on Debian/Ubuntu
- Check `live-build/build.log` for errors
- Verify all dependencies are installed

### Bundle Missing Components

- Run `./scripts/validate-production.sh` to check requirements
- Ensure Go, Python, Node.js are in PATH

### Permission Denied on Install

- Run `install.sh` with `sudo`
- Check SELinux/AppArmor policies

---

## 📞 Support

- **Issues**: https://github.com/iamthegreatdestroyer/sigmavault-nas-os/issues
- **Discussions**: https://github.com/iamthegreatdestroyer/sigmavault-nas-os/discussions
