// Package websocket provides WebSocket support for real-time updates.
package websocket

import (
	"encoding/json"
	"sync"
	"time"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

// MessageType represents the type of WebSocket message.
type MessageType string

const (
	// Message types for real-time updates
	TypeSystemStatus      MessageType = "system.status"
	TypeStorageUpdate     MessageType = "storage.update"
	TypeAgentStatus       MessageType = "agent.status"
	TypeCompressionUpdate MessageType = "compression.update"
	TypeNotification      MessageType = "notification"
	TypeError             MessageType = "error"
	TypePing              MessageType = "ping"
	TypePong              MessageType = "pong"
	TypeHeartbeat         MessageType = "heartbeat"
	TypeConnectionError   MessageType = "connection_error"
	TypeRPCError          MessageType = "rpc_error"
	TypeSubscribe         MessageType = "subscribe"
	TypeUnsubscribe       MessageType = "unsubscribe"

	// Agent lifecycle events (autonomy system)
	TypeAgentStarted       MessageType = "agent.started"
	TypeAgentStopped       MessageType = "agent.stopped"
	TypeAgentRestarted     MessageType = "agent.restarted"
	TypeAgentHealthCheck   MessageType = "agent.health_check"
	TypeAgentTaskAssigned  MessageType = "agent.task_assigned"
	TypeAgentTaskCompleted MessageType = "agent.task_completed"
	TypeAgentTaskFailed    MessageType = "agent.task_failed"

	// Scheduler events
	TypeSchedulerMetrics MessageType = "scheduler.metrics"
	TypeTaskQueued       MessageType = "task.queued"
	TypeTaskDispatched   MessageType = "task.dispatched"

	// Recovery events
	TypeRecoveryStatus       MessageType = "recovery.status"
	TypeCircuitBreakerOpen   MessageType = "circuit_breaker.open"
	TypeCircuitBreakerClosed MessageType = "circuit_breaker.closed"
	TypeAgentRecoveryStarted MessageType = "agent.recovery_started"
	TypeAgentRecoverySuccess MessageType = "agent.recovery_success"
	TypeAgentRecoveryFailed  MessageType = "agent.recovery_failed"
	TypeDeadLetterQueued     MessageType = "dead_letter.queued"

	// Self-tuning events
	TypeTuningStatus MessageType = "tuning.status"
)

// Message represents a WebSocket message.
type Message struct {
	Type      MessageType     `json:"type"`
	Timestamp time.Time       `json:"timestamp"`
	Data      json.RawMessage `json:"data,omitempty"`
}

// Client represents a connected WebSocket client.
type Client struct {
	ID            string
	Conn          *websocket.Conn
	Hub           *Hub
	Send          chan []byte
	mu            sync.Mutex
	Subscriptions map[MessageType]bool
}

// Hub maintains the set of active clients and broadcasts messages.
type Hub struct {
	clients    map[*Client]bool
	register   chan *Client
	unregister chan *Client
	broadcast  chan []byte
	mu         sync.RWMutex
}

// NewHub creates a new WebSocket hub.
func NewHub() *Hub {
	return &Hub{
		clients:    make(map[*Client]bool),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		broadcast:  make(chan []byte),
	}
}

// Run starts the hub's main loop.
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			h.clients[client] = true
			h.mu.Unlock()
			log.Info().Str("client_id", client.ID).Msg("WebSocket client connected")

		case client := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.Send)
			}
			h.mu.Unlock()
			log.Info().Str("client_id", client.ID).Msg("WebSocket client disconnected")

		case message := <-h.broadcast:
			h.mu.RLock()
			deadClients := make([]*Client, 0)
			for client := range h.clients {
				select {
				case client.Send <- message:
				default:
					deadClients = append(deadClients, client)
				}
			}
			h.mu.RUnlock()

			// Handle clients that can't receive (buffer full or closed)
			if len(deadClients) > 0 {
				h.mu.Lock()
				for _, client := range deadClients {
					if _, ok := h.clients[client]; ok {
						delete(h.clients, client)
						close(client.Send)
						log.Warn().Str("client_id", client.ID).Msg("Client connection dropped (buffer full)")

						// Notify remaining clients of the disconnection
						h.mu.Unlock()
						errorMsg := map[string]interface{}{
							"client_id":  client.ID,
							"reason":     "buffer_full",
							"error_code": "CONNECTION_DROP",
						}
						_ = h.Broadcast(TypeConnectionError, errorMsg) // Best effort notification
						h.mu.Lock()
					}
				}
				h.mu.Unlock()
			}
		}
	}
}

