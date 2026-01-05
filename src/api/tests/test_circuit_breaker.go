package main

import (
	"fmt"
	"log"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

// CircuitBreakerTestEvent represents a WebSocket event with timing
type CircuitBreakerTestEvent struct {
	Type       int         `json:"type"`
	Data       interface{} `json:"data"`
	ReceivedAt time.Time
}

// Test scenario: Verify circuit breaker behavior with mock RPC failure
func main() {
	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("CIRCUIT BREAKER VERIFICATION TEST")
	fmt.Println(strings.Repeat("=", 60))

	// Connect to WebSocket server
	u := url.URL{Scheme: "ws", Host: "127.0.0.1:12080", Path: "/ws"}
	fmt.Printf("\nConnecting to %s\n", u.String())

	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		log.Fatalf("Failed to connect to WebSocket server: %v", err)
	}
	defer conn.Close()

	fmt.Println("✅ Connected to WebSocket server!")

	// Subscribe to circuit breaker events
	fmt.Println("\n📡 Subscribing to event types...")
	subscriptionMessage := map[string]interface{}{
		"type": "subscribe",
		"types": []string{
			"system.status",
			"rpc_error",
			"storage.update",
			"connection_error",
			"compression.update",
		},
	}

	if err := conn.WriteJSON(subscriptionMessage); err != nil {
		log.Fatalf("Failed to send subscription message: %v", err)
	}
	fmt.Println("✅ Subscription message sent!")

	// Test parameters
	testDuration := 2 * time.Minute // Test for 2 minutes to observe patterns
	testStart := time.Now()

	// Test state tracking
	testResults := &TestResults{
		Events:                  make([]*CircuitBreakerTestEvent, 0),
		CircuitBreakerOpens:     0,
		CachedDataServed:        0,
		ErrorCodes:              make(map[string]int),
		FirstCircuitBreakerTime: time.Time{},
		FirstRPCDisconnectTime:  time.Time{},
		AutoRecoveryTime:        time.Time{},
	}

	fmt.Printf("\nMonitoring for circuit breaker patterns (duration: %v)...\n\n", testDuration)

	// Read messages
	connectionFailed := false
	for time.Since(testStart) < testDuration {
		// Set a read timeout
		conn.SetReadDeadline(time.Now().Add(10 * time.Second))

		var event CircuitBreakerTestEvent
		if err := conn.ReadJSON(&event); err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				fmt.Printf("❌ WebSocket closed: %v\n", err)
				connectionFailed = true
			} else if err.Error() == "EOF" {
				fmt.Printf("❌ Connection closed by server\n")
				connectionFailed = true
			} else {
				// Timeout or other transient error
				fmt.Printf("⚠️  Read error: %v (continuing...)\n", err)
			}

			// If connection is definitely closed, break
			if connectionFailed && time.Since(testStart) < 5*time.Second {
				fmt.Printf("\nConnection closed too early. Test cannot proceed.\n")
				break
			}
			continue
		}

		event.ReceivedAt = time.Now()
		testResults.Events = append(testResults.Events, &event)

		// Analyze event
		processCircuitBreakerEvent(event, testResults)
	}

	// Print results
	printTestResults(testResults, testStart)
}

