# Phase 2.8 - Option C Action Plan

**Date**: 2025-01-16  
**Phase**: Extended Testing (Options A→B→C→D)  
**Option C**: "Real Compression Integration"  
**Status**: Ready to Begin

---

## Option C Overview

Option C implements real compression algorithm integration, moving from mock data to actual compression job execution and monitoring. This phase bridges the dashboard UI with the Python RPC engine's compression capabilities.

### Option C Scope

1. **Real Compression Engine**
   - Implement actual compression algorithm execution
   - Support multiple compression formats (gzip, zstd, brotli, etc.)
   - Track compression job progress in real-time
   - Calculate actual compression ratios and statistics

2. **Job Management System**
   - Queue management for compression jobs
   - Job lifecycle tracking (queued → running → completed)
   - Error handling and retry logic
   - Job persistence (so jobs survive app restart)

3. **Dashboard Integration**
   - Real data flowing through Compression page
   - Live job progress visualization
   - Statistics updating based on actual compression results
   - Historical job tracking

4. **Performance Optimization**
   - Sub-linear algorithms for job tracking
   - Efficient progress tracking without overhead
   - Batch processing for multiple jobs
   - Stream processing for large files

---

## Prerequisites Met ✅

All requirements for Option C are now in place:

| Requirement        | Status      | Evidence                                                |
| ------------------ | ----------- | ------------------------------------------------------- |
| API client methods | ✅ Complete | `get_compression_jobs()`, `get_compression_stats()`     |
| Go API endpoints   | ✅ Ready    | `/api/v1/compression/jobs`, `/api/v1/compression/stats` |
| Dashboard page     | ✅ Wired    | Compression page with job list + stats section          |
| RPC engine         | ✅ Running  | Python RPC on port 5000                                 |
| Infrastructure     | ✅ Verified | All 3 layers (UI, API, RPC) communicating               |

---

## Implementation Plan

### Phase 1: Compression Engine Enhancement (Python RPC)

**Goal**: Implement real compression logic in Python RPC engine

**Files to Modify**:

- `src/engined/engined/rpc/compression.py` — Add real compression methods
- `src/engined/engined/rpc/job_manager.py` — Create job tracking system

**Tasks**:

1. **Create Compression Job Model**

   ```python
   @dataclass
   class CompressionJob:
       id: str
       source: str
       destination: str
       algorithm: str  # gzip, zstd, brotli
       status: str  # queued, running, completed, failed
       progress: int  # 0-100
       bytes_processed: int
       bytes_total: int
       compression_ratio: float
       start_time: datetime
       end_time: Optional[datetime]
       error: Optional[str]
   ```

2. **Implement Compression Algorithm Wrapper**

   ```python
   async def compress_file(
       job_id: str,
       source_path: str,
       dest_path: str,
       algorithm: str = "zstd",
       compression_level: int = 9
   ) -> CompressionJob:
       # Read source file
       # Apply compression algorithm
       # Track progress every N bytes
       # Handle errors gracefully
       # Return job object with final stats
   ```

3. **Create Job Manager with Queue**

   ```python
   class CompressionJobManager:
       def enqueue_job(self, job_spec: dict) -> str
       async def process_queue(self)
       def get_job_status(self, job_id: str) -> CompressionJob
       def get_active_jobs(self) -> List[CompressionJob]
       def get_job_stats(self) -> dict
   ```

4. **Add RPC Methods**
   ```python
   # In rpc/compression.py
   async def SubmitCompressionJob(self, ctx, params: SubmitJobParams) -> CompressionJob
   async def ListCompressionJobs(self, ctx, params=None) -> List[CompressionJob]
   async def GetCompressionStats(self, ctx) -> CompressionStats
   async def CancelJob(self, ctx, job_id: str) -> bool
   async def DeleteJob(self, ctx, job_id: str) -> bool
   ```

**Success Criteria**:

- [ ] Compression algorithm implementation complete
- [ ] Job manager handles queue processing
- [ ] RPC methods callable from Go API
- [ ] Jobs persist across restarts
- [ ] Progress tracking works without overhead

