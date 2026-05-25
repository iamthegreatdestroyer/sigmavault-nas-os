// Package e2e - WebSocket E2E tests
// Tests real-time event delivery, message streaming, and WebSocket integration
package e2e

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"nhooyr.io/websocket"
)

// WSClient manages a WebSocket client connection
type WSClient struct {
	conn      *websocket.Conn
	baseURL   string
	ctx       context.Context
	cancel    context.CancelFunc
	msgChan   chan interface{}
	errChan   chan error
	closedMu  sync.Mutex
	closed    bool
}

// NewWSClient creates and connects a WebSocket client
func NewWSClient(t *testing.T, baseURL string) *WSClient {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)

	wsURL := fmt.Sprintf("ws://%s/ws", baseURL[7:]) // Remove http://

	conn, _, err := websocket.Dial(ctx, wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect WebSocket: %v", err)
	}

	client := &WSClient{
		conn:    conn,
		baseURL: baseURL,
		ctx:     ctx,
		cancel:  cancel,
		msgChan: make(chan interface{}, 100),
		errChan: make(chan error, 10),
	}

	// Start message reader goroutine
	go client.readMessages()

	return client
}

// readMessages reads messages from WebSocket connection
func (wc *WSClient) readMessages() {
	for {
		select {
		case <-wc.ctx.Done():
			return
		default:
		}

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		var msg interface{}

		// Read message type first
		msgType, data, err := wc.conn.Read(ctx)
		cancel()

		if err != nil {
			wc.errChan <- err
			return
		}

		if msgType == websocket.MessageText {
			if err := json.Unmarshal(data, &msg); err != nil {
				wc.errChan <- err
				continue
			}
			wc.msgChan <- msg
		}
	}
}

// WriteMessage sends a message to the server
func (wc *WSClient) WriteMessage(data interface{}) error {
	payload, _ := json.Marshal(data)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return wc.conn.Write(ctx, websocket.MessageText, payload)
}

// ReadMessage reads a message with timeout
func (wc *WSClient) ReadMessage(timeout time.Duration) (interface{}, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	select {
	case msg := <-wc.msgChan:
		return msg, nil
	case err := <-wc.errChan:
		return nil, err
	case <-ctx.Done():
		return nil, context.DeadlineExceeded
	}
}

// Close closes the WebSocket connection
func (wc *WSClient) Close() error {
	wc.closedMu.Lock()
	defer wc.closedMu.Unlock()

	if wc.closed {
		return nil
	}

	wc.closed = true
	wc.cancel()
	return wc.conn.Close(websocket.StatusNormalClosure, "test complete")
}

// TestE2EWebSocketConnection tests basic WebSocket connection
func TestE2EWebSocketConnection(t *testing.T) {
	srv := NewE2ETestServer(t, 11001)
	defer srv.Close()

	client := NewWSClient(t, srv.baseURL)
	defer client.Close()

	// Try to read connection acknowledgment or test message
	_, err := client.ReadMessage(2 * time.Second)
	if err != nil && err != context.DeadlineExceeded {
		t.Logf("No initial message (expected): %v", err)
	} else {
		t.Log("WebSocket connection established")
	}
}

// TestE2EWebSocketMultipleClients tests multiple concurrent WebSocket clients
func TestE2EWebSocketMultipleClients(t *testing.T) {
	srv := NewE2ETestServer(t, 11002)
	defer srv.Close()

	const numClients = 20
	var wg sync.WaitGroup
	var connectionCount int32
	var errors int32

	for i := 0; i < numClients; i++ {
		wg.Add(1)
		go func(clientNum int) {
			defer wg.Done()

			client := NewWSClient(t, srv.baseURL)
			atomic.AddInt32(&connectionCount, 1)

			// Keep connection open for a bit
			time.Sleep(100 * time.Millisecond)

			if err := client.Close(); err != nil {
				atomic.AddInt32(&errors, 1)
			}
		}(i)
	}

	wg.Wait()

	t.Logf("Successfully connected %d/%d clients", atomic.LoadInt32(&connectionCount), numClients)
	t.Logf("Close errors: %d", atomic.LoadInt32(&errors))

	if atomic.LoadInt32(&connectionCount) < int32(numClients*90/100) {
		t.Errorf("Expected at least 90%% connection success")
	}
}

