# Phase 3: Dashboard Integration - Action Plan

**Status**: 🚀 IN PROGRESS  
**Date Started**: February 7, 2026  
**Estimated Duration**: 2-3 hours  
**Objective**: Enable real-time compression job tracking and visualization in the dashboard

---

## 📋 Phase 3 Overview

Phase 3 focuses on integrating the compression backend (Python RPC engine) with the dashboard UI to display real-time job status, metrics, and history. This phase builds on the completed Phase 2 (handler integration) and Phase 1 (verification).

### Key Tasks

1. ✅ **COMPLETED**: Add Go RPC methods for job listing (compression_v2.go)
2. ✅ **COMPLETED**: Add HTTP handlers for jobs endpoints (compression.go)
3. ✅ **COMPLETED**: Register routes (routes.go)
4. ⏳ **IN PROGRESS**: Verify Python API provides required data
5. **PENDING**: Create dashboard page to consume jobs API
6. **PENDING**: Implement real-time updates (WebSocket)
7. **PENDING**: Add job history and performance metrics
8. **PENDING**: Comprehensive testing

---

## 🏗️ Architecture

### Data Flow (Phase 3)

```
Dashboard UI (React/HTM)
    ↓ [GET /api/v1/compression/jobs]
Go HTTP Handler (ListCompressionJobs)
    ↓ [RPC Call: compression.jobs.list]
Go RPC Client (compression_v2.go)
    ↓ [JSON-RPC over HTTP POST to :5000]
Python RPC Engine
    ↓
Python Handler (handle_compression_jobs_list)
    ↓ [Query _compression_jobs registry]
_compression_jobs: Dict[job_id -> job_data]
    ↓ [Return JSON array of jobs]
Dashboard displays:
  - Job List (table/cards)
  - Job Details (modal/sidebar)
  - Real-time Progress (WebSocket later)
  - Metrics & Charts
```

### New API Endpoints (Phase 3)

**Endpoint 1: List All Compression Jobs**

```
GET /api/v1/compression/jobs?status=completed&limit=100

Request Query Parameters:
- status (optional): Filter by status (completed, failed, running, queued)
- limit (optional): Max jobs to return (default 100, max 1000)

Response: 200 OK
{
  "jobs": [
    {
      "job_id": "uuid",
      "status": "completed",
      "original_size": 1048576,
      "compressed_size": 314572,
      "compression_ratio": 0.30,
      "elapsed_seconds": 0.125,
      "method": "zlib",
      "data_type": "text",
      "created_at": "2025-01-13T10:25:00Z",
      "error": ""
    },
    ...
  ],
  "total": 42
}
```

**Endpoint 2: Get Specific Job Details**

```
GET /api/v1/compression/jobs/{job_id}

Response: 200 OK
{
  "job_id": "uuid",
  "status": "completed",
  "original_size": 1048576,
  "compressed_size": 314572,
  "compression_ratio": 0.30,
  "elapsed_seconds": 0.125,
  "method": "zlib",
  "data_type": "text",
  "created_at": "2025-01-13T10:25:00Z",
  "error": ""
}

Response: 404 Not Found (if job not found)
{
  "error": "Job not found"
}
```

---

## ✅ Completed in Phase 3

### 1. Go RPC Client Methods (compression_v2.go)

Added three new types and two methods:

**CompressionJob Struct** (Line 310-320):

- Represents a job in the registry
- Fields: job_id, status, original_size, compressed_size, compression_ratio,
  elapsed_seconds, method, data_type, created_at, error

**CompressionJobsListParams Struct** (Line 322-326):

- Query parameters: status (optional), limit (optional)

**CompressionJobsListResult Struct** (Line 328-332):

- Result container: jobs array, total count

**ListCompressionJobs Method** (Line 334-344):

- Calls RPC: "compression.jobs.list"
- Takes optional params (status filter, limit)
- Returns list of jobs from Python registry

**GetCompressionJob Method** (Line 346-352):

- Calls RPC: "compression.jobs.get"
- Takes job_id parameter
- Returns single job details

### 2. HTTP Handler Methods (compression.go)

Added two new handlers:

**ListCompressionJobsRequest Struct** (Line 631):

- Query params: status (filter), limit (max results)

**ListCompressionJobs Handler** (Line 633-681):

- Endpoint: GET /api/v1/compression/jobs?status=completed&limit=100
- Validates query parameters (caps limit at 1000)
- Calls RPC client method if available
- Returns mock data as fallback for development
- Handles RPC unavailability gracefully

**GetCompressionJob Handler** (Line 683-719):

- Endpoint: GET /api/v1/compression/jobs/:job_id
- Validates job_id parameter
- Calls RPC client method if available
- Returns 404 if job not found
- Provides mock data fallback

### 3. API Routes Registration (routes.go)

Added two routes (Line 132-134):

```go
// Phase 3: Jobs endpoints for dashboard integration
compression.Get("/jobs", compressionV2Handler.ListCompressionJobs)
compression.Get("/jobs/:job_id", compressionV2Handler.GetCompressionJob)
```

---

## 🔄 Current Status Verification

### What's Working Now

- ✅ Go RPC client methods (compression_v2.go)
- ✅ HTTP handlers (compression.go)
- ✅ Routes registered (routes.go)
- ✅ Fallback mock data for development
- ✅ Error handling and validations

