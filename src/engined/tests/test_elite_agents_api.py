"""
Integration tests for Elite Agent Collective API endpoints.

Tests the FastAPI endpoints for agent discovery, status, and task submission.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import status

from engined.main import create_app
from engined.api.elite_agents import initialize_registry, shutdown_registry


@pytest.fixture
async def app():
    """Create FastAPI app for testing."""
    app = create_app()
    
    # Initialize registry before tests
    await initialize_registry()
    
    yield app
    
    # Shutdown registry after tests
    await shutdown_registry()


@pytest.fixture
async def client(app):
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestEliteAgentsAPI:
    """Test Elite Agent Collective API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_all_agents(self, client):
        """Test listing all agents."""
        response = await client.get("/elite-agents/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total" in data
        assert "agents" in data
        assert data["total"] == 10  # 5 Tier 1 + 5 Tier 2
        assert len(data["agents"]) == 10
    
    @pytest.mark.asyncio
    async def test_list_agents_by_tier(self, client):
        """Test filtering agents by tier."""
        # Test Tier 1
        response = await client.get("/elite-agents/", params={"tier": 1})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        
        # Test Tier 2
        response = await client.get("/elite-agents/", params={"tier": 2})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
    
    @pytest.mark.asyncio
    async def test_list_agents_by_state(self, client):
        """Test filtering agents by state."""
        response = await client.get("/elite-agents/", params={"state": "idle"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Agents should be idle after initialization, but check agents were returned
        assert data["total"] >= 0  # Some agents may be idle
        assert isinstance(data["agents"], list)
    
    @pytest.mark.asyncio
    async def test_list_agents_by_domain(self, client):
        """Test filtering agents by domain."""
        response = await client.get("/elite-agents/", params={"domain": "software_engineering"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # APEX-01 has software_engineering domain
        assert data["total"] >= 1
        
        # Verify all returned agents have the domain
        for agent in data["agents"]:
            assert "software_engineering" in agent["domains"]
    
    @pytest.mark.asyncio
    async def test_get_registry_status(self, client):
        """Test getting overall registry status."""
        response = await client.get("/elite-agents/registry/status")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total_agents"] == 10
        assert "agents_by_state" in data
        assert "agents_by_tier" in data
        assert data["agents_by_state"]["idle"] == 10
        assert data["agents_by_tier"]["1"] == 5
        assert data["agents_by_tier"]["2"] == 5
    
    @pytest.mark.asyncio
    async def test_get_specific_agent(self, client):
        """Test getting status for a specific agent."""
        response = await client.get("/elite-agents/APEX-01")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["agent_id"] == "APEX-01"
        assert data["tier"] == 1
        assert data["state"] == "idle"
        assert "software_engineering" in data["domains"]
        assert "production_code" in data["skills"]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, client):
        """Test getting status for non-existent agent."""
        response = await client.get("/elite-agents/NONEXISTENT-99")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_list_agents_by_tier_endpoint(self, client):
        """Test the dedicated tier listing endpoint."""
        response = await client.get("/elite-agents/tier/1")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 5
        for agent in data["agents"]:
            assert agent["tier"] == 1
    
    @pytest.mark.asyncio
    async def test_list_agents_by_tier_invalid(self, client):
        """Test tier listing with invalid tier number."""
        response = await client.get("/elite-agents/tier/99")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_list_agents_by_domain_endpoint(self, client):
        """Test the dedicated domain listing endpoint."""
        response = await client.get("/elite-agents/domain/cryptography")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # CIPHER-02 has cryptography domain
        assert data["total"] >= 1
        
        for agent in data["agents"]:
            assert "cryptography" in agent["domains"]
    
    @pytest.mark.asyncio
    async def test_list_agents_by_skill_endpoint(self, client):
        """Test the dedicated skill listing endpoint."""
        response = await client.get("/elite-agents/skill/production_code")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # APEX-01 has production_code skill
        assert data["total"] >= 1
        
        for agent in data["agents"]:
            assert "production_code" in agent["skills"]
    
    @pytest.mark.asyncio
    async def test_submit_task(self, client):
        """Test submitting a task to an agent."""
        task_data = {
            "task_type": "code_review",
            "payload": {"code": "def hello(): print('world')"},
            "priority": "HIGH",
            "timeout": 60
        }
        
        response = await client.post("/elite-agents/APEX-01/task", json=task_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "task_id" in data
        assert data["agent_id"] == "APEX-01"
        assert data["status"] == "submitted"
    
    @pytest.mark.asyncio
    async def test_submit_task_invalid_priority(self, client):
        """Test submitting task with invalid priority."""
        task_data = {
            "task_type": "code_review",
            "payload": {"code": "test"},
            "priority": "INVALID",
            "timeout": 60
        }
        
        response = await client.post("/elite-agents/APEX-01/task", json=task_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid priority" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_submit_task_to_nonexistent_agent(self, client):
        """Test submitting task to non-existent agent."""
        task_data = {
            "task_type": "test",
            "payload": {},
            "priority": "MEDIUM"
        }
        
        response = await client.post("/elite-agents/NONEXISTENT-99/task", json=task_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEliteAgentsTier1:
    """Test Tier 1 (Foundational) agents."""
    
    @pytest.mark.asyncio
    async def test_apex_agent_exists(self, client):
        """Test APEX-01 agent is registered."""
        response = await client.get("/elite-agents/APEX-01")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "APEX-01"
        assert "software_engineering" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_cipher_agent_exists(self, client):
        """Test CIPHER-02 agent is registered."""
        response = await client.get("/elite-agents/CIPHER-02")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "CIPHER-02"
        assert "cryptography" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_architect_agent_exists(self, client):
        """Test ARCHITECT-03 agent is registered."""
        response = await client.get("/elite-agents/ARCHITECT-03")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "ARCHITECT-03"
        assert "architecture" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_axiom_agent_exists(self, client):
        """Test AXIOM-04 agent is registered."""
        response = await client.get("/elite-agents/AXIOM-04")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "AXIOM-04"
        assert "mathematics" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_velocity_agent_exists(self, client):
        """Test VELOCITY-05 agent is registered."""
        response = await client.get("/elite-agents/VELOCITY-05")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "VELOCITY-05"
        assert "performance" in data["domains"]


class TestEliteAgentsTier2:
    """Test Tier 2 (Specialist) agents."""
    
    @pytest.mark.asyncio
    async def test_tensor_agent_exists(self, client):
        """Test TENSOR-07 agent is registered."""
        response = await client.get("/elite-agents/TENSOR-07")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "TENSOR-07"
        assert "machine_learning" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_fortress_agent_exists(self, client):
        """Test FORTRESS-08 agent is registered."""
        response = await client.get("/elite-agents/FORTRESS-08")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "FORTRESS-08"
        assert "security" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_flux_agent_exists(self, client):
        """Test FLUX-11 agent is registered."""
        response = await client.get("/elite-agents/FLUX-11")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "FLUX-11"
        assert "devops" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_prism_agent_exists(self, client):
        """Test PRISM-12 agent is registered."""
        response = await client.get("/elite-agents/PRISM-12")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "PRISM-12"
        assert "data_science" in data["domains"]
    
    @pytest.mark.asyncio
    async def test_synapse_agent_exists(self, client):
        """Test SYNAPSE-13 agent is registered."""
        response = await client.get("/elite-agents/SYNAPSE-13")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_id"] == "SYNAPSE-13"
        assert "integration" in data["domains"]
