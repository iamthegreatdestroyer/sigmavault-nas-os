# CLAUDE.md — SigmaVault NAS OS
## AUTONOMOUS MODE: ON

---

## What This Project Is

A Debian-based NAS operating system with three main services:

- **`src/engined`** — Python FastAPI + gRPC engine, 40 AI agent stubs, compression pipeline, encryption API
- **`src/api`** — Go Fiber REST/WebSocket gateway that proxies between engined and clients
- **`src/desktop-ui`** — Python GTK4/libadwaita desktop control panel (7 pages, fully wired)
- **`src/webui`** — React 18 + TypeScript + TailwindCSS browser web UI — **partially built, not committed**
- **`live-build/`** — Debian live-build scripts to produce a bootable ISO

**Submodules** (in `.gitmodules` but not populated — build without them for now):
- `submodules/EliteSigma-NAS` — AI compression engine (zlib fallback exists)
- `submodules/PhantomMesh-VPN` — VPN mesh (stub for now)
- `submodules/elite-agent-collective` — Agent library (stubs in tier1.py / tier2.py are fine)

**Goal: Get CI green, push all local work, and produce a working local-dev stack + Debian `.deb`.**

## Agent Stack
`@APEX` `@CIPHER` `@CORE` `@FORGE` `@ATLAS` `@QUANTUM` `@GENESIS` `@ARCHITECT`

---

## Current State (as of 2026-05-24)

### Git State — CRITICAL
```
Remote (GitHub):  commit 82180e2   ← 5 commits BEHIND local
Local S: drive:   commit a4c5858   ← newest, NOT PUSHED
Uncommitted:      15 modified + 12 untracked files on S: drive
```

### CI State — ALL FAILING
Every GitHub Actions run since October 2025 has failed. Root causes:
1. `src/webui` has no `package.json` committed to git — CI cannot run `pnpm install`
2. 5 unpushed local commits with real fixes never reached CI

### Service Architecture
```
Python engined     Port 5000  — FastAPI, gRPC mock, agents (stubs)
Go API             Port 12080 — Fiber, REST + WebSocket, real routes
Desktop UI         GTK4       — 7 pages, all wired to port 12080
Web UI             Port 5173  — Vite dev / dist/  — EXISTS IN node_modules dist but source NOT committed
```

### What's Complete
- ✅ Go API (Fiber) — routes, handlers, middleware, WebSocket hub, circuit breaker
- ✅ Python engined — FastAPI app, 40 agent stubs, compression bridge structure, gRPC `.proto`
- ✅ Desktop UI (GTK4) — 7 pages operational, live auto-refresh every 10s
- ✅ Phase 4 CI/CD — 6 GitHub Actions workflow files exist (but fail due to missing webui source)
- ✅ Pre-commit hooks, Makefile, VS Code workspace

### What's Missing / Broken
- ❌ `src/webui/package.json` never committed — **#1 CI killer**
- ❌ 5 local commits and 15+ uncommitted files never pushed to GitHub
- ❌ Real gRPC server — `src/engined/engined/rpc/server.py` is a MockServer loop
- ❌ Real compression — bridge exists but `StubCompressionEngine` does `await asyncio.sleep(0.1)`
- ❌ Real encryption — API routes defined but crypto operations return mock responses
- ❌ PhantomMesh VPN — submodule empty, no stub integration
- ❌ ISO build — `live-build/` scripts exist but haven't been validated end-to-end

---

## Definition of Done

Work through sprints in order. Check every box before moving on.

### SPRINT 1 — Git Hygiene (Unlocks everything else)

- [ ] **S1-A**: Stage and commit all modified files on S: drive:
  - `src/api/go.mod`, `src/api/go.sum`, `src/api/internal/rpc/agents_test.go`, `src/api/internal/websocket/hub.go`
  - All `docs/PHASE_2.3_*.md` files
  - All `test-*.ps1` and `verify-*.ps1` scripts (or gitignore them — they are dev scripts)
- [ ] **S1-B**: Commit all untracked files:
  - `docs/PHASE_2.3_TESTING_STRATEGY.md`, `docs/PHASE_2_ENGINE_UNIT_TESTS_COMPLETE.md`
  - `docs/PHASE_3.1_INTEGRATION_TESTING_COMPLETE.md`
  - `src/api/internal/e2e/`, `src/api/internal/rpc/integration_test.go`
  - `src/api/internal/rpc/swarm_integration_test.go`
  - `src/api/internal/websocket/websocket_integration_test.go`
  - `tests/`
