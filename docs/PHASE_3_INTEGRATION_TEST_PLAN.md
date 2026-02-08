# Phase 3 Integration Test Plan

**Objective**: Verify that job registry data flows correctly from Python → RPC → Go → HTTP

---

## 🧪 Test Strategy

### Architecture Under Test
```
Dashboard Client
    ↓ GET /api/v1/compression/jobs
Go HTTP Handler (ListCompressionJobs)
    ↓ RPC Call: compression.jobs.list
Go RPC Client (via HTTP POST)
    ↓ JSON-RPC 2.0 to localhost:5000
Python RPC Handler
    ↓ Query _compression_jobs registry
Return job data
    ↓
HTTP 200 JSON to dashboard
```

---

## 📝 Test Cases

### Test 1: Python RPC Handler Direct Call

**Objective**: Verify Python handlers work correctly

**Setup**:
1. Start Python engine: `python -m engined.main`
   - Expected: Listens on localhost:5000/rpc
   - Verify: `curl http://localhost:5000/` returns 200

2. Populate test jobs (manual or via script)
   - Note: Jobs added when compression completes
   - Or manually add to _compression_jobs dict for testing

**Test 1.1: List Empty Registry**
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

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "jobs": [],
    "total": 0
  },
  "id": 1
}
```

**Test 1.2: Get Non-Existent Job**
```bash
curl -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "compression.jobs.get",
    "params": {"job_id": "nonexistent"},
    "id": 2
  }'
```

**Expected Response** (Error):
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "...",
    "data": "Compression job nonexistent not found"
  },
  "id": 2
}
```

---

### Test 2: Compress Data and Verify Job Registry

**Objective**: Complete a compression, verify job appears in registry

**Setup**:
1. Ensure Python engine running
2. Compress test data via existing endpoint

**Test 2.1: Compress Data**
```bash
curl -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "compression.compress.data",
    "params": {
      "data": "'$(echo -n 'Hello, World! This is a test string for compression.' | base64)'",
      "level": "balanced"
    },
    "id": 3
  }'
```

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "job_id": "abc123...",
    "success": true,
    "original_size": 50,
    "compressed_size": 45,
    "compression_ratio": 0.90,
    "elapsed_seconds": 0.001,
    "method": "...",
    "data_type": "text",
    "checksum": "...",
    "data": "..."
  },
  "id": 3
}
```

**Capture**: Save `job_id` from response (e.g., `abc123`)

**Test 2.2: Query Registry for Job**
```bash
curl -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "compression.jobs.list",
    "params": {"limit": 10},
    "id": 4
  }'
```

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "jobs": [
      {
        "job_id": "abc123...",
        "status": "completed",
        "original_size": 50,
        "compressed_size": 45,
        "compression_ratio": 0.90,
        "elapsed_seconds": 0.001,
        "method": "...",
        "data_type": "text",
        "created_at": "2025-01-13T10:30:00Z",
        "error": ""
      }
    ],
    "total": 1
  },
  "id": 4
}
```

**Test 2.3: Get Specific Job**
```bash
curl -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "compression.jobs.get",
    "params": {"job_id": "abc123..."},
    "id": 5
  }'
```

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "job_id": "abc123...",
    "status": "completed",
    "original_size": 50,
    "compressed_size": 45,
    "compression_ratio": 0.90,
    "elapsed_seconds": 0.001,
    "method": "...",
    "data_type": "text",
    "created_at": "2025-01-13T10:30:00Z",
    "error": ""
  },
  "id": 5
}
```

---

### Test 3: Go RPC Client Methods

**Objective**: Verify Go correctly calls Python RPC handlers

**Setup**:
1. Ensure Python engine running on :5000
2. Build Go API: `cd src/api && go build -o api.exe`
3. Start Go API: `./api.exe` (should connect to RPC on :5000)

**Test 3.1: Test ListCompressionJobs Method**
```go
// In Go code / test
client := rpc.NewClient("http://localhost:5000/rpc")

result, err := client.ListCompressionJobs(ctx, &rpc.CompressionJobsListParams{
    Status: "",
    Limit: 10,
})

// Verify
assert.NoError(err)
assert.NotNil(result)
assert.Greater(len(result.Jobs), 0)  // Should have at least 1 job from Test 2
```

**Test 3.2: Test GetCompressionJob Method**
```go
client := rpc.NewClient("http://localhost:5000/rpc")

job, err := client.GetCompressionJob(ctx, "abc123...")

