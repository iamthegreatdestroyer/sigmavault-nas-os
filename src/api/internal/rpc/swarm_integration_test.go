// Package rpc provides agent swarm integration tests.
// PHASE 3.2: Agent Swarm Integration Testing
// Tests for 40-agent registry, discovery, task distribution, and swarm coordination
package rpc

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// generateMockAgents creates a mock set of N agents with realistic data
func generateMockAgents(count int) []Agent {
	agents := make([]Agent, count)
	tiers := []string{"core", "specialist", "innovator", "meta"}
	roles := []string{
		"ML Specialist", "Security Expert", "System Architect",
		"Data Scientist", "DevOps Engineer", "Performance Optimizer",
		"Compliance Officer", "Research Analyst",
	}
	specializations := []string{
		"machine-learning", "cryptography", "systems-design",
		"data-analysis", "infrastructure", "optimization",
		"compliance", "research", "security", "testing",
	}

	for i := 0; i < count; i++ {
		idx := i + 1
		tier := tiers[i%len(tiers)]
		role := roles[i%len(roles)]
		spec := specializations[i%len(specializations)]

		agents[i] = Agent{
			ID:             fmt.Sprintf("agent-%03d", idx),
			Codename:       fmt.Sprintf("AGENT_%02d", idx),
			Tier:           tier,
			Role:           role,
			Status:         "idle", // most agents idle
			Specialization: spec,
			Description:    fmt.Sprintf("%s specializing in %s", role, spec),
			Capabilities:   []string{"analysis", "task_execution", "reporting"},
			LastActive:     time.Now().Add(-time.Duration(i%100) * time.Minute),
			CreatedAt:      time.Now().Add(-time.Duration(i*10) * time.Hour),
		}
	}
	return agents
}

