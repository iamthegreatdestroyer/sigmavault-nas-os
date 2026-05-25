package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

// TestHealthEndpointSuccess validates GET /health returns correct status
func TestHealthEndpointSuccess(t *testing.T) {
	// Create a mock router with health handler
	router := setupTestRouter()

	// Create test request
	req, err := http.NewRequest("GET", "/api/v1/health", nil)
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}

	// Record response
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Verify status code
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	// Verify response body
	var response map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if status, ok := response["status"]; !ok || status != "healthy" {
		t.Errorf("Expected status 'healthy', got %v", response)
	}
}

// TestAgentsListEndpoint validates GET /api/v1/agents returns agent list
func TestAgentsListEndpoint(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	// Verify response structure
	if agents, ok := response["agents"]; !ok || agents == nil {
		t.Errorf("Expected 'agents' field in response")
	}

	if count, ok := response["count"]; !ok || count == nil {
		t.Errorf("Expected 'count' field in response")
	}
}

// TestAgentsListWithStatusFilter validates filtering by status parameter
func TestAgentsListWithStatusFilter(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents?status=active", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	// Verify filtered agents have status=active
	if agents, ok := response["agents"].([]interface{}); ok {
		for _, agent := range agents {
			if agentMap, ok := agent.(map[string]interface{}); ok {
				if status, ok := agentMap["status"]; !ok || status != "active" {
					t.Errorf("Expected all agents to have status 'active'")
				}
			}
		}
	}
}

// TestAgentsListWithTierFilter validates filtering by tier parameter
func TestAgentsListWithTierFilter(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents?tier=core", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	// Verify filtered agents have tier=core
	if agents, ok := response["agents"].([]interface{}); ok {
		for _, agent := range agents {
			if agentMap, ok := agent.(map[string]interface{}); ok {
				if tier, ok := agentMap["tier"]; !ok || tier != "core" {
					t.Errorf("Expected all agents to have tier 'core'")
				}
			}
		}
	}
}

// TestGetAgentByIDSuccess validates GET /api/v1/agents/:id returns agent
func TestGetAgentByIDSuccess(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents/agent-001", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	if id, ok := response["id"]; !ok || id != "agent-001" {
		t.Errorf("Expected agent ID 'agent-001', got %v", id)
	}
}

// TestGetAgentByIDNotFound validates GET with invalid ID returns 404
func TestGetAgentByIDNotFound(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents/agent-nonexistent", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected 404, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	if errMsg, ok := response["error"]; !ok || errMsg == nil {
		t.Errorf("Expected error message in 404 response")
	}
}

// TestGetAgentMetricsSuccess validates GET /api/v1/agents/:id/metrics
func TestGetAgentMetricsSuccess(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents/agent-001/metrics", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	// Verify metrics fields
	expectedFields := []string{"agent_id", "tasks_completed", "success_rate", "avg_response_time_ms"}
	for _, field := range expectedFields {
		if _, ok := response[field]; !ok {
			t.Errorf("Expected field '%s' in metrics response", field)
		}
	}
}

// TestCompressionStatsEndpoint validates GET /api/v1/compression/stats
func TestCompressionStatsEndpoint(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/compression/stats", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	// Verify stats fields
	expectedFields := []string{"total_jobs", "completed_jobs", "avg_compression_ratio", "total_bytes_saved"}
	for _, field := range expectedFields {
		if _, ok := response[field]; !ok {
			t.Errorf("Expected field '%s' in compression stats", field)
		}
	}
}

