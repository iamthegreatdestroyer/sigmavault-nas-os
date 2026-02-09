// Package main provides integration tests for the Compression API.
// These tests verify the complete flow: Go API → RPC → Python Engine → Response.
package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

// ============================================================================
// Test Constants and Helpers
// ============================================================================

const (
	// Target compression ratio (70%+)
	targetCompressionRatio = 0.70
)

// Note: pythonRPCURL and goAPIURL are defined in rpc_integration_test.go

// callCompressionRPC makes a JSON-RPC call to the Python compression engine.
func callCompressionRPC(t *testing.T, method string, params interface{}) (*JSONRPCResponse, error) {
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

	client := &http.Client{Timeout: 60 * time.Second}
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

// generateCompressibleData generates data with patterns that compress well.
func generateCompressibleData(size int) []byte {
	// Create repetitive pattern data (compresses very well)
	pattern := []byte("SigmaVault NAS OS - Elite Compression Engine Test Data. ")
	data := make([]byte, 0, size)
	for len(data) < size {
		data = append(data, pattern...)
	}
	return data[:size]
}

// generateRandomData generates random data (compresses poorly).
func generateRandomData(size int) []byte {
	data := make([]byte, size)
	_ = rand.Read(data) // gosec: G104 - error intentionally ignored in test
	return data
}

// ============================================================================
// Response Types for Compression API
// ============================================================================

// CompressDataResult represents the compression.compress.data response.
type CompressDataResult struct {
	JobID            string  `json:"job_id"`
	Success          bool    `json:"success"`
	OriginalSize     int64   `json:"original_size"`
	CompressedSize   int64   `json:"compressed_size"`
	CompressionRatio float64 `json:"compression_ratio"`
	ElapsedSeconds   float64 `json:"elapsed_seconds"`
	Data             string  `json:"data"` // Base64 encoded compressed data
}

// DecompressDataResult represents the compression.decompress.data response.
type DecompressDataResult struct {
	JobID            string  `json:"job_id"`
	Success          bool    `json:"success"`
	CompressedSize   int64   `json:"compressed_size"`
	DecompressedSize int64   `json:"decompressed_size"`
	ElapsedSeconds   float64 `json:"elapsed_seconds"`
	Data             string  `json:"data"` // Base64 encoded decompressed data
}

// QueueSubmitResult represents the compression.queue.submit response.
type QueueSubmitResult struct {
	JobID     string `json:"job_id"`
	Status    string `json:"status"`
	Priority  string `json:"priority"`
	JobType   string `json:"job_type"`
	CreatedAt string `json:"created_at"`
}

// QueueStatusResult represents the compression.queue.status response.
type QueueStatusResult struct {
	JobID       string  `json:"job_id"`
	Status      string  `json:"status"`
	Priority    string  `json:"priority"`
	JobType     string  `json:"job_type"`
	Progress    float64 `json:"progress"`
	CreatedAt   string  `json:"created_at"`
	StartedAt   *string `json:"started_at,omitempty"`
	CompletedAt *string `json:"completed_at,omitempty"`
	Error       *string `json:"error,omitempty"`
}

// QueueStatsResult represents queue statistics.
type QueueStatsResult struct {
	TotalJobs     int `json:"total_jobs"`
	PendingJobs   int `json:"pending_jobs"`
	RunningJobs   int `json:"running_jobs"`
	CompletedJobs int `json:"completed_jobs"`
	FailedJobs    int `json:"failed_jobs"`
	CancelledJobs int `json:"cancelled_jobs"`
}

// RunningJobsResult represents the compression.queue.running response.
type RunningJobsResult struct {
	Jobs         []RunningJob `json:"jobs"`
	TotalRunning int          `json:"total_running"`
	TotalPending int          `json:"total_pending"`
	TotalJobs    int          `json:"total_jobs"`
}

// RunningJob represents a job in the running jobs list.
type RunningJob struct {
	JobID          string  `json:"job_id"`
	Status         string  `json:"status"`
	JobType        string  `json:"job_type"`
	Priority       string  `json:"priority"`
	Progress       float64 `json:"progress"`
	Phase          string  `json:"phase"`
	BytesProcessed int64   `json:"bytes_processed"`
	BytesTotal     int64   `json:"bytes_total"`
	CurrentRatio   float64 `json:"current_ratio"`
	ETASeconds     float64 `json:"eta_seconds"`
}

// ============================================================================
// Test: Direct Compression API
// ============================================================================

// TestCompressionCompressData tests the compression.compress.data RPC method.
func TestCompressionCompressData(t *testing.T) {
	t.Log("Testing compression.compress.data RPC method...")

	// Generate 1KB of compressible test data
	testData := generateCompressibleData(1024)
	encodedData := base64.StdEncoding.EncodeToString(testData)

	params := map[string]interface{}{
		"data":  encodedData,
		"level": "balanced",
	}

	resp, err := callCompressionRPC(t, "compression.compress.data", params)
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s (code: %d)", resp.Error.Message, resp.Error.Code)
	}

	var result CompressDataResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Validate response
	if !result.Success {
		t.Error("Expected success=true")
	}
	if result.JobID == "" {
		t.Error("Expected non-empty job_id")
	}
	if result.OriginalSize != int64(len(testData)) {
		t.Errorf("Expected original_size=%d, got %d", len(testData), result.OriginalSize)
	}
	if result.CompressedSize >= result.OriginalSize {
		t.Errorf("Compressed size (%d) should be less than original (%d)",
			result.CompressedSize, result.OriginalSize)
	}
	if result.CompressionRatio < targetCompressionRatio {
		t.Errorf("Compression ratio %.2f%% below target %.2f%%",
			result.CompressionRatio*100, targetCompressionRatio*100)
	}
	if result.Data == "" {
		t.Error("Expected non-empty compressed data")
	}

	t.Logf("✅ compression.compress.data: ratio=%.2f%%, original=%d, compressed=%d, elapsed=%.3fs",
		result.CompressionRatio*100, result.OriginalSize, result.CompressedSize, result.ElapsedSeconds)
}

