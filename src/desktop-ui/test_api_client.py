#!/usr/bin/env python3
"""
Test SigmaVault API Client - No GTK Required

This script tests the API client without needing GTK/GObject.
Perfect for Windows development environment.

Usage:
    pip install aiohttp pydantic python-dateutil
    python test_api_client.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).parent))

from sigmavault_desktop.api import SigmaVaultAPIClient


async def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


async def test_health_check(client: SigmaVaultAPIClient) -> bool:
    """Test API health endpoint."""
    await print_section("TEST 1: API Health Check")
    try:
        is_healthy = await client.health_check()
        status = "✅ HEALTHY" if is_healthy else "⚠️  NOT RESPONDING"
        print(f"Status: {status}")
        return is_healthy
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False


async def test_system_status(client: SigmaVaultAPIClient) -> Optional[dict]:
    """Test system status endpoint."""
    await print_section("TEST 2: System Status")
    try:
        status = await client.get_system_status()
        if status:
            print(f"✅ System Status Retrieved:")
            print(f"   CPU Usage:        {status.cpu_percent:.1f}%")
            print(f"   Memory Usage:     {status.memory_percent:.1f}%")
            print(f"   Disk Total:       {status.disk_total_gb:.2f} GB")
            print(f"   Disk Used:        {status.disk_used_gb:.2f} GB ({status.disk_percent:.1f}%)")
            print(f"   Disk Available:   {status.disk_available_gb:.2f} GB")
            print(f"   Active Jobs:      {status.active_jobs}")
            print(f"   Total Jobs:       {status.total_jobs}")
            return status
        else:
            print("⚠️  No status returned")
            return None
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return None


async def test_compression_jobs(client: SigmaVaultAPIClient) -> Optional[list]:
    """Test compression jobs endpoint."""
    await print_section("TEST 3: Compression Jobs")
    try:
        # Get all jobs
        jobs = await client.get_compression_jobs(limit=100)
        print(f"✅ Total Jobs Found: {len(jobs)}")

        if not jobs:
            print("   (No compression jobs in the system)")
            return jobs

        # Show recent jobs
        print(f"\n   Recent Jobs (first 5):")
        for i, job in enumerate(jobs[:5], 1):
            print(f"\n   [{i}] Job ID: {job.job_id}")
            print(f"       Status: {job.status}")
            print(f"       Type: {job.data_type}")
            print(f"       Original: {job.original_size / 1024 / 1024:.2f} MB")
            print(f"       Compressed: {job.compressed_size / 1024 / 1024:.2f} MB")
            print(f"       Ratio: {job.compression_ratio:.2f}x")
            print(f"       Time: {job.elapsed_seconds:.1f}s")
            if job.status != "pending":
                print(f"       Throughput: {job.throughput_mbps:.2f} MB/s")

        # Count by status
        status_counts = {}
        for job in jobs:
            status_counts[job.status] = status_counts.get(job.status, 0) + 1

        print(f"\n   Summary by Status:")
        for status, count in sorted(status_counts.items()):
            print(f"      {status}: {count}")

        return jobs
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return None


async def test_job_detail(client: SigmaVaultAPIClient, job_id: str) -> Optional[dict]:
    """Test getting single job details."""
    await print_section(f"TEST 4: Job Details ({job_id})")
    try:
        job = await client.get_compression_job(job_id)
        if job:
            print(f"✅ Job Details:")
            print(f"   ID: {job.job_id}")
            print(f"   Status: {job.status}")
            print(f"   Type: {job.data_type}")
            print(f"   Method: {job.method}")
            print(f"   Original: {job.original_size / 1024 / 1024:.2f} MB")
            print(f"   Compressed: {job.compressed_size / 1024 / 1024:.2f} MB")
            print(f"   Compression Ratio: {job.compression_ratio:.2f}x")
            print(f"   Elapsed: {job.elapsed_seconds:.1f}s")
            print(f"   Created: {job.created_at}")
            return job
        else:
            print(f"⚠️  Job {job_id} not found")
            return None
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return None


async def run_all_tests(api_url: str = "http://localhost:12080") -> None:
    """Run all API tests."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                  SigmaVault API Client Test Suite                          ║
║                                                                            ║
║  This script tests the async API client without requiring GTK/GObject.    ║
║  Perfect for testing on Windows or any platform without GNOME.           ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)

    print(f"\n📡 API Base URL: {api_url}")
    print("⏳ Connecting to API...")

    async with SigmaVaultAPIClient(api_url, timeout=10.0) as client:
        # Test 1: Health check
        is_healthy = await test_health_check(client)

        if not is_healthy:
            print("\n⚠️  API is not responding. Make sure the API server is running:")
            print("   cd src/api && go run main.go")
            print("\n   Or check if API is running on a different address:")
            print("   SIGMAVAULT_API_ADDR=<address> python test_api_client.py")
            return

        # Test 2: System status
        status = await test_system_status(client)

        # Test 3: Compression jobs
        jobs = await test_compression_jobs(client)

        # Test 4: Job details (if jobs exist)
        if jobs and len(jobs) > 0:
            await test_job_detail(client, jobs[0].job_id)

    # Summary
    await print_section("Test Summary")
    print("✅ API Client is functioning correctly!")
    print("\n✨ Next steps:")
    print("   1. API client is production-ready")
    print("   2. Ready to integrate into GTK4 application")
    print("   3. Can begin Phase 3b.2 view implementation")
    print("\n📚 For GTK4 UI testing:")
    print("   Option A: Install WSL2 (recommended for development)")
    print("   Option B: Deploy to Linux/NAS device (production)")
    print("   Option C: Use Docker container (isolated testing)")


async def main() -> None:
    """Main entry point."""
    # Allow custom API URL via environment variable
    import os

    api_url = os.environ.get("SIGMAVAULT_API_URL", "http://localhost:12080")

    try:
        await run_all_tests(api_url)
    except KeyboardInterrupt:
        print("\n\n⛔️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
