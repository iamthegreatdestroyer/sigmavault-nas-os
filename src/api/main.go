// Package main provides the entry point for the SigmaVault NAS OS API server.
// This server handles REST API endpoints, WebSocket connections, and RPC
// communication with the Python AI/ML engine.
package main

import (
	"bufio"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"sigmavault-nas-os/api/internal/config"
	"sigmavault-nas-os/api/internal/handlers"
	"sigmavault-nas-os/api/internal/routes"

	"github.com/gofiber/fiber/v2"
	"github.com/joho/godotenv"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"golang.org/x/crypto/bcrypt"
)

// hashPasswordCLI implements `sigmavault-api hashpw [password]`: it prints a bcrypt hash of
// the password (from argv or stdin) to stdout and exits. Used by deploy.sh's first-boot
// credential setup so a random admin password can be hashed without any extra system deps.
// The plaintext is never logged; only the hash is printed.
func hashPasswordCLI(args []string) {
	var pw string
	if len(args) > 0 {
		pw = args[0]
	} else {
		s := bufio.NewScanner(os.Stdin)
		if s.Scan() {
			pw = strings.TrimRight(s.Text(), "\r\n")
		}
	}
	if pw == "" {
		fmt.Fprintln(os.Stderr, "hashpw: empty password")
		os.Exit(2)
	}
	h, err := bcrypt.GenerateFromPassword([]byte(pw), bcrypt.DefaultCost)
	if err != nil {
		fmt.Fprintln(os.Stderr, "hashpw:", err)
		os.Exit(1)
	}
	fmt.Println(string(h))
}

func main() {
	// Subcommand: hash a password for admin-credential provisioning, then exit.
	if len(os.Args) >= 2 && os.Args[1] == "hashpw" {
		hashPasswordCLI(os.Args[2:])
		return
	}

	// Initialize logger
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Warn().Msg("No .env file found, using environment variables")
	}

	// Load configuration
	cfg := config.Load()

	// Validate security configuration in production (@CIPHER audit)
	if err := cfg.Validate(); err != nil {
		log.Fatal().Err(err).Msg("Configuration validation failed")
	}

	log.Info().
		Str("version", cfg.Version).
		Str("environment", cfg.Environment).
		Str("host", cfg.Host).
		Int("port", cfg.Port).
		Msg("Starting SigmaVault NAS OS API Server")

	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName:               "SigmaVault NAS OS API",
		ServerHeader:          "SigmaVault",
		DisableStartupMessage: false,
		ErrorHandler:          handlers.ErrorHandler,
	})

	// Setup all routes and middleware
	routes.Setup(app, cfg)

	// Start server in goroutine
	go func() {
		if err := app.Listen(cfg.ListenAddr()); err != nil {
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