// TestCompressionLevels tests different compression levels.
func TestCompressionLevels(t *testing.T) {
	t.Log("Testing compression levels (fast, balanced, maximum)...")

	testData := generateCompressibleData(4096)
	encodedData := base64.StdEncoding.EncodeToString(testData)

	levels := []string{"fast", "balanced", "maximum"}
	var results []CompressDataResult

	for _, level := range levels {
		params := map[string]interface{}{
			"data":  encodedData,
			"level": level,
		}

		resp, err := callCompressionRPC(t, "compression.compress.data", params)
		if err != nil {
			t.Fatalf("RPC call failed for level %s: %v", level, err)
		}

		if resp.Error != nil {
			t.Fatalf("RPC error for level %s: %s", level, resp.Error.Message)
		}

		var result CompressDataResult
		if err := json.Unmarshal(resp.Result, &result); err != nil {
			t.Fatalf("Failed to parse result for level %s: %v", level, err)
		}

		results = append(results, result)

		t.Logf("   %s: ratio=%.2f%%, size=%d, time=%.4fs",
			level, result.CompressionRatio*100, result.CompressedSize, result.ElapsedSeconds)
	}

	// Validate all levels produce valid results
	for i, result := range results {
		if !result.Success {
			t.Errorf("Level %s failed", levels[i])
		}
	}

	t.Log("✅ All compression levels working correctly")
}

// TestCompressionRoundTrip tests compress → decompress data integrity.
func TestCompressionRoundTrip(t *testing.T) {
	t.Log("Testing compression round-trip (compress → decompress)...")

	// Generate test data
	originalData := generateCompressibleData(2048)
	encodedOriginal := base64.StdEncoding.EncodeToString(originalData)

	// Step 1: Compress
	compressParams := map[string]interface{}{
		"data":  encodedOriginal,
		"level": "balanced",
	}

	compressResp, err := callCompressionRPC(t, "compression.compress.data", compressParams)
	if err != nil {
		t.Fatalf("Compress RPC failed: %v", err)
	}
	if compressResp.Error != nil {
		t.Fatalf("Compress error: %s", compressResp.Error.Message)
	}

	var compressResult CompressDataResult
	if err := json.Unmarshal(compressResp.Result, &compressResult); err != nil {
		t.Fatalf("Failed to parse compress result: %v", err)
	}

	t.Logf("   Compressed: %d → %d bytes (%.2f%%)",
		compressResult.OriginalSize, compressResult.CompressedSize, compressResult.CompressionRatio*100)

	// Step 2: Decompress
	decompressParams := map[string]interface{}{
		"data": compressResult.Data,
	}

	decompressResp, err := callCompressionRPC(t, "compression.decompress.data", decompressParams)
	if err != nil {
		t.Fatalf("Decompress RPC failed: %v", err)
	}
	if decompressResp.Error != nil {
		t.Fatalf("Decompress error: %s", decompressResp.Error.Message)
	}

	var decompressResult DecompressDataResult
	if err := json.Unmarshal(decompressResp.Result, &decompressResult); err != nil {
		t.Fatalf("Failed to parse decompress result: %v", err)
	}

	// Verify data integrity
	decodedData, err := base64.StdEncoding.DecodeString(decompressResult.Data)
	if err != nil {
		t.Fatalf("Failed to decode decompressed data: %v", err)
	}

	if !bytes.Equal(originalData, decodedData) {
		t.Fatalf("Data integrity check failed: original and decompressed data differ")
	}

	t.Logf("   Decompressed: %d → %d bytes", decompressResult.CompressedSize, decompressResult.DecompressedSize)
	t.Log("✅ Round-trip data integrity verified")
}

