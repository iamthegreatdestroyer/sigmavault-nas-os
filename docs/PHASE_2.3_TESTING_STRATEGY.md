# Phase 2.3: Comprehensive Testing & CI/CD Strategy

**Document Date**: February 10, 2026  
**Phase**: Option 2 - Testing & Polish  
**Objective**: Establish production-ready testing infrastructure and CI/CD pipelines  
**Estimated Duration**: 6-8 hours

---

## Executive Summary

Phase 2.3 has successfully implemented:

- ✅ Compression Stats RPC method (Engine + Go API)
- ✅ Agent Management RPC layer (7 methods, 40 agents)
- ✅ System integration (Engine ↔ Go API bridge)

**Current Gap**: Limited testing coverage and no CI/CD infrastructure.

This document outlines a comprehensive testing strategy to validate the three-service architecture and prepare for production deployment.

---

## Architecture Overview: Testing Layers

```
┌─────────────────────────────────────────────────────────┐
│                  E2E TESTS (UI Flow)                    │ Layer 4
│         Desktop UI → Go API → Engine RPC → Results      │
└─────────────────────────────────────────────────────────┘
                             ↑
┌─────────────────────────────────────────────────────────┐
│         INTEGRATION TESTS (Service Bridge)              │ Layer 3
│  Go API client ↔ RPC methods ↔ Python handlers          │
└─────────────────────────────────────────────────────────┘
                             ↑
┌─────────────────────────────────────────────────────────┐
│        UNIT TESTS (Individual Components)               │ Layer 2
│  Engine RPC routing | Handler functions | Agents        │
└─────────────────────────────────────────────────────────┘
                             ↑
┌─────────────────────────────────────────────────────────┐
│          CI/CD (Automated Pipeline)                     │ Layer 1
│  GitHub Actions → Test → Build → Deploy                │
└─────────────────────────────────────────────────────────┘
```

---

## Section 1: Testing Architecture

### 1.1 Test Organization Structure

```
s:\sigmavault-nas-os\
├── tests/
│   ├── unit/
│   │   ├── engine/
│   │   │   ├── test_rpc_routing.py        # RPC handler dispatch
│   │   │   ├── test_compression_stats.py  # Compression logic
│   │   │   ├── test_agent_handlers.py     # Agent query handlers
│   │   │   └── test_error_handling.py     # Error cases
│   │   ├── api/
│   │   │   ├── test_http_endpoints.go    # Go API routes
│   │   │   ├── test_rpc_client.go        # RPC client bridge
│   │   │   └── test_middleware.go        # Auth, logging, etc.
│   │   └── desktop/
│   │       ├── test_components.ts        # React components
│   │       ├── test_store.ts             # State management
│   │       └── test_hooks.ts             # Custom React hooks
│   ├── integration/
│   │   ├── test_engine_api_bridge.py     # Engine ↔ Go API
│   │   ├── test_rpc_methods.py           # All RPC methods
│   │   ├── test_compression_flow.py      # Compression E2E
│   │   ├── test_agent_operations.py      # Agent query E2E
│   │   └── test_error_scenarios.py       # Error handling
│   ├── e2e/
│   │   ├── test_ui_workflows.ts          # UI → Go API → Engine
│   │   ├── test_compression_ui.ts        # Compression dashboard
│   │   ├── test_agent_panel.ts           # Agent management UI
│   │   └── test_concurrent_ops.ts        # Multiple concurrent requests
│   ├── performance/
│   │   ├── test_load.py                  # Load testing script
│   │   ├── test_rpc_throughput.py        # RPC performance
│   │   ├── test_api_latency.py           # API response times
│   │   └── benchmarks.json               # Results storage
│   ├── fixtures/
│   │   ├── agents_data.json              # Test agent data
│   │   ├── compression_jobs.json         # Sample compression jobs
│   │   └── mock_responses.json           # Mock API responses
│   └── conftest.py                       # Pytest fixtures & config
├── .github/
│   └── workflows/
│       ├── test.yml                      # Unit + Integration tests
│       ├── e2e.yml                       # E2E test suite
│       ├── build-api.yml                 # Go API build
│       ├── build-engine.yml              # Engine build
│       ├── build-ui.yml                  # Desktop UI build
│       └── release.yml                   # Release workflow
└── scripts/
    ├── run_all_tests.sh                  # Master test runner
    ├── coverage_report.sh                # Generate coverage
    └── performance_baseline.sh           # Establish perf baseline
```

