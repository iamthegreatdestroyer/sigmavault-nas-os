// Package main provides integration tests for the RPC layer.
// These tests verify end-to-end communication between Go API and Python engine.
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"testing"
	"time"
)

const (
	pythonRPCURL = "http://localhost:8102/api/v1/rpc"
	goAPIURL     = "http://localhost:12080"
)

// JSONRPCRequest represents a JSON-RPC 2.0 request.
type JSONRPCRequest struct {
	JSONRPC string      `json:"jsonrpc"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params,omitempty"`
	ID      int         `json:"id"`
}

// JSONRPCResponse represents a JSON-RPC 2.0 response.
type JSONRPCResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *JSONRPCError   `json:"error,omitempty"`
	ID      int             `json:"id"`
}

// JSONRPCError represents a JSON-RPC 2.0 error.
type JSONRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// SystemStatusResult represents the system.status response.
type SystemStatusResult struct {
	Hostname    string                 `json:"hostname"`
	Platform    string                 `json:"platform"`
	Uptime      int                    `json:"uptime"`
	CPUUsage    float64                `json:"cpu_usage"`
	MemoryUsage map[string]interface{} `json:"memory_usage"`
	LoadAverage map[string]float64     `json:"load_average"`
	Timestamp   string                 `json:"timestamp"`
}

// AgentsListResult represents the agents.list response.
type AgentsListResult struct {
	Agents           []AgentInfo `json:"agents"`
	Total            int         `json:"total"`
	SwarmInitialized bool        `json:"swarm_initialized"`
}

// AgentInfo represents an agent in the list.
type AgentInfo struct {
	AgentID           string  `json:"agent_id"`
	Name              string  `json:"name"`
	Tier              string  `json:"tier"`
	Specialty         string  `json:"specialty"`
	Status            string  `json:"status"`
	TasksCompleted    int     `json:"tasks_completed"`
	SuccessRate       float64 `json:"success_rate"`
	AvgResponseTimeMs float64 `json:"avg_response_time_ms"`
	MemoryUsageMB     float64 `json:"memory_usage_mb"`
	LastActive        string  `json:"last_active"`
}

// AgentsStatusResult represents the agents.status response.
type AgentsStatusResult struct {
	TotalAgents         int     `json:"total_agents"`
	ActiveAgents        int     `json:"active_agents"`
	IdleAgents          int     `json:"idle_agents"`
	BusyAgents          int     `json:"busy_agents"`
	ErrorAgents         int     `json:"error_agents"`
	OfflineAgents       int     `json:"offline_agents"`
	TotalTasksQueued    int     `json:"total_tasks_queued"`
	TotalTasksCompleted int     `json:"total_tasks_completed"`
	UptimeSeconds       float64 `json:"uptime_seconds"`
	IsInitialized       bool    `json:"is_initialized"`
}

// CompressionJobsResult represents the compression.jobs.list response.
type CompressionJobsResult struct {
	Jobs  []interface{} `json:"jobs"`
	Total int           `json:"total"`
}

// callRPC makes a JSON-RPC call to the Python engine.
func callRPC(t *testing.T, method string, params interface{}) (*JSONRPCResponse, error) {
	req := JSONRPCRequest{
		JSONRPC: "2.0",
		Method:  method,
		Params:  params,
		ID:      1,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Post(pythonRPCURL, "application/json", strings.NewReader(string(body)))
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	var rpcResp JSONRPCResponse
	if err := json.Unmarshal(respBody, &rpcResp); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w (body: %s)", err, string(respBody))
	}

	return &rpcResp, nil
}

// TestRPCConnection verifies basic connectivity to the Python RPC engine.
func TestRPCConnection(t *testing.T) {
	t.Log("Testing RPC connection to Python engine...")

	resp, err := callRPC(t, "system.status", nil)
	if err != nil {
		t.Fatalf("Failed to connect to RPC engine: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC returned error: %s (code: %d)", resp.Error.Message, resp.Error.Code)
	}

	if resp.Result == nil {
		t.Fatal("RPC returned nil result")
	}

	t.Log("✅ RPC connection successful")
}

