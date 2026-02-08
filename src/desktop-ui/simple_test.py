#!/usr/bin/env python3
"""Minimal test to verify API connectivity without full imports."""

import asyncio
import sys
from typing import Optional


async def test_api_health():
    """Test basic API health check."""
    try:
        import aiohttp

        print("✅ aiohttp available")
    except ImportError as e:
        print(f"❌ aiohttp not available: {e}")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:12080/health", timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                if resp.status == 200:
                    print(f"✅ API Health Check: {resp.status} OK")
                    data = await resp.json()
                    print(f"   Response: {data}")
                    return True
                else:
                    print(f"⚠️  API returned: {resp.status}")
                    return False
    except asyncio.TimeoutError:
        print("❌ API connection timeout")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run test."""
    print("=" * 70)
    print("SigmaVault API - Minimal Connectivity Test")
    print("=" * 70)
    result = await test_api_health()
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
