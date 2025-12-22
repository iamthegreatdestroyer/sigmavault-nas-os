package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

// Event represents a WebSocket event from the server
type Event struct {
	Type int         `json:"type"`
	Data interface{} `json:"data"`
}

// EventType constants
const (
	TypeSystemStatus         = 0
	TypeCompressionUpdate    = 1
	TypeAgentStatus          = 2
	TypeRPCError             = 3
	TypeHeartbeat            = 4
	TypeCompressionJobsError = 5
	TypeAgentStatusError      = 6
)

var eventTypeNames = map[int]string{
	TypeSystemStatus:         "SystemStatus",
	TypeCompressionUpdate:    "CompressionUpdate",
	TypeAgentStatus:          "AgentStatus",
	TypeRPCError:             "RPCError",
	TypeHeartbeat:            "Heartbeat",
	TypeCompressionJobsError: "CompressionJobsError",
	TypeAgentStatusError:      "AgentStatusError",
}

func main() {
	// Connect to WebSocket server
	u := url.URL{Scheme: "ws", Host: "localhost:8080", Path: "/ws"}
	fmt.Printf("Connecting to %s\n", u.String())

	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		log.Fatalf("Failed to connect to WebSocket server: %v", err)
	}
	defer conn.Close()

	fmt.Println("✅ Connected to WebSocket server!")
	fmt.Println("\nMonitoring events (press Ctrl+C to stop)...\n")

	// Track timing and errors
	eventCounts := make(map[int]int)
	errorCounts := make(map[string]int)
	var lastEventTime time.Time
	eventIntervals := []time.Duration{}
	connectedTime := time.Now()
	
	// Circuit breaker state tracking
	circuitBreakerOpenDetected := false
	staleDataReceived := false
	autoRecoveryDetected := false
	
	rpcDisconnectTime := time.Time{}
	circuitBreakerTime := time.Time{}

	// Read messages
	for {
		var event Event
		err := conn.ReadJSON(&event)
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}

		eventTime := time.Now()
		eventCounts[event.Type]++

		// Calculate interval from last event
		if !lastEventTime.IsZero() {
			interval := eventTime.Sub(lastEventTime)
			eventIntervals = append(eventIntervals, interval)
		}
		lastEventTime = eventTime

		// Print event
		typeName := eventTypeNames[event.Type]
		fmt.Printf("[%s] Type: %d (%s)\n", eventTime.Format("15:04:05.000"), event.Type, typeName)

		// Parse and analyze data based on event type
		if dataJSON, err := json.MarshalIndent(event.Data, "  ", "  "); err == nil {
			fmt.Printf("  Data: %s\n", string(dataJSON))
		}
		
		// Analyze event content for circuit breaker patterns
		dataMap, ok := event.Data.(map[string]interface{})
		if ok {
			analyzeEventData(event.Type, dataMap, &errorCounts, &circuitBreakerOpenDetected,
				&staleDataReceived, &autoRecoveryDetected, &rpcDisconnectTime, &circuitBreakerTime)
		}

		// Print interval if available
		if len(eventIntervals) > 0 {
			lastInterval := eventIntervals[len(eventIntervals)-1]
			fmt.Printf("  Interval: %v\n", lastInterval)
		}
		fmt.Println()
	}

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("Connection Summary")
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("Connected for: %v\n", time.Since(connectedTime))
	fmt.Println("\nEvents Received:")
	for typeID, count := range eventCounts {
		typeName := eventTypeNames[typeID]
		fmt.Printf("  %s (type %d): %d\n", typeName, typeID, count)
	}
	
	// Print error analysis
	if len(errorCounts) > 0 {
		fmt.Println("\nError Codes Detected:")
		for errorCode, count := range errorCounts {
			fmt.Printf("  %s: %d\n", errorCode, count)
		}
	}
	
	// Print circuit breaker verification results
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("Circuit Breaker Verification Results")
	fmt.Println(strings.Repeat("=", 50))
	if circuitBreakerOpenDetected {
		fmt.Println("✅ CIRCUIT_BREAKER_OPEN error code received")
		if !circuitBreakerTime.IsZero() {
			fmt.Printf("   First occurrence: %s\n", circuitBreakerTime.Format("15:04:05.000"))
		}
	} else {
		fmt.Println("❌ CIRCUIT_BREAKER_OPEN error code NOT detected")
	}
	
	if staleDataReceived {
		fmt.Println("✅ Graceful degradation with stale flag detected")
	} else {
		fmt.Println("❌ Graceful degradation NOT detected (stale flag not found)")
	}
	
	if !rpcDisconnectTime.IsZero() {
		fmt.Printf("✅ RPC_DISCONNECT detected at %s\n", rpcDisconnectTime.Format("15:04:05.000"))
	}
	
	if autoRecoveryDetected {
		fmt.Println("✅ Auto-recovery after timeout detected (normal events resumed)")
	} else {
		fmt.Println("⚠️  Auto-recovery NOT confirmed in this test run")
	}

	// Calculate average interval
	if len(eventIntervals) > 0 {
		total := time.Duration(0)
		for _, interval := range eventIntervals {
			total += interval
		}
		avgInterval := total / time.Duration(len(eventIntervals))
		fmt.Printf("\nAverage Event Interval: %v (expected: ~5s)\n", avgInterval)
		fmt.Printf("Min Interval: %v\n", minDuration(eventIntervals))
		fmt.Printf("Max Interval: %v\n", maxDuration(eventIntervals))
	}
}