// TestSystemStatus tests the system.status RPC method.
func TestSystemStatus(t *testing.T) {
	t.Log("Testing system.status RPC method...")

	resp, err := callRPC(t, "system.status", nil)
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s", resp.Error.Message)
	}

	var result SystemStatusResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Validate required fields
	if result.Hostname == "" {
		t.Error("Expected non-empty hostname")
	}
	if result.Platform == "" {
		t.Error("Expected non-empty platform")
	}
	if result.Timestamp == "" {
		t.Error("Expected non-empty timestamp")
	}
	if result.MemoryUsage == nil {
		t.Error("Expected memory_usage object")
	}

	t.Logf("✅ system.status: hostname=%s, platform=%s, cpu=%.1f%%, uptime=%ds",
		result.Hostname, result.Platform, result.CPUUsage, result.Uptime)
}

// TestAgentsList tests the agents.list RPC method.
func TestAgentsList(t *testing.T) {
	t.Log("Testing agents.list RPC method...")

	resp, err := callRPC(t, "agents.list", map[string]interface{}{})
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s (code: %d)", resp.Error.Message, resp.Error.Code)
	}

	var result AgentsListResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Validate 40 agents
	if result.Total != 40 {
		t.Errorf("Expected 40 agents, got %d", result.Total)
	}

	if len(result.Agents) != 40 {
		t.Errorf("Expected 40 agents in list, got %d", len(result.Agents))
	}

	// Verify agent structure
	if len(result.Agents) > 0 {
		agent := result.Agents[0]
		if agent.AgentID == "" {
			t.Error("Expected non-empty agent_id")
		}
		if agent.Name == "" {
			t.Error("Expected non-empty name")
		}
		if agent.Tier == "" {
			t.Error("Expected non-empty tier")
		}
		if agent.Specialty == "" {
			t.Error("Expected non-empty specialty")
		}
	}

	// Count tiers
	tierCounts := make(map[string]int)
	for _, agent := range result.Agents {
		tierCounts[agent.Tier]++
	}

	t.Logf("✅ agents.list: total=%d, initialized=%v", result.Total, result.SwarmInitialized)
	t.Logf("   Tier breakdown: core=%d, specialist=%d, support=%d",
		tierCounts["core"], tierCounts["specialist"], tierCounts["support"])
}

// TestAgentsStatus tests the agents.status RPC method.
func TestAgentsStatus(t *testing.T) {
	t.Log("Testing agents.status RPC method...")

	resp, err := callRPC(t, "agents.status", nil)
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s", resp.Error.Message)
	}

	var result AgentsStatusResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Validate 40 total agents
	if result.TotalAgents != 40 {
		t.Errorf("Expected 40 total agents, got %d", result.TotalAgents)
	}

	// Validate active count
	if result.ActiveAgents != 40 {
		t.Errorf("Expected 40 active agents, got %d", result.ActiveAgents)
	}

	// Validate idle count
	if result.IdleAgents != 40 {
		t.Errorf("Expected 40 idle agents, got %d", result.IdleAgents)
	}

	// Should be initialized
	if !result.IsInitialized {
		t.Error("Expected swarm to be initialized")
	}

	t.Logf("✅ agents.status: total=%d, active=%d, idle=%d, busy=%d, uptime=%.1fs",
		result.TotalAgents, result.ActiveAgents, result.IdleAgents,
		result.BusyAgents, result.UptimeSeconds)
}

// TestCompressionJobsList tests the compression.jobs.list RPC method.
func TestCompressionJobsList(t *testing.T) {
	t.Log("Testing compression.jobs.list RPC method...")

	resp, err := callRPC(t, "compression.jobs.list", map[string]interface{}{})
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s", resp.Error.Message)
	}

	var result CompressionJobsResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Should return empty list initially
	if result.Jobs == nil {
		t.Error("Expected jobs array (can be empty)")
	}

	t.Logf("✅ compression.jobs.list: jobs=%d, total=%d", len(result.Jobs), result.Total)
}

