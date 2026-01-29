// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"encoding/base64"
	"io"
	"sigmavault-nas-os/api/internal/rpc"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

// CompressionV2Handler handles compression requests using the Python RPC engine.
type CompressionV2Handler struct {
	rpcClient *rpc.Client
}

// NewCompressionV2Handler creates a new CompressionV2Handler instance.
func NewCompressionV2Handler(client *rpc.Client) *CompressionV2Handler {
	return &CompressionV2Handler{
		rpcClient: client,
	}
}

// CompressDataRequest is the request body for data compression.
type CompressDataRequest struct {
	Data  string `json:"data"`            // Base64 encoded data
	Level string `json:"level,omitempty"` // fast, balanced, maximum
}

// CompressData handles POST /compression/data - compress in-memory data.
func (h *CompressionV2Handler) CompressData(c *fiber.Ctx) error {
	var req CompressDataRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	if req.Data == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Data field is required",
		})
	}

	// Default level
	if req.Level == "" {
		req.Level = "balanced"
	}

	// Decode base64 to get raw data
	rawData, err := base64.StdEncoding.DecodeString(req.Data)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid base64 encoded data",
		})
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.CompressData(c.Context(), rawData, req.Level)
		if err != nil {
			log.Warn().Err(err).Msg("RPC CompressData failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Compression engine unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response for development
	return c.JSON(fiber.Map{
		"job_id":            uuid.New().String(),
		"success":           true,
		"original_size":     len(rawData),
		"compressed_size":   int(float64(len(rawData)) * 0.3), // Mock 70% compression
		"compression_ratio": 0.70,
		"elapsed_seconds":   0.05,
		"data":              req.Data[:min(100, len(req.Data))] + "...", // Truncated for mock
		"_mock":             true,
	})
}

// DecompressDataRequest is the request body for data decompression.
type DecompressDataRequest struct {
	Data  string `json:"data"`             // Base64 encoded compressed data
	JobID string `json:"job_id,omitempty"` // Optional job ID for tracking
}

// DecompressData handles POST /compression/decompress/data - decompress in-memory data.
func (h *CompressionV2Handler) DecompressData(c *fiber.Ctx) error {
	var req DecompressDataRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	if req.Data == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Data field is required",
		})
	}

	// Decode base64 to get compressed data
	compressedData, err := base64.StdEncoding.DecodeString(req.Data)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid base64 encoded data",
		})
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.DecompressData(c.Context(), compressedData, req.JobID)
		if err != nil {
			log.Warn().Err(err).Msg("RPC DecompressData failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Decompression engine unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response
	return c.JSON(fiber.Map{
		"job_id":            req.JobID,
		"success":           true,
		"compressed_size":   len(compressedData),
		"decompressed_size": int(float64(len(compressedData)) * 3.3), // Mock expansion
		"elapsed_seconds":   0.03,
		"data":              req.Data, // In mock, return same data
		"_mock":             true,
	})
}

// CompressFileRequest is the request body for file compression.
type CompressFileRequest struct {
	SourcePath string `json:"source_path"`
	DestPath   string `json:"dest_path,omitempty"`
	Level      string `json:"level,omitempty"` // fast, balanced, maximum
}

// CompressFile handles POST /compression/file - compress a file.
func (h *CompressionV2Handler) CompressFile(c *fiber.Ctx) error {
	var req CompressFileRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	if req.SourcePath == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "source_path is required",
		})
	}

	if req.Level == "" {
		req.Level = "balanced"
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.CompressFile(c.Context(), &rpc.CompressFileParams{
			SourcePath: req.SourcePath,
			DestPath:   req.DestPath,
			Level:      req.Level,
		})
		if err != nil {
			log.Warn().Err(err).Str("source", req.SourcePath).Msg("RPC CompressFile failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Compression engine unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response
	destPath := req.DestPath
	if destPath == "" {
		destPath = req.SourcePath + ".sv"
	}
	return c.JSON(fiber.Map{
		"job_id":            uuid.New().String(),
		"success":           true,
		"original_size":     1024 * 1024, // Mock 1MB
		"compressed_size":   307200,      // Mock 300KB (~70% compression)
		"compression_ratio": 0.70,
		"elapsed_seconds":   0.15,
		"source_path":       req.SourcePath,
		"dest_path":         destPath,
		"_mock":             true,
	})
}

// DecompressFileRequest is the request body for file decompression.
type DecompressFileRequest struct {
	SourcePath string `json:"source_path"`
	DestPath   string `json:"dest_path,omitempty"`
}

// DecompressFile handles POST /compression/decompress/file - decompress a file.
func (h *CompressionV2Handler) DecompressFile(c *fiber.Ctx) error {
	var req DecompressFileRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	if req.SourcePath == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "source_path is required",
		})
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.DecompressFile(c.Context(), &rpc.DecompressFileParams{
			SourcePath: req.SourcePath,
			DestPath:   req.DestPath,
		})
		if err != nil {
			log.Warn().Err(err).Str("source", req.SourcePath).Msg("RPC DecompressFile failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Decompression engine unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response
	destPath := req.DestPath
	if destPath == "" {
		// Remove .sv extension if present
		if len(req.SourcePath) > 3 && req.SourcePath[len(req.SourcePath)-3:] == ".sv" {
			destPath = req.SourcePath[:len(req.SourcePath)-3]
		} else {
			destPath = req.SourcePath + ".decompressed"
		}
	}
	return c.JSON(fiber.Map{
		"job_id":            uuid.New().String(),
		"success":           true,
		"compressed_size":   307200,      // Mock 300KB
		"decompressed_size": 1024 * 1024, // Mock 1MB
		"elapsed_seconds":   0.08,
		"source_path":       req.SourcePath,
		"dest_path":         destPath,
		"_mock":             true,
	})
}

// QueueSubmitRequest is the request body for submitting a job to the queue.
type QueueSubmitRequest struct {
	Type       string `json:"type"`                  // compress_data, compress_file, decompress_data, decompress_file
	SourcePath string `json:"source_path,omitempty"` // For file operations
	DestPath   string `json:"dest_path,omitempty"`   // For file operations
	Data       string `json:"data,omitempty"`        // Base64 data for data operations
	Priority   string `json:"priority,omitempty"`    // low, normal, high, critical
}

// QueueSubmit handles POST /compression/queue - submit a job to the queue.
func (h *CompressionV2Handler) QueueSubmit(c *fiber.Ctx) error {
	var req QueueSubmitRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	if req.Type == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "type is required (compress_data, compress_file, decompress_data, decompress_file)",
		})
	}

	// Validate type
	validTypes := map[string]bool{
		"compress_data":   true,
		"compress_file":   true,
		"decompress_data": true,
		"decompress_file": true,
	}
	if !validTypes[req.Type] {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid type. Must be: compress_data, compress_file, decompress_data, decompress_file",
		})
	}

	if req.Priority == "" {
		req.Priority = "normal"
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.QueueSubmit(c.Context(), &rpc.QueueSubmitParams{
			Type:       req.Type,
			SourcePath: req.SourcePath,
			DestPath:   req.DestPath,
			Data:       req.Data,
			Priority:   req.Priority,
		})
		if err != nil {
			log.Warn().Err(err).Str("type", req.Type).Msg("RPC QueueSubmit failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Queue submission failed",
				"details": err.Error(),
			})
		}
		return c.Status(fiber.StatusAccepted).JSON(result)
	}

	// Fallback: Return mock response
	jobID := uuid.New().String()
	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"job_id":     jobID,
		"status":     "pending",
		"priority":   req.Priority,
		"job_type":   req.Type,
		"created_at": "2025-01-01T00:00:00Z",
		"_mock":      true,
	})
}

