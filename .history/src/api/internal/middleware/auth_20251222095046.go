// Package middleware provides HTTP middleware for the API.
package middleware

import (
	"sigmavault-nas-os/api/internal/config"

	jwtware "github.com/gofiber/contrib/jwt"
	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

// JWTConfig holds JWT middleware configuration.
type JWTConfig struct {
	Secret    string
	Algorithm string
}

// JWT returns JWT authentication middleware.
func JWT(cfg *config.Config) fiber.Handler {
	return jwtware.New(jwtware.Config{
		SigningKey: jwtware.SigningKey{Key: []byte(cfg.JWTSecret)},
		ContextKey: "user",
		ErrorHandler: func(c *fiber.Ctx, err error) error {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid or expired token",
				"code":  fiber.StatusUnauthorized,
			})
		},
		SuccessHandler: func(c *fiber.Ctx) error {
			return c.Next()
		},
	})
}

// RequireRole checks if the authenticated user has the required role.
func RequireRole(roles ...string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		user := c.Locals("user").(*jwt.Token)
		claims := user.Claims.(jwt.MapClaims)

		userRole, ok := claims["role"].(string)
		if !ok {
			return fiber.NewError(fiber.StatusForbidden, "Invalid token claims")
		}

		// Check if user has one of the required roles
		for _, role := range roles {
			if userRole == role {
				return c.Next()
			}
		}

		return fiber.NewError(fiber.StatusForbidden, "Insufficient permissions")
	}
}

// OptionalAuth allows requests with or without authentication.
func OptionalAuth(cfg *config.Config) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Check for Authorization header
		auth := c.Get("Authorization")
		if auth == "" {
			// No auth header, continue without user
			return c.Next()
		}

		// Try to parse JWT
		tokenString := auth
		if len(auth) > 7 && auth[:7] == "Bearer " {
			tokenString = auth[7:]
		}

		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			return []byte(cfg.JWTSecret), nil
		})

		if err == nil && token.Valid {
			c.Locals("user", token)
		}

		return c.Next()
	}
}