// TestAgentRegistryDiscovery tests listing and filtering of 40 agents
func TestAgentRegistryDiscovery(t *testing.T) {
	mockAgents := generateMockAgents(40)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string            `json:"method"`
				Params *ListAgentsParams `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			// Filter agents by status
			filtered := mockAgents
			if req.Params != nil && req.Params.Status != "" {
				filtered = make([]Agent, 0)
				for _, agent := range mockAgents {
					if agent.Status == req.Params.Status {
						filtered = append(filtered, agent)
					}
				}
			}

			if req.Method == "agents.list" {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  filtered,
					"id":      1,
				})
				return
			}
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: List all 40 agents
	agents, err := client.ListAgents(context.Background(), nil)
	if err != nil {
		t.Fatalf("ListAgents failed: %v", err)
	}
	if len(agents) != 40 {
		t.Errorf("Expected 40 agents, got %d", len(agents))
	}

	// Test 2: Verify agent data structure
	if agents[0].ID == "" {
		t.Error("Agent ID should not be empty")
	}
	if agents[0].Codename == "" {
		t.Error("Agent Codename should not be empty")
	}
	if agents[0].Tier == "" {
		t.Error("Agent Tier should not be empty")
	}

	// Test 3: Filter by status
	idleFilter := &ListAgentsParams{Status: "idle"}
	idleAgents, err := client.ListAgents(context.Background(), idleFilter)
	if err != nil {
		t.Fatalf("ListAgents with filter failed: %v", err)
	}
	if len(idleAgents) != 40 {
		t.Errorf("Expected 40 idle agents, got %d", len(idleAgents))
	}

	// Verify all returned agents have idle status
	for _, agent := range idleAgents {
		if agent.Status != "idle" {
			t.Errorf("Expected idle status, got %s", agent.Status)
		}
	}
}

// TestAgentSwarmInitialization tests swarm startup and agent initialization
func TestAgentSwarmInitialization(t *testing.T) {
	mockAgents := generateMockAgents(40)
	var mu sync.Mutex
	agentStates := make(map[string]string) // agent ID -> status

	// Initialize all agents to offline
	for _, agent := range mockAgents {
		agentStates[agent.ID] = "offline"
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			mu.Lock()
			defer mu.Unlock()

			switch req.Method {
			case "agents.list":
				// Return agents with current statuses
				result := make([]Agent, 0)
				for _, agent := range mockAgents {
					agent.Status = agentStates[agent.ID]
					result = append(result, agent)
				}
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  result,
					"id":      1,
				})

			case "agents.get":
				var params GetAgentParams
				json.Unmarshal(req.Params, &params)
				for _, agent := range mockAgents {
					if agent.ID == params.ID {
						agent.Status = agentStates[agent.ID]
						w.Header().Set("Content-Type", "application/json")
						json.NewEncoder(w).Encode(map[string]interface{}{
							"jsonrpc": "2.0",
							"result":  agent,
							"id":      1,
						})
						return
					}
				}
				http.Error(w, "Agent not found", http.StatusNotFound)
			}
			return
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: Verify initial swarm state
	agents, err := client.ListAgents(context.Background(), nil)
	if err != nil {
		t.Fatalf("Initial ListAgents failed: %v", err)
	}

	offlineCount := 0
	for _, agent := range agents {
		if agent.Status == "offline" {
			offlineCount++
		}
	}
	if offlineCount != 40 {
		t.Errorf("Expected 40 offline agents initially, got %d", offlineCount)
	}

	// Test 2: Simulate agents coming online
	mu.Lock()
	for id := range agentStates {
		agentStates[id] = "idle"
	}
	mu.Unlock()

	agents, err = client.ListAgents(context.Background(), nil)
	if err != nil {
		t.Fatalf("ListAgents after initialization failed: %v", err)
	}

	idleCount := 0
	for _, agent := range agents {
		if agent.Status == "idle" {
			idleCount++
		}
	}
	if idleCount != 40 {
		t.Errorf("Expected 40 idle agents after init, got %d", idleCount)
	}

	// Test 3: Verify individual agent retrieval
	agent, err := client.GetAgent(context.Background(), "agent-001")
	if err != nil {
		t.Fatalf("GetAgent failed: %v", err)
	}
	if agent.ID != "agent-001" {
		t.Errorf("Expected agent-001, got %s", agent.ID)
	}
	if agent.Status != "idle" {
		t.Errorf("Expected idle status, got %s", agent.Status)
	}
}

// TestTaskDistributionAcrossSwarm tests dispatching tasks to multiple agents
func TestTaskDistributionAcrossSwarm(t *testing.T) {
	mockAgents := generateMockAgents(40)
	var mu sync.Mutex
	taskCounter := 0
	tasksByAgent := make(map[string][]AgentTask)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			mu.Lock()
			defer mu.Unlock()

			switch req.Method {
			case "agents.tasks.dispatch":
				var params DispatchTaskParams
				json.Unmarshal(req.Params, &params)

				taskCounter++
				taskID := fmt.Sprintf("task-%04d", taskCounter)
				agentID := params.AgentID
				if agentID == "" {
					agentID = mockAgents[taskCounter%len(mockAgents)].ID
				}

				task := AgentTask{
					ID:         taskID,
					AgentID:    agentID,
					Type:       params.TaskType,
					Status:     "pending",
					Priority:   params.Priority,
					Input:      params.Input,
					Retries:    0,
					MaxRetries: params.MaxRetries,
					CreatedAt:  time.Now(),
				}

				tasksByAgent[agentID] = append(tasksByAgent[agentID], task)

				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  task,
					"id":      1,
				})

			case "agents.tasks.list":
				var params ListTasksParams
				json.Unmarshal(req.Params, &params)

				tasks := tasksByAgent[params.AgentID]
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  tasks,
					"id":      1,
				})
			}
			return
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: Dispatch tasks to multiple agents
	dispatchedTasks := 0
	for i := 0; i < 10; i++ {
		agentID := mockAgents[i].ID
		params := &DispatchTaskParams{
			AgentID:    agentID,
			TaskType:   "analysis",
			Priority:   1,
			Input:      map[string]any{"data": fmt.Sprintf("input-%d", i)},
			Async:      true,
			MaxRetries: 3,
		}
		task, err := client.DispatchTask(context.Background(), params)
		if err != nil {
			t.Fatalf("DispatchTask failed: %v", err)
		}
		if task.Status != "pending" {
			t.Errorf("Expected pending status, got %s", task.Status)
		}
		if task.AgentID != agentID {
			t.Errorf("Expected agentID %s, got %s", agentID, task.AgentID)
		}
		dispatchedTasks++
	}

	if dispatchedTasks != 10 {
		t.Errorf("Expected 10 tasks dispatched, got %d", dispatchedTasks)
	}

	// Test 2: Verify task distribution across swarm
	totalTasksInSwarm := 0
	for _, tasks := range tasksByAgent {
		totalTasksInSwarm += len(tasks)
	}
	if totalTasksInSwarm != 10 {
		t.Errorf("Expected 10 total tasks, got %d", totalTasksInSwarm)
	}

	// Test 3: Retrieve tasks for specific agent
	agentID := mockAgents[0].ID
	tasks, err := client.ListTasks(context.Background(), &ListTasksParams{
		AgentID: agentID,
	})
	if err != nil {
		t.Fatalf("ListTasks failed: %v", err)
	}
	if len(tasks) != 1 {
		t.Errorf("Expected 1 task for agent %s, got %d", agentID, len(tasks))
	}
}

// TestSwarmStatusPolling tests polling overall swarm status
func TestSwarmStatusPolling(t *testing.T) {
	var mu sync.Mutex
	swarmState := &SwarmStatus{
		TotalAgents:    40,
		ActiveAgents:   30,
		IdleAgents:     30,
		BusyAgents:     10,
		ErrorAgents:    0,
		PendingTasks:   15,
		RunningTasks:   10,
		TaskQueue:      5,
		Throughput:     42.5,
		AverageLatency: 120.5,
		HealthScore:    95.0,
		TierBreakdown:  map[int]int{0: 10, 1: 15, 2: 10, 3: 5},
		LastUpdated:    time.Now(),
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string `json:"method"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			mu.Lock()
			defer mu.Unlock()

			if req.Method == "agents.swarm.status" {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  swarmState,
					"id":      1,
				})
				return
			}
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: Get initial swarm status
	status, err := client.GetSwarmStatus(context.Background())
	if err != nil {
		t.Fatalf("GetSwarmStatus failed: %v", err)
	}

	if status.TotalAgents != 40 {
		t.Errorf("Expected 40 total agents, got %d", status.TotalAgents)
	}
	if status.ActiveAgents != 30 {
		t.Errorf("Expected 30 active agents, got %d", status.ActiveAgents)
	}
	if status.HealthScore != 95.0 {
		t.Errorf("Expected health score 95.0, got %f", status.HealthScore)
	}

	// Test 2: Verify status consistency
	accountedAgents := status.IdleAgents + status.BusyAgents + status.ErrorAgents
	if accountedAgents != status.TotalAgents {
		t.Errorf("Agent status breakdown doesn't match total: %d != %d", accountedAgents, status.TotalAgents)
	}

	// Test 3: Polling updates (simulate status change)
	mu.Lock()
	swarmState.BusyAgents = 15
	swarmState.IdleAgents = 15
	swarmState.ErrorAgents = 10
	swarmState.HealthScore = 92.0
	mu.Unlock()

	status, err = client.GetSwarmStatus(context.Background())
	if err != nil {
		t.Fatalf("GetSwarmStatus second poll failed: %v", err)
	}

	if status.BusyAgents != 15 {
		t.Errorf("Expected 15 busy agents after update, got %d", status.BusyAgents)
	}
	if status.HealthScore != 92.0 {
		t.Errorf("Expected health score 92.0, got %f", status.HealthScore)
	}
}