- [ ] **S1-C**: `git push origin main` — get S: drive commits onto GitHub

### SPRINT 2 — Fix the Web UI (Fixes CI)

The `src/webui` has `node_modules/` and `dist/` but the source is not committed.
The CI workflow (`ci-comprehensive.yml`) runs `pnpm install` and `pnpm lint` and `pnpm build` in `src/webui`.

- [ ] **S2-A**: Check `src/webui/.gitignore` — remove any rule that blocks committing source files
- [ ] **S2-B**: If `src/webui/package.json` is missing, create it:
  ```json
  {
    "name": "sigmavault-webui",
    "version": "0.1.0",
    "private": true,
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "tsc && vite build",
      "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
      "preview": "vite preview"
    },
    "dependencies": {
      "react": "^18.2.0",
      "react-dom": "^18.2.0",
      "react-router-dom": "^6.20.0",
      "@tanstack/react-query": "^5.0.0",
      "zustand": "^4.4.0"
    },
    "devDependencies": {
      "@types/react": "^18.2.0",
      "@types/react-dom": "^18.2.0",
      "@typescript-eslint/eslint-plugin": "^6.0.0",
      "@typescript-eslint/parser": "^6.0.0",
      "@vitejs/plugin-react": "^4.2.0",
      "autoprefixer": "^10.4.0",
      "eslint": "^8.45.0",
      "eslint-plugin-react-hooks": "^4.6.0",
      "eslint-plugin-react-refresh": "^0.4.0",
      "postcss": "^8.4.0",
      "tailwindcss": "^3.4.0",
      "typescript": "^5.3.0",
      "vite": "^5.0.0"
    }
  }
  ```
- [ ] **S2-C**: Ensure `tsconfig.json`, `vite.config.ts`, `tailwind.config.js`, `postcss.config.js`, `eslint.config.js` exist in `src/webui/`. Generate any that are missing (standard Vite React TS scaffold config).
- [ ] **S2-D**: Ensure `src/webui/src/` has at minimum: `main.tsx`, `App.tsx`, `index.css`. These files exist in `C:/Users/sgbil/sigmavault-nas-os/src/webui/src/` — copy them if available.
- [ ] **S2-E**: Add `src/webui/.gitignore` containing:
  ```
  node_modules/
  dist/
  .env.local
  *.local
  ```
- [ ] **S2-F**: Commit the full `src/webui/` source (everything except node_modules/ and dist/)
- [ ] **S2-G**: `git push origin main` — this commit is the CI fix
- [ ] **S2-H**: Watch CI — the `Comprehensive CI` workflow should now pass the webui lint/build stage

### SPRINT 3 — Real gRPC Server (Makes compression/agents actually work)

The `.proto` file already exists at `src/engined/engined/rpc/system.proto`.
The `system_pb2.py` and `system_pb2_grpc.py` stubs are already generated.
The `MockServer` in `server.py` needs to become a real `grpc.aio` server.

- [ ] **S3-A**: Add `grpcio>=1.60.0` and `grpcio-tools>=1.60.0` to `src/engined/pyproject.toml` (check if already there)
- [ ] **S3-B**: Replace the `MockServer` class in `src/engined/engined/rpc/server.py` with a real `grpc.aio` server:
  ```python
  import grpc
  from grpc import aio
  from .system_pb2_grpc import add_SystemServiceServicer_to_server, SystemServiceServicer

  class SigmaVaultServicer(SystemServiceServicer):
      def __init__(self, swarm=None):
          self._swarm = swarm
      # Implement each RPC method from system.proto

  async def create_grpc_server(settings, swarm=None):
      server = aio.server()
      add_SystemServiceServicer_to_server(SigmaVaultServicer(swarm), server)
      port = settings.rpc_port  # default 50051
      server.add_insecure_port(f"[::]:{port}")
      return server
  ```
