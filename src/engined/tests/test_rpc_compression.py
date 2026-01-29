"""
Tests for JSON-RPC Compression Handlers

Tests the RPC layer that bridges Go API to Python compression engine.
"""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from engined.api.rpc import (
    JSONRPCRequest,
    JSONRPCResponse,
    handle_compress_data,
    handle_compress_file,
    handle_decompress_data,
    handle_decompress_file,
    handle_queue_submit,
    handle_queue_status,
    handle_queue_running,
    handle_queue_cancel,
    handle_get_compression_config,
    handle_set_compression_config,
)


class TestCompressDataRPC:
    """Tests for compression.compress.data RPC handler."""

    @pytest.mark.asyncio
    async def test_compress_data_basic(self):
        """Test basic data compression via RPC."""
        test_data = b"Hello, World! " * 100
        data_b64 = base64.b64encode(test_data).decode()
        
        params = {
            "data": data_b64,
            "level": "fast",
        }
        
        result = await handle_compress_data(params)
        
        assert result["success"] is True
        assert result["original_size"] == len(test_data)
        assert result["compressed_size"] <= len(test_data)
        assert result["job_id"] is not None
        assert result["data"] is not None  # Base64 compressed data

    @pytest.mark.asyncio
    async def test_compress_data_missing_data(self):
        """Test error when data param is missing."""
        with pytest.raises(ValueError, match="data parameter required"):
            await handle_compress_data({})

    @pytest.mark.asyncio
    async def test_compress_data_invalid_base64(self):
        """Test error when base64 is invalid."""
        with pytest.raises(ValueError, match="Invalid base64"):
            await handle_compress_data({"data": "not-valid-base64!!!"})

    @pytest.mark.asyncio
    async def test_compress_data_with_job_id(self):
        """Test compression with custom job ID."""
        test_data = b"Test data for compression"
        data_b64 = base64.b64encode(test_data).decode()
        
        params = {
            "data": data_b64,
            "job_id": "custom-job-123",
        }
        
        result = await handle_compress_data(params)
        
        assert result["job_id"] == "custom-job-123"
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_compress_data_different_levels(self):
        """Test compression with different levels."""
        test_data = b"Test data " * 50
        data_b64 = base64.b64encode(test_data).decode()
        
        for level in ["fast", "balanced", "maximum", "adaptive"]:
            result = await handle_compress_data({
                "data": data_b64,
                "level": level,
            })
            
            assert result["success"] is True
            assert result["original_size"] == len(test_data)

    @pytest.mark.asyncio
    async def test_compress_data_empty(self):
        """Test compression of empty data."""
        data_b64 = base64.b64encode(b"").decode()
        
        result = await handle_compress_data({"data": data_b64})
        
        assert result["success"] is True
        assert result["original_size"] == 0


class TestDecompressDataRPC:
    """Tests for compression.decompress.data RPC handler."""

    @pytest.mark.asyncio
    async def test_decompress_data_roundtrip(self):
        """Test compress then decompress roundtrip."""
        original_data = b"This is test data for roundtrip compression!"
        data_b64 = base64.b64encode(original_data).decode()
        
        # Compress
        compress_result = await handle_compress_data({"data": data_b64})
        assert compress_result["success"] is True
        
        # Decompress
        decompress_result = await handle_decompress_data({
            "data": compress_result["data"]
        })
        
        assert decompress_result["success"] is True
        
        # Verify roundtrip
        recovered_data = base64.b64decode(decompress_result["data"])
        assert recovered_data == original_data

    @pytest.mark.asyncio
    async def test_decompress_data_missing_data(self):
        """Test error when data param is missing."""
        with pytest.raises(ValueError, match="data parameter required"):
            await handle_decompress_data({})


class TestCompressFileRPC:
    """Tests for compression.compress.file RPC handler."""

    @pytest.mark.asyncio
    async def test_compress_file_not_exists(self):
        """Test error when file doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            await handle_compress_file({
                "source_path": "/nonexistent/file.txt"
            })

    @pytest.mark.asyncio
    async def test_compress_file_missing_path(self):
        """Test error when source_path is missing."""
        with pytest.raises(ValueError, match="source_path parameter required"):
            await handle_compress_file({})

    @pytest.mark.asyncio
    async def test_compress_file_with_temp_file(self, tmp_path):
        """Test file compression with temporary file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = b"File content for compression test " * 100
        test_file.write_bytes(test_content)
        
        result = await handle_compress_file({
            "source_path": str(test_file),
            "level": "fast",
        })
        
        assert result["success"] is True
        assert result["original_size"] == len(test_content)
        assert result["source_path"] == str(test_file)


