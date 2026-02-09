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

	// Circuit breaker fields for graceful degradation during RPC outages
	failureCount             int
	lastFailureTime          time.Time
	circuitBreakerThreshold  int           // default: 5 consecutive failures
	circuitBreakerResetAfter time.Duration // default: 5 minutes
	lastErrorEventTime       time.Time     // rate limiting for error events

	// Caching fields for graceful degradation
	systemStatusCache      map[string]interface{}
	compressionJobsCache   []map[string]interface{}
	agentStatusCache       map[string]interface{}
	lastSuccessfulStatusAt time.Time
}

// NewEventSubscriber creates a new event subscriber.
func NewEventSubscriber(hub *Hub, rpcClient *rpc.Client) *EventSubscriber {
	return &EventSubscriber{
		hub:                      hub,
		rpcClient:                rpcClient,
		done:                     make(chan struct{}),
		circuitBreakerThreshold:  5,
		circuitBreakerResetAfter: 5 * time.Minute,
		systemStatusCache:        make(map[string]interface{}),
		compressionJobsCache:     make([]map[string]interface{}, 0),
		agentStatusCache:         make(map[string]interface{}),
	}
}

// Start begins the event subscriber loop.
// It periodically polls the RPC engine for system status, storage events, and compression progress.
func (es *EventSubscriber) Start(ctx context.Context, pollInterval time.Duration) {
	es.mu.Lock()
	if es.running {
		log.Warn().Msg("EventSubscriber.Start: already running, returning")
		es.mu.Unlock()
		return
	}
	es.running = true
	es.ticker = time.NewTicker(pollInterval)
	es.mu.Unlock()

	log.Info().Msg("EventSubscriber.Start: launching goroutine with run()")
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
		log.Error().Msg("EventSubscriber.run: ticker is nil - not starting polling loop")
		return
	}

	log.Info().Msg("EventSubscriber.run: starting polling loop")

	for {
		select {
		case <-es.done:
			log.Info().Msg("EventSubscriber.run: received done signal, exiting")
			return

		case <-ticker.C:
			log.Debug().Msg("EventSubscriber.run: polling tick - calling pollSystemStatus, pollCompressionJobs, pollAgentStatus")
			// Poll system status
			es.pollSystemStatus(ctx)

			// Poll compression jobs
			es.pollCompressionJobs(ctx)

			// Poll agent status
			es.pollAgentStatus(ctx)

			// Poll scheduler metrics (autonomy system)
			es.pollSchedulerMetrics(ctx)

			// Poll recovery status (autonomy system)
			es.pollRecoveryStatus(ctx)

			// Poll tuning status (autonomy system)
			es.pollTuningStatus(ctx)
		}
	}
}

// pollSystemStatus periodically polls system status and broadcasts updates.
func (es *EventSubscriber) pollSystemStatus(ctx context.Context) {
	es.mu.Lock()
	defer es.mu.Unlock()

	if es.rpcClient == nil {
		log.Debug().Msg("pollSystemStatus: rpcClient is nil, returning")
		return
	}

	log.Debug().Msg("pollSystemStatus: calling rpcClient.GetSystemStatus()")
	status, err := es.rpcClient.GetSystemStatus(ctx, &rpc.GetSystemStatusParams{})
	if err != nil {
		es.failureCount++
		es.lastFailureTime = time.Now()

		log.Error().Err(err).Int("failure_count", es.failureCount).Msg("pollSystemStatus: GetSystemStatus failed")

		// Rate limit error events - only broadcast first error and periodically after
		if es.failureCount == 1 || time.Since(es.lastErrorEventTime) > 30*time.Second {
			es.lastErrorEventTime = time.Now()
			errorMsg := map[string]interface{}{
				"reason":               "rpc_disconnect",
				"error_code":           "SYSTEM_STATUS_FAILED",
				"consecutive_failures": es.failureCount,
				"timestamp":            time.Now().Unix(),
			}
			if err := es.hub.BroadcastIfSubscribed(TypeRPCError, errorMsg); err != nil {
				log.Error().Err(err).Msg("Failed to broadcast RPC error event")
			}
		}

		// Send cached data if available
		if len(es.systemStatusCache) > 0 {
			es.systemStatusCache["stale"] = true
			es.systemStatusCache["last_update"] = es.lastSuccessfulStatusAt
			es.systemStatusCache["error_code"] = "RPC_DISCONNECT"
			es.systemStatusCache["timestamp"] = time.Now().Unix()

			if err := es.hub.BroadcastIfSubscribed(TypeSystemStatus, es.systemStatusCache); err != nil {
				log.Error().Err(err).Msg("Failed to broadcast cached system status on error")
			}
		}

		log.Error().Err(err).Msg("Failed to poll system status from RPC")
		return
	}

	// Clear error counters on success
	es.failureCount = 0
	es.lastFailureTime = time.Time{}

	// Map RPC response to WebSocket data
	data := map[string]interface{}{
		"hostname":     status.Hostname,
		"uptime":       status.Uptime.Seconds(),
		"cpu_usage":    status.CPUUsage,
		"memory_used":  status.MemoryUsage.Used,
		"memory_total": status.MemoryUsage.Total,
		"memory_pct":   status.MemoryUsage.UsedPercent,
		"load_average": status.LoadAverage,
		"timestamp":    time.Now().Unix(),
	}

	// Update cache
	es.systemStatusCache = data
	es.lastSuccessfulStatusAt = time.Now()

	// Log successful event broadcast
	clientCount := es.hub.ClientCount()
	log.Info().Int("client_count", clientCount).Str("event_type", string(TypeSystemStatus)).
		Float64("cpu_usage", status.CPUUsage).Msg("Broadcasting system status event")

	if err := es.hub.Broadcast(TypeSystemStatus, data); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast system status")
	}
}

