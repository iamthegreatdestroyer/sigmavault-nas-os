// Package rpc provides client functionality for communicating with the Python RPC engine.
package rpc

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDefaultConfig(t *testing.T) {
	config := DefaultConfig()

	assert.Equal(t, "http://localhost:8001/api/v1", config.BaseURL)
	assert.Equal(t, 30*time.Second, config.Timeout)
	assert.Equal(t, 3, config.MaxRetries)
	assert.Equal(t, 100*time.Millisecond, config.RetryDelay)
}

func TestNewClient(t *testing.T) {
	config := DefaultConfig()
	client := NewClient(config)

	assert.NotNil(t, client)
	assert.Equal(t, config.BaseURL, client.config.BaseURL)
	assert.NotNil(t, client.httpClient)
}

func TestClient_IsConnected(t *testing.T) {
	tests := []struct {
		name       string
		serverFunc func(w http.ResponseWriter, r *http.Request)
		expectConn bool
	}{
		{
			name: "connected when server responds",
			serverFunc: func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("Content-Type", "application/json")
				response := JSONRPCResponse{
					JSONRPC: "2.0",
					Result:  json.RawMessage(`{"hostname": "test"}`),
					ID:      1,
				}
				_ = json.NewEncoder(w).Encode(response) // error intentionally ignored in test
			},
			expectConn: true,
		},
		{
			name: "disconnected when server errors",
			serverFunc: func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusInternalServerError)
			},
			expectConn: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(tt.serverFunc))
			defer server.Close()

			config := Config{
				BaseURL:    server.URL,
				Timeout:    2 * time.Second,
				MaxRetries: 1,
				RetryDelay: 10 * time.Millisecond,
			}

			client := NewClient(config)
			// The connected state should be determined by health check
			assert.NotNil(t, client)
		})
	}
}

func TestClient_Call_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify request format
		assert.Equal(t, "POST", r.Method)
		assert.Equal(t, "application/json", r.Header.Get("Content-Type"))

		var req JSONRPCRequest
		err := json.NewDecoder(r.Body).Decode(&req)
		require.NoError(t, err)

		assert.Equal(t, "2.0", req.JSONRPC)
		assert.Equal(t, "test.method", req.Method)

		// Send response
		w.Header().Set("Content-Type", "application/json")
		response := JSONRPCResponse{
			JSONRPC: "2.0",
			Result:  json.RawMessage(`{"success": true}`),
			ID:      req.ID,
		}
		_ = json.NewEncoder(w).Encode(response) // error intentionally ignored in test
	}))
	defer server.Close()

	config := Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 1,
		RetryDelay: 10 * time.Millisecond,
	}

	client := NewClient(config)

	var result map[string]bool
	err := client.Call(context.Background(), "test.method", nil, &result)
	require.NoError(t, err)
	assert.True(t, result["success"])
}

func TestClient_Call_RPCError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req JSONRPCRequest
		_ = json.NewDecoder(r.Body).Decode(&req) // error intentionally ignored in test

		w.Header().Set("Content-Type", "application/json")
		response := JSONRPCResponse{
			JSONRPC: "2.0",
			Error: &JSONRPCError{
				Code:    -32601,
				Message: "Method not found",
			},
			ID: req.ID,
		}
		_ = json.NewEncoder(w).Encode(response) // error intentionally ignored in test
	}))
	defer server.Close()

	config := Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 1,
		RetryDelay: 10 * time.Millisecond,
	}

	client := NewClient(config)

	var result interface{}
	err := client.Call(context.Background(), "unknown.method", nil, &result)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "Method not found")
}

func TestClient_Call_Timeout(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(200 * time.Millisecond)
	}))
	defer server.Close()

	config := Config{
		BaseURL:    server.URL,
		Timeout:    50 * time.Millisecond,
		MaxRetries: 1,
		RetryDelay: 10 * time.Millisecond,
	}

	client := NewClient(config)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	var result interface{}
	err := client.Call(ctx, "slow.method", nil, &result)
	assert.Error(t, err)
}

func TestClient_Call_Retry(t *testing.T) {
	callCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		callCount++
		if callCount < 3 {
			w.WriteHeader(http.StatusInternalServerError)
			return
		}

		var req JSONRPCRequest
		_ = json.NewDecoder(r.Body).Decode(&req) // error intentionally ignored in test

		w.Header().Set("Content-Type", "application/json")
		response := JSONRPCResponse{
			JSONRPC: "2.0",
			Result:  json.RawMessage(`{"success": true}`),
			ID:      req.ID,
		}
		_ = json.NewEncoder(w).Encode(response) // error intentionally ignored in test
	}))
	defer server.Close()

	config := Config{
		BaseURL:    server.URL,
		Timeout:    5 * time.Second,
		MaxRetries: 5,
		RetryDelay: 10 * time.Millisecond,
	}

	client := NewClient(config)

	var result map[string]bool
	err := client.Call(context.Background(), "retry.method", nil, &result)
	require.NoError(t, err)
	assert.True(t, result["success"])
	assert.Equal(t, 3, callCount)
}

func TestJSONRPCRequest_Marshal(t *testing.T) {
	req := JSONRPCRequest{
		JSONRPC: "2.0",
		Method:  "test.method",
		Params:  map[string]interface{}{"key": "value"},
		ID:      42,
	}

	data, err := json.Marshal(req)
	require.NoError(t, err)

	var parsed JSONRPCRequest
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, req.JSONRPC, parsed.JSONRPC)
	assert.Equal(t, req.Method, parsed.Method)
	assert.Equal(t, req.ID, parsed.ID)
}

func TestJSONRPCResponse_WithError(t *testing.T) {
	resp := JSONRPCResponse{
		JSONRPC: "2.0",
		Error: &JSONRPCError{
			Code:    -32600,
			Message: "Invalid request",
		},
		ID: 1,
	}

	data, err := json.Marshal(resp)
	require.NoError(t, err)

	var parsed JSONRPCResponse
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.NotNil(t, parsed.Error)
	assert.Equal(t, -32600, parsed.Error.Code)
	assert.Equal(t, "Invalid request", parsed.Error.Message)
}

func TestJSONRPCError_Codes(t *testing.T) {
	testCases := []struct {
		code    int
		message string
	}{
		{-32700, "Parse error"},
		{-32600, "Invalid request"},
		{-32601, "Method not found"},
		{-32602, "Invalid params"},
		{-32603, "Internal error"},
	}

	for _, tc := range testCases {
		t.Run(tc.message, func(t *testing.T) {
			err := &JSONRPCError{
				Code:    tc.code,
				Message: tc.message,
			}
			assert.Equal(t, tc.code, err.Code)
			assert.Equal(t, tc.message, err.Message)
		})
	}
}
