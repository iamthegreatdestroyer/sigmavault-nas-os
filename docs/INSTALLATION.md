# SigmaVault NAS OS Installation Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Download](#download)
3. [Creating Bootable Media](#creating-bootable-media)
4. [Installation](#installation)
5. [First Boot Configuration](#first-boot-configuration)
6. [Accessing the Dashboard](#accessing-the-dashboard)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Component | Requirement                             |
| --------- | --------------------------------------- |
| CPU       | 64-bit processor (AMD64 or ARM64)       |
| RAM       | 4 GB minimum, 8 GB recommended          |
| Storage   | 32 GB for OS, additional drives for NAS |
| Network   | Ethernet recommended                    |

### Supported Hardware

- **x86_64**: Intel/AMD 64-bit processors
- **ARM64**: Raspberry Pi 4/5 (4GB+ RAM)

### Recommended Hardware

- ECC RAM for data integrity
- SATA/NVMe drives for storage pools
- Dedicated network interface (1Gbps+)
- UPS for power protection

---

## Download

### Official Releases

Download the latest ISO from GitHub Releases:

```bash
# AMD64 (Intel/AMD 64-bit)
wget https://github.com/sigmavault/sigmavault-nas-os/releases/download/v1.0.0/sigmavault-nas-os-1.0.0-amd64.iso

# ARM64 (Raspberry Pi 4/5)
wget https://github.com/sigmavault/sigmavault-nas-os/releases/download/v1.0.0/sigmavault-nas-os-1.0.0-arm64.iso
```

### Verify Download

```bash
# Verify SHA256 checksum
sha256sum -c sigmavault-nas-os-1.0.0-amd64.iso.sha256
```

---

## Creating Bootable Media

### Linux (Recommended)

```bash
# Identify your USB device (be careful!)
lsblk

# Write ISO to USB (replace /dev/sdX with your device)
sudo dd if=sigmavault-nas-os-1.0.0-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

### Windows

1. Download [Rufus](https://rufus.ie/) or [balenaEtcher](https://www.balena.io/etcher/)
2. Select the SigmaVault ISO
3. Select your USB drive
4. Click "Flash" / "Start"

### macOS

```bash
# Identify your USB device
diskutil list

# Unmount the disk
diskutil unmountDisk /dev/diskN

# Write ISO (replace N with disk number)
sudo dd if=sigmavault-nas-os-1.0.0-amd64.iso of=/dev/rdiskN bs=4m
```

---

## Installation

### BIOS Configuration

1. Boot into BIOS/UEFI (usually Del, F2, or F12 at startup)
2. Set boot priority to USB first
3. Disable Secure Boot (if needed)
4. Save and exit

### Installation Process

1. Boot from USB media
2. Select "Install SigmaVault NAS OS" from the boot menu
3. Follow the guided installation:
   - Select language and keyboard
   - Configure network (DHCP or static IP)
   - Select installation disk
   - Create admin account
   - Set hostname

### Partitioning

The installer will automatically create:

| Partition           | Size      | Purpose              |
| ------------------- | --------- | -------------------- |
| EFI                 | 512 MB    | UEFI boot            |
| /boot               | 1 GB      | Kernel and initramfs |
| /                   | 20 GB     | Root filesystem      |
| /var/lib/sigmavault | Remaining | Data storage         |

---

## First Boot Configuration

### Initial Login

After installation, log in with the credentials you created:

```
Username: admin (or your chosen username)
Password: [your password]
```

### Service Status

Check that all SigmaVault services are running:

```bash
# Check service status
sudo systemctl status sigmavault-api
sudo systemctl status sigmavault-engined
sudo systemctl status sigmavault-webui

# View logs
sudo journalctl -u sigmavault-api -f
```

### Network Configuration

If you need to change network settings:

```bash
# Edit network configuration
sudo nano /etc/network/interfaces

# Or use NetworkManager
sudo nmtui
```

---

## Accessing the Dashboard

### Web Interface

Open a browser and navigate to:

```
http://[your-nas-ip]:12080
```

Default port: **12080**

### First Login

1. Create your admin account
2. Configure storage pools
3. Set up network shares
4. Enable AI agents

### API Access

The REST API is available at:

```
http://[your-nas-ip]:12080/api/v1/
```

---

## Configuration

### Environment Variables

Key configuration options in `/etc/sigmavault/config.env`:

```bash
# API Server
SIGMAVAULT_ENV=production
SIGMAVAULT_PORT=12080
SIGMAVAULT_JWT_SECRET=[generate-secure-secret]
SIGMAVAULT_CORS_ORIGINS=http://your-nas-ip:12080

# AI Engine
SIGMAVAULT_RPC_URL=http://localhost:8001/api/v1
SIGMAVAULT_RPC_TIMEOUT=30s

# Storage
SIGMAVAULT_DATA_DIR=/var/lib/sigmavault
```

### Generate Secure JWT Secret

```bash
# Generate 64-character random secret
openssl rand -hex 32
```

### Storage Configuration

```bash
# View available disks
lsblk

# Create storage pool (example with ZFS)
sudo zpool create datapool /dev/sdb /dev/sdc

# Mount for SigmaVault
sudo mkdir -p /var/lib/sigmavault/storage
sudo ln -s /datapool /var/lib/sigmavault/storage
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check service logs
sudo journalctl -u sigmavault-api -n 50

# Restart services
sudo systemctl restart sigmavault-api sigmavault-engined sigmavault-webui
```

### Network Issues

```bash
# Check network status
ip addr show
ping -c 4 8.8.8.8

# Restart networking
sudo systemctl restart networking
```

### Permission Issues

```bash
# Fix data directory permissions
sudo chown -R sigmavault:sigmavault /var/lib/sigmavault
sudo chmod 750 /var/lib/sigmavault
```

### JWT Secret Error

If you see "SECURITY: SIGMAVAULT_JWT_SECRET must be set in production":

```bash
# Edit config and set JWT secret
sudo nano /etc/sigmavault/config.env
# Add: SIGMAVAULT_JWT_SECRET=your-32-character-secret-here

# Restart API
sudo systemctl restart sigmavault-api
```

### Log Locations

| Service    | Log Location                       |
| ---------- | ---------------------------------- |
| API Server | `journalctl -u sigmavault-api`     |
| AI Engine  | `journalctl -u sigmavault-engined` |
| WebUI      | `journalctl -u sigmavault-webui`   |
| System     | `/var/log/syslog`                  |

---

## Getting Help

- **Documentation**: https://github.com/sigmavault/sigmavault-nas-os/docs
- **Issues**: https://github.com/sigmavault/sigmavault-nas-os/issues
- **Discussions**: https://github.com/sigmavault/sigmavault-nas-os/discussions

---

## Next Steps

1. [Configure Storage Pools](docs/storage.md)
2. [Set Up Network Shares](docs/shares.md)
3. [Enable AI Compression](docs/compression.md)
4. [Configure Backup](docs/backup.md)
5. [Security Hardening](docs/security.md)

---

**SigmaVault NAS OS v1.0.0** - AI-Powered Storage, Quantum-Ready Security