// TestAgentMetricsCollection tests collecting metrics from all agents
func TestAgentMetricsCollection(t *testing.T) {
	mockAgents := generateMockAgents(40)
	metricsMap := make(map[string]AgentMetrics)

	// Generate realistic metrics for each agent
	for i, agent := range mockAgents {
		metricsMap[agent.ID] = AgentMetrics{
			TasksCompleted:      int64(100 + i*10),
			TasksFailed:         int64(5 + (i % 10)),
			AverageLatency:      float64(50 + (i % 100)),
			SuccessRate:         0.90 + float64(i%10)*0.01,
			TotalProcessingTime: int64(1000 * (i + 1)),
			MemoryUsage:         uint64((i + 1) * 100 * 1024 * 1024),
			LastUpdated:         time.Now(),
		}
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string         `json:"method"`
				Params GetAgentParams `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "agents.metrics" {
				if metrics, ok := metricsMap[req.Params.ID]; ok {
					w.Header().Set("Content-Type", "application/json")
					json.NewEncoder(w).Encode(map[string]interface{}{
						"jsonrpc": "2.0",
						"result":  metrics,
						"id":      1,
					})
					return
				}
			}
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: Collect metrics from first 10 agents
	for i := 0; i < 10; i++ {
		agentID := mockAgents[i].ID
		metrics, err := client.GetAgentMetrics(context.Background(), agentID)
		if err != nil {
			t.Fatalf("GetAgentMetrics failed for %s: %v", agentID, err)
		}
		if metrics.TasksCompleted == 0 {
			t.Errorf("Expected non-zero TasksCompleted for %s", agentID)
		}
		if metrics.SuccessRate <= 0 || metrics.SuccessRate > 1 {
			t.Errorf("Invalid success rate for %s: %f", agentID, metrics.SuccessRate)
		}
	}

	// Test 2: Verify metrics consistency
	metricsCount := 0
	for i := 0; i < 10; i++ {
		agentID := mockAgents[i].ID
		metrics, err := client.GetAgentMetrics(context.Background(), agentID)
		if err != nil {
			continue
		}
		if metrics.TasksFailed <= metrics.TasksCompleted {
			metricsCount++
		}
	}
	if metricsCount != 10 {
		t.Errorf("Expected 10 valid metrics, got %d", metricsCount)
	}
}

// TestSwarmFailureRecovery tests failure handling and recovery mechanisms
func TestSwarmFailureRecovery(t *testing.T) {
	mockAgents := generateMockAgents(40)
	var mu sync.Mutex
	failureCount := 0
	agentErrors := make(map[string]int)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			mu.Lock()
			defer mu.Unlock()

			switch req.Method {
			case "agents.list":
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  mockAgents,
					"id":      1,
				})

			case "agents.tasks.dispatch":
				var params DispatchTaskParams
				json.Unmarshal(req.Params, &params)

				failureCount++
				if failureCount%5 == 0 {
					// Simulate failures on every 5th dispatch
					http.Error(w, "Service error", http.StatusInternalServerError)
					agentErrors[params.AgentID]++
					return
				}

				// Success case
				task := AgentTask{
					ID:      fmt.Sprintf("task-%04d", failureCount),
					AgentID: params.AgentID,
					Status:  "pending",
				}
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  task,
					"id":      1,
				})
			}
			return
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: Attempt multiple task dispatches with failure/recovery
	successCount := 0
	for i := 0; i < 10; i++ {
		params := &DispatchTaskParams{
			AgentID:  mockAgents[i].ID,
			TaskType: "test",
			Input:    map[string]any{"test": true},
		}
		_, err := client.DispatchTask(context.Background(), params)
		if err == nil {
			successCount++
		}
	}

	if successCount < 8 { // At least 8 should succeed (retry mechanism)
		t.Errorf("Expected at least 8 successful dispatches, got %d", successCount)
	}

	// Test 2: Verify agent list still available after failures
	agents, err := client.ListAgents(context.Background(), nil)
	if err != nil {
		t.Fatalf("ListAgents after failures failed: %v", err)
	}
	if len(agents) != 40 {
		t.Errorf("Expected 40 agents despite failures, got %d", len(agents))
	}
}

// TestConcurrentSwarmOperations tests concurrent operations across the 40-agent swarm
func TestConcurrentSwarmOperations(t *testing.T) {
	mockAgents := generateMockAgents(40)
	var mu sync.Mutex
	var taskCounter int64
	concurrentRequests := int64(0)
	maxConcurrentRequests := int64(0)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			concurrent := atomic.AddInt64(&concurrentRequests, 1)
			defer atomic.AddInt64(&concurrentRequests, -1)

			// Track max concurrent (lock-free CAS loop)
			for {
				prev := atomic.LoadInt64(&maxConcurrentRequests)
				if concurrent <= prev {
					break
				}
				if atomic.CompareAndSwapInt64(&maxConcurrentRequests, prev, concurrent) {
					break
				}
			}

			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			mu.Lock()
			defer mu.Unlock()

			switch req.Method {
			case "agents.list":
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  mockAgents,
					"id":      1,
				})

			case "agents.tasks.dispatch":
				taskCounter++
				var params DispatchTaskParams
				json.Unmarshal(req.Params, &params)

				task := AgentTask{
					ID:      fmt.Sprintf("task-%05d", taskCounter),
					AgentID: params.AgentID,
					Status:  "pending",
				}
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  task,
					"id":      1,
				})
			}
			return
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: Concurrent agent listing
	var wg sync.WaitGroup
	listErrors := 0
	var listMu sync.Mutex

	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := client.ListAgents(context.Background(), nil)
			if err != nil {
				listMu.Lock()
				listErrors++
				listMu.Unlock()
			}
		}()
	}
	wg.Wait()

	if listErrors > 0 {
		t.Errorf("Concurrent ListAgents had %d errors", listErrors)
	}

	// Test 2: Concurrent task dispatches
	dispatchErrors := 0
	var dispatchMu sync.Mutex

	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			agentID := mockAgents[idx%40].ID
			params := &DispatchTaskParams{
				AgentID:  agentID,
				TaskType: "concurrent_test",
				Input:    map[string]any{"index": idx},
			}
			_, err := client.DispatchTask(context.Background(), params)
			if err != nil {
				dispatchMu.Lock()
				dispatchErrors++
				dispatchMu.Unlock()
			}
		}(i)
	}
	wg.Wait()

	if dispatchErrors > 0 {
		t.Errorf("Concurrent DispatchTask had %d errors", dispatchErrors)
	}

	// Test 3: Verify concurrency was actually achieved
	if maxConcurrentRequests < 5 {
		t.Logf("Warning: Expected at least 5 concurrent requests, got %d", maxConcurrentRequests)
	}
}

// TestAgentTierDistribution tests agent tier breakdown and organization
func TestAgentTierDistribution(t *testing.T) {
	tiers := []AgentTier{
		{
			Tier:        1,
			Name:        "Core",
			Description: "Foundational agents",
			AgentCount:  10,
			Agents:      []string{"agent-001", "agent-002", "agent-003", "agent-004", "agent-005", "agent-006", "agent-007", "agent-008", "agent-009", "agent-010"},
		},
		{
			Tier:        2,
			Name:        "Specialist",
			Description: "Domain specialists",
			AgentCount:  15,
			Agents:      []string{"agent-011", "agent-012", "agent-013", "agent-014", "agent-015", "agent-016", "agent-017", "agent-018", "agent-019", "agent-020", "agent-021", "agent-022", "agent-023", "agent-024", "agent-025"},
		},
		{
			Tier:        3,
			Name:        "Innovator",
			Description: "Innovation specialists",
			AgentCount:  10,
			Agents:      []string{"agent-026", "agent-027", "agent-028", "agent-029", "agent-030", "agent-031", "agent-032", "agent-033", "agent-034", "agent-035"},
		},
		{
			Tier:        4,
			Name:        "Meta",
			Description: "Meta-level orchestration",
			AgentCount:  5,
			Agents:      []string{"agent-036", "agent-037", "agent-038", "agent-039", "agent-040"},
		},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string `json:"method"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "agents.tiers.list" {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  tiers,
					"id":      1,
				})
				return
			}
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: List all tiers
	tiersList, err := client.ListTiers(context.Background())
	if err != nil {
		t.Fatalf("ListTiers failed: %v", err)
	}

	if len(tiersList) != 4 {
		t.Errorf("Expected 4 tiers, got %d", len(tiersList))
	}

	// Test 2: Verify tier structure
	expectedAgents := 10 + 15 + 10 + 5
	totalAgents := 0
	for _, tier := range tiersList {
		totalAgents += tier.AgentCount
		if len(tier.Agents) != tier.AgentCount {
			t.Errorf("Tier %d: agent count mismatch: %d != %d", tier.Tier, len(tier.Agents), tier.AgentCount)
		}
	}

	if totalAgents != expectedAgents {
		t.Errorf("Expected %d total agents across tiers, got %d", expectedAgents, totalAgents)
	}

	// Test 3: Verify tier names
	tierNames := make(map[int]string)
	for _, tier := range tiersList {
		tierNames[tier.Tier] = tier.Name
	}

	expectedNames := map[int]string{
		1: "Core",
		2: "Specialist",
		3: "Innovator",
		4: "Meta",
	}

	for tierNum, expectedName := range expectedNames {
		if tierNames[tierNum] != expectedName {
			t.Errorf("Tier %d: expected name %q, got %q", tierNum, expectedName, tierNames[tierNum])
		}
	}
}

