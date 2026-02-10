"""
Compression API Endpoints

Provides REST API for AI-powered compression operations.
Supports multiple algorithms with adaptive optimization.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from engined.agents.swarm import AgentSwarm

router = APIRouter()


class CompressionAlgorithm(str, Enum):
    """Supported compression algorithms."""

    ZSTD = "zstd"
    LZ4 = "lz4"
    BROTLI = "brotli"
    AUTO = "auto"  # AI-selected based on content analysis


class CompressionLevel(str, Enum):
    """Compression level presets."""

    FASTEST = "fastest"
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"
    MAXIMUM = "maximum"


class JobStatus(str, Enum):
    """Compression job status."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPRESSING = "compressing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CompressionRequest(BaseModel):
    """Request model for compression operations."""

    source_path: str = Field(description="Source file or directory path")
    destination_path: str | None = Field(
        default=None,
        description="Destination path (defaults to source with .compressed extension)",
    )
    algorithm: CompressionAlgorithm = Field(
        default=CompressionAlgorithm.AUTO,
        description="Compression algorithm to use",
    )
    level: CompressionLevel = Field(
        default=CompressionLevel.BALANCED,
        description="Compression level preset",
    )
    preserve_original: bool = Field(
        default=True,
        description="Keep original file after compression",
    )
    recursive: bool = Field(
        default=False,
        description="Process directories recursively",
    )
    encrypt: bool = Field(
        default=False,
        description="Encrypt after compression",
    )


class CompressionResult(BaseModel):
    """Result model for compression operations."""

    job_id: str = Field(description="Unique job identifier")
    status: JobStatus = Field(description="Current job status")
    source_path: str = Field(description="Source path")
    destination_path: str | None = Field(description="Destination path")
    algorithm_used: str | None = Field(description="Algorithm that was used")
    original_size: int | None = Field(description="Original size in bytes")
    compressed_size: int | None = Field(description="Compressed size in bytes")
    compression_ratio: float | None = Field(description="Compression ratio (0-1)")
    time_elapsed_ms: int | None = Field(description="Processing time in milliseconds")
    created_at: str = Field(description="Job creation timestamp")
    completed_at: str | None = Field(description="Job completion timestamp")
    error: str | None = Field(description="Error message if failed")


class CompressionStats(BaseModel):
    """Compression statistics model."""

    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    bytes_processed: int
    bytes_saved: int
    average_ratio: float
    most_used_algorithm: str


# In-memory job storage (would be Redis/DB in production)
_compression_jobs: dict[str, CompressionResult] = {}


@router.post("/jobs", response_model=CompressionResult, status_code=status.HTTP_202_ACCEPTED)
async def start_compression(
    request: Request,
    compression_request: CompressionRequest,
    background_tasks: BackgroundTasks,
) -> CompressionResult:
    """
    Start a new compression job.
    
    The job runs asynchronously. Use the returned job_id to track progress.
    When algorithm is 'auto', AI agents analyze the content and select
    the optimal algorithm.
    """
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)

    if not swarm or not swarm.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent swarm not ready",
        )

    job_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    result = CompressionResult(
        job_id=job_id,
        status=JobStatus.PENDING,
        source_path=compression_request.source_path,
        destination_path=compression_request.destination_path,
        algorithm_used=None,
        original_size=None,
        compressed_size=None,
        compression_ratio=None,
        time_elapsed_ms=None,
        created_at=now.isoformat(),
        completed_at=None,
        error=None,
    )

    _compression_jobs[job_id] = result

    # Queue background processing
    background_tasks.add_task(
        process_compression_job,
        job_id,
        compression_request,
        swarm,
    )

    return result


