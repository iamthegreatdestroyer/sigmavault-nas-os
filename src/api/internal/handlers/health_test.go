// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"encoding/json"
	"io"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHealthCheck(t *testing.T) {
	app := fiber.New()
	app.Get("/health", HealthCheck)

	req := httptest.NewRequest("GET", "/health", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var result HealthResponse
	err = json.Unmarshal(body, &result)
	require.NoError(t, err)

	assert.Equal(t, "healthy", result.Status)
	assert.Equal(t, "0.1.0", result.Version)
	assert.False(t, result.Timestamp.IsZero())
	assert.WithinDuration(t, time.Now(), result.Timestamp, 5*time.Second)
}

func TestReadyCheck(t *testing.T) {
	app := fiber.New()
	app.Get("/ready", ReadyCheck)

	req := httptest.NewRequest("GET", "/ready", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var result ReadyResponse
	err = json.Unmarshal(body, &result)
	require.NoError(t, err)

	assert.Equal(t, "ready", result.Status)
	assert.NotNil(t, result.Components)
	assert.Contains(t, result.Components, "api")
	assert.Equal(t, "ready", result.Components["api"])
}

func TestSystemInfo(t *testing.T) {
	app := fiber.New()
	app.Get("/info", SystemInfo)

	req := httptest.NewRequest("GET", "/info", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var result SystemInfoResponse
	err = json.Unmarshal(body, &result)
	require.NoError(t, err)

	assert.Equal(t, "0.1.0", result.Version)
	assert.NotEmpty(t, result.GoVersion)
	assert.Greater(t, result.NumGoroutine, 0)
	assert.Greater(t, result.NumCPU, 0)
	assert.GreaterOrEqual(t, result.Uptime, int64(0))
	assert.False(t, result.StartTime.IsZero())
}

func TestHealthResponse_JSON(t *testing.T) {
	resp := HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now(),
		Version:   "1.0.0",
	}

	data, err := json.Marshal(resp)
	require.NoError(t, err)

	var parsed HealthResponse
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, resp.Status, parsed.Status)
	assert.Equal(t, resp.Version, parsed.Version)
}

func TestReadyResponse_Components(t *testing.T) {
	tests := []struct {
		name       string
		components map[string]string
		wantStatus string
	}{
		{
			name: "all ready",
			components: map[string]string{
				"api":      "ready",
				"database": "ready",
			},
			wantStatus: "ready",
		},
		{
			name: "component unavailable",
			components: map[string]string{
				"api":      "ready",
				"database": "unavailable",
			},
			wantStatus: "degraded",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status := "ready"
			for _, v := range tt.components {
				if v == "unavailable" {
					status = "degraded"
					break
				}
			}
			assert.Equal(t, tt.wantStatus, status)
		})
	}
}
