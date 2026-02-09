package websocket

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

// MockRPCClient implements a mock RPC client for testing circuit breaker behavior.
type MockRPCClient struct {
	mu              sync.Mutex
	shouldFail      bool
	failCount       int
	maxFails        int
	callCount       int
	isConnected     bool
	latency         time.Duration
	failureError    error
	successResponse interface{}
}

// NewMockRPCClient creates a new mock RPC client with configurable behavior.
func NewMockRPCClient() *MockRPCClient {
	return &MockRPCClient{
		isConnected:  true,
		failureError: errors.New("mock RPC connection failed"),
	}
}

// SetFailureMode configures the mock to fail for a specific number of calls.
func (m *MockRPCClient) SetFailureMode(fails int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.shouldFail = fails > 0
	m.maxFails = fails
	m.failCount = 0
}

// SetLatency sets artificial latency for simulating slow responses.
func (m *MockRPCClient) SetLatency(d time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.latency = d
}

// SetConnected sets the connection status.
func (m *MockRPCClient) SetConnected(connected bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.isConnected = connected
}

// IsConnected returns the mock connection status.
func (m *MockRPCClient) IsConnected() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.isConnected
}

// Call simulates an RPC call with configurable failure behavior.
func (m *MockRPCClient) Call() (interface{}, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.callCount++

	if m.latency > 0 {
		m.mu.Unlock()
		time.Sleep(m.latency)
		m.mu.Lock()
	}

	if m.shouldFail {
		if m.maxFails > 0 && m.failCount >= m.maxFails {
			m.shouldFail = false
			return m.successResponse, nil
		}
		m.failCount++
		return nil, m.failureError
	}

	return m.successResponse, nil
}

// GetCallCount returns the number of calls made.
func (m *MockRPCClient) GetCallCount() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.callCount
}

// ResetCallCount resets the call counter.
func (m *MockRPCClient) ResetCallCount() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.callCount = 0
}

// CircuitBreaker represents a generic circuit breaker for testing.
type CircuitBreaker struct {
	mu                      sync.Mutex
	failureCount            int
	lastFailureTime         time.Time
	threshold               int
	resetAfter              time.Duration
	state                   CircuitState
	cache                   interface{}
	onStateChange           func(from, to CircuitState)
	halfOpenSuccessRequired int
	halfOpenSuccessCount    int
}

// CircuitState represents the state of the circuit breaker.
type CircuitState int

const (
	StateClosed CircuitState = iota
	StateOpen
	StateHalfOpen
)

func (s CircuitState) String() string {
	switch s {
	case StateClosed:
		return "CLOSED"
	case StateOpen:
		return "OPEN"
	case StateHalfOpen:
		return "HALF_OPEN"
	default:
		return "UNKNOWN"
	}
}

// NewCircuitBreaker creates a new circuit breaker with configurable parameters.
func NewCircuitBreaker(threshold int, resetAfter time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		threshold:               threshold,
		resetAfter:              resetAfter,
		state:                   StateClosed,
		halfOpenSuccessRequired: 1,
	}
}

// SetOnStateChange sets a callback for state changes.
func (cb *CircuitBreaker) SetOnStateChange(fn func(from, to CircuitState)) {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	cb.onStateChange = fn
}

// SetCache stores cached data for fallback.
func (cb *CircuitBreaker) SetCache(data interface{}) {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	cb.cache = data
}

// GetCache returns cached data.
func (cb *CircuitBreaker) GetCache() interface{} {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	return cb.cache
}

// GetState returns the current circuit state.
func (cb *CircuitBreaker) GetState() CircuitState {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	return cb.state
}

// GetFailureCount returns the current failure count.
func (cb *CircuitBreaker) GetFailureCount() int {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	return cb.failureCount
}

// Execute runs the given function through the circuit breaker.
func (cb *CircuitBreaker) Execute(fn func() (interface{}, error)) (interface{}, error, bool) {
	cb.mu.Lock()

	if cb.state == StateOpen {
		if time.Since(cb.lastFailureTime) >= cb.resetAfter {
			oldState := cb.state
			cb.state = StateHalfOpen
			cb.halfOpenSuccessCount = 0
			if cb.onStateChange != nil {
				cb.onStateChange(oldState, cb.state)
			}
		} else {
			cache := cb.cache
			cb.mu.Unlock()
			return cache, nil, true
		}
	}

	cb.mu.Unlock()

	result, err := fn()

	cb.mu.Lock()
	defer cb.mu.Unlock()

	if err != nil {
		cb.failureCount++
		cb.lastFailureTime = time.Now()

		if cb.failureCount >= cb.threshold && cb.state == StateClosed {
			oldState := cb.state
			cb.state = StateOpen
			if cb.onStateChange != nil {
				cb.onStateChange(oldState, cb.state)
			}
		}

		if cb.state == StateHalfOpen {
			oldState := cb.state
			cb.state = StateOpen
			cb.halfOpenSuccessCount = 0
			if cb.onStateChange != nil {
				cb.onStateChange(oldState, cb.state)
			}
		}

		return cb.cache, err, cb.cache != nil
	}

	if cb.state == StateHalfOpen {
		cb.halfOpenSuccessCount++
		if cb.halfOpenSuccessCount >= cb.halfOpenSuccessRequired {
			oldState := cb.state
			cb.state = StateClosed
			cb.failureCount = 0
			cb.halfOpenSuccessCount = 0
			if cb.onStateChange != nil {
				cb.onStateChange(oldState, cb.state)
			}
		}
	} else if cb.state == StateClosed {
		cb.failureCount = 0
	}

	return result, nil, false
}

