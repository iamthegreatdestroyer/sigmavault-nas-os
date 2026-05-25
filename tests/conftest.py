"""
Pytest Configuration & Shared Fixtures

This module provides:
- Pytest configuration (markers, logging)
- Shared fixtures (Engine mock, API mock, agents)
- Test utilities and helpers
- Performance benchmarking setup
"""

import pytest
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
import logging


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_services: mark test as requiring running services"
    )


# ============================================================================
# LOGGING FIXTURES
# ============================================================================

@pytest.fixture
def caplog_setup():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


# ============================================================================
# EVENT LOOP FIXTURE
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    
    yield loop
    loop.close()


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def agent_data() -> Dict[str, Any]:
    """Load test agent data from fixture."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "fixtures/agents_data.json"
    )
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def compression_jobs() -> Dict[str, Any]:
    """Load test compression job data from fixture."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "fixtures/compression_jobs.json"
    )
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def test_agent_list() -> list:
    """Return sample agent data for testing."""
    return [
        {
            "id": f"agent-{str(i).zfill(3)}",
            "codename": ["TENSOR", "CIPHER", "ARCHITECT", "FLUX"][i % 4],
            "tier": ["core", "specialist", "support"][i % 3],
            "status": "active",
            "tasks_completed": (i + 1) * 100,
            "success_rate": 0.95 + (i % 5) * 0.01,
            "avg_response_time_ms": 50 + (i % 100),
        }
        for i in range(40)
    ]


@pytest.fixture
def test_compression_job() -> Dict[str, Any]:
    """Return sample compression job data."""
    return {
        "job_id": "job-001",
        "source_size_bytes": 1000000,
        "status": "running",
        "progress_percent": 45,
        "created_at": datetime.utcnow().isoformat(),
        "estimated_completion_ms": 5000,
    }


# ============================================================================
# ENGINE MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_engine_response() -> AsyncMock:
    """Create mock Engine RPC response."""
    mock = AsyncMock()
    mock.return_value = {"result": {"data": "test"}, "jsonrpc": "2.0", "id": 1}
    return mock


@pytest.fixture
def mock_rpc_client() -> Mock:
    """Create mock JSON-RPC client."""
    client = Mock()
    client.call = AsyncMock()
    client.call.return_value = {"result": {}, "jsonrpc": "2.0", "id": 1}
    return client


# ============================================================================
# GO API MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_http_response() -> Mock:
    """Create mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.json = Mock(return_value={"status": "success"})
    response.text = '{"status": "success"}'
    return response


@pytest.fixture
def mock_api_client() -> Mock:
    """Create mock API HTTP client."""
    client = Mock()
    client.get = Mock(return_value=Mock(status_code=200, json=lambda: {}))
    client.post = Mock(return_value=Mock(status_code=201, json=lambda: {}))
    client.request = AsyncMock()
    return client


# ============================================================================
# PERFORMANCE FIXTURES
# ============================================================================

@pytest.fixture
def benchmark_baseline() -> Dict[str, float]:
    """Load baseline performance metrics."""
    baseline_path = os.path.join(
        os.path.dirname(__file__),
        "../benchmarks/baseline.json"
    )
    
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r') as f:
            return json.load(f)
    
    # Default baseline if no file exists
    return {
        "rpc_latency_p50_ms": 50,
        "rpc_latency_p95_ms": 100,
        "rpc_latency_p99_ms": 200,
        "rpc_throughput_rps": 1000,
        "api_latency_p50_ms": 60,
        "api_latency_p95_ms": 150,
        "api_latency_p99_ms": 300,
        "api_throughput_rps": 500,
    }


@pytest.fixture
def timer():
    """Provide simple timer utility for performance measurement."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            import time
            self.start_time = time.time()
        
        def stop(self):
            import time
            self.end_time = time.time()
        
        @property
        def elapsed_ms(self) -> float:
            if not self.start_time or not self.end_time:
                return 0
            return (self.end_time - self.start_time) * 1000
    
    return Timer()


# ============================================================================
# ERROR SCENARIO FIXTURES
# ============================================================================

@pytest.fixture
def json_rpc_error() -> Dict[str, Any]:
    """JSON-RPC error response template."""
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": -32600,
            "message": "Invalid Request",
            "data": None
        },
        "id": None
    }


@pytest.fixture
def standard_errors():
    """Dictionary of standard error codes and messages."""
    return {
        -32700: "Parse error",
        -32600: "Invalid Request",
        -32601: "Method not found",
        -32602: "Invalid params",
        -32603: "Internal error",
        -32000: "Server error",
    }


# ============================================================================
# UTILITY FIXTURES & HELPERS
# ============================================================================

@pytest.fixture
def temp_test_file(tmp_path):
    """Create temporary test file."""
    test_file = tmp_path / "test_data.json"
    test_file.write_text(json.dumps({"test": "data"}))
    return test_file


@pytest.fixture
def assert_valid_rpc_response():
    """Fixture for asserting valid JSON-RPC response structure."""
    def _assert(response: Dict) -> None:
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        # Either result or error should be present, not both
        has_result = "result" in response
        has_error = "error" in response
        assert has_result or has_error
        assert not (has_result and has_error)
    
    return _assert


@pytest.fixture
def assert_valid_http_response():
    """Fixture for asserting valid HTTP response structure."""
    def _assert(response: Dict, expected_status: int = 200) -> None:
        assert hasattr(response, 'status_code')
        assert response.status_code == expected_status
        assert hasattr(response, 'json')
        if response.status_code < 400:
            assert "data" in response.json() or "result" in response.json()
    
    return _assert


# ============================================================================
# SERVICE INTEGRATION FIXTURES
# ============================================================================

@pytest.fixture
def engine_url() -> str:
    """Get Engine service URL from environment or use default."""
    return os.getenv("ENGINE_URL", "http://localhost:5000")


@pytest.fixture
def api_url() -> str:
    """Get API service URL from environment or use default."""
    return os.getenv("API_URL", "http://localhost:12080")


# ============================================================================
# PYTEST PLUGINS
# ============================================================================

pytest_plugins = [
    "pytest_asyncio",
]


# ============================================================================
# CLEANUP & TEARDOWN
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    # Cleanup happens here
    pass


# ============================================================================
# PARAMETRIZE HELPERS
# ============================================================================

def generate_agent_ids(count: int) -> list:
    """Generate test agent IDs."""
    return [f"agent-{str(i).zfill(3)}" for i in range(count)]


def generate_compression_jobs(count: int) -> list:
    """Generate test compression jobs."""
    return [
        {
            "job_id": f"job-{str(i).zfill(4)}",
            "status": ["queued", "running", "completed", "failed"][i % 4],
            "progress_percent": (i * 10) % 100,
        }
        for i in range(count)
    ]

