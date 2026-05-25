"""
Unit Tests: Compression Stats Tracking

Tests the compression.stats RPC method and underlying job tracking
mechanism that maintains statistics about completed, in-flight, and
failed compression operations.

Scope:
  ✓ Job tracking and lifecycle
  ✓ Stats calculation (totals, averages, ratios)
  ✓ Concurrent job handling
  ✓ Large dataset performance
  ✓ Error scenarios and edge cases
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def compression_job_new() -> Dict[str, Any]:
    """Fresh compression job."""
    return {
        "job_id": "job-0001",
        "source_size_bytes": 1_000_000,
        "target_size_bytes": 100_000,
        "status": "completed",
        "progress_percent": 100,
        "compression_ratio": 0.10,
        "duration_seconds": 30,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": (datetime.utcnow() + timedelta(seconds=30)).isoformat()
    }


@pytest.fixture
def compression_job_in_progress() -> Dict[str, Any]:
    """In-progress compression job."""
    return {
        "job_id": "job-0002",
        "source_size_bytes": 5_000_000,
        "target_size_bytes": None,
        "status": "running",
        "progress_percent": 45,
        "compression_ratio": None,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": (datetime.utcnow() - timedelta(seconds=15)).isoformat(),
        "estimated_completion_ms": 5000
    }


@pytest.fixture
def compression_job_failed() -> Dict[str, Any]:
    """Failed compression job."""
    return {
        "job_id": "job-0003",
        "source_size_bytes": 500_000,
        "status": "failed",
        "progress_percent": 35,
        "error": "Compression codec not supported",
        "created_at": datetime.utcnow().isoformat(),
        "failed_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def compression_stats_tracker():
    """Create mock compression stats tracker."""
    
    class CompressionStatsTracker:
        def __init__(self):
            self.jobs: Dict[str, Dict] = {}
            self.completed_jobs = []
            self.failed_jobs = []
            self.running_jobs = []
        
        async def add_job(self, job: Dict) -> bool:
            """Add job and track it."""
            job_id = job.get("job_id")
            if not job_id:
                raise ValueError("job_id is required")
            
            if job_id in self.jobs:
                raise ValueError(f"Job {job_id} already exists")
            
            self.jobs[job_id] = job
            
            if job.get("status") == "completed":
                self.completed_jobs.append(job_id)
            elif job.get("status") == "running":
                self.running_jobs.append(job_id)
            elif job.get("status") == "failed":
                self.failed_jobs.append(job_id)
            
            return True
        
        async def update_job(self, job_id: str, updates: Dict) -> bool:
            """Update job status and metrics."""
            if job_id not in self.jobs:
                raise ValueError(f"Job {job_id} not found")
            
            self.jobs[job_id].update(updates)
            
            # Update tracking lists
            status = updates.get("status")
            if status == "completed" and job_id not in self.completed_jobs:
                self.completed_jobs.append(job_id)
                if job_id in self.running_jobs:
                    self.running_jobs.remove(job_id)
            elif status == "failed" and job_id not in self.failed_jobs:
                self.failed_jobs.append(job_id)
                if job_id in self.running_jobs:
                    self.running_jobs.remove(job_id)
            
            return True
        
        async def get_job(self, job_id: str) -> Dict:
            """Get job by ID."""
            if job_id not in self.jobs:
                raise ValueError(f"Job {job_id} not found")
            return self.jobs[job_id]
        
        async def get_stats(self) -> Dict[str, Any]:
            """Calculate and return compression statistics."""
            
            total_source_bytes = 0
            total_target_bytes = 0
            total_duration_seconds = 0
            completed_count = len(self.completed_jobs)
            running_count = len(self.running_jobs)
            failed_count = len(self.failed_jobs)
            
            # Calculate completed stats
            for job_id in self.completed_jobs:
                job = self.jobs[job_id]
                total_source_bytes += job.get("source_size_bytes", 0)
                total_target_bytes += job.get("target_size_bytes", 0)
                total_duration_seconds += job.get("duration_seconds", 0)
            
            # Calculate average compression ratio
            avg_compression_ratio = 0.0
            if completed_count > 0 and total_source_bytes > 0:
                avg_compression_ratio = total_target_bytes / total_source_bytes
            
            # Calculate total compression
            total_compression_ratio = (
                (total_source_bytes - total_target_bytes) / total_source_bytes
                if total_source_bytes > 0
                else 0
            )
            
            # Calculate average duration
            avg_duration_seconds = (
                total_duration_seconds / completed_count
                if completed_count > 0
                else 0
            )
            
            return {
                "completed_jobs": completed_count,
                "running_jobs": running_count,
                "failed_jobs": failed_count,
                "total_source_bytes": total_source_bytes,
                "total_target_bytes": total_target_bytes,
                "avg_compression_ratio": round(avg_compression_ratio, 4),
                "total_compression_ratio": round(total_compression_ratio, 4),
                "avg_duration_seconds": round(avg_duration_seconds, 2),
                "total_bytes_saved": total_source_bytes - total_target_bytes,
                "space_efficiency_percent": round(total_compression_ratio * 100, 2)
            }
    
    return CompressionStatsTracker()


# ============================================================================
# TEST CASES: Job Tracking
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_completed_job(compression_stats_tracker, compression_job_new):
    """Test adding completed compression job."""
    result = await compression_stats_tracker.add_job(compression_job_new)
    
    assert result is True
    assert "job-0001" in compression_stats_tracker.jobs
    assert "job-0001" in compression_stats_tracker.completed_jobs
    assert len(compression_stats_tracker.completed_jobs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_running_job(compression_stats_tracker, compression_job_in_progress):
    """Test adding in-progress compression job."""
    result = await compression_stats_tracker.add_job(compression_job_in_progress)
    
    assert result is True
    assert "job-0002" in compression_stats_tracker.jobs
    assert "job-0002" in compression_stats_tracker.running_jobs
    assert len(compression_stats_tracker.running_jobs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_failed_job(compression_stats_tracker, compression_job_failed):
    """Test adding failed compression job."""
    result = await compression_stats_tracker.add_job(compression_job_failed)
    
    assert result is True
    assert "job-0003" in compression_stats_tracker.jobs
    assert "job-0003" in compression_stats_tracker.failed_jobs
    assert len(compression_stats_tracker.failed_jobs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_by_id(compression_stats_tracker, compression_job_new):
    """Test retrieving job by ID."""
    await compression_stats_tracker.add_job(compression_job_new)
    
    retrieved = await compression_stats_tracker.get_job("job-0001")
    
    assert retrieved["job_id"] == "job-0001"
    assert retrieved["source_size_bytes"] == 1_000_000
    assert retrieved["compression_ratio"] == 0.10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_nonexistent_job(compression_stats_tracker):
    """Test retrieving non-existent job raises error."""
    with pytest.raises(ValueError, match="Job .* not found"):
        await compression_stats_tracker.get_job("job-nonexistent")


# ============================================================================
# TEST CASES: Error Scenarios
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_job_missing_id(compression_stats_tracker, compression_job_new):
    """Test adding job without job_id raises error."""
    job = compression_job_new.copy()
    del job["job_id"]
    
    with pytest.raises(ValueError, match="job_id is required"):
        await compression_stats_tracker.add_job(job)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_duplicate_job(compression_stats_tracker, compression_job_new):
    """Test adding duplicate job ID raises error."""
    await compression_stats_tracker.add_job(compression_job_new)
    
    # Try to add same job again
    with pytest.raises(ValueError, match="already exists"):
        await compression_stats_tracker.add_job(compression_job_new)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_nonexistent_job(compression_stats_tracker):
    """Test updating non-existent job raises error."""
    with pytest.raises(ValueError, match="Job .* not found"):
        await compression_stats_tracker.update_job("job-none", {"status": "completed"})


# ============================================================================
# TEST CASES: Job State Transitions
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_transition_running_to_completed(
    compression_stats_tracker,
    compression_job_in_progress
):
    """Test transitioning job from running to completed."""
    await compression_stats_tracker.add_job(compression_job_in_progress)
    
    # Verify initial state
    assert "job-0002" in compression_stats_tracker.running_jobs
    assert "job-0002" not in compression_stats_tracker.completed_jobs
    
    # Transition to complete
    await compression_stats_tracker.update_job("job-0002", {
        "status": "completed",
        "progress_percent": 100,
        "target_size_bytes": 1_250_000,
        "compression_ratio": 0.25,
        "duration_seconds": 45
    })
    
    # Verify new state
    assert "job-0002" not in compression_stats_tracker.running_jobs
    assert "job-0002" in compression_stats_tracker.completed_jobs
    job = await compression_stats_tracker.get_job("job-0002")
    assert job["status"] == "completed"
    assert job["progress_percent"] == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transition_running_to_failed(compression_stats_tracker, compression_job_in_progress):
    """Test transitioning job from running to failed."""
    await compression_stats_tracker.add_job(compression_job_in_progress)
    
    await compression_stats_tracker.update_job("job-0002", {
        "status": "failed",
        "error": "Out of memory"
    })
    
    assert "job-0002" not in compression_stats_tracker.running_jobs
    assert "job-0002" in compression_stats_tracker.failed_jobs


# ============================================================================
# TEST CASES: Statistics Calculation
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_stats_single_completed_job(
    compression_stats_tracker,
    compression_job_new
):
    """Test stats calculation with single completed job."""
    await compression_stats_tracker.add_job(compression_job_new)
    
    stats = await compression_stats_tracker.get_stats()
    
    assert stats["completed_jobs"] == 1
    assert stats["running_jobs"] == 0
    assert stats["failed_jobs"] == 0
    assert stats["total_source_bytes"] == 1_000_000
    assert stats["total_target_bytes"] == 100_000
    assert stats["avg_compression_ratio"] == 0.10
    assert stats["total_compression_ratio"] == 0.90
    assert stats["total_bytes_saved"] == 900_000
    assert stats["space_efficiency_percent"] == 90.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stats_multiple_jobs(compression_stats_tracker):
    """Test stats calculation with multiple jobs."""
    
    # Add 3 completed jobs with different sizes
    job1 = {
        "job_id": "job-1",
        "source_size_bytes": 1_000_000,
        "target_size_bytes": 100_000,
        "status": "completed",
        "duration_seconds": 30,
        "compression_ratio": 0.10
    }
    job2 = {
        "job_id": "job-2",
        "source_size_bytes": 2_000_000,
        "target_size_bytes": 500_000,
        "status": "completed",
        "duration_seconds": 45,
        "compression_ratio": 0.25
    }
    job3 = {
        "job_id": "job-3",
        "source_size_bytes": 500_000,
        "target_size_bytes": 250_000,
        "status": "completed",
        "duration_seconds": 20,
        "compression_ratio": 0.50
    }
    
    await compression_stats_tracker.add_job(job1)
    await compression_stats_tracker.add_job(job2)
    await compression_stats_tracker.add_job(job3)
    
    stats = await compression_stats_tracker.get_stats()
    
    assert stats["completed_jobs"] == 3
    assert stats["total_source_bytes"] == 3_500_000  # 1M + 2M + 0.5M
    assert stats["total_target_bytes"] == 850_000  # 100K + 500K + 250K
    assert stats["total_bytes_saved"] == 2_650_000
    assert stats["avg_duration_seconds"] == 31.67  # (30 + 45 + 20) / 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stats_mixed_job_states(
    compression_stats_tracker,
    compression_job_new,
    compression_job_in_progress,
    compression_job_failed
):
    """Test stats calculation with mixed job states."""
    
    await compression_stats_tracker.add_job(compression_job_new)
    await compression_stats_tracker.add_job(compression_job_in_progress)
    await compression_stats_tracker.add_job(compression_job_failed)
    
    stats = await compression_stats_tracker.get_stats()
    
    assert stats["completed_jobs"] == 1
    assert stats["running_jobs"] == 1
    assert stats["failed_jobs"] == 1
    # Only completed jobs count for byte stats
    assert stats["total_source_bytes"] == 1_000_000
    assert stats["total_target_bytes"] == 100_000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stats_empty_tracker(compression_stats_tracker):
    """Test stats with no jobs."""
    stats = await compression_stats_tracker.get_stats()
    
    assert stats["completed_jobs"] == 0
    assert stats["running_jobs"] == 0
    assert stats["failed_jobs"] == 0
    assert stats["total_source_bytes"] == 0
    assert stats["total_target_bytes"] == 0
    assert stats["avg_compression_ratio"] == 0.0
    assert stats["total_compression_ratio"] == 0.0
    assert stats["avg_duration_seconds"] == 0.0


# ============================================================================
# TEST CASES: Concurrent Operations
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_add_jobs(compression_stats_tracker):
    """Test adding jobs concurrently."""
    
    jobs = [
        {
            "job_id": f"job-{i}",
            "source_size_bytes": 1_000_000 * i,
            "target_size_bytes": 100_000 * i,
            "status": "completed",
            "duration_seconds": 30,
            "compression_ratio": 0.10
        }
        for i in range(1, 11)
    ]
    
    # Add all jobs concurrently
    results = await asyncio.gather(
        *[compression_stats_tracker.add_job(job) for job in jobs]
    )
    
    assert all(results)
    assert len(compression_stats_tracker.jobs) == 10
    assert len(compression_stats_tracker.completed_jobs) == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_add_and_update(compression_stats_tracker):
    """Test concurrent add and update operations."""
    
    # Start with 5 running jobs
    running_jobs = [
        {
            "job_id": f"job-r{i}",
            "source_size_bytes": 1_000_000,
            "status": "running",
            "progress_percent": 20
        }
        for i in range(5)
    ]
    
    for job in running_jobs:
        await compression_stats_tracker.add_job(job)
    
    # Concurrently update all to completed while adding new jobs
    new_jobs = [
        {
            "job_id": f"job-n{i}",
            "source_size_bytes": 500_000,
            "target_size_bytes": 50_000,
            "status": "completed",
            "duration_seconds": 20,
            "compression_ratio": 0.10
        }
        for i in range(5)
    ]
    
    updates = [
        compression_stats_tracker.update_job(
            f"job-r{i}",
            {
                "status": "completed",
                "progress_percent": 100,
                "target_size_bytes": 100_000,
                "duration_seconds": 30
            }
        )
        for i in range(5)
    ]
    
    adds = [compression_stats_tracker.add_job(job) for job in new_jobs]
    
    await asyncio.gather(*updates, *adds)
    
    # Verify final state
    assert len(compression_stats_tracker.completed_jobs) == 10
    assert len(compression_stats_tracker.running_jobs) == 0


# ============================================================================
# TEST CASES: Performance & Scale
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_dataset_performance(compression_stats_tracker, timer):
    """Test performance with large number of jobs."""
    
    timer.start()
    
    # Add 1000 jobs
    for i in range(1000):
        job = {
            "job_id": f"job-{i:05d}",
            "source_size_bytes": 1_000_000,
            "target_size_bytes": 100_000,
            "status": "completed",
            "duration_seconds": 30,
            "compression_ratio": 0.10
        }
        await compression_stats_tracker.add_job(job)
    
    timer.stop()
    
    # 1000 jobs should be added in < 1000ms
    assert timer.elapsed_ms < 1000, f"Too slow: {timer.elapsed_ms}ms for 1000 jobs"
    
    # Stats calculation should be fast
    timer.start()
    stats = await compression_stats_tracker.get_stats()
    timer.stop()
    
    assert stats["completed_jobs"] == 1000
    assert timer.elapsed_ms < 100, f"Stats calculation too slow: {timer.elapsed_ms}ms"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stats_accuracy_large_dataset(compression_stats_tracker):
    """Test stats accuracy with many jobs."""
    
    total_source = 0
    total_target = 0
    
    # Add 100 jobs with known sizes
    for i in range(100):
        source = (i + 1) * 100_000  # 100K, 200K, ..., 10M
        target = source // 10  # 10:1 ratio
        total_source += source
        total_target += target
        
        job = {
            "job_id": f"job-{i:03d}",
            "source_size_bytes": source,
            "target_size_bytes": target,
            "status": "completed",
            "duration_seconds": 30,
            "compression_ratio": 0.10
        }
        await compression_stats_tracker.add_job(job)
    
    stats = await compression_stats_tracker.get_stats()
    
    assert stats["completed_jobs"] == 100
    assert stats["total_source_bytes"] == total_source
    assert stats["total_target_bytes"] == total_target
    assert stats["total_bytes_saved"] == total_source - total_target


# ============================================================================
# TEST SETUP & MARKERS
# ============================================================================

@pytest.mark.unit
class TestCompressionStats:
    """Test suite for compression stats tracking."""
    
    @pytest.mark.asyncio
    async def test_suite_setup(self):
        """Verify test suite is properly initialized."""
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

