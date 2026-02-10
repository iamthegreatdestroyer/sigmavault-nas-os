"""
Core infrastructure components for SigmaVault NAS OS.

This module provides foundational patterns for resilience and reliability:
- Circuit breaker pattern for fault tolerance
- Health check system for monitoring
- Self-healing mechanisms
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState

__all__ = ["CircuitBreaker", "CircuitBreakerConfig", "CircuitBreakerState"]
