// Package middleware provides HTTP middleware for the API.
package middleware

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/limiter"
)

// RateLimiter returns a rate limiting middleware.
func RateLimiter() fiber.Handler {
	return limiter.New(limiter.Config{
		Max:        100,             // Maximum number of requests
		Expiration: 1 * time.Minute, // Per minute
		KeyGenerator: func(c *fiber.Ctx) string {
			return c.IP()
		},
		LimitReached: func(c *fiber.Ctx) error {
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error": "Too many requests",
				"code":  fiber.StatusTooManyRequests,
			})
		},
	})
}

// StrictRateLimiter returns a stricter rate limiter for sensitive endpoints.
func StrictRateLimiter() fiber.Handler {
	return limiter.New(limiter.Config{
		Max:        10,              // Maximum 10 requests
		Expiration: 1 * time.Minute, // Per minute
		KeyGenerator: func(c *fiber.Ctx) string {
			return c.IP()
		},
		LimitReached: func(c *fiber.Ctx) error {
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error": "Too many requests, please try again later",
				"code":  fiber.StatusTooManyRequests,
			})
		},
	})
}

// APIKeyAuth validates API key authentication.
func APIKeyAuth(validKeys []string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		apiKey := c.Get("X-API-Key")
		if apiKey == "" {
			apiKey = c.Query("api_key")
		}

		if apiKey == "" {
			return fiber.NewError(fiber.StatusUnauthorized, "API key required")
		}

		// Check if the key is valid
		for _, key := range validKeys {
			if apiKey == key {
				return c.Next()
			}
		}

		return fiber.NewError(fiber.StatusUnauthorized, "Invalid API key")
	}
}

// SecurityHeaders adds security-related headers to responses.
func SecurityHeaders() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Security headers
		c.Set("X-Content-Type-Options", "nosniff")
		c.Set("X-Frame-Options", "DENY")
		c.Set("X-XSS-Protection", "1; mode=block")
		c.Set("Referrer-Policy", "strict-origin-when-cross-origin")
		c.Set("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

		// Content Security Policy for API
		c.Set("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")

		return c.Next()
	}
}
