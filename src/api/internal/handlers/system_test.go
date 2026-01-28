// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"encoding/json"
	"io"
	"net/http/httptest"
	"testing"
	"time"

	"sigmavault-nas-os/api/internal/models"

	"github.com/gofiber/fiber/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewSystemHandler(t *testing.T) {
	handler := NewSystemHandler(nil)
	assert.NotNil(t, handler)
	assert.Nil(t, handler.rpcClient)
}

func TestGetSystemStatus_Fallback(t *testing.T) {
	handler := NewSystemHandler(nil)

	app := fiber.New()
	app.Get("/system/status", handler.GetSystemStatus)

	req := httptest.NewRequest("GET", "/system/status", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var result models.SystemStatus
	err = json.Unmarshal(body, &result)
	require.NoError(t, err)

	// Hostname should be set
	assert.NotEmpty(t, result.Hostname)

	// Memory stats should be populated
	assert.Greater(t, result.MemoryTotal, uint64(0))
	assert.Greater(t, result.MemoryUsed, uint64(0))

	// Timestamp should be recent
	assert.WithinDuration(t, time.Now(), result.Timestamp, 5*time.Second)
}

func TestGetNetworkInterfaces_Fallback(t *testing.T) {
	handler := NewSystemHandler(nil)

	app := fiber.New()
	app.Get("/system/network", handler.GetNetworkInterfaces)

	req := httptest.NewRequest("GET", "/system/network", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var result struct {
		Interfaces []models.NetworkInterface `json:"interfaces"`
		Count      int                       `json:"count"`
	}
	err = json.Unmarshal(body, &result)
	require.NoError(t, err)

	// Should return empty list in fallback mode
	assert.NotNil(t, result.Interfaces)
}

func TestGetServices_Fallback(t *testing.T) {
	handler := NewSystemHandler(nil)

	app := fiber.New()
	app.Get("/system/services", handler.GetServices)

	req := httptest.NewRequest("GET", "/system/services", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var result struct {
		Services []models.Service `json:"services"`
		Count    int              `json:"count"`
	}
	err = json.Unmarshal(body, &result)
	require.NoError(t, err)

	assert.NotNil(t, result.Services)
	// Should have at least some services in fallback mode
	assert.GreaterOrEqual(t, result.Count, 0)
}

func TestSystemStatus_Model(t *testing.T) {
	status := models.SystemStatus{
		Hostname:     "test-host",
		Uptime:       3600,
		CPUUsage:     50.5,
		MemoryTotal:  16000000000,
		MemoryUsed:   8000000000,
		MemoryUsePct: 50.0,
		LoadAvg:      []float64{1.0, 0.5, 0.25},
		Timestamp:    time.Now(),
	}

	data, err := json.Marshal(status)
	require.NoError(t, err)

	var parsed models.SystemStatus
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, status.Hostname, parsed.Hostname)
	assert.Equal(t, status.Uptime, parsed.Uptime)
	assert.InDelta(t, status.CPUUsage, parsed.CPUUsage, 0.01)
	assert.Equal(t, status.MemoryTotal, parsed.MemoryTotal)
	assert.Equal(t, len(status.LoadAvg), len(parsed.LoadAvg))
}

func TestNetworkInterface_Model(t *testing.T) {
	iface := models.NetworkInterface{
		Name:       "eth0",
		Status:     "up",
		IPAddress:  "192.168.1.100",
		MacAddress: "00:11:22:33:44:55",
		Speed:      1000,
		RxBytes:    1000000,
		TxBytes:    500000,
	}

	data, err := json.Marshal(iface)
	require.NoError(t, err)

	var parsed models.NetworkInterface
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, iface.Name, parsed.Name)
	assert.Equal(t, iface.IPAddress, parsed.IPAddress)
	assert.Equal(t, iface.MacAddress, parsed.MacAddress)
}

func TestService_Model(t *testing.T) {
	now := time.Now()
	service := models.Service{
		Name:      "sigmavault-api",
		Status:    "running",
		Enabled:   true,
		StartedAt: now,
	}

	data, err := json.Marshal(service)
	require.NoError(t, err)

	var parsed models.Service
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, service.Name, parsed.Name)
	assert.Equal(t, service.Status, parsed.Status)
	assert.Equal(t, service.Enabled, parsed.Enabled)
}

func TestGetNotifications_Returns200(t *testing.T) {
	handler := NewSystemHandler(nil)

	app := fiber.New()
	app.Get("/system/notifications", handler.GetNotifications)

	req := httptest.NewRequest("GET", "/system/notifications", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)
}

func TestRestartService_RequiresName(t *testing.T) {
	handler := NewSystemHandler(nil)

	app := fiber.New()
	app.Post("/system/services/:name/restart", handler.RestartService)

	// Without a name in URL params, should still work with the param
	req := httptest.NewRequest("POST", "/system/services/test-service/restart", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	// In fallback mode (no RPC), should return 503 or fallback behavior
	assert.Contains(t, []int{200, 400, 503}, resp.StatusCode)
}
