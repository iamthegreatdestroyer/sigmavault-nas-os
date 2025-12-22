// Package routes sets up all API routes.
package routes

import (
	"context"
	"time"

	"sigmavault-nas-os/api/internal/config"
	"sigmavault-nas-os/api/internal/handlers"
	"sigmavault-nas-os/api/internal/middleware"
	"sigmavault-nas-os/api/internal/rpc"
	"sigmavault-nas-os/api/internal/websocket"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/rs/zerolog/log"
)

// Setup configures all routes for the application.
func Setup(app *fiber.App, cfg *config.Config) {
	// Global middleware
	app.Use(recover.New())
	app.Use(middleware.Logger())
	app.Use(middleware.RequestID())
	app.Use(middleware.Timing())
	app.Use(middleware.SecurityHeaders())
	app.Use(cors.New(cors.Config{
		AllowOrigins:     cfg.CORSOrigins,
		AllowMethods:     "GET,POST,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders:     "Origin,Content-Type,Accept,Authorization,X-Request-ID,X-API-Key",
		AllowCredentials: true,
		MaxAge:           86400,
	}))

	// Initialize RPC client for Python engine communication
	rpcClient := rpc.NewClient(rpc.Config{
		BaseURL: cfg.RPCEngineURL,
		Timeout: cfg.RPCEngineTimeout,
	})

	// RPC client uses lazy connection - it will connect on first Call()
	// Perform a health check to verify engine availability (non-blocking)
	if err := rpcClient.HealthCheck(context.Background()); err != nil {
		log.Warn().Err(err).Str("url", cfg.RPCEngineURL).Msg("RPC engine not available at startup, handlers will retry")
	} else {
		log.Info().Str("url", cfg.RPCEngineURL).Msg("Connected to RPC engine")
	}

	// Create handlers with RPC client injection
	authHandler := handlers.NewAuthHandler(cfg)
	storageHandler := handlers.NewStorageHandler(rpcClient)
	systemHandler := handlers.NewSystemHandler(rpcClient)
	agentsHandler := handlers.NewAgentsHandler(rpcClient)
	compressionHandler := handlers.NewCompressionHandler(rpcClient)

	// Create WebSocket hub
	wsHub := websocket.NewHub()
	go wsHub.Run()

	// Initialize event subscriber to broadcast RPC events to WebSocket clients
	eventSubscriber := websocket.NewEventSubscriber(wsHub, rpcClient)
	eventSubscriber.Start(context.Background(), 5*time.Second)
	app.Locals("eventSubscriber", eventSubscriber)

	wsHandler := websocket.NewHandler(wsHub)

	// API version prefix
	api := app.Group("/api/v1")

	// Health endpoints (public)
	api.Get("/health", handlers.HealthCheck)
	api.Get("/ready", handlers.ReadyCheck)
	api.Get("/info", handlers.SystemInfo)

	// Authentication endpoints
	auth := api.Group("/auth")
	auth.Use(middleware.StrictRateLimiter())
	auth.Post("/login", authHandler.Login)
	auth.Post("/refresh", authHandler.RefreshToken)
	auth.Post("/logout", authHandler.Logout)

	// Protected routes - require JWT
	protected := api.Group("")
	protected.Use(middleware.JWT(cfg))

	// User endpoints
	protected.Get("/auth/me", authHandler.GetCurrentUser)

	// Storage endpoints
	storage := protected.Group("/storage")
	storage.Get("/pools", storageHandler.ListPools)
	storage.Get("/pools/:id", storageHandler.GetPool)
	storage.Post("/pools", middleware.RequireRole("admin"), storageHandler.CreatePool)
	storage.Delete("/pools/:id", middleware.RequireRole("admin"), storageHandler.DeletePool)
	storage.Get("/shares", storageHandler.ListShares)
	storage.Post("/shares", middleware.RequireRole("admin"), storageHandler.CreateShare)
	storage.Delete("/shares/:id", middleware.RequireRole("admin"), storageHandler.DeleteShare)

	// System endpoints
	system := protected.Group("/system")
	system.Get("/status", systemHandler.GetSystemStatus)
	system.Get("/network", systemHandler.GetNetworkInterfaces)
	system.Get("/services", systemHandler.GetServices)
	system.Post("/services/:id/restart", middleware.RequireRole("admin"), systemHandler.RestartService)
	system.Get("/notifications", systemHandler.GetNotifications)
	system.Post("/notifications/:id/read", systemHandler.MarkNotificationRead)
	system.Post("/reboot", middleware.RequireRole("admin"), systemHandler.Reboot)
	system.Post("/shutdown", middleware.RequireRole("admin"), systemHandler.Shutdown)

	// AI Agents endpoints
	agents := protected.Group("/agents")
	agents.Get("/", agentsHandler.ListAgents)
	agents.Get("/:id", agentsHandler.GetAgent)
	agents.Get("/:id/metrics", agentsHandler.AgentMetrics)

	// Compression endpoints
	compression := protected.Group("/compression")
	compression.Post("/jobs", compressionHandler.StartCompression)
	compression.Get("/jobs", compressionHandler.ListCompressionJobs)
	compression.Get("/jobs/:id", compressionHandler.GetCompressionJob)
	compression.Delete("/jobs/:id", compressionHandler.CancelCompressionJob)

	// WebSocket endpoint for real-time updates
	app.Get("/ws", wsHandler.HandleWebSocket)

	// Static file serving for web UI (if enabled)
	if cfg.ServeStatic {
		app.Static("/", cfg.StaticPath)
		// Fallback to index.html for SPA routing
		app.Get("/*", func(c *fiber.Ctx) error {
			return c.SendFile(cfg.StaticPath + "/index.html")
		})
	}
}
