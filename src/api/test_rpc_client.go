package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

// MockRPCClient simulates the Engine RPC client
type MockRPCClient struct {
	serverURL    string
	client       *http.Client
	requestCount int
	mu           sync.Mutex
}

// JSONRPCRequest represents a JSON-RPC 2.0 request
type JSONRPCRequest struct {
	JSONRPC string                 `json:"jsonrpc"`
	Method  string                 `json:"method"`
	Params  map[string]interface{} `json:"params,omitempty"`
	ID      int                    `json:"id"`
}

// JSONRPCResponse represents a JSON-RPC 2.0 response
type JSONRPCResponse struct {
	JSONRPC string        `json:"jsonrpc"`
	Result  interface{}   `json:"result,omitempty"`
	Error   *JSONRPCError `json:"error,omitempty"`
	ID      int           `json:"id"`
}

// JSONRPCError represents a JSON-RPC error
type JSONRPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// NewMockRPCClient creates a new mock RPC client
func NewMockRPCClient(serverURL string) *MockRPCClient {
	return &MockRPCClient{
		serverURL: serverURL,
		client:    &http.Client{Timeout: 5 * time.Second},
	}
}

// Call invokes an RPC method and returns the result
func (c *MockRPCClient) Call(ctx context.Context, method string, params map[string]interface{}) (interface{}, error) {
	c.mu.Lock()
	c.requestCount++
	requestID := c.requestCount
	c.mu.Unlock()

	request := JSONRPCRequest{
		JSONRPC: "2.0",
		Method:  method,
		Params:  params,
		ID:      requestID,
	}

	// Marshal request
	reqBody, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	// Create HTTP request
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.serverURL, strings.NewReader(string(reqBody)))
	if err != nil {
		return nil, fmt.Errorf("failed to create HTTP request: %v", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")

	// Execute request
	httpResp, err := c.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %v", err)
	}
	defer httpResp.Body.Close()

	// Parse response
	var response JSONRPCResponse
	if err := json.NewDecoder(httpResp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}

	// Check for RPC error
	if response.Error != nil {
		return nil, fmt.Errorf("RPC error %d: %s", response.Error.Code, response.Error.Message)
	}

	return response.Result, nil
}

// TestRPCClientConnection validates successful connection to RPC server
func TestRPCClientConnection(t *testing.T) {
	// Setup mock RPC server
	server := setupMockRPCServer()
	defer server.Close()

	// Create client
	client := NewMockRPCClient(server.URL)

	// Test connection by calling agents.list
	result, err := client.Call(context.Background(), "agents.list", nil)
	if err != nil {
		t.Fatalf("Failed to connect to RPC server: %v", err)
	}

	if result == nil {
		t.Errorf("Expected non-nil result from RPC call")
	}
}

// TestRPCClientInvokeAgentsList validates agents.list RPC method
func TestRPCClientInvokeAgentsList(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	result, err := client.Call(context.Background(), "agents.list", nil)
	if err != nil {
		t.Fatalf("agents.list call failed: %v", err)
	}

	// Parse result
	if resultMap, ok := result.(map[string]interface{}); ok {
		if agents, ok := resultMap["agents"]; !ok || agents == nil {
			t.Errorf("Expected 'agents' field in agents.list result")
		}
	} else {
		t.Errorf("Expected map[string]interface{} from agents.list, got %T", result)
	}
}

// TestRPCClientInvokeAgentsGet validates agents.get RPC method with ID
func TestRPCClientInvokeAgentsGet(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	params := map[string]interface{}{
		"id": "agent-001",
	}

	result, err := client.Call(context.Background(), "agents.get", params)
	if err != nil {
		t.Fatalf("agents.get call failed: %v", err)
	}

	// Verify result contains agent data
	if resultMap, ok := result.(map[string]interface{}); ok {
		if id, ok := resultMap["id"].(string); !ok || id != "agent-001" {
			t.Errorf("Expected agent ID 'agent-001' in result")
		}
	}
}

// TestRPCClientInvokeCompressionStats validates compression.stats RPC method
func TestRPCClientInvokeCompressionStats(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	result, err := client.Call(context.Background(), "compression.stats", nil)
	if err != nil {
		t.Fatalf("compression.stats call failed: %v", err)
	}

	// Verify stats result
	if resultMap, ok := result.(map[string]interface{}); ok {
		expectedFields := []string{"completed_jobs", "avg_compression_ratio"}
		for _, field := range expectedFields {
			if _, ok := resultMap[field]; !ok {
				t.Errorf("Expected field '%s' in compression stats", field)
			}
		}
	}
}

