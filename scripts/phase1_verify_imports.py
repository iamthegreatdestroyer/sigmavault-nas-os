#!/usr/bin/env python3
"""Phase 1 Verification - Test Python Compression RPC Infrastructure"""

import sys
from pathlib import Path

# Add engined to path
engined_path = Path(__file__).parent.parent / "src" / "engined"
sys.path.insert(0, str(engined_path))

print("\n" + "=" * 80)
print("PHASE 1: PYTHON COMPRESSION RPC VERIFICATION")
print("=" * 80)

# Test 1: Import CompressionBridge
print("\n[TEST 1] Importing CompressionBridge...")
try:
    from engined.compression.bridge import CompressionBridge, CompressionConfig, CompressionLevel
    print("✓ CompressionBridge imported successfully")
    print(f"  - CompressionLevel values: {[e.value for e in CompressionLevel]}")
except Exception as e:
    print(f"✗ Failed to import CompressionBridge: {e}")
    sys.exit(1)

# Test 2: Import CompressionJobQueue
print("\n[TEST 2] Importing CompressionJobQueue...")
try:
    from engined.compression.job_queue import (
        CompressionJobQueue,
        CompressionJob,
        JobStatus,
        JobPriority,
        JobType,
    )
    print("✓ CompressionJobQueue imported successfully")
    print(f"  - JobStatus values: {[e.value for e in JobStatus]}")
    print(f"  - JobPriority values: {[(e.name, e.value) for e in JobPriority]}")
    print(f"  - JobType values: {[e.value for e in JobType]}")
except Exception as e:
    print(f"✗ Failed to import CompressionJobQueue: {e}")
    sys.exit(1)

# Test 3: Import RPC handlers
print("\n[TEST 3] Importing RPC handlers...")
try:
    from engined.api.rpc import (
        handle_compress_data,
        handle_compress_file,
        handle_decompress_data,
        handle_decompress_file,
        handle_queue_submit,
        handle_queue_status,
        handle_get_compression_config,
    )
    print("✓ All RPC handlers imported successfully")
    print("  - handle_compress_data")
    print("  - handle_compress_file")
    print("  - handle_decompress_data")
    print("  - handle_decompress_file")
    print("  - handle_queue_submit")
    print("  - handle_queue_status")
    print("  - handle_get_compression_config")
except Exception as e:
    print(f"✗ Failed to import RPC handlers: {e}")
    sys.exit(1)

# Test 4: Check CompressionBridge class structure
print("\n[TEST 4] Inspecting CompressionBridge class...")
try:
    import inspect
    methods = [m for m in dir(CompressionBridge) if not m.startswith('_')]
    print(f"✓ CompressionBridge has {len(methods)} public methods:")
    for method in methods:
        attr = getattr(CompressionBridge, method)
        if callable(attr):
            print(f"  - {method}()")
except Exception as e:
    print(f"✗ Failed to inspect CompressionBridge: {e}")
    sys.exit(1)

# Test 5: Check dataclass definitions
print("\n[TEST 5] Inspecting dataclass definitions...")
try:
    from dataclasses import fields
    
    print("✓ CompressionJob fields:")
    for field in fields(CompressionJob):
        print(f"  - {field.name}: {field.type}")
except Exception as e:
    print(f"✗ Failed to inspect dataclasses: {e}")
    sys.exit(1)

# Test 6: Try to instantiate CompressionConfig
print("\n[TEST 6] Instantiating CompressionConfig...")
try:
    config = CompressionConfig(level=CompressionLevel.BALANCED)
    print(f"✓ CompressionConfig created:")
    print(f"  - level: {config.level.value}")
    print(f"  - chunk_size: {config.chunk_size:,} bytes")
    print(f"  - use_semantic: {config.use_semantic}")
    print(f"  - lossless: {config.lossless}")
except Exception as e:
    print(f"✗ Failed to instantiate CompressionConfig: {e}")
    sys.exit(1)

# Test 7: Check RPC handler signatures
print("\n[TEST 7] Inspecting RPC handler signatures...")
try:
    import inspect
    
    handlers = {
        "compress_data": handle_compress_data,
        "compress_file": handle_compress_file,
        "decompress_data": handle_decompress_data,
        "decompress_file": handle_decompress_file,
        "queue_submit": handle_queue_submit,
        "queue_status": handle_queue_status,
    }
    
    for name, handler in handlers.items():
        sig = inspect.signature(handler)
        is_async = inspect.iscoroutinefunction(handler)
        print(f"  - {name}: async={is_async}, params={list(sig.parameters.keys())}")
except Exception as e:
    print(f"✗ Failed to inspect handlers: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL VERIFICATION TESTS PASSED")
print("=" * 80)
print("\nPhase 1 Infrastructure Status:")
print("  ✓ CompressionBridge: Ready")
print("  ✓ CompressionJobQueue: Ready")
print("  ✓ RPC Handlers: Ready")
print("  ✓ Dataclasses: Complete")
print("\nREADY TO BEGIN PHASE 1.1: RUNTIME TESTING\n")
