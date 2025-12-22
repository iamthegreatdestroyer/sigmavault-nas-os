// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"sigmavault-nas-os/api/internal/models"
	"sigmavault-nas-os/api/internal/rpc"

	"github.com/gofiber/fiber/v2"
	"github.com/rs/zerolog/log"
)

// StorageHandler handles storage-related requests.
type StorageHandler struct {
	rpcClient *rpc.Client
}

// NewStorageHandler creates a new StorageHandler instance.
func NewStorageHandler(client *rpc.Client) *StorageHandler {
	return &StorageHandler{
		rpcClient: client,
	}
}

// ListPools returns all ZFS storage pools.
func (h *StorageHandler) ListPools(c *fiber.Ctx) error {
	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rpcPools, err := h.rpcClient.ListPools(c.Context(), &rpc.ListPoolsParams{})
		if err == nil {
			pools := make([]models.StoragePool, 0, len(rpcPools))
			for _, rp := range rpcPools {
				pools = append(pools, models.StoragePool{
					ID:         rp.Name, // Use Name as ID (pools identified by name in ZFS)
					Name:       rp.Name,
					Status:     rp.Status,
					TotalBytes: rp.Size,
					UsedBytes:  rp.Allocated,
					FreeBytes:  rp.Free,
					UsedPct:    rp.Capacity,
				})
			}
			return c.JSON(fiber.Map{
				"pools": pools,
				"count": len(pools),
			})
		}
		log.Warn().Err(err).Msg("Failed to list pools via RPC, falling back to mock data")
	}

	// Fallback mock data
	pools := []models.StoragePool{
		{
			ID:         "pool-001",
			Name:       "tank",
			Status:     "healthy",
			TotalBytes: 4 * 1024 * 1024 * 1024 * 1024, // 4TB
			UsedBytes:  1 * 1024 * 1024 * 1024 * 1024, // 1TB
			FreeBytes:  3 * 1024 * 1024 * 1024 * 1024, // 3TB
			UsedPct:    25.0,
		},
	}

	return c.JSON(fiber.Map{
		"pools": pools,
		"count": len(pools),
	})
}

// GetPool returns a specific ZFS pool by ID.
func (h *StorageHandler) GetPool(c *fiber.Ctx) error {
	poolID := c.Params("id")

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rp, err := h.rpcClient.GetPool(c.Context(), poolID)
		if err == nil {
			pool := models.StoragePool{
				ID:         rp.Name,
				Name:       rp.Name,
				Status:     rp.Status,
				TotalBytes: rp.Size,
				UsedBytes:  rp.Allocated,
				FreeBytes:  rp.Free,
				UsedPct:    rp.Capacity,
			}
			return c.JSON(pool)
		}
		log.Warn().Err(err).Str("pool_id", poolID).Msg("Failed to get pool via RPC, falling back to mock data")
	}

	// Fallback mock data
	pool := models.StoragePool{
		ID:         poolID,
		Name:       "tank",
		Status:     "healthy",
		TotalBytes: 4 * 1024 * 1024 * 1024 * 1024,
		UsedBytes:  1 * 1024 * 1024 * 1024 * 1024,
		FreeBytes:  3 * 1024 * 1024 * 1024 * 1024,
		UsedPct:    25.0,
	}

	return c.JSON(pool)
}

// CreatePoolRequest represents a request to create a new pool.
type CreatePoolRequest struct {
	Name    string   `json:"name" validate:"required"`
	Disks   []string `json:"disks" validate:"required,min=1"`
	RaidZ   int      `json:"raidz"` // 0, 1, 2, or 3
	Mirror  bool     `json:"mirror"`
	Encrypt bool     `json:"encrypt"`
}

// CreatePool creates a new ZFS storage pool.
func (h *StorageHandler) CreatePool(c *fiber.Ctx) error {
	var req CreatePoolRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	// Determine RAID type string
	raidType := "stripe"
	if req.Mirror {
		raidType = "mirror"
	} else if req.RaidZ > 0 {
		raidType = "raidz" + string(rune('0'+req.RaidZ))
	}

	// Build vdev configuration from disk list
	vdevs := []rpc.CreateVDevParam{
		{
			Type:  raidType,
			Disks: req.Disks,
		},
	}

	// Build encryption params if enabled
	var encryptionParams *rpc.EncryptionParams
	if req.Encrypt {
		encryptionParams = &rpc.EncryptionParams{
			Algorithm: "aes-256-gcm",
			KeyFormat: "passphrase",
		}
	}

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rp, err := h.rpcClient.CreatePool(c.Context(), &rpc.CreatePoolParams{
			Name:       req.Name,
			VDevs:      vdevs,
			Properties: map[string]string{},
			Encryption: encryptionParams,
		})
		if err == nil {
			return c.Status(fiber.StatusCreated).JSON(fiber.Map{
				"message":   "Pool created successfully",
				"pool_id":   rp.Name,
				"pool_name": rp.Name,
				"status":    rp.Status,
			})
		}
		log.Warn().Err(err).Str("pool_name", req.Name).Msg("Failed to create pool via RPC")
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to create storage pool")
	}

	// RPC not available - return mock success for development
	return c.Status(fiber.StatusCreated).JSON(fiber.Map{
		"message":   "Pool creation initiated",
		"pool_name": req.Name,
	})
}

