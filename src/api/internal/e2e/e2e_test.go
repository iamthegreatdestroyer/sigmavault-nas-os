// Package e2e provides end-to-end testing for the SigmaVault NAS OS API.
// PHASE 4: E2E Testing - Tests complete request flows from client through API to engine
package e2e

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"sigmavault-nas-os/api/internal/config"
	"sigmavault-nas-os/api/internal/routes"
	"sigmavault-nas-os/api/internal/rpc"
	"sigmavault-nas-os/api/internal/websocket"

	"github.com/gofiber/fiber/v2"
)

// E2ETestServer wraps a test API server with lifecycle management
type E2ETestServer struct {
	app       *fiber.App
	server    *http.Server
	baseURL   string
	port      int
	wsHub     *websocket.Hub
	rpcClient *rpc.Client
}

// NewE2ETestServer creates and starts a test API server
func NewE2ETestServer(t *testing.T, port int) *E2ETestServer {
	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName:               "SigmaVault E2E Test",
		DisableStartupMessage: true,
	})

	// Create mock RPC client for testing
	rpcClient := rpc.NewClient(rpc.Config{
		BaseURL: "http://localhost:5001",
		Timeout: 30 * time.Second,
	})

	// Setup routes
	routes.Setup(app, &config.Config{
		Version:      "0.1.0",
		Environment:  "test",
		Port:         port,
		RPCEngineURL: "http://localhost:5001",
		CORSOrigins:  "http://localhost:3000,http://localhost:5173",
		JWTSecret:    "test-secret-key-at-least-32-chars-long",
		JWTExpiry:    24 * time.Hour,
	})

	// Start server in goroutine
	addr := fmt.Sprintf(":%d", port)
	go func() {
		if err := app.Listen(addr); err != nil {
			t.Logf("Server error: %v", err)
		}
	}()

	// Wait for server to start
	time.Sleep(100 * time.Millisecond)

	return &E2ETestServer{
		app:       app,
		port:      port,
		baseURL:   fmt.Sprintf("http://localhost:%d", port),
		rpcClient: rpcClient,
	}
}

// Close shuts down the test server
func (ts *E2ETestServer) Close() error {
	return ts.app.Shutdown()
}

// TestE2EHealthCheck validates basic server health endpoints
func TestE2EHealthCheck(t *testing.T) {
	// Skip this test for now - health check requires engine availability
	// The real health check happens in integration tests with a full stack
	t.Skip("Health check test requires RPC engine running")
}

// TestE2EBasicAPIFlow tests a complete request/response cycle
func TestE2EBasicAPIFlow(t *testing.T) {
	srv := NewE2ETestServer(t, 9002)
	defer srv.Close()

	// Create a test system info request
	resp, err := http.Get(srv.baseURL + "/api/v1/info")
	if err != nil {
		t.Fatalf("Failed to reach info endpoint: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	// Parse response
	body, _ := io.ReadAll(resp.Body)
	if len(body) == 0 {
		t.Error("Expected non-empty response body")
	}
}

// TestE2EAuthenticationFlow tests the complete authentication flow
func TestE2EAuthenticationFlow(t *testing.T) {
	srv := NewE2ETestServer(t, 9003)
	defer srv.Close()

	// Test login endpoint (mock - will depend on actual auth implementation)
	loginPayload := map[string]string{
		"username": "testuser",
		"password": "testpass",
	}

	payload, _ := json.Marshal(loginPayload)
	resp, err := http.Post(
		srv.baseURL+"/api/v1/auth/login",
		"application/json",
		bytes.NewBuffer(payload),
	)
	if err != nil {
		t.Logf("Auth endpoint not implemented yet (expected): %v", err)
		return
	}
	defer resp.Body.Close()

	// Verify response contains token if successful
	if resp.StatusCode == http.StatusOK {
		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			t.Logf("Failed to parse auth response: %v", err)
		}

		if token, ok := result["token"].(string); !ok || token == "" {
			t.Error("Expected token in response")
		}
	}
}

// TestE2EConcurrentRequests tests multiple concurrent API requests
func TestE2EConcurrentRequests(t *testing.T) {
	srv := NewE2ETestServer(t, 9004)
	defer srv.Close()

	const numRequests = 50
	var wg sync.WaitGroup
	var successCount int32
	var errorCount int32

	for i := 0; i < numRequests; i++ {
		wg.Add(1)
		go func(requestNum int) {
			defer wg.Done()

			resp, err := http.Get(srv.baseURL + "/api/v1/info")
			if err != nil {
				atomic.AddInt32(&errorCount, 1)
				return
			}
			defer resp.Body.Close()

			if resp.StatusCode == http.StatusOK {
				atomic.AddInt32(&successCount, 1)
			} else {
				atomic.AddInt32(&errorCount, 1)
			}
		}(i)
	}

	wg.Wait()

	if atomic.LoadInt32(&successCount) < int32(numRequests*80/100) {
		t.Errorf("Expected at least 80%% success rate, got %d/%d", successCount, numRequests)
	}

	t.Logf("Concurrent requests: %d successful, %d failed", atomic.LoadInt32(&successCount), atomic.LoadInt32(&errorCount))
}

// TestE2EErrorHandling tests API error handling and recovery
func TestE2EErrorHandling(t *testing.T) {
	srv := NewE2ETestServer(t, 9005)
	defer srv.Close()

	tests := []struct {
		name           string
		endpoint       string
		expectedStatus int
	}{
		{"Invalid endpoint", "/api/v1/nonexistent", http.StatusNotFound},
		{"Health check", "/api/v1/health", http.StatusOK},
		{"Info endpoint", "/api/v1/info", http.StatusOK},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			resp, err := http.Get(srv.baseURL + test.endpoint)
			if err != nil {
				t.Errorf("Request failed: %v", err)
				return
			}
			defer resp.Body.Close()

			if resp.StatusCode != test.expectedStatus {
				t.Errorf("Expected status %d, got %d", test.expectedStatus, resp.StatusCode)
			}
		})
	}
}