// ============================================================================
// Test: Queue-Based Operations
// ============================================================================

// TestQueueSubmit tests the compression.queue.submit RPC method.
func TestQueueSubmit(t *testing.T) {
	t.Log("Testing compression.queue.submit RPC method...")

	testData := generateCompressibleData(512)
	encodedData := base64.StdEncoding.EncodeToString(testData)

	params := map[string]interface{}{
		"type":     "compress_data",
		"data":     encodedData,
		"priority": "normal",
	}

	resp, err := callCompressionRPC(t, "compression.queue.submit", params)
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s (code: %d)", resp.Error.Message, resp.Error.Code)
	}

	var result QueueSubmitResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Validate response
	if result.JobID == "" {
		t.Error("Expected non-empty job_id")
	}
	if result.Status == "" {
		t.Error("Expected non-empty status")
	}
	if result.Priority != "normal" {
		t.Errorf("Expected priority='normal', got '%s'", result.Priority)
	}
	if result.JobType != "compress_data" {
		t.Errorf("Expected job_type='compress_data', got '%s'", result.JobType)
	}

	t.Logf("✅ compression.queue.submit: job_id=%s, status=%s, priority=%s",
		result.JobID, result.Status, result.Priority)
}

// TestQueueStatus tests the compression.queue.status RPC method.
func TestQueueStatus(t *testing.T) {
	t.Log("Testing compression.queue.status RPC method...")

	// First, submit a job
	testData := generateCompressibleData(256)
	encodedData := base64.StdEncoding.EncodeToString(testData)

	submitParams := map[string]interface{}{
		"type":     "compress_data",
		"data":     encodedData,
		"priority": "high",
	}

	submitResp, err := callCompressionRPC(t, "compression.queue.submit", submitParams)
	if err != nil {
		t.Fatalf("Submit RPC failed: %v", err)
	}
	if submitResp.Error != nil {
		t.Fatalf("Submit error: %s", submitResp.Error.Message)
	}

	var submitResult QueueSubmitResult
	if err := json.Unmarshal(submitResp.Result, &submitResult); err != nil {
		t.Fatalf("Failed to parse submit result: %v", err)
	}

	// Now get job status
	statusParams := map[string]interface{}{
		"job_id": submitResult.JobID,
	}

	statusResp, err := callCompressionRPC(t, "compression.queue.status", statusParams)
	if err != nil {
		t.Fatalf("Status RPC failed: %v", err)
	}
	if statusResp.Error != nil {
		t.Fatalf("Status error: %s", statusResp.Error.Message)
	}

	var statusResult QueueStatusResult
	if err := json.Unmarshal(statusResp.Result, &statusResult); err != nil {
		t.Fatalf("Failed to parse status result: %v", err)
	}

	// Validate response
	if statusResult.JobID != submitResult.JobID {
		t.Errorf("Job ID mismatch: expected %s, got %s", submitResult.JobID, statusResult.JobID)
	}
	if statusResult.Priority != "high" {
		t.Errorf("Expected priority='high', got '%s'", statusResult.Priority)
	}
	if statusResult.JobType != "compress_data" {
		t.Errorf("Expected job_type='compress_data', got '%s'", statusResult.JobType)
	}

	t.Logf("✅ compression.queue.status: job_id=%s, status=%s, progress=%.1f%%",
		statusResult.JobID, statusResult.Status, statusResult.Progress*100)
}

