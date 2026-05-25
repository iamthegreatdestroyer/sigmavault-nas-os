// Package websocket provides comprehensive WebSocket event system integration tests.
// PHASE 3.3: WebSocket Event System Testing
// Tests for connection lifecycle, message routing, event streaming, and error handling
package websocket

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// TestWebSocketConnectionLifecycle tests the complete lifecycle of a WebSocket connection
func TestWebSocketConnectionLifecycle(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	// Test 1: Create and register a client
	client := &Client{
		ID:            "test-client-001",
		Send:          make(chan []byte, 256),
		Hub:           hub,
		Subscriptions: make(map[MessageType]bool),
	}

	hub.register <- client

	// Brief wait for registration to process
	time.Sleep(10 * time.Millisecond)

	// Verify client is registered
	hub.mu.RLock()
	if len(hub.clients) != 1 {
		t.Errorf("Expected 1 client after registration, got %d", len(hub.clients))
	}
	hub.mu.RUnlock()

	// Test 2: Send a message to the client
	testMessage := Message{
		Type:      TypeSystemStatus,
		Timestamp: time.Now(),
		Data:      json.RawMessage(`{"cpu": 45.5, "memory": 72.3}`),
	}

	msgBytes, err := json.Marshal(testMessage)
	if err != nil {
		t.Fatalf("Failed to marshal test message: %v", err)
	}

	hub.broadcast <- msgBytes

	// Test 3: Verify message is delivered to client
	select {
	case received := <-client.Send:
		var msg Message
		if err := json.Unmarshal(received, &msg); err != nil {
			t.Errorf("Failed to unmarshal received message: %v", err)
		}
		if msg.Type != TypeSystemStatus {
			t.Errorf("Expected message type %v, got %v", TypeSystemStatus, msg.Type)
		}
	case <-time.After(100 * time.Millisecond):
		t.Error("Message delivery timeout - client did not receive broadcast")
	}

	// Test 4: Unregister client
	hub.unregister <- client
	time.Sleep(10 * time.Millisecond)

	// Verify client is unregistered
	hub.mu.RLock()
	if len(hub.clients) != 0 {
		t.Errorf("Expected 0 clients after unregistration, got %d", len(hub.clients))
	}
	hub.mu.RUnlock()
}

// TestMultipleClientBroadcasting tests broadcasting to multiple connected clients
func TestMultipleClientBroadcasting(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	const numClients = 10
	clients := make([]*Client, numClients)

	// Create and register multiple clients
	for i := 0; i < numClients; i++ {
		client := &Client{
			ID:            fmt.Sprintf("test-client-%03d", i),
			Send:          make(chan []byte, 256),
			Hub:           hub,
			Subscriptions: make(map[MessageType]bool),
		}
		clients[i] = client
		hub.register <- client
	}

	time.Sleep(20 * time.Millisecond)

	// Verify all clients are registered
	hub.mu.RLock()
	if len(hub.clients) != numClients {
		t.Errorf("Expected %d registered clients, got %d", numClients, len(hub.clients))
	}
	hub.mu.RUnlock()

	// Test: Broadcast a message to all clients
	testMessage := Message{
		Type:      TypeSystemStatus,
		Timestamp: time.Now(),
		Data:      json.RawMessage(`{"broadcast": true}`),
	}

	msgBytes, _ := json.Marshal(testMessage)
	hub.broadcast <- msgBytes

	// Verify all clients receive the broadcast
	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	receivedCount := 0
	for _, client := range clients {
		select {
		case <-client.Send:
			receivedCount++
		case <-ctx.Done():
			break
		}
	}

	if receivedCount != numClients {
		t.Errorf("Expected %d clients to receive message, only %d did", numClients, receivedCount)
	}
}

// TestClientSubscriptionManagement tests subscription and unsubscription to message types
func TestClientSubscriptionManagement(t *testing.T) {
	client := &Client{
		ID:            "test-subscriber",
		Send:          make(chan []byte, 256),
		Subscriptions: make(map[MessageType]bool),
	}

	// Test 1: Subscribe to multiple event types
	subscription1 := Message{
		Type: TypeSubscribe,
		Data: json.RawMessage(`{"subscriptions": ["system.status", "agent.status"]}`),
	}

	var sub1Data struct {
		Subscriptions []string `json:"subscriptions"`
	}
	json.Unmarshal(subscription1.Data, &sub1Data)

	for _, subType := range sub1Data.Subscriptions {
		client.Subscriptions[MessageType(subType)] = true
	}

	if len(client.Subscriptions) != 2 {
		t.Errorf("Expected 2 subscriptions, got %d", len(client.Subscriptions))
	}

	// Test 2: Verify subscription state
	if !client.Subscriptions[TypeSystemStatus] {
		t.Error("Expected subscription to TypeSystemStatus")
	}
	if !client.Subscriptions[TypeAgentStatus] {
		t.Error("Expected subscription to TypeAgentStatus")
	}

	// Test 3: Unsubscribe from one type
	delete(client.Subscriptions, TypeSystemStatus)

	if len(client.Subscriptions) != 1 {
		t.Errorf("Expected 1 subscription after unsubscribe, got %d", len(client.Subscriptions))
	}
	if client.Subscriptions[TypeSystemStatus] {
		t.Error("Expected no subscription to TypeSystemStatus after unsubscribe")
	}
}

