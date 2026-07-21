//go:build !sigmavault_devauth

// This file is compiled into ALL shipped builds (default; no build tag). The development
// auth bypass does not exist in the binary — devAuthBypass is a no-op, so JWT() always
// performs full token validation. To get the dev bypass, build with -tags sigmavault_devauth
// (see auth_devbypass_on.go).
package middleware

import (
	"sigmavault-nas-os/api/internal/config"

	"github.com/gofiber/fiber/v2"
)

// devAuthBypass returns nil in shipped builds: no auth bypass is compiled in.
func devAuthBypass(_ *config.Config) fiber.Handler { return nil }
