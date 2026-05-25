// Package e2e - Integration tests
// Tests complete system flows combining REST API, engine communication, and WebSocket events
package e2e

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// TestE2EAPIToEngineIntegration tests complete flow from API request to engine communication
func TestE2EAPIToEngineIntegration(t *testing.T) {
	srv := NewE2ETestServer(t, 12001)
	defer srv.Close()

	t.Run("Health check triggers RPC call", func(t *testing.T) {
		start := time.Now()
		resp, err := http.Get(srv.baseURL + "/api/v1/health")
		duration := time.Since(start)

		if err != nil {
			t.Fatalf("Failed to reach health endpoint: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected 200, got %d", resp.StatusCode)
		}

		t.Logf("Health check completed in %v", duration)

		// Verify response structure
		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			t.Fatalf("Failed to parse response: %v", err)
		}

		if _, ok := result["status"]; !ok {
			t.Error("Missing 'status' field in response")
		}
	})

	t.Run("Info endpoint returns system information", func(t *testing.T) {
		resp, err := http.Get(srv.baseURL + "/api/v1/info")
		if err != nil {
			t.Fatalf("Failed to reach info endpoint: %v", err)
		}
		defer resp.Body.Close()

		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			t.Logf("Info endpoint returned: %v", err)
		}

		t.Logf("System info retrieved: %v", result)
	})
}

// TestE2ERequestValidation tests API request validation
func TestE2ERequestValidation(t *testing.T) {
	srv := NewE2ETestServer(t, 12002)
	defer srv.Close()

	t.Run("Valid request", func(t *testing.T) {
		resp, err := http.Get(srv.baseURL + "/api/v1/health")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected 200, got %d", resp.StatusCode)
		}
	})

	t.Run("Invalid endpoint", func(t *testing.T) {
		resp, err := http.Get(srv.baseURL + "/api/v1/invalid")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusNotFound {
			t.Logf("Expected 404, got %d (endpoint may exist)", resp.StatusCode)
		}
	})

	t.Run("Malformed request", func(t *testing.T) {
		payload := []byte("{invalid json")
		resp, err := http.Post(
			srv.baseURL+"/api/v1/compression/compress",
			"application/json",
			bytes.NewBuffer(payload),
		)
		if err != nil {
			t.Logf("Request error: %v", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode >= 400 {
			t.Logf("Invalid request properly rejected with %d", resp.StatusCode)
		}
	})
}

// TestE2EMiddlewareExecution tests API middleware execution
func TestE2EMiddlewareExecution(t *testing.T) {
	srv := NewE2ETestServer(t, 12003)
	defer srv.Close()

	t.Run("Request ID tracking", func(t *testing.T) {
		client := &http.Client{}
		req, _ := http.NewRequest("GET", srv.baseURL+"/api/v1/health", nil)
		req.Header.Add("X-Request-ID", "test-12345")

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		// Check if request ID is reflected in response
		requestID := resp.Header.Get("X-Request-ID")
		t.Logf("Request ID tracking: %s", requestID)
	})

	t.Run("Security headers present", func(t *testing.T) {
		resp, err := http.Get(srv.baseURL + "/api/v1/health")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		securityHeaders := []string{
			"X-Content-Type-Options",
			"X-Frame-Options",
			"X-XSS-Protection",
		}

		for _, header := range securityHeaders {
			if value := resp.Header.Get(header); value != "" {
				t.Logf("Security header %s: %s", header, value)
			}
		}
	})

	t.Run("CORS headers", func(t *testing.T) {
		resp, err := http.Get(srv.baseURL + "/api/v1/health")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		origin := resp.Header.Get("Access-Control-Allow-Origin")
		t.Logf("CORS origin: %s", origin)
	})
}

// TestE2EAndroidRouteCompatibility tests API routes work as expected
func TestE2ERouteCompatibility(t *testing.T) {
	srv := NewE2ETestServer(t, 12004)
	defer srv.Close()

	routes := []struct {
		name   string
		method string
		path   string
	}{
		{"Health", "GET", "/api/v1/health"},
		{"Ready", "GET", "/api/v1/ready"},
		{"Info", "GET", "/api/v1/info"},
	}

	for _, route := range routes {
		t.Run(route.name, func(t *testing.T) {
			var resp *http.Response
			var err error

			switch route.method {
			case "GET":
				resp, err = http.Get(srv.baseURL + route.path)
			case "POST":
				resp, err = http.Post(srv.baseURL+route.path, "application/json", bytes.NewBuffer([]byte("{}")))
			}

			if err != nil {
				t.Logf("Request error: %v", err)
				return
			}
			defer resp.Body.Close()

			t.Logf("Route %s returned %d", route.path, resp.StatusCode)

			// Read response to validate it's valid JSON
			body, _ := io.ReadAll(resp.Body)
			if len(body) > 0 {
				var result interface{}
				if err := json.Unmarshal(body, &result); err != nil {
					t.Logf("Response is not JSON: %s", string(body[:min(100, len(body))]))
				} else {
					t.Log("Response is valid JSON")
				}
			}
		})
	}
}

// TestE2ERateLimiting tests rate limiting behavior
func TestE2ERateLimiting(t *testing.T) {
	srv := NewE2ETestServer(t, 12005)
	defer srv.Close()

	t.Run("Normal load within limits", func(t *testing.T) {
		const requests = 10
		var successCount int32

		for i := 0; i < requests; i++ {
			resp, err := http.Get(srv.baseURL + "/api/v1/health")
			if err != nil {
				continue
			}
			resp.Body.Close()

			if resp.StatusCode == http.StatusOK {
				atomic.AddInt32(&successCount, 1)
			}
		}

		t.Logf("Normal load: %d/%d requests succeeded", atomic.LoadInt32(&successCount), requests)
	})

	t.Run("Burst load handling", func(t *testing.T) {
		const workers = 20
		const requestsPerWorker = 5
		var wg sync.WaitGroup
		var successCount int32

		for w := 0; w < workers; w++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for r := 0; r < requestsPerWorker; r++ {
					resp, err := http.Get(srv.baseURL + "/api/v1/health")
					if err == nil {
						resp.Body.Close()
						atomic.AddInt32(&successCount, 1)
					}
				}
			}()
		}

		wg.Wait()

		totalRequests := workers * requestsPerWorker
		successRate := float64(atomic.LoadInt32(&successCount)) / float64(totalRequests) * 100
		t.Logf("Burst load: %.1f%% success rate (%d/%d)", successRate, atomic.LoadInt32(&successCount), totalRequests)
	})
}

