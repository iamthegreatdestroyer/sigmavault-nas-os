# SigmaVault WebSocket Protocol Specification

**Version:** 1.0  
**Date:** 2025-12-23  
**Status:** Production Ready  
**Phase:** 2.7.5 Complete

---

## Overview

The SigmaVault WebSocket system provides real-time event streaming between the Go API server and web clients. It supports bidirectional communication with subscription-based filtering and graceful degradation during RPC outages.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      WebSocket Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐  │
│  │  Web Client  │ ◄───► │     Hub      │ ◄───► │  EventSub    │  │
│  │  (Browser)   │  WS   │  (Router)    │       │  (RPC Poll)  │  │
│  └──────────────┘       └──────────────┘       └──────────────┘  │
│         │                      │                      │          │
│         ▼                      ▼                      ▼          │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐  │
│  │ Subscription │       │  Broadcast   │       │    Cache     │  │
│  │   Filters    │       │   System     │       │   Layer      │  │
│  └──────────────┘       └──────────────┘       └──────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Connection Endpoint

```
WS  /ws
```

### Connection Flow

1. Client establishes WebSocket connection to `/ws`
2. Server sends initial `notification` event with welcome message
3. Client automatically subscribed to default event types
4. Server begins broadcasting events based on subscriptions

### Default Subscriptions

Clients are automatically subscribed to these event types on connection:

- `system.status`
- `agent.status`
- `compression.update`
- `notification`
- `rpc_error`
- `connection_error`
- `heartbeat`
- `storage.update`

## Message Format

All messages use JSON format with this structure:

```typescript
interface Event {
  type: MessageType; // Event type identifier
  timestamp: string; // ISO 8601 timestamp
  data?: object; // Event-specific payload
}

type MessageType =
  | "system.status"
  | "storage.update"
  | "agent.status"
  | "compression.update"
  | "notification"
  | "rpc_error"
  | "connection_error"
  | "heartbeat"
  | "subscribe"
  | "unsubscribe";
```

## Event Types

### `system.status`

System metrics broadcast every 5 seconds.

```json
{
  "type": "system.status",
  "timestamp": "2025-12-23T13:08:37Z",
  "data": {
    "hostname": "The_Plug",
    "uptime": 123456.78,
    "cpu_usage": 65.3,
    "memory_used": 4294967296,
    "memory_total": 17179869184,
    "memory_pct": 25.0,
    "load_average": [1.5, 1.2, 0.9],
    "timestamp": 1703337717
  }
}
```

**Stale Data Fields** (when RPC is down):

```json
{
  "data": {
    "stale": true,
    "error_code": "RPC_DISCONNECT",
    "last_update": "2025-12-23T13:05:00Z"
    // ... cached data fields ...
  }
}
```

### `compression.update`

Compression job progress updates. The v2 API provides detailed progress streaming optimized for WebSocket clients.

#### Individual Job Update

Sent for each running/pending job during polling:

```json
{
  "type": "compression.update",
  "timestamp": "2025-12-23T13:08:37Z",
  "data": {
    "job_id": "job-abc123",
    "status": "running",
    "job_type": "compress_file",
    "priority": "normal",
    "progress": 45.2,
    "phase": "compressing",
    "bytes_processed": 52428800,
    "bytes_total": 116000000,
    "compression_ratio": 0.23,
    "elapsed_seconds": 120.5,
    "eta_seconds": 147.3,
    "input_path": "/data/file.tar",
    "output_path": "/data/file.tar.sigma",
    "timestamp": 1703337717
  }
}
```

#### Summary Update

Includes all running/pending jobs with queue statistics:

```json
{
  "type": "compression.update",
  "timestamp": "2025-12-23T13:08:37Z",
  "data": {
    "jobs": [
      {
        "job_id": "job-abc123",
        "status": "running",
        "progress": 45.2,
        "...": "..."
      }
    ],
    "total_running": 2,
    "total_pending": 5,
    "total_jobs": 15,
    "timestamp": 1703337717
  }
}
```

#### Progress Fields

| Field               | Type   | Description                                                            |
| ------------------- | ------ | ---------------------------------------------------------------------- |
| `job_id`            | string | Unique job identifier                                                  |
| `status`            | string | `pending`, `running`, `completed`, `failed`, `cancelled`               |
| `job_type`          | string | `compress_data`, `compress_file`, `decompress_data`, `decompress_file` |
| `priority`          | string | `low`, `normal`, `high`, `critical`                                    |
| `progress`          | number | Completion percentage (0-100)                                          |
| `phase`             | string | Current operation phase                                                |
| `bytes_processed`   | number | Bytes processed so far                                                 |
| `bytes_total`       | number | Total bytes to process                                                 |
| `compression_ratio` | number | Current compression ratio (original/compressed)                        |
| `elapsed_seconds`   | number | Time elapsed since job started                                         |
| `eta_seconds`       | number | Estimated time remaining                                               |
| `input_path`        | string | Source file path (if file operation)                                   |
| `output_path`       | string | Destination file path (if file operation)                              |

````

### `agent.status`

Agent swarm status updates.

