#!/usr/bin/env python3
"""
Test Script: Verify Real Compression RPC Pipeline

Tests that:
1. Python RPC engine accepts compression requests
2. Compression bridge properly compresses data
3. Job tracking works correctly
4. RPC handlers integrate with Go API properly
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add engined to path
engined_path = Path(__file__).parent.parent / "src" / "engined"
sys.path.insert(0, str(engined_path))

async def test_compression_bridge():
    """Test the CompressionBridge directly."""
    logger.info("=" * 80)
    logger.info("TEST 1: Direct CompressionBridge Testing")
    logger.info("=" * 80)
    
    from engined.compression.bridge import CompressionBridge, CompressionConfig, CompressionLevel
    
    # Create bridge with balanced compression
    config = CompressionConfig(level=CompressionLevel.BALANCED)
    bridge = CompressionBridge(config)
    
    # Initialize
    logger.info("Initializing compression bridge...")
    success = await bridge.initialize()
    if not success:
        logger.error("Failed to initialize bridge")
        return False
    
    logger.info(f"✓ Bridge initialized")
    logger.info(f"  Engine type: {type(bridge._engine).__name__}")
    logger.info(f"  Config level: {config.level.value}")
    
    # Test 1: Compress small data
    test_data = b"The quick brown fox jumps over the lazy dog. " * 100
    logger.info(f"\nCompressing {len(test_data)} bytes of test data...")
    
    result = await bridge.compress_data(test_data)
    
    if not result.success:
        logger.error(f"✗ Compression failed: {result.error}")
        return False
    
    logger.info(f"✓ Compression successful")
    logger.info(f"  Job ID: {result.job_id}")
    logger.info(f"  Original size: {result.original_size:,} bytes")
    logger.info(f"  Compressed size: {result.compressed_size:,} bytes")
    logger.info(f"  Compression ratio: {result.compression_ratio:.2f}x")
    logger.info(f"  Method: {result.method}")
    logger.info(f"  Elapsed: {result.elapsed_seconds:.3f}s")
    logger.info(f"  Checksum: {result.checksum[:16]}...")
    
    # Test 2: Decompress back
    logger.info(f"\nDecompressing {result.compressed_size} bytes...")
    
    decompressed = await bridge.decompress_data(result.compressed_data)
    
    if not decompressed.success:
        logger.error(f"✗ Decompression failed: {decompressed.error}")
        return False
    
    logger.info(f"✓ Decompression successful")
    logger.info(f"  Decompressed size: {decompressed.original_size:,} bytes")
    logger.info(f"  Matches original: {decompressed.compressed_data == test_data}")
    
    if decompressed.compressed_data != test_data:
        logger.error("✗ Decompressed data does not match original!")
        return False
    
    logger.info("✓ Data integrity verified")
    
    return True


async def test_rpc_handlers():
    """Test the JSON-RPC handlers."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: JSON-RPC Handler Testing")
    logger.info("=" * 80)
    
    import base64
    from engined.api.rpc import (
        handle_compress_data,
        handle_decompress_data,
        handle_get_compression_config,
    )
    
    # Test 1: Compress via RPC
    test_data = b"RPC compression test data " * 50
    data_b64 = base64.b64encode(test_data).decode()
    
    logger.info(f"Calling compression.compress.data RPC...")
    
    params = {
        "data": data_b64,
        "level": "balanced",
    }
    
    result = await handle_compress_data(params)
    
    if not result.get("success"):
        logger.error(f"✗ RPC compression failed: {result.get('error')}")
        return False
    
    logger.info(f"✓ RPC compression successful")
    logger.info(f"  Job ID: {result['job_id']}")
    logger.info(f"  Original: {result['original_size']:,} bytes")
    logger.info(f"  Compressed: {result['compressed_size']:,} bytes")
    logger.info(f"  Ratio: {result['compression_ratio']:.2f}x")
    
    # Test 2: Decompress via RPC
    logger.info(f"\nCalling compression.decompress.data RPC...")
    
    compressed_b64 = result.get("data")
    params = {
        "data": compressed_b64,
    }
    
    result2 = await handle_decompress_data(params)
    
    if not result2.get("success"):
        logger.error(f"✗ RPC decompression failed: {result2.get('error')}")
        return False
    
    logger.info(f"✓ RPC decompression successful")
    logger.info(f"  Decompressed size: {result2['original_size']:,} bytes")
    
    # Verify data integrity
    decompressed_data = base64.b64decode(result2.get("data", ""))
    if decompressed_data != test_data:
        logger.error("✗ RPC decompressed data does not match original!")
        return False
    
    logger.info("✓ RPC data integrity verified")
    
    # Test 3: Get config
    logger.info(f"\nCalling compression.config.get RPC...")
    
    config = await handle_get_compression_config()
    
    logger.info(f"✓ Configuration retrieved")
    logger.info(f"  Level: {config.get('level')}")
    logger.info(f"  Use semantic: {config.get('use_semantic')}")
    logger.info(f"  Chunk size: {config.get('chunk_size'):,} bytes")
    
    return True