// processCircuitBreakerEvent analyzes an event for circuit breaker patterns
func processCircuitBreakerEvent(event CircuitBreakerTestEvent, results *TestResults) {
	dataMap, ok := event.Data.(map[string]interface{})
	if !ok {
		return
	}

	eventTypeName := getEventTypeName(event.Type)
	fmt.Printf("[%s] %s\n", event.ReceivedAt.Format("15:04:05.000"), eventTypeName)

	// Check for error codes
	if errorCode, exists := dataMap["error_code"]; exists {
		if errorCodeStr, ok := errorCode.(string); ok {
			results.ErrorCodes[errorCodeStr]++
			fmt.Printf("  ❌ Error Code: %s\n", errorCodeStr)

			if errorCodeStr == "CIRCUIT_BREAKER_OPEN" {
				results.CircuitBreakerOpens++
				if results.FirstCircuitBreakerTime.IsZero() {
					results.FirstCircuitBreakerTime = event.ReceivedAt
				}
				fmt.Printf("     Circuit breaker is OPEN (count: %d)\n", results.CircuitBreakerOpens)
			} else if errorCodeStr == "RPC_DISCONNECT" {
				if results.FirstRPCDisconnectTime.IsZero() {
					results.FirstRPCDisconnectTime = event.ReceivedAt
				}
				fmt.Printf("     RPC connection failed\n")
			}
		}
	}

	// Check for stale flag (graceful degradation)
	if stale, exists := dataMap["stale"]; exists {
		if staleBool, ok := stale.(bool); ok && staleBool {
			results.CachedDataServed++
			fmt.Printf("  📦 Serving STALE cached data (count: %d)\n", results.CachedDataServed)

			if lastUpdate, exists := dataMap["last_update"]; exists {
				fmt.Printf("     Last successful update: %v\n", lastUpdate)
			}
		} else if staleBool, ok := stale.(bool); ok && !staleBool && results.CircuitBreakerOpens > 0 {
			// Fresh data after circuit was open indicates recovery
			if results.AutoRecoveryTime.IsZero() {
				results.AutoRecoveryTime = event.ReceivedAt
				timeSinceOpen := event.ReceivedAt.Sub(results.FirstCircuitBreakerTime)
				fmt.Printf("  ✅ AUTO-RECOVERY DETECTED\n")
				fmt.Printf("     Time to recover: %v\n", timeSinceOpen)
			}
		}
	}

	// Check for other important fields
	if reason, exists := dataMap["reason"]; exists {
		fmt.Printf("     Reason: %v\n", reason)
	}

	if failures, exists := dataMap["consecutive_failures"]; exists {
		fmt.Printf("     Consecutive failures: %v\n", failures)
	}

	fmt.Println()
}

// TestResults holds the results of the circuit breaker test
type TestResults struct {
	Events                  []*CircuitBreakerTestEvent
	CircuitBreakerOpens     int
	CachedDataServed        int
	ErrorCodes              map[string]int
	FirstCircuitBreakerTime time.Time
	FirstRPCDisconnectTime  time.Time
	AutoRecoveryTime        time.Time
}

