# Task 2.7: Error Handling & Recovery Design

**Status**: Implementation Phase  
**Priority**: Critical Infrastructure  
**Scope**: WebSocket Hub + Event Subscriber Error Resilience

## Overview

This task implements comprehensive error handling and recovery for WebSocket connections and RPC backend failures. The implementation preserves client connections during failures, notifies clients of error conditions, and enables graceful degradation with cached data.

## Architecture Principles

1. **Client Resilience**: Never silently drop clients; always notify of failures
2. **Graceful Degradation**: Continue serving cached data when backend unavailable
3. **Heartbeat Availability**: Keep-alive pings continue even during RPC failures
4. **Observable Failures**: Detailed logging and error events for debugging
5. **Automatic Recovery**: Exponential backoff retry with circuit breaker

## Error Handling Strategy

### 1. Error Event Types

```go
// Existing message types to utilize
const (
    TypeSystemStatus      MessageType = "system_status"      // System metrics
    TypeStorageUpdate     MessageType = "storage_update"     // Storage info
    TypeAgentStatus       MessageType = "agent_status"       // Agent swarm status
    TypeCompressionUpdate MessageType = "compression_update" // Compression jobs
    TypeNotification      MessageType = "notification"       // User notifications
    TypeError             MessageType = "error"              // ⭐ Error events
    TypePing              MessageType = "ping"               // Keep-alive ping
    TypePong              MessageType = "pong"               // Ping response

    // New error-specific types
    TypeConnectionError   MessageType = "connection_error"   // Connection loss
    TypeRPCError          MessageType = "rpc_error"         // RPC backend failure
    TypeHeartbeat         MessageType = "heartbeat"         // Heartbeat keep-alive
)
```

### 2. Error Event Data Structure

```go
// ErrorEvent sent on TypeError, TypeRPCError, etc.
type ErrorEvent struct {
    Code      string      `json:"code"`        // Error code (e.g., "RPC_UNAVAILABLE")
    Message   string      `json:"message"`     // Human-readable error message
    Details   string      `json:"details"`     // Additional details
    Timestamp int64       `json:"timestamp"`   // Unix timestamp
    Component string      `json:"component"`   // Which component failed (hub, rpc, etc)
    Severity  string      `json:"severity"`    // "warning", "error", "critical"
    Data      interface{} `json:"data"`        // Optional recovery data (cached state)
}

// StatusData with optional error flag for graceful degradation
type StatusDataWithError struct {
    Error    *ErrorEvent `json:"error,omitempty"`   // Null if no error
    IsStale  bool        `json:"is_stale"`          // True if data is cached
    Data     interface{} `json:"data"`              // Actual data (cached or fresh)
}
```

### 3. Hub Error Handling (hub.go)

#### Problem: Silent Client Drops

**Current**: Broadcast default case silently deletes slow clients
**Solution**: Send error event before dropping

```go
// Current problematic code:
case message := <-h.broadcast:
  h.mu.RLock()
  for client := range h.clients {
    select {
    case client.Send <- message:
    default:
      close(client.Send)      // ❌ Silent drop
      delete(h.clients, client)
    }
  }
  h.mu.RUnlock()

// Solution: Send error event first
case message := <-h.broadcast:
  h.mu.RLock()
  for client := range h.clients {
    select {
    case client.Send <- message:
    default:
      // Send error event before dropping
      errorMsg := h.createErrorEvent(
          "SLOW_CLIENT",
          "Client buffer full, connection closing",
          "hub",
          "warning",
      )
      // Try to send error (may also fail but we've tried)
      select {
      case client.Send <- errorMsg:
      default:
      }

      close(client.Send)
      delete(h.clients, client)
      h.errorCount++ // Track error metrics
      log.Warn().Str("client_id", client.ID).
          Msg("Client disconnected due to slow buffer")
    }
  }
  h.mu.RUnlock()
```

#### Improvements to readPump

```go
// Current: Logs but doesn't notify
// Improved: Also sends error event to other connected clients
func (c *Client) readPump() {
  defer func() {
    c.Conn.Close()
  }()

  for {
    _, message, err := c.Conn.ReadMessage()
    if err != nil {
      if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
        log.Error().Err(err).Str("client_id", c.ID).Msg("WebSocket read error")

        // NEW: Notify other clients of disconnection
        if c.Hub != nil {
          c.Hub.BroadcastError(
              "CLIENT_DISCONNECTED",
              fmt.Sprintf("Client %s disconnected unexpectedly", c.ID),
              "client",
              "warning",
          )
        }
      }
      break
    }
    c.handleMessage(message)
  }
}
```

