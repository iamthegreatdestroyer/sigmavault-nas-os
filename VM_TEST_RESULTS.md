# SigmaVault NAS OS — Docker Stack Test Results

Date: 2026-06-03
Host: Windows 11 Pro / Docker Desktop
Tag: v0.4.0

## Stack

| Service | Container | Image | Host Port | Internal Port | Status |
|---|---|---|---|---|---|
| engined | sigmavault-nas-os-engined-1 | sigmavault-nas-os-engined | 6100 | 5000 | ✅ healthy |
| engined gRPC | (same container) | — | 6151 | 50051 | ✅ bound |
| api | sigmavault-nas-os-api-1 | sigmavault-nas-os-api | 12080 | 12080 | ✅ healthy |
| webui | sigmavault-nas-os-webui-1 | sigmavault-nas-os-webui | 5173 | 5173 | ✅ running |

> Note: engined host port is 6100 (not 5000) because Docker Desktop on Windows
> occupies 5000. Internal container port remains 5000; inter-service traffic
> (api→engined) uses the Docker network name `engined:5000` unaffected.

## Smoke Test Results

### engined (port 6100)

```
GET /health/live   → HTTP 200
{"status":"alive","timestamp":"2026-06-03T05:15:33Z","version":"0.1.0","uptime_seconds":24215}

GET /health/ready  → HTTP 200
{"ready":true,"checks":{"swarm_initialized":true,"agents_available":true}}

POST /api/v1/rpc   → HTTP 200
{"jsonrpc":"2.0","result":{"hostname":"6770ae14e88a","platform":"Linux",
"uptime":506149,"cpu_usage":12.0,"memory_usage":{"used_percent":32.8},
"load_average":{"load1":5.69},"timestamp":"2026-06-03T05:15:33Z"},
"error":null,"id":1}
```

### Go API (port 12080)

```
GET /api/v1/health  → HTTP 200
{"status":"healthy","timestamp":"2026-06-03T05:15:35Z","version":"0.1.0",
"engine":"connected","agents":{"idle":40,"total":40}}

GET /api/v1/info    → HTTP 200
{"version":"0.1.0","go_version":"go1.25.10","num_goroutine":12,
"num_cpu":16,"uptime_seconds":24218}

GET /api/v1/storage/disks → HTTP 200
{"count":1,"disks":[{"model":"Samsung 870 EVO","name":"sda",...}]}
```

Key: `"engine":"connected"` and `"agents":{"idle":40,"total":40}` confirm
the Go API is successfully communicating with engined over the Docker network.

### WebUI (port 5173)

```
GET /  → HTTP 200  (Vite dev server, React SPA)
Vite v7.3.5 ready in 2167ms
```

## Service Communication Verified

- **api → engined**: Go API polls engined every 5s via RPC. Health endpoint
  confirms `"engine":"connected"` and all 40 agent stubs visible.
- **engined gRPC**: Port 50051 bound (6151 on host); gRPC server started
  alongside FastAPI.
- **webui → api**: Vite proxy configured for `/api → http://api:12080` and
  `/ws → ws://api:12080`.

## Known Non-Issues

- `Method not found: agents.scheduler.metrics` — expected; scheduler/recovery/
  tuning RPC methods are stubs not yet implemented in engined.
- `EliteSigma-NAS not found` — expected; submodule not populated, zlib
  fallback engine is active.
- Port 5000 remapped to 6100 on host only; all container-internal traffic
  uses port 5000 unaffected.

## Dockerfiles

| File | Base | Purpose |
|---|---|---|
| [docker/Dockerfile.engined](docker/Dockerfile.engined) | python:3.12-slim | Python FastAPI + gRPC engine |
| [docker/Dockerfile.api](docker/Dockerfile.api) | golang:1.25-alpine → alpine:3.20 | Go Fiber API (multi-stage) |
| [src/webui/Dockerfile](src/webui/Dockerfile) | node:20-alpine | React 18 Vite dev server |