### 1.2 Test Framework Selection

| Component       | Language           | Framework                      | Rationale                                   |
| --------------- | ------------------ | ------------------------------ | ------------------------------------------- |
| Engine (Python) | Python             | pytest + pytest-asyncio        | Native async support, comprehensive plugins |
| Go API          | Go                 | testing + testify              | Standard Go testing, assertion library      |
| Desktop UI      | TypeScript         | Vitest + React Testing Library | Fast, ESM-native, component focus           |
| E2E             | Cypress/Playwright | Cypress                        | UI interaction testing, visual debugging    |
| Performance     | Python             | Locust                         | Real-time load testing, realistic scenarios |

### 1.3 Coverage Targets

| Component   | Unit    | Integration | E2E     | Overall  |
| ----------- | ------- | ----------- | ------- | -------- |
| Engine      | 90%     | 85%         | 70%     | 85%+     |
| Go API      | 85%     | 80%         | 75%     | 80%+     |
| Desktop UI  | 80%     | -           | 75%     | 78%+     |
| **Overall** | **88%** | **82%**     | **73%** | **81%+** |

---

## Section 2: Unit Testing Strategy

### 2.1 Engine Unit Tests (Python)

**File**: `tests/unit/engine/test_rpc_routing.py`

```python
# Test coverage:
# 1. RPC method routing dispatch
# 2. Request/response validation
# 3. Error handling and JSON-RPC error codes
# 4. Parameter validation

Test Cases:
  ✓ Valid RPC request -> correct handler invoked
  ✓ Invalid method -> JSON-RPC error (-32601)
  ✓ Missing required params -> validation error (-32602)
  ✓ Internal error -> -32603 with stack trace
  ✓ Timeout handling -> proper error response
  ✓ Concurrent requests -> no race conditions
```

**File**: `tests/unit/engine/test_compression_stats.py`

```python
# Test coverage:
# 1. Compression stats collection
# 2. Job tracking and completion
# 3. Statistics calculation
# 4. Edge cases (no jobs, overflow, etc.)

Test Cases:
  ✓ Add compression job -> tracked correctly
  ✓ Retrieve stats for nonexistent job -> error
  ✓ Stats calculation (avg, total, success rate)
  ✓ Large job list -> performance acceptable
  ✓ Completed jobs cleanup -> memory managed
  ✓ Concurrent job tracking -> accurate counts
```

**File**: `tests/unit/engine/test_agent_handlers.py`

```python
# Test coverage:
# 1. Agent query handlers
# 2. Metrics calculation
# 3. Tier organization
# 4. Status aggregation

Test Cases:
  ✓ agents.list -> all 40 agents returned
  ✓ agents.get -> valid agent details
  ✓ agents.get_by_codename -> valid lookup
  ✓ agents.metrics -> correct calculations
  ✓ agents.list_tiers -> proper distribution
  ✓ agents.swarm_status -> accurate aggregation
  ✓ Invalid agent -> proper error handling
  ✓ Tier filtering -> correct subset returned
```

### 2.2 Go API Unit Tests

**File**: `tests/unit/api/test_http_endpoints.go`

```go
// Test coverage:
// 1. Route registration
// 2. Request/response marshaling
// 3. Status code correctness
// 4. Header handling

Test Cases:
  ✓ /health endpoint -> 200 OK
  ✓ /api/v1/agents -> 200 with agent list
  ✓ /api/v1/agents/:id -> 200 with agent details
  ✓ /api/v1/agents/:id/metrics -> 200 with metrics
  ✓ /api/v1/compression/stats -> 200 with stats
  ✓ Non-existent endpoint -> 404
  ✓ Invalid query params -> 400
  ✓ Missing auth token -> 401
  ✓ Insufficient permissions -> 403
  ✓ Method not allowed -> 405
```

**File**: `tests/unit/api/test_rpc_client.go`

