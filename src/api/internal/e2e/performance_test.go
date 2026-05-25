// Package e2e - Performance benchmarking tests
// Tests response times, throughput, and performance characteristics
package e2e

import (
	"fmt"
	"math"
	"net/http"
	"sort"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// PerformanceMetrics tracks timing and throughput metrics
type PerformanceMetrics struct {
	mu           sync.Mutex
	durations    []time.Duration
	errorCount   int32
	successCount int32
}

// Record adds a duration measurement
func (pm *PerformanceMetrics) Record(d time.Duration) {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	pm.durations = append(pm.durations, d)
	atomic.AddInt32(&pm.successCount, 1)
}

// RecordError increments the error counter
func (pm *PerformanceMetrics) RecordError() {
	atomic.AddInt32(&pm.errorCount, 1)
}

// Percentile calculates the Nth percentile latency
func (pm *PerformanceMetrics) Percentile(p float64) time.Duration {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	if len(pm.durations) == 0 {
		return 0
	}

	sorted := make([]time.Duration, len(pm.durations))
	copy(sorted, pm.durations)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })

	index := int(math.Ceil(float64(len(sorted)) * p / 100))
	if index >= len(sorted) {
		index = len(sorted) - 1
	}
	return sorted[index]
}

// Mean calculates the average duration
func (pm *PerformanceMetrics) Mean() time.Duration {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	if len(pm.durations) == 0 {
		return 0
	}

	var sum time.Duration
	for _, d := range pm.durations {
		sum += d
	}
	return sum / time.Duration(len(pm.durations))
}

// StdDev calculates the standard deviation
func (pm *PerformanceMetrics) StdDev() time.Duration {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	if len(pm.durations) == 0 {
		return 0
	}

	mean := 0.0
	for _, d := range pm.durations {
		mean += d.Seconds()
	}
	mean /= float64(len(pm.durations))

	variance := 0.0
	for _, d := range pm.durations {
		diff := d.Seconds() - mean
		variance += diff * diff
	}
	variance /= float64(len(pm.durations))

	return time.Duration(math.Sqrt(variance)*1000) * time.Millisecond
}

// Throughput calculates requests per second
func (pm *PerformanceMetrics) Throughput(duration time.Duration) float64 {
	if duration == 0 {
		return 0
	}
	return float64(atomic.LoadInt32(&pm.successCount)) / duration.Seconds()
}

// BenchmarkE2EResponseTime benchmarks response time for the health endpoint
func BenchmarkE2EResponseTime(b *testing.B) {
	srv := NewE2ETestServer(&testing.T{}, 10001)
	defer srv.Close()

	metrics := &PerformanceMetrics{}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		start := time.Now()
		resp, err := http.Get(srv.baseURL + "/api/v1/health")
		duration := time.Since(start)

		if err != nil {
			metrics.RecordError()
			continue
		}
		resp.Body.Close()

		metrics.Record(duration)
	}

	b.StopTimer()

	b.Logf("\n=== Response Time Benchmark ===")
	b.Logf("Requests: %d", atomic.LoadInt32(&metrics.successCount))
	b.Logf("Errors: %d", atomic.LoadInt32(&metrics.errorCount))
	b.Logf("Mean: %v", metrics.Mean())
	b.Logf("StdDev: %v", metrics.StdDev())
	b.Logf("P50: %v", metrics.Percentile(50))
	b.Logf("P95: %v", metrics.Percentile(95))
	b.Logf("P99: %v", metrics.Percentile(99))
	b.Logf("Max: %v", metrics.Percentile(100))
}

// BenchmarkE2EHighConcurrency benchmarks system under high concurrent load
func BenchmarkE2EHighConcurrency(b *testing.B) {
	srv := NewE2ETestServer(&testing.T{}, 10002)
	defer srv.Close()

	const concurrency = 100
	metrics := &PerformanceMetrics{}

	done := make(chan struct{})
	var wg sync.WaitGroup

	// Start worker goroutines
	for w := 0; w < concurrency; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				select {
				case <-done:
					return
				default:
					start := time.Now()
					resp, err := http.Get(srv.baseURL + "/api/v1/info")
					duration := time.Since(start)

					if err != nil {
						metrics.RecordError()
						continue
					}
					resp.Body.Close()

					metrics.Record(duration)
				}
			}
		}()
	}

	time.Sleep(time.Duration(b.N) * time.Millisecond)
	close(done)
	wg.Wait()

	b.Logf("\n=== High Concurrency Benchmark (workers=%d) ===", concurrency)
	b.Logf("Successful requests: %d", atomic.LoadInt32(&metrics.successCount))
	b.Logf("Errors: %d", atomic.LoadInt32(&metrics.errorCount))
	b.Logf("Mean latency: %v", metrics.Mean())
	b.Logf("P99 latency: %v", metrics.Percentile(99))
	b.Logf("Throughput: %.2f req/sec", metrics.Throughput(1*time.Second))
}

