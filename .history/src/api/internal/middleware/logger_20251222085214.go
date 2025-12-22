// Package middleware provides HTTP middleware for the API.
package middleware

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/rs/zerolog/log"
)

// Logger returns a middleware that logs HTTP requests.
func Logger() fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()

		// Process request
		err := c.Next()

		// Calculate latency
		latency := time.Since(start)

		// Get status code
		status := c.Response().StatusCode()

		// Log the request
		logger := log.With().
			Str("method", c.Method()).
			Str("path", c.Path()).
			Int("status", status).
			Dur("latency", latency).
			Str("ip", c.IP()).
			Str("user_agent", c.Get("User-Agent")).
			Logger()

		if err != nil {
			logger.Error().Err(err).Msg("Request failed")
		} else if status >= 500 {
			logger.Error().Msg("Server error")
		} else if status >= 400 {
			logger.Warn().Msg("Client error")
		} else {
			logger.Info().Msg("Request completed")
		}

		return err
	}
}

// RequestID adds a unique request ID to each request.
func RequestID() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Check if request ID already exists
		requestID := c.Get("X-Request-ID")
		if requestID == "" {
			requestID = generateRequestID()
		}

		// Set request ID in response header
		c.Set("X-Request-ID", requestID)
		c.Locals("request_id", requestID)

		return c.Next()
	}
}

// generateRequestID generates a simple request ID.
func generateRequestID() string {
	// Simple timestamp-based ID for now
	return time.Now().Format("20060102150405.000000")
}

// Timing adds server timing headers.
func Timing() fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()

		err := c.Next()

		// Add Server-Timing header
		duration := time.Since(start)
		c.Set("Server-Timing", "total;dur="+duration.String())

		return err
	}
}
