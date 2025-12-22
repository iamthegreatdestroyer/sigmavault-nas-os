// Package handlers provides HTTP request handlers for the API.
package handlers

import (
	"time"

	"sigmavault-nas-os/api/internal/config"
	"sigmavault-nas-os/api/internal/models"

	jwtware "github.com/gofiber/contrib/jwt"
	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

// AuthHandler handles authentication-related requests.
type AuthHandler struct {
	config *config.Config
}

// NewAuthHandler creates a new AuthHandler instance.
func NewAuthHandler(cfg *config.Config) *AuthHandler {
	return &AuthHandler{config: cfg}
}

// LoginRequest represents a login request.
type LoginRequest struct {
	Username string `json:"username" validate:"required"`
	Password string `json:"password" validate:"required"`
}

// TokenResponse represents an authentication token response.
type TokenResponse struct {
	AccessToken  string    `json:"access_token"`
	RefreshToken string    `json:"refresh_token"`
	TokenType    string    `json:"token_type"`
	ExpiresAt    time.Time `json:"expires_at"`
}

// Login authenticates a user and returns JWT tokens.
func (h *AuthHandler) Login(c *fiber.Ctx) error {
	var req LoginRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	// TODO: Implement actual user authentication against database
	// For now, accept a test user in development
	if req.Username != "admin" || req.Password != "admin" {
		return fiber.NewError(fiber.StatusUnauthorized, "Invalid credentials")
	}

	// Create user claims
	user := models.User{
		ID:       uuid.New().String(),
		Username: req.Username,
		Email:    "admin@sigmavault.local",
		Role:     "admin",
	}

	// Generate access token
	accessToken, expiresAt, err := h.generateAccessToken(user)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to generate token")
	}

	// Generate refresh token
	refreshToken, err := h.generateRefreshToken(user)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to generate refresh token")
	}

	return c.JSON(TokenResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "Bearer",
		ExpiresAt:    expiresAt,
	})
}

// RefreshToken refreshes an access token using a refresh token.
func (h *AuthHandler) RefreshToken(c *fiber.Ctx) error {
	type RefreshRequest struct {
		RefreshToken string `json:"refresh_token" validate:"required"`
	}

	var req RefreshRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	// Parse and validate refresh token
	token, err := jwt.Parse(req.RefreshToken, func(token *jwt.Token) (interface{}, error) {
		return []byte(h.config.JWTSecret), nil
	})

	if err != nil || !token.Valid {
		return fiber.NewError(fiber.StatusUnauthorized, "Invalid refresh token")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return fiber.NewError(fiber.StatusUnauthorized, "Invalid token claims")
	}

	// Verify it's a refresh token
	if tokenType, ok := claims["type"].(string); !ok || tokenType != "refresh" {
		return fiber.NewError(fiber.StatusUnauthorized, "Not a refresh token")
	}

	// Reconstruct user from claims
	user := models.User{
		ID:       claims["sub"].(string),
		Username: claims["username"].(string),
		Role:     claims["role"].(string),
	}

	// Generate new access token
	accessToken, expiresAt, err := h.generateAccessToken(user)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to generate token")
	}

	return c.JSON(TokenResponse{
		AccessToken:  accessToken,
		RefreshToken: req.RefreshToken, // Return same refresh token
		TokenType:    "Bearer",
		ExpiresAt:    expiresAt,
	})
}

// Logout invalidates the current session.
func (h *AuthHandler) Logout(c *fiber.Ctx) error {
	// TODO: Implement token blacklisting for proper logout
	return c.JSON(fiber.Map{
		"message": "Logged out successfully",
	})
}

// GetCurrentUser returns the current authenticated user.
func (h *AuthHandler) GetCurrentUser(c *fiber.Ctx) error {
	user := c.Locals("user").(*jwt.Token)
	claims := user.Claims.(jwt.MapClaims)

	return c.JSON(fiber.Map{
		"id":       claims["sub"],
		"username": claims["username"],
		"email":    claims["email"],
		"role":     claims["role"],
	})
}

// generateAccessToken creates a new JWT access token.
func (h *AuthHandler) generateAccessToken(user models.User) (string, time.Time, error) {
	expiresAt := time.Now().Add(h.config.JWTExpiry)

	claims := jwt.MapClaims{
		"sub":      user.ID,
		"username": user.Username,
		"email":    user.Email,
		"role":     user.Role,
		"type":     "access",
		"exp":      expiresAt.Unix(),
		"iat":      time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(h.config.JWTSecret))
	if err != nil {
		return "", time.Time{}, err
	}

	return tokenString, expiresAt, nil
}

// generateRefreshToken creates a new JWT refresh token.
func (h *AuthHandler) generateRefreshToken(user models.User) (string, error) {
	claims := jwt.MapClaims{
		"sub":      user.ID,
		"username": user.Username,
		"role":     user.Role,
		"type":     "refresh",
		"exp":      time.Now().Add(h.config.JWTRefreshExpiry).Unix(),
		"iat":      time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(h.config.JWTSecret))
}

// JWTMiddleware returns the JWT middleware configuration.
func JWTMiddleware(cfg *config.Config) fiber.Handler {
	return jwtware.New(jwtware.Config{
		SigningKey: jwtware.SigningKey{Key: []byte(cfg.JWTSecret)},
		ErrorHandler: func(c *fiber.Ctx, err error) error {
			return fiber.NewError(fiber.StatusUnauthorized, "Invalid or expired token")
		},
	})
}
