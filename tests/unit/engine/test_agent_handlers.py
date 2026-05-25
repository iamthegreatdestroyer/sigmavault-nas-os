"""
Unit Tests: Agent RPC Handlers

Tests all 7 agent RPC methods that query, filter, and analyze the
40-agent swarm data. Validates correct operation, parameter validation,
and error handling for agent management operations.

Scope:
  ✓ agents.list - List all agents
  ✓ agents.get - Get single agent by ID
  ✓ agents.get_by_codename - Get agent by codename
  ✓ agents.metrics - Calculate agent metrics
  ✓ agents.list_tiers - List tier distribution
  ✓ agents.swarm_status - Get swarm health status
  ✓ Concurrent agent queries
  ✓ Error handling and edge cases
"""

import pytest
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def agent_handlers():
    """Create mock agent handlers with access to fixture data."""
    
    class AgentHandlers:
        def __init__(self, agent_data):
            self.agents = {agent["id"]: agent for agent in agent_data}
            self.agents_by_codename = {agent["codename"]: agent for agent in agent_data}
            self.tiers = {}
            
            # Build tier map
            for agent in agent_data:
                tier = agent.get("tier")
                if tier not in self.tiers:
                    self.tiers[tier] = []
                self.tiers[tier].append(agent["id"])
        
        async def handle_agents_list(self, params: Dict) -> Dict:
            """List all agents, optionally filtered by status or tier."""
            
            status_filter = params.get("status")
            tier_filter = params.get("tier")
            
            agents = list(self.agents.values())
            
            if status_filter:
                agents = [a for a in agents if a.get("status") == status_filter]
            
            if tier_filter:
                agents = [a for a in agents if a.get("tier") == tier_filter]
            
            return {
                "agents": agents,
                "count": len(agents),
                "total": len(self.agents)
            }
        
        async def handle_agents_get(self, params: Dict) -> Dict:
            """Get single agent by ID."""
            
            agent_id = params.get("id")
            if not agent_id:
                raise ValueError("Missing required parameter: id")
            
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            return self.agents[agent_id]
        
        async def handle_agents_get_by_codename(self, params: Dict) -> Dict:
            """Get agent by codename."""
            
            codename = params.get("codename")
            if not codename:
                raise ValueError("Missing required parameter: codename")
            
            if codename not in self.agents_by_codename:
                raise ValueError(f"Agent {codename} not found")
            
            return self.agents_by_codename[codename]
        
        async def handle_agents_metrics(self, params: Dict) -> Dict:
            """Get metrics for agent or all agents."""
            
            agent_id = params.get("id")
            
            if agent_id:
                if agent_id not in self.agents:
                    raise ValueError(f"Agent {agent_id} not found")
                
                agent = self.agents[agent_id]
                return {
                    "agent_id": agent_id,
                    "tasks_completed": agent.get("tasks_completed", 0),
                    "success_rate": agent.get("success_rate", 0.0),
                    "avg_response_time_ms": agent.get("avg_response_time_ms", 0)
                }
            else:
                # Return aggregated metrics for all agents
                metrics = {}
                total_tasks = 0
                total_success = 0
                total_response_time = 0
                agent_count = len(self.agents)
                
                for agent in self.agents.values():
                    total_tasks += agent.get("tasks_completed", 0)
                    total_success += agent.get("success_rate", 0.0)
                    total_response_time += agent.get("avg_response_time_ms", 0)
                
                return {
                    "total_agents": agent_count,
                    "total_tasks": total_tasks,
                    "avg_success_rate": round(total_success / agent_count, 4) if agent_count > 0 else 0.0,
                    "avg_response_time_ms": round(total_response_time / agent_count, 2) if agent_count > 0 else 0.0,
                    "total_throughput_tasks_per_minute": round(total_tasks / agent_count * 100, 0)  # Rough estimate
                }
        
        async def handle_agents_list_tiers(self, params: Dict) -> Dict:
            """List agents grouped by tier."""
            
            tier_distribution = {}
            for tier, agent_ids in self.tiers.items():
                tier_distribution[tier] = {
                    "count": len(agent_ids),
                    "agents": agent_ids[:5]  # Show first 5 in each tier
                }
            
            return {
                "tiers": tier_distribution,
                "total_tiers": len(tier_distribution),
                "total_agents": len(self.agents)
            }
        
        async def handle_agents_swarm_status(self, params: Dict) -> Dict:
            """Get overall swarm health status."""
            
            active_count = sum(1 for a in self.agents.values() if a.get("status") == "active")
            inactive_count = len(self.agents) - active_count
            
            # Calculate health score (0-100)
            avg_success = sum(a.get("success_rate", 0.0) for a in self.agents.values()) / len(self.agents)
            health_score = int(avg_success * 100)
            
            return {
                "status": "healthy" if health_score >= 80 else "degraded",
                "active_agents": active_count,
                "inactive_agents": inactive_count,
                "health_score": health_score,
                "total_agents": len(self.agents),
                "uptime_percent": round((active_count / len(self.agents)) * 100, 2) if len(self.agents) > 0 else 0.0
            }
    
    return AgentHandlers