async def process_compression_job(
    job_id: str,
    request: CompressionRequest,
    swarm: AgentSwarm,
) -> None:
    """Background task to process compression job."""
    import time

    job = _compression_jobs.get(job_id)
    if not job:
        return

    start_time = time.monotonic()

    try:
        # Update status to analyzing
        job.status = JobStatus.ANALYZING

        # Request agent to analyze and compress
        agent_result = await swarm.submit_compression_task(
            source_path=request.source_path,
            algorithm=request.algorithm.value,
            level=request.level.value,
            encrypt=request.encrypt,
        )

        # Update with results
        job.status = JobStatus.COMPLETED
        job.algorithm_used = agent_result.get("algorithm", request.algorithm.value)
        job.original_size = agent_result.get("original_size", 0)
        job.compressed_size = agent_result.get("compressed_size", 0)
        job.destination_path = agent_result.get("destination_path", request.destination_path)

        if job.original_size and job.compressed_size:
            job.compression_ratio = 1 - (job.compressed_size / job.original_size)

        job.time_elapsed_ms = int((time.monotonic() - start_time) * 1000)
        job.completed_at = datetime.now(UTC).isoformat()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.now(UTC).isoformat()


@router.get("/jobs", response_model=list[CompressionResult])
async def list_compression_jobs(
    status_filter: JobStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[CompressionResult]:
    """
    List compression jobs.
    
    Optionally filter by status and paginate results.
    """
    jobs = list(_compression_jobs.values())

    if status_filter:
        jobs = [j for j in jobs if j.status == status_filter]

    # Sort by creation time (newest first)
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    return jobs[offset : offset + limit]


@router.get("/jobs/{job_id}", response_model=CompressionResult)
async def get_compression_job(job_id: str) -> CompressionResult:
    """Get details of a specific compression job."""
    job = _compression_jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_compression_job(job_id: str) -> None:
    """
    Cancel a pending or running compression job.
    
    Only pending and analyzing jobs can be cancelled.
    """
    job = _compression_jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job.status not in (JobStatus.PENDING, JobStatus.ANALYZING, JobStatus.COMPRESSING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel job with status {job.status}",
        )

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(UTC).isoformat()


@router.get("/stats", response_model=CompressionStats)
async def get_compression_stats() -> CompressionStats:
    """Get compression statistics across all jobs."""
    jobs = list(_compression_jobs.values())

    completed = [j for j in jobs if j.status == JobStatus.COMPLETED]
    failed = [j for j in jobs if j.status == JobStatus.FAILED]

    total_original = sum(j.original_size or 0 for j in completed)
    total_compressed = sum(j.compressed_size or 0 for j in completed)

    # Count algorithm usage
    algorithm_counts: dict[str, int] = {}
    for job in completed:
        if job.algorithm_used:
            algorithm_counts[job.algorithm_used] = algorithm_counts.get(job.algorithm_used, 0) + 1

    most_used = max(algorithm_counts, key=algorithm_counts.get) if algorithm_counts else "none"

    return CompressionStats(
        total_jobs=len(jobs),
        completed_jobs=len(completed),
        failed_jobs=len(failed),
        bytes_processed=total_original,
        bytes_saved=total_original - total_compressed,
        average_ratio=1 - (total_compressed / total_original) if total_original > 0 else 0,
        most_used_algorithm=most_used,
    )


@router.post("/analyze")
async def analyze_content(
    request: Request,
    source_path: str,
) -> dict:
    """
    Analyze content and recommend optimal compression settings.
    
    Uses AI agents to analyze file content type, size, and patterns
    to recommend the best compression algorithm and level.
    """
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)

    if not swarm or not swarm.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent swarm not ready",
        )

    analysis = await swarm.analyze_content(source_path)

    return {
        "source_path": source_path,
        "content_type": analysis.get("content_type", "unknown"),
        "recommended_algorithm": analysis.get("recommended_algorithm", "zstd"),
        "recommended_level": analysis.get("recommended_level", "balanced"),
        "estimated_ratio": analysis.get("estimated_ratio", 0.5),
        "estimated_time_ms": analysis.get("estimated_time_ms", 1000),
    }
