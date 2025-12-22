// Package main provides the entry point for the SigmaVault NAS OS API server.
// This server handles REST API endpoints, WebSocket connections, and RPC
// communication with the Python AI/ML engine.
package main

import (
	"os"
	"os/signal"
	"syscall"

	"sigmavault-nas-os/api/internal/config"
	"sigmavault-nas-os/api/internal/handlers"
	"sigmavault-nas-os/api/internal/middleware"
	"sigmavault-nas-os/api/internal/routes"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/joho/godotenv"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	// Initialize logger
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Warn().Msg("No .env file found, using environment variables")
	}

	// Load configuration
	cfg := config.Load()

	log.Info().
		Str("version", cfg.Version).
		Str("environment", cfg.Environment).
		Int("port", cfg.Port).
		Msg("Starting SigmaVault NAS OS API Server")

	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName:               "SigmaVault NAS OS API",
		ServerHeader:          "SigmaVault",
		DisableStartupMessage: false,
		ErrorHandler:          handlers.ErrorHandler,
	})

	// Global middleware
	app.Use(recover.New())
	app.Use(middleware.Logger())
	app.Use(cors.New(cors.Config{
		AllowOrigins:     cfg.CORSOrigins,
		AllowMethods:     "GET,POST,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders:     "Origin,Content-Type,Accept,Authorization,X-Request-ID",
		AllowCredentials: true,
		MaxAge:           86400,
	}))

	// Health check (no auth required)
	app.Get("/health", handlers.HealthCheck)
	app.Get("/ready", handlers.ReadyCheck)

	// Setup routes
	routes.SetupRoutes(app, cfg)

	// Start server in goroutine
	go func() {
		if err := app.Listen(":" + cfg.PortString()); err != nil {
			log.Fatal().Err(err).Msg("Failed to start server")
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info().Msg("Shutting down server...")
	if err := app.Shutdown(); err != nil {
		log.Error().Err(err).Msg("Error during server shutdown")
	}
	log.Info().Msg("Server stopped")
}
