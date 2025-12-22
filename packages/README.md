# Debian Packages Directory

Each subdirectory contains a Debian package with standard `debian/` control files.

## Package Structure

```
packages/
├── sigmavault-core/
│   ├── debian/
│   │   ├── control
│   │   ├── rules
│   │   ├── changelog
│   │   └── ...
│   └── src/
├── sigmavault-webui/
├── sigmavault-api/
└── sigmavault-engined/
```

## Building Packages

```bash
cd packages/sigmavault-core
dpkg-buildpackage -us -uc -b
```

## Package List

| Package | Description |
|---------|-------------|
| `sigmavault-core` | Core services and configuration |
| `sigmavault-webui` | React web interface |
| `sigmavault-api` | Go API gateway |
| `sigmavault-engined` | Python RPC engine |
| `sigmavault-agents` | Elite Agent Collective runtime |
