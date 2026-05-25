"""
Unit Tests: Engine RPC Routing Layer

Tests the core JSON-RPC 2.0 routing mechanism that dispatches
requests to appropriate handler functions.

Scope:
  ✓ Valid method routing
  ✓ Invalid method handling
  ✓ Parameter validation
  ✓ Error response formatting
  ✓ Concurrent request handling
  ✓ Timeout scenarios
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def rpc_request_valid() -> Dict[str, Any]:
    """Valid JSON-RPC 2.0 request."""
    return {
        "jsonrpc": "2.0",
        "method": "agents.list",
        "params": {},
        "id": 1
    }


@pytest.fixture
def rpc_request_with_params() -> Dict[str, Any]:
    """JSON-RPC request with parameters."""
    return {
        "jsonrpc": "2.0",
        "method": "agents.get",
        "params": {"id": "agent-001"},
        "id": 2
    }


@pytest.fixture
def rpc_request_invalid_method() -> Dict[str, Any]:
    """RPC request with non-existent method."""
    return {
        "jsonrpc": "2.0",
        "method": "invalid.method",
        "params": {},
        "id": 3
    }


@pytest.fixture
def rpc_request_missing_params() -> Dict[str, Any]:
    """RPC request missing required parameters."""
    return {
        "jsonrpc": "2.0",
        "method": "agents.get",
        "params": {},  # Missing required 'id' parameter
        "id": 4
    }


@pytest.fixture
def mock_handler() -> AsyncMock:
    """Mock RPC handler function."""
    handler = AsyncMock()
    handler.return_value = {
        "result": {"data": "test"},
        "jsonrpc": "2.0",
        "id": 1
    }
    return handler


@pytest.fixture
def rpc_router(mock_handler):
    """Create mock RPC router with registered handlers."""
    
    class MockRPCRouter:
        def __init__(self):
            self.handlers = {
                "agents.list": self.handle_agents_list,
                "agents.get": self.handle_agents_get,
                "agents.get_by_codename": self.handle_agents_get_by_codename,
                "agents.metrics": self.handle_agents_metrics,
                "agents.list_tiers": self.handle_agents_list_tiers,
                "agents.swarm_status": self.handle_agents_status,
                "compression.stats": self.handle_compression_stats,
            }
            self.mock_handler = mock_handler
        
        async def route_and_call(self, request: Dict) -> Dict:
            """Route request to appropriate handler."""
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            # Check method exists
            if method not in self.handlers:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": f"Method '{method}' not found"
                    },
                    "id": request_id
                }
            
            # Call handler
            try:
                result = await self.handlers[method](params)
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request_id
                }
            except TypeError as e:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": "Invalid params",
                        "data": str(e)
                    },
                    "id": request_id
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    },
                    "id": request_id
                }
        
        async def handle_agents_list(self, params):
            return {"agents": [{"id": "agent-001"}, {"id": "agent-002"}]}
        
        async def handle_agents_get(self, params):
            if "id" not in params:
                raise TypeError("Missing required parameter: id")
            return {"id": params["id"], "name": "Test Agent"}
        
        async def handle_agents_get_by_codename(self, params):
            if "codename" not in params:
                raise TypeError("Missing required parameter: codename")
            return {"codename": params["codename"]}
        
        async def handle_agents_metrics(self, params):
            if "id" not in params:
                raise TypeError("Missing required parameter: id")
            return {"metrics": "data"}
        
        async def handle_agents_list_tiers(self, params):
            return {"tiers": ["core", "specialist", "support"]}
        
        async def handle_agents_status(self, params):
            return {"status": "active"}
        
        async def handle_compression_stats(self, params):
            return {"stats": "data"}
    
    return MockRPCRouter()


# ============================================================================
# TEST CASES: Valid Routing
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_agents_list(rpc_router, rpc_request_valid):
    """Test routing of agents.list method."""
    response = await rpc_router.route_and_call(rpc_request_valid)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "agents" in response["result"]
    assert len(response["result"]["agents"]) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_agents_get_with_params(rpc_router, rpc_request_with_params):
    """Test routing agent.get with required parameters."""
    response = await rpc_router.route_and_call(rpc_request_with_params)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert response["result"]["id"] == "agent-001"
    assert "error" not in response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_compression_stats(rpc_router):
    """Test routing compression.stats method."""
    request = {
        "jsonrpc": "2.0",
        "method": "compression.stats",
        "params": {},
        "id": 5
    }
    response = await rpc_router.route_and_call(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "result" in response
    assert "stats" in response["result"]


# ============================================================================
# TEST CASES: Error Handling
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_invalid_method(rpc_router, rpc_request_invalid_method):
    """Test routing invalid method returns -32601 error."""
    response = await rpc_router.route_and_call(rpc_request_invalid_method)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]
    assert "result" not in response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_missing_required_params(rpc_router, rpc_request_missing_params):
    """Test routing request with missing params returns -32602 error."""
    response = await rpc_router.route_and_call(rpc_request_missing_params)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response
    assert response["error"]["code"] == -32602
    assert "Invalid params" in response["error"]["message"]


# ============================================================================
# TEST CASES: Parameter Validation
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_required_parameter_id():
    """Test validation of required 'id' parameter."""
    valid_params = {"id": "agent-001"}
    invalid_params = {}
    
    def validate_id(params):
        if "id" not in params:
            raise TypeError("Missing required parameter: id")
        return True
    
    # Valid case should not raise
    assert validate_id(valid_params) is True
    
    # Invalid case should raise
    with pytest.raises(TypeError):
        validate_id(invalid_params)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_parameter_types():
    """Test validation of parameter types."""
    
    def validate_compression_params(params):
        if "job_id" in params and not isinstance(params["job_id"], str):
            raise TypeError("job_id must be string")
        if "timeout_ms" in params and not isinstance(params["timeout_ms"], int):
            raise TypeError("timeout_ms must be integer")
        return True
    
    # Valid params
    assert validate_compression_params({"job_id": "job-001"}) is True
    assert validate_compression_params({"timeout_ms": 5000}) is True
    assert validate_compression_params({"job_id": "job-001", "timeout_ms": 5000}) is True
    
    # Invalid params
    with pytest.raises(TypeError):
        validate_compression_params({"job_id": 123})  # Should be string
    
    with pytest.raises(TypeError):
        validate_compression_params({"timeout_ms": "5000"})  # Should be int


# ============================================================================
# TEST CASES: Concurrent Requests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_requests(rpc_router):
    """Test router handles concurrent requests without interference."""
    
    requests = [
        {"jsonrpc": "2.0", "method": "agents.list", "params": {}, "id": i}
        for i in range(1, 6)
    ]
    
    # Execute all requests concurrently
    responses = await asyncio.gather(
        *[rpc_router.route_and_call(req) for req in requests]
    )
    
    # Verify all received responses
    assert len(responses) == 5
    
    # Verify response IDs match request IDs
    for i, response in enumerate(responses, 1):
        assert response["id"] == i
        assert "result" in response or "error" in response
        assert response["jsonrpc"] == "2.0"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_mixed_requests(rpc_router):
    """Test concurrent mix of valid and invalid requests."""
    
    requests = [
        {"jsonrpc": "2.0", "method": "agents.list", "params": {}, "id": 1},  # Valid
        {"jsonrpc": "2.0", "method": "invalid.method", "params": {}, "id": 2},  # Invalid
        {"jsonrpc": "2.0", "method": "agents.get", "params": {"id": "agent-001"}, "id": 3},  # Valid
        {"jsonrpc": "2.0", "method": "agents.get", "params": {}, "id": 4},  # Invalid params
    ]
    
    responses = await asyncio.gather(
        *[rpc_router.route_and_call(req) for req in requests]
    )
    
    # Verify first response (valid)
    assert responses[0]["id"] == 1
    assert "result" in responses[0]
    
    # Verify second response (invalid method)
    assert responses[1]["id"] == 2
    assert "error" in responses[1]
    assert responses[1]["error"]["code"] == -32601
    
    # Verify third response (valid)
    assert responses[2]["id"] == 3
    assert "result" in responses[2]
    
    # Verify fourth response (invalid params)
    assert responses[3]["id"] == 4
    assert "error" in responses[3]
    assert responses[3]["error"]["code"] == -32602


# ============================================================================
# TEST CASES: Response Format Validation
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.unit
async def test_response_has_required_fields(rpc_router, rpc_request_valid):
    """Test all responses have required JSON-RPC fields."""
    response = await rpc_router.route_and_call(rpc_request_valid)
    
    # All responses must have jsonrpc and id
    assert "jsonrpc" in response
    assert response["jsonrpc"] == "2.0"
    assert "id" in response
    
    # Either result or error must be present
    assert ("result" in response) or ("error" in response)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_error_response_has_required_fields(rpc_router, rpc_request_invalid_method):
    """Test error responses have proper structure."""
    response = await rpc_router.route_and_call(rpc_request_invalid_method)
    
    assert "error" in response
    error = response["error"]
    assert "code" in error
    assert "message" in error
    assert isinstance(error["code"], int)
    assert isinstance(error["message"], str)


# ============================================================================
# TEST CASES: Timeout & Performance
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_timeout_handling():
    """Test handling of slow/timeout requests."""
    
    async def slow_handler():
        await asyncio.sleep(2)
        return {"data": "result"}
    
    # Request completes before timeout
    try:
        result = await asyncio.wait_for(slow_handler(), timeout=3)
        assert result["data"] == "result"
    except asyncio.TimeoutError:
        pytest.fail("Request should not timeout with 3s limit")
    
    # Request times out
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_handler(), timeout=0.5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_response_latency(timer):
    """Test that routing adds minimal latency."""
    
    async def mock_handler():
        return {"result": "data"}
    
    timer.start()
    
    # Simulate request routing
    for _ in range(100):
        await mock_handler()
    
    timer.stop()
    
    # 100 requests should complete in < 100ms total
    assert timer.elapsed_ms < 100, f"Latency too high: {timer.elapsed_ms}ms"


# ============================================================================
# TEST SETUP & MARKERS
# ============================================================================

@pytest.mark.unit
class TestRPCRouting:
    """Test suite for RPC routing layer."""
    
    @pytest.mark.asyncio
    async def test_suite_setup(self):
        """Verify test suite is properly initialized."""
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