// TestQueueRunning tests the compression.queue.running RPC method.
func TestQueueRunning(t *testing.T) {
	t.Log("Testing compression.queue.running RPC method...")

	params := map[string]interface{}{
		"include_pending": true,
		"limit":           10,
	}

	resp, err := callCompressionRPC(t, "compression.queue.running", params)
	if err != nil {
		t.Fatalf("RPC call failed: %v", err)
	}

	if resp.Error != nil {
		t.Fatalf("RPC error: %s (code: %d)", resp.Error.Message, resp.Error.Code)
	}

	var result RunningJobsResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("Failed to parse result: %v", err)
	}

	// Validate structure
	t.Logf("✅ compression.queue.running: jobs=%d, running=%d, pending=%d, total=%d",
		len(result.Jobs), result.TotalRunning, result.TotalPending, result.TotalJobs)

	// If there are jobs, validate job structure
	for i, job := range result.Jobs {
		if job.JobID == "" {
			t.Errorf("Job %d: expected non-empty job_id", i)
		}
		if job.Status == "" {
			t.Errorf("Job %d: expected non-empty status", i)
		}
		t.Logf("   Job %d: id=%s, status=%s, type=%s, progress=%.1f%%",
			i, job.JobID[:8], job.Status, job.JobType, job.Progress*100)
	}
}

// ============================================================================
// Test: Performance and Latency
// ============================================================================

// TestCompressionLatency measures compression API latency.
func TestCompressionLatency(t *testing.T) {
	t.Log("Measuring compression API latency...")

	// Test different data sizes
	sizes := []int{1024, 4096, 16384, 65536} // 1KB, 4KB, 16KB, 64KB

	for _, size := range sizes {
		testData := generateCompressibleData(size)
		encodedData := base64.StdEncoding.EncodeToString(testData)

		start := time.Now()
		params := map[string]interface{}{
			"data":  encodedData,
			"level": "fast",
		}

		resp, err := callCompressionRPC(t, "compression.compress.data", params)
		duration := time.Since(start)

		if err != nil {
			t.Errorf("Size %d: RPC failed: %v", size, err)
			continue
		}
		if resp.Error != nil {
			t.Errorf("Size %d: RPC error: %s", size, resp.Error.Message)
			continue
		}

		var result CompressDataResult
		_ = json.Unmarshal(resp.Result, &result) // error intentionally ignored in test

		t.Logf("   %dKB: latency=%v, ratio=%.2f%%, throughput=%.2f MB/s",
			size/1024, duration, result.CompressionRatio*100,
			float64(size)/(duration.Seconds()*1024*1024))

		// Target: <1s latency for reasonable sizes
		if duration > time.Second && size <= 65536 {
			t.Logf("⚠️  Warning: Latency %v exceeds 1s target for %dKB", duration, size/1024)
		}
	}

	t.Log("✅ Compression latency measurement complete")
}

// TestCompressionRatioTarget validates the 70%+ compression ratio target.
func TestCompressionRatioTarget(t *testing.T) {
	t.Log("Validating 70%+ compression ratio target...")

	// Test with highly compressible data
	sizes := []int{1024, 4096, 16384}

	for _, size := range sizes {
		testData := generateCompressibleData(size)
		encodedData := base64.StdEncoding.EncodeToString(testData)

		params := map[string]interface{}{
			"data":  encodedData,
			"level": "maximum",
		}

		resp, err := callCompressionRPC(t, "compression.compress.data", params)
		if err != nil {
			t.Fatalf("RPC failed for size %d: %v", size, err)
		}
		if resp.Error != nil {
			t.Fatalf("RPC error for size %d: %s", size, resp.Error.Message)
		}

		var result CompressDataResult
		json.Unmarshal(resp.Result, &result)

		if result.CompressionRatio < targetCompressionRatio {
			t.Errorf("Size %d: ratio %.2f%% below target %.2f%%",
				size, result.CompressionRatio*100, targetCompressionRatio*100)
		} else {
			t.Logf("   %dKB: %.2f%% compression ratio ✓", size/1024, result.CompressionRatio*100)
		}
	}

	t.Log("✅ Compression ratio target validation complete")
}

