// Package main implements Task 2.7.5.4 - Cache Synchronization testing
// Tests graceful degradation with stale flag when RPC fails
package main

import (
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

// MessageType defines WebSocket message types (string-based)
type MessageType = string

const (
	TypeSystemStatus      MessageType = "system.status"
	TypeStorageUpdate     MessageType = "storage.update"
	TypeAgentStatus       MessageType = "agent.status"
	TypeCompressionUpdate MessageType = "compression.update"
	TypeNotification      MessageType = "notification"
	TypeRPCError          MessageType = "rpc_error"
	TypeConnectionError   MessageType = "connection_error"
	TypeHeartbeat         MessageType = "heartbeat"
)

type Event struct {
	Type      MessageType     `json:"type"`
	Timestamp time.Time       `json:"timestamp"`
	Data      json.RawMessage `json:"data,omitempty"`
}

// CacheTestResults tracks cache behavior observations
type CacheTestResults struct {
	mu sync.Mutex

	// Event counts
	TotalEvents     int
	SystemStatusOK  int
	SystemStatusErr int
	StaleDataEvents int
	RPCErrorEvents  int
	OtherEvents     int

	// Timing
	StartTime     time.Time
	LastEventTime time.Time
	LastStaleTime time.Time
	LastFreshTime time.Time

	// Cache content tracking
	LastCachedHostname string
	StaleFlagSeen      bool
	ErrorCodeSeen      bool
	LastUpdateSeen     bool
}

func main() {
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("   Task 2.7.5.4 - CACHE SYNCHRONIZATION TEST")
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println()
	fmt.Println("PURPOSE: Verify graceful degradation when RPC fails")
	fmt.Println("  - Server caches last successful RPC response")
	fmt.Println("  - On RPC failure, server broadcasts cached data with stale=true")
	fmt.Println("  - Client can distinguish fresh vs stale data")
	fmt.Println()
	fmt.Println("HOW TO TEST:")
	fmt.Println("  1. Start this test with RPC running → observe fresh data")
	fmt.Println("  2. Stop the Python RPC engine (Ctrl+C on port 8002)")
	fmt.Println("  3. Observe stale flag appearing in system.status events")
	fmt.Println("  4. Restart RPC → observe recovery to fresh data")
	fmt.Println()
	fmt.Println("Press Ctrl+C to stop the test")
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println()

	// Connect to WebSocket
	serverURL := "ws://127.0.0.1:12080/ws"
	u, _ := url.Parse(serverURL)

	fmt.Printf("🔌 Connecting to %s...\n", serverURL)
	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		fmt.Printf("❌ Connection failed: %v\n", err)
		os.Exit(1)
	}
	defer conn.Close()
	fmt.Println("✅ Connected!")
	fmt.Println()

	// Initialize results
	results := &CacheTestResults{
		StartTime: time.Now(),
	}

	// Handle shutdown gracefully
	done := make(chan os.Signal, 1)
	signal.Notify(done, os.Interrupt, syscall.SIGTERM)

	// Start event reader
	eventChan := make(chan Event, 100)
	go readEvents(conn, eventChan)

	// Start status reporter
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	fmt.Println("📡 Monitoring events...")
	fmt.Println("─────────────────────────────────────────────────────────")

	for {
		select {
		case <-done:
			fmt.Println()
			printFinalReport(results)
			return

		case event := <-eventChan:
			processEvent(event, results)

		case <-ticker.C:
			printInterimReport(results)
		}
	}
}

func readEvents(conn *websocket.Conn, eventChan chan<- Event) {
	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			fmt.Printf("❌ WebSocket read error: %v\n", err)
			return
		}

		var event Event
		if err := json.Unmarshal(message, &event); err != nil {
			fmt.Printf("⚠️  Failed to parse event: %v\n", err)
			continue
		}

		eventChan <- event
	}
}

func processEvent(event Event, results *CacheTestResults) {
	results.mu.Lock()
	defer results.mu.Unlock()

	results.TotalEvents++
	results.LastEventTime = time.Now()

	timestamp := time.Now().Format("15:04:05")

	switch event.Type {
	case TypeSystemStatus:
		// Parse the data to check for stale flag
		var data map[string]interface{}
		if err := json.Unmarshal(event.Data, &data); err != nil {
			results.SystemStatusErr++
			return
		}

		// Check for stale flag
		isStale := false
		if stale, ok := data["stale"].(bool); ok && stale {
			isStale = true
			results.StaleDataEvents++
			results.LastStaleTime = time.Now()
			results.StaleFlagSeen = true
		} else {
			results.SystemStatusOK++
			results.LastFreshTime = time.Now()
		}

		// Check for error_code (indicates RPC failure)
		if errorCode, ok := data["error_code"].(string); ok && errorCode != "" {
			results.ErrorCodeSeen = true
		}

		// Check for last_update field (present in stale data)
		if _, ok := data["last_update"]; ok {
			results.LastUpdateSeen = true
		}

		// Track hostname
		if hostname, ok := data["hostname"].(string); ok {
			results.LastCachedHostname = hostname
		}

		// Output with visual indicator
		cpuUsage := 0.0
		if cpu, ok := data["cpu_usage"].(float64); ok {
			cpuUsage = cpu
		}

		if isStale {
			fmt.Printf("[%s] 📦 STALE system.status | CPU: %.1f%% | hostname: %s | error_code: %v\n",
				timestamp, cpuUsage,
				results.LastCachedHostname,
				data["error_code"])
		} else {
			fmt.Printf("[%s] ✅ FRESH system.status | CPU: %.1f%% | hostname: %s\n",
				timestamp, cpuUsage, results.LastCachedHostname)
		}

	case TypeRPCError:
		results.RPCErrorEvents++
		var data map[string]interface{}
		if err := json.Unmarshal(event.Data, &data); err == nil {
			reason := data["reason"]
			errorCode := data["error_code"]
			failures := data["consecutive_failures"]
			fmt.Printf("[%s] 🔴 RPC_ERROR | reason: %v | code: %v | failures: %v\n",
				timestamp, reason, errorCode, failures)
		}

	default:
		results.OtherEvents++
		fmt.Printf("[%s] 📨 %s event received\n", timestamp, event.Type)
	}
}

