// Package circuitbreaker provides a circuit breaker pattern implementation for Go.
// State machine: CLOSED → OPEN → HALF_OPEN → CLOSED
//
// Features:
// - Automatic failure detection and recovery
// - Configurable thresholds and timeouts
// - Exponential backoff for recovery attempts
// - Thread-safe implementation
// - Prometheus metrics integration ready
//
// Author: @FORTRESS + @VELOCITY
package circuitbreaker

import (
	"errors"
	"fmt"
	"sync"
	"time"
)

// State represents the circuit breaker state.
type State int

const (
	// StateClosed - Normal operation, requests pass through
	StateClosed State = iota
	// StateOpen - Failure threshold exceeded, requests blocked
	StateOpen
	// StateHalfOpen - Testing if service recovered
	StateHalfOpen
)

func (s State) String() string {
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

// Config holds circuit breaker configuration.
type Config struct {
	// FailureThreshold is the number of failures before opening circuit
	FailureThreshold int

	// SuccessThreshold is the number of successes in HALF_OPEN to close circuit
	SuccessThreshold int

	// Timeout is the duration to wait before trying HALF_OPEN state
	Timeout time.Duration

	// TimeoutMax is the maximum timeout for exponential backoff
	TimeoutMax time.Duration

	// TimeoutMultiplier is the multiplier for exponential backoff
	TimeoutMultiplier float64
}

// DefaultConfig returns the default circuit breaker configuration.
func DefaultConfig() Config {
	return Config{
		FailureThreshold:  5,
		SuccessThreshold:  2,
		Timeout:           10 * time.Second,
		TimeoutMax:        5 * time.Minute,
		TimeoutMultiplier: 2.0,
	}
}

// Metrics holds circuit breaker metrics.
type Metrics struct {
	TotalCalls       uint64
	FailedCalls      uint64
	SuccessfulCalls  uint64
	RejectedCalls    uint64
	StateTransitions map[string]uint64
	LastFailureTime  *time.Time
	LastSuccessTime  *time.Time
}

// CircuitBreaker implements the circuit breaker pattern.
type CircuitBreaker struct {
	name            string
	config          Config
	state           State
	failureCount    int
	successCount    int
	lastFailureTime *time.Time
	nextAttemptTime *time.Time
	currentTimeout  time.Duration
	metrics         Metrics
	mu              sync.RWMutex
}

// New creates a new circuit breaker with the given configuration.
func New(name string, config Config) *CircuitBreaker {
	return &CircuitBreaker{
		name:           name,
		config:         config,
		state:          StateClosed,
		currentTimeout: config.Timeout,
		metrics: Metrics{
			StateTransitions: make(map[string]uint64),
		},
	}
}

// ErrCircuitOpen is returned when the circuit breaker is open.
var ErrCircuitOpen = errors.New("circuit breaker is open")

// Call executes the given function with circuit breaker protection.
func (cb *CircuitBreaker) Call(fn func() error) error {
	cb.mu.Lock()
	cb.metrics.TotalCalls++

	if !cb.shouldAttempt() {
		cb.metrics.RejectedCalls++
		cb.mu.Unlock()
		return fmt.Errorf("%w: %s", ErrCircuitOpen, cb.name)
	}
	cb.mu.Unlock()

	err := fn()

	if err != nil {
		cb.onFailure(err)
		return err
	}

	cb.onSuccess()
	return nil
}

// shouldAttempt determines if a request should be attempted.
// Must be called with lock held.
func (cb *CircuitBreaker) shouldAttempt() bool {
	if cb.state == StateClosed {
		return true
	}

	if cb.state == StateOpen {
		// Check if timeout has expired
		if cb.nextAttemptTime != nil && time.Now().After(*cb.nextAttemptTime) {
			cb.transitionState(StateHalfOpen)
			return true
		}
		return false
	}

	// HALF_OPEN state - allow attempts
	return true
}

// onSuccess handles successful call.
func (cb *CircuitBreaker) onSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.metrics.SuccessfulCalls++
	now := time.Now()
	cb.metrics.LastSuccessTime = &now

	if cb.state == StateHalfOpen {
		cb.successCount++
		if cb.successCount >= cb.config.SuccessThreshold {
			cb.transitionState(StateClosed)
		}
	} else if cb.state == StateClosed {
		// Reset failure count on success
		cb.failureCount = 0
	}
}

// onFailure handles failed call.
func (cb *CircuitBreaker) onFailure(err error) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.metrics.FailedCalls++
	now := time.Now()
	cb.metrics.LastFailureTime = &now
	cb.lastFailureTime = &now

	if cb.state == StateHalfOpen {
		// Immediate transition back to OPEN on failure
		cb.transitionState(StateOpen)
		cb.setNextAttemptTime()
	} else if cb.state == StateClosed {
		cb.failureCount++
		if cb.failureCount >= cb.config.FailureThreshold {
			cb.transitionState(StateOpen)
			cb.setNextAttemptTime()
		}
	}
}

// transitionState transitions to a new state and updates metrics.
// Must be called with lock held.
func (cb *CircuitBreaker) transitionState(newState State) {
	if cb.state != newState {
		oldState := cb.state
		cb.state = newState

		// Update metrics
		transitionKey := fmt.Sprintf("%s_to_%s", oldState.String(), newState.String())
		cb.metrics.StateTransitions[transitionKey]++

		// Reset counters on state change
		if newState == StateHalfOpen {
			cb.successCount = 0
			cb.failureCount = 0
		} else if newState == StateClosed {
			cb.failureCount = 0
			cb.currentTimeout = cb.config.Timeout // Reset backoff
		}
	}
}

// setNextAttemptTime sets next attempt time with exponential backoff.
// Must be called with lock held.
func (cb *CircuitBreaker) setNextAttemptTime() {
	nextAttempt := time.Now().Add(cb.currentTimeout)
	cb.nextAttemptTime = &nextAttempt

	// Exponential backoff with maximum cap
	newTimeout := time.Duration(float64(cb.currentTimeout) * cb.config.TimeoutMultiplier)
	if newTimeout > cb.config.TimeoutMax {
		newTimeout = cb.config.TimeoutMax
	}
	cb.currentTimeout = newTimeout
}

// GetState returns the current circuit breaker state.
func (cb *CircuitBreaker) GetState() State {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state
}

// GetMetrics returns the current metrics.
func (cb *CircuitBreaker) GetMetrics() Metrics {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	// Create a copy to avoid race conditions
	metricsCopy := cb.metrics
	metricsCopy.StateTransitions = make(map[string]uint64, len(cb.metrics.StateTransitions))
	for k, v := range cb.metrics.StateTransitions {
		metricsCopy.StateTransitions[k] = v
	}

	return metricsCopy
}

// Reset manually resets the circuit breaker to CLOSED state.
// Use with caution - only for testing or manual recovery.
func (cb *CircuitBreaker) Reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.state = StateClosed
	cb.failureCount = 0
	cb.successCount = 0
	cb.currentTimeout = cb.config.Timeout
	cb.nextAttemptTime = nil
}

// IsOpen returns true if the circuit breaker is in OPEN state.
func (cb *CircuitBreaker) IsOpen() bool {
	return cb.GetState() == StateOpen
}

// IsClosed returns true if the circuit breaker is in CLOSED state.
func (cb *CircuitBreaker) IsClosed() bool {
	return cb.GetState() == StateClosed
}

// IsHalfOpen returns true if the circuit breaker is in HALF_OPEN state.
func (cb *CircuitBreaker) IsHalfOpen() bool {
	return cb.GetState() == StateHalfOpen
}