- [ ] **S3-C**: Wire each method from `system.proto` into the servicer. Read `src/api/internal/rpc/client.go` to see what methods the Go client calls — match them exactly.
- [ ] **S3-D**: Update `src/api/internal/rpc/client.go` — confirm it connects to port 50051 (already set). If it still connects to a mock, remove the mock fallback.
- [ ] **S3-E**: `cd src/engined && python -m pytest tests/ -x` — ensure tests still pass
- [ ] **S3-F**: Commit + push

### SPRINT 4 — Real Compression (Replaces the stub engine)

The `StubCompressionEngine` in `src/engined/engined/compression/bridge.py` just does `asyncio.sleep(0.1)` and returns fake stats. Replace with real zlib/lzma compression (EliteSigma-NAS submodule not needed for v1).

- [ ] **S4-A**: In `src/engined/engined/compression/bridge.py`, implement a `ZlibCompressionEngine` class:
  - Uses Python's built-in `zlib` and `lzma` modules — no external deps
  - `compress_file(path, config) -> CompressionJob` — reads in chunks, compresses, writes `.svz` file
  - Reports real `compression_ratio`, `bytes_original`, `bytes_compressed`
  - Emits real `CompressionProgress` events through the existing `CompressionEventEmitter`
- [ ] **S4-B**: Wire `ZlibCompressionEngine` as the default when `EliteSigma-NAS` submodule is absent:
  ```python
  if ELITESIGMA_PATH.exists():
      from elitesigma import EliteSigmaEngine as _Engine
  else:
      from .zlib_engine import ZlibCompressionEngine as _Engine
  ```
- [ ] **S4-C**: Update `src/engined/tests/test_compression.py` to test the real engine with a temp file
- [ ] **S4-D**: `cd src/engined && python -m pytest tests/test_compression.py -v` — all tests pass
- [ ] **S4-E**: Commit + push

### SPRINT 5 — CI Green (All workflows pass)

- [ ] **S5-A**: Read the CI failure logs from GitHub Actions for the latest run. Fix each failure category:
  - **Go lint** — run `cd src/api && go vet ./...` locally and fix all warnings
  - **Python ruff** — run `cd src/engined && ruff check engined/ --fix`
  - **WebUI lint** — run `cd src/webui && pnpm lint` and fix
  - **Go tests** — `cd src/api && go test ./... -race`
  - **Python tests** — `cd src/engined && python -m pytest tests/ --cov=engined --cov-fail-under=80`
  - **WebUI build** — `cd src/webui && pnpm build`
- [ ] **S5-B**: Fix the `security-scan.yml` workflow — check if it's failing on CVEs or on missing tools
- [ ] **S5-C**: Push — confirm both `Comprehensive CI` and `Security Scanning` workflows turn green
- [ ] **S5-D**: All CI badges in README must be green. Update badge URLs if they point to old repo (sgbilod → iamthegreatdestroyer)

### SPRINT 6 — Debian Package (Installable artifact)

- [ ] **S6-A**: Read `debian/control` and `debian/rules` — verify they reference the correct binary paths
- [ ] **S6-B**: Run `cd S:/sigmavault-nas-os && dpkg-buildpackage -us -uc -b` in a Debian environment (WSL or Docker):
  ```bash
  docker run --rm -v $(pwd):/src debian:trixie bash -c "cd /src && apt-get install -y debhelper && dpkg-buildpackage -us -uc -b"
  ```
- [ ] **S6-C**: Validate the resulting `.deb` installs cleanly: `sudo dpkg -i sigmavault_*.deb`
- [ ] **S6-D**: Verify all 3 systemd services start: `sigmavault-api.service`, `sigmavault-engined.service`, `sigmavault-webui.service`
- [ ] **S6-E**: Commit any fixes to the debian/ packaging and push. Tag `v0.3.0`.

---

## Execution Plan (Step by Step)