```go
// Test coverage:
// 1. RPC client creation
// 2. Method invocation
// 3. Response parsing
// 4. Error scenarios

Test Cases:
  ✓ Connect to Engine -> success
  ✓ Remote method call -> valid response
  ✓ Parameter marshaling -> correct format
  ✓ Response unmarshaling -> correct types
  ✓ Timeout handling -> error returned
  ✓ Connection failure -> graceful handling
  ✓ RPC error propagation -> correct error structure
```

### 2.3 Desktop UI Unit Tests

**File**: `tests/unit/desktop/test_components.ts`

```typescript
// Test coverage:
// 1. Component rendering
// 2. Props handling
// 3. Event handlers
// 4. State updates

Test Cases:
  ✓ AgentPanel renders with agent data
  ✓ AgentCard displays agent details
  ✓ CompressionStats shows correct values
  ✓ MetricsChart renders data visualization
  ✓ Loading state shows spinner
  ✓ Error state shows error message
  ✓ Click handlers trigger correct callbacks
  ✓ Props changes trigger re-render
```

---

## Section 3: Integration Testing Strategy

### 3.1 Engine ↔ Go API Bridge Tests

**Scenario**: Test that Go API correctly bridges HTTP requests to Engine RPC calls

```python
# tests/integration/test_engine_api_bridge.py

Test Flow:
  1. Start Engine (port 5000)
  2. Start Go API (port 12080)
  3. Send HTTP request to Go API
  4. Go API calls Engine RPC method
  5. Engine returns result
  6. Go API returns HTTP response
  7. Verify data transformation is lossless

Test Cases:
  ✓ agents.list HTTP → Engine RPC → HTTP response
  ✓ agents.metrics HTTP → Engine RPC → HTTP response
  ✓ compression.stats HTTP → Engine RPC → HTTP response
  ✓ Error propagation: Engine error → HTTP error
  ✓ Timeout handling: Engine timeout → HTTP 504
  ✓ Large response handling: Streaming if > 1MB
  ✓ Concurrent bridge calls: No request interference
  ✓ Auth token passed through Go API → Engine
```

### 3.2 RPC Methods Integration Tests

**Scenario**: Test all RPC methods working correctly together

```python
# tests/integration/test_rpc_methods.py

Test Workflow:
  1. List all agents (agents.list)
  2. Get individual agent metrics (agents.metrics) for each
  3. Get agent by codename (agents.get_by_codename)
  4. Get tier summary (agents.list_tiers)
  5. Get swarm status (agents.swarm_status)
  6. Start compression job (compression.start)
  7. Get compression stats (compression.stats)
  8. Track job completion

Expected Behavior:
  ✓ agents.list returns 40 agents with IDs
  ✓ agents.metrics for each agent returns valid metrics
  ✓ All 3 tiers returned by agents.list_tiers
  ✓ Swarm status shows all agents active
  ✓ Compression job can be tracked
  ✓ Stats update correctly as job progresses
```

### 3.3 Error Scenario Integration Tests

**Scenario**: Test system handles error cases across service boundaries

```python
# tests/integration/test_error_scenarios.py

Error Cases:
  ✓ Invalid RPC method → Go API returns 400
  ✓ Connection loss → Go API retry with backoff
  ✓ Timeout on Engine → Go API timeout handling
  ✓ Invalid JSON → Go API parsing error
  ✓ Missing required field → Go API validation
  ✓ Agent not found → Engine returns proper error
  ✓ Compression job failure → Stats reflect failure
  ✓ Concurrent errors → Isolation maintained
```

---

## Section 4: End-to-End Testing Strategy

### 4.1 UI Workflow Tests

**Scenario**: Test complete user workflows from Desktop UI through all layers