// Broadcast sends a message to all connected clients.
func (h *Hub) Broadcast(msgType MessageType, data interface{}) error {
	jsonData, err := json.Marshal(data)
	if err != nil {
		return err
	}

	msg := Message{
		Type:      msgType,
		Timestamp: time.Now(),
		Data:      jsonData,
	}

	encoded, err := json.Marshal(msg)
	if err != nil {
		return err
	}

	h.broadcast <- encoded
	return nil
}

// BroadcastIfSubscribed sends a message to connected clients who are subscribed to the message type.
func (h *Hub) BroadcastIfSubscribed(msgType MessageType, data interface{}) error {
	jsonData, err := json.Marshal(data)
	if err != nil {
		return err
	}

	msg := Message{
		Type:      msgType,
		Timestamp: time.Now(),
		Data:      jsonData,
	}

	encoded, err := json.Marshal(msg)
	if err != nil {
		return err
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	totalClients := len(h.clients)
	subscribedCount := 0
	unsubscribedCount := 0

	log.Debug().Str("msg_type", string(msgType)).Int("total_clients", totalClients).
		Msg("BroadcastIfSubscribed: starting broadcast")

	for client := range h.clients {
		if client.IsSubscribedTo(msgType) {
			select {
			case client.Send <- encoded:
				subscribedCount++
				log.Debug().Str("client_id", client.ID).Str("msg_type", string(msgType)).
					Msg("Event sent to subscribed client")
			default:
				log.Warn().Str("client_id", client.ID).Str("msg_type", string(msgType)).
					Msg("Failed to send message to subscribed client (buffer full)")
			}
		} else {
			unsubscribedCount++
			log.Debug().Str("client_id", client.ID).Str("msg_type", string(msgType)).
				Msg("Client not subscribed to this event type")
		}
	}

	log.Debug().Str("msg_type", string(msgType)).
		Int("sent_to", subscribedCount).
		Int("skipped", unsubscribedCount).
		Int("total_clients", totalClients).
		Msg("BroadcastIfSubscribed: broadcast complete")

	return nil
}

// ClientCount returns the number of connected clients.
func (h *Hub) ClientCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}

// Handler handles WebSocket connections.
type Handler struct {
	hub *Hub
}

// NewHandler creates a new WebSocket handler.
func NewHandler(hub *Hub) *Handler {
	return &Handler{hub: hub}
}

// HandleWebSocket handles WebSocket upgrade and connection.
func (h *Handler) HandleWebSocket(c *fiber.Ctx) error {
	// Check if WebSocket upgrade is requested
	if websocket.IsWebSocketUpgrade(c) {
		return websocket.New(h.handleConnection)(c)
	}
	return fiber.ErrUpgradeRequired
}

// handleConnection handles an individual WebSocket connection.
func (h *Handler) handleConnection(conn *websocket.Conn) {
	// Create default subscriptions for all core event types
	// This ensures clients receive events without needing to explicitly subscribe
	defaultSubscriptions := map[MessageType]bool{
		TypeSystemStatus:      true,
		TypeStorageUpdate:     true,
		TypeAgentStatus:       true,
		TypeCompressionUpdate: true,
		TypeNotification:      true,
		TypeRPCError:          true,
		TypeConnectionError:   true,
		TypeHeartbeat:         true,
	}

	client := &Client{
		ID:            generateClientID(),
		Conn:          conn,
		Hub:           h.hub,
		Send:          make(chan []byte, 256),
		Subscriptions: defaultSubscriptions,
	}

	log.Info().Str("client_id", client.ID).Int("default_subscriptions", len(defaultSubscriptions)).Msg("WebSocket client created with default subscriptions")

	// Register client
	h.hub.register <- client

	// Send welcome message to confirm connection and subscriptions
	welcomeData := map[string]interface{}{
		"client_id":     client.ID,
		"subscriptions": getSubscriptionList(defaultSubscriptions),
		"message":       "Connected to SigmaVault WebSocket. You are subscribed to all core events.",
	}
	welcomeMsg := Message{
		Type:      TypeNotification,
		Timestamp: time.Now(),
	}
	if jsonData, err := json.Marshal(welcomeData); err == nil {
		welcomeMsg.Data = jsonData
		if encoded, err := json.Marshal(welcomeMsg); err == nil {
			select {
			case client.Send <- encoded:
				log.Debug().Str("client_id", client.ID).Msg("Sent welcome message to client")
			default:
				log.Warn().Str("client_id", client.ID).Msg("Failed to send welcome message (buffer full)")
			}
		}
	}

	// Channel to signal when connection is closed
	done := make(chan struct{})

	// Start both reader and writer as concurrent goroutines
	go client.writePump()

	go func() {
		client.readPump()
		log.Info().Str("client_id", client.ID).Msg("WebSocket connection read pump ended")
		done <- struct{}{}
	}()

	// Wait for read pump to finish (indicates connection closed)
	<-done

	// Unregister client when done
	h.hub.unregister <- client
}

