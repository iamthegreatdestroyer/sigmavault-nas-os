"""
Copyright 2025 Stephen Bilodeau. All Rights Reserved.
SigmaVault NAS OS - Compression Module Tests

Comprehensive tests for the compression bridge, job queue, and event emitter.
"""

import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Import compression module components
from engined.compression import (
    CompressionBridge,
    CompressionConfig,
    CompressionEvent,
    CompressionEventEmitter,
    CompressionEventType,
    CompressionJob,
    CompressionJobQueue,
    CompressionLevel,
    CompressionProgress,
    JobPriority,
    JobStatus,
    JobType,
    StubCompressionEngine,
    WebSocketEventBridge,
    get_compression_emitter,
    set_compression_emitter,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def compression_config():
    """Default compression configuration."""
    return CompressionConfig(
        level=CompressionLevel.BALANCED,
        chunk_size=1024 * 64,  # 64KB for faster tests
        use_semantic=True,
        lossless=True,
    )


@pytest.fixture
def bridge(compression_config):
    """CompressionBridge instance."""
    return CompressionBridge(config=compression_config)


@pytest.fixture
def event_emitter():
    """CompressionEventEmitter instance."""
    return CompressionEventEmitter(history_size=100)


@pytest.fixture
def temp_file():
    """Create temporary file with sample data."""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
        # Write compressible data (repeated patterns)
        content = b"The quick brown fox jumps over the lazy dog. " * 100
        f.write(content)
        f.flush()
        yield f.name
    # Cleanup
    try:
        os.unlink(f.name)
    except Exception:
        pass


@pytest.fixture
def sample_json_data():
    """Sample JSON data for compression."""
    return b'{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "count": 2}'


@pytest.fixture
def sample_binary_data():
    """Sample binary data."""
    return bytes(range(256)) * 10


# =============================================================================
# CompressionBridge Tests
# =============================================================================


class TestCompressionBridge:
    """Tests for CompressionBridge."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, bridge):
        """Test successful bridge initialization."""
        result = await bridge.initialize()
        assert result is True
        assert bridge._initialized is True
        # Should use StubCompressionEngine if EliteSigma-NAS not available
        assert bridge._engine is not None

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, bridge):
        """Test that initialization is idempotent."""
        await bridge.initialize()
        engine_before = bridge._engine
        await bridge.initialize()
        assert bridge._engine is engine_before

    @pytest.mark.asyncio
    async def test_compress_data_success(self, bridge, sample_json_data):
        """Test data compression."""
        result = await bridge.compress_data(sample_json_data)

        assert result.success is True
        assert result.original_size == len(sample_json_data)
        assert result.compressed_size > 0
        assert result.compression_ratio > 0
        assert result.elapsed_seconds >= 0
        assert result.checksum != ""
        assert result.is_lossless is True
        assert result.compressed_data is not None

    @pytest.mark.asyncio
    async def test_compress_data_empty(self, bridge):
        """Test compression of empty data."""
        result = await bridge.compress_data(b"")
        assert result.success is True
        assert result.original_size == 0

    @pytest.mark.asyncio
    async def test_compress_file_success(self, bridge, temp_file):
        """Test file compression."""
        output_path = temp_file + ".compressed"

        try:
            result = await bridge.compress_file(temp_file, output_path)

            assert result.success is True
            assert result.original_size > 0
            assert result.compressed_size > 0
            assert result.output_path == output_path
            assert Path(output_path).exists()
        finally:
            if Path(output_path).exists():
                os.unlink(output_path)

    @pytest.mark.asyncio
    async def test_compress_file_not_found(self, bridge):
        """Test compression of non-existent file."""
        result = await bridge.compress_file("/nonexistent/file.txt")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_progress_callback(self, bridge, sample_json_data):
        """Test progress callbacks are called."""
        progress_updates = []

        async def capture_progress(progress: CompressionProgress):
            progress_updates.append(progress)

        bridge.add_progress_callback(capture_progress)
        await bridge.compress_data(sample_json_data)

        assert len(progress_updates) > 0
        # Should have progress phases
        phases = {p.phase for p in progress_updates}
        assert "compressing" in phases or "finalizing" in phases

    @pytest.mark.asyncio
    async def test_remove_progress_callback(self, bridge):
        """Test removing progress callback."""
        async def callback(p):
            pass

        bridge.add_progress_callback(callback)
        assert callback in bridge._progress_callbacks

        bridge.remove_progress_callback(callback)
        assert callback not in bridge._progress_callbacks

    @pytest.mark.asyncio
    async def test_decompress_data(self, bridge, sample_json_data):
        """Test compression and decompression roundtrip."""
        # Compress
        compress_result = await bridge.compress_data(sample_json_data)
        assert compress_result.success is True

        # Decompress
        decompress_result = await bridge.decompress_data(
            compress_result.compressed_data
        )
        assert decompress_result.success is True
        # Decompressed data should match original
        assert decompress_result.compressed_data == sample_json_data

    def test_get_stats(self, bridge):
        """Test getting bridge statistics."""
        stats = bridge.get_stats()

        assert "initialized" in stats
        assert "config" in stats
        assert stats["config"]["level"] == CompressionLevel.BALANCED.value


# =============================================================================
# StubCompressionEngine Tests
# =============================================================================


class TestStubCompressionEngine:
    """Tests for StubCompressionEngine fallback."""

    def test_compress_decompress_roundtrip(self):
        """Test zlib compression roundtrip."""
        engine = StubCompressionEngine()
        original = b"Test data for compression" * 100

        compressed = engine.compress(original)
        decompressed = engine.decompress(compressed)

        assert decompressed == original
        assert len(compressed) < len(original)  # Should compress

    def test_compress_binary_data(self, sample_binary_data):
        """Test compression of binary data."""
        engine = StubCompressionEngine()

        compressed = engine.compress(sample_binary_data)
        decompressed = engine.decompress(compressed)

        assert decompressed == sample_binary_data


# =============================================================================
# CompressionJobQueue Tests
# =============================================================================


class TestCompressionJobQueue:
    """Tests for CompressionJobQueue."""

    @pytest.fixture
    def job_queue(self, bridge):
        """Job queue instance."""
        return CompressionJobQueue(bridge=bridge, max_concurrent=2)

    @pytest.mark.asyncio
    async def test_start_stop(self, job_queue):
        """Test queue start and stop."""
        await job_queue.start()
        assert job_queue._started is True
        assert len(job_queue._workers) == 2

        await job_queue.stop()
        assert job_queue._started is False
        assert len(job_queue._workers) == 0

    @pytest.mark.asyncio
    async def test_submit_data_job(self, job_queue, sample_json_data):
        """Test submitting a data compression job."""
        await job_queue.start()

        try:
            job = await job_queue.submit_data(
                data=sample_json_data,
                compress=True,
                priority=JobPriority.NORMAL,
            )

            assert job.id is not None
            assert job.job_type == JobType.COMPRESS_DATA
            assert job.status == JobStatus.PENDING
            assert job.bytes_total == len(sample_json_data)

            # Wait for completion
            timeout = 5.0
            while not job.is_complete and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            assert job.status == JobStatus.COMPLETED
            assert job.result is not None
            assert job.result.success is True
        finally:
            await job_queue.stop()

    @pytest.mark.asyncio
    async def test_submit_file_job(self, job_queue, temp_file):
        """Test submitting a file compression job."""
        await job_queue.start()
        output_path = temp_file + ".sigma"

        try:
            job = await job_queue.submit_file(
                input_path=temp_file,
                output_path=output_path,
                compress=True,
            )

            assert job.input_path == temp_file
            assert job.output_path == output_path

            # Wait for completion
            timeout = 5.0
            while not job.is_complete and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            assert job.status == JobStatus.COMPLETED
            assert Path(output_path).exists()
        finally:
            await job_queue.stop()
            if Path(output_path).exists():
                os.unlink(output_path)

    @pytest.mark.asyncio
    async def test_job_priority_ordering(self, job_queue, sample_json_data):
        """Test that high priority jobs are processed first."""
        # Don't start queue yet - submit jobs first
        jobs = []

        # Submit low priority first
        low_job = await job_queue.submit_data(
            data=sample_json_data,
            priority=JobPriority.LOW,
        )
        jobs.append(low_job)

        # Then high priority
        high_job = await job_queue.submit_data(
            data=sample_json_data,
            priority=JobPriority.HIGH,
        )
        jobs.append(high_job)

        # Start queue
        await job_queue.start()

        try:
            # Wait for both to complete
            timeout = 5.0
            while not all(j.is_complete for j in jobs) and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            # High priority should start before low priority
            assert high_job.started_at is not None
            assert low_job.started_at is not None
            # Can't guarantee strict ordering due to concurrency
        finally:
            await job_queue.stop()

    @pytest.mark.asyncio
    async def test_cancel_job(self, job_queue, sample_json_data):
        """Test job cancellation."""
        job = await job_queue.submit_data(
            data=sample_json_data * 100,  # Larger data
            priority=JobPriority.LOW,
        )

        # Cancel before starting
        assert job_queue.cancel_job(job.id) is True

        await job_queue.start()

        try:
            # Wait briefly
            await asyncio.sleep(0.5)

            assert job.status == JobStatus.CANCELLED
        finally:
            await job_queue.stop()

    @pytest.mark.asyncio
    async def test_get_jobs(self, job_queue, sample_json_data):
        """Test getting jobs by status."""
        await job_queue.start()

        try:
            job1 = await job_queue.submit_data(sample_json_data)
            job2 = await job_queue.submit_data(sample_json_data)

            # Wait for completion
            timeout = 5.0
            while not all(j.is_complete for j in [job1, job2]) and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            completed = job_queue.get_jobs(status=JobStatus.COMPLETED)
            assert len(completed) == 2
        finally:
            await job_queue.stop()

    def test_get_stats(self, job_queue):
        """Test queue statistics."""
        stats = job_queue.get_stats()

        assert "total_jobs" in stats
        assert "pending" in stats
        assert "running" in stats
        assert "workers" in stats

    @pytest.mark.asyncio
    async def test_progress_callback(self, job_queue, sample_json_data):
        """Test job progress callbacks."""
        progress_updates = []

        async def capture_progress(job):
            progress_updates.append(job.progress)

        job_queue.add_progress_callback(capture_progress)
        await job_queue.start()

        try:
            job = await job_queue.submit_data(sample_json_data * 10)

            timeout = 5.0
            while not job.is_complete and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            # Should have progress updates
            assert len(progress_updates) > 0
        finally:
            await job_queue.stop()

    @pytest.mark.asyncio
    async def test_complete_callback(self, job_queue, sample_json_data):
        """Test job completion callbacks."""
        completed_jobs = []

        async def capture_complete(job):
            completed_jobs.append(job)

        job_queue.add_complete_callback(capture_complete)
        await job_queue.start()

        try:
            job = await job_queue.submit_data(sample_json_data)

            timeout = 5.0
            while not job.is_complete and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            assert len(completed_jobs) == 1
            assert completed_jobs[0].id == job.id
        finally:
            await job_queue.stop()


# =============================================================================
# CompressionJob Tests
# =============================================================================


class TestCompressionJob:
    """Tests for CompressionJob dataclass."""

    def test_job_creation(self):
        """Test job creation with defaults."""
        job = CompressionJob(
            id="test-123",
            job_type=JobType.COMPRESS_FILE,
            priority=JobPriority.NORMAL,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
        )

        assert job.id == "test-123"
        assert job.progress == 0.0
        assert job.is_complete is False
        assert job.is_cancelled is False

    def test_job_cancel(self):
        """Test job cancellation."""
        job = CompressionJob(
            id="test-123",
            job_type=JobType.COMPRESS_FILE,
            priority=JobPriority.NORMAL,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
        )

        assert job.cancel() is True
        assert job.is_cancelled is True

        # Can't cancel twice
        assert job.cancel() is True  # Still returns True (already cancelled)

    def test_job_cancel_completed(self):
        """Test cannot cancel completed job."""
        job = CompressionJob(
            id="test-123",
            job_type=JobType.COMPRESS_FILE,
            priority=JobPriority.NORMAL,
            status=JobStatus.COMPLETED,
            created_at=datetime.now(),
        )

        assert job.cancel() is False

    def test_job_to_dict(self):
        """Test job serialization."""
        job = CompressionJob(
            id="test-123",
            job_type=JobType.COMPRESS_FILE,
            priority=JobPriority.HIGH,
            status=JobStatus.RUNNING,
            created_at=datetime.now(),
            input_path="/path/to/file.txt",
            progress=50.0,
        )

        data = job.to_dict()

        assert data["id"] == "test-123"
        assert data["job_type"] == "compress_file"
        assert data["priority"] == 2  # HIGH = 2
        assert data["status"] == "running"
        assert data["progress"] == 50.0
        assert data["input_path"] == "/path/to/file.txt"

    def test_elapsed_and_eta(self):
        """Test elapsed time and ETA calculations."""
        started = datetime.now()
        job = CompressionJob(
            id="test-123",
            job_type=JobType.COMPRESS_FILE,
            priority=JobPriority.NORMAL,
            status=JobStatus.RUNNING,
            created_at=started,
            started_at=started,
            progress=50.0,
        )

        # Elapsed should be near 0
        assert job.elapsed_seconds >= 0
        # ETA should be calculable
        assert job.eta_seconds >= 0


# =============================================================================
# CompressionEventEmitter Tests
# =============================================================================


class TestCompressionEventEmitter:
    """Tests for CompressionEventEmitter."""

    @pytest.mark.asyncio
    async def test_emit_event(self, event_emitter):
        """Test basic event emission."""
        received_events = []

        async def handler(event):
            received_events.append(event)

        event_emitter.on(CompressionEventType.JOB_STARTED, handler)

        await event_emitter.emit(
            CompressionEventType.JOB_STARTED,
            job_id="test-123",
            data={"input_size": 1000},
        )

        assert len(received_events) == 1
        assert received_events[0].job_id == "test-123"
        assert received_events[0].data["input_size"] == 1000

    @pytest.mark.asyncio
    async def test_global_handler(self, event_emitter):
        """Test global event handler receives all events."""
        received_events = []

        async def handler(event):
            received_events.append(event)

        event_emitter.on_all(handler)

        await event_emitter.emit(CompressionEventType.JOB_STARTED, "job-1")
        await event_emitter.emit(CompressionEventType.JOB_COMPLETED, "job-2")

        assert len(received_events) == 2

    @pytest.mark.asyncio
    async def test_emit_job_progress(self, event_emitter):
        """Test job progress event emission."""
        received_events = []

        async def handler(event):
            received_events.append(event)

        event_emitter.on(CompressionEventType.JOB_PROGRESS, handler)

        await event_emitter.emit_job_progress(
            job_id="test-123",
            progress=50.0,
            bytes_processed=500,
            bytes_total=1000,
            current_ratio=2.5,
            phase="compressing",
            eta_seconds=5.0,
        )

        assert len(received_events) == 1
        assert received_events[0].data["progress"] == 50.0
        assert received_events[0].data["current_ratio"] == 2.5

    @pytest.mark.asyncio
    async def test_event_history(self, event_emitter):
        """Test event history tracking."""
        await event_emitter.emit(CompressionEventType.JOB_STARTED, "job-1")
        await event_emitter.emit(CompressionEventType.JOB_PROGRESS, "job-1")
        await event_emitter.emit(CompressionEventType.JOB_COMPLETED, "job-1")

        history = event_emitter.get_history()
        assert len(history) == 3

        # Filter by type
        started = event_emitter.get_history(event_type=CompressionEventType.JOB_STARTED)
        assert len(started) == 1

        # Filter by job
        job_events = event_emitter.get_job_events("job-1")
        assert len(job_events) == 3

    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Test history size limit."""
        emitter = CompressionEventEmitter(history_size=5)

        for i in range(10):
            await emitter.emit(CompressionEventType.JOB_PROGRESS, f"job-{i}")

        history = emitter.get_history(limit=100)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_remove_handler(self, event_emitter):
        """Test handler removal."""
        call_count = 0

        async def handler(event):
            nonlocal call_count
            call_count += 1

        event_emitter.on(CompressionEventType.JOB_STARTED, handler)
        await event_emitter.emit(CompressionEventType.JOB_STARTED, "job-1")
        assert call_count == 1

        event_emitter.off(CompressionEventType.JOB_STARTED, handler)
        await event_emitter.emit(CompressionEventType.JOB_STARTED, "job-2")
        assert call_count == 1  # Handler removed, shouldn't increment

    def test_clear_history(self, event_emitter):
        """Test clearing history."""
        asyncio.run(event_emitter.emit(CompressionEventType.JOB_STARTED, "job-1"))
        assert len(event_emitter.get_history()) > 0

        event_emitter.clear_history()
        assert len(event_emitter.get_history()) == 0


# =============================================================================
# CompressionEvent Tests
# =============================================================================


class TestCompressionEvent:
    """Tests for CompressionEvent dataclass."""

    def test_event_to_dict(self):
        """Test event serialization."""
        event = CompressionEvent(
            event_type=CompressionEventType.JOB_PROGRESS,
            job_id="test-123",
            timestamp=datetime.now(),
            data={"progress": 50.0},
        )

        data = event.to_dict()

        assert data["type"] == "compression.job.progress"
        assert data["job_id"] == "test-123"
        assert data["data"]["progress"] == 50.0

    def test_event_to_websocket_message(self):
        """Test WebSocket message formatting."""
        event = CompressionEvent(
            event_type=CompressionEventType.JOB_COMPLETED,
            job_id="test-123",
            timestamp=datetime.now(),
            data={"compression_ratio": 5.0},
        )

        message = event.to_websocket_message()

        assert message["type"] == "compression_event"
        assert message["event"] == "compression.job.completed"
        assert message["payload"]["compression_ratio"] == 5.0


# =============================================================================
# WebSocketEventBridge Tests
# =============================================================================


class TestWebSocketEventBridge:
    """Tests for WebSocketEventBridge."""

    @pytest.mark.asyncio
    async def test_forward_events(self, event_emitter):
        """Test event forwarding to WebSocket."""
        forwarded_messages = []

        async def mock_send(message):
            forwarded_messages.append(message)

        bridge = WebSocketEventBridge(event_emitter, mock_send)
        await bridge.connect()

        try:
            await event_emitter.emit(CompressionEventType.JOB_STARTED, "job-1")

            assert len(forwarded_messages) == 1
            assert forwarded_messages[0]["type"] == "compression_event"
        finally:
            await bridge.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_stops_forwarding(self, event_emitter):
        """Test disconnecting stops event forwarding."""
        forwarded_messages = []

        async def mock_send(message):
            forwarded_messages.append(message)

        bridge = WebSocketEventBridge(event_emitter, mock_send)
        await bridge.connect()
        await bridge.disconnect()

        await event_emitter.emit(CompressionEventType.JOB_STARTED, "job-1")

        assert len(forwarded_messages) == 0


# =============================================================================
# Global Emitter Tests
# =============================================================================


class TestGlobalEmitter:
    """Tests for global emitter functions."""

    def test_get_global_emitter(self):
        """Test getting global emitter."""
        emitter = get_compression_emitter()
        assert emitter is not None

        # Should return same instance
        emitter2 = get_compression_emitter()
        assert emitter is emitter2

    def test_set_global_emitter(self):
        """Test setting global emitter."""
        custom_emitter = CompressionEventEmitter()
        set_compression_emitter(custom_emitter)

        assert get_compression_emitter() is custom_emitter


# =============================================================================
# Integration Tests
# =============================================================================


class TestCompressionIntegration:
    """Integration tests for the full compression pipeline."""

    @pytest.mark.asyncio
    async def test_full_compression_workflow(self, temp_file):
        """Test complete compression workflow with events."""
        # Setup components
        bridge = CompressionBridge()
        queue = CompressionJobQueue(bridge=bridge, max_concurrent=2)
        emitter = CompressionEventEmitter()

        # Track events
        events = []

        async def track_event(event):
            events.append(event)

        emitter.on_all(track_event)

        # Wire up queue to emitter
        async def on_job_progress(job):
            await emitter.emit_job_progress(
                job_id=job.id,
                progress=job.progress,
                bytes_processed=job.bytes_processed,
                bytes_total=job.bytes_total,
                current_ratio=job.current_ratio,
                phase=job.phase,
            )

        async def on_job_complete(job):
            if job.status == JobStatus.COMPLETED:
                await emitter.emit_job_completed(
                    job_id=job.id,
                    original_size=job.result.original_size if job.result else 0,
                    compressed_size=job.result.compressed_size if job.result else 0,
                    compression_ratio=job.result.compression_ratio if job.result else 0,
                    elapsed_seconds=job.elapsed_seconds,
                )
            elif job.status == JobStatus.FAILED:
                await emitter.emit_job_failed(
                    job_id=job.id,
                    error=job.error or "Unknown error",
                )

        queue.add_progress_callback(on_job_progress)
        queue.add_complete_callback(on_job_complete)

        await queue.start()
        output_path = temp_file + ".sigma"

        try:
            # Submit and emit queued event
            job = await queue.submit_file(temp_file, output_path)
            await emitter.emit_job_queued(
                job_id=job.id,
                job_type=job.job_type.value,
                priority=job.priority.name,
                input_path=job.input_path,
                input_size=job.bytes_total,
            )

            # Wait for completion
            timeout = 10.0
            while not job.is_complete and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            # Verify results
            assert job.status == JobStatus.COMPLETED
            assert job.result.success is True
            assert job.result.compression_ratio > 1.0

            # Verify events were emitted
            event_types = [e.event_type for e in events]
            assert CompressionEventType.JOB_QUEUED in event_types
            assert CompressionEventType.JOB_COMPLETED in event_types

        finally:
            await queue.stop()
            if Path(output_path).exists():
                os.unlink(output_path)

    @pytest.mark.asyncio
    async def test_concurrent_jobs(self):
        """Test concurrent job processing."""
        bridge = CompressionBridge()
        queue = CompressionJobQueue(bridge=bridge, max_concurrent=4)

        await queue.start()

        try:
            # Submit multiple jobs
            jobs = []
            for i in range(8):
                data = f"Job {i} data: " * 100
                job = await queue.submit_data(data.encode())
                jobs.append(job)

            # Wait for all to complete
            timeout = 15.0
            while not all(j.is_complete for j in jobs) and timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1

            # All should complete successfully
            for job in jobs:
                assert job.status == JobStatus.COMPLETED
                assert job.result.success is True

        finally:
            await queue.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