```
STEP 1: Sprint 1 — push everything local
  cd S:/sigmavault-nas-os
  git add -A
  git commit -m "chore: push all local Phase 2.3 work including tests and docs"
  git push origin main

STEP 2: Sprint 2 — fix webui
  ls src/webui/          ← check what's there
  # If package.json is missing, create it (see S2-B above)
  # Copy source files from C:/Users/sgbil/sigmavault-nas-os/src/webui/src/ if available
  # Create/verify tsconfig.json, vite.config.ts, etc.
  git add src/webui/ -f   ← force-add (webui src may be gitignored by accident)
  git commit -m "feat(webui): add React 18 + TypeScript + Tailwind source to git"
  git push origin main
  # Watch CI on GitHub Actions

STEP 3: Sprint 3 — real gRPC
  Read src/engined/engined/rpc/system.proto
  Read src/api/internal/rpc/client.go  ← what methods does Go call?
  Edit src/engined/engined/rpc/server.py  ← replace MockServer
  cd src/engined && python -m pytest tests/ -x
  git add -A && git commit -m "feat(rpc): implement real grpc.aio server" && git push

STEP 4: Sprint 4 — real compression
  Edit src/engined/engined/compression/bridge.py  ← add ZlibCompressionEngine
  cd src/engined && python -m pytest tests/test_compression.py -v
  git add -A && git commit -m "feat(compression): implement zlib fallback engine" && git push

STEP 5: Sprint 5 — CI green
  Check GitHub Actions logs: gh run view --repo iamthegreatdestroyer/sigmavault-nas-os
  Fix each failure. Push. Repeat until all green.

STEP 6: Sprint 6 — Debian package
  docker run debian:trixie ...  (see S6-B above)
  Validate install. Tag v0.3.0.
```

---

## Critical Rules

1. **Do not empty the agent stub implementations** — tier1.py and tier2.py stubs are fine for now; the framework is more important than real LLM calls.
2. **Do not add the EliteSigma-NAS submodule** — write a zlib fallback instead. The submodule has its own incomplete state.
3. **Private keys, RPC secrets stay in config** — never in source code or logged.
4. **Run tests after every sprint** — Go: `go test ./...`; Python: `pytest tests/`
5. **Do not break the existing GTK4 desktop UI** — it's fully working. Don't touch `src/desktop-ui/` unless fixing a specific bug.
6. **Mock-first, real second** — keep mock fallbacks in the Go RPC client so the API still works even if engined is offline.

---

## Key File Map

| What you need | File |
|---|---|
| Go API entry point | `src/api/main.go` |
| Go routes | `src/api/internal/routes/routes.go` |
| Go RPC client (calls engined) | `src/api/internal/rpc/client.go` |
| Go WebSocket hub | `src/api/internal/websocket/hub.go` |
| Python engined entry | `src/engined/engined/main.py` |
| gRPC server (mock → real) | `src/engined/engined/rpc/server.py` |
| gRPC proto | `src/engined/engined/rpc/system.proto` |
| Compression bridge | `src/engined/engined/compression/bridge.py` |
| Compression job queue | `src/engined/engined/compression/job_queue.py` |
| Agent registry | `src/engined/engined/agents/registry.py` |
| Agent tier 1 stubs | `src/engined/engined/agents/tier1.py` |
| Desktop UI window | `src/desktop-ui/sigmavault_desktop/window.py` |
| Desktop API client | `src/desktop-ui/sigmavault_desktop/api/client.py` |
| Web UI App | `src/webui/src/App.tsx` |
| Comprehensive CI | `.github/workflows/ci-comprehensive.yml` |
| Debian packaging | `debian/control`, `debian/rules` |
| systemd services | `live-build/config/includes.chroot/etc/systemd/system/` |
| Configs | `configs/development.env` |

---

## Port Reference

| Service | Port | Protocol |
|---|---|---|
| Python engined (FastAPI) | 5000 | HTTP/REST |
| Python gRPC server | 50051 | gRPC |
| Go API (Fiber) | 12080 | HTTP/REST + WebSocket |
| Web UI (Vite dev) | 5173 | HTTP |
| Desktop UI | N/A | GTK4 (native) |

---

## Completion Signal

When Sprint 5 is complete and all CI passes:
```
git tag v0.3.0
git push origin v0.3.0
```

Then write `COMPLETION_REPORT.md`:
```markdown
# SigmaVault NAS OS v0.3.0 — Completion Report
Date: [today]
Tag: v0.3.0
CI: All green (Comprehensive CI + Security Scanning)
Services: engined (real gRPC) + Go API + Desktop UI + Web UI all running
Compression: zlib fallback engine operational
Remaining (v0.4.0): PhantomMesh VPN, ISO build, EliteSigma-NAS integration, real Kyber encryption
```
