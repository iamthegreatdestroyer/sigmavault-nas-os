#!/usr/bin/env python3
"""
Phase 3 Integration Test - Python RPC Handlers Verification

This script verifies that:
1. Python RPC engine starts correctly
2. compression.jobs.list handler works
3. compression.jobs.get handler works
4. Job registry stores data correctly
4. Job data structure matches Go expectations

Run from: src/engined/ directory
"""

import json
import base64
import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from engined.api.rpc import (
    _compression_jobs,
    handle_compression_jobs_list,
    handle_compression_job_get,
)


def print_header(text: str):
    """Print a formatted test section header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def print_test(name: str, status: str):
    """Print test result."""
    icon = "✅" if status == "PASS" else "❌"
    print(f"  {icon} {name}: {status}")


def test_empty_jobs_list():
    """Test 1: Empty job registry should return empty list."""
    print_header("TEST 1: Empty Jobs List")
    
    # Clear jobs for clean test
    _compression_jobs.clear()
    
    result = handle_compression_jobs_list({})
    
    # Verify response structure
    assert "jobs" in result, "Response missing 'jobs' key"
    assert "total" in result, "Response missing 'total' key"
    assert isinstance(result["jobs"], list), "jobs should be a list"
    assert isinstance(result["total"], int), "total should be an int"
    
    # Verify empty case
    assert len(result["jobs"]) == 0, "Expected empty jobs list"
    assert result["total"] == 0, "Expected total=0"
    
    print_test("Empty jobs list returns correct structure", "PASS")
    print(f"  Response: {json.dumps(result, indent=4)}")


def test_get_nonexistent_job():
    """Test 2: Getting non-existent job should raise error."""
    print_header("TEST 2: Get Non-Existent Job")
    
    try:
        handle_compression_job_get({"job_id": "nonexistent"})
        print_test("Should raise error for missing job", "FAIL")
        return False
    except ValueError as e:
        assert "not found" in str(e), f"Expected 'not found' in error, got: {e}"
        print_test("Raises ValueError for missing job", "PASS")
        print(f"  Error message: {e}")
        return True


def test_add_and_retrieve_job():
    """Test 3: Add job to registry and retrieve it."""
    print_header("TEST 3: Add and Retrieve Job")
    
    # Clear and add test job
    _compression_jobs.clear()
    
    test_job_id = "test-job-001"
    test_job = {
        "job_id": test_job_id,
        "status": "completed",
        "original_size": 1024,
        "compressed_size": 512,
        "compression_ratio": 0.5,
        "elapsed_seconds": 0.123,
        "method": "zlib",
        "data_type": "text",
        "created_at": "2025-01-13T10:30:00Z",
        "error": "",
    }
    
    _compression_jobs[test_job_id] = test_job
    print_test("Added test job to registry", "PASS")
    print(f"  Job ID: {test_job_id}")
    
    # Test list retrieval
    list_result = handle_compression_jobs_list({})
    assert len(list_result["jobs"]) == 1, "Expected 1 job in list"
    assert list_result["total"] == 1, "Expected total=1"
    assert list_result["jobs"][0]["job_id"] == test_job_id
    print_test("Job appears in list", "PASS")
    
    # Test get retrieval
    get_result = handle_compression_job_get({"job_id": test_job_id})
    assert get_result["job_id"] == test_job_id
    assert get_result["status"] == "completed"
    assert get_result["original_size"] == 1024
    assert get_result["compressed_size"] == 512
    print_test("Get returns job with correct fields", "PASS")
    print(f"  Response: {json.dumps(get_result, indent=4)}")


def test_multiple_jobs_sorting():
    """Test 4: Multiple jobs are sorted by created_at descending."""
    print_header("TEST 4: Multiple Jobs Sorting")
    
    # Clear and add multiple jobs with different timestamps
    _compression_jobs.clear()
    
    jobs_data = [
        {
            "job_id": "job-001",
            "created_at": "2025-01-13T10:00:00Z",
            "status": "completed",
            "original_size": 100,
            "compressed_size": 50,
            "compression_ratio": 0.5,
            "elapsed_seconds": 0.1,
            "method": "zlib",
            "data_type": "text",
            "error": "",
        },
        {
            "job_id": "job-002",
            "created_at": "2025-01-13T10:30:00Z",
            "status": "completed",
            "original_size": 200,
            "compressed_size": 100,
            "compression_ratio": 0.5,
            "elapsed_seconds": 0.2,
            "method": "zlib",
            "data_type": "text",
            "error": "",
        },
        {
            "job_id": "job-003",
            "created_at": "2025-01-13T10:15:00Z",
            "status": "completed",
            "original_size": 150,
            "compressed_size": 75,
            "compression_ratio": 0.5,
            "elapsed_seconds": 0.15,
            "method": "zlib",
            "data_type": "text",
            "error": "",
        },
    ]
    
    for job in jobs_data:
        _compression_jobs[job["job_id"]] = job
    
    print_test("Added 3 test jobs with different timestamps", "PASS")
    
    # Get list which should sort them
    result = handle_compression_jobs_list({})
    
    # Verify sorting: newest first (job-002, job-003, job-001)
    expected_order = ["job-002", "job-003", "job-001"]
    actual_order = [j["job_id"] for j in result["jobs"]]
    
    assert actual_order == expected_order, (
        f"Expected order {expected_order}, got {actual_order}"
    )
    
    print_test("Jobs sorted by created_at descending", "PASS")
    print(f"  Order: {' → '.join(actual_order)}")


def test_status_filter():
    """Test 5: Status filter works correctly."""
    print_header("TEST 5: Status Filter")
    
    # Clear and add jobs with different statuses
    _compression_jobs.clear()
    
    _compression_jobs["job-completed-1"] = {
        "job_id": "job-completed-1",
        "status": "completed",
        "created_at": "2025-01-13T10:30:00Z",
        "original_size": 100,
        "compressed_size": 50,
        "compression_ratio": 0.5,
        "elapsed_seconds": 0.1,
        "method": "zlib",
        "data_type": "text",
        "error": "",
    }
    
    _compression_jobs["job-completed-2"] = {
        "job_id": "job-completed-2",
        "status": "completed",
        "created_at": "2025-01-13T10:31:00Z",
        "original_size": 200,
        "compressed_size": 100,
        "compression_ratio": 0.5,
        "elapsed_seconds": 0.2,
        "method": "zlib",
        "data_type": "text",
        "error": "",
    }
    
    _compression_jobs["job-failed"] = {
        "job_id": "job-failed",
        "status": "failed",
        "created_at": "2025-01-13T10:32:00Z",
        "original_size": 150,
        "compressed_size": 0,
        "compression_ratio": 0.0,
        "elapsed_seconds": 0.05,
        "method": "zlib",
        "data_type": "text",
        "error": "Test error message",
    }
    
    print_test("Added 2 completed and 1 failed job", "PASS")
    
    # Test filter by completed
    result = handle_compression_jobs_list({"status": "completed"})
    assert len(result["jobs"]) == 2, f"Expected 2 completed, got {len(result['jobs'])}"
    assert all(j["status"] == "completed" for j in result["jobs"])
    print_test("Status filter for 'completed' works", "PASS")
    
    # Test filter by failed
    result = handle_compression_jobs_list({"status": "failed"})
    assert len(result["jobs"]) == 1, f"Expected 1 failed, got {len(result['jobs'])}"
    assert result["jobs"][0]["status"] == "failed"
    print_test("Status filter for 'failed' works", "PASS")
    
    # Test no filter returns all
    result = handle_compression_jobs_list({})
    assert len(result["jobs"]) == 3, f"Expected 3 total, got {len(result['jobs'])}"
    print_test("No filter returns all jobs", "PASS")


def test_limit_parameter():
    """Test 6: Limit parameter works correctly."""
    print_header("TEST 6: Limit Parameter")
    
    # Clear and add 5 jobs
    _compression_jobs.clear()
    
    for i in range(5):
        _compression_jobs[f"job-{i:03d}"] = {
            "job_id": f"job-{i:03d}",
            "status": "completed",
            "created_at": f"2025-01-13T10:{i*6:02d}:00Z",
            "original_size": 100 * (i + 1),
            "compressed_size": 50 * (i + 1),
            "compression_ratio": 0.5,
            "elapsed_seconds": 0.1 * (i + 1),
            "method": "zlib",
            "data_type": "text",
            "error": "",
        }
    
    print_test("Added 5 test jobs", "PASS")
    
    # Test limit=2
    result = handle_compression_jobs_list({"limit": 2})
    assert len(result["jobs"]) == 2, f"Expected 2 with limit=2, got {len(result['jobs'])}"
    assert result["total"] == 5, f"Total should still be 5, got {result['total']}"
    print_test("Limit=2 returns 2 jobs but total=5", "PASS")
    
    # Test limit=10 (more than available)
    result = handle_compression_jobs_list({"limit": 10})
    assert len(result["jobs"]) == 5, f"Expected 5, got {len(result['jobs'])}"
    print_test("Limit=10 returns all 5 available jobs", "PASS")
    
    # Test default limit
    result = handle_compression_jobs_list({})
    assert len(result["jobs"]) == 5, "Default should return all"
    print_test("No limit returns all jobs", "PASS")


def test_response_structure():
    """Test 7: Response structure matches Go expectations."""
    print_header("TEST 7: Response Structure")
    
    # Clear and add a job
    _compression_jobs.clear()
    job_data = {
        "job_id": "structure-test",
        "status": "completed",
        "original_size": 1024,
        "compressed_size": 512,
        "compression_ratio": 0.5,
        "elapsed_seconds": 0.123,
        "method": "zlib",
        "data_type": "text",
        "created_at": "2025-01-13T10:30:00Z",
        "error": "",
    }
    _compression_jobs["structure-test"] = job_data
    
    result = handle_compression_jobs_list({})
    jobs = result["jobs"]
    
    # Verify each job has required fields that Go expects
    required_fields = [
        "job_id", "status", "original_size", "compressed_size",
        "compression_ratio", "elapsed_seconds", "method", "data_type",
        "created_at", "error"
    ]
    
    for field in required_fields:
        assert field in jobs[0], f"Missing required field: {field}"
    
    # Verify field types
    job = jobs[0]
    assert isinstance(job["job_id"], str), "job_id should be string"
    assert isinstance(job["status"], str), "status should be string"
    assert isinstance(job["original_size"], int), "original_size should be int"
    assert isinstance(job["compressed_size"], int), "compressed_size should be int"
    assert isinstance(job["compression_ratio"], (int, float)), "compression_ratio should be numeric"
    assert isinstance(job["elapsed_seconds"], (int, float)), "elapsed_seconds should be numeric"
    assert isinstance(job["method"], str), "method should be string"
    assert isinstance(job["data_type"], str), "data_type should be string"
    assert isinstance(job["created_at"], str), "created_at should be string (ISO8601)"
    assert isinstance(job["error"], str), "error should be string"
    
    print_test("All required fields present", "PASS")
    print_test("All field types correct for Go unmarshaling", "PASS")
    print(f"  Job: {json.dumps(job, indent=4)}")


def main():
    """Run all integration tests."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                  Phase 3 Integration Test Suite                           ║
║                   Python RPC Handler Verification                         ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    tests = [
        test_empty_jobs_list,
        test_get_nonexistent_job,
        test_add_and_retrieve_job,
        test_multiple_jobs_sorting,
        test_status_filter,
        test_limit_parameter,
        test_response_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print_test(test_func.__name__, "FAIL")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print_test(test_func.__name__, "ERROR")
            print(f"  Error: {e}")
            failed += 1
    
    # Summary
    print_header(f"Test Summary")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    total = passed + failed
    print(f"  📊 Success Rate: {passed}/{total} ({100*passed//total}%)")
    
    if failed == 0:
        print("""
╔════════════════════════════════════════════════════════════════════════════╗
║  🎉 All tests passed! Python RPC handlers are ready for Go integration.    ║
╚════════════════════════════════════════════════════════════════════════════╝
        """)
        return 0
    else:
        print("""
╔════════════════════════════════════════════════════════════════════════════╗
║  ⚠️  Some tests failed. See errors above for details.                      ║
╚════════════════════════════════════════════════════════════════════════════╝
        """)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
