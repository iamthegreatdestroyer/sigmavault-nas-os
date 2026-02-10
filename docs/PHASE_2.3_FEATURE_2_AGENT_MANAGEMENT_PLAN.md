# Feature 2: Agent Management Development Plan

## Current State Assessment

### ✅ What Exists
1. **Go API Handlers** (`src/api/internal/handlers/agents.go`):
   - `ListAgents()` - Returns all agents
   - `GetAgent(id)` - Gets specific agent
   - `AgentMetrics(id)` - Gets agent metrics
   - Falls back to mock data if RPC unavailable

2. **RPC Client Methods** (`src/api/internal/rpc/agents.go`):
   - `ListAgents()` - calls "agents.list" RPC
   - `GetAgent(id)` - calls "agents.get" RPC
   - `GetAgentByCodename()` - calls "agents.get_by_codename" RPC
   - `GetSwarmStatus()` - swarm-wide stats
   - `ListTiers()` - agent tier breakdown
   - `GetAgentMetrics()` - agent performance metrics
   - `DispatchTask()`, `CancelTask()`, `GetTaskStatus()` - task control
   - Memory, collaboration, scheduler, recovery, event, tuning status methods

3. **Data Models** (`src/api/internal/rpc/agents.go` & `internal/models/models.go`):
   - Full Agent struct with: ID, Codename, Tier, Role, Status, Capabilities, Metrics
   - AgentMetrics struct with performance data
   - AgentTask struct for task management
   - SwarmStatus struct for fleet-wide metrics
   - AgentTier struct for tier organization

4. **Routes** (`src/api/internal/routes/routes.go`, lines 115-118):
   ```go
   agents := protected.Group("/agents")
   agents.Get("/", agentsHandler.ListAgents)
   agents.Get("/:id", agentsHandler.GetAgent)
   agents.Get("/:id/metrics", agentsHandler.AgentMetrics)
   ```

5. **Desktop UI**:
   - Exists at `src/desktop-ui/` (GTK-based from Phase 2.2)
   - Likely has agents menu/section

### ❌ What's Missing
1. **Engine RPC Handlers**:
   - Likely missing these methods in `src/engined/engined/api/rpc.py`:
     - agents.list
     - agents.get
     - agents.get_by_codename
     - agents.metrics
     - agents.swarm_status
     - agents.list_tiers
   
2. **Agent Control Panel UI**:
   - Need to build Desktop UI agents page with:
     - List of all agents (with search/sort)
     - Agent status indicators (idle/active/error/offline)
     - Agent details view
     - Agent performance metrics graph
     - Agent tier visualization
     - Agent configuration panel

3. **Advanced Agent Controls**:
   - Task dispatch interface
   - Task status monitoring
   - Agent memory management UI
   - Collaboration initiation UI
   - Recovery trigger UI

## Implementation Priority

### Phase 2.3.2a: Foundation (CRITICAL)
1. Check if Engine has agents API module
2. Review what agent data Engine tracks
3. Implement missing RPC handlers in Engine
4. Test RPC endpoints return valid data
5. Verify Go API endpoints respond with real data

### Phase 2.3.2b: UI (HIGH)
1. Build agents list view in Desktop UI
2. Add agent detail panel
3. Implement agent status visualization
4. Add metrics/performance graphs

### Phase 2.3.2c: Advanced Features (MEDIUM)
1. Task dispatch UI
2. Agent configuration editor
3. Collaboration interface
4. Memory view

## Discovery Questions

1. **Where is agent data stored in Engine?**
   - Is there an `agents.py` or `swarm.py` module in `src/engined/engined/api/`?
   - What data structure represents agents?

2. **What agent information is available?**
   - Can Engine provide real agent list?
   - Or is it static/mock data?
   - Are there actual agent instances running?

3. **Does Desktop UI have existing agents page?**
   - Check `src/desktop-ui/` for agents components
   - Existing layout/structure?

## Next Steps

1. Check `src/engined/engined/` for agents module
2. Review Engine API structure for agent endpoints
3. Implement missing RPC handlers
4. Build UI components based on data available
5. Test end-to-end integration

## Success Criteria

✅ `/api/v1/agents` returns list of agents
✅ `/api/v1/agents/:id` returns agent details
✅ `/api/v1/agents/:id/metrics` returns agent metrics
✅ Desktop UI displays agent panel with:
   - List of all agents
   - Agent status (color-coded)
   - Agent specialization
   - Basic metrics

## Reference: Testing Endpoints

```bash
# Test list agents
curl -H "Authorization: Bearer <TOKEN>" http://localhost:12080/api/v1/agents

# Test get specific agent
curl -H "Authorization: Bearer <TOKEN>" http://localhost:12080/api/v1/agents/agent-tensor-001

# Test agent metrics
curl -H "Authorization: Bearer <TOKEN>" http://localhost:12080/api/v1/agents/agent-tensor-001/metrics
```

## RPC Methods to Implement in Engine

Priority list of RPC methods needed in `src/engined/engined/api/rpc.py`:

```python
# List all agents
elif method == "agents.list":
    result = await handle_agents_list(params)

# Get specific agent
elif method == "agents.get":
    agent_id = params.get("id") if isinstance(params, dict) else None
    result = await handle_agents_get(agent_id)

# Get agent by codename
elif method == "agents.get_by_codename":
    codename = params.get("codename") if isinstance(params, dict) else None
    result = await handle_agents_get_by_codename(codename)

# Get agent metrics
elif method == "agents.metrics":
    agent_id = params.get("id") if isinstance(params, dict) else None
    result = await handle_agents_metrics(agent_id)

# Get swarm status
elif method == "agents.swarm_status":
    result = await handle_agents_swarm_status()

# List tiers
elif method == "agents.list_tiers":
    result = await handle_agents_list_tiers()
```
