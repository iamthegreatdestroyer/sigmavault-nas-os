# SigmaVault NAS OS

> **AI-Powered Storage Platform** — Part of the [Sigma Ecosystem](https://github.com/iamthegreatdestroyer)

A Debian 13-based NAS operating system with intelligent compression, a 40-agent orchestration framework, and post-quantum encryption primitives. Designed for self-hosted, air-gapped deployment from a portable drive.

[![CI](https://github.com/iamthegreatdestroyer/sigmavault-nas-os/actions/workflows/ci-comprehensive.yml/badge.svg)](https://github.com/iamthegreatdestroyer/sigmavault-nas-os/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What Works Today (v0.3.0)

| Component | Status | Details |
|-----------|--------|---------|
| **Go API Gateway** | Shipped | Fiber REST + WebSocket on port 12080; JWT auth, rate limiting, circuit breaker |
| **Python RPC Engine** | Shipped | FastAPI + real gRPC server (port 50051); system status, compression, agent routes |
| **Compression Pipeline** | Shipped | zlib (FAST/BALANCED) + lzma (MAXIMUM) with 4-byte magic headers for auto-routing |
| **40-Agent Framework** | Shipped (stubs) | Full lifecycle: task queue, scheduler, MNEMONIC memory, recovery, self-tuning. Agents execute task stubs — real LLM calls not yet wired |
| **Desktop UI** | Shipped | GTK4 + libadwaita; 7 pages (dashboard, storage, compression, agents, encryption, settings, logs); auto-refresh every 10s |
| **Web UI** | Scaffold | React 18 + TypeScript + Tailwind; basic routing, builds cleanly |
| **Debian Package** | Shipped | `sigmavault-desktop_0.1.0-1_all.deb` builds and installs on Debian 13 |
| **CI/CD** | Passing | Go lint/test, Python ruff/pytest, WebUI lint/build, Trivy security scanning |
| **1TB Portable Deploy** | Shipped | `deploy.sh` installs full stack on fresh Debian 13 from thumb drive |

## What's Planned (Roadmap)

| Feature | Target | Depends On |
|---------|--------|------------|
| **Ryot-backed semantic compression** | v0.4.0 | Ryot fractal quantization (Layer 4) — CPU-first, adaptive bit-depth |
| **Real agent LLM calls** | v0.4.0 | Ollama integration (qwen3:30b pre-cached on deployment drive) |
| **Post-quantum encryption** | v0.5.0 | sigmavault (Kyber-1024 + Dilithium-3) already shipped as Layer 3 — needs wiring into NAS crypto routes |
| **PhantomMesh VPN integration** | v0.5.0 | PhantomMesh (WireGuard mesh) shipped as Layer 3 — needs submodule wiring |
| **Agent safety layer** | v0.4.0 | Immutable audit logs, human approval gates for destructive ops, automatic rollback |
| **Storage backend (Btrfs/ZFS)** | v0.5.0 | Snapshot policies, SMART monitoring, semantic tiering |
| **ISO build end-to-end** | v0.5.0 | live-build scripts exist, need validation on real hardware |
| **ARM64 (Raspberry Pi 4/5)** | v0.6.0 | Cross-compilation, resource profiling for constrained hardware |

---

## Architecture

```
+---------------------------------------------------------+
|              Web UI (React 18, port 5173)                |
|            Desktop UI (GTK4, native)                     |
+---------------------------------------------------------+
|           Go Fiber API Gateway (port 12080)              |
|    REST endpoints, JWT auth, WebSocket hub               |
+---------------------------------------------------------+
|        Python FastAPI RPC Engine (port 5000)             |
|  +---------------------------------------------------+  |
|  |  gRPC Server (port 50051)                         |  |
|  |  40-Agent Swarm Framework (stubs, MNEMONIC mem)   |  |
|  |  Compression Bridge (zlib/lzma, Ryot planned)     |  |
|  |  Task Scheduler (100 RPS, 10 max concurrent)      |  |
|  +---------------------------------------------------+  |
+---------------------------------------------------------+
|                  Debian 13 (Trixie)                      |
+---------------------------------------------------------+
```

**Sigma Ecosystem context:** This is Layer 1 (Foundation) of a 33-repo ecosystem. Layers 2-7 provide the cryptography (sigmavault), networking (PhantomMesh), inference engine (Ryot/Ryzanstein), semantic encoding (sigmalang), and AI agent orchestration (elite-agent-collective) that this NAS OS consumes.

---

## Quick Start

### Clone

```bash
git clone --recursive https://github.com/iamthegreatdestroyer/sigmavault-nas-os.git
cd sigmavault-nas-os
```

### Run Services (Development)

```bash
# Python engine
cd src/engined && pip install -e . && python -m engined

# Go API (separate terminal)
cd src/api && go run main.go

# Web UI (separate terminal)
cd src/webui && pnpm install && pnpm dev
```

### Deploy to Bare Debian 13

```bash
# From 1TB portable drive mounted at /mnt/sigma
sudo bash /mnt/sigma/SigmaVault/deploy.sh
```

### Build Debian Package

```bash
cd debian && dpkg-buildpackage -us -uc -b
```

---

## Agent Swarm

40 agents organized in 4 tiers. Currently stubs with full lifecycle infrastructure (task queue, priority scheduling, MNEMONIC memory, health recovery, self-tuning). Real LLM execution is the v0.4.0 milestone.

### Tier 1 (Foundational)

| Agent | Domain |
|-------|--------|
| @APEX | Core architecture, algorithm design |
| @CIPHER | Cryptography, security audit |
| @ARCHITECT | Systems design, API patterns |
| @AXIOM | Mathematical proofs, compression bounds |
| @VELOCITY | Performance optimization, I/O |

### Selected Tier 2 Specialists

| Agent | Domain |
|-------|--------|
| @TENSOR | AI model compression |
| @FORTRESS | Security hardening |
| @ORACLE | Predictive disk failure (SMART) |
| @FLUX | CI/CD automation |

[Full 40-agent registry](https://github.com/iamthegreatdestroyer/elite-agent-collective)

---

## Repository Structure

```
sigmavault-nas-os/
+-- src/
|   +-- api/              Go Fiber REST + WebSocket gateway (16K LoC)
|   +-- engined/          Python FastAPI + gRPC engine (18K LoC)
|   |   +-- agents/       40-agent swarm framework (4.7K LoC)
|   |   +-- compression/  Compression bridge + job queue (1.7K LoC)
|   |   +-- rpc/          gRPC server + protobuf
|   |   +-- api/          FastAPI route modules
|   +-- desktop-ui/       GTK4 + libadwaita (6.9K LoC)
|   +-- webui/            React 18 + TypeScript scaffold
+-- live-build/           Debian ISO builder config
+-- debian/               .deb package metadata
+-- scripts/              deploy.sh, start-services.sh, precache-models.sh
+-- docs/                 Phase reports, integration guides
+-- submodules/           EliteSigma-NAS, PhantomMesh-VPN, elite-agent-collective
```

---

## Development

### VS Code Integration

1. Open workspace: `sigmavault-nas-os.code-workspace`
2. Copilot instructions pre-configured in `.github/copilot-instructions.md`
3. Use `@AGENT_NAME` in Copilot Chat for specialist assistance

### Service Ports

| Service | Port | Protocol |
|---------|------|----------|
| Python FastAPI | 5000 | HTTP/REST |
| Python gRPC | 50051 | gRPC |
| Go Fiber API | 12080 | HTTP/REST + WebSocket |
| Vite Dev Server | 5173 | HTTP |

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