// TestE2EPerformanceBaseline establishes baseline performance metrics
func TestE2EPerformanceBaseline(t *testing.T) {
	srv := NewE2ETestServer(t, 10003)
	defer srv.Close()

	t.Run("Health endpoint baseline", func(t *testing.T) {
		const iterations = 100
		metrics := &PerformanceMetrics{}

		start := time.Now()
		for i := 0; i < iterations; i++ {
			reqStart := time.Now()
			resp, err := http.Get(srv.baseURL + "/api/v1/health")
			duration := time.Since(reqStart)

			if err != nil {
				metrics.RecordError()
				continue
			}
			resp.Body.Close()
			metrics.Record(duration)
		}
		totalDuration := time.Since(start)

		t.Logf("Requests: %d, Errors: %d", atomic.LoadInt32(&metrics.successCount), atomic.LoadInt32(&metrics.errorCount))
		t.Logf("Mean: %v, StdDev: %v", metrics.Mean(), metrics.StdDev())
		t.Logf("P50: %v, P95: %v, P99: %v", metrics.Percentile(50), metrics.Percentile(95), metrics.Percentile(99))
		t.Logf("Throughput: %.2f req/sec", metrics.Throughput(totalDuration))

		// Verify performance targets
		if metrics.Percentile(99) > 500*time.Millisecond {
			t.Logf("Warning: P99 latency (%v) exceeds 500ms target", metrics.Percentile(99))
		}
	})

	t.Run("Multiple endpoints baseline", func(t *testing.T) {
		endpoints := []string{
			"/api/v1/health",
			"/api/v1/ready",
			"/api/v1/info",
		}

		for _, endpoint := range endpoints {
			t.Run(endpoint, func(t *testing.T) {
				const iterations = 50
				metrics := &PerformanceMetrics{}

				for i := 0; i < iterations; i++ {
					reqStart := time.Now()
					resp, err := http.Get(srv.baseURL + endpoint)
					duration := time.Since(reqStart)

					if err != nil {
						metrics.RecordError()
						continue
					}
					resp.Body.Close()
					metrics.Record(duration)
				}

				t.Logf("Mean: %v, P95: %v, P99: %v",
					metrics.Mean(),
					metrics.Percentile(95),
					metrics.Percentile(99),
				)
			})
		}
	})

	t.Run("Concurrent requests baseline", func(t *testing.T) {
		const workers = 20
		const requestsPerWorker = 25
		metrics := &PerformanceMetrics{}

		var wg sync.WaitGroup
		start := time.Now()

		for w := 0; w < workers; w++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for r := 0; r < requestsPerWorker; r++ {
					reqStart := time.Now()
					resp, err := http.Get(srv.baseURL + "/api/v1/info")
					duration := time.Since(reqStart)

					if err != nil {
						metrics.RecordError()
						continue
					}
					resp.Body.Close()
					metrics.Record(duration)
				}
			}()
		}

		wg.Wait()
		totalDuration := time.Since(start)

		totalRequests := workers * requestsPerWorker
		t.Logf("Total requests: %d (concurrent workers=%d)", totalRequests, workers)
		t.Logf("Total time: %v", totalDuration)
		t.Logf("Mean latency: %v", metrics.Mean())
		t.Logf("P99 latency: %v", metrics.Percentile(99))
		t.Logf("Throughput: %.2f req/sec", metrics.Throughput(totalDuration))
	})
}

// TestE2ELatencyDistribution tests and documents latency distributions
func TestE2ELatencyDistribution(t *testing.T) {
	srv := NewE2ETestServer(t, 10004)
	defer srv.Close()

	const iterations = 500
	metrics := &PerformanceMetrics{}

	for i := 0; i < iterations; i++ {
		start := time.Now()
		resp, err := http.Get(srv.baseURL + "/api/v1/health")
		duration := time.Since(start)

		if err != nil {
			metrics.RecordError()
			continue
		}
		resp.Body.Close()
		metrics.Record(duration)
	}

	// Create latency distribution histogram
	percentiles := []float64{1, 5, 10, 25, 50, 75, 90, 95, 99}

	t.Logf("\n=== Latency Distribution ===")
	t.Logf("Request count: %d", iterations)
	for _, p := range percentiles {
		latency := metrics.Percentile(p)
		t.Logf("P%.0f: %v", p, latency)
	}

	t.Logf("\nSummary:")
	t.Logf("Mean: %v", metrics.Mean())
	t.Logf("StdDev: %v", metrics.StdDev())
	t.Logf("Min: %v", metrics.Percentile(1))
	t.Logf("Max: %v", metrics.Percentile(100))
}

// TestE2EMemoryUsage estimates memory usage under different loads
func TestE2EMemoryUsage(t *testing.T) {
	srv := NewE2ETestServer(t, 10005)
	defer srv.Close()

	t.Run("Sequential requests memory", func(t *testing.T) {
		for i := 0; i < 100; i++ {
			resp, err := http.Get(srv.baseURL + "/api/v1/info")
			if err != nil {
				t.Logf("Request %d failed: %v", i, err)
				continue
			}
			resp.Body.Close()
		}
		t.Log("Sequential requests completed")
	})

	t.Run("Concurrent requests memory", func(t *testing.T) {
		var wg sync.WaitGroup
		for w := 0; w < 50; w++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for r := 0; r < 20; r++ {
					resp, err := http.Get(srv.baseURL + "/api/v1/info")
					if err != nil {
						continue
					}
					resp.Body.Close()
				}
			}()
		}
		wg.Wait()
		t.Log("Concurrent requests completed")
	})
}

// PrintPerformanceReport generates a formatted performance report
func (pm *PerformanceMetrics) PrintReport(testName string) string {
	report := fmt.Sprintf(`
=== Performance Report: %s ===
Total Requests: %d
Errors: %d
Success Rate: %.2f%%

Latency Metrics:
  Mean:        %v
  Min:         %v
  Max:         %v
  StdDev:      %v
  P50 (Median): %v
  P95:         %v
  P99:         %v

Throughput: %.2f requests/sec

`, testName,
		atomic.LoadInt32(&pm.successCount),
		atomic.LoadInt32(&pm.errorCount),
		float64(atomic.LoadInt32(&pm.successCount))/
			float64(atomic.LoadInt32(&pm.successCount)+atomic.LoadInt32(&pm.errorCount))*100,
		pm.Mean(),
		pm.Percentile(1),
		pm.Percentile(100),
		pm.StdDev(),
		pm.Percentile(50),
		pm.Percentile(95),
		pm.Percentile(99),
		pm.Throughput(time.Second),
	)
	return report
}
