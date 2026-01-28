// Package main implements Task 2.7.5.5 - WebSocket Performance Testing
// Tests concurrent connections, message throughput, and resource usage
package main

import (
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"os/signal"
	"runtime"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

// MessageType for WebSocket events
type MessageType = string

type Event struct {
	Type      MessageType     `json:"type"`
	Timestamp time.Time       `json:"timestamp"`
	Data      json.RawMessage `json:"data,omitempty"`
}

// PerformanceStats tracks metrics across all connections
type PerformanceStats struct {
	mu sync.RWMutex

	// Connection metrics
	TotalConnections   int32
	ActiveConnections  int32
	FailedConnections  int32
	ConnectionAttempts int32

	// Message metrics
	TotalMessages     int64
	MessagesPerSecond float64
	AverageLatency    time.Duration
	MaxLatency        time.Duration

	// Resource metrics
	Goroutines int
	HeapAlloc  uint64
	HeapSys    uint64

	// Timing
	StartTime       time.Time
	LastMessageTime time.Time

	// Per-connection tracking
	messageCounters map[int]int64
}

func main() {
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("   Task 2.7.5.5 - WEBSOCKET PERFORMANCE TEST")
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println()
	fmt.Println("PURPOSE: Test WebSocket server under concurrent load")
	fmt.Println("  - Establish multiple simultaneous connections")
	fmt.Println("  - Measure message throughput per connection")
	fmt.Println("  - Monitor resource usage (memory, goroutines)")
	fmt.Println()

	// Configuration
	serverURL := "ws://127.0.0.1:12080/ws"
	numConnections := 10 // Number of concurrent connections
	testDuration := 30 * time.Second

	fmt.Printf("Configuration:\n")
	fmt.Printf("  Server: %s\n", serverURL)
	fmt.Printf("  Concurrent connections: %d\n", numConnections)
	fmt.Printf("  Test duration: %v\n", testDuration)
	fmt.Println()
	fmt.Println("Press Ctrl+C to stop early")
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println()

	// Initialize stats
	stats := &PerformanceStats{
		StartTime:       time.Now(),
		messageCounters: make(map[int]int64),
	}

	// Handle shutdown
	done := make(chan os.Signal, 1)
	signal.Notify(done, os.Interrupt, syscall.SIGTERM)

	// Create connections
	var wg sync.WaitGroup
	stopChan := make(chan struct{})

	fmt.Printf("🔌 Establishing %d concurrent connections...\n", numConnections)

	for i := 0; i < numConnections; i++ {
		wg.Add(1)
		go func(connID int) {
			defer wg.Done()
			runConnection(connID, serverURL, stats, stopChan)
		}(i)
		time.Sleep(50 * time.Millisecond) // Stagger connections slightly
	}

	// Wait for connections to establish
	time.Sleep(500 * time.Millisecond)
	printConnectionStatus(stats)

	// Start metrics reporter
	metricsTicker := time.NewTicker(5 * time.Second)
	defer metricsTicker.Stop()

	// Create test timer
	testTimer := time.NewTimer(testDuration)
	defer testTimer.Stop()

	fmt.Println()
	fmt.Println("📡 Monitoring performance...")
	fmt.Println("─────────────────────────────────────────────────────────")

	lastMessageCount := int64(0)
	lastTime := time.Now()

	for {
		select {
		case <-done:
			fmt.Println("\n⚠️  Test interrupted by user")
			close(stopChan)
			goto cleanup

		case <-testTimer.C:
			fmt.Println("\n✅ Test duration completed")
			close(stopChan)
			goto cleanup

		case <-metricsTicker.C:
			// Calculate messages per second
			currentCount := atomic.LoadInt64(&stats.TotalMessages)
			elapsed := time.Since(lastTime).Seconds()
			mps := float64(currentCount-lastMessageCount) / elapsed
			lastMessageCount = currentCount
			lastTime = time.Now()

			// Update stats
			stats.mu.Lock()
			stats.MessagesPerSecond = mps
			stats.Goroutines = runtime.NumGoroutine()
			var m runtime.MemStats
			runtime.ReadMemStats(&m)
			stats.HeapAlloc = m.HeapAlloc
			stats.HeapSys = m.HeapSys
			stats.mu.Unlock()

			printMetrics(stats)
		}
	}

cleanup:
	// Wait for all connections to close
	fmt.Println("\n⏳ Closing connections...")

	// Give connections time to close
	closeChan := make(chan struct{})
	go func() {
		wg.Wait()
		close(closeChan)
	}()

	select {
	case <-closeChan:
		fmt.Println("✅ All connections closed")
	case <-time.After(5 * time.Second):
		fmt.Println("⚠️  Some connections timed out")
	}

	printFinalReport(stats)
}

func runConnection(connID int, serverURL string, stats *PerformanceStats, stop <-chan struct{}) {
	atomic.AddInt32(&stats.ConnectionAttempts, 1)

	u, _ := url.Parse(serverURL)
	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		atomic.AddInt32(&stats.FailedConnections, 1)
		fmt.Printf("  ❌ Connection %d failed: %v\n", connID, err)
		return
	}
	defer conn.Close()

	atomic.AddInt32(&stats.ActiveConnections, 1)
	atomic.AddInt32(&stats.TotalConnections, 1)

	defer func() {
		atomic.AddInt32(&stats.ActiveConnections, -1)
	}()

	// Read messages until stopped
	messageChan := make(chan struct{}, 100)
	go func() {
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				return
			}

			var event Event
			if err := json.Unmarshal(message, &event); err == nil {
				atomic.AddInt64(&stats.TotalMessages, 1)
				stats.mu.Lock()
				stats.messageCounters[connID]++
				stats.LastMessageTime = time.Now()
				stats.mu.Unlock()
			}

			select {
			case messageChan <- struct{}{}:
			default:
			}
		}
	}()

	// Wait for stop signal
	<-stop
}