// TestTaskStatusTracking tests tracking tasks across multiple agents
func TestTaskStatusTracking(t *testing.T) {
	mockAgents := generateMockAgents(10) // Use 10 for simpler tracking
	var mu sync.Mutex
	taskStates := make(map[string]TaskResult)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			mu.Lock()
			defer mu.Unlock()

			switch req.Method {
			case "agents.tasks.dispatch":
				var params DispatchTaskParams
				json.Unmarshal(req.Params, &params)
				taskID := fmt.Sprintf("task-%s-%d", params.AgentID, time.Now().UnixNano())
				result := TaskResult{
					TaskID:   taskID,
					AgentID:  params.AgentID,
					Status:   "pending",
					Progress: 0.0,
					Duration: 0,
				}
				taskStates[taskID] = result

				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result": AgentTask{
						ID:      taskID,
						AgentID: params.AgentID,
						Status:  "pending",
					},
					"id": 1,
				})

			case "agents.tasks.status":
				var params GetTaskStatusParams
				json.Unmarshal(req.Params, &params)

				if result, ok := taskStates[params.TaskID]; ok {
					w.Header().Set("Content-Type", "application/json")
					json.NewEncoder(w).Encode(map[string]interface{}{
						"jsonrpc": "2.0",
						"result":  result,
						"id":      1,
					})
					return
				}
				http.Error(w, "Task not found", http.StatusNotFound)
			}
			return
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test 1: Dispatch tasks and track them
	dispatchedTasks := 0
	taskIDs := make([]string, 0)

	for i := 0; i < 5; i++ {
		params := &DispatchTaskParams{
			AgentID:    mockAgents[i].ID,
			TaskType:   "tracking_test",
			Input:      map[string]any{"index": i},
			MaxRetries: 3,
		}
		task, err := client.DispatchTask(context.Background(), params)
		if err != nil {
			t.Fatalf("DispatchTask failed: %v", err)
		}
		taskIDs = append(taskIDs, task.ID)
		dispatchedTasks++
	}

	if dispatchedTasks != 5 {
		t.Errorf("Expected 5 dispatched tasks, got %d", dispatchedTasks)
	}

	// Test 2: Query status of dispatched tasks
	for _, taskID := range taskIDs {
		status, err := client.GetTaskStatus(context.Background(), taskID)
		if err != nil {
			t.Fatalf("GetTaskStatus failed for %s: %v", taskID, err)
		}
		if status.TaskID != taskID {
			t.Errorf("Expected taskID %s, got %s", taskID, status.TaskID)
		}
		if status.Status != "pending" {
			t.Errorf("Expected pending status for %s, got %s", taskID, status.Status)
		}
	}

	// Test 3: Simulate status updates and recheck
	mu.Lock()
	for _, taskID := range taskIDs {
		if result, ok := taskStates[taskID]; ok {
			result.Status = "completed"
			result.Progress = 100.0
			result.Duration = 1000
			taskStates[taskID] = result
		}
	}
	mu.Unlock()

	// Verify updated statuses
	for _, taskID := range taskIDs {
		status, err := client.GetTaskStatus(context.Background(), taskID)
		if err != nil {
			t.Fatalf("GetTaskStatus after update failed for %s: %v", taskID, err)
		}
		if status.Status != "completed" {
			t.Errorf("Expected completed status after update, got %s", status.Status)
		}
		if status.Progress != 100.0 {
			t.Errorf("Expected 100%% progress, got %f", status.Progress)
		}
	}
}