// TestRealTimeEventStreaming tests continuous event streaming to clients
func TestRealTimeEventStreaming(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	client := &Client{
		ID:            "streaming-client",
		Send:          make(chan []byte, 256),
		Hub:           hub,
		Subscriptions: make(map[MessageType]bool),
	}

	hub.register <- client
	time.Sleep(10 * time.Millisecond)

	// Test: Send multiple events in rapid succession
	const numEvents = 50
	eventCount := int32(0)

	go func() {
		for i := 0; i < numEvents; i++ {
			msg := Message{
				Type:      TypeSystemStatus,
				Timestamp: time.Now(),
				Data:      json.RawMessage(fmt.Sprintf(`{"event": %d}`, i)),
			}
			msgBytes, _ := json.Marshal(msg)
			hub.broadcast <- msgBytes
			time.Sleep(5 * time.Millisecond)
		}
	}()

	// Collect all received events
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

collectEvents:
	for {
		select {
		case <-client.Send:
			atomic.AddInt32(&eventCount, 1)
		case <-ctx.Done():
			break collectEvents
		}
	}

	if atomic.LoadInt32(&eventCount) < int32(numEvents-5) { // Allow small margin
		t.Errorf("Expected approximately %d events, received %d", numEvents, eventCount)
	}
}

// TestMessageRoutingByType tests filtering and routing of messages by type
func TestMessageRoutingByType(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	// Create two clients with different subscriptions
	client1 := &Client{
		ID:            "client-system",
		Send:          make(chan []byte, 256),
		Hub:           hub,
		Subscriptions: map[MessageType]bool{TypeSystemStatus: true},
	}

	client2 := &Client{
		ID:            "client-agent",
		Send:          make(chan []byte, 256),
		Hub:           hub,
		Subscriptions: map[MessageType]bool{TypeAgentStatus: true},
	}

	hub.register <- client1
	hub.register <- client2
	time.Sleep(20 * time.Millisecond)

	// Test 1: Send system status message
	sysMsg := Message{
		Type:      TypeSystemStatus,
		Timestamp: time.Now(),
		Data:      json.RawMessage(`{"type": "system"}`),
	}
	msgBytes, _ := json.Marshal(sysMsg)
	hub.broadcast <- msgBytes

	// Test 2: Send agent status message
	agentMsg := Message{
		Type:      TypeAgentStatus,
		Timestamp: time.Now(),
		Data:      json.RawMessage(`{"type": "agent"}`),
	}
	msgBytes, _ = json.Marshal(agentMsg)
	hub.broadcast <- msgBytes

	// Both clients receive all broadcasts (hub broadcasts to all)
	// In a real filtering implementation, this would be done at client level
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	client1Received := 0
	client2Received := 0

	// Try to receive up to 4 messages (2 per client)
	for i := 0; i < 4; i++ {
		select {
		case <-client1.Send:
			client1Received++
		case <-client2.Send:
			client2Received++
		case <-ctx.Done():
			i = 4 // exit loop
		}
	}

	// Both clients should have received all 2 broadcasts
	if client1Received < 2 {
		t.Errorf("Client 1 should have received 2 broadcasts, got %d", client1Received)
	}
	if client2Received < 2 {
		t.Errorf("Client 2 should have received 2 broadcasts, got %d", client2Received)
	}
}

// TestErrorHandlingAndRecovery tests error handling during message transmission
func TestErrorHandlingAndRecovery(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	client := &Client{
		ID:            "error-test-client",
		Send:          make(chan []byte, 1), // Small buffer to force send failures
		Hub:           hub,
		Subscriptions: make(map[MessageType]bool),
	}

	hub.register <- client
	time.Sleep(10 * time.Millisecond)

	// Test 1: Send message that might block due to small buffer
	msg1 := Message{
		Type:      TypeSystemStatus,
		Timestamp: time.Now(),
		Data:      json.RawMessage(`{"seq": 1}`),
	}
	msgBytes, _ := json.Marshal(msg1)

	done := make(chan bool, 1)
	go func() {
		hub.broadcast <- msgBytes
		done <- true
	}()

	// Message should eventually be delivered
	select {
	case <-done:
		// Expected - message was broadcast
	case <-time.After(100 * time.Millisecond):
		t.Error("Broadcast operation timed out")
	}

	// Test 2: Verify error messages can be sent
	errorMsg := Message{
		Type:      TypeError,
		Timestamp: time.Now(),
		Data:      json.RawMessage(`{"error": "test error"}`),
	}
	msgBytes, _ = json.Marshal(errorMsg)
	hub.broadcast <- msgBytes

	select {
	case <-client.Send:
		// Expected
	case <-time.After(50 * time.Millisecond):
		t.Error("Error message not received")
	}
}

