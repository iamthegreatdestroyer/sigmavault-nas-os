package websocket

import (
	"github.com/gofiber/fiber/v2"
)

// Client-specific utilities can go here if needed
// Main WebSocket handler is implemented in hub.go

// GetWebSocketHandler returns the WebSocket handler from the handler instance.
func (h *Handler) GetWebSocketHandler() fiber.Handler {
	return h.HandleWebSocket
}
