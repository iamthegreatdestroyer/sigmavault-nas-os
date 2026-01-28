// Package rpc provides tests for agent-related RPC methods.
package rpc

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestAgent_JSONSerialization(t *testing.T) {
	now := time.Now()
	agent := Agent{
		ID:             "agent-001",
		Codename:       "TENSOR",
		Tier:           1,
		Role:           "ML Specialist",
		Status:         "idle",
		Specialization: "machine-learning",
		Description:    "Machine Learning & Deep Neural Networks",
		Capabilities:   []string{"training", "inference", "optimization"},
		LastActive:     now,
		CreatedAt:      now,
	}

	data, err := json.Marshal(agent)
	require.NoError(t, err)

	var parsed Agent
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, agent.ID, parsed.ID)
	assert.Equal(t, agent.Codename, parsed.Codename)
	assert.Equal(t, agent.Tier, parsed.Tier)
	assert.Equal(t, agent.Role, parsed.Role)
	assert.Equal(t, agent.Status, parsed.Status)
	assert.Equal(t, agent.Specialization, parsed.Specialization)
	assert.Equal(t, agent.Description, parsed.Description)
	assert.Equal(t, agent.Capabilities, parsed.Capabilities)
}

func TestAgentMetrics_JSONSerialization(t *testing.T) {
	metrics := AgentMetrics{
		TasksCompleted:      100,
		TasksFailed:         5,
		AverageLatency:      45.5,
		SuccessRate:         0.95,
		TotalProcessingTime: 5000,
		MemoryUsage:         1024 * 1024 * 100,
		LastUpdated:         time.Now(),
	}

	data, err := json.Marshal(metrics)
	require.NoError(t, err)

	var parsed AgentMetrics
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, metrics.TasksCompleted, parsed.TasksCompleted)
	assert.Equal(t, metrics.TasksFailed, parsed.TasksFailed)
	assert.Equal(t, metrics.AverageLatency, parsed.AverageLatency)
	assert.Equal(t, metrics.SuccessRate, parsed.SuccessRate)
}

func TestAgentTask_JSONSerialization(t *testing.T) {
	now := time.Now()
	task := AgentTask{
		ID:         "task-001",
		AgentID:    "agent-001",
		Type:       "compression",
		Status:     "running",
		Priority:   1,
		Progress:   0.5,
		Input:      map[string]any{"file": "test.dat"},
		Retries:    0,
		MaxRetries: 3,
		StartedAt:  &now,
		CreatedAt:  now,
	}

	data, err := json.Marshal(task)
	require.NoError(t, err)

	var parsed AgentTask
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, task.ID, parsed.ID)
	assert.Equal(t, task.AgentID, parsed.AgentID)
	assert.Equal(t, task.Type, parsed.Type)
	assert.Equal(t, task.Status, parsed.Status)
	assert.Equal(t, task.Priority, parsed.Priority)
	assert.Equal(t, task.Progress, parsed.Progress)
}

func TestSwarmStatus_JSONSerialization(t *testing.T) {
	status := SwarmStatus{
		TotalAgents:    40,
		ActiveAgents:   38,
		IdleAgents:     30,
		BusyAgents:     8,
		ErrorAgents:    2,
		PendingTasks:   5,
		RunningTasks:   10,
		TaskQueue:      15,
		Throughput:     120.5,
		AverageLatency: 25.0,
		HealthScore:    95.0,
		TierBreakdown:  map[int]int{1: 10, 2: 20, 3: 10},
		LastUpdated:    time.Now(),
	}

	data, err := json.Marshal(status)
	require.NoError(t, err)

	var parsed SwarmStatus
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, status.TotalAgents, parsed.TotalAgents)
	assert.Equal(t, status.ActiveAgents, parsed.ActiveAgents)
	assert.Equal(t, status.IdleAgents, parsed.IdleAgents)
	assert.Equal(t, status.BusyAgents, parsed.BusyAgents)
	assert.Equal(t, status.ErrorAgents, parsed.ErrorAgents)
	assert.Equal(t, status.Throughput, parsed.Throughput)
	assert.Equal(t, status.HealthScore, parsed.HealthScore)
	assert.Equal(t, 3, len(parsed.TierBreakdown))
}

func TestAgentTier_JSONSerialization(t *testing.T) {
	tier := AgentTier{
		Tier:        1,
		Name:        "Core",
		Description: "Core foundational agents",
		AgentCount:  10,
		Agents:      []string{"TENSOR", "CIPHER", "VELOCITY", "AXIOM", "APEX"},
	}

	data, err := json.Marshal(tier)
	require.NoError(t, err)

	var parsed AgentTier
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, tier.Tier, parsed.Tier)
	assert.Equal(t, tier.Name, parsed.Name)
	assert.Equal(t, tier.Description, parsed.Description)
	assert.Equal(t, tier.AgentCount, parsed.AgentCount)
	assert.Equal(t, tier.Agents, parsed.Agents)
}