// TestMethodNotFound tests that unknown methods return proper errors.
func TestMethodNotFound(t *testing.T) {
	t.Log("Testing unknown method handling...")

	resp, err := callRPC(t, "unknown.method", nil)
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error == nil {
		t.Fatal("Expected error for unknown method")
	}

	if resp.Error.Code != -32601 {
		t.Errorf("Expected error code -32601, got %d", resp.Error.Code)
	}

	t.Logf("✅ Method not found: code=%d, message=%s", resp.Error.Code, resp.Error.Message)
}

// TestAgentTierFiltering tests filtering agents by tier.
func TestAgentTierFiltering(t *testing.T) {
	t.Log("Testing agent tier filtering...")

	// Test core tier filter
	resp, err := callRPC(t, "agents.list", map[string]interface{}{"tier": "core"})
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s", resp.Error.Message)
	}

	var result AgentsListResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Verify all returned agents are core tier
	for _, agent := range result.Agents {
		if agent.Tier != "core" {
			t.Errorf("Expected tier 'core', got '%s' for agent %s", agent.Tier, agent.Name)
		}
	}

	t.Logf("✅ Tier filtering: requested 'core', got %d agents", len(result.Agents))
}

// TestRPCLatency measures RPC call latency.
func TestRPCLatency(t *testing.T) {
	t.Log("Measuring RPC latency...")

	iterations := 10
	var totalDuration time.Duration

	for i := 0; i < iterations; i++ {
		start := time.Now()
		resp, err := callRPC(t, "system.status", nil)
		duration := time.Since(start)

		if err != nil {
			t.Fatalf("RPC call %d failed: %v", i+1, err)
		}
		if resp.Error != nil {
			t.Fatalf("RPC call %d error: %s", i+1, resp.Error.Message)
		}

		totalDuration += duration
	}

	avgLatency := totalDuration / time.Duration(iterations)

	t.Logf("✅ RPC latency: avg=%v over %d calls", avgLatency, iterations)

	// Warn if latency is too high
	if avgLatency > 500*time.Millisecond {
		t.Logf("⚠️  Warning: Average latency exceeds 500ms")
	}
}

// TestConcurrentRPCCalls tests concurrent RPC calls.
func TestConcurrentRPCCalls(t *testing.T) {
	t.Log("Testing concurrent RPC calls...")

	concurrency := 10
	done := make(chan error, concurrency)

	start := time.Now()
	for i := 0; i < concurrency; i++ {
		go func(id int) {
			resp, err := callRPC(t, "system.status", nil)
			if err != nil {
				done <- fmt.Errorf("call %d failed: %w", id, err)
				return
			}
			if resp.Error != nil {
				done <- fmt.Errorf("call %d rpc error: %s", id, resp.Error.Message)
				return
			}
			done <- nil
		}(i)
	}

	// Collect results
	var errors []error
	for i := 0; i < concurrency; i++ {
		if err := <-done; err != nil {
			errors = append(errors, err)
		}
	}

	duration := time.Since(start)

	if len(errors) > 0 {
		for _, err := range errors {
			t.Errorf("Concurrent call error: %v", err)
		}
		t.Fatalf("%d/%d concurrent calls failed", len(errors), concurrency)
	}

	t.Logf("✅ Concurrent RPC: %d calls completed in %v", concurrency, duration)
}

// TestMain runs before/after all tests.
func TestMain(m *testing.M) {
	// Check if Python engine is running
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(pythonRPCURL)
	if err != nil {
		fmt.Println("⚠️  Python RPC engine not reachable at", pythonRPCURL)
		fmt.Println("   Please ensure the Python engine is running:")
		fmt.Println("   cd src/engined && python -m uvicorn engined.main:create_app --factory --port 8002")
		os.Exit(1)
	}
	resp.Body.Close()

	fmt.Println("═══════════════════════════════════════════════════════")
	fmt.Println("  SigmaVault NAS OS - gRPC Integration Tests")
	fmt.Println("  Python RPC Engine:", pythonRPCURL)
	fmt.Println("═══════════════════════════════════════════════════════")

	os.Exit(m.Run())
}
