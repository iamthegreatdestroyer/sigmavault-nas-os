// Package rpc provides agent-related RPC methods.
package rpc

import (
	"context"
	"time"
)

// Agent represents an AI agent in the swarm.
type Agent struct {
	ID             string         `json:"id"`
	Codename       string         `json:"codename"`
	Tier           int            `json:"tier"`
	Role           string         `json:"role"`
	Status         string         `json:"status"` // idle, busy, error, offline
	Specialization string         `json:"specialization"`
	Description    string         `json:"description,omitempty"`
	Capabilities   []string       `json:"capabilities"`
	CurrentTask    *AgentTask     `json:"current_task,omitempty"`
	Metrics        *AgentMetrics  `json:"metrics,omitempty"`
	Config         map[string]any `json:"config,omitempty"`
	LastActive     time.Time      `json:"last_active"`
	CreatedAt      time.Time      `json:"created_at"`
}

// AgentMetrics contains performance metrics for an agent.
type AgentMetrics struct {
	TasksCompleted      int64     `json:"tasks_completed"`
	TasksFailed         int64     `json:"tasks_failed"`
	AverageLatency      float64   `json:"average_latency_ms"`
	SuccessRate         float64   `json:"success_rate"`
	TotalProcessingTime int64     `json:"total_processing_time_ms"`
	MemoryUsage         uint64    `json:"memory_usage"`
	LastUpdated         time.Time `json:"last_updated"`
}

// AgentTask represents a task assigned to an agent.
type AgentTask struct {
	ID          string         `json:"id"`
	AgentID     string         `json:"agent_id"`
	Type        string         `json:"type"`
	Status      string         `json:"status"` // pending, running, completed, failed, cancelled
	Priority    int            `json:"priority"`
	Progress    float64        `json:"progress"`
	Input       map[string]any `json:"input,omitempty"`
	Output      map[string]any `json:"output,omitempty"`
	Error       string         `json:"error,omitempty"`
	Retries     int            `json:"retries"`
	MaxRetries  int            `json:"max_retries"`
	StartedAt   *time.Time     `json:"started_at,omitempty"`
	CompletedAt *time.Time     `json:"completed_at,omitempty"`
	CreatedAt   time.Time      `json:"created_at"`
}

// SwarmStatus represents the overall swarm status.
type SwarmStatus struct {
	TotalAgents    int         `json:"total_agents"`
	ActiveAgents   int         `json:"active_agents"`
	IdleAgents     int         `json:"idle_agents"`
	BusyAgents     int         `json:"busy_agents"`
	ErrorAgents    int         `json:"error_agents"`
	PendingTasks   int         `json:"pending_tasks"`
	RunningTasks   int         `json:"running_tasks"`
	TaskQueue      int         `json:"task_queue"`
	Throughput     float64     `json:"throughput"` // tasks per minute
	AverageLatency float64     `json:"average_latency_ms"`
	HealthScore    float64     `json:"health_score"` // 0-100
	TierBreakdown  map[int]int `json:"tier_breakdown"`
	LastUpdated    time.Time   `json:"last_updated"`
}