---

### Phase 2: Go API Handler Enhancement

**Goal**: Wire Go handlers to real RPC compression methods

**Files to Modify**:

- `src/api/internal/handlers/compression.go` — Replace mock handlers

**Tasks**:

1. **Replace Mock GetCompressionStats Handler**

   ```go
   func (h *CompressionV2Handler) GetCompressionStats(c *fiber.Ctx) error {
       // Call real RPC method
       stats, err := h.rpcClient.GetCompressionStats(c.Context())
       if err != nil {
           // Log error, return 500
       }
       return c.JSON(stats)
   }
   ```

2. **Replace Mock ListCompressionJobs Handler**

   ```go
   func (h *CompressionV2Handler) ListCompressionJobs(c *fiber.Ctx) error {
       // Call real RPC method
       jobs, err := h.rpcClient.ListCompressionJobs(c.Context(), ...)
       if err != nil {
           // Log error, return 500
       }
       return c.JSON(fiber.Map{
           "jobs": jobs,
           "count": len(jobs),
       })
   }
   ```

3. **Add Compression Job Submission Handler**

   ```go
   func (h *CompressionV2Handler) SubmitCompressionJob(c *fiber.Ctx) error {
       // Parse request body
       // Validate parameters
       // Call RPC SubmitCompressionJob
       // Return job ID and initial status
   }
   ```

4. **Add Job Control Handlers**
   ```go
   func (h *CompressionV2Handler) CancelJob(c *fiber.Ctx) error { ... }
   func (h *CompressionV2Handler) DeleteJob(c *fiber.Ctx) error { ... }
   ```

**Success Criteria**:

- [ ] All handlers call real RPC methods
- [ ] Error handling consistent across handlers
- [ ] Job creation returns valid job ID
- [ ] Job cancellation works correctly

---

### Phase 3: Dashboard Page Integration

**Goal**: Connect Compression page to real job data

**Files to Modify**:

- `src/desktop-ui/ui/pages/compression.py` — Update to use real data

**Tasks**:

1. **Update Compression Page Data Binding**
   - Parse real job data from API
   - Display actual progress percentages
   - Show real compression ratios
   - Track actual speeds (bytes/sec)

2. **Add Real-Time Progress Updates**
   - Refresh job list every 1-2 seconds (instead of 10)
   - Show progress bars updating smoothly
   - Display ETA based on current speed
   - Handle job completion transitions

3. **Add Job Control UI**
   - Submit new compression job button
   - Cancel active job buttons
   - Delete completed job buttons
   - Confirmation dialogs for destructive operations

4. **Enhance Statistics Display**
   - Show aggregate statistics:
     - Total jobs processed
     - Average compression ratio
     - Total data compressed
     - Average compression speed

**Success Criteria**:

- [ ] Compression page shows real job data
- [ ] Progress bars update smoothly
- [ ] Jobs transition through all states
- [ ] User can submit new jobs
- [ ] Statistics reflect real compression data

---

### Phase 4: Testing & Validation

**Goal**: Comprehensive testing of real compression system

**Test Cases**:

1. **Unit Tests** (Python RPC)
   - [ ] Compression algorithm produces correct output
   - [ ] Job progress tracking is accurate
   - [ ] Queue manages jobs in order
   - [ ] Error handling works correctly

2. **Integration Tests**
   - [ ] RPC methods return data in correct format
   - [ ] Go handlers properly call RPC methods
   - [ ] API returns data matching expected schema
   - [ ] Database/persistence works

3. **UI Tests**
   - [ ] Compression page loads without errors
   - [ ] Job list displays all active jobs
   - [ ] Progress bars show correct percentages
   - [ ] Auto-refresh updates data correctly
   - [ ] Job submission form works
   - [ ] Cancel/delete buttons functional

4. **End-to-End Tests**
   - [ ] Submit compression job from UI
   - [ ] Watch progress update in real-time
   - [ ] Verify compressed file has correct stats
   - [ ] Cancel mid-job works cleanly
   - [ ] Delete completed job works

