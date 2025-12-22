# Phase 2.7.4 - Test Client Updates for Error Event Handling

## Overview

**Status**: Implementation Complete, Ready for Execution  
**Duration**: Phase 2.7.3 → 2.7.4 (Test Client Implementation)  
**Objective**: Implement comprehensive error event handling in WebSocket test clients with full circuit breaker verification

---

## Architecture Summary

### Circuit Breaker Pattern Implementation
Located in: `src/api/internal/websocket/events.go`

**Key Parameters**:
- **Threshold**: 5 consecutive RPC failures
- **Reset Timeout**: 5 minutes (configurable)
- **Error Codes**:
  - `CIRCUIT_BREAKER_OPEN` - Circuit breaker engaged, preventing further RPC calls
  - `RPC_DISCONNECT` - Backend RPC connection lost
  - `SYSTEM_STATUS_FAILED` - System status poll failed
  - `AGENT_STATUS_FAILED` - Agent status poll failed
  - `COMPRESSION_JOBS_FAILED` - Compression job poll failed

**Graceful Degradation**:
- When circuit breaker opens: serve cached data with `stale=true` flag
- Response includes: `last_update`, `error_code`, `consecutive_failures`, `reason`
- Maintains semantic completeness of cached data
- Auto-recovery after timeout or successful RPC

---

## Implementation Details

### 1. test_websocket.go - Comprehensive Monitoring
**Location**: `src/api/test_websocket.go`  
**Size**: 272 lines  
**Purpose**: Real-time WebSocket event monitoring with error analysis

#### Key Features:
✅ **Event Type Monitoring** (7 types)
- TypeSystemStatus (0)
- TypeCompressionUpdate (1)
- TypeAgentStatus (2)
- TypeRPCError (3)
- TypeHeartbeat (4)
- TypeCompressionJobsError (5)
- TypeAgentStatusError (6)

✅ **Error Event Handling**
- Detects and counts error codes from event payloads
- Tracks error code occurrences with counts
- Extracts error metadata: `reason`, `consecutive_failures`, `last_update`

✅ **Circuit Breaker Verification**
- Detects `CIRCUIT_BREAKER_OPEN` events
- Records first occurrence timestamp
- Tracks `RPC_DISCONNECT` events
- Validates graceful degradation (stale flag)

✅ **Auto-Recovery Detection**
- Monitors transition from stale → fresh data
- Detects TypeSystemStatus events with `stale=false`
- Confirms recovery after circuit breaker period

✅ **Performance Metrics**
- Event intervals and distribution
- Average event frequency
- Min/max intervals

#### Output Structure:
```
[HH:MM:SS.mmm] Type: X (EventTypeName)
  Data: {...}
  Interval: XXms
  [Optional] ⚠️  Circuit breaker OPEN detected!
  [Optional] 📦 Stale flag detected - serving cached data
  [Optional] ✅ Auto-recovery detected

Connection Summary
=================================================
Connected for: XXs

Events Received:
  EventType: X

Error Codes Detected:
  CIRCUIT_BREAKER_OPEN: X
  RPC_DISCONNECT: X

Circuit Breaker Verification Results
=================================================
✅ CIRCUIT_BREAKER_OPEN error code received
   First occurrence: HH:MM:SS.mmm
✅ Graceful degradation with stale flag detected
✅ RPC_DISCONNECT detected at HH:MM:SS.mmm
✅ Auto-recovery after timeout detected (normal events resumed)

Average Event Interval: XXms
```

---

### 2. test_circuit_breaker.go - Focused Verification
**Location**: `src/api/test_circuit_breaker.go`  
**Size**: 289 lines  
**Purpose**: Comprehensive circuit breaker behavior verification with 4-point validation criteria

#### Test Parameters:
- **Duration**: 2 minutes (captures circuit breaker lifecycle)
- **Read Timeout**: 10 seconds per event
- **Success Criteria**: 4-point verification checklist

#### Key Data Structures:
```go
type CircuitBreakerTestEvent struct {
    Type       int
    Data       interface{}
    ReceivedAt time.Time
}

type TestResults struct {
    Events                  []*CircuitBreakerTestEvent
    CircuitBreakerOpens     int
    CachedDataServed        int
    ErrorCodes              map[string]int
    FirstCircuitBreakerTime time.Time
    FirstRPCDisconnectTime  time.Time
    AutoRecoveryTime        time.Time
}
```

#### 4-Point Verification Criteria:

| Criterion | Description | Detection Method | Success Indicator |
|-----------|-------------|------------------|-------------------|
| **1. Error Event Handling** | Validates error event detection and parsing | CircuitBreakerOpens > 0 OR ErrorCodes populated | ✅/⚠️ |
| **2. Graceful Degradation** | Confirms cached data serving during outage | CachedDataServed > 0 | ✅/⚠️ |
| **3. Stale Flag Presence** | Validates stale=true in responses | stale boolean field found in events | ✅/⚠️ |
| **4. Auto-Recovery** | Confirms fresh data after timeout | AutoRecoveryTime populated + timing valid | ✅/⚠️ |