// printTestResults prints the final test results and verification status
func printTestResults(results *TestResults, startTime time.Time) {
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("TEST RESULTS AND VERIFICATION")
	fmt.Println(strings.Repeat("=", 60))

	testDuration := time.Since(startTime)
	fmt.Printf("\nTest Duration: %v\n", testDuration)
	fmt.Printf("Total Events: %d\n\n", len(results.Events))

	// Verify error event handling
	fmt.Println("✓ Error Event Handling:")
	fmt.Printf("  Circuit breaker opens detected: %d\n", results.CircuitBreakerOpens)
	fmt.Printf("  RPC disconnect events: %d\n", results.ErrorCodes["RPC_DISCONNECT"])
	fmt.Printf("  System status failed events: %d\n", results.ErrorCodes["SYSTEM_STATUS_FAILED"])

	// Verify graceful degradation
	fmt.Println("\n✓ Graceful Degradation:")
	fmt.Printf("  Stale cached data served: %d times\n", results.CachedDataServed)
	if results.CachedDataServed > 0 {
		fmt.Println("  ✅ Graceful degradation working (stale flag detected)")
	} else {
		fmt.Println("  ⚠️  No graceful degradation observed (may not have failed)")
	}

	// Verify auto-recovery
	fmt.Println("\n✓ Auto-Recovery:")
	if !results.AutoRecoveryTime.IsZero() {
		recoveryTime := results.AutoRecoveryTime.Sub(results.FirstCircuitBreakerTime)
		fmt.Printf("  ✅ Auto-recovery detected after %v\n", recoveryTime)
		if recoveryTime > 4*time.Minute && recoveryTime < 6*time.Minute {
			fmt.Println("     Recovery time is within expected 5-minute window")
		} else {
			fmt.Printf("     ⚠️  Recovery time unexpected (expected ~5 minutes)\n")
		}
	} else if results.CircuitBreakerOpens > 0 {
		fmt.Println("  ⚠️  Circuit breaker opened but auto-recovery not observed in test window")
	} else {
		fmt.Println("  ⚠️  Circuit breaker never opened in test window (RPC may be healthy)")
	}

	// Verify error code detection
	fmt.Println("\n✓ Error Code Detection:")
	if len(results.ErrorCodes) > 0 {
		for errorCode, count := range results.ErrorCodes {
			fmt.Printf("  %s: %d occurrences\n", errorCode, count)
		}
		if _, hasCircuitBreaker := results.ErrorCodes["CIRCUIT_BREAKER_OPEN"]; hasCircuitBreaker {
			fmt.Println("  ✅ CIRCUIT_BREAKER_OPEN error code detected")
		}
		if _, hasRPCDisconnect := results.ErrorCodes["RPC_DISCONNECT"]; hasRPCDisconnect {
			fmt.Println("  ✅ RPC_DISCONNECT error code detected")
		}
	} else {
		fmt.Println("  No error codes detected (RPC connection may be stable)")
	}

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("VERIFICATION SUMMARY")
	fmt.Println(strings.Repeat("=", 60))

	successCriteria := 0
	totalCriteria := 4

	// Criterion 1: Error event handling
	if results.CircuitBreakerOpens > 0 || len(results.ErrorCodes) > 0 {
		fmt.Println("✅ [1/4] Error event types handled (CIRCUIT_BREAKER_OPEN, RPC_DISCONNECT, etc.)")
		successCriteria++
	} else {
		fmt.Println("⚠️  [1/4] Error event types not observed (may need to simulate failure)")
	}

	// Criterion 2: Graceful degradation
	if results.CachedDataServed > 0 {
		fmt.Println("✅ [2/4] Graceful degradation with stale flag working")
		successCriteria++
	} else {
		fmt.Println("⚠️  [2/4] Graceful degradation not observed")
	}

	// Criterion 3: Stale flag in responses
	staleFlagFound := false
	for _, evt := range results.Events {
		if dataMap, ok := evt.Data.(map[string]interface{}); ok {
			if _, exists := dataMap["stale"]; exists {
				staleFlagFound = true
				break
			}
		}
	}
	if staleFlagFound {
		fmt.Println("✅ [3/4] Stale flag present in cached responses")
		successCriteria++
	} else {
		fmt.Println("⚠️  [3/4] Stale flag not found (no cache events)")
	}

	// Criterion 4: Auto-recovery
	if !results.AutoRecoveryTime.IsZero() {
		fmt.Println("✅ [4/4] Auto-recovery confirmed after timeout")
		successCriteria++
	} else if results.CircuitBreakerOpens > 0 {
		fmt.Println("⚠️  [4/4] Auto-recovery not confirmed in test window")
	} else {
		fmt.Println("⚠️  [4/4] Circuit breaker not triggered (test window too short)")
	}

	fmt.Printf("\nPassed: %d/%d criteria\n", successCriteria, totalCriteria)

	if successCriteria == totalCriteria {
		fmt.Println("\n🎉 ALL VERIFICATION CRITERIA MET!")
	} else {
		fmt.Println("\n⚠️  Some criteria not met - review test results above")
	}

	fmt.Println(strings.Repeat("=", 60))
}

// getEventTypeName returns the human-readable name for an event type
func getEventTypeName(eventType int) string {
	names := map[int]string{
		0: "SystemStatus",
		1: "CompressionUpdate",
		2: "AgentStatus",
		3: "RPCError",
		4: "Heartbeat",
		5: "CompressionJobsError",
		6: "AgentStatusError",
	}
	if name, exists := names[eventType]; exists {
		return name
	}
	return fmt.Sprintf("Unknown(%d)", eventType)
}
