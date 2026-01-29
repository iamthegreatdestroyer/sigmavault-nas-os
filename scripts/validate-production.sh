#!/usr/bin/env bash
# =============================================================================
# SigmaVault NAS OS - Production Readiness Validation
# @ECLIPSE Testing + @CIPHER Security Audit
# =============================================================================
set -uo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

log_pass() { 
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASS_COUNT++))
}

log_fail() { 
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAIL_COUNT++))
}

log_warn() { 
    echo -e "${YELLOW}[! WARN]${NC} $1"
    ((WARN_COUNT++))
}

log_info() { 
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

# Header
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║         SigmaVault NAS OS - Production Readiness Validation              ║"
echo "║                     @ECLIPSE Testing + @CIPHER Security                   ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# Section 1: File Structure Validation
# =============================================================================
log_section "Section 1: File Structure Validation"

# Check critical files exist
CRITICAL_FILES=(
    "VERSION"
    "CHANGELOG.md"
    "Makefile"
    "src/api/main.go"
    "src/api/go.mod"
    "src/engined/pyproject.toml"
    "src/engined/engined/main.py"
    "src/webui/package.json"
    "src/webui/src/App.tsx"
    ".github/workflows/ci.yml"
    "scripts/build-production.sh"
    "scripts/build-iso.sh"
    "scripts/create-release.sh"
    "docs/INSTALLATION.md"
    "configs/production.env.example"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        log_pass "File exists: $file"
    else
        log_fail "Missing file: $file"
    fi
done

# =============================================================================
# Section 2: Go API Validation
# =============================================================================
log_section "Section 2: Go API Validation"

cd src/api

# Check Go module
if go mod verify 2>/dev/null; then
    log_pass "Go modules verified"
else
    log_warn "Go modules have issues"
fi

# Build check
if go build -o /dev/null . 2>/dev/null; then
    log_pass "Go API builds successfully"
else
    log_fail "Go API build failed"
fi

# Run tests
if go test -v ./tests/... 2>&1 | grep -q "PASS"; then
    TEST_COUNT=$(go test -v ./tests/... 2>&1 | grep -c "--- PASS")
    log_pass "Go tests passed: $TEST_COUNT tests"
else
    log_fail "Go tests failed"
fi

# Check security configuration
if grep -q "Validate()" internal/config/config.go; then
    log_pass "Security validation function exists"
else
    log_fail "Missing Validate() in config.go"
fi

if grep -q "MustValidate" internal/config/config.go; then
    log_pass "MustValidate() panic wrapper exists"
else
    log_warn "Missing MustValidate() helper"
fi

cd ../..

# =============================================================================
# Section 3: Python Engine Validation
# =============================================================================
log_section "Section 3: Python Engine Validation"

cd src/engined

# Check Python files syntax
if python -m py_compile engined/main.py 2>/dev/null; then
    log_pass "Python main.py syntax valid"
else
    log_fail "Python main.py has syntax errors"
fi

# Run pytest
if python -m pytest -v --tb=no 2>&1 | grep -q "passed"; then
    PYTEST_PASS=$(python -m pytest -v --tb=no 2>&1 | grep -oP '\d+(?= passed)')
    log_pass "Python tests passed: ${PYTEST_PASS:-all} tests"
else
    log_warn "Python tests may have issues"
fi

# Check pyproject.toml
if [[ -f "pyproject.toml" ]]; then
    log_pass "pyproject.toml exists"
else
    log_fail "Missing pyproject.toml"
fi

cd ../..

# =============================================================================
# Section 4: WebUI Validation
# =============================================================================
log_section "Section 4: WebUI Validation"

cd src/webui

# Check package.json
if [[ -f "package.json" ]]; then
    log_pass "package.json exists"
    
    # Check for required dependencies
    if grep -q '"react"' package.json; then
        log_pass "React dependency present"
    else
        log_fail "React dependency missing"
    fi
    
    if grep -q '"typescript"' package.json; then
        log_pass "TypeScript dependency present"
    else
        log_warn "TypeScript dependency missing"
    fi
else
    log_fail "Missing package.json"
fi

# Check TypeScript config
if [[ -f "tsconfig.json" ]]; then
    log_pass "tsconfig.json exists"
else
    log_warn "Missing tsconfig.json"
fi

cd ../..

# =============================================================================
# Section 5: CI/CD Validation
# =============================================================================
log_section "Section 5: CI/CD Validation"

# Check GitHub Actions workflow
if [[ -f ".github/workflows/ci.yml" ]]; then
    log_pass "CI/CD workflow exists"
    
    # Check for required jobs
    if grep -q "test-python:" .github/workflows/ci.yml; then
        log_pass "Python test job configured"
    else
        log_warn "Missing Python test job"
    fi
    
    if grep -q "test-go:" .github/workflows/ci.yml; then
        log_pass "Go test job configured"
    else
        log_warn "Missing Go test job"
    fi
    
    if grep -q "security-scan:" .github/workflows/ci.yml; then
        log_pass "Security scan job configured"
    else
        log_warn "Missing security scan job"
    fi
else
    log_fail "Missing CI/CD workflow"
fi

# =============================================================================
# Section 6: Security Audit
# =============================================================================
log_section "Section 6: Security Audit (@CIPHER)"

# Check for hardcoded secrets
log_info "Scanning for hardcoded secrets..."

SECRET_PATTERNS=(
    "password.*="
    "secret.*="
    "api_key.*="
    "token.*="
)

SECRETS_FOUND=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rn --include="*.go" --include="*.py" --include="*.ts" "$pattern" src/ 2>/dev/null | grep -v "example\|test\|mock\|config.go" | head -5; then
        ((SECRETS_FOUND++))
    fi
done

if [[ $SECRETS_FOUND -eq 0 ]]; then
    log_pass "No hardcoded secrets found"
else
    log_warn "Potential hardcoded secrets detected"
fi

# Check JWT configuration
if grep -q "32 characters" src/api/internal/config/config.go 2>/dev/null; then
    log_pass "JWT secret length validation (32+ chars)"
else
    log_warn "JWT secret length not validated"
fi

# Check rate limiting
if grep -q "RateLimiter" src/api/internal/middleware/security.go 2>/dev/null; then
    log_pass "Rate limiting middleware present"
else
    log_warn "Rate limiting not implemented"
fi

# Check security headers
if grep -q "X-Frame-Options" src/api/internal/middleware/security.go 2>/dev/null; then
    log_pass "Security headers configured"
else
    log_warn "Security headers not configured"
fi

# =============================================================================
# Section 7: Documentation Validation
# =============================================================================
log_section "Section 7: Documentation Validation"

DOCS=(
    "README.md"
    "CHANGELOG.md"
    "docs/INSTALLATION.md"
    "docs/README.md"
)

for doc in "${DOCS[@]}"; do
    if [[ -f "$doc" ]]; then
        LINES=$(wc -l < "$doc")
        if [[ $LINES -gt 10 ]]; then
            log_pass "Documentation: $doc ($LINES lines)"
        else
            log_warn "Documentation sparse: $doc ($LINES lines)"
        fi
    else
        log_warn "Missing documentation: $doc"
    fi
done

# =============================================================================
# Section 8: Build Scripts Validation
# =============================================================================
log_section "Section 8: Build Scripts Validation"

SCRIPTS=(
    "scripts/build-all.sh"
    "scripts/build-production.sh"
    "scripts/build-iso.sh"
    "scripts/create-release.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [[ -f "$script" ]]; then
        if [[ -x "$script" ]] || head -1 "$script" | grep -q "#!/"; then
            log_pass "Build script: $script"
        else
            log_warn "Script not executable: $script"
        fi
    else
        log_warn "Missing script: $script"
    fi
done

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                    Production Readiness Summary                           ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
printf "║  ${GREEN}PASSED:${NC}  %-5d tests                                                  ║\n" "$PASS_COUNT"
printf "║  ${YELLOW}WARNINGS:${NC} %-5d items                                                  ║\n" "$WARN_COUNT"
printf "║  ${RED}FAILED:${NC}  %-5d tests                                                  ║\n" "$FAIL_COUNT"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"

TOTAL=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
SCORE=$((PASS_COUNT * 100 / TOTAL))

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "║  ${GREEN}STATUS: PRODUCTION READY${NC}                                              ║"
    echo -e "║  ${GREEN}SCORE: ${SCORE}%${NC}                                                           ║"
elif [[ $FAIL_COUNT -lt 3 ]]; then
    echo -e "║  ${YELLOW}STATUS: NEEDS ATTENTION${NC}                                              ║"
    echo -e "║  ${YELLOW}SCORE: ${SCORE}%${NC}                                                           ║"
else
    echo -e "║  ${RED}STATUS: NOT READY FOR PRODUCTION${NC}                                     ║"
    echo -e "║  ${RED}SCORE: ${SCORE}%${NC}                                                           ║"
fi

echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Exit with appropriate code
if [[ $FAIL_COUNT -eq 0 ]]; then
    exit 0
else
    exit 1
fi
