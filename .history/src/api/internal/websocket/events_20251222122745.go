// Package websocket provides WebSocket support for real-time updates.
package websocket

import (
	"context"
	"sync"
	"time"

	"sigmavault-nas-os/api/internal/rpc"

	"github.com/rs/zerolog/log"
)

// EventSubscriber manages subscriptions to RPC events and broadcasts to WebSocket clients.
type EventSubscriber struct {
	hub       *Hub
	rpcClient *rpc.Client
	ticker    *time.Ticker
	done      chan struct{}
	mu        sync.RWMutex
	running   bool
}

// NewEventSubscriber creates a new event subscriber.
func NewEventSubscriber(hub *Hub, rpcClient *rpc.Client) *EventSubscriber {
	return &EventSubscriber{
		hub:       hub,
		rpcClient: rpcClient,
		done:      make(chan struct{}),
	}
}

// Start begins the event subscriber loop.
// It periodically polls the RPC engine for system status, storage events, and compression progress.
func (es *EventSubscriber) Start(ctx context.Context, pollInterval time.Duration) {
	es.mu.Lock()
	if es.running {
		es.mu.Unlock()
		return
	}
	es.running = true
	es.ticker = time.NewTicker(pollInterval)
	es.mu.Unlock()

	go es.run(ctx)
	log.Info().Dur("poll_interval", pollInterval).Msg("WebSocket event subscriber started")
}

// Stop stops the event subscriber.
func (es *EventSubscriber) Stop() {
	es.mu.Lock()
	if !es.running {
		es.mu.Unlock()
		return
	}
	es.running = false
	if es.ticker != nil {
		es.ticker.Stop()
	}
	es.mu.Unlock()

	close(es.done)
	log.Info().Msg("WebSocket event subscriber stopped")
}

// run is the main event loop.
func (es *EventSubscriber) run(ctx context.Context) {
	es.mu.RLock()
	ticker := es.ticker
	es.mu.RUnlock()

	if ticker == nil {
		return
	}

	for {
		select {
		case <-es.done:
			return

		case <-ticker.C:
			// Poll system status
			es.pollSystemStatus(ctx)

			// Poll compression jobs
			es.pollCompressionJobs(ctx)

			// Poll agent status
			es.pollAgentStatus(ctx)
		}
	}
}

// pollSystemStatus periodically polls system status and broadcasts updates.
func (es *EventSubscriber) pollSystemStatus(ctx context.Context) {
	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	status, err := es.rpcClient.GetSystemStatus(ctx, &rpc.GetSystemStatusParams{})
	if err != nil {
		log.Error().Err(err).Msg("Failed to poll system status from RPC")
		return
	}

	// Map RPC response to WebSocket data
	data := map[string]interface{}{
		"hostname":      status.Hostname,
		"uptime":        status.Uptime.Seconds(),
		"cpu_usage":     status.CPUUsage,
		"memory_used":   status.MemoryUsage.Used,
		"memory_total":  status.MemoryUsage.Total,
		"memory_pct":    status.MemoryUsage.UsedPercent,
		"load_average":  status.LoadAverage,
		"timestamp":     time.Now().Unix(),
	}

	if err := es.hub.Broadcast(TypeSystemStatus, data); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast system status")
	}
}

// pollCompressionJobs periodically polls compression jobs and broadcasts progress updates.
func (es *EventSubscriber) pollCompressionJobs(ctx context.Context) {
	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	jobs, err := es.rpcClient.ListCompressionJobs(ctx, &rpc.ListJobsParams{
		Status: "running", // Only interested in running jobs
	})
	if err != nil {
		log.Debug().Err(err).Msg("Failed to poll compression jobs from RPC")
		return
	}

	for _, job := range jobs {
		// Calculate elapsed time from start timestamp
		elapsed := int64(0)
		if job.StartedAt != nil {
			elapsed = int64(time.Since(*job.StartedAt).Seconds())
		}

		data := map[string]interface{}{
			"job_id":             job.ID,
			"status":             job.Status,
			"source_path":        job.SourcePath,
			"progress":           job.Progress,
			"compression_ratio":  job.Ratio,
			"elapsed_seconds":    elapsed,
			"eta_seconds":        job.ETA,
			"timestamp":          time.Now().Unix(),
		}

		if err := es.hub.Broadcast(TypeCompressionUpdate, data); err != nil {
			log.Error().Err(err).Str("job_id", job.ID).Msg("Failed to broadcast compression job update")
		}
	}
}