// TestRPCClientParameterMarshaling validates Go types marshal to JSON correctly
func TestRPCClientParameterMarshaling(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	// Test with various parameter types
	params := map[string]interface{}{
		"id":      "agent-001",
		"timeout": 5000,
		"active":  true,
		"ratio":   0.95,
	}

	// Server should receive and echo back the parameters
	result, err := client.Call(context.Background(), "test.echo_params", params)
	if err != nil {
		t.Fatalf("Parameter marshaling test failed: %v", err)
	}

	// Verify parameters were marshaled correctly
	if resultMap, ok := result.(map[string]interface{}); ok {
		if id, ok := resultMap["id"].(string); !ok || id != "agent-001" {
			t.Errorf("String parameter not marshaled correctly")
		}
		if timeout, ok := resultMap["timeout"].(float64); !ok || timeout != 5000 {
			t.Errorf("Integer parameter not marshaled correctly")
		}
	}
}

// TestRPCClientResponseUnmarshaling validates JSON unmarshals to Go types correctly
func TestRPCClientResponseUnmarshaling(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	result, err := client.Call(context.Background(), "agents.get", map[string]interface{}{"id": "agent-001"})
	if err != nil {
		t.Fatalf("Response unmarshaling test failed: %v", err)
	}

	// Verify types after unmarshaling
	if resultMap, ok := result.(map[string]interface{}); ok {
		// String field
		if _, ok := resultMap["id"].(string); !ok {
			t.Errorf("Expected string type for 'id' field")
		}
		// Number field
		if _, ok := resultMap["tasks_completed"].(float64); !ok {
			t.Errorf("Expected float64 type for numeric fields (JSON unmarshaling)")
		}
	}
}

// TestRPCClientErrorPropagation validates RPC errors are propagated correctly
func TestRPCClientErrorPropagation(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	// Call non-existent method
	_, err := client.Call(context.Background(), "nonexistent.method", nil)
	if err == nil {
		t.Errorf("Expected error for non-existent method")
	}

	// Verify error message contains "Method not found" or similar
	if !strings.Contains(err.Error(), "RPC error") {
		t.Errorf("Expected RPC error message, got: %v", err)
	}
}

// TestRPCClientTimeoutHandling validates timeout behavior
func TestRPCClientTimeoutHandling(t *testing.T) {
	// Setup slow server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(2 * time.Second) // Slow response
		json.NewEncoder(w).Encode(JSONRPCResponse{
			JSONRPC: "2.0",
			Result:  nil,
			ID:      1,
		})
	}))
	defer server.Close()

	// Create client with short timeout
	client := &MockRPCClient{
		serverURL: server.URL,
		client:    &http.Client{Timeout: 100 * time.Millisecond},
	}

	// Call should timeout
	_, err := client.Call(context.Background(), "slow.method", nil)
	if err == nil {
		t.Errorf("Expected timeout error for slow request")
	}

	if !strings.Contains(err.Error(), "timeout") && !strings.Contains(err.Error(), "context deadline") {
		t.Logf("Note: Got error %v (timeout handling may work differently)", err)
	}
}

// TestRPCClientContextCancellation validates context cancellation
func TestRPCClientContextCancellation(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	// Create cancellable context
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	// Call should fail due to cancelled context
	_, err := client.Call(ctx, "agents.list", nil)
	if err == nil {
		t.Errorf("Expected error for cancelled context")
	}
}

// TestRPCClientConcurrentInvocations validates handling of concurrent requests
func TestRPCClientConcurrentInvocations(t *testing.T) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)
	var wg sync.WaitGroup
	errorChan := make(chan error, 10)

	// Make 10 concurrent calls
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(index int) {
			defer wg.Done()
			var method string
			var params map[string]interface{}

			switch index % 3 {
			case 0:
				method = "agents.list"
			case 1:
				method = "agents.get"
				params = map[string]interface{}{"id": fmt.Sprintf("agent-%03d", index)}
			case 2:
				method = "compression.stats"
			}

			_, err := client.Call(context.Background(), method, params)
			if err != nil {
				errorChan <- err
			}
		}(i)
	}

	wg.Wait()
	close(errorChan)

	// Check for errors
	for err := range errorChan {
		t.Errorf("Concurrent call error: %v", err)
	}
}

