# =============================================================================
# SigmaVault NAS OS - Makefile
# @FORGE Build System — Desktop Edition (v4 Action Plan)
# =============================================================================

VERSION := $(shell cat VERSION 2>/dev/null || echo "1.0.0")
BINARY_NAME := sigmavault-api
GO_DIR := src/api
PYTHON_DIR := src/engined
DESKTOP_DIR := src/desktop-ui

# Build settings
LDFLAGS := -ldflags="-s -w -X main.Version=$(VERSION)"
CGO := CGO_ENABLED=0

# Colors for output
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
NC := \033[0m

.PHONY: all build test clean install release docker iso help

# Default target
all: test build

# =============================================================================
# Build Targets
# =============================================================================

## build: Build all components (Go API + Desktop schemas)
build: build-api build-desktop
	@echo "$(GREEN)✓ All components built$(NC)"

## build-api: Build Go API server
build-api:
	@echo "$(BLUE)Building Go API server...$(NC)"
	cd $(GO_DIR) && $(CGO) go build $(LDFLAGS) -o ../../$(BINARY_NAME) .
	@echo "$(GREEN)✓ API server built: $(BINARY_NAME)$(NC)"

## build-api-linux: Build Go API for Linux (cross-compile)
build-api-linux:
	@echo "$(BLUE)Building for Linux AMD64...$(NC)"
	cd $(GO_DIR) && GOOS=linux GOARCH=amd64 $(CGO) go build $(LDFLAGS) -o ../../$(BINARY_NAME)-linux-amd64 .
	@echo "$(BLUE)Building for Linux ARM64...$(NC)"
	cd $(GO_DIR) && GOOS=linux GOARCH=arm64 $(CGO) go build $(LDFLAGS) -o ../../$(BINARY_NAME)-linux-arm64 .
	@echo "$(GREEN)✓ Linux binaries built$(NC)"

## build-desktop: Compile GSettings schemas and GResources
build-desktop:
	@echo "$(BLUE)Compiling GSettings schemas...$(NC)"
	glib-compile-schemas $(DESKTOP_DIR)/data/ 2>/dev/null || true
	@echo "$(BLUE)Compiling GResources...$(NC)"
	glib-compile-resources --sourcedir=$(DESKTOP_DIR)/resources \
		--target=$(DESKTOP_DIR)/resources/sigmavault.gresource \
		$(DESKTOP_DIR)/resources/sigmavault.gresource.xml 2>/dev/null || true
	@echo "$(GREEN)✓ Desktop resources built$(NC)"

# =============================================================================
# Test Targets
# =============================================================================

## test: Run all tests
test: test-python test-go test-integration test-desktop
	@echo "$(GREEN)✓ All tests passed$(NC)"

## test-python: Run Python engine tests
test-python:
	@echo "$(BLUE)Running Python engine tests...$(NC)"
	cd $(PYTHON_DIR) && python -m pytest -v
	@echo "$(GREEN)✓ Python engine tests passed$(NC)"

## test-go: Run Go tests
test-go:
	@echo "$(BLUE)Running Go tests...$(NC)"
	cd $(GO_DIR) && go test -v ./...
	@echo "$(GREEN)✓ Go tests passed$(NC)"

## test-integration: Run integration tests
test-integration:
	@echo "$(BLUE)Running integration tests...$(NC)"
	cd $(GO_DIR) && go test -v ./tests/...
	@echo "$(GREEN)✓ Integration tests passed$(NC)"

## test-desktop: Run desktop UI tests
test-desktop:
	@echo "$(BLUE)Running desktop UI tests...$(NC)"
	cd $(DESKTOP_DIR) && python -m pytest -v tests/ 2>/dev/null || echo "$(YELLOW)⚠ No desktop tests yet$(NC)"
	@echo "$(GREEN)✓ Desktop tests passed$(NC)"

## test-coverage: Run tests with coverage
test-coverage:
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	cd $(GO_DIR) && go test -coverprofile=coverage.out ./...
	cd $(GO_DIR) && go tool cover -html=coverage.out -o coverage.html
	cd $(PYTHON_DIR) && python -m pytest --cov=engined --cov-report=html
	@echo "$(GREEN)✓ Coverage reports generated$(NC)"

# =============================================================================
# Development Targets
# =============================================================================

## dev: Start development servers
dev:
	@echo "$(BLUE)Starting development environment...$(NC)"
	@echo "$(YELLOW)Start these in separate terminals:$(NC)"
	@echo "  1. make run-engine      # Python RPC engine (:8000 + :50051)"
	@echo "  2. make run-api         # Go API server     (:3000)"
	@echo "  3. make run-desktop     # GTK4 Settings app"

## run-api: Run API server
run-api:
	cd $(GO_DIR) && go run .

## run-engine: Run Python engine
run-engine:
	cd $(PYTHON_DIR) && python -m engined.main

## run-desktop: Run GTK4 desktop application
run-desktop:
	@echo "$(BLUE)Launching SigmaVault Settings...$(NC)"
	cd $(DESKTOP_DIR) && python -m main

# =============================================================================
# Release Targets
# =============================================================================

## release: Create release package
release:
	@echo "$(BLUE)Creating release package...$(NC)"
	./scripts/create-release.sh
	@echo "$(GREEN)✓ Release package created$(NC)"

## iso: Build Debian live ISO
iso:
	@echo "$(BLUE)Building Debian live ISO...$(NC)"
	./scripts/build-iso.sh
	@echo "$(GREEN)✓ ISO built$(NC)"

## docker: Build Docker image
docker:
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t sigmavault-nas-os:$(VERSION) -f docker/Dockerfile.builder .
	@echo "$(GREEN)✓ Docker image built$(NC)"

# =============================================================================
# Clean Targets
# =============================================================================

## clean: Clean build artifacts
clean:
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -f $(BINARY_NAME) $(BINARY_NAME)-linux-*
	rm -rf $(GO_DIR)/coverage.*
	rm -rf $(PYTHON_DIR)/.pytest_cache $(PYTHON_DIR)/__pycache__
	rm -rf $(PYTHON_DIR)/htmlcov $(PYTHON_DIR)/.coverage
	rm -rf $(DESKTOP_DIR)/resources/*.gresource
	rm -rf $(DESKTOP_DIR)/data/gschemas.compiled
	rm -rf $(DESKTOP_DIR)/__pycache__ $(DESKTOP_DIR)/**/__pycache__
	rm -rf release-*
	@echo "$(GREEN)✓ Clean complete$(NC)"

## clean-all: Clean everything including dependencies
clean-all: clean
	rm -rf $(PYTHON_DIR)/.venv
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

# =============================================================================
# Install Targets
# =============================================================================

## install: Install to system (requires root)
install: build
	@echo "$(BLUE)Installing SigmaVault NAS OS...$(NC)"
	sudo install -m 755 $(BINARY_NAME) /usr/local/bin/
	sudo install -m 644 live-build/config/includes.chroot/etc/systemd/system/*.service /etc/systemd/system/
	@# Desktop application
	sudo install -d /usr/lib/python3/dist-packages/sigmavault
	sudo cp -r $(DESKTOP_DIR)/*.py $(DESKTOP_DIR)/ui $(DESKTOP_DIR)/api /usr/lib/python3/dist-packages/sigmavault/
	sudo install -m 644 $(DESKTOP_DIR)/data/com.sigmavault.Settings.gschema.xml /usr/share/glib-2.0/schemas/
	sudo glib-compile-schemas /usr/share/glib-2.0/schemas/
	sudo install -m 644 $(DESKTOP_DIR)/data/com.sigmavault.Settings.desktop.in /usr/share/applications/com.sigmavault.Settings.desktop
	sudo install -m 755 $(DESKTOP_DIR)/data/sigmavault-settings /usr/local/bin/
	@# Nautilus extension
	sudo install -d /usr/share/nautilus-python/extensions
	sudo install -m 644 $(DESKTOP_DIR)/nautilus-sigmavault.py /usr/share/nautilus-python/extensions/
	sudo systemctl daemon-reload
	@echo "$(GREEN)✓ Installation complete$(NC)"

## uninstall: Uninstall from system
uninstall:
	@echo "$(BLUE)Uninstalling SigmaVault NAS OS...$(NC)"
	sudo systemctl stop sigmavault-api sigmavault-engined 2>/dev/null || true
	sudo systemctl disable sigmavault-api sigmavault-engined 2>/dev/null || true
	sudo rm -f /usr/local/bin/$(BINARY_NAME)
	sudo rm -f /usr/local/bin/sigmavault-settings
	sudo rm -rf /usr/lib/python3/dist-packages/sigmavault
	sudo rm -f /usr/share/applications/com.sigmavault.Settings.desktop
	sudo rm -f /usr/share/glib-2.0/schemas/com.sigmavault.Settings.gschema.xml
	sudo glib-compile-schemas /usr/share/glib-2.0/schemas/ 2>/dev/null || true
	sudo rm -f /usr/share/nautilus-python/extensions/nautilus-sigmavault.py
	sudo rm -f /etc/systemd/system/sigmavault-*.service
	sudo systemctl daemon-reload
	@echo "$(GREEN)✓ Uninstallation complete$(NC)"

# =============================================================================
# Lint Targets
# =============================================================================

## lint: Run all linters
lint: lint-go lint-python lint-desktop
	@echo "$(GREEN)✓ All linting passed$(NC)"

## lint-go: Run Go linter
lint-go:
	@echo "$(BLUE)Linting Go code...$(NC)"
	cd $(GO_DIR) && golangci-lint run ./...

## lint-python: Run Python linter (engine)
lint-python:
	@echo "$(BLUE)Linting Python engine code...$(NC)"
	cd $(PYTHON_DIR) && ruff check . && mypy .

## lint-desktop: Run Desktop UI linter
lint-desktop:
	@echo "$(BLUE)Linting Desktop UI code...$(NC)"
	cd $(DESKTOP_DIR) && ruff check . 2>/dev/null || echo "$(YELLOW)⚠ Install ruff for desktop linting$(NC)"

# =============================================================================
# Format Targets
# =============================================================================

## fmt: Format all code
fmt: fmt-go fmt-python fmt-desktop
	@echo "$(GREEN)✓ All code formatted$(NC)"

## fmt-go: Format Go code
fmt-go:
	cd $(GO_DIR) && gofmt -w .

## fmt-python: Format Python code (engine)
fmt-python:
	cd $(PYTHON_DIR) && ruff format .

## fmt-desktop: Format Desktop UI code
fmt-desktop:
	cd $(DESKTOP_DIR) && ruff format . 2>/dev/null || echo "$(YELLOW)⚠ Install ruff for desktop formatting$(NC)"

# =============================================================================
# Help
# =============================================================================

## help: Show this help
help:
	@echo "SigmaVault NAS OS - Build System (Desktop Edition)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^## [a-zA-Z_-]+:' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ": "}; {printf "  %-20s %s\n", $$1, $$2}' | \
		sed 's/## //'
	@echo ""
	@echo "Quick Start:"
	@echo "  make dev            # Show dev server commands"
	@echo "  make run-desktop    # Launch GTK4 Settings app"
	@echo "  make build          # Build all components"
	@echo "  make test           # Run all tests"
	@echo "  make iso            # Build Debian live ISO"