#### Improvements to writePump

```go
// Enhanced error handling with context
func (c *Client) writePump() {
  ticker := time.NewTicker(30 * time.Second)
  defer func() {
    ticker.Stop()
    c.Conn.Close()
  }()

  writeErrors := 0
  const MAX_WRITE_ERRORS = 3

  for {
    select {
    case message, ok := <-c.Send:
      if !ok {
        c.Conn.WriteMessage(websocket.CloseMessage, []byte{})
        return
      }

      c.mu.Lock()
      err := c.Conn.WriteMessage(websocket.TextMessage, message)
      c.mu.Unlock()

      if err != nil {
        writeErrors++
        log.Error().Err(err).Str("client_id", c.ID).
            Int("write_errors", writeErrors).Msg("WebSocket write error")

        // Close after multiple failures
        if writeErrors >= MAX_WRITE_ERRORS {
          return
        }
      } else {
        writeErrors = 0 // Reset on success
      }

    case <-ticker.C:
      c.mu.Lock()
      err := c.Conn.WriteMessage(websocket.PingMessage, nil)
      c.mu.Unlock()

      if err != nil {
        log.Error().Err(err).Str("client_id", c.ID).Msg("Ping error")
        return
      }
    }
  }
}
```

#### New Methods: Error Broadcasting

```go
// BroadcastError sends error event to all subscribed clients
func (h *Hub) BroadcastError(code, message, component, severity string) {
  errorEvent := ErrorEvent{
    Code:      code,
    Message:   message,
    Component: component,
    Severity:  severity,
    Timestamp: time.Now().Unix(),
  }
  h.BroadcastIfSubscribed(TypeError, errorEvent)
}

// GetErrorMetrics returns current error tracking
func (h *Hub) GetErrorMetrics() map[string]interface{} {
  h.mu.RLock()
  defer h.mu.RUnlock()

  return map[string]interface{}{
    "total_clients":       len(h.clients),
    "error_count":         h.errorCount,
    "slow_client_drops":   h.slowClientDrops,
    "read_errors":         h.readErrors,
    "write_errors":        h.writeErrors,
  }
}
```

### 4. EventSubscriber RPC Failure Recovery (events.go)

#### Problem: Silent RPC Failures

**Current**: Polls fail silently, clients unaware
**Solution**: Broadcast error events, cache state, send heartbeat

#### Circuit Breaker Pattern

```go
// Add to EventSubscriber struct
type EventSubscriber struct {
  hub                    *Hub
  rpcClient              *rpc.Client
  ticker                 *time.Ticker
  done                   chan struct{}
  mu                     sync.RWMutex
  running                bool

  // Error tracking for circuit breaker
  consecutiveErrors      int
  circuitOpen            bool              // Stop polling if true
  circuitOpenTime        time.Time
  lastHealthCheckTime    time.Time
  healthCheckInterval    time.Duration     // How often to retry

  // Cached state for graceful degradation
  cachedSystemStatus     interface{}
  cachedCompressionJobs  []interface{}
  cachedAgentStatus      interface{}
  cacheTimestamps        map[string]time.Time
}

// Constants for circuit breaker
const (
  MAX_CONSECUTIVE_ERRORS = 3
  CIRCUIT_OPEN_DURATION  = 30 * time.Second  // Wait before retry
  HEALTH_CHECK_INTERVAL  = 10 * time.Second  // Retry health check
)
```

#### Improved RPC Polling with Error Recovery

