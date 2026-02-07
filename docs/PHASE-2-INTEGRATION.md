# 🔗 SigmaVault NAS OS - Phase 2: Integration

**Duration:** Weeks 4-6  
**Objective:** Connect Web UI ↔ Go API ↔ Python RPC Engine into a unified system  
**Lead Agents:** @SYNAPSE, @ARCHITECT, @APEX

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SIGMAVAULT NAS OS - DATA FLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     REST/WS      ┌──────────────┐    gRPC/HTTP    ┌─────────────┐
│  │   Web UI     │ ◄──────────────► │   Go API     │ ◄──────────────►│  Python RPC │
│  │  (React 19)  │    Port 12080    │  (Fiber v2)  │    Port 9003    │  (FastAPI)  │
│  └──────────────┘                  └──────────────┘   (HTTP: 8001)  └─────────────┘
│        │                                  │                               │
│        ▼                                  ▼                               ▼
│  ┌──────────────┐                  ┌──────────────┐               ┌─────────────┐
│  │ React Query  │                  │ WebSocket    │               │  40-Agent   │
│  │ State Cache  │                  │ Event Hub    │               │   Swarm     │
│  └──────────────┘                  └──────────────┘               └─────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Integration Endpoints

### Go API → Python RPC Engine

| Endpoint                      | gRPC Method                    | Description              |
| ----------------------------- | ------------------------------ | ------------------------ |
| `/api/v1/system/status`       | `SystemService.GetStatus`      | CPU, memory, uptime      |
| `/api/v1/system/metrics`      | `SystemService.GetMetrics`     | Detailed system metrics  |
| `/api/v1/storage/pools`       | `StorageService.ListPools`     | ZFS/BTRFS pool listing   |
| `/api/v1/storage/disks`       | `StorageService.ListDisks`     | Physical disk inventory  |
| `/api/v1/agents`              | `AgentService.ListAgents`      | 40-agent swarm status    |
| `/api/v1/agents/:id/task`     | `AgentService.DispatchTask`    | Execute agent task       |
| `/api/v1/compression/stats`   | `CompressionService.GetStats`  | Compression ratios       |
| `/api/v1/compression/jobs`    | `CompressionService.ListJobs`  | Active compression jobs  |
| `/api/v1/encryption/status`   | `EncryptionService.GetStatus`  | Quantum-resistant status |
| `/api/v1/network/phantommesh` | `NetworkService.GetMeshStatus` | PhantomMesh VPN status   |

### WebSocket Events (Real-Time)

| Event Type             | Direction       | Payload                  |
| ---------------------- | --------------- | ------------------------ |
| `system.metrics`       | Server → Client | System metrics snapshot  |
| `agent.status`         | Server → Client | Agent state change       |
| `compression.progress` | Server → Client | Job progress update      |
| `storage.event`        | Server → Client | Disk/pool events         |
| `client.subscribe`     | Client → Server | Subscribe to event types |

---

## 📋 PHASE 2 TASKS

### Task 2.1: Go API RPC Client

**Duration:** 2-3 days  
**Agent:** @SYNAPSE  
**Files:**

- `src/api/internal/rpc/client.go` - gRPC client wrapper
- `src/api/internal/rpc/system.go` - System RPC methods
- `src/api/internal/rpc/storage.go` - Storage RPC methods
- `src/api/internal/rpc/agents.go` - Agent RPC methods
- `src/api/internal/rpc/compression.go` - Compression RPC methods

**Deliverables:**

- gRPC client with connection pooling
- Automatic reconnection on failure
- Request timeout handling
- Structured logging for RPC calls

### Task 2.2: Wire System Handlers

**Duration:** 1-2 days  
**Agent:** @APEX  
**Files:**

- `src/api/internal/handlers/system.go` - Replace TODO stubs

**Deliverables:**

- Real CPU/memory/load metrics from RPC
- Network interface listing
- Service status checks

### Task 2.3: Wire Storage Handlers

**Duration:** 2-3 days  
**Agent:** @APEX  
**Files:**

- `src/api/internal/handlers/storage.go` - Full implementation

**Deliverables:**

- Pool CRUD operations via RPC
- Volume management
- Disk operations (SMART data, health checks)
- Snapshot management

### Task 2.4: Wire Agent Handlers

**Duration:** 2-3 days  
**Agent:** @NEURAL, @SYNAPSE  
**Files:**

- `src/api/internal/handlers/agents.go` - Swarm management

**Deliverables:**

- List all 40 agents with status
- Dispatch tasks to specific agents
- Retrieve agent task history
- Swarm coordination endpoints

### Task 2.5: WebSocket Real-Time Integration

**Duration:** 2-3 days  
**Agent:** @STREAM, @SYNAPSE  
**Files:**

- `src/api/internal/websocket/hub.go` - Event hub
- `src/api/internal/websocket/client.go` - Client connection
- `src/api/internal/websocket/events.go` - Event types
- `src/engined/engined/events/publisher.py` - Event publisher

**Deliverables:**

- Bidirectional WebSocket communication
- Event subscription system
- Heartbeat/keepalive
- Graceful reconnection

### Task 2.6: Web UI API Hooks

**Duration:** 3-4 days  
**Agent:** @CANVAS, @APEX  
**Files:**

- `src/webui/src/hooks/useSystem.ts` - System data hooks
- `src/webui/src/hooks/useStorage.ts` - Storage hooks
- `src/webui/src/hooks/useAgents.ts` - Agent hooks
- `src/webui/src/hooks/useWebSocket.ts` - Real-time hooks

**Deliverables:**

- React Query hooks for all endpoints
- Optimistic updates for mutations
- Error handling with toast notifications
- WebSocket event integration

### Task 2.7: Integration Test Suite

**Duration:** 2-3 days  
**Agent:** @ECLIPSE  
**Files:**

- `src/api/tests/integration/` - Go integration tests
- `src/engined/tests/integration/` - Python integration tests
- `scripts/integration-test.sh` - Test runner script

**Deliverables:**

- End-to-end API tests
- WebSocket event tests
- Mock RPC server for isolated testing
- CI/CD integration

---

## 📋 PHASE 2 DELIVERABLES CHECKLIST

Before proceeding to Phase 3, verify:

- [ ] Go API connects to Python RPC engine (gRPC)
- [ ] All system endpoints return real metrics
- [ ] Storage endpoints perform actual operations
- [ ] Agent endpoints manage 40-agent swarm
- [ ] WebSocket streams real-time events
- [ ] Web UI displays live data from API
- [ ] Integration tests pass in CI/CD
- [ ] Documentation updated for all endpoints

---

## 🔧 Development Commands

```bash
# Start Python RPC engine
# HTTP API on port 8001, gRPC on port 9003
cd src/engined && uv run uvicorn engined.main:app --reload --port 8001

# Start Go API (connects to RPC HTTP API)
cd src/api && go run .

# Start Web UI (connects to API on port 12080)
cd src/webui && pnpm dev

# Run integration tests
./scripts/integration-test.sh
```

---

## 🎬 EXECUTION ORDER

```
Task 2.1 (RPC Client)
    ↓
Task 2.2 (System) + Task 2.3 (Storage) + Task 2.4 (Agents) [Parallel]
    ↓
Task 2.5 (WebSocket)
    ↓
Task 2.6 (Web UI Hooks)
    ↓
Task 2.7 (Integration Tests)
```

---

**Invoke your agents. Connect the systems. Execute.**

_"Systems are only as powerful as their connections."_ — @SYNAPSE