func printInterimReport(results *CacheTestResults) {
	results.mu.Lock()
	defer results.mu.Unlock()

	elapsed := time.Since(results.StartTime)
	fmt.Println()
	fmt.Println("─────────────────────────────────────────────────────────")
	fmt.Printf("📊 INTERIM REPORT (%.0f seconds elapsed)\n", elapsed.Seconds())
	fmt.Printf("   Total events: %d\n", results.TotalEvents)
	fmt.Printf("   Fresh status: %d | Stale status: %d | RPC errors: %d\n",
		results.SystemStatusOK, results.StaleDataEvents, results.RPCErrorEvents)
	fmt.Printf("   Stale flag seen: %v | Error code seen: %v\n",
		results.StaleFlagSeen, results.ErrorCodeSeen)
	fmt.Println("─────────────────────────────────────────────────────────")
	fmt.Println()
}

func printFinalReport(results *CacheTestResults) {
	results.mu.Lock()
	defer results.mu.Unlock()

	elapsed := time.Since(results.StartTime)

	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("                    FINAL TEST REPORT")
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Printf("Test Duration: %.1f seconds\n", elapsed.Seconds())
	fmt.Println()

	fmt.Println("EVENT SUMMARY")
	fmt.Println("─────────────────────────────────────────────────────────")
	fmt.Printf("  Total events received:     %d\n", results.TotalEvents)
	fmt.Printf("  Fresh system.status:       %d\n", results.SystemStatusOK)
	fmt.Printf("  Stale system.status:       %d\n", results.StaleDataEvents)
	fmt.Printf("  RPC error events:          %d\n", results.RPCErrorEvents)
	fmt.Printf("  Other events:              %d\n", results.OtherEvents)
	fmt.Println()

	fmt.Println("CACHE BEHAVIOR VERIFICATION")
	fmt.Println("─────────────────────────────────────────────────────────")

	// Check 1: Fresh data received
	if results.SystemStatusOK > 0 {
		fmt.Println("  ✅ Fresh data received (RPC working)")
	} else {
		fmt.Println("  ⚠️  No fresh data received")
	}

	// Check 2: Stale flag detection
	if results.StaleFlagSeen {
		fmt.Println("  ✅ Stale flag detected in cached responses")
	} else {
		fmt.Println("  ⏳ Stale flag not seen (stop RPC to test)")
	}

	// Check 3: Error code present
	if results.ErrorCodeSeen {
		fmt.Println("  ✅ Error code present in stale data")
	} else if results.StaleFlagSeen {
		fmt.Println("  ⚠️  Stale data missing error_code field")
	} else {
		fmt.Println("  ⏳ Error code not tested (need RPC failure)")
	}

	// Check 4: RPC errors broadcast
	if results.RPCErrorEvents > 0 {
		fmt.Println("  ✅ RPC error events broadcast to clients")
	} else {
		fmt.Println("  ⏳ No RPC errors observed")
	}

	// Check 5: Last update timestamp
	if results.LastUpdateSeen {
		fmt.Println("  ✅ last_update timestamp present in stale data")
	} else if results.StaleFlagSeen {
		fmt.Println("  ⚠️  Stale data missing last_update field")
	} else {
		fmt.Println("  ⏳ last_update not tested (need RPC failure)")
	}

	fmt.Println()

	// Overall assessment
	fmt.Println("OVERALL ASSESSMENT")
	fmt.Println("─────────────────────────────────────────────────────────")
	if results.SystemStatusOK > 0 && results.StaleFlagSeen && results.RPCErrorEvents > 0 {
		fmt.Println("  🎉 FULL CACHE SYNC VERIFIED")
		fmt.Println("     - Server caches data successfully")
		fmt.Println("     - Stale flag indicates degraded mode")
		fmt.Println("     - RPC errors broadcast to clients")
	} else if results.SystemStatusOK > 0 {
		fmt.Println("  ⏳ PARTIAL TEST - Fresh data OK")
		fmt.Println("     To complete test: stop Python RPC, observe stale data")
	} else {
		fmt.Println("  ❓ INCONCLUSIVE - Need more test time")
	}
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
}