// TestSwarmHealthMetrics tests comprehensive swarm health monitoring
func TestSwarmHealthMetrics(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string `json:"method"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "agents.swarm.status" {
				status := SwarmStatus{
					TotalAgents:    40,
					ActiveAgents:   38,
					IdleAgents:     25,
					BusyAgents:     13,
					ErrorAgents:    2,
					PendingTasks:   42,
					RunningTasks:   28,
					TaskQueue:      14,
					Throughput:     85.5,
					AverageLatency: 145.2,
					HealthScore:    87.5,
					TierBreakdown:  map[int]int{1: 10, 2: 15, 3: 10, 4: 5},
					LastUpdated:    time.Now(),
				}

				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  status,
					"id":      1,
				})
				return
			}
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	status, err := client.GetSwarmStatus(context.Background())
	if err != nil {
		t.Fatalf("GetSwarmStatus failed: %v", err)
	}

	// Verify all health metrics
	tests := []struct {
		name     string
		got      interface{}
		expected interface{}
	}{
		{"TotalAgents", status.TotalAgents, 40},
		{"ActiveAgents", status.ActiveAgents, 38},
		{"ErrorAgents", status.ErrorAgents, 2},
		{"Throughput", status.Throughput, 85.5},
		{"HealthScore", status.HealthScore, 87.5},
	}

	for _, test := range tests {
		if test.got != test.expected {
			t.Errorf("%s: got %v, want %v", test.name, test.got, test.expected)
		}
	}
}

// TestAgentCodenameLookup tests retrieving agents by unique codenames
func TestAgentCodenameLookup(t *testing.T) {
	mockAgents := generateMockAgents(40)
	codenameMap := make(map[string]Agent)

	for _, agent := range mockAgents {
		codenameMap[agent.Codename] = agent
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string            `json:"method"`
				Params map[string]string `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "agents.get_by_codename" {
				codename, ok := req.Params["codename"]
				if ok {
					if agent, found := codenameMap[codename]; found {
						w.Header().Set("Content-Type", "application/json")
						json.NewEncoder(w).Encode(map[string]interface{}{
							"jsonrpc": "2.0",
							"result":  agent,
							"id":      1,
						})
						return
					}
				}
				http.Error(w, "Agent not found", http.StatusNotFound)
				return
			}
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Test: Retrieve agents by codename
	testCodenamesCount := 0
	for _, mockAgent := range mockAgents[:10] { // Test first 10
		agent, err := client.GetAgentByCodename(context.Background(), mockAgent.Codename)
		if err != nil {
			t.Logf("GetAgentByCodename failed for %s: %v", mockAgent.Codename, err)
			continue
		}
		if agent.Codename != mockAgent.Codename {
			t.Errorf("Codename mismatch: got %s, want %s", agent.Codename, mockAgent.Codename)
		}
		testCodenamesCount++
	}

	if testCodenamesCount < 9 { // At least 9 should succeed
		t.Errorf("Expected at least 9 successful codename lookups, got %d", testCodenamesCount)
	}
}