5. **Performance Tests**
   - [ ] Job tracking has <1% overhead
   - [ ] UI refresh doesn't cause delays
   - [ ] Large files compress without issues
   - [ ] Multiple concurrent jobs handled

**Success Criteria**:

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] All UI tests passing
- [ ] End-to-end workflow verified
- [ ] Performance metrics acceptable

---

## Implementation Sequence

```
1. Python RPC Compression Engine
   ↓
2. Go API Handlers (wired to real RPC)
   ↓
3. Dashboard Compression Page (consuming real data)
   ↓
4. Testing & Validation
   ↓
   → Option C Complete → Option D Ready
```

---

## Key Decisions

### Compression Algorithm Selection

**Primary**: ZStandard (zstd)

- Modern, fast, good compression ratio
- Widely supported
- Tunable compression level

**Secondary**: GZIP

- Compatibility, widely available
- Slower but reliable

**Tertiary**: Brotli

- Excellent ratio for text
- Slower compression speed

### Job Persistence Strategy

**Approach**: SQLite database for job history

- Lightweight, no external dependencies
- Survives app restart
- Easy querying for statistics

**Schema**:

```sql
CREATE TABLE compression_jobs (
    id TEXT PRIMARY KEY,
    source TEXT,
    destination TEXT,
    algorithm TEXT,
    status TEXT,
    progress INT,
    bytes_processed INT,
    bytes_total INT,
    compression_ratio FLOAT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    error TEXT
);
```

### Progress Tracking Method

**Approach**: Callback-based progress reporting

- Read chunks from source file
- Report bytes processed every chunk
- Calculate percentage and ETA
- Update RPC job object
- Minimal overhead (sub-linear)

---

## Risk Mitigation

| Risk                           | Impact | Mitigation                             |
| ------------------------------ | ------ | -------------------------------------- |
| Slow compression blocking UI   | High   | Async job queue, background processing |
| Job loss on restart            | Medium | SQLite persistence layer               |
| Memory issues with large files | Medium | Streaming/chunked processing           |
| Compression algorithm bugs     | High   | Thorough testing, error handling       |
| RPC method unavailable         | Medium | Graceful degradation, error messages   |

---

## Success Metrics

| Metric                    | Target         | Notes                                     |
| ------------------------- | -------------- | ----------------------------------------- |
| Compression speed         | >50 MB/s       | Depends on algorithm + file type          |
| Job tracking overhead     | <1% CPU        | Background processing should be efficient |
| UI responsiveness         | <100ms latency | Auto-refresh shouldn't lag                |
| Test coverage             | >90%           | All compression paths tested              |
| Mean time to compress 1GB | <30s           | With zstd level 9                         |

---

## Timeline Estimate

| Phase     | Tasks                         | Estimated Time    |
| --------- | ----------------------------- | ----------------- |
| 1         | Python RPC compression engine | 2-3 hours         |
| 2         | Go API handlers               | 30 minutes        |
| 3         | Dashboard page updates        | 1-2 hours         |
| 4         | Testing & validation          | 2-3 hours         |
| **Total** |                               | **5.5-8.5 hours** |

---

## Deliverables

1. ✅ Real compression algorithm implementation
2. ✅ Job queue management system
3. ✅ Go API handlers connected to real compression
4. ✅ Dashboard Compression page with real data
5. ✅ Comprehensive test suite
6. ✅ Performance benchmarks
7. ✅ Option C completion document
8. ✅ Option C git commit

---

## Go/No-Go Criteria for Option C

**PROCEED if**:

- [x] All Option B infrastructure in place
- [x] API client methods available
- [x] Go handlers can call RPC methods
- [x] Python RPC engine running
- [x] Dashboard page architecture sound

**WAIT if**:

- [ ] API infrastructure unstable
- [ ] RPC engine having issues
- [ ] Dashboard page scaffolding incomplete

**Current Status**: ✅ **GO FOR OPTION C**

All prerequisites met. Ready to proceed with real compression integration.

---

**Next Action**: Begin Phase 1 (Python RPC Compression Engine)
