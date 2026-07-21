//go:build sigmavault_devauth

// This file is compiled ONLY when the binary is built with -tags sigmavault_devauth — a
// developer convenience, never shipped. deploy.sh and the ISO build do NOT pass this tag, so
// production binaries physically do not contain the bypass below. Even in a dev build, the
// bypass activates only when running in development mode.
package middleware

import (
	"sigmavault-nas-os/api/internal/config"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

// devAuthBypass injects a fake admin user (skipping all auth) when built with the dev tag AND
// running in development mode; nil otherwise.
func devAuthBypass(cfg *config.Config) fiber.Handler {
	if !cfg.IsDevelopment() {
		return nil
	}
	return func(c *fiber.Ctx) error {
		c.Locals("user", &jwt.Token{
			Claims: jwt.MapClaims{
				"user_id": "dev-user",
				"email":   "dev@sigmavault.local",
				"role":    "admin",
			},
		})
		return c.Next()
	}
}