### What Needs Testing

- ⏳ RPC calls to Python engine (integration test needed)
- ⏳ Real job data display
- ⏳ Dashboard UI consumption of endpoints
- ⏳ Real-time updates via WebSocket

---

## 📝 Next Steps in Phase 3

### Task 1: Verify Python RPC Handler

**Objective**: Confirm Python engine responds correctly

**Steps**:

1. Start Python RPC engine: `python -m engined.main` (port 5000)
2. Test via curl:
   ```bash
   curl -X POST http://localhost:5000/rpc \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "method": "compression.jobs.list",
       "params": {"limit": 10},
       "id": 1
     }'
   ```
3. Verify response structure matches Go structs

**Expected Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "jobs": [...],
    "total": 0
  },
  "id": 1
}
```

### Task 2: Start Go API Server

**Objective**: Run API with Phase 3 code

**Steps**:

1. Build: `cd src/api && go build -o api.exe`
2. Start: `./api.exe` or `go run main.go`
3. Expected: API starts on port 12080, connects to RPC engine on port 5000

### Task 3: Test Endpoints

**Objective**: Verify endpoints work end-to-end

**Testing Script**:

```bash
# Test 1: List jobs (should return empty or mock data)
curl http://localhost:12080/api/v1/compression/jobs?limit=5

# Test 2: Get specific job (should return mock data)
curl http://localhost:12080/api/v1/compression/jobs/test-job-id

# Test 3: Filter by status
curl http://localhost:12080/api/v1/compression/jobs?status=completed&limit=10
```

### Task 4: Dashboard Integration (Next Phase Section)

**Objective**: Create/update UI to display real data

**Files to Update**:

- `src/desktop-ui/views/compression.py` (GTK4 UI)
- or create new web dashboard in `src/webui/`

---

## 🎯 Implementation Checklist for Remaining Tasks

### Task: Verify Python Integration (Immediate Next Step)

- [ ] Confirm Python RPC handlers work
- [ ] Test job registry population
- [ ] Verify filtering works (status, limit)
- [ ] Check error handling

### Task: Dashboard Page (After verification)

- [ ] Create/update compression dashboard view
- [ ] Add job list display (table or cards)
- [ ] Implement job details modal/sidebar
- [ ] Add real-time refresh (polling initially, WebSocket later)

### Task: Performance Metrics

- [ ] Compression ratio chart
- [ ] Speed metrics display
- [ ] Storage saved calculation
- [ ] Time series analysis

### Task: Real-Time Updates

- [ ] WebSocket connection setup
- [ ] Live progress updates
- [ ] Job status notifications
- [ ] Rate limiting for updates

---

## 📊 File Changes Summary

| File              | Changes               | Lines Added | Status      |
| ----------------- | --------------------- | ----------- | ----------- |
| compression_v2.go | Added RPC job methods | ~45         | ✅ Complete |
| compression.go    | Added HTTP handlers   | ~90         | ✅ Complete |
| routes.go         | Registered routes     | 2           | ✅ Complete |
| Python rpc.py     | No changes needed     | —           | ✅ Ready    |

**Total Changes**: ~145 lines of new code  
**Compilation Status**: ✅ Go fmt verified (pending full build test)

---

## 🧪 Quality Assurance

### Code Review Checklist

- ✅ Go syntax valid (go fmt verified)
- ✅ Handler signatures match routes
- ✅ RPC parameters align with Python handlers
- ✅ Response struct fields match expected JSON
- ✅ Error handling implemented
- ✅ Mock fallback data for development

### Testing Checklist (To Be Done)

- [ ] RPC calls TO Python engine
- [ ] RPC calls FROM Dashboard UI
- [ ] Real job data population
- [ ] Error scenarios (no engine, missing job)
- [ ] Rate limiting (if needed)
- [ ] WebSocket integration

---

## 🚦 Phase 3 Status Summary

**Current Progress**: ~30% (Infrastructure Complete, Testing & UI Pending)

**What's Done**:
✅ Go RPC client methods  
✅ HTTP handlers  
✅ Route registration  
✅ Mock fallback data  
✅ Error handling

**What's Remaining**:
⏳ Integration testing (Py ↔ Go ↔ UI)  
⏳ Dashboard UI implementation  
⏳ Real-time updates (WebSocket)  
⏳ Performance metrics/charts  
⏳ End-to-end testing

**Blocking Issues**: None

**Critical Path**:

1. Verify Python handlers work → 5 mins
2. Test Go endpoints → 10 mins
3. Update dashboard UI → 45 mins
4. Real-time integration → 30 mins

---

## 🔗 Related Documents

- [Phase 2 Completion Report](PHASE_2.8_OPTION_C_PHASE2_HANDLER_INTEGRATION_REPORT.md)
- [Phase 1 Verification Report](PHASE_2.8_OPTION_C_PHASE1_VERIFICATION_REPORT.md)
- [Master Action Plan](NEXT_STEPS_MASTER_ACTION_PLAN_v4.md)

---

## 📌 Next Decision Point

After completing the above checklist:

**Option A** (Recommended): Proceed to WebSocket implementation for real-time updates  
**Option B**: Focus on dashboard UI first, then add real-time later  
**Option C**: Complete full test suite before UI work

Current Recommendation: **Option A** - Real-time capability is expected by modern dashboards
