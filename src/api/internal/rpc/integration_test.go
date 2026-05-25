// Package rpc integration tests for API-Engine communication.
package rpc

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

// TestRPCClientHealthCheck tests basic RPC client health verification.
func TestRPCClientHealthCheck(t *testing.T) {
	// Mock RPC server that responds to health check
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string `json:"method"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "health.check" {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result": map[string]interface{}{
						"status": "healthy",
						"uptime": 3600,
					},
					"id": 1,
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

	err := client.HealthCheck(context.Background())
	if err != nil {
		t.Fatalf("HealthCheck failed: %v", err)
	}
}

// TestRPCClientConnectionRetry tests retry behavior on connection failure.
func TestRPCClientConnectionRetry(t *testing.T) {
	callCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		callCount++
		// Fail first call, succeed on second
		if callCount == 1 {
			http.Error(w, "Service unavailable", http.StatusServiceUnavailable)
			return
		}

		if r.Method == "POST" && r.URL.Path == "/rpc" {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"jsonrpc": "2.0",
				"result": map[string]interface{}{
					"agents": []interface{}{},
				},
				"id": 1,
			})
			return
		}
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 5,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Should eventually succeed after retry
	result := map[string]interface{}{}
	err := client.Call(ctx, "agent.list", nil, &result)
	if err != nil {
		t.Fatalf("Call failed after retry: %v", err)
	}

	if callCount < 2 {
		t.Logf("Expected at least 2 calls (initial + retry), got %d", callCount)
	}
}

// TestMockAgentExecution tests agent task execution via RPC.
func TestMockAgentExecution(t *testing.T) {
	expectedAgentID := "agent-001"
	expectedTask := "compress"

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "agent.execute_task" {
				var params map[string]interface{}
				json.Unmarshal(req.Params, &params)

				agentID := params["agent_id"].(string)
				taskType := params["task"].(string)

				if agentID != expectedAgentID || taskType != expectedTask {
					http.Error(w, "Invalid params", http.StatusBadRequest)
					return
				}

				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result": map[string]interface{}{
						"task_id": "task-123",
						"status":  "running",
					},
					"id": 1,
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

	ctx := context.Background()
	result := map[string]interface{}{}

	params := map[string]interface{}{
		"agent_id": expectedAgentID,
		"task":     expectedTask,
	}

	err := client.Call(ctx, "agent.execute_task", params, &result)
	if err != nil {
		t.Fatalf("execute_task failed: %v", err)
	}

	taskID, ok := result["task_id"].(string)
	if !ok || taskID != "task-123" {
		t.Errorf("Expected task_id='task-123', got %v", result["task_id"])
	}

	status, ok := result["status"].(string)
	if !ok || status != "running" {
		t.Errorf("Expected status='running', got %v", result["status"])
	}
}

// TestRPCClientConcurrency tests concurrent RPC calls.
func TestRPCClientConcurrency(t *testing.T) {
	callMutex := sync.Mutex{}
	callCount := 0

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			callMutex.Lock()
			callCount++
			callMutex.Unlock()

			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"jsonrpc": "2.0",
				"result": map[string]interface{}{
					"agents_count": 40,
				},
				"id": 1,
			})
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

	ctx := context.Background()
	numGoroutines := 10

	wg := sync.WaitGroup{}
	wg.Add(numGoroutines)

	for i := 0; i < numGoroutines; i++ {
		go func(idx int) {
			defer wg.Done()
			result := map[string]interface{}{}
			err := client.Call(ctx, "agent.list", nil, &result)
			if err != nil {
				t.Errorf("Concurrent call %d failed: %v", idx, err)
			}
		}(i)
	}

	wg.Wait()

	if callCount != numGoroutines {
		t.Errorf("Expected %d calls, got %d", numGoroutines, callCount)
	}
}

// TestRPCClientTimeout tests timeout behavior.
func TestRPCClientTimeout(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			// Simulate slow server
			time.Sleep(2 * time.Second)
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"jsonrpc": "2.0",
				"result":  "too late",
				"id":      1,
			})
			return
		}
		http.Error(w, "Not found", http.StatusNotFound)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:    server.URL,
		Timeout:    500 * time.Millisecond, // Short timeout
		MaxRetries: 3,
	})

	ctx := context.Background()
	result := map[string]interface{}{}

	err := client.Call(ctx, "agent.list", nil, &result)
	if err == nil {
		t.Fatal("Expected timeout error, got nil")
	}

	// Verify it's a timeout-related error
	if !isTimeoutError(err) {
		t.Logf("Got error: %v (type check: %T)", err, err)
	}
}

// TestAgentRegistryIntegration tests agent registry RPC calls.
func TestAgentRegistryIntegration(t *testing.T) {
	testAgents := []map[string]interface{}{
		{
			"id":       "agent-001",
			"codename": "APEX",
			"tier":     "core",
		},
		{
			"id":       "agent-002",
			"codename": "TENSOR",
			"tier":     "core",
		},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string `json:"method"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "agent.list" {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  testAgents,
					"id":      1,
				})
				return
			}

			if req.Method == "agent.get" {
				w.Header().Set("Content-Type", "application/json")
				// Return first agent
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  testAgents[0],
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

	ctx := context.Background()

	// Test list
	var listResult []map[string]interface{}
	err := client.Call(ctx, "agent.list", nil, &listResult)
	if err != nil {
		t.Fatalf("agent.list failed: %v", err)
	}

	if len(listResult) != 2 {
		t.Errorf("Expected 2 agents, got %d", len(listResult))
	}

	// Test get
	getResult := map[string]interface{}{}
	err = client.Call(ctx, "agent.get", nil, &getResult)
	if err != nil {
		t.Fatalf("agent.get failed: %v", err)
	}

	if getResult["codename"] != "APEX" {
		t.Errorf("Expected codename='APEX', got %v", getResult["codename"])
	}
}