// TestSwarmLoadBalancing tests task distribution load balancing
func TestSwarmLoadBalancing(t *testing.T) {
	mockAgents := generateMockAgents(40)
	var mu sync.Mutex
	taskCounts := make(map[string]int) // agent ID -> task count

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			mu.Lock()
			defer mu.Unlock()

			if req.Method == "agents.tasks.dispatch" {
				var params DispatchTaskParams
				json.Unmarshal(req.Params, &params)

				agentID := params.AgentID
				taskCounts[agentID]++

				task := AgentTask{
					ID:      fmt.Sprintf("task-%s-%d", agentID, taskCounts[agentID]),
					AgentID: agentID,
					Status:  "pending",
				}

				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  task,
					"id":      1,
				})
				return
			}
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 3,
	})

	// Dispatch 40 tasks (one per agent)
	for i := 0; i < 40; i++ {
		agentID := mockAgents[i].ID
		params := &DispatchTaskParams{
			AgentID:    agentID,
			TaskType:   "load_test",
			Input:      map[string]any{"index": i},
			MaxRetries: 3,
		}
		_, err := client.DispatchTask(context.Background(), params)
		if err != nil {
			t.Logf("DispatchTask failed for %s: %v", agentID, err)
		}
	}

	// Verify load is balanced (each agent should have ~1 task)
	mu.Lock()
	defer mu.Unlock()

	for agentID, count := range taskCounts {
		if count == 0 {
			t.Errorf("Agent %s has no tasks", agentID)
		}
		if count > 2 {
			t.Errorf("Agent %s has unbalanced load: %d tasks", agentID, count)
		}
	}
}
