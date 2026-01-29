# =============================================================================
# SigmaVault NAS OS - Makefile
# @FORGE Build System
# =============================================================================

VERSION := $(shell cat VERSION 2>/dev/null || echo "1.0.0")
BINARY_NAME := sigmavault-api
GO_DIR := src/api
PYTHON_DIR := src/engined
WEBUI_DIR := src/webui

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

## build: Build all components
build: build-api build-webui
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

## build-webui: Build React WebUI
build-webui:
	@echo "$(BLUE)Building WebUI...$(NC)"
	cd $(WEBUI_DIR) && pnpm install && pnpm build
	@echo "$(GREEN)✓ WebUI built$(NC)"

# =============================================================================
# Test Targets
# =============================================================================

## test: Run all tests
test: test-python test-go test-integration
	@echo "$(GREEN)✓ All tests passed$(NC)"

## test-python: Run Python tests
test-python:
	@echo "$(BLUE)Running Python tests...$(NC)"
	cd $(PYTHON_DIR) && python -m pytest -v
	@echo "$(GREEN)✓ Python tests passed$(NC)"

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
	@echo "$(BLUE)Starting development servers...$(NC)"
	@echo "$(YELLOW)Start these in separate terminals:$(NC)"
	@echo "  1. cd $(PYTHON_DIR) && python -m engined.main"
	@echo "  2. cd $(GO_DIR) && go run ."
	@echo "  3. cd $(WEBUI_DIR) && pnpm dev"

## run-api: Run API server
run-api:
	cd $(GO_DIR) && go run .

## run-engine: Run Python engine
run-engine:
	cd $(PYTHON_DIR) && python -m engined.main

## run-webui: Run WebUI dev server
run-webui:
	cd $(WEBUI_DIR) && pnpm dev

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
	rm -rf $(WEBUI_DIR)/dist $(WEBUI_DIR)/node_modules
	rm -rf release-*
	@echo "$(GREEN)✓ Clean complete$(NC)"

## clean-all: Clean everything including dependencies
clean-all: clean
	rm -rf $(WEBUI_DIR)/node_modules
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
	sudo systemctl daemon-reload
	@echo "$(GREEN)✓ Installation complete$(NC)"

## uninstall: Uninstall from system
uninstall:
	@echo "$(BLUE)Uninstalling SigmaVault NAS OS...$(NC)"
	sudo systemctl stop sigmavault-api sigmavault-engined sigmavault-webui 2>/dev/null || true
	sudo systemctl disable sigmavault-api sigmavault-engined sigmavault-webui 2>/dev/null || true
	sudo rm -f /usr/local/bin/$(BINARY_NAME)
	sudo rm -f /etc/systemd/system/sigmavault-*.service
	sudo systemctl daemon-reload
	@echo "$(GREEN)✓ Uninstallation complete$(NC)"

# =============================================================================
# Lint Targets
# =============================================================================

## lint: Run all linters
lint: lint-go lint-python lint-webui
	@echo "$(GREEN)✓ All linting passed$(NC)"

## lint-go: Run Go linter
lint-go:
	@echo "$(BLUE)Linting Go code...$(NC)"
	cd $(GO_DIR) && golangci-lint run ./...

## lint-python: Run Python linter
lint-python:
	@echo "$(BLUE)Linting Python code...$(NC)"
	cd $(PYTHON_DIR) && ruff check . && mypy .

## lint-webui: Run WebUI linter
lint-webui:
	@echo "$(BLUE)Linting WebUI code...$(NC)"
	cd $(WEBUI_DIR) && pnpm lint

# =============================================================================
# Format Targets
# =============================================================================

## fmt: Format all code
fmt: fmt-go fmt-python fmt-webui
	@echo "$(GREEN)✓ All code formatted$(NC)"

## fmt-go: Format Go code
fmt-go:
	cd $(GO_DIR) && gofmt -w .

## fmt-python: Format Python code
fmt-python:
	cd $(PYTHON_DIR) && ruff format .

## fmt-webui: Format WebUI code
fmt-webui:
	cd $(WEBUI_DIR) && pnpm format

# =============================================================================
# Help
# =============================================================================

## help: Show this help
help:
	@echo "SigmaVault NAS OS - Build System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^## [a-zA-Z_-]+:' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ": "}; {printf "  %-20s %s\n", $$1, $$2}' | \
		sed 's/## //'
	@echo ""
	@echo "Examples:"
	@echo "  make build          # Build all components"
	@echo "  make test           # Run all tests"
	@echo "  make release        # Create release package"
	@echo "  make iso            # Build Debian live ISO"