// pollCompressionJobs periodically polls compression jobs and broadcasts progress updates.
// Now uses the v2 compression API with detailed progress information.
func (es *EventSubscriber) pollCompressionJobs(ctx context.Context) {
	es.mu.Lock()
	defer es.mu.Unlock()

	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	// Circuit breaker check - prevent cascading failures
	if es.failureCount >= es.circuitBreakerThreshold {
		if time.Since(es.lastFailureTime) < es.circuitBreakerResetAfter {
			// Circuit still open - serve cached data
			if len(es.compressionJobsCache) > 0 {
				payload := map[string]interface{}{
					"jobs":       es.compressionJobsCache,
					"stale":      true,
					"error_code": "CIRCUIT_BREAKER_OPEN",
					"timestamp":  time.Now().Unix(),
				}
				if err := es.hub.BroadcastIfSubscribed(TypeCompressionUpdate, payload); err != nil {
					log.Error().Err(err).Msg("Failed to broadcast cached compression jobs")
				}
			}
			return
		}
		// Reset circuit after timeout for recovery attempt
		es.failureCount = 0
		es.lastFailureTime = time.Time{}
	}

	// Use v2 API with detailed progress info
	runningJobs, err := es.rpcClient.GetRunningJobs(ctx, true)
	if err != nil {
		es.failureCount++
		es.lastFailureTime = time.Now()

		// Rate limit error events - only broadcast on first failure or every 30 seconds
		if es.failureCount == 1 || time.Since(es.lastErrorEventTime) > 30*time.Second {
			es.lastErrorEventTime = time.Now()
			errorMsg := map[string]interface{}{
				"reason":               "rpc_disconnect",
				"error_code":           "COMPRESSION_JOBS_FAILED",
				"consecutive_failures": es.failureCount,
				"timestamp":            time.Now().Unix(),
			}
			if err := es.hub.BroadcastIfSubscribed(TypeRPCError, errorMsg); err != nil {
				log.Error().Err(err).Msg("Failed to broadcast RPC error event for compression jobs")
			}
		}

		// Send cached data if available
		if len(es.compressionJobsCache) > 0 {
			payload := map[string]interface{}{
				"jobs":       es.compressionJobsCache,
				"stale":      true,
				"error_code": "RPC_DISCONNECT",
				"timestamp":  time.Now().Unix(),
			}
			if err := es.hub.BroadcastIfSubscribed(TypeCompressionUpdate, payload); err != nil {
				log.Error().Err(err).Msg("Failed to broadcast cached compression jobs on error")
			}
		}

		log.Debug().Err(err).Msg("Failed to poll compression jobs from RPC")
		return
	}

	// Clear error counters on success
	es.failureCount = 0
	es.lastFailureTime = time.Time{}

	// Build job list with detailed progress info from v2 API
	jobList := make([]map[string]interface{}, 0, len(runningJobs.Jobs))
	for _, job := range runningJobs.Jobs {
		data := map[string]interface{}{
			"job_id":            job.JobID,
			"status":            job.Status,
			"job_type":          job.JobType,
			"priority":          job.Priority,
			"progress":          job.Progress,
			"phase":             job.Phase,
			"bytes_processed":   job.BytesProcessed,
			"bytes_total":       job.BytesTotal,
			"compression_ratio": job.CurrentRatio,
			"elapsed_seconds":   job.ElapsedSeconds,
			"eta_seconds":       job.ETASeconds,
			"input_path":        job.InputPath,
			"output_path":       job.OutputPath,
			"timestamp":         time.Now().Unix(),
		}
		jobList = append(jobList, data)

		// Broadcast individual job updates
		if err := es.hub.Broadcast(TypeCompressionUpdate, data); err != nil {
			log.Error().Err(err).Str("job_id", job.JobID).Msg("Failed to broadcast compression job update")
		}
	}

	// Also broadcast summary update with all jobs
	summaryData := map[string]interface{}{
		"jobs":          jobList,
		"total_running": runningJobs.TotalRunning,
		"total_pending": runningJobs.TotalPending,
		"total_jobs":    runningJobs.TotalJobs,
		"timestamp":     time.Now().Unix(),
	}
	if err := es.hub.BroadcastIfSubscribed(TypeCompressionUpdate, summaryData); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast compression jobs summary")
	}

	// Update cache
	es.compressionJobsCache = jobList
	es.lastSuccessfulStatusAt = time.Now()
}