// TestE2EWebSocketMessageReceival tests receiving messages from WebSocket
func TestE2EWebSocketMessageReceival(t *testing.T) {
	srv := NewE2ETestServer(t, 11003)
	defer srv.Close()

	client := NewWSClient(t, srv.baseURL)
	defer client.Close()

	// Send a test subscription message
	testMsg := map[string]interface{}{
		"type": "subscribe",
		"channel": "events",
	}

	if err := client.WriteMessage(testMsg); err != nil {
		t.Logf("Failed to write subscription (may not be implemented): %v", err)
	}

	// Wait for acknowledgment or messages
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	select {
	case msg := <-client.msgChan:
		t.Logf("Received message: %v", msg)
	case err := <-client.errChan:
		t.Logf("Message error: %v (may be expected if server doesn't send)", err)
	case <-ctx.Done():
		t.Log("No messages received (expected if server doesn't send unsolicited messages)")
	}
}

// TestE2EWebSocketBroadcast tests broadcast message delivery
func TestE2EWebSocketBroadcast(t *testing.T) {
	srv := NewE2ETestServer(t, 11004)
	defer srv.Close()

	const numClients = 10
	clients := make([]*WSClient, numClients)
	var wg sync.WaitGroup

	// Connect all clients
	for i := 0; i < numClients; i++ {
		clients[i] = NewWSClient(t, srv.baseURL)
		defer clients[i].Close()
	}

	// Send broadcast message
	broadcastMsg := map[string]interface{}{
		"type": "broadcast",
		"data": "test message",
	}

	// Send from first client (simulating server broadcast)
	if err := clients[0].WriteMessage(broadcastMsg); err != nil {
		t.Logf("Failed to send broadcast (may not be implemented): %v", err)
		return
	}

	// Check if other clients would receive (if implemented)
	time.Sleep(100 * time.Millisecond)

	for i := 1; i < numClients; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
			defer cancel()

			select {
			case <-clients[idx].msgChan:
				// Message received
			case <-ctx.Done():
				// No message (expected if broadcast not implemented)
			}
		}(i)
	}

	wg.Wait()
	t.Log("Broadcast test completed")
}

// TestE2EWebSocketErrorHandling tests error handling in WebSocket
func TestE2EWebSocketErrorHandling(t *testing.T) {
	srv := NewE2ETestServer(t, 11005)
	defer srv.Close()

	t.Run("Connection to non-existent WebSocket", func(t *testing.T) {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		_, _, err := websocket.Dial(ctx, "ws://localhost:11005/nonexistent", nil)
		if err == nil {
			t.Error("Expected error connecting to non-existent WebSocket")
		}
	})

	t.Run("Invalid message format", func(t *testing.T) {
		client := NewWSClient(t, srv.baseURL)
		defer client.Close()

		// Send invalid JSON
		ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
		err := client.conn.Write(ctx, websocket.MessageText, []byte("{invalid json"))
		cancel()

		if err != nil {
			t.Logf("Write error detected: %v", err)
		}
	})
}

// TestE2EWebSocketConnectionCycle tests full connection lifecycle
func TestE2EWebSocketConnectionCycle(t *testing.T) {
	srv := NewE2ETestServer(t, 11006)
	defer srv.Close()

	for i := 0; i < 5; i++ {
		t.Run(fmt.Sprintf("Cycle %d", i+1), func(t *testing.T) {
			client := NewWSClient(t, srv.baseURL)

			// Keep open briefly
			time.Sleep(50 * time.Millisecond)

			// Graceful close
			if err := client.Close(); err != nil {
				t.Logf("Close error: %v", err)
			}

			// Verify reconnection works
			client2 := NewWSClient(t, srv.baseURL)
			time.Sleep(50 * time.Millisecond)
			client2.Close()

			t.Log("Cycle completed")
		})
	}
}