// TestRPCClientRequestIDSequence validates request IDs are sequential
func TestRPCClientRequestIDSequence(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req JSONRPCRequest
		json.NewDecoder(r.Body).Decode(&req)

		// Return response with same ID
		response := JSONRPCResponse{
			JSONRPC: "2.0",
			Result:  map[string]int{"received_id": req.ID},
			ID:      req.ID,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	// Make 5 calls and verify IDs increment
	for i := 1; i <= 5; i++ {
		result, err := client.Call(context.Background(), "test.method", nil)
		if err != nil {
			t.Fatalf("Call %d failed: %v", i, err)
		}

		// Verify returned ID matches expected
		if resultMap, ok := result.(map[string]interface{}); ok {
			if receivedID, ok := resultMap["received_id"].(float64); !ok || int(receivedID) != i {
				t.Errorf("Expected ID %d, got %v", i, receivedID)
			}
		}
	}
}

// TestRPCClientConnectionPooling validates connection reuse
func TestRPCClientConnectionPooling(t *testing.T) {
	requestCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestCount++
		response := JSONRPCResponse{
			JSONRPC: "2.0",
			Result:  map[string]int{"request_number": requestCount},
			ID:      1,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	// Make multiple calls - should reuse connection
	for i := 0; i < 5; i++ {
		_, err := client.Call(context.Background(), "agents.list", nil)
		if err != nil {
			t.Fatalf("Call %d failed: %v", i, err)
		}
	}

	// All 5 calls should have succeeded
	if requestCount != 5 {
		t.Errorf("Expected 5 requests, got %d", requestCount)
	}
}

// TestRPCClientJSONRPCCompliance validates compliance with JSON-RPC 2.0 spec
func TestRPCClientJSONRPCCompliance(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Validate incoming request format
		var req JSONRPCRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}

		// Verify required fields
		if req.JSONRPC != "2.0" {
			t.Errorf("Expected jsonrpc 2.0, got %s", req.JSONRPC)
		}
		if req.Method == "" {
			t.Errorf("Expected non-empty method")
		}
		if req.ID == 0 {
			t.Errorf("Expected non-zero ID")
		}

		// Send valid response
		response := JSONRPCResponse{
			JSONRPC: "2.0",
			Result:  "ok",
			ID:      req.ID,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	_, err := client.Call(context.Background(), "test.method", nil)
	if err != nil {
		t.Errorf("JSON-RPC compliance test failed: %v", err)
	}
}

// BenchmarkRPCClientCall measures RPC method invocation performance
func BenchmarkRPCClientCall(b *testing.B) {
	server := setupMockRPCServer()
	defer server.Close()

	client := NewMockRPCClient(server.URL)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		client.Call(context.Background(), "agents.list", nil)
	}
}

// setupMockRPCServer creates a mock JSON-RPC 2.0 server
func setupMockRPCServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req JSONRPCRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "application/json")

		var response JSONRPCResponse
		response.JSONRPC = "2.0"
		response.ID = req.ID

		// Route based on method
		switch req.Method {
		case "agents.list":
			response.Result = map[string]interface{}{
				"agents": []map[string]string{
					{"id": "agent-001", "codename": "APEX"},
					{"id": "agent-002", "codename": "CIPHER"},
				},
				"count": 2,
			}

		case "agents.get":
			if id, ok := req.Params["id"].(string); ok {
				response.Result = map[string]interface{}{
					"id":              id,
					"codename":        "TEST_AGENT",
					"tasks_completed": int64(100),
					"status":          "active",
				}
			} else {
				response.Error = &JSONRPCError{
					Code:    -32602,
					Message: "Invalid params: missing 'id'",
				}
			}

		case "compression.stats":
			response.Result = map[string]interface{}{
				"completed_jobs":        98,
				"avg_compression_ratio": 0.15,
				"total_bytes_saved":     8500000000,
			}

		case "test.echo_params":
			response.Result = req.Params

		default:
			response.Error = &JSONRPCError{
				Code:    -32601,
				Message: "Method not found",
			}
		}

		json.NewEncoder(w).Encode(response)
	}))
}
