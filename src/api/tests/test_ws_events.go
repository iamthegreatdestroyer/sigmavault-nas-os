//go:build ignore
// +build ignore

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"os"
	"os/signal"
	"time"

	"github.com/gorilla/websocket"
)

// MessageType matches the server's string-based type
type MessageType string

// Message matches the server's message structure
type Message struct {
	Type      MessageType     `json:"type"`
	Timestamp time.Time       `json:"timestamp"`
	Data      json.RawMessage `json:"data,omitempty"`
}

// Event types from hub.go
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

func main() {
	fmt.Println("========================================")
	fmt.Println("WebSocket Event Delivery Test")
	fmt.Println("========================================")
	fmt.Println()

	// Connect to WebSocket server
	u := url.URL{Scheme: "ws", Host: "127.0.0.1:12080", Path: "/ws"}
	fmt.Printf("Connecting to %s...\n", u.String())

	conn, resp, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer conn.Close()

	fmt.Printf("✅ Connected! (HTTP %d)\n", resp.StatusCode)

	// Channel for interrupt
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt)

	// Channel for messages
	done := make(chan struct{})
	eventCount := 0
	eventsByType := make(map[MessageType]int)

	// Start reading messages
	go func() {
		defer close(done)
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
					log.Printf("Read error: %v", err)
				}
				return
			}

			var msg Message
			if err := json.Unmarshal(message, &msg); err != nil {
				fmt.Printf("❌ Failed to parse message: %s\n", string(message))
				continue
			}

			eventCount++
			eventsByType[msg.Type]++
			fmt.Printf("[%s] Type: %s | Data: %.100s...\n",
				time.Now().Format("15:04:05"),
				msg.Type,
				string(msg.Data))
		}
	}()

	// Wait for events (poll interval is 5s, wait for 20s to capture multiple polls)
	testDuration := 20 * time.Second
	fmt.Printf("\nWaiting for events (duration: %v, poll interval: 5s)...\n\n", testDuration)

	select {
	case <-time.After(testDuration):
		fmt.Println("\n⏱️ Test duration complete")
	case <-interrupt:
		fmt.Println("\n⚠️ Interrupted")
	case <-done:
		fmt.Println("\n❌ Connection closed unexpectedly")
	}

	// Close connection
	conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
	time.Sleep(100 * time.Millisecond)

	// Print summary
	fmt.Println("\n========================================")
	fmt.Println("Test Results")
	fmt.Println("========================================")
	fmt.Printf("Total events received: %d\n", eventCount)
	if eventCount > 0 {
		fmt.Println("\nEvents by type:")
		for t, c := range eventsByType {
			fmt.Printf("  %s: %d\n", t, c)
		}
		fmt.Println("\n✅ SUCCESS: Events are being delivered!")
	} else {
		fmt.Println("\n❌ FAILURE: No events received")
		fmt.Println("\nPossible causes:")
		fmt.Println("  1. RPC engine not running or not returning data")
		fmt.Println("  2. EventSubscriber not started")
		fmt.Println("  3. Hub not broadcasting events")
	}
}