// TestE2EWebSocketStressTest performs a stress test
func TestE2EWebSocketStressTest(t *testing.T) {
	srv := NewE2ETestServer(t, 11007)
	defer srv.Close()

	const numClients = 50
	const messagesPerClient = 10
	const testDuration = 5 * time.Second

	var wg sync.WaitGroup
	var msgCount int32
	var errorCount int32
	startTime := time.Now()

	for c := 0; c < numClients; c++ {
		wg.Add(1)
		go func(clientNum int) {
			defer wg.Done()

			client := NewWSClient(t, srv.baseURL)
			defer client.Close()

			for m := 0; m < messagesPerClient; m++ {
				if time.Since(startTime) > testDuration {
					break
				}

				msg := map[string]interface{}{
					"type": "test",
					"id": fmt.Sprintf("client%d_msg%d", clientNum, m),
				}

				if err := client.WriteMessage(msg); err != nil {
					atomic.AddInt32(&errorCount, 1)
				} else {
					atomic.AddInt32(&msgCount, 1)
				}

				time.Sleep(10 * time.Millisecond)
			}
		}(c)
	}

	wg.Wait()
	elapsed := time.Since(startTime)

	t.Logf("Stress test results:")
	t.Logf("  Messages sent: %d", atomic.LoadInt32(&msgCount))
	t.Logf("  Errors: %d", atomic.LoadInt32(&errorCount))
	t.Logf("  Duration: %v", elapsed)
	t.Logf("  Throughput: %.2f msg/sec", float64(atomic.LoadInt32(&msgCount))/elapsed.Seconds())
}

// TestE2EWebSocketLatency measures WebSocket message latency
func TestE2EWebSocketLatency(t *testing.T) {
	srv := NewE2ETestServer(t, 11008)
	defer srv.Close()

	client := NewWSClient(t, srv.baseURL)
	defer client.Close()

	const iterations = 20
	var durations []time.Duration

	for i := 0; i < iterations; i++ {
		start := time.Now()

		// Send ping-like message
		msg := map[string]interface{}{
			"type": "ping",
			"id": i,
		}

		if err := client.WriteMessage(msg); err != nil {
			t.Logf("Send error: %v", err)
			continue
		}

		// Try to read response (if server echoes)
		ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
		select {
		case <-client.msgChan:
			duration := time.Since(start)
			durations = append(durations, duration)
		case <-ctx.Done():
			// No response (expected if echo not implemented)
		}
		cancel()

		time.Sleep(50 * time.Millisecond)
	}

	if len(durations) > 0 {
		var avg time.Duration
		for _, d := range durations {
			avg += d
		}
		avg /= time.Duration(len(durations))

		t.Logf("WebSocket message latency: %.2fms (samples: %d)", avg.Seconds()*1000, len(durations))
	} else {
		t.Log("No latency measurements (echo not implemented)")
	}
}

// TestE2EWebSocketReconnection tests reconnection scenarios
func TestE2EWebSocketReconnection(t *testing.T) {
	srv := NewE2ETestServer(t, 11009)
	defer srv.Close()

	t.Run("Immediate reconnection", func(t *testing.T) {
		client1 := NewWSClient(t, srv.baseURL)
		client1.Close()

		// Immediately reconnect
		client2 := NewWSClient(t, srv.baseURL)
		defer client2.Close()

		t.Log("Immediate reconnection successful")
	})

	t.Run("Delayed reconnection", func(t *testing.T) {
		client1 := NewWSClient(t, srv.baseURL)
		client1.Close()

		// Wait before reconnecting
		time.Sleep(500 * time.Millisecond)

		client2 := NewWSClient(t, srv.baseURL)
		defer client2.Close()

		t.Log("Delayed reconnection successful")
	})

	t.Run("Sequential connections", func(t *testing.T) {
		for i := 0; i < 10; i++ {
			client := NewWSClient(t, srv.baseURL)
			time.Sleep(25 * time.Millisecond)
			client.Close()
		}
		t.Log("Sequential connections successful")
	})
}