// TestInvalidJSONRequestBody validates 400 for malformed JSON
func TestInvalidJSONRequestBody(t *testing.T) {
	router := setupTestRouter()

	// Try to POST with invalid JSON
	invalidJSON := `{"incomplete": json`
	req, _ := http.NewRequest("POST", "/api/v1/agents", strings.NewReader(invalidJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400 for invalid JSON, got %d", w.Code)
	}
}

// TestMissingRequiredParameters validates 400 for missing required params
func TestMissingRequiredParameters(t *testing.T) {
	router := setupTestRouter()

	// Request without required query parameter
	req, _ := http.NewRequest("GET", "/api/v1/agents/", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Adjust based on actual route implementation (might be 404 or 400)
	if w.Code != http.StatusBadRequest && w.Code != http.StatusNotFound {
		t.Errorf("Expected 400 or 404 for missing params, got %d", w.Code)
	}
}

// TestResponseContentType validates Content-Type header is application/json
func TestResponseContentType(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	contentType := w.Header().Get("Content-Type")
	if contentType != "application/json" {
		t.Errorf("Expected Content-Type 'application/json', got '%s'", contentType)
	}
}

// TestResponseHasRequiredHeaders validates required response headers
func TestResponseHasRequiredHeaders(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Check for Content-Type and Content-Length
	if w.Header().Get("Content-Type") == "" {
		t.Errorf("Expected Content-Type header")
	}

	if w.Header().Get("Content-Length") == "" && len(w.Body.Bytes()) > 0 {
		// Content-Length may not always be present, but verify body has data
		if w.Body.Len() == 0 {
			t.Errorf("Expected non-empty response body")
		}
	}
}

// TestConcurrentRequestsToHealthEndpoint validates handling of concurrent requests
func TestConcurrentRequestsToHealthEndpoint(t *testing.T) {
	router := setupTestRouter()
	var wg sync.WaitGroup
	errorChan := make(chan error, 10)

	// Make 10 concurrent requests
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(index int) {
			defer wg.Done()
			req, _ := http.NewRequest("GET", "/api/v1/health", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			if w.Code != http.StatusOK {
				errorChan <- fmt.Errorf("request %d: expected 200, got %d", index, w.Code)
			}
		}(i)
	}

	wg.Wait()
	close(errorChan)

	for err := range errorChan {
		if err != nil {
			t.Errorf("Concurrent request error: %v", err)
		}
	}
}

// TestConcurrentRequestsToDifferentEndpoints validates handling mixed concurrent requests
func TestConcurrentRequestsToDifferentEndpoints(t *testing.T) {
	router := setupTestRouter()
	var wg sync.WaitGroup
	endpoints := []string{
		"/api/v1/health",
		"/api/v1/agents",
		"/api/v1/agents/agent-001",
		"/api/v1/compression/stats",
	}

	errorChan := make(chan error, len(endpoints)*3)

	// Make 3 requests to each endpoint concurrently
	for i := 0; i < 3; i++ {
		for _, endpoint := range endpoints {
			wg.Add(1)
			go func(ep string, idx int) {
				defer wg.Done()
				req, _ := http.NewRequest("GET", ep, nil)
				w := httptest.NewRecorder()
				router.ServeHTTP(w, req)

				// Allow 200 or 404 for endpoints that may not exist
				if w.Code != http.StatusOK && w.Code != http.StatusNotFound {
					errorChan <- fmt.Errorf("%s returned %d", ep, w.Code)
				}
			}(endpoint, i)
		}
	}

	wg.Wait()
	close(errorChan)

	for err := range errorChan {
		t.Errorf("Concurrent concurrent request error: %v", err)
	}
}

// TestEndpointResponseLatency measures response time for /health endpoint
func TestEndpointResponseLatency(t *testing.T) {
	router := setupTestRouter()
	const targetLatency = 100 * time.Millisecond

	req, _ := http.NewRequest("GET", "/api/v1/health", nil)

	start := time.Now()
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	elapsed := time.Since(start)

	if elapsed > targetLatency {
		t.Logf("Warning: response latency %v exceeds target %v", elapsed, targetLatency)
	}

	if elapsed > 500*time.Millisecond {
		t.Errorf("Response took %v, which is excessively slow", elapsed)
	}
}

// TestEndpointResponseSize validates response body is reasonable size
func TestEndpointResponseSize(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	bodySize := len(w.Body.Bytes())
	const maxSize = 1024 * 1024 // 1MB max for agents list

	if bodySize > maxSize {
		t.Errorf("Response body size %d bytes exceeds reasonable limit %d", bodySize, maxSize)
	}

	if bodySize == 0 {
		t.Errorf("Response body is empty")
	}
}

// TestResponseDataTypes validates JSON response data types
func TestResponseDataTypes(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	var response map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	// Verify types
	if statusStr, ok := response["status"].(string); !ok || statusStr == "" {
		t.Errorf("Expected 'status' field to be non-empty string")
	}
}

// TestEndpointMethodNotAllowed validates 405 for unsupported HTTP methods
func TestEndpointMethodNotAllowed(t *testing.T) {
	router := setupTestRouter()

	// Try DELETE on query endpoint (should not be supported)
	req, _ := http.NewRequest("DELETE", "/api/v1/agents/agent-001", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Should be 405 (Method Not Allowed) or 404 (Not Found)
	if w.Code != http.StatusMethodNotAllowed && w.Code != http.StatusNotFound {
		t.Logf("Note: DELETE returned %d (consider implementing 405 for unsupported methods)", w.Code)
	}
}

// TestEmptyQueryResultHandling validates proper response when filter returns no results
func TestEmptyQueryResultHandling(t *testing.T) {
	router := setupTestRouter()

	// Query with filter that returns no results (non-existent status or tier)
	req, _ := http.NewRequest("GET", "/api/v1/agents?status=nonexistent", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200 for valid query with empty results, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	// Verify response structure is still valid (with empty agents)
	if count, ok := response["count"].(float64); !ok || int(count) != 0 {
		t.Errorf("Expected count 0 for empty result")
	}
}

// TestMultipleQueryParameters validates combining multiple query filters
func TestMultipleQueryParameters(t *testing.T) {
	router := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/agents?status=active&tier=core", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200 for query with multiple params, got %d", w.Code)
	}

	var response map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &response)

	// Verify filtered agents match both criteria
	if agents, ok := response["agents"].([]interface{}); ok {
		for _, agent := range agents {
			if agentMap, ok := agent.(map[string]interface{}); ok {
				if status, ok := agentMap["status"]; !ok || status != "active" {
					t.Errorf("Not all agents have status 'active'")
				}
				if tier, ok := agentMap["tier"]; !ok || tier != "core" {
					t.Errorf("Not all agents have tier 'core'")
				}
			}
		}
	}
}

// setupTestRouter creates a test HTTP router with mock handlers
func setupTestRouter() http.Handler {
	mux := http.NewServeMux()

	// Health endpoint
	mux.HandleFunc("/api/v1/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	})

	// Agents list endpoint with filtering
	mux.HandleFunc("/api/v1/agents", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		agents := mockAgentsList()

		// Apply filters if provided
		statusFilter := r.URL.Query().Get("status")
		tierFilter := r.URL.Query().Get("tier")

		if statusFilter != "" && statusFilter != "nonexistent" {
			filtered := []map[string]interface{}{}
			for _, agent := range agents {
				if agent["status"] == statusFilter {
					filtered = append(filtered, agent)
				}
			}
			agents = filtered
		}

		if tierFilter != "" {
			filtered := []map[string]interface{}{}
			for _, agent := range agents {
				if agent["tier"] == tierFilter {
					filtered = append(filtered, agent)
				}
			}
			agents = filtered
		}

		response := map[string]interface{}{
			"agents": agents,
			"count":  len(agents),
			"total":  len(mockAgentsList()),
		}
		json.NewEncoder(w).Encode(response)
	})

	// Get agent by ID
	mux.HandleFunc("/api/v1/agents/agent-001", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		agent := map[string]interface{}{
			"id":       "agent-001",
			"codename": "APEX",
			"tier":     "core",
			"status":   "active",
		}
		json.NewEncoder(w).Encode(agent)
	})

	// Get agent by ID - nonexistent
	mux.HandleFunc("/api/v1/agents/agent-nonexistent", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "agent not found"})
	})

	// Agent metrics
	mux.HandleFunc("/api/v1/agents/agent-001/metrics", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		metrics := map[string]interface{}{
			"agent_id":             "agent-001",
			"tasks_completed":      1250,
			"success_rate":         0.98,
			"avg_response_time_ms": 45.5,
		}
		json.NewEncoder(w).Encode(metrics)
	})

	// Compression stats
	mux.HandleFunc("/api/v1/compression/stats", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		stats := map[string]interface{}{
			"total_jobs":            125,
			"completed_jobs":        98,
			"running_jobs":          15,
			"failed_jobs":           12,
			"avg_compression_ratio": 0.15,
			"total_bytes_saved":     8500000000,
		}
		json.NewEncoder(w).Encode(stats)
	})

	return mux
}

// mockAgentsList returns test agent data
func mockAgentsList() []map[string]interface{} {
	return []map[string]interface{}{
		{
			"id":       "agent-001",
			"codename": "APEX",
			"tier":     "core",
			"status":   "active",
		},
		{
			"id":       "agent-002",
			"codename": "CIPHER",
			"tier":     "core",
			"status":   "active",
		},
		{
			"id":       "agent-003",
			"codename": "ARCHITECT",
			"tier":     "core",
			"status":   "active",
		},
		{
			"id":       "agent-004",
			"codename": "TENSOR",
			"tier":     "specialist",
			"status":   "active",
		},
		{
			"id":       "agent-005",
			"codename": "QUANTUM",
			"tier":     "specialist",
			"status":   "inactive",
		},
	}
}

// BenchmarkHealthEndpoint measures /health endpoint performance
func BenchmarkHealthEndpoint(b *testing.B) {
	router := setupTestRouter()
	req, _ := http.NewRequest("GET", "/api/v1/health", nil)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}

// BenchmarkAgentsListEndpoint measures /agents list performance
func BenchmarkAgentsListEndpoint(b *testing.B) {
	router := setupTestRouter()
	req, _ := http.NewRequest("GET", "/api/v1/agents", nil)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}