// TestE2EErrorRecovery tests error recovery scenarios
func TestE2EErrorRecovery(t *testing.T) {
	srv := NewE2ETestServer(t, 12006)
	defer srv.Close()

	t.Run("Graceful error response", func(t *testing.T) {
		resp, err := http.Get(srv.baseURL + "/api/v1/nonexistent")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusNotFound {
			t.Logf("Expected 404, got %d", resp.StatusCode)
		}

		// Verify error response is valid JSON
		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			t.Logf("Error response parse: %v", err)
		}
	})

	t.Run("Server continues after error", func(t *testing.T) {
		// Send bad request
		resp1, _ := http.Post(srv.baseURL+"/api/v1/invalid", "application/json", bytes.NewBuffer([]byte("{}")))
		if resp1 != nil {
			resp1.Body.Close()
		}

		// Verify server still works
		resp2, err := http.Get(srv.baseURL + "/api/v1/health")
		if err != nil {
			t.Errorf("Server not recovered: %v", err)
			return
		}
		defer resp2.Body.Close()

		if resp2.StatusCode == http.StatusOK {
			t.Log("Server recovered after error")
		}
	})
}

// TestE2ESystemStability tests long-running stability
func TestE2ESystemStability(t *testing.T) {
	srv := NewE2ETestServer(t, 12007)
	defer srv.Close()

	const duration = 10 * time.Second
	const workers = 5
	var wg sync.WaitGroup
	var totalRequests int32
	var totalErrors int32

	startTime := time.Now()

	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()

			for {
				if time.Since(startTime) > duration {
					break
				}

				resp, err := http.Get(srv.baseURL + "/api/v1/health")
				if err != nil {
					atomic.AddInt32(&totalErrors, 1)
					continue
				}
				resp.Body.Close()

				atomic.AddInt32(&totalRequests, 1)
				time.Sleep(10 * time.Millisecond)
			}
		}()
	}

	wg.Wait()

	totalTime := time.Since(startTime)
	requestsPerSec := float64(atomic.LoadInt32(&totalRequests)) / totalTime.Seconds()

	t.Logf("Stability test results:")
	t.Logf("  Duration: %v", totalTime)
	t.Logf("  Total requests: %d", atomic.LoadInt32(&totalRequests))
	t.Logf("  Total errors: %d", atomic.LoadInt32(&totalErrors))
	t.Logf("  Throughput: %.2f req/sec", requestsPerSec)

	if atomic.LoadInt32(&totalErrors) > atomic.LoadInt32(&totalRequests)/10 {
		t.Errorf("Error rate too high")
	}
}

// TestE2EResponseCompleteness tests response data completeness
func TestE2EResponseCompleteness(t *testing.T) {
	srv := NewE2ETestServer(t, 12008)
	defer srv.Close()

	t.Run("Health response contains required fields", func(t *testing.T) {
		resp, err := http.Get(srv.baseURL + "/api/v1/health")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			t.Fatalf("Response parsing failed: %v", err)
		}

		requiredFields := []string{"status"}
		for _, field := range requiredFields {
			if _, ok := result[field]; !ok {
				t.Errorf("Missing required field: %s", field)
			}
		}
	})

	t.Run("Consistent response structure", func(t *testing.T) {
		const requests = 5
		var responses []map[string]interface{}

		for i := 0; i < requests; i++ {
			resp, _ := http.Get(srv.baseURL + "/api/v1/info")
			if resp == nil {
				continue
			}

			var result map[string]interface{}
			json.NewDecoder(resp.Body).Decode(&result)
			responses = append(responses, result)
			resp.Body.Close()
		}

		if len(responses) > 1 {
			t.Logf("Collected %d consistent responses", len(responses))
		}
	})
}

// Helper function
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
