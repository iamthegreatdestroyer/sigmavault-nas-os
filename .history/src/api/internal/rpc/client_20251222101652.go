// Package rpc provides a client for communicating with the Python RPC engine.
// This implements the integration layer between the Go API and the engined service.
package rpc

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2/log"
)

// Config holds configuration for the RPC client.
type Config struct {
	// BaseURL is the base URL of the RPC engine (e.g., "http://localhost:50051")
	BaseURL string

	// Timeout is the default request timeout
	Timeout time.Duration

	// MaxRetries is the maximum number of retry attempts
	MaxRetries int

	// RetryDelay is the initial delay between retries (uses exponential backoff)
	RetryDelay time.Duration

	// MaxIdleConns controls the maximum number of idle connections
	MaxIdleConns int

	// MaxConnsPerHost controls the maximum connections per host
	MaxConnsPerHost int
}

// DefaultConfig returns the default RPC client configuration.
func DefaultConfig() Config {
	return Config{
		BaseURL:         "http://localhost:50051",
		Timeout:         30 * time.Second,
		MaxRetries:      3,
		RetryDelay:      100 * time.Millisecond,
		MaxIdleConns:    100,
		MaxConnsPerHost: 10,
	}
}

// Client provides methods for calling the Python RPC engine.
type Client struct {
	config     Config
	httpClient *http.Client
	mu         sync.RWMutex
	connected  bool
}

// NewClient creates a new RPC client with the given configuration.
func NewClient(cfg Config) *Client {
	transport := &http.Transport{
		MaxIdleConns:        cfg.MaxIdleConns,
		MaxConnsPerHost:     cfg.MaxConnsPerHost,
		IdleConnTimeout:     90 * time.Second,
		DisableCompression:  false,
		DisableKeepAlives:   false,
		ForceAttemptHTTP2:   true,
	}

	return &Client{
		config: cfg,
		httpClient: &http.Client{
			Transport: transport,
			Timeout:   cfg.Timeout,
		},
		connected: false,
	}
}

// JSONRPCRequest represents a JSON-RPC 2.0 request.
type JSONRPCRequest struct {
	JSONRPC string      `json:"jsonrpc"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params,omitempty"`
	ID      int64       `json:"id"`
}

// JSONRPCResponse represents a JSON-RPC 2.0 response.
type JSONRPCResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *JSONRPCError   `json:"error,omitempty"`
	ID      int64           `json:"id"`
}

// JSONRPCError represents a JSON-RPC 2.0 error.
type JSONRPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func (e *JSONRPCError) Error() string {
	return fmt.Sprintf("RPC error %d: %s", e.Code, e.Message)
}

// requestID generates a unique request ID.
var requestIDCounter int64
var requestIDMu sync.Mutex

func nextRequestID() int64 {
	requestIDMu.Lock()
	defer requestIDMu.Unlock()
	requestIDCounter++
	return requestIDCounter
}

// Call makes a JSON-RPC call to the engine.
func (c *Client) Call(ctx context.Context, method string, params interface{}, result interface{}) error {
	req := JSONRPCRequest{
		JSONRPC: "2.0",
		Method:  method,
		Params:  params,
		ID:      nextRequestID(),
	}

	body, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}

	var lastErr error
	for attempt := 0; attempt <= c.config.MaxRetries; attempt++ {
		if attempt > 0 {
			delay := c.config.RetryDelay * time.Duration(1<<uint(attempt-1))
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(delay):
			}
			log.Debugf("Retrying RPC call %s (attempt %d/%d)", method, attempt+1, c.config.MaxRetries)
		}

		resp, err := c.doRequest(ctx, body)
		if err != nil {
			lastErr = err
			continue
		}

		if resp.Error != nil {
			return resp.Error
		}

		if result != nil && resp.Result != nil {
			if err := json.Unmarshal(resp.Result, result); err != nil {
				return fmt.Errorf("unmarshal result: %w", err)
			}
		}

		c.mu.Lock()
		c.connected = true
		c.mu.Unlock()

		return nil
	}

	c.mu.Lock()
	c.connected = false
	c.mu.Unlock()

	return fmt.Errorf("RPC call failed after %d attempts: %w", c.config.MaxRetries+1, lastErr)
}

// doRequest performs the actual HTTP request.
func (c *Client) doRequest(ctx context.Context, body []byte) (*JSONRPCResponse, error) {
	url := c.config.BaseURL + "/rpc"

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, string(respBody))
	}

	var rpcResp JSONRPCResponse
	if err := json.NewDecoder(resp.Body).Decode(&rpcResp); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}

	return &rpcResp, nil
}

// IsConnected returns whether the client is currently connected to the engine.
func (c *Client) IsConnected() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.connected
}

// HealthCheck performs a health check against the RPC engine.
func (c *Client) HealthCheck(ctx context.Context) error {
	var result struct {
		Status string `json:"status"`
	}

	if err := c.Call(ctx, "health.check", nil, &result); err != nil {
		return err
	}

	if result.Status != "healthy" && result.Status != "ok" {
		return fmt.Errorf("unhealthy status: %s", result.Status)
	}

	return nil
}

// Close closes the RPC client and releases resources.
func (c *Client) Close() error {
	c.httpClient.CloseIdleConnections()
	c.mu.Lock()
	c.connected = false
	c.mu.Unlock()
	return nil
}