// AgentTier represents a tier of agents.
type AgentTier struct {
	Tier        int      `json:"tier"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	AgentCount  int      `json:"agent_count"`
	Agents      []string `json:"agents"`
}

// TaskResult represents the result of a dispatched task.
type TaskResult struct {
	TaskID      string         `json:"task_id"`
	AgentID     string         `json:"agent_id"`
	Status      string         `json:"status"`
	Progress    float64        `json:"progress"`
	Output      map[string]any `json:"output,omitempty"`
	Error       string         `json:"error,omitempty"`
	Duration    int64          `json:"duration_ms"`
	CompletedAt *time.Time     `json:"completed_at,omitempty"`
}

// MemoryEntry represents an entry in the MNEMONIC memory system.
type MemoryEntry struct {
	ID          string         `json:"id"`
	Type        string         `json:"type"` // episodic, semantic, procedural
	AgentID     string         `json:"agent_id,omitempty"`
	Category    string         `json:"category"`
	Content     map[string]any `json:"content"`
	Embedding   []float32      `json:"embedding,omitempty"`
	Relevance   float64        `json:"relevance,omitempty"`
	AccessCount int            `json:"access_count"`
	CreatedAt   time.Time      `json:"created_at"`
	AccessedAt  time.Time      `json:"accessed_at"`
	ExpiresAt   *time.Time     `json:"expires_at,omitempty"`
}

// ListAgentsParams are parameters for ListAgents.
type ListAgentsParams struct {
	Status string `json:"status,omitempty"`
	Tier   int    `json:"tier,omitempty"`
}

// ListAgents retrieves all agents in the swarm.
func (c *Client) ListAgents(ctx context.Context, params *ListAgentsParams) ([]Agent, error) {
	var result []Agent
	if err := c.Call(ctx, "agents.list", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetAgentParams are parameters for GetAgent.
type GetAgentParams struct {
	ID string `json:"id"`
}

// GetAgent retrieves a specific agent.
func (c *Client) GetAgent(ctx context.Context, id string) (*Agent, error) {
	params := GetAgentParams{ID: id}
	var result Agent
	if err := c.Call(ctx, "agents.get", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetAgentByCodename retrieves an agent by codename.
func (c *Client) GetAgentByCodename(ctx context.Context, codename string) (*Agent, error) {
	params := map[string]string{"codename": codename}
	var result Agent
	if err := c.Call(ctx, "agents.get_by_codename", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetSwarmStatus retrieves the overall swarm status.
func (c *Client) GetSwarmStatus(ctx context.Context) (*SwarmStatus, error) {
	var result SwarmStatus
	if err := c.Call(ctx, "agents.swarm.status", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListTiers retrieves all agent tiers.
func (c *Client) ListTiers(ctx context.Context) ([]AgentTier, error) {
	var result []AgentTier
	if err := c.Call(ctx, "agents.tiers.list", nil, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// DispatchTaskParams are parameters for dispatching a task.
type DispatchTaskParams struct {
	AgentID       string         `json:"agent_id,omitempty"`
	AgentCodename string         `json:"agent_codename,omitempty"`
	TaskType      string         `json:"task_type"`
	Priority      int            `json:"priority,omitempty"`
	Input         map[string]any `json:"input"`
	Async         bool           `json:"async,omitempty"`
	Timeout       int            `json:"timeout_seconds,omitempty"`
	MaxRetries    int            `json:"max_retries,omitempty"`
}

// DispatchTask dispatches a task to an agent.
func (c *Client) DispatchTask(ctx context.Context, params *DispatchTaskParams) (*AgentTask, error) {
	var result AgentTask
	if err := c.Call(ctx, "agents.tasks.dispatch", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetTaskStatusParams are parameters for GetTaskStatus.
type GetTaskStatusParams struct {
	TaskID string `json:"task_id"`
}

// GetTaskStatus retrieves the status of a dispatched task.
func (c *Client) GetTaskStatus(ctx context.Context, taskID string) (*TaskResult, error) {
	params := GetTaskStatusParams{TaskID: taskID}
	var result TaskResult
	if err := c.Call(ctx, "agents.tasks.status", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CancelTaskParams are parameters for CancelTask.
type CancelTaskParams struct {
	TaskID string `json:"task_id"`
}

// CancelTask cancels a running or pending task.
func (c *Client) CancelTask(ctx context.Context, taskID string) error {
	params := CancelTaskParams{TaskID: taskID}
	return c.Call(ctx, "agents.tasks.cancel", params, nil)
}

// ListTasksParams are parameters for ListTasks.
type ListTasksParams struct {
	AgentID string `json:"agent_id,omitempty"`
	Status  string `json:"status,omitempty"`
	Limit   int    `json:"limit,omitempty"`
	Offset  int    `json:"offset,omitempty"`
}

// ListTasks retrieves tasks.
func (c *Client) ListTasks(ctx context.Context, params *ListTasksParams) ([]AgentTask, error) {
	var result []AgentTask
	if err := c.Call(ctx, "agents.tasks.list", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetAgentMetrics retrieves metrics for a specific agent.
func (c *Client) GetAgentMetrics(ctx context.Context, agentID string) (*AgentMetrics, error) {
	params := GetAgentParams{ID: agentID}
	var result AgentMetrics
	if err := c.Call(ctx, "agents.metrics", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// MemoryQueryParams are parameters for querying the memory system.
type MemoryQueryParams struct {
	Query    string  `json:"query"`
	Type     string  `json:"type,omitempty"` // episodic, semantic, procedural
	AgentID  string  `json:"agent_id,omitempty"`
	Category string  `json:"category,omitempty"`
	Limit    int     `json:"limit,omitempty"`
	MinScore float64 `json:"min_score,omitempty"`
}

// QueryMemory performs a semantic search on the MNEMONIC memory system.
func (c *Client) QueryMemory(ctx context.Context, params *MemoryQueryParams) ([]MemoryEntry, error) {
	var result []MemoryEntry
	if err := c.Call(ctx, "agents.memory.query", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// StoreMemoryParams are parameters for storing a memory entry.
type StoreMemoryParams struct {
	Type     string         `json:"type"`
	AgentID  string         `json:"agent_id,omitempty"`
	Category string         `json:"category"`
	Content  map[string]any `json:"content"`
	TTLHours int            `json:"ttl_hours,omitempty"`
}

// StoreMemory stores an entry in the MNEMONIC memory system.
func (c *Client) StoreMemory(ctx context.Context, params *StoreMemoryParams) (*MemoryEntry, error) {
	var result MemoryEntry
	if err := c.Call(ctx, "agents.memory.store", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CollaborationRequest represents a request for agent collaboration.
type CollaborationRequest struct {
	ID           string         `json:"id"`
	Initiator    string         `json:"initiator"` // Agent codename
	Participants []string       `json:"participants"`
	TaskType     string         `json:"task_type"`
	Input        map[string]any `json:"input"`
	Status       string         `json:"status"`
	Result       map[string]any `json:"result,omitempty"`
	CreatedAt    time.Time      `json:"created_at"`
	CompletedAt  *time.Time     `json:"completed_at,omitempty"`
}

// InitiateCollaborationParams are parameters for initiating agent collaboration.
type InitiateCollaborationParams struct {
	Initiator    string         `json:"initiator"`
	Participants []string       `json:"participants"`
	TaskType     string         `json:"task_type"`
	Input        map[string]any `json:"input"`
}

// InitiateCollaboration starts a multi-agent collaboration.
func (c *Client) InitiateCollaboration(ctx context.Context, params *InitiateCollaborationParams) (*CollaborationRequest, error) {
	var result CollaborationRequest
	if err := c.Call(ctx, "agents.collaborate", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetCollaborationStatus retrieves the status of a collaboration.
func (c *Client) GetCollaborationStatus(ctx context.Context, collabID string) (*CollaborationRequest, error) {
	params := map[string]string{"id": collabID}
	var result CollaborationRequest
	if err := c.Call(ctx, "agents.collaborate.status", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// SchedulerMetrics contains metrics from the task scheduler.
type SchedulerMetrics struct {
	QueueSize       int     `json:"queue_size"`
	TasksScheduled  int     `json:"tasks_scheduled"`
	TasksDispatched int     `json:"tasks_dispatched"`
	TasksCompleted  int     `json:"tasks_completed"`
	TasksFailed     int     `json:"tasks_failed"`
	AvgWaitTimeMs   float64 `json:"avg_wait_time_ms"`
	WorkersActive   int     `json:"workers_active"`
	IsRunning       bool    `json:"is_running"`
}

// GetSchedulerMetrics retrieves metrics from the task scheduler.
func (c *Client) GetSchedulerMetrics(ctx context.Context) (*SchedulerMetrics, error) {
	var result SchedulerMetrics
	if err := c.Call(ctx, "agents.scheduler.metrics", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// RecoveryStatus contains status from the agent recovery system.
type RecoveryStatus struct {
	IsMonitoring        bool               `json:"is_monitoring"`
	AgentsHealthy       int                `json:"agents_healthy"`
	AgentsDegraded      int                `json:"agents_degraded"`
	AgentsFailed        int                `json:"agents_failed"`
	TotalRestarts       int                `json:"total_restarts"`
	CircuitBreakersOpen int                `json:"circuit_breakers_open"`
	DeadLetterQueueSize int                `json:"dead_letter_queue_size"`
	HealthScores        map[string]float64 `json:"health_scores,omitempty"`
}

// GetRecoveryStatus retrieves status from the agent recovery system.
func (c *Client) GetRecoveryStatus(ctx context.Context) (*RecoveryStatus, error) {
	var result RecoveryStatus
	if err := c.Call(ctx, "agents.recovery.status", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// EventStatus contains status from the event emitter system.
type EventStatus struct {
	EventsEmitted   int  `json:"events_emitted"`
	EventsProcessed int  `json:"events_processed"`
	EventsDropped   int  `json:"events_dropped"`
	HandlersCalled  int  `json:"handlers_called"`
	HandlerErrors   int  `json:"handler_errors"`
	IsRunning       bool `json:"is_running"`
}

// GetEventStatus retrieves status from the event emitter system.
func (c *Client) GetEventStatus(ctx context.Context) (*EventStatus, error) {
	var result EventStatus
	if err := c.Call(ctx, "agents.events.status", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// MemoryStatus contains status from the MNEMONIC memory system.
type MemoryStatus struct {
	TotalMemories     int            `json:"total_memories"`
	TotalStored       int            `json:"total_stored"`
	TotalForgotten    int            `json:"total_forgotten"`
	TotalRetrieved    int            `json:"total_retrieved"`
	ConsolidationRuns int            `json:"consolidation_runs"`
	ByType            map[string]int `json:"by_type,omitempty"`
	IsRunning         bool           `json:"is_running"`
}

// GetMemoryStatus retrieves status from the MNEMONIC memory system.
func (c *Client) GetMemoryStatus(ctx context.Context) (*MemoryStatus, error) {
	var result MemoryStatus
	if err := c.Call(ctx, "agents.memory.status", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// TuningStatus contains status from the self-tuning system.
type TuningStatus struct {
	Strategy          string  `json:"strategy"`
	IsRunning         bool    `json:"is_running"`
	ParametersCount   int     `json:"parameters_count"`
	BestScore         float64 `json:"best_score"`
	CurrentScore      float64 `json:"current_score"`
	SessionsCompleted int     `json:"sessions_completed"`
	CurrentSession    *string `json:"current_session,omitempty"`
	ExplorationRate   float64 `json:"exploration_rate"`
}

// GetTuningStatus retrieves status from the self-tuning system.
func (c *Client) GetTuningStatus(ctx context.Context) (*TuningStatus, error) {
	var result TuningStatus
	if err := c.Call(ctx, "agents.tuning.status", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}
