// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"sigmavault-nas-os/api/internal/models"
	"sigmavault-nas-os/api/internal/rpc"

	"github.com/gofiber/fiber/v2"
	"github.com/rs/zerolog/log"
)

// AgentsHandler handles AI agent swarm-related requests.
type AgentsHandler struct {
	rpcClient *rpc.Client
}

// NewAgentsHandler creates a new AgentsHandler instance.
func NewAgentsHandler(client *rpc.Client) *AgentsHandler {
	return &AgentsHandler{
		rpcClient: client,
	}
}

// ListAgents returns all AI agents in the swarm.
func (h *AgentsHandler) ListAgents(c *fiber.Ctx) error {
	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rpcAgents, err := h.rpcClient.ListAgents(c.Context(), &rpc.ListAgentsParams{})
		if err == nil {
			agents := make([]models.AgentStatus, 0, len(rpcAgents))
			activeCount := 0
			idleCount := 0
			for _, ra := range rpcAgents {
				agents = append(agents, models.AgentStatus{
					ID:     ra.ID,
					Name:   ra.Codename,
					Type:   ra.Role,
					Status: ra.Status,
				})
				if ra.Status == "active" {
					activeCount++
				} else if ra.Status == "idle" {
					idleCount++
				}
			}
			return c.JSON(fiber.Map{
				"agents":       agents,
				"count":        len(agents),
				"active_count": activeCount,
				"idle_count":   idleCount,
			})
		}
		log.Warn().Err(err).Msg("Failed to list agents via RPC, falling back to static data")
	}

	// Fallback static data for development
	agents := []models.AgentStatus{
		{
			ID:             "agent-tensor-001",
			Name:           "TENSOR",
			Type:           "compression",
			Status:         "active",
			TasksQueued:    0,
			TasksCompleted: 0,
		},
		{
			ID:             "agent-cipher-001",
			Name:           "CIPHER",
			Type:           "encryption",
			Status:         "active",
			TasksQueued:    0,
			TasksCompleted: 0,
		},
		{
			ID:             "agent-velocity-001",
			Name:           "VELOCITY",
			Type:           "optimization",
			Status:         "idle",
			TasksQueued:    0,
			TasksCompleted: 0,
		},
	}

	return c.JSON(fiber.Map{
		"agents":       agents,
		"count":        len(agents),
		"active_count": 2,
		"idle_count":   1,
	})
}

// GetAgent returns a specific agent's status.
func (h *AgentsHandler) GetAgent(c *fiber.Ctx) error {
	agentID := c.Params("id")

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		ra, err := h.rpcClient.GetAgent(c.Context(), agentID)
		if err == nil {
			return c.JSON(models.AgentStatus{
				ID:     ra.ID,
				Name:   ra.Codename,
				Type:   ra.Role,
				Status: ra.Status,
			})
		}
		log.Warn().Err(err).Str("agent_id", agentID).Msg("Failed to get agent via RPC, falling back to static data")
	}

	// Fallback static data
	agent := models.AgentStatus{
		ID:             agentID,
		Name:           "TENSOR",
		Type:           "compression",
		Status:         "active",
		TasksQueued:    0,
		TasksCompleted: 0,
	}

	return c.JSON(agent)
}

// AgentMetrics returns performance metrics for agents.
func (h *AgentsHandler) AgentMetrics(c *fiber.Ctx) error {
	agentID := c.Query("agent_id", "") // Optional filter by agent

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		if agentID != "" {
			metrics, err := h.rpcClient.GetAgentMetrics(c.Context(), agentID)
			if err == nil {
				return c.JSON(metrics)
			}
			log.Warn().Err(err).Str("agent_id", agentID).Msg("Failed to get agent metrics via RPC, falling back to static data")
		} else {
			// Get aggregated metrics - list all agents and aggregate
			agents, err := h.rpcClient.ListAgents(c.Context(), &rpc.ListAgentsParams{})
			if err == nil {
				activeCount := 0
				idleCount := 0
				for _, a := range agents {
					if a.Status == "active" {
						activeCount++
					} else if a.Status == "idle" {
						idleCount++
					}
				}
				return c.JSON(fiber.Map{
					"total_agents":  len(agents),
					"active_agents": activeCount,
					"idle_agents":   idleCount,
					"agent_count":   len(agents),
				})
			}
			log.Warn().Err(err).Msg("Failed to get agents for metrics via RPC, falling back to static data")
		}
	}

	// Fallback static data
	return c.JSON(fiber.Map{
		"total_agents":          40,
		"active_agents":         35,
		"idle_agents":           5,
		"total_tasks_queued":    15,
		"total_tasks_completed": 1250,
		"avg_cpu_usage":         45.2,
		"avg_memory_usage":      1024 * 1024 * 512, // 512MB
		"compression_ratio":     0.92,              // 92% average compression
	})
}