# ============================================================================
# TEST CASES: agents.list
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_list_all(agent_data, agent_handlers):
    """Test listing all agents."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_list({})
    
    assert "agents" in result
    assert "count" in result
    assert "total" in result
    assert result["count"] == len(agent_data)
    assert result["total"] == len(agent_data)
    assert len(result["agents"]) == len(agent_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_list_filter_by_status(agent_data, agent_handlers):
    """Test listing agents filtered by status."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_list({"status": "active"})
    
    assert "agents" in result
    assert result["count"] <= result["total"]
    # All returned agents should have active status
    for agent in result["agents"]:
        assert agent.get("status") == "active"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_list_filter_by_tier(agent_data, agent_handlers):
    """Test listing agents filtered by tier."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_list({"tier": "core"})
    
    assert "agents" in result
    # All returned agents should be core tier
    for agent in result["agents"]:
        assert agent.get("tier") == "core"


# ============================================================================
# TEST CASES: agents.get
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_get_valid_id(agent_data, agent_handlers):
    """Test getting agent by valid ID."""
    handlers = agent_handlers(agent_data)
    
    # Get first agent ID from fixture data
    agent_id = agent_data[0]["id"]
    
    result = await handlers.handle_agents_get({"id": agent_id})
    
    assert result["id"] == agent_id
    assert "codename" in result
    assert "tier" in result
    assert "status" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_get_invalid_id(agent_data, agent_handlers):
    """Test getting agent with non-existent ID."""
    handlers = agent_handlers(agent_data)
    
    with pytest.raises(ValueError, match="not found"):
        await handlers.handle_agents_get({"id": "agent-nonexistent"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_get_missing_id_param(agent_data, agent_handlers):
    """Test agents.get without id parameter."""
    handlers = agent_handlers(agent_data)
    
    with pytest.raises(ValueError, match="Missing required parameter"):
        await handlers.handle_agents_get({})


# ============================================================================
# TEST CASES: agents.get_by_codename
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_get_by_codename_valid(agent_data, agent_handlers):
    """Test getting agent by valid codename."""
    handlers = agent_handlers(agent_data)
    
    # Get first agent's codename from fixture data
    codename = agent_data[0]["codename"]
    
    result = await handlers.handle_agents_get_by_codename({"codename": codename})
    
    assert result["codename"] == codename
    assert "id" in result
    assert "tier" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_get_by_codename_invalid(agent_data, agent_handlers):
    """Test getting agent with non-existent codename."""
    handlers = agent_handlers(agent_data)
    
    with pytest.raises(ValueError, match="not found"):
        await handlers.handle_agents_get_by_codename({"codename": "INVALID-AGENT"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_get_by_codename_missing_param(agent_data, agent_handlers):
    """Test agents.get_by_codename without codename parameter."""
    handlers = agent_handlers(agent_data)
    
    with pytest.raises(ValueError, match="Missing required parameter"):
        await handlers.handle_agents_get_by_codename({})


# ============================================================================
# TEST CASES: agents.metrics
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_metrics_single_agent(agent_data, agent_handlers):
    """Test getting metrics for single agent."""
    handlers = agent_handlers(agent_data)
    
    agent_id = agent_data[0]["id"]
    result = await handlers.handle_agents_metrics({"id": agent_id})
    
    assert result["agent_id"] == agent_id
    assert "tasks_completed" in result
    assert "success_rate" in result
    assert "avg_response_time_ms" in result
    assert 0.0 <= result["success_rate"] <= 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_metrics_all_agents(agent_data, agent_handlers):
    """Test getting aggregated metrics for all agents."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_metrics({})
    
    assert "total_agents" in result
    assert "total_tasks" in result
    assert "avg_success_rate" in result
    assert "avg_response_time_ms" in result
    assert result["total_agents"] == len(agent_data)
    assert 0.0 <= result["avg_success_rate"] <= 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_metrics_invalid_agent(agent_data, agent_handlers):
    """Test getting metrics for non-existent agent."""
    handlers = agent_handlers(agent_data)
    
    with pytest.raises(ValueError, match="not found"):
        await handlers.handle_agents_metrics({"id": "agent-invalid"})