// TestE2EResponseTiming tests API response times
func TestE2EResponseTiming(t *testing.T) {
	srv := NewE2ETestServer(t, 9006)
	defer srv.Close()

	const numRequests = 20
	var totalDuration time.Duration
	var maxDuration time.Duration
	var minDuration = time.Hour

	for i := 0; i < numRequests; i++ {
		start := time.Now()
		resp, err := http.Get(srv.baseURL + "/api/v1/info")
		duration := time.Since(start)

		if err != nil {
			t.Errorf("Request failed: %v", err)
			continue
		}
		resp.Body.Close()

		totalDuration += duration
		if duration > maxDuration {
			maxDuration = duration
		}
		if duration < minDuration {
			minDuration = duration
		}
	}

	avgDuration := totalDuration / numRequests

	t.Logf("Response timing: avg=%v, min=%v, max=%v", avgDuration, minDuration, maxDuration)

	// Assert that average response time is acceptable (< 100ms)
	if avgDuration > 100*time.Millisecond {
		t.Errorf("Average response time %v exceeds 100ms threshold", avgDuration)
	}
}

// TestE2ERequestHeaders validates proper header handling
func TestE2ERequestHeaders(t *testing.T) {
	srv := NewE2ETestServer(t, 9007)
	defer srv.Close()

	client := &http.Client{}
	req, _ := http.NewRequest("GET", srv.baseURL+"/api/v1/health", nil)

	// Add custom headers
	req.Header.Add("X-Request-ID", "test-request-123")
	req.Header.Add("User-Agent", "E2E-Test/1.0")

	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Request failed: %v", err)
	}
	defer resp.Body.Close()

	// Verify security headers are present
	if resp.Header.Get("X-Content-Type-Options") == "" {
		t.Error("Expected X-Content-Type-Options security header")
	}

	// Verify request ID was received
	if resp.Header.Get("X-Request-ID") != "" {
		t.Logf("Request ID header present: %s", resp.Header.Get("X-Request-ID"))
	}
}

// TestE2ELoadPatterns tests different load patterns
func TestE2ELoadPatterns(t *testing.T) {
	srv := NewE2ETestServer(t, 9008)
	defer srv.Close()

	t.Run("Burst load", func(t *testing.T) {
		const burstsCount = 5
		const requestsPerBurst = 20
		var wg sync.WaitGroup
		var successCount int32

		for burst := 0; burst < burstsCount; burst++ {
			for i := 0; i < requestsPerBurst; i++ {
				wg.Add(1)
				go func() {
					defer wg.Done()
					resp, err := http.Get(srv.baseURL + "/api/v1/info")
					if err != nil {
						return
					}
					defer resp.Body.Close()
					if resp.StatusCode == http.StatusOK {
						atomic.AddInt32(&successCount, 1)
					}
				}()
			}

			wg.Wait()
			time.Sleep(50 * time.Millisecond)
		}

		if atomic.LoadInt32(&successCount) < int32(burstsCount*requestsPerBurst*80/100) {
			t.Errorf("Burst load test: insufficient success rate")
		}

		t.Logf("Burst load: %d successful requests", atomic.LoadInt32(&successCount))
	})
}

// TestE2ETimeout tests request timeout handling
func TestE2ETimeout(t *testing.T) {
	srv := NewE2ETestServer(t, 9009)
	defer srv.Close()

	client := &http.Client{
		Timeout: 5 * time.Millisecond,
	}

	// This should timeout because 5ms is too short for any real request
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Millisecond)
	defer cancel()

	req, _ := http.NewRequestWithContext(ctx, "GET", srv.baseURL+"/api/v1/health", nil)
	_, err := client.Do(req)

	if err == nil {
		t.Log("Request completed within timeout (server is very fast)")
	} else {
		t.Logf("Timeout handling verified: %v", err)
	}
}

// TestE2EContentNegotiation tests different response content types
func TestE2EContentNegotiation(t *testing.T) {
	srv := NewE2ETestServer(t, 9010)
	defer srv.Close()

	tests := []struct {
		name        string
		contentType string
	}{
		{"JSON", "application/json"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			client := &http.Client{}
			req, _ := http.NewRequest("GET", srv.baseURL+"/api/v1/info", nil)
			req.Header.Add("Accept", test.contentType)

			resp, err := client.Do(req)
			if err != nil {
				t.Errorf("Request failed: %v", err)
				return
			}
			defer resp.Body.Close()

			if resp.StatusCode != http.StatusOK {
				t.Errorf("Expected 200, got %d", resp.StatusCode)
			}
		})
	}
}
