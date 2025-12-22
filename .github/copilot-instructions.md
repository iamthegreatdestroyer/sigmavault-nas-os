# SigmaVault NAS OS - Elite Agent Collective Integration

## Project Context
SigmaVault NAS OS is a Debian 13 (Trixie) based NAS operating system integrating:
- **EliteSigma-NAS**: AI-powered compression (90%+), quantum-resistant encryption, 40-agent swarm
- **PhantomMesh-VPN**: Secure mesh networking with multi-site federation
- **Elite Agent Collective**: 40 specialized AI agents with MNEMONIC memory system

## Architecture
- **Base**: Debian 13 (Trixie) with live-build for reproducible ISOs
- **Targets**: AMD64 and ARM64 (Raspberry Pi 4/5)
- **Frontend**: React 18 + TypeScript + TailwindCSS
- **Backend**: Go Fiber API + Python FastAPI RPC engine
- **Config Management**: Salt Stack

## Agent Auto-Activation Rules

| File Pattern | Primary Agents |
|--------------|----------------|
| `**/security/**`, `**/crypto/**` | @CIPHER, @FORTRESS, @QUANTUM |
| `**/compression/**`, `**/ml/**` | @TENSOR, @VELOCITY, @AXIOM |
| `**/api/**`, `**/rpc/**` | @SYNAPSE, @ARCHITECT |
| `**/webui/**`, `**/frontend/**` | @CANVAS, @STREAM |
| `**/live-build/**`, `**/packages/**` | @FORGE, @FLUX, @PHOTON |
| `**/tests/**` | @ECLIPSE |
| `**/docs/**` | @SCRIBE |
| `**/phantommesh/**` | @LATTICE, @CRYPTO |
| `**/analytics/**`, `**/monitoring/**` | @SENTRY, @PRISM, @ORACLE |

## Collaboration Chains (Use for Complex Tasks)

### Quantum-Secure Storage
```
@CIPHER → @QUANTUM → @VELOCITY → @ECLIPSE
```

### AI Compression Engine
```
@TENSOR → @AXIOM → @VELOCITY → @PRISM
```

### PhantomMesh Integration
```
@LATTICE → @CRYPTO → @FORTRESS → @SYNAPSE
```

### Web Interface Development
```
@CANVAS → @STREAM → @SYNAPSE → @MENTOR
```

### Build System Automation
```
@FORGE → @FLUX → @PHOTON → @ECLIPSE
```

## Code Standards

### Python
- PEP 8 compliance, type hints required

### TypeScript
- Strict mode, ESLint + Prettier

### Go
- Effective Go guidelines, golangci-lint

### Rust
- Clippy lints, Rustfmt

## Priority: Automation First
Always prefer sub-linear algorithms (O(1), O(log n)) over linear.