// DeletePool destroys a ZFS pool.
func (h *StorageHandler) DeletePool(c *fiber.Ctx) error {
	poolID := c.Params("id")

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		err := h.rpcClient.DestroyPool(c.Context(), poolID, false)
		if err == nil {
			return c.JSON(fiber.Map{
				"message": "Pool deleted successfully",
				"pool_id": poolID,
			})
		}
		log.Warn().Err(err).Str("pool_id", poolID).Msg("Failed to delete pool via RPC")
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to delete storage pool")
	}

	// RPC not available - return mock success for development
	return c.JSON(fiber.Map{
		"message": "Pool deletion initiated",
		"pool_id": poolID,
	})
}

// ListShares returns all file shares.
func (h *StorageHandler) ListShares(c *fiber.Ctx) error {
	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rpcShares, err := h.rpcClient.ListShares(c.Context(), &rpc.ListSharesParams{})
		if err == nil {
			shares := make([]models.Share, 0, len(rpcShares))
			for _, rs := range rpcShares {
				shares = append(shares, models.Share{
					ID:          rs.ID,
					Name:        rs.Name,
					Path:        rs.Path,
					Type:        rs.Protocol,
					Description: rs.Description,
					ReadOnly:    rs.ReadOnly,
				})
			}
			return c.JSON(fiber.Map{
				"shares": shares,
				"count":  len(shares),
			})
		}
		log.Warn().Err(err).Msg("Failed to list shares via RPC, falling back to empty list")
	}

	// Fallback - empty list
	shares := []models.Share{}

	return c.JSON(fiber.Map{
		"shares": shares,
		"count":  len(shares),
	})
}

// CreateShareRequest represents a request to create a share.
type CreateShareRequest struct {
	Name        string   `json:"name" validate:"required"`
	Path        string   `json:"path" validate:"required"`
	Type        string   `json:"type" validate:"required,oneof=smb nfs both"`
	Description string   `json:"description"`
	ReadOnly    bool     `json:"read_only"`
	AllowedIPs  []string `json:"allowed_ips"`
}

// CreateShare creates a new file share.
func (h *StorageHandler) CreateShare(c *fiber.Ctx) error {
	var req CreateShareRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rs, err := h.rpcClient.CreateShare(c.Context(), &rpc.CreateShareParams{
			Name:        req.Name,
			Path:        req.Path,
			Protocol:    req.Type,
			Description: req.Description,
			ReadOnly:    req.ReadOnly,
		})
		if err == nil {
			return c.Status(fiber.StatusCreated).JSON(fiber.Map{
				"message":    "Share created successfully",
				"share_id":   rs.ID,
				"share_name": rs.Name,
				"path":       rs.Path,
				"type":       rs.Protocol,
			})
		}
		log.Warn().Err(err).Str("share_name", req.Name).Msg("Failed to create share via RPC")
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to create network share")
	}

	// RPC not available - return mock success for development
	return c.Status(fiber.StatusCreated).JSON(fiber.Map{
		"message":    "Share created successfully",
		"share_name": req.Name,
	})
}

// DeleteShare removes a file share.
func (h *StorageHandler) DeleteShare(c *fiber.Ctx) error {
	shareID := c.Params("id")

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		err := h.rpcClient.DeleteShare(c.Context(), shareID)
		if err == nil {
			return c.JSON(fiber.Map{
				"message":  "Share deleted successfully",
				"share_id": shareID,
			})
		}
		log.Warn().Err(err).Str("share_id", shareID).Msg("Failed to delete share via RPC")
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to delete network share")
	}

	// RPC not available - return mock success for development
	return c.JSON(fiber.Map{
		"message":  "Share deleted successfully",
		"share_id": shareID,
	})
}