#### Test Flow:
1. Connect to WebSocket server (localhost:8080)
2. Monitor events for 2 minutes
3. Capture all error events with timestamps
4. Detect circuit breaker state transitions (open → closed)
5. Track error codes and graceful degradation
6. Validate 4-point criteria
7. Generate verification results

#### Output Structure:
```
============================================================
CIRCUIT BREAKER VERIFICATION TEST
============================================================

Connecting to ws://localhost:8080/ws
✅ Connected to WebSocket server!

Monitoring for circuit breaker patterns (duration: 2m0s)...

[Real-time Event Stream with Analysis]
HH:MM:SS - Type: X (EventName) - [Optional: ❌ ERROR_CODE detected, 📦 stale flag, ✅ recovery]

============================================================
CIRCUIT BREAKER TEST RESULTS
============================================================

Events Captured:        XXX
Error Events:           XX
Circuit Breaker Opens:  X
Cached Data Served:     X

Error Code Summary:
  CIRCUIT_BREAKER_OPEN: X
  RPC_DISCONNECT: X
  SYSTEM_STATUS_FAILED: X

Verification Criteria:
[1/4] ✅ Error event handling: Detected
[2/4] ✅ Graceful degradation: Cached data served (X events)
[3/4] ✅ Stale flag present: Found in event payloads
[4/4] ✅ Auto-recovery: Fresh data after HH:MM:SS, timing valid

🎉 ALL VERIFICATION CRITERIA MET - Phase 2.7.4 PASSED
```

---

## Test Execution Plan

### Prerequisites:
1. SigmaVault API running on localhost:8080
2. WebSocket endpoint accessible at /ws
3. Go toolchain installed (for compilation)
4. Optional: Backend RPC service available or configured to fail

### Test Scenarios:

#### Scenario A: Normal Operation (no RPC failure)
- **Execution**: `go run src/api/test_websocket.go`
- **Expected**: Stable event stream, no error codes, no circuit breaker activation
- **Duration**: Run until Ctrl+C
- **Success**: Event counts increase, intervals stable (~5s)

#### Scenario B: Circuit Breaker Verification (with RPC failure)
- **Execution**: `go run src/api/test_circuit_breaker.go`
- **Pre-condition**: Optional - stop backend RPC service to trigger failure
- **Expected**: Circuit breaker opens after 5 failures, graceful degradation with stale flag
- **Duration**: 2 minutes (automated)
- **Success**: All 4 verification criteria pass

#### Scenario C: Auto-Recovery Observation (extended test)
- **Execution**: Run test_circuit_breaker.go with backend RPC failing, restart after ~3 minutes
- **Expected**: Circuit breaker opens, stale data served, recovery occurs ~5min after first failure
- **Duration**: ~5-6 minutes
- **Success**: AutoRecoveryTime populated, fresh data received

### Step-by-Step Execution:

```bash
# Step 1: Start the API server (if not already running)
# Make sure SigmaVault API is accessible on localhost:8080

# Step 2: Run comprehensive monitoring
cd src/api
go run test_websocket.go

# [In another terminal] Step 3: Run focused circuit breaker test
cd src/api
go run test_circuit_breaker.go

# [Optional] Step 4: Test with RPC failure
# Stop backend RPC service (simulate failure)
# Then run test_circuit_breaker.go again to observe circuit breaker activation
# Restart RPC after 3 minutes to test auto-recovery
```

---

## Success Criteria Checklist

### Phase 2.7.4 Completion Requirements:

- [ ] **Task 1**: Update test_websocket.go for error event handling
  - [x] Add event type constants (TypeRPCError, TypeCompressionJobsError, TypeAgentStatusError)
  - [x] Implement analyzeEventData() for error code tracking
  - [x] Add circuit breaker state tracking variables
  - [x] Implement graceful degradation detection (stale flag)
  - [x] Implement auto-recovery detection

- [ ] **Task 2**: Create circuit breaker verification test
  - [x] Create test_circuit_breaker.go file
  - [x] Implement 4-point verification criteria
  - [x] Implement event capture with timestamps
  - [x] Implement error code tracking
  - [x] Implement auto-recovery detection

- [ ] **Task 3**: Execute graceful degradation test
  - [ ] Run test_circuit_breaker.go against API
  - [ ] Verify stale=true flag in responses
  - [ ] Confirm last_update timestamp present
  - [ ] Document graceful degradation behavior

- [ ] **Task 4**: Test auto-recovery mechanism
  - [ ] Monitor 5-minute timeout window
  - [ ] Verify fresh data (stale=false) after timeout
  - [ ] Confirm failure count reset
  - [ ] Document auto-recovery timing