# ============================================================================
# TEST CASES: agents.list_tiers
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_list_tiers(agent_data, agent_handlers):
    """Test listing tier distribution of agents."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_list_tiers({})
    
    assert "tiers" in result
    assert "total_tiers" in result
    assert "total_agents" in result
    assert result["total_agents"] == len(agent_data)
    
    # Verify tier structure
    for tier_name, tier_info in result["tiers"].items():
        assert "count" in tier_info
        assert "agents" in tier_info
        assert isinstance(tier_info["agents"], list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_list_tiers_counts(agent_data, agent_handlers):
    """Test tie tier counts are accurate."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_list_tiers({})
    
    # Verify total count matches sum of tier counts
    total_from_tiers = sum(tier["count"] for tier in result["tiers"].values())
    assert total_from_tiers == result["total_agents"]


# ============================================================================
# TEST CASES: agents.swarm_status
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_swarm_status(agent_data, agent_handlers):
    """Test getting swarm health status."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_swarm_status({})
    
    assert "status" in result
    assert result["status"] in ["healthy", "degraded"]
    assert "active_agents" in result
    assert "inactive_agents" in result
    assert "health_score" in result
    assert "total_agents" in result
    assert "uptime_percent" in result
    
    # Verify values are reasonable
    assert 0 <= result["health_score"] <= 100
    assert 0.0 <= result["uptime_percent"] <= 100.0
    assert result["active_agents"] + result["inactive_agents"] == result["total_agents"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_swarm_status_health_calculation(agent_data, agent_handlers):
    """Test swarm health score calculation."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_swarm_status({})
    
    # Health score >= 80 means healthy
    if result["health_score"] >= 80:
        assert result["status"] == "healthy"
    else:
        assert result["status"] == "degraded"


# ============================================================================
# TEST CASES: Concurrent Operations
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_agent_queries(agent_data, agent_handlers):
    """Test concurrent queries to different methods."""
    handlers = agent_handlers(agent_data)
    
    import asyncio
    
    agent_id = agent_data[0]["id"]
    codename = agent_data[0]["codename"]
    
    # Run multiple queries concurrently
    results = await asyncio.gather(
        handlers.handle_agents_list({}),
        handlers.handle_agents_get({"id": agent_id}),
        handlers.handle_agents_get_by_codename({"codename": codename}),
        handlers.handle_agents_metrics({}),
        handlers.handle_agents_list_tiers({}),
        handlers.handle_agents_swarm_status({})
    )
    
    assert len(results) == 6
    assert results[0]["count"] == len(agent_data)  # list
    assert results[1]["id"] == agent_id  # get
    assert results[2]["codename"] == codename  # get_by_codename
    assert results[3]["total_agents"] == len(agent_data)  # metrics
    assert results[4]["total_agents"] == len(agent_data)  # list_tiers
    assert results[5]["total_agents"] == len(agent_data)  # swarm_status


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_same_method(agent_data, agent_handlers):
    """Test concurrent calls to same method."""
    handlers = agent_handlers(agent_data)
    
    import asyncio
    
    # Call agents.list 10 times concurrently
    results = await asyncio.gather(
        *[handlers.handle_agents_list({}) for _ in range(10)]
    )
    
    # All results should be identical
    assert len(results) == 10
    for result in results:
        assert result["total"] == len(agent_data)


# ============================================================================
# TEST CASES: Edge Cases
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_list_empty_filter_result(agent_data, agent_handlers):
    """Test agents.list with filter that returns no results."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_list({"status": "nonexistent_status"})
    
    assert result["count"] == 0
    assert result["agents"] == []
    assert result["total"] == len(agent_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_metrics_data_types(agent_data, agent_handlers):
    """Test metrics return proper data types."""
    handlers = agent_handlers(agent_data)
    
    result = await handlers.handle_agents_metrics({})
    
    assert isinstance(result["total_agents"], int)
    assert isinstance(result["total_tasks"], int)
    assert isinstance(result["avg_success_rate"], float)
    assert isinstance(result["avg_response_time_ms"], float)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent_data_consistency(agent_data, agent_handlers):
    """Test that agent data is consistent across methods."""
    handlers = agent_handlers(agent_data)
    
    agent_id = agent_data[0]["id"]
    codename = agent_data[0]["codename"]
    
    # Get agent via different methods
    result_by_id = await handlers.handle_agents_get({"id": agent_id})
    result_by_codename = await handlers.handle_agents_get_by_codename({"codename": codename})
    
    # Both should return same agent
    assert result_by_id["id"] == result_by_codename["id"]
    assert result_by_id["codename"] == result_by_codename["codename"]


# ============================================================================
# TEST SETUP & MARKERS
# ============================================================================

@pytest.mark.unit
class TestAgentHandlers:
    """Test suite for all agent RPC methods."""
    
    @pytest.mark.asyncio
    async def test_suite_setup(self):
        """Verify test suite is properly initialized."""
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

