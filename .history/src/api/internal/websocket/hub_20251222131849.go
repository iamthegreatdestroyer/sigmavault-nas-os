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
			for client := range h.clients {
				select {
				case client.Send <- message:
				default:
					close(client.Send)
					delete(h.clients, client)
				}
			}
			h.mu.RUnlock()
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
	client := &Client{
		ID:            generateClientID(),
		Conn:          conn,
		Hub:           h.hub,
		Send:          make(chan []byte, 256),
		Subscriptions: make(map[MessageType]bool),
	}

	// Register client
	h.hub.register <- client

	// Start writer goroutine
	go client.writePump()

	// Read messages (blocking)
	client.readPump()

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
				c.Conn.WriteMessage(websocket.CloseMessage, []byte{})
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

	default:
		log.Debug().Str("type", string(msg.Type)).Str("client_id", c.ID).Msg("Received WebSocket message")
	}
}

// generateClientID generates a unique client ID.
func generateClientID() string {
	return time.Now().Format("20060102150405.000000")
}