- [ ] **Task 5**: Verify all event types
  - [ ] Confirm all 7 event types appear in output
  - [ ] Verify error codes parsed correctly
  - [ ] Document event type distribution
  - [ ] Verify error-specific event handling

- [ ] **Task 6**: Generate completion report
  - [ ] Document test results with timeline
  - [ ] Verify all 4 verification criteria met
  - [ ] Create Phase 2.7.4 summary
  - [ ] Mark phase as complete

---

## Error Code Reference

### Standard Error Codes:
| Code | Source | Meaning | Trigger |
|------|--------|---------|---------|
| `CIRCUIT_BREAKER_OPEN` | EventSubscriber | Circuit breaker engaged | 5 consecutive RPC failures |
| `RPC_DISCONNECT` | RPC client | Backend RPC unavailable | Connection refused/timeout |
| `SYSTEM_STATUS_FAILED` | EventSubscriber poll | System status RPC failed | RPC error during poll |
| `AGENT_STATUS_FAILED` | EventSubscriber poll | Agent status RPC failed | RPC error during poll |
| `COMPRESSION_JOBS_FAILED` | EventSubscriber poll | Compression jobs RPC failed | RPC error during poll |

### Event Payload Structure:
```json
{
  "type": 3,
  "data": {
    "error_code": "CIRCUIT_BREAKER_OPEN",
    "reason": "Circuit breaker threshold exceeded",
    "consecutive_failures": 5,
    "stale": true,
    "last_update": "2024-01-15T10:30:45Z",
    "timestamp": 1705317045
  }
}
```

---

## Implementation Status

### Code Files:
| File | Lines | Status | Purpose |
|------|-------|--------|---------|
| test_websocket.go | 272 | ✅ Complete | Comprehensive monitoring |
| test_circuit_breaker.go | 289 | ✅ Complete | Focused verification |
| events.go (backend) | 526 | ✅ No changes | Circuit breaker impl |

### Functions Implemented:

**test_websocket.go**:
- `main()` - Event monitoring loop with state tracking
- `analyzeEventData()` - Error code extraction and analysis
- `minDuration()` - Interval calculation
- `maxDuration()` - Interval calculation

**test_circuit_breaker.go**:
- `main()` - 2-minute test session
- `processCircuitBreakerEvent()` - Real-time analysis
- `printTestResults()` - 4-point verification
- `getEventTypeName()` - Type name mapping

---

## Performance Characteristics

### Expected Behavior:
- **Normal Event Interval**: ~5 seconds (TypeSystemStatus)
- **Heartbeat Interval**: ~30 seconds (TypeHeartbeat)
- **Error Event Frequency**: High during RPC outage, low during normal operation
- **Circuit Breaker Activation**: < 10 seconds after 5th failure
- **Auto-Recovery Time**: ~5 minutes after circuit opens
- **Stale Data Duration**: Entire circuit breaker window

### Resource Usage:
- **Memory**: ~10-50 MB per test client
- **CPU**: Minimal (event-driven)
- **Network**: ~1-5 KB/s during normal operation
- **Disk**: None (runtime memory only)

---

## Troubleshooting Guide

### Issue: "Failed to connect to WebSocket server"
- **Cause**: API not running or not on localhost:8080
- **Solution**: Verify API is running with `curl http://localhost:8080/health`

### Issue: "No events received"
- **Cause**: WebSocket connection established but no events sent
- **Solution**: Ensure RPC backend is available and API is actively polling

### Issue: "Circuit breaker not detected"
- **Cause**: RPC service is stable, no failures occurring
- **Solution**: Stop backend RPC service or configure it to fail to trigger circuit breaker

### Issue: "Stale flag not found"
- **Cause**: Circuit breaker never engaged, no cached responses
- **Solution**: Trigger RPC failure to force circuit breaker activation

### Issue: "Auto-recovery not confirmed"
- **Cause**: Test duration too short or RPC still failing
- **Solution**: Run 2-minute test_circuit_breaker.go, ensure RPC recovers within window

---

## Next Steps

1. **Execute test_websocket.go** against running API to validate error monitoring
2. **Execute test_circuit_breaker.go** with RPC failure scenario to verify circuit breaker
3. **Document results** including error codes, timing, and verification criteria
4. **Generate Phase 2.7.4 completion report** with all 6 task validations
5. **Archive test outputs** for reference and compliance

---

## References

- **Circuit Breaker Implementation**: `src/api/internal/websocket/events.go` (lines 1-50+)
- **WebSocket Hub**: `src/api/internal/websocket/hub.go`
- **RPC Client**: `src/api/internal/rpc/client.go`
- **Error Handling**: `src/api/internal/websocket/events.go` (error code section)

---

**Phase 2.7.4 Specification**: Complete  
**Status**: Ready for Test Execution  
**Last Updated**: 2024-01-15  
**Prepared by**: Copilot ECLIPSE (Testing & Verification)

