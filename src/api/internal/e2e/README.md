# PHASE 4: E2E & Performance Testing

## Overview

This directory contains comprehensive end-to-end (E2E) and performance testing for the SigmaVault NAS OS API server. The test suite validates complete system flows from REST API requests through engine communication to real-time WebSocket event delivery.

## Test Structure

### Files

- **e2e_test.go** - Basic E2E tests validating API endpoints and request/response cycles
- **performance_test.go** - Performance benchmarks and latency distribution tests
- **websocket_test.go** - WebSocket connection, messaging, and real-time event tests
- **integration_test.go** - Full system integration tests combining REST, engine, and WebSocket flows

## Test Coverage

### E2E Tests (e2e_test.go)

| Test | Purpose | Coverage |
|------|---------|----------|
| TestE2EHealthCheck | Validates /health endpoint | Server health status |
| TestE2EBasicAPIFlow | Tests complete request/response cycle | API functionality |
| TestE2EAuthenticationFlow | Tests auth flow (when implemented) | Authentication system |
| TestE2EConcurrentRequests | Tests 50 concurrent API requests | Concurrency handling |
| TestE2EErrorHandling | Tests error responses for various scenarios | Error paths |
| TestE2EResponseTiming | Measures response times | Performance baseline |
| TestE2ERequestHeaders | Validates security and custom headers | Header handling |
| TestE2ELoadPatterns | Tests burst load handling | Load resilience |
| TestE2ETimeout | Tests timeout handling | Timeout behavior |
| TestE2EContentNegotiation | Tests response content types | Content negotiation |

### Performance Tests (performance_test.go)

| Test | Purpose | Metrics |
|------|---------|---------|
| BenchmarkE2EResponseTime | Micro-benchmark response time | Mean, StdDev, P50/P95/P99 |
| BenchmarkE2EHighConcurrency | Tests under 100 concurrent workers | Throughput, latency |
| TestE2EPerformanceBaseline | Establishes baseline metrics | Mean latency, throughput |
| TestE2ELatencyDistribution | Documents latency distribution | Percentile analysis |
| TestE2EMemoryUsage | Monitors memory usage | Memory patterns |

### WebSocket Tests (websocket_test.go)

| Test | Purpose | Coverage |
|------|---------|----------|
| TestE2EWebSocketConnection | Tests basic WS connection | Connection lifecycle |
| TestE2EWebSocketMultipleClients | Tests 20 concurrent WS clients | Concurrent connections |
| TestE2EWebSocketMessageReceival | Tests receiving messages | Message delivery |
| TestE2EWebSocketBroadcast | Tests broadcast message delivery | Broadcasting |
| TestE2EWebSocketErrorHandling | Tests error scenarios | Error handling |
| TestE2EWebSocketConnectionCycle | Tests connection lifecycle | Reconnection |
| TestE2EWebSocketStressTest | 50 clients × 10 messages stress test | Stress tolerance |
| TestE2EWebSocketLatency | Measures WS message latency | Latency metrics |
| TestE2EWebSocketReconnection | Tests reconnection scenarios | Reconnection reliability |

### Integration Tests (integration_test.go)

| Test | Purpose | Coverage |
|------|---------|----------|
| TestE2EAPIToEngineIntegration | Tests API→Engine flow | Full request path |
| TestE2ERequestValidation | Tests request validation | Input validation |
| TestE2EMiddlewareExecution | Tests middleware stack | Request tracking, security headers |
| TestE2ERouteCompatibility | Tests all API routes | Route functionality |
| TestE2ERateLimiting | Tests rate limiting behavior | Rate limit enforcement |
| TestE2EErrorRecovery | Tests error recovery | System resilience |
| TestE2ESystemStability | Long-running stability test | System stability |
| TestE2EResponseCompleteness | Tests response data completeness | Response structure |

## Running the Tests

### Run All E2E Tests

```bash
cd src/api
go test ./internal/e2e -v -timeout 120s
```

### Run Specific Test Category

```bash
# Only E2E tests
go test ./internal/e2e -v -run TestE2E -timeout 60s

# Only WebSocket tests
go test ./internal/e2e -v -run WebSocket -timeout 60s

# Only integration tests
go test ./internal/e2e -v -run Integration -timeout 60s

# Only performance tests
go test ./internal/e2e -v -run Performance -timeout 120s
```

### Run Benchmarks

```bash
# Run benchmarks with specific duration
go test ./internal/e2e -bench=Benchmark -benchtime=10s -benchmem

# Run response time benchmark
go test ./internal/e2e -bench=BenchmarkE2EResponseTime -benchtime=30s

# Run concurrency benchmark
go test ./internal/e2e -bench=BenchmarkE2EHighConcurrency -benchtime=30s
```

### Run with Coverage

```bash
go test ./internal/e2e -v -cover -coverprofile=coverage.out -timeout 120s
go tool cover -html=coverage.out
```

### Run Specific Test

```bash
# Single test
go test ./internal/e2e -v -run TestE2EHealthCheck

# Specific WebSocket test
go test ./internal/e2e -v -run TestE2EWebSocketConnection
```