func minDuration(durations []time.Duration) time.Duration {
	if len(durations) == 0 {
		return 0
	}
	min := durations[0]
	for _, d := range durations[1:] {
		if d < min {
			min = d
		}
	}
	return min
}

func maxDuration(durations []time.Duration) time.Duration {
	if len(durations) == 0 {
		return 0
	}
	max := durations[0]
	for _, d := range durations[1:] {
		if d > max {
			max = d
		}
	}
	return max
}

// analyzeEventData examines event data for circuit breaker patterns and error codes
func analyzeEventData(eventType int, dataMap map[string]interface{}, 
	errorCounts *map[string]int,
	circuitBreakerOpenDetected *bool,
	staleDataReceived *bool,
	autoRecoveryDetected *bool,
	rpcDisconnectTime *time.Time,
	circuitBreakerTime *time.Time) {
	
	// Check for error_code field
	if errorCode, exists := dataMap["error_code"]; exists {
		if errorCodeStr, ok := errorCode.(string); ok {
			(*errorCounts)[errorCodeStr]++
			
			// Track specific error codes
			if errorCodeStr == "CIRCUIT_BREAKER_OPEN" {
				*circuitBreakerOpenDetected = true
				if circuitBreakerTime.IsZero() {
					*circuitBreakerTime = time.Now()
				}
				fmt.Printf("  ⚠️  Circuit breaker OPEN detected!\n")
			} else if errorCodeStr == "RPC_DISCONNECT" {
				if rpcDisconnectTime.IsZero() {
					*rpcDisconnectTime = time.Now()
				}
				fmt.Printf("  ⚠️  RPC disconnection detected\n")
			}
		}
	}
	
	// Check for stale flag (indicates graceful degradation with cached data)
	if stale, exists := dataMap["stale"]; exists {
		if staleBool, ok := stale.(bool); ok && staleBool {
			*staleDataReceived = true
			fmt.Printf("  📦 Stale flag detected - serving cached data\n")
			
			// Print cache metadata if available
			if lastUpdate, exists := dataMap["last_update"]; exists {
				fmt.Printf("     Last update: %v\n", lastUpdate)
			}
		}
	}
	
	// Detect auto-recovery by checking for successful status updates after errors
	if eventType == TypeSystemStatus {
		if stale, exists := dataMap["stale"]; exists {
			if staleBool, ok := stale.(bool); ok && !staleBool {
				// Fresh data received after stale period indicates recovery
				if *staleDataReceived && *circuitBreakerOpenDetected {
					*autoRecoveryDetected = true
					fmt.Printf("  ✅ Auto-recovery detected - fresh data received\n")
				}
			}
		}
	}
	
	// Print reason if available (for RPC errors)
	if reason, exists := dataMap["reason"]; exists {
		if reasonStr, ok := reason.(string); ok {
			fmt.Printf("     Reason: %s\n", reasonStr)
		}
	}
	
	// Print consecutive failures if available
	if failures, exists := dataMap["consecutive_failures"]; exists {
		if failureCount, ok := failures.(float64); ok {
			fmt.Printf("     Consecutive failures: %.0f\n", failureCount)
		}
	}
}
