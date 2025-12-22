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
	TypeSystemStatus       = 0
	TypeCompressionUpdate  = 1
	TypeAgentStatus        = 2
	TypeError              = 3
	TypeHeartbeat          = 4
)

var eventTypeNames = map[int]string{
	TypeSystemStatus:      "SystemStatus",
	TypeCompressionUpdate: "CompressionUpdate",
	TypeAgentStatus:       "AgentStatus",
	TypeError:             "Error",
	TypeHeartbeat:         "Heartbeat",
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

	// Track timing
	eventCounts := make(map[int]int)
	var lastEventTime time.Time
	eventIntervals := []time.Duration{}
	connectedTime := time.Now()

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

		// Print data
		if dataJSON, err := json.MarshalIndent(event.Data, "  ", "  "); err == nil {
			fmt.Printf("  Data: %s\n", string(dataJSON))
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