```typescript
// tests/e2e/test_ui_workflows.ts

Workflow 1: Agent Management Panel
  1. Open Agent Management panel
  2. View list of all 40 agents
  3. Click on individual agent
  4. View agent details and metrics
  5. Verify metrics data is real-time
  6. Filter agents by tier
  7. Verify filtered results

Expected Results:
  ✓ All 40 agents load immediately (< 2s)
  ✓ Agent details modal shows correct data
  ✓ Metrics are current and accurate
  ✓ Tier filtering works correctly
  ✓ No UI freezing or lag during data load

Workflow 2: Compression Monitor
  1. Open Compression Stats panel
  2. View current compression jobs
  3. Start new compression job
  4. Monitor job progress
  5. View completion status
  6. Review compression statistics

Expected Results:
  ✓ Current jobs display immediately
  ✓ Job start completes in < 1s
  ✓ Progress updates in real-time (< 1s intervals)
  ✓ Stats calculate correctly
  ✓ No data loss on refresh

Workflow 3: System Dashboard
  1. Open main system dashboard
  2. View agent swarm status
  3. View compression statistics
  4. Monitor real-time metrics
  5. Check system health

Expected Results:
  ✓ Dashboard loads in < 3s
  ✓ All components update simultaneously
  ✓ Real-time metrics poll interval < 5s
  ✓ CPU/memory metrics reflect actual usage
```

### 4.2 Cross-Service Integration Tests

```typescript
// tests/e2e/test_concurrent_ops.ts

Concurrent Operations:
  • 10 simultaneous agent metric requests
  • 3 compression jobs running in parallel
  • UI components all updating simultaneously
  • No request interference or data corruption
  • Proper request/response pairing

Expected Results:
  ✓ All requests complete within 5s
  ✓ No response mixing between requests
  ✓ Memory usage stays < 500MB
  ✓ No request timeouts (< 5% failure rate)
```

---

## Section 5: Performance Testing Strategy

### 5.1 Load Testing

**Tool**: Locust (Python-based)

```python
# tests/performance/test_load.py

Scenarios:
  1. Ramp-up: 0 → 100 users over 2 minutes
  2. Steady State: 100 users for 5 minutes
  3. Peak: 200 users for 2 minutes
  4. Cool-down: 200 → 0 users over 2 minutes

RPC Methods Under Load:
  • agents.list - 20% of requests
  • agents.metrics - 50% of requests
  • agents.get - 15% of requests
  • compression.stats - 15% of requests

Acceptance Criteria:
  ✓ p95 latency < 500ms
  ✓ p99 latency < 1000ms
  ✓ Success rate > 99%
  ✓ No memory leaks (steady heap)
  ✓ CPU utilization < 80%
```

### 5.2 Throughput Testing

```python
# tests/performance/test_rpc_throughput.py

Metrics:
  • RPC methods/second: Target 1000+ RPS
  • API endpoints/second: Target 500+ RPS
  • Response chunking: Test 10MB responses
  • Memory scaling: Monitor with 10k-100k agents

Thresholds:
  ✓ Engine maintains 1000+ RPS
  ✓ Go API maintains 500+ RPS
  ✓ Memory stable under sustained load
  ✓ No connection pool exhaustion
```

### 5.3 Baseline Establishment

```bash
# scripts/performance_baseline.sh

Establishes:
  • Current response time baseline (p50, p95, p99)
  • Current throughput baseline (RPS)
  • Memory usage baseline
  • CPU usage baseline

Output: benchmarks/baseline_2026_02_10.json

Used for: Regression detection in future tests
```

---

## Section 6: CI/CD Pipeline Strategy

### 6.1 GitHub Actions Workflows

**File**: `.github/workflows/test.yml`

```yaml
name: Unit & Integration Tests

on: [push, pull_request]

jobs:
  engine-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements-test.txt
      - run: pytest tests/unit/engine -v --cov
      - run: pytest tests/integration -v
      - upload coverage to codecov

  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
      - run: go test ./tests/unit/api -v
      - run: go test ./tests/integration -v

  ui-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npm run test:unit
      - run: npm run test:coverage
```

**File**: `.github/workflows/e2e.yml`

```yaml
name: End-to-End Tests

on: [push]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    services:
      engine:
        image: sigmavault-engine:latest
        ports: [5000]
      api:
        image: sigmavault-api:latest
        ports: [12080]

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npx cypress run --spec "tests/e2e/**"
      - upload: artifacts/e2e-results.html
```

**File**: `.github/workflows/release.yml`

```yaml
name: Release & Deploy

on: [release]

jobs:
  build-and-test:
    # All unit/integration tests pass

  package:
    # Create ISO, Docker images, release artifacts

  deploy:
    # Push to registry, update docs
```

### 6.2 CI/CD Metrics & Reporting

**Directory**: `.github/artifacts/`