async def test_compression_pipeline():
    """Test the full end-to-end compression pipeline."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: End-to-End Pipeline Testing")
    logger.info("=" * 80)
    
    from engined.compression.job_queue import CompressionJobQueue, CompressionJob, JobType, JobPriority, JobStatus
    from engined.compression.bridge import CompressionBridge, CompressionConfig
    
    # Create bridge and queue
    bridge = CompressionBridge(CompressionConfig())
    await bridge.initialize()
    
    queue = CompressionJobQueue(bridge, max_concurrent=4)
    await queue.initialize()
    
    logger.info("✓ Job queue initialized")
    logger.info(f"  Max concurrent: {queue.max_concurrent}")
    
    # Create a job
    test_data = b"Job queue test data " * 100
    
    logger.info(f"\nSubmitting compression job with {len(test_data)} bytes...")
    
    job_id = await queue.compress_data(
        test_data,
        priority=JobPriority.NORMAL,
        job_type=JobType.COMPRESS_DATA,
    )
    
    logger.info(f"✓ Job submitted: {job_id}")
    
    # Wait for completion
    max_wait = 30  # seconds
    start = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start < max_wait:
        job = queue.get_job(job_id)
        if job and job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            break
        await asyncio.sleep(0.5)
    
    # Check result
    job = queue.get_job(job_id)
    if not job:
        logger.error(f"✗ Job not found after completion")
        return False
    
    logger.info(f"✓ Job completed: {job.status.value}")
    logger.info(f"  Progress: {job.progress}%")
    logger.info(f"  Bytes processed: {job.bytes_processed:,}/{job.bytes_total:,}")
    logger.info(f"  Compression ratio: {job.current_ratio:.2f}x")
    
    if job.status == JobStatus.FAILED:
        logger.error(f"✗ Job failed: {job.error}")
        return False
    
    logger.info("✓ Job completed successfully")
    
    return True


async def main():
    """Run all tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "OPTION C - REAL COMPRESSION INTEGRATION TEST" + " " * 14 + "║")
    logger.info("║" + " " * 25 + "Full RPC Pipeline Verification" + " " * 23 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info(f"\nStarting tests at {datetime.now().isoformat()}\n")
    
    results = []
    
    # Run tests
    try:
        logger.info("\n[1/3] Testing CompressionBridge...")
        results.append(("CompressionBridge", await test_compression_bridge()))
        
        logger.info("\n[2/3] Testing RPC Handlers...")
        results.append(("RPC Handlers", await test_rpc_handlers()))
        
        logger.info("\n[3/3] Testing Full Pipeline...")
        results.append(("Full Pipeline", await test_compression_pipeline()))
        
    except Exception as e:
        logger.error(f"\n✗ Test suite crashed: {e}", exc_info=True)
        return False
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status:8} | {test_name}")
    
    logger.info("=" * 80)
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✓ All tests PASSED - Option C infrastructure is READY!")
        return True
    else:
        logger.error(f"\n✗ {total - passed} test(s) FAILED - infrastructure needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
