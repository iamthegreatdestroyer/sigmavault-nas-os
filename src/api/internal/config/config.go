// Package config handles application configuration from environment variables.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config holds all application configuration.
type Config struct {
	// Server settings
	Environment string
	Port        int
	Version     string

	// CORS settings
	CORSOrigins string

	// JWT settings
	JWTSecret        string
	JWTExpiry        time.Duration
	JWTRefreshExpiry time.Duration

	// RPC Engine settings
	RPCEngineURL     string
	RPCEngineTimeout time.Duration

	// Database/Storage settings
	DataDir string

	// WebSocket settings
	WSPingInterval time.Duration
	WSPongTimeout  time.Duration

	// Static file serving
	ServeStatic bool
	StaticPath  string
}

// Load reads configuration from environment variables with sensible defaults.
func Load() *Config {
	return &Config{
		Environment:      getEnv("SIGMAVAULT_ENV", "development"),
		Port:             getEnvInt("SIGMAVAULT_PORT", 12080),
		Version:          getEnv("SIGMAVAULT_VERSION", "0.1.0"),
		CORSOrigins:      getEnv("SIGMAVAULT_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"),
		JWTSecret:        getEnv("SIGMAVAULT_JWT_SECRET", "dev-secret-change-in-production"),
		JWTExpiry:        getEnvDuration("SIGMAVAULT_JWT_EXPIRY", 15*time.Minute),
		JWTRefreshExpiry: getEnvDuration("SIGMAVAULT_JWT_REFRESH_EXPIRY", 7*24*time.Hour),
		RPCEngineURL:     getEnv("SIGMAVAULT_RPC_URL", "http://localhost:8001/api/v1"),
		RPCEngineTimeout: getEnvDuration("SIGMAVAULT_RPC_TIMEOUT", 30*time.Second),
		DataDir:          getEnv("SIGMAVAULT_DATA_DIR", "/var/lib/sigmavault"),
		WSPingInterval:   getEnvDuration("SIGMAVAULT_WS_PING_INTERVAL", 30*time.Second),
		WSPongTimeout:    getEnvDuration("SIGMAVAULT_WS_PONG_TIMEOUT", 10*time.Second),
		ServeStatic:      getEnvBool("SIGMAVAULT_SERVE_STATIC", false),
		StaticPath:       getEnv("SIGMAVAULT_STATIC_PATH", "./static"),
	}
}

// PortString returns the port as a string.
func (c *Config) PortString() string {
	return strconv.Itoa(c.Port)
}

// IsDevelopment returns true if running in development mode.
func (c *Config) IsDevelopment() bool {
	return strings.ToLower(c.Environment) == "development"
}

// IsProduction returns true if running in production mode.
func (c *Config) IsProduction() bool {
	return strings.ToLower(c.Environment) == "production"
}

// Validate checks configuration for security issues (@CIPHER audit).
func (c *Config) Validate() error {
	// In production, require secure JWT secret
	if c.IsProduction() {
		if c.JWTSecret == "dev-secret-change-in-production" {
			return fmt.Errorf("SECURITY: SIGMAVAULT_JWT_SECRET must be set in production")
		}
		if len(c.JWTSecret) < 32 {
			return fmt.Errorf("SECURITY: JWT secret must be at least 32 characters in production")
		}
	}

	// Validate CORS origins in production
	if c.IsProduction() && c.CORSOrigins == "http://localhost:5173,http://localhost:3000" {
		return fmt.Errorf("SECURITY: SIGMAVAULT_CORS_ORIGINS must be configured for production")
	}

	return nil
}

// MustValidate panics if configuration is invalid.
func (c *Config) MustValidate() {
	if err := c.Validate(); err != nil {
		panic(err)
	}
}

// Helper functions for reading environment variables

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getEnvDuration(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolValue, err := strconv.ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}
