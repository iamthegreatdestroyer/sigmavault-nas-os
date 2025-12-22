// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"os"
	"runtime"
	"time"

	"sigmavault-nas-os/api/internal/models"
	"sigmavault-nas-os/api/internal/rpc"

	"github.com/gofiber/fiber/v2"
	"github.com/rs/zerolog/log"
)

// SystemHandler handles system-related requests.
type SystemHandler struct {
	rpcClient *rpc.Client
}

// NewSystemHandler creates a new SystemHandler instance.
func NewSystemHandler(client *rpc.Client) *SystemHandler {
	return &SystemHandler{
		rpcClient: client,
	}
}

// GetSystemStatus returns the current system status.
func (h *SystemHandler) GetSystemStatus(c *fiber.Ctx) error {
	// Try to get real metrics from RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		status, err := h.rpcClient.GetSystemStatus(c.Context(), &rpc.GetSystemStatusParams{})
		if err == nil {
			// Map RPC response to API model
			return c.JSON(models.SystemStatus{
				Hostname:     status.Hostname,
				Uptime:       int64(status.Uptime.Seconds()),
				CPUUsage:     status.CPUUsage,
				MemoryTotal:  status.MemoryUsage.Total,
				MemoryUsed:   status.MemoryUsage.Used,
				MemoryUsePct: status.MemoryUsage.UsedPercent,
				LoadAvg:      []float64{status.LoadAverage.Load1, status.LoadAverage.Load5, status.LoadAverage.Load15},
				Timestamp:    time.Now(),
			})
		}
		log.Warn().Err(err).Msg("Failed to get system status from RPC, falling back to local metrics")
	}

	// Fallback to local metrics if RPC unavailable
	hostname, _ := os.Hostname()

	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	status := models.SystemStatus{
		Hostname:     hostname,
		Uptime:       int64(time.Since(startTime).Seconds()),
		CPUUsage:     0.0,
		MemoryTotal:  m.Sys,
		MemoryUsed:   m.Alloc,
		MemoryUsePct: float64(m.Alloc) / float64(m.Sys) * 100,
		LoadAvg:      []float64{0.0, 0.0, 0.0},
		Timestamp:    time.Now(),
	}

	return c.JSON(status)
}

// GetNetworkInterfaces returns all network interfaces.
func (h *SystemHandler) GetNetworkInterfaces(c *fiber.Ctx) error {
	// Try to get real data from RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		interfaces, err := h.rpcClient.GetNetworkInterfaces(c.Context())
		if err == nil {
			// Map RPC response to API models
			result := make([]models.NetworkInterface, len(interfaces))
			for i, iface := range interfaces {
				result[i] = models.NetworkInterface{
					Name:        iface.Name,
					Status:      iface.Status,
					IPAddress:   iface.IPAddress,
					MacAddress:  iface.MACAddress,
					Speed:       iface.SpeedMbps,
					RxBytes:     iface.RxBytes,
					TxBytes:     iface.TxBytes,
					RxBytesRate: iface.RxBytesRate,
					TxBytesRate: iface.TxBytesRate,
				}
			}
			return c.JSON(fiber.Map{
				"interfaces": result,
				"count":      len(result),
			})
		}
		log.Warn().Err(err).Msg("Failed to get network interfaces from RPC, returning empty list")
	}

	// Fallback to empty list
	interfaces := []models.NetworkInterface{}

	return c.JSON(fiber.Map{
		"interfaces": interfaces,
		"count":      len(interfaces),
	})
}

// GetServices returns the status of system services.
func (h *SystemHandler) GetServices(c *fiber.Ctx) error {
	// Try to get real data from RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		services, err := h.rpcClient.ListServices(c.Context())
		if err == nil {
			// Map RPC response to API models
			result := make([]models.Service, len(services))
			for i, svc := range services {
				result[i] = models.Service{
					Name:      svc.Name,
					Status:    svc.Status,
					Enabled:   svc.Enabled,
					StartedAt: svc.StartedAt,
				}
			}
			return c.JSON(fiber.Map{
				"services": result,
				"count":    len(result),
			})
		}
		log.Warn().Err(err).Msg("Failed to get services from RPC, returning fallback list")
	}

	// Fallback to static list
	services := []models.Service{
		{
			Name:      "sigmavault-api",
			Status:    "running",
			Enabled:   true,
			StartedAt: startTime,
		},
		{
			Name:    "sigmavault-rpc",
			Status:  "unknown",
			Enabled: true,
		},
		{
			Name:    "smbd",
			Status:  "unknown",
			Enabled: true,
		},
		{
			Name:    "nfs-server",
			Status:  "unknown",
			Enabled: true,
		},
	}

	return c.JSON(fiber.Map{
		"services": services,
		"count":    len(services),
	})
}