## Performance Baseline Targets

### Response Time

- **Mean**: < 50ms
- **P95**: < 200ms
- **P99**: < 500ms
- **Max**: < 1000ms

### Throughput

- **Single client**: > 100 req/sec
- **Concurrent (20 workers)**: > 1000 req/sec total
- **Concurrent (100 workers)**: > 5000 req/sec total

### WebSocket

- **Connection latency**: < 100ms
- **Message delivery latency**: < 50ms
- **Max concurrent clients**: > 100
- **Message throughput**: > 1000 msg/sec

### Reliability

- **Success rate (normal): > 99%
- **Success rate (burst): > 95%
- **Error recovery time: < 1s
- **Goroutine cleanup: 100% on connection close

## Test Server Details

### newE2ETestServer()

Each test uses a fresh test server instance on a unique port to avoid conflicts.

- **Fiber app** with full middleware stack
- **RPC client** configured for engine communication
- **WebSocket hub** for real-time events
- **CORS, security headers, rate limiting** all enabled

### Ports

Tests use ports 9001-9010 for basic E2E tests, 10001-10005 for performance, 11001-11009 for WebSocket, and 12001-12008 for integration tests.

## Key Metrics Tracked

### Latency Metrics
- Mean response time
- Standard deviation
- Percentiles: P1, P50, P95, P99, P100 (max)

### Throughput Metrics
- Requests per second
- Messages per second
- Success/error counts

### Resource Metrics
- Goroutine count
- Memory usage patterns
- Connection lifecycle

## Common Issues

### Test Timeouts

If tests timeout, increase the timeout parameter:
```bash
go test ./internal/e2e -v -timeout 180s
```

### Port Conflicts

If a port is already in use, tests will fail. Either:
1. Wait for the port to be released
2. Kill the process using the port
3. Tests use different port ranges to minimize conflicts

### WebSocket Connection Issues

The WebSocket client requires a proper HTTP server. Ensure:
- Server is running and responsive on `/api/v1/health`
- WebSocket endpoint is at `/ws`
- CORS is properly configured

## Performance Profiling

### CPU Profile

```bash
go test ./internal/e2e -v -cpuprofile=cpu.prof -run TestE2EPerformanceBaseline
go tool pprof cpu.prof
```

### Memory Profile

```bash
go test ./internal/e2e -v -memprofile=mem.prof -run TestE2EPerformanceBaseline
go tool pprof mem.prof
```

### Trace

```bash
go test ./internal/e2e -v -trace=trace.out -run TestE2EPerformanceBaseline
go tool trace trace.out
```

## Future Enhancements

### Planned for PHASE 4 Extensions

1. **OpenTelemetry Integration**
   - Trace API requests through full system
   - Measure component latencies
   - Generate distributed traces

2. **Load Testing Configuration**
   - Configurable load profiles (sustained, burst, spike)
   - Ramp-up and ramp-down scenarios
   - Multi-endpoint load patterns

3. **Failure Injection**
   - Network failures
   - Engine timeouts
   - Partial degradation scenarios

4. **Real-time Monitoring**
   - Live metrics dashboard
   - Real-time latency graphs
   - Alerts on performance degradation

5. **Soak Testing**
   - Days-long sustained load
   - Memory leak detection
   - Connection cleanup verification

## Test Dependencies

### External Packages

```
nhooyr.io/websocket - WebSocket client library
- Used for E2E WebSocket testing
- Supports context-based cancellation
- Proper connection cleanup

github.com/gofiber/fiber/v2 - Web framework
- Test servers use Fiber
- Real API handler execution
```

### Internal Packages

- `internal/config` - Configuration management
- `internal/handlers` - API handlers
- `internal/middleware` - Middleware stack
- `internal/routes` - Route setup
- `internal/rpc` - Engine communication
- `internal/websocket` - WebSocket implementation

## Success Criteria for PHASE 4

- ✅ All E2E tests passing (100% pass rate)
- ✅ Performance within baseline targets
- ✅ WebSocket stability verified
- ✅ System handles 100+ concurrent connections
- ✅ Error recovery verified
- ✅ No goroutine leaks
- ✅ No panics under load
- ✅ < 1s error recovery time

## Continuous Integration

### CI Configuration

Tests run on every commit:
```yaml
test-e2e:
  runs-on: linux
  timeout: 300 seconds
  steps:
    - go test ./internal/e2e -v -timeout 120s -race
    - go test ./internal/e2e -bench=. -benchtime=10s -benchmem
```

###ail Criteria

- All tests must pass
- No race conditions detected
- Performance within 10% of baseline
- Coverage > 80%

## References

- [Go Testing Documentation](https://golang.org/pkg/testing/)
- [Fiber Framework Documentation](https://docs.gofiber.io/)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [Performance Testing Best Practices](https://go.dev/blog/profiling-go-programs)

---

**Status**: PHASE 4 Testing Framework Created  
**Last Updated**: Current Session  
**Maintainer**: Engineering Team