// QueueStatus handles GET /compression/queue/:id - get job status.
func (h *CompressionV2Handler) QueueStatus(c *fiber.Ctx) error {
	jobID := c.Params("id")

	if jobID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "job_id is required",
		})
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.GetQueueStatus(c.Context(), jobID)
		if err != nil {
			log.Warn().Err(err).Str("job_id", jobID).Msg("RPC GetQueueStatus failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Queue status unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response
	return c.JSON(fiber.Map{
		"job_id":       jobID,
		"status":       "completed",
		"priority":     "normal",
		"job_type":     "compress_file",
		"progress":     100.0,
		"created_at":   "2025-01-01T00:00:00Z",
		"started_at":   "2025-01-01T00:00:01Z",
		"completed_at": "2025-01-01T00:00:02Z",
		"_mock":        true,
	})
}

// QueueStats handles GET /compression/queue - get queue statistics.
func (h *CompressionV2Handler) QueueStats(c *fiber.Ctx) error {
	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.GetQueueStats(c.Context())
		if err != nil {
			log.Warn().Err(err).Msg("RPC GetQueueStats failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Queue stats unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response
	return c.JSON(fiber.Map{
		"total_jobs":     10,
		"pending_jobs":   2,
		"running_jobs":   1,
		"completed_jobs": 6,
		"failed_jobs":    1,
		"cancelled_jobs": 0,
		"_mock":          true,
	})
}

// QueueCancel handles DELETE /compression/queue/:id - cancel a queued job.
func (h *CompressionV2Handler) QueueCancel(c *fiber.Ctx) error {
	jobID := c.Params("id")

	if jobID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "job_id is required",
		})
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.QueueCancel(c.Context(), jobID)
		if err != nil {
			log.Warn().Err(err).Str("job_id", jobID).Msg("RPC QueueCancel failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Queue cancel failed",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response
	return c.JSON(fiber.Map{
		"job_id":    jobID,
		"cancelled": true,
		"_mock":     true,
	})
}

// GetConfig handles GET /compression/config - get compression configuration.
func (h *CompressionV2Handler) GetConfig(c *fiber.Ctx) error {
	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.GetCompressionConfig(c.Context())
		if err != nil {
			log.Warn().Err(err).Msg("RPC GetCompressionConfig failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Config unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response
	return c.JSON(fiber.Map{
		"level":        "balanced",
		"chunk_size":   1024 * 1024, // 1MB
		"use_semantic": true,
		"lossless":     true,
		"engine":       "stub",
		"_mock":        true,
	})
}

// SetConfigRequest is the request body for setting compression config.
type SetConfigRequest struct {
	Level       string `json:"level,omitempty"`
	ChunkSize   int    `json:"chunk_size,omitempty"`
	UseSemantic *bool  `json:"use_semantic,omitempty"`
	Lossless    *bool  `json:"lossless,omitempty"`
}

// SetConfig handles PUT /compression/config - update compression configuration.
func (h *CompressionV2Handler) SetConfig(c *fiber.Ctx) error {
	var req SetConfigRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.SetCompressionConfig(c.Context(), &rpc.SetCompressionConfigParams{
			Level:       req.Level,
			ChunkSize:   req.ChunkSize,
			UseSemantic: req.UseSemantic,
			Lossless:    req.Lossless,
		})
		if err != nil {
			log.Warn().Err(err).Msg("RPC SetCompressionConfig failed")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Config update failed",
				"details": err.Error(),
			})
		}
		return c.JSON(result)
	}

	// Fallback: Return mock response with updated values
	level := "balanced"
	if req.Level != "" {
		level = req.Level
	}
	chunkSize := 1024 * 1024
	if req.ChunkSize > 0 {
		chunkSize = req.ChunkSize
	}
	useSemantic := true
	if req.UseSemantic != nil {
		useSemantic = *req.UseSemantic
	}
	lossless := true
	if req.Lossless != nil {
		lossless = *req.Lossless
	}

	return c.JSON(fiber.Map{
		"level":        level,
		"chunk_size":   chunkSize,
		"use_semantic": useSemantic,
		"lossless":     lossless,
		"engine":       "stub",
		"_mock":        true,
	})
}

// CompressUpload handles multipart file upload compression.
// POST /compression/upload - upload and compress a file.
func (h *CompressionV2Handler) CompressUpload(c *fiber.Ctx) error {
	// Get the file from the form
	file, err := c.FormFile("file")
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "File upload required (field name: 'file')",
		})
	}

	level := c.FormValue("level", "balanced")

	// Open the file
	src, err := file.Open()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "Failed to open uploaded file",
		})
	}
	defer src.Close()

	// Read file content
	data, err := io.ReadAll(src)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "Failed to read uploaded file",
		})
	}

	// Try RPC engine
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		result, err := h.rpcClient.CompressData(c.Context(), data, level)
		if err != nil {
			log.Warn().Err(err).Str("filename", file.Filename).Msg("RPC CompressData failed for upload")
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error":   "Compression engine unavailable",
				"details": err.Error(),
			})
		}
		return c.JSON(fiber.Map{
			"filename":          file.Filename,
			"job_id":            result.JobID,
			"success":           result.Success,
			"original_size":     result.OriginalSize,
			"compressed_size":   result.CompressedSize,
			"compression_ratio": result.CompressionRatio,
			"elapsed_seconds":   result.ElapsedSeconds,
			"data":              result.Data, // Base64 compressed data
		})
	}

	// Fallback: Return mock response
	return c.JSON(fiber.Map{
		"filename":          file.Filename,
		"job_id":            uuid.New().String(),
		"success":           true,
		"original_size":     len(data),
		"compressed_size":   int(float64(len(data)) * 0.3),
		"compression_ratio": 0.70,
		"elapsed_seconds":   0.05,
		"_mock":             true,
	})
}

// Helper function for min
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
