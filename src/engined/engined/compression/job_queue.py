"""
Copyright 2025 Stephen Bilodeau. All Rights Reserved.
SigmaVault NAS OS - Compression Job Queue

Manages asynchronous compression jobs with priority scheduling,
progress tracking, and cancellation support.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable, Union
from pathlib import Path

from .bridge import CompressionBridge, CompressionConfig, CompressionResult, CompressionProgress

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status of a compression job."""
    PENDING = "pending"       # Waiting in queue
    RUNNING = "running"       # Currently processing
    COMPLETED = "completed"   # Finished successfully
    FAILED = "failed"         # Finished with error
    CANCELLED = "cancelled"   # User cancelled


class JobPriority(Enum):
    """Priority levels for job scheduling."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

    def __lt__(self, other: "JobPriority") -> bool:
        return self.value < other.value


class JobType(Enum):
    """Type of compression job."""
    COMPRESS_FILE = "compress_file"
    COMPRESS_DATA = "compress_data"
    DECOMPRESS_FILE = "decompress_file"
    DECOMPRESS_DATA = "decompress_data"


@dataclass
class CompressionJob:
    """
    Represents a compression/decompression job.
    
    Tracks status, progress, and result of async compression operations.
    """
    id: str
    job_type: JobType
    priority: JobPriority
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0-100 percentage
    bytes_processed: int = 0
    bytes_total: int = 0
    current_ratio: float = 1.0
    phase: str = "pending"
    result: Optional[CompressionResult] = None
    error: Optional[str] = None
    
    # Job parameters
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    input_data: Optional[bytes] = None
    config: CompressionConfig = field(default_factory=CompressionConfig)
    
    # Metadata
    user_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Internal
    _cancelled: bool = field(default=False, repr=False)
    _task: Optional[asyncio.Task] = field(default=None, repr=False)

    def cancel(self) -> bool:
        """
        Request cancellation of this job.
        
        Returns:
            True if cancellation requested, False if job already complete.
        """
        if self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return False
        
        self._cancelled = True
        if self._task and not self._task.done():
            self._task.cancel()
        return True

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancelled

    @property
    def is_complete(self) -> bool:
        """Check if job has finished (success, failure, or cancelled)."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def eta_seconds(self) -> float:
        """Estimate remaining time in seconds."""
        if self.progress <= 0:
            return 0.0
        elapsed = self.elapsed_seconds
        remaining_progress = 100 - self.progress
        return (elapsed / self.progress) * remaining_progress

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization."""
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "bytes_processed": self.bytes_processed,
            "bytes_total": self.bytes_total,
            "current_ratio": self.current_ratio,
            "phase": self.phase,
            "elapsed_seconds": self.elapsed_seconds,
            "eta_seconds": self.eta_seconds,
            "error": self.error,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "user_id": self.user_id,
            "tags": self.tags,
            "result": {
                "success": self.result.success,
                "original_size": self.result.original_size,
                "compressed_size": self.result.compressed_size,
                "compression_ratio": self.result.compression_ratio,
                "elapsed_seconds": self.result.elapsed_seconds,
                "data_type": self.result.data_type,
                "checksum": self.result.checksum,
            } if self.result else None,
        }


class CompressionJobQueue:
    """
    Async job queue for compression operations.
    
    Features:
    - Priority-based scheduling
    - Concurrent job execution
    - Progress callbacks
    - Job cancellation
    - Auto-retry on failure
    """

    def __init__(
        self,
        bridge: Optional[CompressionBridge] = None,
        max_concurrent: int = 4,
        max_retries: int = 2,
    ):
        """
        Initialize job queue.
        
        Args:
            bridge: CompressionBridge instance (created if not provided).
            max_concurrent: Maximum concurrent jobs.
            max_retries: Maximum retry attempts for failed jobs.
        """
        self.bridge = bridge or CompressionBridge()
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        
        self._jobs: Dict[str, CompressionJob] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running: int = 0
        self._workers: list[asyncio.Task] = []
        self._started: bool = False
        self._stopping: bool = False
        
        # Callbacks
        self._on_progress: list[Callable[[CompressionJob], Awaitable[None]]] = []
        self._on_complete: list[Callable[[CompressionJob], Awaitable[None]]] = []

    async def start(self) -> None:
        """Start the job queue workers."""
        if self._started:
            return
        
        self._started = True
        self._stopping = False
        
        # Initialize bridge
        await self.bridge.initialize()
        
        # Register for progress updates from bridge
        self.bridge.add_progress_callback(self._handle_bridge_progress)
        
        # Start worker tasks
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info(f"CompressionJobQueue started with {self.max_concurrent} workers")

    async def stop(self, wait: bool = True) -> None:
        """
        Stop the job queue.
        
        Args:
            wait: If True, wait for running jobs to complete.
        """
        self._stopping = True
        
        if not wait:
            # Cancel all workers
            for worker in self._workers:
                worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        self._started = False
        logger.info("CompressionJobQueue stopped")

    def add_progress_callback(
        self,
        callback: Callable[[CompressionJob], Awaitable[None]]
    ) -> None:
        """Register callback for job progress updates."""
        self._on_progress.append(callback)

    def add_complete_callback(
        self,
        callback: Callable[[CompressionJob], Awaitable[None]]
    ) -> None:
        """Register callback for job completion."""
        self._on_complete.append(callback)

    async def submit_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        compress: bool = True,
        priority: JobPriority = JobPriority.NORMAL,
        config: Optional[CompressionConfig] = None,
        user_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> CompressionJob:
        """
        Submit a file compression/decompression job.
        
        Args:
            input_path: Path to input file.
            output_path: Path for output file (auto-generated if not provided).
            compress: True for compression, False for decompression.
            priority: Job priority.
            config: Compression configuration.
            user_id: User identifier.
            tags: Job metadata tags.
            
        Returns:
            CompressionJob instance for tracking.
        """
        job_id = str(uuid.uuid4())
        job_type = JobType.COMPRESS_FILE if compress else JobType.DECOMPRESS_FILE
        
        # Auto-generate output path if needed
        if output_path is None:
            input_file = Path(input_path)
            if compress:
                output_path = str(input_file.with_suffix(input_file.suffix + ".sigma"))
            else:
                # Remove .sigma extension if present
                if input_file.suffix == ".sigma":
                    output_path = str(input_file.with_suffix(""))
                else:
                    output_path = str(input_file.with_suffix(".decompressed"))
        
        # Get file size for progress tracking
        try:
            bytes_total = Path(input_path).stat().st_size
        except OSError:
            bytes_total = 0
        
        job = CompressionJob(
            id=job_id,
            job_type=job_type,
            priority=priority,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            input_path=input_path,
            output_path=output_path,
            bytes_total=bytes_total,
            config=config or CompressionConfig(),
            user_id=user_id,
            tags=tags or {},
        )
        
        self._jobs[job_id] = job
        
        # Add to priority queue (negative priority for max-heap behavior)
        await self._queue.put((-priority.value, datetime.now(), job_id))
        
        logger.info(f"Job {job_id} submitted: {job_type.value} {input_path}")
        return job

    async def submit_data(
        self,
        data: bytes,
        compress: bool = True,
        priority: JobPriority = JobPriority.NORMAL,
        config: Optional[CompressionConfig] = None,
        user_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> CompressionJob:
        """
        Submit a data compression/decompression job.
        
        Args:
            data: Input bytes.
            compress: True for compression, False for decompression.
            priority: Job priority.
            config: Compression configuration.
            user_id: User identifier.
            tags: Job metadata tags.
            
        Returns:
            CompressionJob instance for tracking.
        """
        job_id = str(uuid.uuid4())
        job_type = JobType.COMPRESS_DATA if compress else JobType.DECOMPRESS_DATA
        
        job = CompressionJob(
            id=job_id,
            job_type=job_type,
            priority=priority,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            input_data=data,
            bytes_total=len(data),
            config=config or CompressionConfig(),
            user_id=user_id,
            tags=tags or {},
        )
        
        self._jobs[job_id] = job
        await self._queue.put((-priority.value, datetime.now(), job_id))
        
        logger.info(f"Job {job_id} submitted: {job_type.value} ({len(data)} bytes)")
        return job

    def get_job(self, job_id: str) -> Optional[CompressionJob]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[CompressionJob]:
        """
        Get jobs matching criteria.
        
        Args:
            status: Filter by status.
            user_id: Filter by user.
            limit: Maximum number of jobs to return.
            
        Returns:
            List of matching jobs.
        """
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]
        
        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID to cancel.
            
        Returns:
            True if cancellation requested, False if job not found or already complete.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return False
        return job.cancel()

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        jobs = list(self._jobs.values())
        return {
            "total_jobs": len(jobs),
            "pending": len([j for j in jobs if j.status == JobStatus.PENDING]),
            "running": len([j for j in jobs if j.status == JobStatus.RUNNING]),
            "completed": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            "failed": len([j for j in jobs if j.status == JobStatus.FAILED]),
            "cancelled": len([j for j in jobs if j.status == JobStatus.CANCELLED]),
            "workers": len(self._workers),
            "queue_size": self._queue.qsize(),
        }

    async def _worker(self, worker_id: int) -> None:
        """Background worker for processing jobs."""
        logger.debug(f"Worker {worker_id} started")
        
        while not self._stopping:
            try:
                # Get next job from queue (with timeout)
                try:
                    _, _, job_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue
                
                job = self._jobs.get(job_id)
                if job is None:
                    continue
                
                # Skip if cancelled
                if job.is_cancelled:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = datetime.now()
                    await self._emit_complete(job)
                    continue
                
                # Process job
                self._running += 1
                try:
                    await self._process_job(job)
                finally:
                    self._running -= 1
                
            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.debug(f"Worker {worker_id} stopped")

    async def _process_job(self, job: CompressionJob) -> None:
        """Process a single job."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        job.phase = "starting"
        
        try:
            # Create task for processing
            job._task = asyncio.current_task()
            
            # Execute based on job type
            if job.job_type == JobType.COMPRESS_FILE:
                result = await self.bridge.compress_file(
                    job.input_path,
                    job.output_path,
                    job.id,
                )
            elif job.job_type == JobType.DECOMPRESS_FILE:
                result = await self.bridge.decompress_file(
                    job.input_path,
                    job.output_path,
                    job.id,
                )
            elif job.job_type == JobType.COMPRESS_DATA:
                result = await self.bridge.compress_data(
                    job.input_data,
                    job.id,
                )
            elif job.job_type == JobType.DECOMPRESS_DATA:
                result = await self.bridge.decompress_data(
                    job.input_data,
                    job.id,
                )
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # Update job with result
            job.result = result
            job.progress = 100.0
            job.phase = "complete"
            
            if result.success:
                job.status = JobStatus.COMPLETED
            else:
                job.status = JobStatus.FAILED
                job.error = result.error
            
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            job.phase = "cancelled"
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.phase = "error"
        finally:
            job.completed_at = datetime.now()
            job._task = None
            await self._emit_complete(job)

    async def _handle_bridge_progress(self, progress: CompressionProgress) -> None:
        """Handle progress update from bridge."""
        job = self._jobs.get(progress.job_id)
        if job is None:
            return
        
        # Update job progress
        if progress.bytes_total > 0:
            job.progress = (progress.bytes_processed / progress.bytes_total) * 100
        job.bytes_processed = progress.bytes_processed
        job.bytes_total = progress.bytes_total
        job.current_ratio = progress.current_ratio
        job.phase = progress.phase
        
        # Emit progress callbacks
        await self._emit_progress(job)

    async def _emit_progress(self, job: CompressionJob) -> None:
        """Emit progress callbacks."""
        for callback in self._on_progress:
            try:
                await callback(job)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    async def _emit_complete(self, job: CompressionJob) -> None:
        """Emit completion callbacks."""
        for callback in self._on_complete:
            try:
                await callback(job)
            except Exception as e:
                logger.error(f"Complete callback error: {e}")