// CompressionHandler handles AI compression-related requests.
type CompressionHandler struct {
	rpcClient *rpc.Client
}

// NewCompressionHandler creates a new CompressionHandler instance.
func NewCompressionHandler(client *rpc.Client) *CompressionHandler {
	return &CompressionHandler{
		rpcClient: client,
	}
}

// StartCompressionRequest represents a compression job request.
type StartCompressionRequest struct {
	SourcePath string `json:"source_path" validate:"required"`
	Algorithm  string `json:"algorithm"` // auto, lz4, zstd, neural
	Priority   string `json:"priority"`  // low, normal, high
}

// StartCompression initiates a compression job.
func (h *CompressionHandler) StartCompression(c *fiber.Ctx) error {
	var req StartCompressionRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	// Default algorithm
	if req.Algorithm == "" {
		req.Algorithm = "auto"
	}
	if req.Priority == "" {
		req.Priority = "normal"
	}

	// Map priority string to int
	priorityInt := 5 // normal
	switch req.Priority {
	case "low":
		priorityInt = 1
	case "high":
		priorityInt = 10
	}

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		job, err := h.rpcClient.CreateCompressionJob(c.Context(), &rpc.CreateJobParams{
			Type:       "compress",
			SourcePath: req.SourcePath,
			Algorithm:  req.Algorithm,
			Priority:   priorityInt,
		})
		if err == nil {
			return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
				"message":     "Compression job queued",
				"job_id":      job.ID,
				"source_path": job.SourcePath,
				"algorithm":   job.Algorithm,
				"status":      job.Status,
			})
		}
		log.Warn().Err(err).Str("source_path", req.SourcePath).Msg("Failed to start compression via RPC")
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to start compression job")
	}

	// RPC not available - return mock response for development
	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"message":     "Compression job queued",
		"job_id":      "job-mock-uuid",
		"source_path": req.SourcePath,
		"algorithm":   req.Algorithm,
		"status":      "pending",
	})
}

// ListCompressionJobs returns all compression jobs.
func (h *CompressionHandler) ListCompressionJobs(c *fiber.Ctx) error {
	status := c.Query("status", "") // Filter by status

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rpcResult, err := h.rpcClient.ListCompressionJobs(c.Context(), &rpc.CompressionJobsListParams{Status: status})
		if err == nil {
			jobs := make([]models.CompressionJob, 0, len(rpcResult.Jobs))
			for _, rj := range rpcResult.Jobs {
				jobs = append(jobs, models.CompressionJob{
					ID:         rj.ID,
					Status:     rj.Status,
					SourcePath: rj.SourcePath,
					Algorithm:  rj.Algorithm,
					Progress:   rj.Progress,
				})
			}
			return c.JSON(fiber.Map{
				"jobs":   jobs,
				"count":  len(jobs),
				"filter": status,
			})
		}
		log.Warn().Err(err).Msg("Failed to list compression jobs via RPC, falling back to empty list")
	}

	// Fallback - empty list
	jobs := []models.CompressionJob{}

	return c.JSON(fiber.Map{
		"jobs":   jobs,
		"count":  len(jobs),
		"filter": status,
	})
}

// GetCompressionJob returns a specific compression job.
func (h *CompressionHandler) GetCompressionJob(c *fiber.Ctx) error {
	jobID := c.Params("id")

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		rj, err := h.rpcClient.GetCompressionJobStatus(c.Context(), jobID)
		if err == nil {
			return c.JSON(models.CompressionJob{
				ID:         rj.ID,
				Status:     rj.Status,
				SourcePath: rj.SourcePath,
				Algorithm:  rj.Algorithm,
				Progress:   rj.Progress,
			})
		}
		log.Warn().Err(err).Str("job_id", jobID).Msg("Failed to get compression job via RPC, falling back to static data")
	}

	// Fallback static data
	job := models.CompressionJob{
		ID:         jobID,
		Status:     "completed",
		SourcePath: "/data/example",
		Algorithm:  "zstd",
		Progress:   100.0,
	}

	return c.JSON(job)
}

// CancelCompressionJob cancels a pending or running compression job.
func (h *CompressionHandler) CancelCompressionJob(c *fiber.Ctx) error {
	jobID := c.Params("id")

	// Try RPC engine first
	if h.rpcClient != nil && h.rpcClient.IsConnected() {
		err := h.rpcClient.CancelCompressionJob(c.Context(), jobID)
		if err == nil {
			return c.JSON(fiber.Map{
				"message": "Job cancelled successfully",
				"job_id":  jobID,
			})
		}
		log.Warn().Err(err).Str("job_id", jobID).Msg("Failed to cancel compression job via RPC")
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to cancel compression job")
	}

	// RPC not available - return mock response for development
	return c.JSON(fiber.Map{
		"message": "Job cancellation requested",
		"job_id":  jobID,
	})
}
