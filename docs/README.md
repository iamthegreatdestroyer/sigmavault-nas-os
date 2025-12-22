# SigmaVault NAS OS Documentation

## Quick Links

- [Installation Guide](installation.md)
- [Configuration](configuration.md)
- [API Reference](api-reference.md)
- [Elite Agent Collective](agents.md)
- [Development Guide](development.md)

## Architecture Overview

SigmaVault NAS OS is built on a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                   Web Interface (React)                      │
├─────────────────────────────────────────────────────────────┤
│                    API Gateway (Go Fiber)                    │
├─────────────────────────────────────────────────────────────┤
│                  RPC Engine (Python FastAPI)                 │
├──────────────────────────┬──────────────────────────────────┤
│     EliteSigma-NAS       │         PhantomMesh-VPN          │
│  • AI Compression        │    • Mesh Networking             │
│  • Agent Swarm (40)      │    • Multi-Site Federation       │
│  • MNEMONIC Memory       │    • Quantum-Resistant Tunnels   │
├──────────────────────────┴──────────────────────────────────┤
│                  Salt Stack Configuration                    │
├─────────────────────────────────────────────────────────────┤
│                  Debian 13 (Trixie) Base OS                  │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### AI-Powered Storage (EliteSigma-NAS)
- **90%+ Compression**: Semantic encoding understands file content
- **40 Agent Swarm**: Specialized AI agents for different tasks
- **MNEMONIC Memory**: Sub-linear retrieval with Bloom filters, LSH, HNSW

### Quantum-Resistant Security
- **Kyber KEM**: Post-quantum key encapsulation
- **AES-256-GCM**: Authenticated encryption
- **Zero-Knowledge Proofs**: Privacy-preserving operations

### Integrated VPN Mesh (PhantomMesh)
- **WireGuard-Based**: Modern, fast VPN protocol
- **Auto-Discovery**: Zero-configuration peer finding
- **Multi-Site Federation**: Unified storage across locations

## Getting Started

```bash
# Clone with submodules
git clone --recursive https://github.com/iamthegreatdestroyer/sigmavault-nas-os.git

# Build ISO
cd sigmavault-nas-os/live-build
sudo lb config
sudo lb build
```

## Development

See the [Development Guide](development.md) for:
- Setting up the development environment
- Using the Elite Agent Collective
- Contributing guidelines