// RestartServiceRequest represents a request to restart a service.
type RestartServiceRequest struct {
	ServiceName string `json:"service_name" validate:"required"`
}

// RestartService restarts a system service.
func (h *SystemHandler) RestartService(c *fiber.Ctx) error {
	serviceName := c.Params("name")
	if serviceName == "" {
		serviceName = c.Params("id")
	}

	if serviceName == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Service name is required",
		})
	}

	// Call RPC engine to restart service
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		err := h.rpcClient.RestartService(c.Context(), serviceName)
		if err != nil {
			log.Error().Err(err).Str("service", serviceName).Msg("Failed to restart service via RPC")
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":        "Failed to restart service",
				"service_name": serviceName,
				"details":      err.Error(),
			})
		}

		return c.JSON(fiber.Map{
			"message":      "Service restarted successfully",
			"service_name": serviceName,
		})
	}

	// RPC not available
	return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
		"error":        "RPC engine not available",
		"service_name": serviceName,
	})
}

// GetNotifications returns system notifications.
func (h *SystemHandler) GetNotifications(c *fiber.Ctx) error {
	// Notifications are managed locally for now
	// TODO: Add notification storage/retrieval
	notifications := []models.Notification{}

	return c.JSON(fiber.Map{
		"notifications": notifications,
		"count":         len(notifications),
		"unread_count":  0,
	})
}

// MarkNotificationRead marks a notification as read.
func (h *SystemHandler) MarkNotificationRead(c *fiber.Ctx) error {
	notificationID := c.Params("id")

	// TODO: Implement notification update in storage
	return c.JSON(fiber.Map{
		"message":         "Notification marked as read",
		"notification_id": notificationID,
	})
}

// Reboot initiates a system reboot.
func (h *SystemHandler) Reboot(c *fiber.Ctx) error {
	// Parse optional delay parameter
	type RebootRequest struct {
		DelaySeconds int `json:"delay_seconds"`
	}
	var req RebootRequest
	if err := c.BodyParser(&req); err != nil {
		req.DelaySeconds = 60 // Default 60 second delay
	}
	if req.DelaySeconds == 0 {
		req.DelaySeconds = 60
	}

	// Call RPC engine to initiate reboot
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		err := h.rpcClient.Reboot(c.Context(), req.DelaySeconds)
		if err != nil {
			log.Error().Err(err).Msg("Failed to initiate reboot via RPC")
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "Failed to initiate reboot",
				"details": err.Error(),
			})
		}

		log.Warn().Int("delay", req.DelaySeconds).Msg("System reboot initiated")
		return c.JSON(fiber.Map{
			"message":       "System reboot initiated",
			"delay_seconds": req.DelaySeconds,
			"warning":       "System will restart soon",
		})
	}

	return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
		"error": "RPC engine not available",
	})
}

// Shutdown initiates a system shutdown.
func (h *SystemHandler) Shutdown(c *fiber.Ctx) error {
	// Parse optional delay parameter
	type ShutdownRequest struct {
		DelaySeconds int `json:"delay_seconds"`
	}
	var req ShutdownRequest
	if err := c.BodyParser(&req); err != nil {
		req.DelaySeconds = 60 // Default 60 second delay
	}
	if req.DelaySeconds == 0 {
		req.DelaySeconds = 60
	}

	// Call RPC engine to initiate shutdown
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		err := h.rpcClient.Shutdown(c.Context(), req.DelaySeconds)
		if err != nil {
			log.Error().Err(err).Msg("Failed to initiate shutdown via RPC")
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "Failed to initiate shutdown",
				"details": err.Error(),
			})
		}

		log.Warn().Int("delay", req.DelaySeconds).Msg("System shutdown initiated")
		return c.JSON(fiber.Map{
			"message":       "System shutdown initiated",
			"delay_seconds": req.DelaySeconds,
			"warning":       "System will shut down soon",
		})
	}

	return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
		"error": "RPC engine not available",
	})
}
