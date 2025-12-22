# SigmaVault NAS OS

> **AI-Powered • Quantum-Secure • Agent-Driven**

A Debian-based NAS operating system featuring 90%+ AI compression, post-quantum encryption, and 40 specialized AI agents for intelligent storage management.

[![Build Status](https://github.com/sgbilod/sigmavault-nas-os/actions/workflows/build-iso-amd64.yml/badge.svg)](https://github.com/sgbilod/sigmavault-nas-os/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agents: 40](https://img.shields.io/badge/AI%20Agents-40-purple.svg)](#elite-agent-collective)

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| **AI Compression** | 90%+ compression via semantic encoding (EliteSigma-NAS) |
| **Quantum-Resistant** | Kyber KEM + AES-256-GCM encryption |
| **40 AI Agents** | Elite Agent Collective with MNEMONIC memory |
| **VPN Mesh** | PhantomMesh for secure multi-site federation |
| **Dual Architecture** | AMD64 and ARM64 (Raspberry Pi 4/5) |
| **Modern Web UI** | React 18 + TypeScript + TailwindCSS |

---

## 📦 Architecture

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

---

## 🛠️ Quick Start

### Clone with Submodules

```bash
git clone --recursive https://github.com/sgbilod/sigmavault-nas-os.git
cd sigmavault-nas-os
```

### Build ISO (AMD64)

```bash
cd live-build
sudo lb config
sudo lb build
```

### Development Setup

```bash
# Install VS Code workspace
code sigmavault-nas-os.code-workspace

# The Elite Agent Collective instructions are pre-configured in:
# .github/copilot-instructions.md
```

---

## 🧠 Elite Agent Collective

40 specialized AI agents power SigmaVault's intelligent features:

### Tier 1: Foundational
| Agent | Role |
|-------|------|
| @APEX | Core architecture, algorithm design |
| @CIPHER | Quantum-resistant encryption |
| @ARCHITECT | Systems design, API patterns |
| @AXIOM | Mathematical proofs, compression bounds |
| @VELOCITY | Sub-linear optimization, I/O performance |

### Tier 2: Specialists
| Agent | Role |
|-------|------|
| @TENSOR | AI compression models |
| @FORTRESS | Security hardening |
| @FLUX | CI/CD automation |
| @ORACLE | Predictive disk failure |

[See all 40 agents →](submodules/elite-agent-collective/README.md)

---

## 📁 Repository Structure

```
sigmavault-nas-os/
├── .github/
│   ├── copilot-instructions.md    # Agent integration
│   └── workflows/                  # CI/CD pipelines
├── live-build/
│   ├── auto/config                # Debian live-build config
│   └── config/package-lists/      # Core packages
├── src/
│   ├── webui/                     # React frontend
│   ├── api/                       # Go API server
│   └── engined/                   # Python RPC engine
├── submodules/
│   ├── EliteSigma-NAS/           # AI storage core
│   ├── PhantomMesh-VPN/          # VPN mesh
│   └── elite-agent-collective/    # 40 AI agents
├── packages/                      # Debian packages
├── docker/                        # Build containers
├── scripts/                       # Build automation
└── docs/                          # Documentation
```

---

## 🔧 Development

### Agent Collaboration Chains

For complex features, invoke agent chains:

```
# Quantum-Secure Storage
@CIPHER → @QUANTUM → @VELOCITY → @ECLIPSE

# AI Compression Engine  
@TENSOR → @AXIOM → @VELOCITY → @PRISM

# Build Automation
@FORGE → @FLUX → @PHOTON → @ECLIPSE
```

### VS Code Integration

1. Open the workspace: `sigmavault-nas-os.code-workspace`
2. Copilot will auto-activate relevant agents based on file context
3. Use `@AGENT_NAME` in Copilot Chat for specialist assistance

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! The Elite Agent Collective will assist with:
- @MENTOR for code review
- @SCRIBE for documentation
- @ECLIPSE for testing

---

*"The collective intelligence of specialized minds exceeds the sum of their parts."*