// pollAgentStatus periodically polls agent swarm status and broadcasts updates.
func (es *EventSubscriber) pollAgentStatus(ctx context.Context) {
	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	agents, err := es.rpcClient.ListAgents(ctx, &rpc.ListAgentsParams{})
	if err != nil {
		log.Debug().Err(err).Msg("Failed to poll agents from RPC")
		return
	}

	// Aggregate agent statistics
	stats := map[string]interface{}{
		"total_agents":      len(agents),
		"active_agents":     countAgentsByStatus(agents, "busy"),
		"idle_agents":       countAgentsByStatus(agents, "idle"),
		"error_agents":      countAgentsByStatus(agents, "error"),
		"avg_response_time": calculateAvgResponseTime(agents),
		"timestamp":         time.Now().Unix(),
	}

	if err := es.hub.Broadcast(TypeAgentStatus, stats); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast agent status")
	}
}

// Helper functions

// countAgentsByStatus counts agents with a specific status.
func countAgentsByStatus(agents []rpc.Agent, status string) int {
	count := 0
	for _, agent := range agents {
		if agent.Status == status {
			count++
		}
	}
	return count
}

// calculateAvgResponseTime calculates average response time from all agents.
func calculateAvgResponseTime(agents []*rpc.Agent) float64 {
	if len(agents) == 0 {
		return 0
	}

	total := 0.0
	for _, agent := range agents {
		total += agent.AvgResponseTimeMs
	}

	return total / float64(len(agents))
}

// SubscribeToEvents sets up event subscriptions for a client.
// The client will receive messages of specified types.
func (c *Client) SubscribeToEvents(types ...MessageType) {
	c.mu.Lock()
	defer c.mu.Unlock()

	for _, msgType := range types {
		c.Subscriptions[msgType] = true
	}

	log.Debug().Str("client_id", c.ID).Strs("types", toStringSlice(types)).Msg("Client subscribed to event types")
}

// UnsubscribeFromEvents removes subscriptions for a client.
func (c *Client) UnsubscribeFromEvents(types ...MessageType) {
	c.mu.Lock()
	defer c.mu.Unlock()

	for _, msgType := range types {
		delete(c.Subscriptions, msgType)
	}

	log.Debug().Str("client_id", c.ID).Strs("types", toStringSlice(types)).Msg("Client unsubscribed from event types")
}

// IsSubscribedTo checks if a client is subscribed to a message type.
func (c *Client) IsSubscribedTo(msgType MessageType) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	subscribed, exists := c.Subscriptions[msgType]
	return exists && subscribed
}

// BroadcastIfSubscribed broadcasts a message to all connected clients subscribed to a type.
func (h *Hub) BroadcastIfSubscribed(msgType MessageType, data interface{}) error {
	h.mu.RLock()
	defer h.mu.RUnlock()

	// Count subscribed clients (for logging)
	subscribedCount := 0
	for client := range h.clients {
		if client.IsSubscribedTo(msgType) {
			subscribedCount++
		}
	}

	if subscribedCount == 0 {
		return nil // No subscribers, skip broadcast
	}

	// Perform the broadcast
	return h.Broadcast(msgType, data)
}

// toStringSlice converts MessageType slice to string slice.
func toStringSlice(types []MessageType) []string {
	result := make([]string, len(types))
	for i, t := range types {
		result[i] = string(t)
	}
	return result
}
