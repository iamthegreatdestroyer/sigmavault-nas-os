// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"runtime"
	"time"

	"github.com/gofiber/fiber/v2"
)

// HealthResponse represents the health check response.
type HealthResponse struct {
	Status    string    `json:"status"`
	Timestamp time.Time `json:"timestamp"`
	Version   string    `json:"version"`
}

// ReadyResponse represents the readiness check response.
type ReadyResponse struct {
	Status     string            `json:"status"`
	Timestamp  time.Time         `json:"timestamp"`
	Components map[string]string `json:"components"`
}

// SystemInfoResponse represents detailed system information.
type SystemInfoResponse struct {
	Version      string    `json:"version"`
	GoVersion    string    `json:"go_version"`
	NumGoroutine int       `json:"num_goroutine"`
	NumCPU       int       `json:"num_cpu"`
	Uptime       int64     `json:"uptime_seconds"`
	StartTime    time.Time `json:"start_time"`
}

var startTime = time.Now()

// HealthCheck performs a basic health check.
func HealthCheck(c *fiber.Ctx) error {
	return c.JSON(HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now(),
		Version:   "0.1.0",
	})
}

// ReadyCheck performs a readiness check including dependencies.
func ReadyCheck(c *fiber.Ctx) error {
	// TODO: Add actual dependency checks (database, RPC engine, etc.)
	components := map[string]string{
		"api":        "ready",
		"rpc_engine": "unknown", // Will check when RPC engine is implemented
		"database":   "unknown", // Will check when database is implemented
	}

	status := "ready"
	for _, v := range components {
		if v == "unavailable" {
			status = "degraded"
			break
		}
	}

	return c.JSON(ReadyResponse{
		Status:     status,
		Timestamp:  time.Now(),
		Components: components,
	})
}

// SystemInfo returns detailed system information.
func SystemInfo(c *fiber.Ctx) error {
	return c.JSON(SystemInfoResponse{
		Version:      "0.1.0",
		GoVersion:    runtime.Version(),
		NumGoroutine: runtime.NumGoroutine(),
		NumCPU:       runtime.NumCPU(),
		Uptime:       int64(time.Since(startTime).Seconds()),
		StartTime:    startTime,
	})
}

// ErrorHandler is a custom error handler for Fiber.
func ErrorHandler(c *fiber.Ctx, err error) error {
	// Default to 500 Internal Server Error
	code := fiber.StatusInternalServerError
	message := "Internal Server Error"

	// Check if it's a Fiber error
	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
		message = e.Message
	}

	return c.Status(code).JSON(fiber.Map{
		"error": message,
		"code":  code,
	})
}