func printConnectionStatus(stats *PerformanceStats) {
	active := atomic.LoadInt32(&stats.ActiveConnections)
	failed := atomic.LoadInt32(&stats.FailedConnections)
	attempts := atomic.LoadInt32(&stats.ConnectionAttempts)

	fmt.Printf("\n📊 Connection Status:\n")
	fmt.Printf("  Active:  %d\n", active)
	fmt.Printf("  Failed:  %d\n", failed)
	fmt.Printf("  Total:   %d attempts\n", attempts)
}

func printMetrics(stats *PerformanceStats) {
	stats.mu.RLock()
	defer stats.mu.RUnlock()

	elapsed := time.Since(stats.StartTime)
	active := atomic.LoadInt32(&stats.ActiveConnections)
	totalMsgs := atomic.LoadInt64(&stats.TotalMessages)

	fmt.Printf("\n[%.0fs] Active: %d | Messages: %d | Rate: %.1f/s | Goroutines: %d | Heap: %.1f MB\n",
		elapsed.Seconds(),
		active,
		totalMsgs,
		stats.MessagesPerSecond,
		stats.Goroutines,
		float64(stats.HeapAlloc)/(1024*1024))
}

func printFinalReport(stats *PerformanceStats) {
	stats.mu.RLock()
	defer stats.mu.RUnlock()

	elapsed := time.Since(stats.StartTime)
	totalMsgs := atomic.LoadInt64(&stats.TotalMessages)
	avgRate := float64(totalMsgs) / elapsed.Seconds()

	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("                    PERFORMANCE REPORT")
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Printf("Test Duration: %.1f seconds\n", elapsed.Seconds())
	fmt.Println()

	fmt.Println("CONNECTION METRICS")
	fmt.Println("─────────────────────────────────────────────────────────")
	fmt.Printf("  Total connection attempts:  %d\n", stats.ConnectionAttempts)
	fmt.Printf("  Successful connections:     %d\n", stats.TotalConnections)
	fmt.Printf("  Failed connections:         %d\n", stats.FailedConnections)
	fmt.Printf("  Final active connections:   %d\n", stats.ActiveConnections)
	fmt.Println()

	fmt.Println("MESSAGE METRICS")
	fmt.Println("─────────────────────────────────────────────────────────")
	fmt.Printf("  Total messages received:    %d\n", totalMsgs)
	fmt.Printf("  Average messages/second:    %.2f\n", avgRate)
	fmt.Printf("  Messages per connection:    %.1f avg\n",
		float64(totalMsgs)/float64(stats.TotalConnections))
	fmt.Println()

	fmt.Println("RESOURCE METRICS (Final)")
	fmt.Println("─────────────────────────────────────────────────────────")
	fmt.Printf("  Goroutines:                 %d\n", stats.Goroutines)
	fmt.Printf("  Heap allocated:             %.2f MB\n", float64(stats.HeapAlloc)/(1024*1024))
	fmt.Printf("  Heap system:                %.2f MB\n", float64(stats.HeapSys)/(1024*1024))
	fmt.Println()

	// Per-connection breakdown
	fmt.Println("PER-CONNECTION BREAKDOWN")
	fmt.Println("─────────────────────────────────────────────────────────")
	for connID, count := range stats.messageCounters {
		fmt.Printf("  Connection %d: %d messages\n", connID, count)
	}
	fmt.Println()

	// Assessment
	fmt.Println("PERFORMANCE ASSESSMENT")
	fmt.Println("─────────────────────────────────────────────────────────")

	// Connection success rate
	successRate := float64(stats.TotalConnections) / float64(stats.ConnectionAttempts) * 100
	if successRate >= 100 {
		fmt.Printf("  ✅ Connection success rate: %.0f%%\n", successRate)
	} else if successRate >= 90 {
		fmt.Printf("  ⚠️  Connection success rate: %.0f%%\n", successRate)
	} else {
		fmt.Printf("  ❌ Connection success rate: %.0f%%\n", successRate)
	}

	// Message throughput (expect ~2 events per connection per 5 seconds = ~4/s for 10 connections)
	expectedRate := float64(stats.TotalConnections) * 0.4 // ~2 events/5s per connection
	if avgRate >= expectedRate*0.8 {
		fmt.Printf("  ✅ Message throughput: %.2f/s (expected ~%.1f/s)\n", avgRate, expectedRate)
	} else {
		fmt.Printf("  ⚠️  Message throughput: %.2f/s (expected ~%.1f/s)\n", avgRate, expectedRate)
	}

	// Memory usage (should be reasonable)
	heapMB := float64(stats.HeapAlloc) / (1024 * 1024)
	if heapMB < 50 {
		fmt.Printf("  ✅ Memory usage: %.2f MB (acceptable)\n", heapMB)
	} else if heapMB < 100 {
		fmt.Printf("  ⚠️  Memory usage: %.2f MB (moderate)\n", heapMB)
	} else {
		fmt.Printf("  ❌ Memory usage: %.2f MB (high)\n", heapMB)
	}

	// Goroutine count (should be proportional to connections)
	expectedGoroutines := int(stats.TotalConnections)*2 + 20 // 2 per connection + baseline
	if stats.Goroutines <= expectedGoroutines {
		fmt.Printf("  ✅ Goroutine count: %d (expected ~%d)\n", stats.Goroutines, expectedGoroutines)
	} else {
		fmt.Printf("  ⚠️  Goroutine count: %d (expected ~%d)\n", stats.Goroutines, expectedGoroutines)
	}

	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
}