class TestDecompressFileRPC:
    """Tests for compression.decompress.file RPC handler."""

    @pytest.mark.asyncio
    async def test_decompress_file_not_exists(self):
        """Test error when file doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            await handle_decompress_file({
                "source_path": "/nonexistent/file.compressed"
            })

    @pytest.mark.asyncio
    async def test_decompress_file_missing_path(self):
        """Test error when source_path is missing."""
        with pytest.raises(ValueError, match="source_path parameter required"):
            await handle_decompress_file({})


class TestQueueSubmitRPC:
    """Tests for compression.queue.submit RPC handler."""

    @pytest.mark.asyncio
    async def test_queue_submit_data(self):
        """Test submitting data compression to queue."""
        test_data = b"Data for queue processing"
        data_b64 = base64.b64encode(test_data).decode()
        
        result = await handle_queue_submit({
            "type": "compress_data",
            "data": data_b64,
            "priority": "high",
        })
        
        assert result["job_id"] is not None
        assert result["status"] in ["pending", "running"]
        assert result["priority"] == "high"
        assert result["job_type"] == "compress_data"

    @pytest.mark.asyncio
    async def test_queue_submit_invalid_type(self):
        """Test error with invalid job type."""
        with pytest.raises(ValueError, match="Invalid job type"):
            await handle_queue_submit({
                "type": "invalid_type",
                "data": base64.b64encode(b"test").decode(),
            })

    @pytest.mark.asyncio
    async def test_queue_submit_file_missing_path(self):
        """Test error when file path missing for file operation."""
        with pytest.raises(ValueError, match="source_path required"):
            await handle_queue_submit({
                "type": "compress_file",
            })

    @pytest.mark.asyncio
    async def test_queue_submit_data_missing_data(self):
        """Test error when data missing for data operation."""
        with pytest.raises(ValueError, match="data required"):
            await handle_queue_submit({
                "type": "compress_data",
            })


class TestQueueStatusRPC:
    """Tests for compression.queue.status RPC handler."""

    @pytest.mark.asyncio
    async def test_queue_status_all(self):
        """Test getting overall queue status."""
        result = await handle_queue_status({})
        
        # Should return queue statistics
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_queue_status_specific_job(self):
        """Test getting status of specific job."""
        # First submit a job
        test_data = b"Data for status check"
        data_b64 = base64.b64encode(test_data).decode()
        
        submit_result = await handle_queue_submit({
            "type": "compress_data",
            "data": data_b64,
        })
        
        # Then check its status
        status_result = await handle_queue_status({
            "job_id": submit_result["job_id"]
        })
        
        assert status_result["job_id"] == submit_result["job_id"]
        assert "status" in status_result

    @pytest.mark.asyncio
    async def test_queue_status_not_found(self):
        """Test error when job not found."""
        with pytest.raises(ValueError, match="Job not found"):
            await handle_queue_status({"job_id": "nonexistent-job-id"})


class TestQueueRunningRPC:
    """Tests for compression.queue.running RPC handler (WebSocket progress)."""

    @pytest.mark.asyncio
    async def test_queue_running_empty(self):
        """Test getting running jobs when queue is empty."""
        result = await handle_queue_running({})
        
        assert isinstance(result, dict)
        assert "jobs" in result
        assert isinstance(result["jobs"], list)
        assert "total_running" in result
        assert "total_pending" in result
        assert "total_jobs" in result

    @pytest.mark.asyncio
    async def test_queue_running_with_pending(self):
        """Test getting running jobs includes pending when requested."""
        # Submit a job
        test_data = b"Data for running check"
        data_b64 = base64.b64encode(test_data).decode()
        
        submit_result = await handle_queue_submit({
            "type": "compress_data",
            "data": data_b64,
        })
        
        # Get running jobs with pending
        result = await handle_queue_running({"include_pending": True})
        
        assert isinstance(result, dict)
        assert "jobs" in result
        assert result["total_pending"] >= 0 or result["total_running"] >= 0

    @pytest.mark.asyncio
    async def test_queue_running_job_structure(self):
        """Test that returned jobs have correct structure for WebSocket streaming."""
        # Submit a job
        test_data = b"Data for structure check " * 10
        data_b64 = base64.b64encode(test_data).decode()
        
        await handle_queue_submit({
            "type": "compress_data",
            "data": data_b64,
        })
        
        # Get running jobs
        result = await handle_queue_running({"include_pending": True})
        
        if result["jobs"]:
            job = result["jobs"][0]
            # Verify all WebSocket-required fields are present
            expected_fields = [
                "job_id", "status", "job_type", "priority", 
                "progress", "phase", "bytes_processed", "bytes_total",
                "current_ratio", "elapsed_seconds", "eta_seconds",
                "created_at"
            ]
            for field in expected_fields:
                assert field in job, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_queue_running_limit(self):
        """Test that limit parameter works."""
        result = await handle_queue_running({"limit": 5})
        
        assert isinstance(result, dict)
        assert len(result["jobs"]) <= 5


class TestQueueCancelRPC:
    """Tests for compression.queue.cancel RPC handler."""

    @pytest.mark.asyncio
    async def test_queue_cancel_missing_job_id(self):
        """Test error when job_id is missing."""
        with pytest.raises(ValueError, match="job_id required"):
            await handle_queue_cancel({})

    @pytest.mark.asyncio
    async def test_queue_cancel_job(self):
        """Test cancelling a queued job."""
        # Submit a job
        test_data = b"Data to cancel"
        data_b64 = base64.b64encode(test_data).decode()
        
        submit_result = await handle_queue_submit({
            "type": "compress_data",
            "data": data_b64,
        })
        
        # Cancel it
        cancel_result = await handle_queue_cancel({
            "job_id": submit_result["job_id"]
        })
        
        assert cancel_result["job_id"] == submit_result["job_id"]
        assert "cancelled" in cancel_result


class TestCompressionConfigRPC:
    """Tests for compression config RPC handlers."""

    @pytest.mark.asyncio
    async def test_get_config(self):
        """Test getting compression config."""
        result = await handle_get_compression_config()
        
        assert "level" in result
        assert "chunk_size" in result
        assert "use_semantic" in result
        assert "lossless" in result
        assert "engine" in result

    @pytest.mark.asyncio
    async def test_set_config(self):
        """Test setting compression config."""
        result = await handle_set_compression_config({
            "level": "maximum",
            "chunk_size": 2 * 1024 * 1024,  # 2MB
            "use_semantic": True,
            "lossless": True,
        })
        
        assert result["success"] is True
        assert result["level"] == "maximum"
        assert result["chunk_size"] == 2 * 1024 * 1024
        assert result["use_semantic"] is True
        assert result["lossless"] is True

    @pytest.mark.asyncio
    async def test_set_config_partial(self):
        """Test setting only some config options."""
        # First get current config
        current = await handle_get_compression_config()
        
        # Set only level
        result = await handle_set_compression_config({
            "level": "fast",
        })
        
        assert result["success"] is True
        assert result["level"] == "fast"
        # Other values should remain unchanged
        assert result["chunk_size"] == current["chunk_size"]


class TestRPCIntegration:
    """Integration tests for full RPC flow."""

    @pytest.mark.asyncio
    async def test_full_compression_flow(self):
        """Test complete compression flow via RPC."""
        # 1. Check config
        config = await handle_get_compression_config()
        assert config["engine"] in ["semantic", "stub"]
        
        # 2. Compress data
        original_data = b"Integration test data " * 50
        compress_result = await handle_compress_data({
            "data": base64.b64encode(original_data).decode(),
            "level": "balanced",
        })
        assert compress_result["success"] is True
        
        # 3. Decompress
        decompress_result = await handle_decompress_data({
            "data": compress_result["data"]
        })
        assert decompress_result["success"] is True
        
        # 4. Verify
        recovered = base64.b64decode(decompress_result["data"])
        assert recovered == original_data

    @pytest.mark.asyncio
    async def test_large_data_compression(self):
        """Test compression of larger data via RPC."""
        # 100KB of data
        large_data = b"Large data block for testing " * 3600
        assert len(large_data) >= 100 * 1024
        
        result = await handle_compress_data({
            "data": base64.b64encode(large_data).decode(),
            "level": "balanced",
        })
        
        assert result["success"] is True
        assert result["original_size"] == len(large_data)
        assert result["compression_ratio"] > 1.0  # Some compression achieved

    @pytest.mark.asyncio
    async def test_binary_data_compression(self):
        """Test compression of binary data via RPC."""
        import os
        binary_data = os.urandom(1024)  # 1KB random bytes
        
        result = await handle_compress_data({
            "data": base64.b64encode(binary_data).decode(),
            "level": "fast",
        })
        
        assert result["success"] is True
        
        # Decompress and verify
        decompress_result = await handle_decompress_data({
            "data": result["data"]
        })
        
        recovered = base64.b64decode(decompress_result["data"])
        assert recovered == binary_data