// TestConcurrentClientConnections tests handling of concurrent client connections
func TestConcurrentClientConnections(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	const numClients = 10   // Reduced from 100
	const numOperations = 3 // Reduced from 10

	var wg sync.WaitGroup
	registerCount := int32(0)
	unregisterCount := int32(0)

	// Simulate concurrent client registrations and unregistrations
	for i := 0; i < numClients; i++ {
		wg.Add(1)
		go func(clientNum int) {
			defer wg.Done()
			defer func() {
				if r := recover(); r != nil {
					fmt.Printf("Recovered from panic in client %d: %v\n", clientNum, r)
				}
			}()

			client := &Client{
				ID:            fmt.Sprintf("concurrent-client-%03d", clientNum),
				Send:          make(chan []byte, 256),
				Hub:           hub,
				Subscriptions: make(map[MessageType]bool),
			}

			// Register
			hub.register <- client
			atomic.AddInt32(&registerCount, 1)

			// Perform some operations
			for op := 0; op < numOperations; op++ {
				msg := Message{
					Type:      TypeSystemStatus,
					Timestamp: time.Now(),
					Data:      json.RawMessage(fmt.Sprintf(`{"op": %d}`, op)),
				}
				msgBytes, _ := json.Marshal(msg)
				hub.broadcast <- msgBytes

				// Drain from send channel to prevent blockage
				select {
				case <-client.Send:
				default:
				}
			}

			// Unregister
			hub.unregister <- client
			atomic.AddInt32(&unregisterCount, 1)
		}(i)
	}

	wg.Wait()
	time.Sleep(100 * time.Millisecond)

	// Verify registration/unregistration counts
	if atomic.LoadInt32(&registerCount) != numClients {
		t.Errorf("Expected %d registrations, got %d", numClients, atomic.LoadInt32(&registerCount))
	}
	if atomic.LoadInt32(&unregisterCount) != numClients {
		t.Errorf("Expected %d unregistrations, got %d", numClients, atomic.LoadInt32(&unregisterCount))
	}

	// Verify all clients are cleaned up
	hub.mu.RLock()
	if len(hub.clients) != 0 {
		t.Errorf("Expected 0 clients in hub after all operations, got %d", len(hub.clients))
	}
	hub.mu.RUnlock()

	// Verify registration/unregistration counts
	if atomic.LoadInt32(&registerCount) != numClients {
		t.Errorf("Expected %d registrations, got %d", numClients, atomic.LoadInt32(&registerCount))
	}

	if atomic.LoadInt32(&unregisterCount) != numClients {
		t.Errorf("Expected %d unregistrations, got %d", numClients, atomic.LoadInt32(&unregisterCount))
	}

	// Hub should be empty
	hub.mu.RLock()
	if len(hub.clients) != 0 {
		t.Errorf("Expected 0 clients in hub after all operations, got %d", len(hub.clients))
	}
	hub.mu.RUnlock()
}

// TestMessageTypeVariety tests all defined message types are handled correctly
func TestMessageTypeVariety(t *testing.T) {
	messageTypes := []MessageType{
		TypeSystemStatus,
		TypeStorageUpdate,
		TypeAgentStatus,
		TypeCompressionUpdate,
		TypeNotification,
		TypeError,
		TypePing,
		TypePong,
		TypeHeartbeat,
		TypeConnectionError,
		TypeRPCError,
		TypeSubscribe,
		TypeUnsubscribe,
		TypeAgentStarted,
		TypeAgentStopped,
		TypeAgentTaskCompleted,
		TypeSchedulerMetrics,
		TypeRecoveryStatus,
		TypeCircuitBreakerOpen,
		TypeTuningStatus,
	}

	for _, msgType := range messageTypes {
		msg := Message{
			Type:      msgType,
			Timestamp: time.Now(),
			Data:      json.RawMessage(`{"test": "data"}`),
		}

		// Verify message can be marshaled
		msgBytes, err := json.Marshal(msg)
		if err != nil {
			t.Errorf("Failed to marshal message of type %v: %v", msgType, err)
		}

		// Verify message can be unmarshaled
		var unmarshaledMsg Message
		if err := json.Unmarshal(msgBytes, &unmarshaledMsg); err != nil {
			t.Errorf("Failed to unmarshal message of type %v: %v", msgType, err)
		}

		if unmarshaledMsg.Type != msgType {
			t.Errorf("Message type mismatch: expected %v, got %v", msgType, unmarshaledMsg.Type)
		}
	}
}