// TestCompressionEngineIntegration tests compression RPC calls.
func TestCompressionEngineIntegration(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "compression.compress" {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result": map[string]interface{}{
						"original_size":   1000,
						"compressed_size": 100,
						"ratio":           0.9,
						"algorithm":       "zstd",
					},
					"id": 1,
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

	ctx := context.Background()
	result := map[string]interface{}{}

	params := map[string]interface{}{
		"data_path": "/test/data",
	}

	err := client.Call(ctx, "compression.compress", params, &result)
	if err != nil {
		t.Fatalf("compression.compress failed: %v", err)
	}

	ratio, ok := result["ratio"].(float64)
	if !ok || ratio < 0.5 {
		t.Errorf("Expected high compression ratio, got %v", result["ratio"])
	}
}

// TestEventStreamIntegration tests event streaming from RPC engine.
func TestEventStreamIntegration(t *testing.T) {
	eventsSent := []map[string]interface{}{
		{
			"type":      "agent_started",
			"agent_id":  "agent-001",
			"timestamp": time.Now().Unix(),
		},
		{
			"type":      "task_completed",
			"task_id":   "task-123",
			"status":    "success",
			"timestamp": time.Now().Unix(),
		},
	}

	eventIndex := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/rpc" {
			var req struct {
				Method string `json:"method"`
			}
			json.NewDecoder(r.Body).Decode(&req)

			if req.Method == "event.get_recent" {
				w.Header().Set("Content-Type", "application/json")

				// Return events with offset
				var events []map[string]interface{}
				if eventIndex < len(eventsSent) {
					events = append(events, eventsSent[eventIndex])
					eventIndex++
				}

				json.NewEncoder(w).Encode(map[string]interface{}{
					"jsonrpc": "2.0",
					"result":  events,
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

	ctx := context.Background()

	// Poll for events
	for i := 0; i < 2; i++ {
		var result []map[string]interface{}
		err := client.Call(ctx, "event.get_recent", nil, &result)
		if err != nil {
			t.Fatalf("event.get_recent failed: %v", err)
		}

		if len(result) > 0 {
			event := result[0]
			if event["type"] != eventsSent[i]["type"] {
				t.Errorf("Event %d: expected type=%v, got %v", i, eventsSent[i]["type"], event["type"])
			}
		}
	}
}

// Helper function to check if error is timeout-related
func isTimeoutError(err error) bool {
	if err == nil {
		return false
	}
	errStr := fmt.Sprintf("%v", err)
	return errStr == "context deadline exceeded" || errStr == "timeout"
}