```go
// Example: pollSystemStatus with error recovery
func (es *EventSubscriber) pollSystemStatus(ctx context.Context) {
  // Check if circuit is open
  if es.isCircuitOpen() {
    // Try health check periodically
    if es.shouldAttemptHealthCheck() {
      es.performHealthCheck(ctx)
    }

    // Send cached state with error flag
    es.sendCachedSystemStatus(true)
    return
  }

  // Normal polling flow
  status, err := es.rpcClient.GetSystemStatus(ctx, &rpc.GetSystemStatusParams{})

  if err != nil {
    es.consecutiveErrors++
    log.Error().Err(err).Int("consecutive_errors", es.consecutiveErrors).
        Msg("Failed to poll system status from RPC")

    // Broadcast error event
    es.hub.BroadcastError(
        "RPC_FAILURE",
        fmt.Sprintf("System status RPC failed: %v", err),
        "rpc",
        "error",
    )

    // Open circuit if threshold exceeded
    if es.consecutiveErrors >= MAX_CONSECUTIVE_ERRORS {
      es.openCircuit()
    }

    // Send cached data with error flag
    es.sendCachedSystemStatus(true)
    return
  }

  // Success: reset error counter and update cache
  es.consecutiveErrors = 0
  if es.circuitOpen {
    es.closeCircuit()
    // Notify recovery
    es.hub.BroadcastError(
        "RPC_RECOVERED",
        "System status RPC connection restored",
        "rpc",
        "warning",
    )
  }

  // Update cache
  data := mapSystemStatus(status)
  es.cacheSystemStatus(data)

  // Broadcast fresh data
  if err := es.hub.BroadcastIfSubscribed(TypeSystemStatus, data); err != nil {
    log.Error().Err(err).Msg("Failed to broadcast system status")
  }
}

// Helper: Send cached status with error flag
func (es *EventSubscriber) sendCachedSystemStatus(isStale bool) {
  es.mu.RLock()
  cached := es.cachedSystemStatus
  timestamp := es.cacheTimestamps["system_status"]
  es.mu.RUnlock()

  if cached == nil {
    return // No cache available
  }

  wrapped := map[string]interface{}{
    "data":     cached,
    "is_stale": isStale,
    "cached_at": timestamp.Unix(),
  }

  if isStale {
    wrapped["error"] = map[string]interface{}{
      "code": "RPC_UNAVAILABLE",
      "message": "System status RPC unavailable, showing cached data",
      "severity": "warning",
    }
  }

  es.hub.BroadcastIfSubscribed(TypeSystemStatus, wrapped)
}

// Helper: Cache system status
func (es *EventSubscriber) cacheSystemStatus(data interface{}) {
  es.mu.Lock()
  defer es.mu.Unlock()

  es.cachedSystemStatus = data
  es.cacheTimestamps["system_status"] = time.Now()
}

// Circuit breaker: Open
func (es *EventSubscriber) openCircuit() {
  es.mu.Lock()
  defer es.mu.Unlock()

  es.circuitOpen = true
  es.circuitOpenTime = time.Now()

  log.Warn().Msg("RPC circuit breaker opened, suspending polling")
}

// Circuit breaker: Close
func (es *EventSubscriber) closeCircuit() {
  es.mu.Lock()
  defer es.mu.Unlock()

  es.circuitOpen = false
  es.consecutiveErrors = 0

  log.Info().Msg("RPC circuit breaker closed, resuming normal polling")
}

// Check if circuit is open
func (es *EventSubscriber) isCircuitOpen() bool {
  es.mu.RLock()
  defer es.mu.RUnlock()

  if !es.circuitOpen {
    return false
  }

  // Check if enough time has passed to retry
  if time.Since(es.circuitOpenTime) > CIRCUIT_OPEN_DURATION {
    return false // Allow retry
  }

  return true
}

// Should attempt health check (periodic retry while circuit open)
func (es *EventSubscriber) shouldAttemptHealthCheck() bool {
  es.mu.RLock()
  defer es.mu.RUnlock()

  if !es.circuitOpen {
    return false
  }

  return time.Since(es.lastHealthCheckTime) > HEALTH_CHECK_INTERVAL
}

// Perform health check
func (es *EventSubscriber) performHealthCheck(ctx context.Context) {
  es.mu.Lock()
  es.lastHealthCheckTime = time.Now()
  es.mu.Unlock()

  if es.rpcClient == nil {
    return
  }

  // Try a lightweight health check
  ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
  defer cancel()

  _, err := es.rpcClient.GetSystemStatus(ctx, &rpc.GetSystemStatusParams{})
  if err == nil {
    es.closeCircuit()
  }
}
```

#### Heartbeat During Failures