// TestCircuitBreakerStateTransitions verifies correct state machine behavior.
func TestCircuitBreakerStateTransitions(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		threshold      int
		resetAfter     time.Duration
		operations     []string
		expectedStates []CircuitState
		description    string
	}{
		{
			name:           "Closed_to_Open_on_threshold_failures",
			threshold:      3,
			resetAfter:     100 * time.Millisecond,
			operations:     []string{"fail", "fail", "fail"},
			expectedStates: []CircuitState{StateClosed, StateClosed, StateOpen},
			description:    "Circuit should open after threshold consecutive failures",
		},
		{
			name:           "Stays_closed_with_intermittent_success",
			threshold:      3,
			resetAfter:     100 * time.Millisecond,
			operations:     []string{"fail", "success", "fail", "success"},
			expectedStates: []CircuitState{StateClosed, StateClosed, StateClosed, StateClosed},
			description:    "Circuit stays closed if failures don't exceed threshold",
		},
		{
			name:           "Open_to_HalfOpen_to_Closed_on_recovery",
			threshold:      2,
			resetAfter:     50 * time.Millisecond,
			operations:     []string{"fail", "fail", "wait_and_success"},
			expectedStates: []CircuitState{StateClosed, StateOpen, StateClosed},
			description:    "Circuit transitions through half-open on recovery",
		},
		{
			name:           "HalfOpen_to_Open_on_failure",
			threshold:      2,
			resetAfter:     50 * time.Millisecond,
			operations:     []string{"fail", "fail", "wait_and_fail"},
			expectedStates: []CircuitState{StateClosed, StateOpen, StateOpen},
			description:    "Circuit reopens if half-open test fails",
		},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			cb := NewCircuitBreaker(tc.threshold, tc.resetAfter)
			mock := NewMockRPCClient()

			actualStates := make([]CircuitState, 0)

			for _, op := range tc.operations {
				switch op {
				case "fail":
					mock.SetFailureMode(1)
					_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
						return mock.Call()
					})
					actualStates = append(actualStates, cb.GetState())

				case "success":
					mock.SetFailureMode(0)
					_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
						return mock.Call()
					})
					actualStates = append(actualStates, cb.GetState())

				case "wait":
					time.Sleep(tc.resetAfter + 10*time.Millisecond)
					mock.SetFailureMode(0)
					actualStates = append(actualStates, cb.GetState())

				case "wait_and_success":
					time.Sleep(tc.resetAfter + 10*time.Millisecond)
					mock.SetFailureMode(0)
					_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
						return mock.Call()
					})
					actualStates = append(actualStates, cb.GetState())

				case "wait_and_fail":
					time.Sleep(tc.resetAfter + 10*time.Millisecond)
					mock.SetFailureMode(1)
					_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
						return mock.Call()
					})
					actualStates = append(actualStates, cb.GetState())
				}
			}

			if len(actualStates) != len(tc.expectedStates) {
				t.Errorf("Expected %d states, got %d", len(tc.expectedStates), len(actualStates))
				return
			}

			for i, expected := range tc.expectedStates {
				if actualStates[i] != expected {
					t.Errorf("State %d: expected %s, got %s", i, expected, actualStates[i])
				}
			}

			t.Logf("PASS: %s - %s", tc.name, tc.description)
		})
	}
}