// pollAgentStatus periodically polls agent swarm status and broadcasts updates.
func (es *EventSubscriber) pollAgentStatus(ctx context.Context) {
	es.mu.Lock()
	defer es.mu.Unlock()

	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	// Circuit breaker check - prevent cascading failures
	if es.failureCount >= es.circuitBreakerThreshold {
		if time.Since(es.lastFailureTime) < es.circuitBreakerResetAfter {
			// Circuit still open - serve cached data
			if len(es.agentStatusCache) > 0 {
				payload := map[string]interface{}{
					"agents":     es.agentStatusCache,
					"stale":      true,
					"error_code": "CIRCUIT_BREAKER_OPEN",
					"timestamp":  time.Now().Unix(),
				}
				if err := es.hub.BroadcastIfSubscribed(TypeAgentStatus, payload); err != nil {
					log.Error().Err(err).Msg("Failed to broadcast cached agent status")
				}
			}
			return
		}
		// Reset circuit after timeout for recovery attempt
		es.failureCount = 0
		es.lastFailureTime = time.Time{}
	}

	agents, err := es.rpcClient.ListAgents(ctx, &rpc.ListAgentsParams{})
	if err != nil {
		es.failureCount++
		es.lastFailureTime = time.Now()

		// Rate limit error events - only broadcast on first failure or every 30 seconds
		if es.failureCount == 1 || time.Since(es.lastErrorEventTime) > 30*time.Second {
			es.lastErrorEventTime = time.Now()
			errorMsg := map[string]interface{}{
				"reason":               "rpc_disconnect",
				"error_code":           "AGENT_STATUS_FAILED",
				"consecutive_failures": es.failureCount,
				"timestamp":            time.Now().Unix(),
			}
			if err := es.hub.BroadcastIfSubscribed(TypeRPCError, errorMsg); err != nil {
				log.Error().Err(err).Msg("Failed to broadcast RPC error event for agent status")
			}
		}

		// Serve cached data if available
		if len(es.agentStatusCache) > 0 {
			payload := map[string]interface{}{
				"agents":     es.agentStatusCache,
				"stale":      true,
				"error_code": "RPC_DISCONNECT",
				"timestamp":  time.Now().Unix(),
			}
			if err := es.hub.BroadcastIfSubscribed(TypeAgentStatus, payload); err != nil {
				log.Error().Err(err).Msg("Failed to broadcast cached agent status on error")
			}
		}

		log.Debug().Err(err).Msg("Failed to poll agents from RPC")
		return
	}

	// Clear error counters on successful RPC call
	es.failureCount = 0
	es.lastFailureTime = time.Time{}

	// Aggregate agent statistics and build agent map
	agentMap := make(map[string]interface{})
	totalAgents := len(agents)
	activeCount := 0
	idleCount := 0
	errorCount := 0

	for _, agent := range agents {
		// Count by status
		switch agent.Status {
		case "busy":
			activeCount++
		case "idle":
			idleCount++
		case "error":
			errorCount++
		}

		agentData := map[string]interface{}{
			"id":             agent.ID,
			"codename":       agent.Codename,
			"status":         agent.Status,
			"specialization": agent.Specialization,
			"tier":           agent.Tier,
			"last_active":    agent.LastActive.Unix(),
			"timestamp":      time.Now().Unix(),
		}
		// Add metrics if available
		if agent.Metrics != nil {
			agentData["tasks_completed"] = agent.Metrics.TasksCompleted
			agentData["success_rate"] = agent.Metrics.SuccessRate
			agentData["memory_usage"] = agent.Metrics.MemoryUsage
			agentData["average_latency"] = agent.Metrics.AverageLatency
		}
		// Add current task info if available
		if agent.CurrentTask != nil {
			agentData["current_task_id"] = agent.CurrentTask.ID
			agentData["task_type"] = agent.CurrentTask.Type
			agentData["task_progress"] = agent.CurrentTask.Progress
			agentData["task_status"] = agent.CurrentTask.Status
		}
		agentMap[agent.ID] = agentData
	}

	// Build aggregate statistics
	stats := map[string]interface{}{
		"agents":        agentMap,
		"total_agents":  totalAgents,
		"active_agents": activeCount,
		"idle_agents":   idleCount,
		"error_agents":  errorCount,
		"timestamp":     time.Now().Unix(),
	}

	// Broadcast aggregated stats
	if err := es.hub.Broadcast(TypeAgentStatus, stats); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast agent status")
	}

	// Update cache for future graceful degradation
	es.agentStatusCache = agentMap
	es.lastSuccessfulStatusAt = time.Now()
}