```json
{
  "type": "agent.status",
  "timestamp": "2025-12-23T13:08:37Z",
  "data": {
    "agent_id": "TENSOR-07",
    "status": "active",
    "current_task": "compression_analysis",
    "memory_usage": 256.5,
    "timestamp": 1703337717
  }
}
````

### `notification`

General notifications.

```json
{
  "type": "notification",
  "timestamp": "2025-12-23T13:08:37Z",
  "data": {
    "message": "Welcome to SigmaVault WebSocket",
    "level": "info"
  }
}
```

### `rpc_error`

RPC communication errors.

```json
{
  "type": "rpc_error",
  "timestamp": "2025-12-23T13:08:37Z",
  "data": {
    "reason": "rpc_disconnect",
    "error_code": "SYSTEM_STATUS_FAILED",
    "consecutive_failures": 3,
    "timestamp": 1703337717
  }
}
```

### `heartbeat`

Connection keepalive signal.

```json
{
  "type": "heartbeat",
  "timestamp": "2025-12-23T13:08:37Z",
  "data": {
    "server_time": 1703337717
  }
}
```

## Subscription Management

### Subscribe to Events

```json
{
  "type": "subscribe",
  "data": {
    "events": ["system.status", "compression.update"]
  }
}
```

### Unsubscribe from Events

```json
{
  "type": "unsubscribe",
  "data": {
    "events": ["compression.update"]
  }
}
```

## Graceful Degradation

The WebSocket system implements graceful degradation when the RPC engine is unavailable:

### Cache Behavior

1. **Fresh Data**: When RPC is healthy, all fields are current
2. **Stale Data**: When RPC fails:
   - `stale: true` flag added to data
   - `error_code` field indicates failure reason
   - `last_update` shows when data was last fresh
   - Cached values are served until RPC recovers

### Circuit Breaker

- **Threshold**: 5 consecutive failures triggers circuit breaker
- **Reset**: After 5 minutes, circuit attempts to close
- **Behavior**: While open, serves cached data with `CIRCUIT_BREAKER_OPEN` error code

### Error Codes

| Code                      | Description                 |
| ------------------------- | --------------------------- |
| `RPC_DISCONNECT`          | RPC connection failed       |
| `SYSTEM_STATUS_FAILED`    | System status RPC failed    |
| `COMPRESSION_JOBS_FAILED` | Compression jobs RPC failed |
| `AGENT_STATUS_FAILED`     | Agent status RPC failed     |
| `CIRCUIT_BREAKER_OPEN`    | Circuit breaker activated   |

## Performance Characteristics

### Tested Metrics (Phase 2.7.5)

| Metric                  | Value      | Notes                     |
| ----------------------- | ---------- | ------------------------- |
| Connection Success Rate | 100%       | 10 concurrent connections |
| Message Throughput      | 4.19 msg/s | With 5s poll interval     |
| Memory Usage            | 0.64 MB    | 10 clients, 30 seconds    |
| Goroutines              | 22         | Efficient multiplexing    |
| Messages per Connection | 13.0 avg   | Balanced distribution     |

### Scalability

- Hub uses client map with mutex for thread-safe access
- ReadPump/WritePump pattern per connection
- Buffered channels (256 messages) per client
- Broadcast uses selective subscription filtering

### Poll Intervals

| Event Type        | Default Interval |
| ----------------- | ---------------- |
| System Status     | 5 seconds        |
| Compression Jobs  | 5 seconds        |
| Agent Status      | 5 seconds        |
| Scheduler Metrics | 5 seconds        |
| Recovery Status   | 5 seconds        |
| Tuning Status     | 5 seconds        |

## Client Implementation Guide

### JavaScript/TypeScript

```typescript
class SigmaVaultWebSocket {
  private ws: WebSocket;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;

  connect(url: string = "ws://localhost:12080/ws") {
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("Connected to SigmaVault");
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleEvent(msg);
    };

    this.ws.onclose = () => {
      this.attemptReconnect();
    };
  }

  private handleEvent(event: Event) {
    switch (event.type) {
      case "system.status":
        if (event.data.stale) {
          console.warn("Serving stale data:", event.data.error_code);
        }
        this.updateSystemStatus(event.data);
        break;
      case "rpc_error":
        console.error("RPC Error:", event.data);
        break;
      // ... handle other event types
    }
  }

  subscribe(events: string[]) {
    this.ws.send(
      JSON.stringify({
        type: "subscribe",
        data: { events },
      }),
    );
  }

  unsubscribe(events: string[]) {
    this.ws.send(
      JSON.stringify({
        type: "unsubscribe",
        data: { events },
      }),
    );
  }
}
```

### React Hook

```typescript
import { useEffect, useState, useCallback } from "react";

interface SystemStatus {
  hostname: string;
  cpu_usage: number;
  memory_pct: number;
  stale?: boolean;
}

export function useSystemStatus(): SystemStatus | null {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:12080/ws");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "system.status") {
        setStatus(msg.data);
      }
    };

    return () => ws.close();
  }, []);

  return status;
}
```

## Test Files

| File                            | Purpose                           |
| ------------------------------- | --------------------------------- |
| `tests/test_ws_events.go`       | Basic event delivery verification |
| `tests/test_cache_sync.go`      | Cache synchronization testing     |
| `tests/test_circuit_breaker.go` | Circuit breaker behavior          |
| `tests/test_performance.go`     | Concurrent connection testing     |
| `tests/test_websocket.go`       | Comprehensive WebSocket testing   |

## Changelog

### v1.0 (2025-12-23)

- Initial production-ready implementation
- 8 event types supported
- Default subscriptions on connection
- Graceful degradation with caching
- Circuit breaker pattern for RPC failures
- Performance tested with 10 concurrent connections

---

**Authors:** TENSOR Agent, STREAM Agent  
**Reviewed:** ECLIPSE Testing Agent  
**Approved:** Phase 2.7.5 Completion
