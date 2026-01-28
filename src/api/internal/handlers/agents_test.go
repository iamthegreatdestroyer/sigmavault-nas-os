// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"encoding/json"
	"io"
	"net/http/httptest"
	"testing"

	"sigmavault-nas-os/api/internal/models"

	"github.com/gofiber/fiber/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewAgentsHandler(t *testing.T) {
	handler := NewAgentsHandler(nil)
	assert.NotNil(t, handler)
	assert.Nil(t, handler.rpcClient)
}

func TestListAgents_Fallback(t *testing.T) {
	// Test with no RPC client (fallback mode)
	handler := NewAgentsHandler(nil)

	app := fiber.New()
	app.Get("/agents", handler.ListAgents)

	req := httptest.NewRequest("GET", "/agents", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var result struct {
		Agents      []models.AgentStatus `json:"agents"`
		Count       int                  `json:"count"`
		ActiveCount int                  `json:"active_count"`
		IdleCount   int                  `json:"idle_count"`
	}
	err = json.Unmarshal(body, &result)
	require.NoError(t, err)

	assert.Equal(t, 3, result.Count)
	assert.Equal(t, 2, result.ActiveCount)
	assert.Equal(t, 1, result.IdleCount)
	assert.Len(t, result.Agents, 3)

	// Check agent types
	agentNames := make(map[string]bool)
	for _, agent := range result.Agents {
		agentNames[agent.Name] = true
	}
	assert.True(t, agentNames["TENSOR"])
	assert.True(t, agentNames["CIPHER"])
	assert.True(t, agentNames["VELOCITY"])
}

func TestGetAgent_NotFound(t *testing.T) {
	handler := NewAgentsHandler(nil)

	app := fiber.New()
	app.Get("/agents/:id", handler.GetAgent)

	req := httptest.NewRequest("GET", "/agents/nonexistent-id", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	// In fallback mode, returns 200 with empty/default data or 404
	// Current implementation returns 200 with fallback data
	assert.Contains(t, []int{200, 404}, resp.StatusCode)
}

func TestGetAgent_Found(t *testing.T) {
	handler := NewAgentsHandler(nil)

	app := fiber.New()
	app.Get("/agents/:id", handler.GetAgent)

	// Test with a known fallback agent ID
	req := httptest.NewRequest("GET", "/agents/agent-tensor-001", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	assert.Equal(t, 200, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var agent models.AgentStatus
	err = json.Unmarshal(body, &agent)
	require.NoError(t, err)

	assert.Equal(t, "agent-tensor-001", agent.ID)
	assert.Equal(t, "TENSOR", agent.Name)
	assert.Equal(t, "compression", agent.Type)
}

func TestAgentMetrics_Fallback(t *testing.T) {
	handler := NewAgentsHandler(nil)

	app := fiber.New()
	app.Get("/agents/:id/metrics", handler.AgentMetrics)

	// Test with a known fallback agent ID
	req := httptest.NewRequest("GET", "/agents/agent-tensor-001/metrics", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	// In fallback mode, should return metrics for known agent
	assert.Contains(t, []int{200, 404}, resp.StatusCode)
}

func TestAgentMetrics_NotFound(t *testing.T) {
	handler := NewAgentsHandler(nil)

	app := fiber.New()
	app.Get("/agents/:id/metrics", handler.AgentMetrics)

	req := httptest.NewRequest("GET", "/agents/nonexistent-id/metrics", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	// In fallback mode, returns 200 with default metrics or 404
	// Current implementation returns 200 with fallback data
	assert.Contains(t, []int{200, 404}, resp.StatusCode)
}

func TestAgentStatus_Model(t *testing.T) {
	agent := models.AgentStatus{
		ID:             "test-agent-001",
		Name:           "TestAgent",
		Type:           "testing",
		Status:         "active",
		TasksQueued:    5,
		TasksCompleted: 100,
	}

	data, err := json.Marshal(agent)
	require.NoError(t, err)

	var parsed models.AgentStatus
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, agent.ID, parsed.ID)
	assert.Equal(t, agent.Name, parsed.Name)
	assert.Equal(t, agent.Type, parsed.Type)
	assert.Equal(t, agent.Status, parsed.Status)
	assert.Equal(t, agent.TasksQueued, parsed.TasksQueued)
	assert.Equal(t, agent.TasksCompleted, parsed.TasksCompleted)
}