// TestCircuitBreakerCachedDataFallback verifies cached data is served when circuit is open.
func TestCircuitBreakerCachedDataFallback(t *testing.T) {
	t.Parallel()

	cb := NewCircuitBreaker(3, 1*time.Second)
	mock := NewMockRPCClient()

	cachedData := map[string]interface{}{
		"status":    "healthy",
		"cached":    true,
		"timestamp": time.Now().Unix(),
	}
	cb.SetCache(cachedData)

	mock.SetFailureMode(10)
	for i := 0; i < 3; i++ {
		_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
			return mock.Call()
		})
	}

	if cb.GetState() != StateOpen {
		t.Fatalf("Expected circuit to be OPEN, got %s", cb.GetState())
	}

	result, err, fromCache := cb.Execute(func() (interface{}, error) {
		return mock.Call()
	})

	if !fromCache {
		t.Error("Expected result to come from cache")
	}

	if err != nil {
		t.Errorf("Expected no error when serving cached data, got: %v", err)
	}

	resultMap, ok := result.(map[string]interface{})
	if !ok {
		t.Error("Expected cached map result")
	} else {
		if resultMap["cached"] != true {
			t.Error("Expected cached flag in result")
		}
	}

	initialCalls := mock.GetCallCount()
	_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
		return mock.Call()
	})
	if mock.GetCallCount() != initialCalls {
		t.Error("Mock should not be called when circuit is open")
	}

	t.Log("PASS: Cached data is correctly served when circuit is open")
}

// TestCircuitBreakerRecoveryAfterCooldown verifies recovery after reset period.
func TestCircuitBreakerRecoveryAfterCooldown(t *testing.T) {
	t.Parallel()

	resetAfter := 100 * time.Millisecond
	cb := NewCircuitBreaker(2, resetAfter)
	mock := NewMockRPCClient()

	mock.SetFailureMode(5)
	for i := 0; i < 2; i++ {
		_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
			return mock.Call()
		})
	}

	if cb.GetState() != StateOpen {
		t.Fatalf("Expected OPEN state, got %s", cb.GetState())
	}

	time.Sleep(resetAfter + 20*time.Millisecond)

	mock.SetFailureMode(0)
	mock.successResponse = "recovered"

	result, err, fromCache := cb.Execute(func() (interface{}, error) {
		return mock.Call()
	})

	if err != nil {
		t.Errorf("Expected success, got error: %v", err)
	}

	if fromCache {
		t.Error("Expected fresh data, not cached")
	}

	if cb.GetState() != StateClosed {
		t.Errorf("Expected CLOSED state after recovery, got %s", cb.GetState())
	}

	if result != "recovered" {
		t.Errorf("Expected 'recovered' result, got %v", result)
	}

	t.Log("PASS: Circuit correctly recovers after cooldown period")
}

// TestCircuitBreakerConcurrency tests thread-safety of circuit breaker.
func TestCircuitBreakerConcurrency(t *testing.T) {
	t.Parallel()

	cb := NewCircuitBreaker(10, 100*time.Millisecond)
	mock := NewMockRPCClient()
	mock.SetFailureMode(0)

	cb.SetCache("cached_value")

	var wg sync.WaitGroup
	const numGoroutines = 50
	const callsPerGoroutine = 100

	errs := make([]error, 0)
	errMu := sync.Mutex{}

	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < callsPerGoroutine; j++ {
				_, err, _ := cb.Execute(func() (interface{}, error) {
					return mock.Call()
				})
				if err != nil {
					errMu.Lock()
					errs = append(errs, err)
					errMu.Unlock()
				}
			}
		}()
	}

	wg.Wait()

	if len(errs) > 0 {
		t.Errorf("Got %d unexpected errors in concurrent execution", len(errs))
	}

	if mock.GetCallCount() != numGoroutines*callsPerGoroutine {
		t.Errorf("Expected %d calls, got %d", numGoroutines*callsPerGoroutine, mock.GetCallCount())
	}

	t.Logf("PASS: Circuit breaker is thread-safe: %d concurrent calls", numGoroutines*callsPerGoroutine)
}

// TestCircuitBreakerTimeoutSimulation tests behavior with slow RPC calls.
func TestCircuitBreakerTimeoutSimulation(t *testing.T) {
	t.Parallel()

	cb := NewCircuitBreaker(3, 200*time.Millisecond)
	mock := NewMockRPCClient()

	mock.SetLatency(50 * time.Millisecond)
	mock.SetFailureMode(3)

	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	start := time.Now()
	failCount := 0

	for i := 0; i < 3; i++ {
		select {
		case <-ctx.Done():
			t.Fatal("Context cancelled prematurely")
		default:
			_, err, _ := cb.Execute(func() (interface{}, error) {
				return mock.Call()
			})
			if err != nil {
				failCount++
			}
		}
	}

	elapsed := time.Since(start)

	if cb.GetState() != StateOpen {
		t.Errorf("Expected OPEN state after 3 failures, got %s", cb.GetState())
	}

	if failCount != 3 {
		t.Errorf("Expected 3 failures, got %d", failCount)
	}

	if elapsed < 150*time.Millisecond {
		t.Errorf("Expected at least 150ms elapsed, got %v", elapsed)
	}

	t.Logf("PASS: Timeout simulation completed in %v with %d failures", elapsed, failCount)
}