Contains:

- Test results (JSON format)
- Coverage reports (HTML)
- Performance baseline comparisons
- Build artifacts checksums

**Reporting**:

- Pull requests: Pass/fail badges with coverage
- Dashboard: Real-time test metrics
- Alerts: Notify on failures/regressions

---

## Section 7: Test Execution Plan

### Phase 1: Foundation (1-1.5 hours)

1. ✅ Create test directory structure
2. ✅ Configure pytest & test fixtures
3. ✅ Set up test runners (Python, Go, TypeScript)
4. ✅ Create mock data fixtures

### Phase 2: Unit Tests (1.5-2 hours)

1. ✅ Engine RPC routing tests
2. ✅ Compression stats tests
3. ✅ Agent handler tests
4. ✅ Go API endpoint tests
5. ✅ Desktop UI component tests

### Phase 3: Integration Tests (1.5-2 hours)

1. ✅ Engine ↔ Go API bridge tests
2. ✅ RPC methods integration
3. ✅ Error scenario testing
4. ✅ Cross-service workflows

### Phase 4: E2E & Performance (1-1.5 hours)

1. ✅ UI workflow tests
2. ✅ Load testing scripts
3. ✅ Performance baseline
4. ✅ Regression detection

### Phase 5: CI/CD Setup (0.5-1 hour)

1. ✅ GitHub Actions workflows
2. ✅ Automated test triggering
3. ✅ Coverage reporting
4. ✅ Release pipeline

---

## Section 8: Quality Gates & Acceptance Criteria

### Pre-Merge Requirements

- [ ] All unit tests pass (100%)
- [ ] Integration tests pass (100%)
- [ ] Code coverage ≥ 80%
- [ ] No new lint warnings
- [ ] Performance within baseline ±10%

### Pre-Release Requirements

- [ ] E2E tests pass (100%)
- [ ] Load test passes (p95 < 500ms)
- [ ] No memory leaks detected
- [ ] Documentation complete
- [ ] All changes tracked in CHANGELOG

### Production Deployment

- [ ] All test suites green
- [ ] 2 independent approvals
- [ ] Performance validated
- [ ] Rollback plan documented
- [ ] Monitoring/alerts configured

---

## Section 9: Risk Mitigation

| Risk                    | Probability | Impact | Mitigation                                 |
| ----------------------- | ----------- | ------ | ------------------------------------------ |
| Test flakiness          | Medium      | High   | Use fixtures, isolated tests, retries      |
| Performance regression  | Medium      | High   | Continuous baseline monitoring             |
| CI/CD complexity        | Low         | Medium | Start simple, iterate                      |
| Coverage gaps           | Medium      | Medium | Regular coverage analysis                  |
| Test maintenance burden | High        | Low    | Automated refactoring, clear documentation |

---

## Section 10: Success Metrics

**By End of Phase 2.3 Testing**:

✓ **Coverage**: 80%+ overall code coverage  
✓ **Speed**: All tests complete in < 5 minutes  
✓ **Reliability**: 100% pass rate on main branch  
✓ **Performance**: Baseline established for regression detection  
✓ **Deployment**: Automated CI/CD pipeline operational

**Key Indicators**:

- 0 critical bugs in E2E tests (goal)
- Response time p95 < 500ms (target)
- Zero test timeouts in 100 runs (goal)
- 100% regression detection (target)

---

## Appendix A: Test Execution Commands

```bash
# Run all tests
./scripts/run_all_tests.sh

# Run specific test suite
pytest tests/unit/engine -v
go test ./tests/unit/api -v
npm run test:unit

# Generate coverage report
./scripts/coverage_report.sh

# Run performance tests
pytest tests/performance -v --benchmark

# Run E2E tests (requires running services)
npx cypress run
```

---

## Appendix B: Environment Setup

**Required for Testing**:

- Python 3.11+ with pytest, pytest-asyncio, pytest-cov
- Go 1.20+ with testify
- Node.js 18+ with Vitest, React Testing Library
- Docker (for E2E service orchestration)
- Cypress or Playwright (for UI automation)

---

**Document Status**: Ready for Implementation  
**Next Step**: Begin Phase 1 (Foundation) - Create test infrastructure