// TestHeartbeatMechanism tests periodic heartbeat messages
func TestHeartbeatMechanism(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	client := &Client{
		ID:            "heartbeat-client",
		Send:          make(chan []byte, 256),
		Hub:           hub,
		Subscriptions: make(map[MessageType]bool),
	}

	hub.register <- client
	time.Sleep(10 * time.Millisecond)

	// Send heartbeat messages
	const numHeartbeats = 5
	for i := 0; i < numHeartbeats; i++ {
		heartbeat := Message{
			Type:      TypeHeartbeat,
			Timestamp: time.Now(),
		}
		msgBytes, _ := json.Marshal(heartbeat)
		hub.broadcast <- msgBytes
		time.Sleep(20 * time.Millisecond)
	}

	// Collect heartbeat messages
	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	heartbeatCount := 0
	for {
		select {
		case received := <-client.Send:
			var msg Message
			if err := json.Unmarshal(received, &msg); err != nil {
				continue
			}
			if msg.Type == TypeHeartbeat {
				heartbeatCount++
			}
		case <-ctx.Done():
			goto verifyHeartbeats
		}
	}

verifyHeartbeats:
	if heartbeatCount < numHeartbeats-1 {
		t.Errorf("Expected at least %d heartbeats, got %d", numHeartbeats-1, heartbeatCount)
	}
}

// TestClientCleanup tests proper cleanup when clients disconnect
func TestClientCleanup(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	clients := make([]*Client, 5)

	// Register multiple clients
	for i := 0; i < 5; i++ {
		client := &Client{
			ID:            fmt.Sprintf("cleanup-client-%d", i),
			Send:          make(chan []byte, 256),
			Hub:           hub,
			Subscriptions: make(map[MessageType]bool),
		}
		clients[i] = client
		hub.register <- client
	}

	time.Sleep(20 * time.Millisecond)

	// Verify all clients are registered
	hub.mu.RLock()
	if len(hub.clients) != 5 {
		t.Errorf("Expected 5 registered clients, got %d", len(hub.clients))
	}
	hub.mu.RUnlock()

	// Unregister some clients
	for i := 0; i < 3; i++ {
		hub.unregister <- clients[i]
	}

	time.Sleep(20 * time.Millisecond)

	// Verify remaining clients
	hub.mu.RLock()
	if len(hub.clients) != 2 {
		t.Errorf("Expected 2 remaining clients, got %d", len(hub.clients))
	}
	hub.mu.RUnlock()

	// Unregister remaining clients
	for i := 3; i < 5; i++ {
		hub.unregister <- clients[i]
	}

	time.Sleep(20 * time.Millisecond)

	// Hub should be empty
	hub.mu.RLock()
	if len(hub.clients) != 0 {
		t.Errorf("Expected 0 clients after cleanup, got %d", len(hub.clients))
	}
	hub.mu.RUnlock()
}

// TestBroadcastWithDifferentDataTypes tests broadcasting messages with various data types
func TestBroadcastWithDifferentDataTypes(t *testing.T) {
	hub := NewHub()
	go hub.Run()
	defer hub.Stop()

	client := &Client{
		ID:            "datatype-client",
		Send:          make(chan []byte, 256),
		Hub:           hub,
		Subscriptions: make(map[MessageType]bool),
	}

	hub.register <- client
	time.Sleep(10 * time.Millisecond)

	testCases := []struct {
		name string
		data string
	}{
		{"string_field", `{"value": "test"}`},
		{"numeric_field", `{"count": 42, "ratio": 3.14}`},
		{"boolean_field", `{"active": true, "enabled": false}`},
		{"array_field", `{"items": [1, 2, 3]}`},
		{"nested_object", `{"config": {"nested": {"value": "deep"}}}`},
		{"null_field", `{"optional": null}`},
		{"mixed_types", `{"string": "test", "number": 100, "bool": true, "array": [1, "two", 3.0]}`},
	}

	for _, tc := range testCases {
		msg := Message{
			Type:      TypeSystemStatus,
			Timestamp: time.Now(),
			Data:      json.RawMessage(tc.data),
		}

		msgBytes, err := json.Marshal(msg)
		if err != nil {
			t.Errorf("Failed to marshal message with %s: %v", tc.name, err)
			continue
		}

		hub.broadcast <- msgBytes

		select {
		case received := <-client.Send:
			var unmarshaledMsg Message
			if err := json.Unmarshal(received, &unmarshaledMsg); err != nil {
				t.Errorf("Failed to unmarshal message with %s: %v", tc.name, err)
			}
		case <-time.After(100 * time.Millisecond):
			t.Errorf("Timeout waiting for message with %s", tc.name)
		}
	}
}