// TestCircuitBreakerErrorTypes tests different error scenarios.
func TestCircuitBreakerErrorTypes(t *testing.T) {
	t.Parallel()

	errorTypes := []struct {
		name        string
		err         error
		shouldTrip  bool
		description string
	}{
		{
			name:        "Connection_refused",
			err:         errors.New("connection refused"),
			shouldTrip:  true,
			description: "Connection refused should increment failure count",
		},
		{
			name:        "Timeout_error",
			err:         context.DeadlineExceeded,
			shouldTrip:  true,
			description: "Timeout errors should increment failure count",
		},
		{
			name:        "Service_unavailable",
			err:         errors.New("service unavailable: 503"),
			shouldTrip:  true,
			description: "Service unavailable should increment failure count",
		},
		{
			name:        "RPC_error",
			err:         errors.New("RPC error -32603: Internal error"),
			shouldTrip:  true,
			description: "RPC internal errors should increment failure count",
		},
	}

	for _, tc := range errorTypes {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			cb := NewCircuitBreaker(2, 100*time.Millisecond)
			initialFailures := cb.GetFailureCount()

			_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
				return nil, tc.err
			})

			newFailures := cb.GetFailureCount()

			if tc.shouldTrip && newFailures <= initialFailures {
				t.Errorf("Expected failure count to increase for %s", tc.name)
			}

			t.Logf("PASS: %s - %s", tc.name, tc.description)
		})
	}
}

// TestCircuitBreakerMetrics tests failure count tracking.
func TestCircuitBreakerMetrics(t *testing.T) {
	t.Parallel()

	cb := NewCircuitBreaker(5, 100*time.Millisecond)
	mock := NewMockRPCClient()

	if cb.GetFailureCount() != 0 {
		t.Error("Initial failure count should be 0")
	}

	if cb.GetState() != StateClosed {
		t.Error("Initial state should be CLOSED")
	}

	mock.SetFailureMode(3)
	for i := 0; i < 3; i++ {
		_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
			return mock.Call()
		})
	}

	if cb.GetFailureCount() != 3 {
		t.Errorf("Expected 3 failures, got %d", cb.GetFailureCount())
	}

	mock.SetFailureMode(0)
	_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
		return mock.Call()
	})

	if cb.GetFailureCount() != 0 {
		t.Errorf("Expected 0 failures after success, got %d", cb.GetFailureCount())
	}

	t.Log("PASS: Metrics tracking works correctly")
}

// TestCircuitBreakerEdgeCases tests boundary conditions.
func TestCircuitBreakerEdgeCases(t *testing.T) {
	t.Parallel()

	t.Run("Threshold_of_1", func(t *testing.T) {
		cb := NewCircuitBreaker(1, 50*time.Millisecond)
		_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
			return nil, errors.New("single failure")
		})
		if cb.GetState() != StateOpen {
			t.Error("Circuit should open after single failure with threshold=1")
		}
	})

	t.Run("Zero_reset_time", func(t *testing.T) {
		cb := NewCircuitBreaker(2, 0)
		mock := NewMockRPCClient()
		mock.SetFailureMode(2)

		_, _, _ = cb.Execute(func() (interface{}, error) { return mock.Call() }) // intentionally ignore result in test
		_, _, _ = cb.Execute(func() (interface{}, error) { return mock.Call() }) // intentionally ignore result in test

		mock.SetFailureMode(0)
		_, _, _ = cb.Execute(func() (interface{}, error) { return mock.Call() }) // intentionally ignore result in test

		if cb.GetState() != StateClosed {
			t.Errorf("Expected CLOSED with zero reset, got %s", cb.GetState())
		}
	})

	t.Run("Empty_cache_handling", func(t *testing.T) {
		cb := NewCircuitBreaker(1, 100*time.Millisecond)

		_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in test
			return nil, errors.New("failure")
		})

		result, err, fromCache := cb.Execute(func() (interface{}, error) {
			return "should_not_see", nil
		})
		_ = err // error intentionally ignored in test

		if fromCache && result != nil {
			t.Error("Empty cache should return nil")
		}
	})

	t.Log("PASS: Edge cases handled correctly")
}

// BenchmarkCircuitBreakerExecution benchmarks circuit breaker overhead.
func BenchmarkCircuitBreakerExecution(b *testing.B) {
	cb := NewCircuitBreaker(1000, time.Hour)
	mock := NewMockRPCClient()
	mock.SetFailureMode(0)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in benchmark
			return mock.Call()
		})
	}
}

// BenchmarkCircuitBreakerConcurrent benchmarks concurrent access.
func BenchmarkCircuitBreakerConcurrent(b *testing.B) {
	cb := NewCircuitBreaker(1000, time.Hour)
	mock := NewMockRPCClient()
	mock.SetFailureMode(0)

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			_, _, _ = cb.Execute(func() (interface{}, error) { // intentionally ignore result in benchmark
				return mock.Call()
			})
		}
	})
}