// pollSchedulerMetrics polls task scheduler metrics and broadcasts updates.
func (es *EventSubscriber) pollSchedulerMetrics(ctx context.Context) {
	es.mu.Lock()
	defer es.mu.Unlock()

	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	metrics, err := es.rpcClient.GetSchedulerMetrics(ctx)
	if err != nil {
		log.Debug().Err(err).Msg("Failed to poll scheduler metrics from RPC")
		return
	}

	data := map[string]interface{}{
		"queue_size":       metrics.QueueSize,
		"tasks_scheduled":  metrics.TasksScheduled,
		"tasks_dispatched": metrics.TasksDispatched,
		"tasks_completed":  metrics.TasksCompleted,
		"tasks_failed":     metrics.TasksFailed,
		"avg_wait_time_ms": metrics.AvgWaitTimeMs,
		"workers_active":   metrics.WorkersActive,
		"is_running":       metrics.IsRunning,
		"timestamp":        time.Now().Unix(),
	}

	if err := es.hub.BroadcastIfSubscribed(TypeSchedulerMetrics, data); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast scheduler metrics")
	}
}

// pollRecoveryStatus polls agent recovery system status and broadcasts updates.
func (es *EventSubscriber) pollRecoveryStatus(ctx context.Context) {
	es.mu.Lock()
	defer es.mu.Unlock()

	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	status, err := es.rpcClient.GetRecoveryStatus(ctx)
	if err != nil {
		log.Debug().Err(err).Msg("Failed to poll recovery status from RPC")
		return
	}

	data := map[string]interface{}{
		"is_monitoring":          status.IsMonitoring,
		"agents_healthy":         status.AgentsHealthy,
		"agents_degraded":        status.AgentsDegraded,
		"agents_failed":          status.AgentsFailed,
		"total_restarts":         status.TotalRestarts,
		"circuit_breakers_open":  status.CircuitBreakersOpen,
		"dead_letter_queue_size": status.DeadLetterQueueSize,
		"health_scores":          status.HealthScores,
		"timestamp":              time.Now().Unix(),
	}

	if err := es.hub.BroadcastIfSubscribed(TypeRecoveryStatus, data); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast recovery status")
	}

	// Broadcast circuit breaker events if any are open
	if status.CircuitBreakersOpen > 0 {
		circuitData := map[string]interface{}{
			"open_count": status.CircuitBreakersOpen,
			"reason":     "agents_failing_health_checks",
			"timestamp":  time.Now().Unix(),
		}
		if err := es.hub.BroadcastIfSubscribed(TypeCircuitBreakerOpen, circuitData); err != nil {
			log.Error().Err(err).Msg("Failed to broadcast circuit breaker open event")
		}
	}
}

// pollTuningStatus polls self-tuning system status and broadcasts updates.
func (es *EventSubscriber) pollTuningStatus(ctx context.Context) {
	es.mu.Lock()
	defer es.mu.Unlock()

	if es.rpcClient == nil || !es.rpcClient.IsConnected() {
		return
	}

	status, err := es.rpcClient.GetTuningStatus(ctx)
	if err != nil {
		log.Debug().Err(err).Msg("Failed to poll tuning status from RPC")
		return
	}

	data := map[string]interface{}{
		"strategy":           status.Strategy,
		"is_running":         status.IsRunning,
		"parameters_count":   status.ParametersCount,
		"best_score":         status.BestScore,
		"current_score":      status.CurrentScore,
		"sessions_completed": status.SessionsCompleted,
		"current_session":    status.CurrentSession,
		"exploration_rate":   status.ExplorationRate,
		"timestamp":          time.Now().Unix(),
	}

	if err := es.hub.BroadcastIfSubscribed(TypeTuningStatus, data); err != nil {
		log.Error().Err(err).Msg("Failed to broadcast tuning status")
	}
}

// Helper functions removed to satisfy golangci-lint unused checks:
// - countAgentsByStatus: never called in codebase
// - calculateAvgResponseTime: never called in codebase

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

// toStringSlice converts MessageType slice to string slice.
func toStringSlice(types []MessageType) []string {
	result := make([]string, len(types))
	for i, t := range types {
		result[i] = string(t)
	}
	return result
}