```go
// Add heartbeat events every 10 seconds even when RPC fails
func (es *EventSubscriber) startHeartbeat() {
  heartbeatTicker := time.NewTicker(10 * time.Second)
  go func() {
    defer heartbeatTicker.Stop()

    for {
      select {
      case <-es.done:
        return
      case <-heartbeatTicker.C:
        // Send heartbeat to keep connection alive
        heartbeat := map[string]interface{}{
          "timestamp": time.Now().Unix(),
          "clients_connected": es.hub.ClientCount(),
        }
        es.hub.BroadcastIfSubscribed(TypeHeartbeat, heartbeat)
      }
    }
  }()
}
```

### 5. Graceful Shutdown

```go
// In routes.go Setup function, propagate context for shutdown
func Setup(app *fiber.App, config *config.Config) {
  ctx, cancel := context.WithCancel(context.Background())
  defer cancel()

  // ... existing code ...

  // Start event subscriber with context
  eventSubscriber.Start(ctx, 5*time.Second)

  // Register graceful shutdown
  app.Hooks().OnShutdown(func() error {
    log.Info().Msg("WebSocket shutdown initiated")
    cancel()                    // Stop event subscriber
    eventSubscriber.Stop()      // Stop polling
    time.Sleep(100 * time.Millisecond)  // Grace period

    // Notify all connected clients
    hub.BroadcastError(
        "SERVER_SHUTDOWN",
        "Server is shutting down, please reconnect after restart",
        "server",
        "critical",
    )

    // Close all client connections
    hub.mu.RLock()
    clients := make([]*Client, 0, len(hub.clients))
    for client := range hub.clients {
      clients = append(clients, client)
    }
    hub.mu.RUnlock()

    for _, client := range clients {
      client.Conn.Close()
    }

    log.Info().Msg("WebSocket shutdown complete")
    return nil
  })
}
```

## Implementation Sequence

### Phase 1: Hub Error Handling (hub.go)

1. Add error metrics fields to Hub struct
2. Implement BroadcastError method
3. Modify broadcast loop to send error before dropping clients
4. Enhance readPump with error notification
5. Enhance writePump with error handling

### Phase 2: Error Events (hub.go + events.go)

1. Add ErrorEvent struct
2. Add error broadcasting utilities
3. Export error-related functions

### Phase 3: RPC Error Recovery (events.go)

1. Add circuit breaker fields to EventSubscriber
2. Implement circuit breaker methods (open, close, check)
3. Update pollSystemStatus with error handling
4. Update pollCompressionJobs with error handling
5. Update pollAgentStatus with error handling
6. Implement caching layer

### Phase 4: Heartbeat & Recovery (events.go)

1. Implement heartbeat broadcaster
2. Add graceful degradation with cached state
3. Implement health check and recovery

### Phase 5: Graceful Shutdown (routes.go)

1. Add context propagation
2. Implement shutdown hook
3. Notify clients before shutdown

### Phase 6: Test Updates (test_websocket.go)

1. Add error event handling
2. Implement reconnection logic
3. Add heartbeat verification
4. Test error scenarios

## Error Codes

```
RPC_FAILURE          - RPC backend call failed
RPC_UNAVAILABLE      - RPC backend not responding
RPC_RECOVERED        - RPC backend recovered after failure
SLOW_CLIENT          - Client buffer full, connection closing
CLIENT_DISCONNECTED  - Client disconnected unexpectedly
JSON_MARSHAL_ERROR   - Failed to marshal message to JSON
CIRCUIT_OPEN         - Circuit breaker is open, polling suspended
SERVER_SHUTDOWN      - Server is shutting down
```

## Testing Strategy

1. **Unit Tests**: Error event creation, circuit breaker logic
2. **Integration Tests**: RPC failure scenarios, cached state broadcasting
3. **E2E Tests**: Client reconnection, heartbeat validation, graceful shutdown
4. **Load Tests**: Multiple clients with RPC failures
5. **Chaos Tests**: Intermittent RPC failures, slow clients

## Success Criteria

- ✅ All client disconnections logged and notified
- ✅ RPC failures don't cause client disconnection
- ✅ Cached data sent during RPC outages
- ✅ Heartbeat continues during failures
- ✅ Circuit breaker prevents hammering dead RPC
- ✅ Graceful shutdown notifies all clients
- ✅ Error metrics available for monitoring
- ✅ Test client validates error handling

## References

- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
- RFC 6455 WebSocket Protocol: https://tools.ietf.org/html/rfc6455
- Go Concurrency Patterns: https://go.dev/blog/pipelines