// readPump reads messages from the WebSocket connection.
func (c *Client) readPump() {
	defer func() {
		c.Conn.Close()
	}()

	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Error().Err(err).Str("client_id", c.ID).Msg("WebSocket read error")
			}
			break
		}

		// Handle incoming message
		c.handleMessage(message)
	}
}

// writePump writes messages to the WebSocket connection.
func (c *Client) writePump() {
	ticker := time.NewTicker(30 * time.Second)
	defer func() {
		ticker.Stop()
		c.Conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.Send:
			if !ok {
				// Channel closed
				_ = c.Conn.WriteMessage(websocket.CloseMessage, []byte{}) // Best effort close
				return
			}

			c.mu.Lock()
			err := c.Conn.WriteMessage(websocket.TextMessage, message)
			c.mu.Unlock()

			if err != nil {
				log.Error().Err(err).Str("client_id", c.ID).Msg("WebSocket write error")
				return
			}

		case <-ticker.C:
			// Send ping to keep connection alive
			c.mu.Lock()
			err := c.Conn.WriteMessage(websocket.PingMessage, nil)
			c.mu.Unlock()

			if err != nil {
				return
			}
		}
	}
}

// handleMessage processes an incoming WebSocket message.
func (c *Client) handleMessage(data []byte) {
	var msg Message
	if err := json.Unmarshal(data, &msg); err != nil {
		log.Error().Err(err).Str("client_id", c.ID).Msg("Failed to parse WebSocket message")
		return
	}

	switch msg.Type {
	case TypePing:
		// Respond with pong
		pong := Message{Type: TypePong, Timestamp: time.Now()}
		response, _ := json.Marshal(pong)
		c.Send <- response

	case TypeSubscribe:
		// Handle subscription request
		var subscribeMsg struct {
			Types []MessageType `json:"types"`
		}
		if err := json.Unmarshal(msg.Data, &subscribeMsg); err != nil {
			log.Error().Err(err).Str("client_id", c.ID).Msg("Failed to parse subscription message")
			return
		}
		c.SubscribeToEvents(subscribeMsg.Types...)
		log.Debug().Str("client_id", c.ID).Interface("types", subscribeMsg.Types).Msg("Client subscribed to event types")

	case TypeUnsubscribe:
		// Handle unsubscription request
		var unsubscribeMsg struct {
			Types []MessageType `json:"types"`
		}
		if err := json.Unmarshal(msg.Data, &unsubscribeMsg); err != nil {
			log.Error().Err(err).Str("client_id", c.ID).Msg("Failed to parse unsubscription message")
			return
		}
		c.UnsubscribeFromEvents(unsubscribeMsg.Types...)
		log.Debug().Str("client_id", c.ID).Interface("types", unsubscribeMsg.Types).Msg("Client unsubscribed from event types")

	default:
		log.Debug().Str("type", string(msg.Type)).Str("client_id", c.ID).Msg("Received WebSocket message")
	}
}

// generateClientID generates a unique client ID using UUID v4.
func generateClientID() string {
	return uuid.New().String()
}

// getSubscriptionList converts a subscription map to a list of strings for JSON serialization.
func getSubscriptionList(subs map[MessageType]bool) []string {
	result := make([]string, 0, len(subs))
	for msgType, subscribed := range subs {
		if subscribed {
			result = append(result, string(msgType))
		}
	}
	return result
}