// Verify
assert.NoError(err)
assert.NotNil(job)
assert.Equal("abc123...", job.JobID)
assert.Equal("completed", job.Status)
```

---

### Test 4: Go HTTP Handlers

**Objective**: Verify HTTP API returns correct data

**Setup**:
1. Ensure Python engine with populated jobs
2. Ensure Go API running on :12080

**Test 4.1: List Jobs Endpoint**
```bash
curl http://localhost:12080/api/v1/compression/jobs?limit=10
```

**Expected Response** (200 OK):
```json
{
  "jobs": [
    {
      "job_id": "abc123...",
      "status": "completed",
      "original_size": 50,
      "compressed_size": 45,
      "compression_ratio": 0.90,
      "elapsed_seconds": 0.001,
      "method": "zlib",
      "data_type": "text",
      "created_at": "2025-01-13T10:30:00Z",
      "error": ""
    }
  ],
  "total": 1
}
```

**Test 4.2: List with Status Filter**
```bash
curl http://localhost:12080/api/v1/compression/jobs?status=completed&limit=10
```

**Expected Response** (200 OK):
- Same format as 4.1
- Only jobs with status="completed"

**Test 4.3: Get Specific Job Endpoint**
```bash
curl http://localhost:12080/api/v1/compression/jobs/abc123...
```

**Expected Response** (200 OK):
```json
{
  "job_id": "abc123...",
  "status": "completed",
  "original_size": 50,
  "compressed_size": 45,
  "compression_ratio": 0.90,
  "elapsed_seconds": 0.001,
  "method": "zlib",
  "data_type": "text",
  "created_at": "2025-01-13T10:30:00Z",
  "error": ""
}
```

**Test 4.4: Get Non-Existent Job**
```bash
curl http://localhost:12080/api/v1/compression/jobs/nonexistent &
```

**Expected Response** (404 Not Found):
```json
{
  "error": "Job not found"
}
```

**Test 4.5: Empty Query Parameters**
```bash
curl http://localhost:12080/api/v1/compression/jobs
```

**Expected Response** (200 OK):
- Default limit applied (100)
- All jobs returned (no filter)

---

### Test 5: Multiple Jobs Scenario

**Objective**: Verify listing, filtering, and sorting with multiple jobs

**Setup**:
1. Create 5 test jobs via direct Python calls or compress multiple files
2. Set different statuses for testing (some completed, some failed if possible)

**Test 5.1: List All**
```bash
curl http://localhost:12080/api/v1/compression/jobs?limit=200
```

**Expected**:
- Returns all 5 jobs
- Jobs sorted by created_at descending (newest first)

**Test 5.2: Filter by Status**
```bash
curl http://localhost:12080/api/v1/compression/jobs?status=completed&limit=100
```

**Expected**:
- Only completed jobs returned
- Still sorted by created_at descending

**Test 5.3: Limit Parameter**
```bash
curl http://localhost:12080/api/v1/compression/jobs?limit=2
```

**Expected**:
- Only 2 jobs returned
- Most recent 2

**Test 5.4: Pagination Simulation**
```bash
# First page
curl http://localhost:12080/api/v1/compression/jobs?limit=2

# Get next page manually by job_id
# (Advanced: might need to implement offset/cursor pagination)
```

---

## 🔍 Verification Checklist

### Python RPC Layer
- [ ] RPC service responds on :5000
- [ ] compression.jobs.list handler returns correct format
- [ ] compression.jobs.get handler returns single job
- [ ] Jobs stored in _compression_jobs after compression
- [ ] Status filter works correctly
- [ ] Limit parameter respected
- [ ] Sorting by created_at descending works

### Go RPC Client
- [ ] ListCompressionJobs method makes correct RPC call
- [ ] GetCompressionJob method makes correct RPC call
- [ ] Type marshaling/unmarshaling correct
- [ ] Error handling for RPC failures
- [ ] Default params applied when needed

### Go HTTP Handlers
- [ ] ListCompressionJobs handler parses query params
- [ ] GetCompressionJob handler extracts path param
- [ ] Response JSON matches expected format
- [ ] HTTP 200 for success
- [ ] HTTP 404 for not found
- [ ] HTTP 400 for invalid params
- [ ] Mock fallback works when RPC unavailable

### HTTP Routes
- [ ] Routes registered correctly
- [ ] URL patterns match handler signatures
- [ ] HTTP methods correct (GET for both)

---

## 📊 Test Results Template

```
Test Name: [Test Case]
Status: [PASS/FAIL/SKIP]
Duration: [time]
Expected: [expected result]
Actual: [actual result]
Notes: [any observations]
```

---

## 🚀 Running the Full Integration Test

**Quick Start Script** (bash):
```bash
#!/bin/bash
set -e

echo "Starting Python Engine..."
cd src/engined
python -m engined.main &
PYTHON_PID=$!
sleep 2

echo "Building Go API..."
cd ../../src/api
go build -o api.exe

echo "Starting Go API..."
./api.exe &
GO_PID=$!
sleep 2

echo "Running Test 2.1: Compress Data..."
COMPRESS_RESPONSE=$(curl -s -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "compression.compress.data",
    "params": {
      "data": "'$(echo -n 'Test string' | base64)'",
      "level": "balanced"
    },
    "id": 1
  }')

JOB_ID=$(echo $COMPRESS_RESPONSE | jq -r '.result.job_id')
echo "Created job: $JOB_ID"

echo "Running Test 4.1: List Jobs via HTTP..."
curl -s http://localhost:12080/api/v1/compression/jobs?limit=10 | jq '.'

echo "Running Test 4.3: Get Specific Job..."
curl -s http://localhost:12080/api/v1/compression/jobs/$JOB_ID | jq '.'

echo "Cleaning up..."
kill $PYTHON_PID $GO_PID

echo "✅ Integration tests complete"
```

---

## ✅ Success Criteria

All tests pass when:
1. ✅ Python RPC handlers respond correctly
2. ✅ Go RPC client methods work
3. ✅ Go HTTP handlers return data
4. ✅ All HTTP endpoints accessible
5. ✅ Data flows correctly through all layers
6. ✅ Error cases handled properly
7. ✅ Status codes correct
8. ✅ JSON format matches spec

---

## 📝 Next Steps After Testing

If all tests pass:
1. Create dashboard UI to consume endpoints
2. Add real-time WebSocket updates
3. Implement caching if needed
4. Add performance optimizations
5. Full system integration testing

If tests fail:
1. Identify which layer has problem
2. Debug specific handler/method
3. Fix and re-test
4. Document findings in Phase 3 report