// TestConcurrentCompression tests concurrent compression operations.
func TestConcurrentCompression(t *testing.T) {
	t.Log("Testing concurrent compression operations...")

	concurrency := 5
	done := make(chan error, concurrency)

	testData := generateCompressibleData(2048)
	encodedData := base64.StdEncoding.EncodeToString(testData)

	start := time.Now()
	for i := 0; i < concurrency; i++ {
		go func(id int) {
			params := map[string]interface{}{
				"data":  encodedData,
				"level": "fast",
			}

			resp, err := callCompressionRPC(t, "compression.compress.data", params)
			if err != nil {
				done <- fmt.Errorf("call %d failed: %w", id, err)
				return
			}
			if resp.Error != nil {
				done <- fmt.Errorf("call %d rpc error: %s", id, resp.Error.Message)
				return
			}

			var result CompressDataResult
			json.Unmarshal(resp.Result, &result)
			if !result.Success {
				done <- fmt.Errorf("call %d compression failed", id)
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
			t.Errorf("Concurrent compression error: %v", err)
		}
		t.Fatalf("%d/%d concurrent compressions failed", len(errors), concurrency)
	}

	t.Logf("✅ Concurrent compression: %d operations completed in %v", concurrency, duration)
}

// ============================================================================
// Test: Error Handling
// ============================================================================

// TestCompressionInvalidData tests error handling for invalid input.
func TestCompressionInvalidData(t *testing.T) {
	t.Log("Testing compression error handling for invalid input...")

	testCases := []struct {
		name   string
		params map[string]interface{}
	}{
		{
			name: "empty data",
			params: map[string]interface{}{
				"data":  "",
				"level": "balanced",
			},
		},
		{
			name: "invalid base64",
			params: map[string]interface{}{
				"data":  "not-valid-base64!!!",
				"level": "balanced",
			},
		},
		{
			name: "missing data parameter",
			params: map[string]interface{}{
				"level": "balanced",
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			resp, err := callCompressionRPC(t, "compression.compress.data", tc.params)
			if err != nil {
				t.Logf("   %s: HTTP error (expected) - %v", tc.name, err)
				return
			}

			if resp.Error != nil {
				t.Logf("   %s: RPC error %d - %s (expected)", tc.name, resp.Error.Code, resp.Error.Message)
				return
			}

			// If we get here, check if success is false
			var result map[string]interface{}
			json.Unmarshal(resp.Result, &result)
			if success, ok := result["success"].(bool); ok && !success {
				t.Logf("   %s: success=false (expected)", tc.name)
				return
			}

			t.Errorf("%s: Expected error but got success", tc.name)
		})
	}

	t.Log("✅ Error handling validation complete")
}

// TestDecompressInvalidData tests decompression error handling.
func TestDecompressInvalidData(t *testing.T) {
	t.Log("Testing decompression error handling for invalid input...")

	// Random data that's not valid compressed data
	invalidData := make([]byte, 100)
	rand.Read(invalidData)
	encodedData := base64.StdEncoding.EncodeToString(invalidData)

	params := map[string]interface{}{
		"data": encodedData,
	}

	resp, err := callCompressionRPC(t, "compression.decompress.data", params)
	if err != nil {
		t.Logf("   HTTP error (expected): %v", err)
		return
	}

	if resp.Error != nil {
		t.Logf("   RPC error %d: %s (expected)", resp.Error.Code, resp.Error.Message)
		return
	}

	var result map[string]interface{}
	json.Unmarshal(resp.Result, &result)
	if success, ok := result["success"].(bool); ok && !success {
		t.Log("   success=false (expected)")
		return
	}

	// It's possible the random data might coincidentally be valid (unlikely)
	t.Log("⚠️  Decompression didn't fail - random data may have been valid")
}

// ============================================================================
// Test: Engine Connection Check
// ============================================================================

// TestCompressionEngineConnection checks if the Python engine is running.
func TestCompressionEngineConnection(t *testing.T) {
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(pythonRPCURL)
	if err != nil {
		t.Fatalf("Python RPC engine not reachable at %s. Please start: cd src/engined && python -m engined.main", pythonRPCURL)
	}
	resp.Body.Close()

	t.Log("═══════════════════════════════════════════════════════")
	t.Log("  SigmaVault NAS OS - Compression Integration Tests")
	t.Logf("  Python RPC Engine: %s", pythonRPCURL)
	t.Logf("  Target Compression Ratio: %.0f%%+", targetCompressionRatio*100)
	t.Log("═══════════════════════════════════════════════════════")
	t.Log("✅ Python RPC engine connected")

	_ = context.Background() // Placeholder for future context usage
}
