#!/usr/bin/env python3
"""
Test API Connection — Verify desktop UI can connect to Go API.

Run the Go API server first:
    cd src/api && go run main.go

Then run this script:
    python scripts/test_api_connection.py
"""

import sys
from pathlib import Path

# Add desktop-ui to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "desktop-ui"))

from api.client import SigmaVaultAPIClient

# Check if API is on alternate port (12080 if 3000 is occupied)
API_URL = "http://localhost:12080"


def test_health():
    """Test basic health endpoint."""
    client = SigmaVaultAPIClient(base_url=API_URL)
    print("Testing /api/v1/health...")
    result = client.get_health()
    if result:
        print(f"  ✓ Status: {result.get('status')}, Version: {result.get('version')}")
        return True
    else:
        print("  ✗ Failed to connect")
        return False


def test_info():
    """Test info endpoint."""
    client = SigmaVaultAPIClient(base_url=API_URL)
    print("\nTesting /api/v1/info...")
    result = client.get_info()
    if result:
        print(f"  ✓ Go version: {result.get('go_version')}")
        print(f"    Uptime: {result.get('uptime_seconds')}s")
        print(f"    Goroutines: {result.get('num_goroutine')}")
        return True
    else:
        print("  ✗ Failed to fetch info")
        return False


def test_agents():
    """Test agents endpoint (requires auth in production)."""
    client = SigmaVaultAPIClient(base_url=API_URL)
    print("\nTesting /api/v1/agents...")
    result = client.get_agents()
    if result:
        count = result.get("count", 0)
        active = result.get("active_count", 0)
        idle = result.get("idle_count", 0)
        print(f"  ✓ Agents: {count} total, {active} active, {idle} idle")
        if "agents" in result:
            for agent in result["agents"][:3]:  # Show first 3
                print(f"    - {agent.get('name')}: {agent.get('status')}")
        return True
    else:
        print("  ✗ Failed to fetch agents (may require login)")
        return False


def test_system_status():
    """Test system status endpoint."""
    client = SigmaVaultAPIClient(base_url=API_URL)
    print("\nTesting /api/v1/system/status...")
    result = client.get_system_status()
    if result:
        print(f"  ✓ Hostname: {result.get('hostname', 'N/A')}")
        uptime = result.get('uptime')
        print(f"    Uptime: {uptime if uptime is not None else 'N/A'}")
        cpu = result.get('cpu_usage')
        print(f"    CPU: {f'{cpu:.1f}%' if cpu is not None else 'N/A'}")
        mem = result.get('memory_use_pct')
        print(f"    Memory: {f'{mem:.1f}%' if mem is not None else 'N/A'}")
        return True
    else:
        print("  ✗ Failed to fetch system status")
        return False


def test_storage():
    """Test storage endpoints."""
    client = SigmaVaultAPIClient(base_url=API_URL)
    print("\nTesting /api/v1/storage/pools...")
    result = client.get_pools()
    if result:
        pools = result.get("pools", [])
        print(f"  ✓ Pools: {len(pools)}")
        for pool in pools:
            print(f"    - {pool.get('name')}: {pool.get('health')}")
        return True
    else:
        print("  ✗ Failed to fetch pools")
        return False


def test_compression():
    """Test compression endpoints."""
    client = SigmaVaultAPIClient(base_url=API_URL)
    print("\nTesting /api/v1/compression/jobs...")
    result = client.get_compression_jobs()
    if result:
        jobs = result.get("jobs", [])
        print(f"  ✓ Jobs: {len(jobs)}")
        return True
    else:
        print("  ✗ Failed to fetch compression jobs")
        return False


def main():
    print("=" * 60)
    print("SigmaVault Desktop UI → Go API Connection Test")
    print("=" * 60)
    print("\nMake sure the Go API is running: cd src/api && go run main.go\n")

    results = []
    
    # Public endpoints (no auth required)
    results.append(("Health", test_health()))
    results.append(("System Info", test_info()))
    
    # Protected endpoints (may fail if auth is required)
    results.append(("Agents", test_agents()))
    results.append(("System Status", test_system_status()))
    results.append(("Storage", test_storage()))
    results.append(("Compression", test_compression()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Desktop UI can connect to Go API.")
        return 0
    elif passed >= 2:
        print("\n⚠ Some tests failed (protected endpoints may require auth).")
        return 0
    else:
        print("\n✗ Connection failed. Is the Go API running?")
        return 1


if __name__ == "__main__":
    sys.exit(main())