func TestTaskResult_JSONSerialization(t *testing.T) {
	now := time.Now()
	result := TaskResult{
		TaskID:      "task-001",
		AgentID:     "agent-001",
		Status:      "completed",
		Progress:    1.0,
		Output:      map[string]any{"compressed_size": 1024},
		Duration:    500,
		CompletedAt: &now,
	}

	data, err := json.Marshal(result)
	require.NoError(t, err)

	var parsed TaskResult
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, result.TaskID, parsed.TaskID)
	assert.Equal(t, result.AgentID, parsed.AgentID)
	assert.Equal(t, result.Status, parsed.Status)
	assert.Equal(t, result.Progress, parsed.Progress)
	assert.Equal(t, result.Duration, parsed.Duration)
}

func TestMemoryEntry_JSONSerialization(t *testing.T) {
	entry := MemoryEntry{
		ID:       "mem-001",
		Type:     "episodic",
		AgentID:  "agent-001",
		Category: "task-history",
		Content:  map[string]any{"action": "compress", "result": "success"},
	}

	data, err := json.Marshal(entry)
	require.NoError(t, err)

	var parsed MemoryEntry
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, entry.ID, parsed.ID)
	assert.Equal(t, entry.Type, parsed.Type)
	assert.Equal(t, entry.AgentID, parsed.AgentID)
	assert.Equal(t, entry.Category, parsed.Category)
}

func TestAgentStatus_Values(t *testing.T) {
	validStatuses := []string{"idle", "busy", "error", "offline"}

	for _, status := range validStatuses {
		t.Run(status, func(t *testing.T) {
			agent := Agent{
				ID:     "test",
				Status: status,
			}
			assert.Equal(t, status, agent.Status)
		})
	}
}

func TestTaskStatus_Values(t *testing.T) {
	validStatuses := []string{"pending", "running", "completed", "failed", "cancelled"}

	for _, status := range validStatuses {
		t.Run(status, func(t *testing.T) {
			task := AgentTask{
				ID:     "test",
				Status: status,
			}
			assert.Equal(t, status, task.Status)
		})
	}
}

func TestMemoryType_Values(t *testing.T) {
	validTypes := []string{"episodic", "semantic", "procedural"}

	for _, memType := range validTypes {
		t.Run(memType, func(t *testing.T) {
			entry := MemoryEntry{
				ID:   "test",
				Type: memType,
			}
			assert.Equal(t, memType, entry.Type)
		})
	}
}

func TestSwarmStatus_HealthScore_Range(t *testing.T) {
	testCases := []struct {
		name        string
		healthScore float64
		isValid     bool
	}{
		{"perfect health", 100.0, true},
		{"good health", 95.0, true},
		{"moderate health", 75.0, true},
		{"low health", 50.0, true},
		{"critical health", 25.0, true},
		{"zero health", 0.0, true},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			status := SwarmStatus{
				HealthScore: tc.healthScore,
			}

			if tc.isValid {
				assert.GreaterOrEqual(t, status.HealthScore, 0.0)
				assert.LessOrEqual(t, status.HealthScore, 100.0)
			}
		})
	}
}

func TestAgentWithTask(t *testing.T) {
	now := time.Now()
	task := &AgentTask{
		ID:        "task-001",
		AgentID:   "agent-001",
		Type:      "inference",
		Status:    "running",
		Progress:  0.75,
		StartedAt: &now,
	}

	agent := Agent{
		ID:          "agent-001",
		Codename:    "TENSOR",
		Status:      "busy",
		CurrentTask: task,
	}

	assert.NotNil(t, agent.CurrentTask)
	assert.Equal(t, "task-001", agent.CurrentTask.ID)
	assert.Equal(t, "running", agent.CurrentTask.Status)
	assert.Equal(t, 0.75, agent.CurrentTask.Progress)
}

func TestAgentWithMetrics(t *testing.T) {
	metrics := &AgentMetrics{
		TasksCompleted: 500,
		TasksFailed:    10,
		SuccessRate:    0.98,
		AverageLatency: 15.5,
	}

	agent := Agent{
		ID:       "agent-001",
		Codename: "VELOCITY",
		Metrics:  metrics,
	}

	assert.NotNil(t, agent.Metrics)
	assert.Equal(t, int64(500), agent.Metrics.TasksCompleted)
	assert.Equal(t, 0.98, agent.Metrics.SuccessRate)
}
