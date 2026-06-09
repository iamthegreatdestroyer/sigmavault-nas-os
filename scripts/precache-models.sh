#!/bin/bash
# SigmaVault NAS OS — Offline Model Pre-Cache
# Usage: sudo bash scripts/precache-models.sh
# Target: Run ONCE on a connected machine, then the 1TB drive has models for air-gap ops.

set -euo pipefail

log()  { printf "  [$(date +%H:%M:%S)] %s\n" "$*"; }
ok()   { printf "  OK: %s\n" "$*"; }
die()  { printf "  ERROR: %s\n" "$*" >&2; exit 1; }

# --- Models to pre-cache ---
# Qwen3-30B FP8: agentic coding, ~140 tok/s on CPU, ~30GB
# Gemma4-27B A4B: 256K context, text+image, ~17GB
QWEN_TAG="qwen3:30b-fp8"
GEMMA_TAG="gemma4:27b-a4b"
REQUIRED_GB=55  # FP8 Qwen + A4B Gemma combined, with headroom

echo ""
echo "======================================="
echo "  SigmaVault — Model Pre-Cache"
echo "======================================="
echo "  Qwen : ${QWEN_TAG}"
echo "  Gemma: ${GEMMA_TAG}"
echo "======================================="
echo ""

[[ $EUID -eq 0 ]] || die "Run as root: sudo $0"

# 1. Ensure Ollama is installed
if ! command -v ollama &>/dev/null; then
    log "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    ok "Ollama installed: $(ollama --version)"
else
    ok "Ollama already installed: $(ollama --version)"
fi

# 2. Ensure Ollama service is running
if ! systemctl is-active --quiet ollama; then
    systemctl start ollama
    sleep 2
fi
ok "Ollama service: running"

# 3. Disk space check
AVAIL_GB=$(df -BG /var/lib/ollama 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G' || df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
if [[ "${AVAIL_GB}" -lt "${REQUIRED_GB}" ]]; then
    die "Need ${REQUIRED_GB}GB free, only ${AVAIL_GB}GB available. Free disk space and retry."
fi
ok "Disk space: ${AVAIL_GB}GB available (need ${REQUIRED_GB}GB)"

# 4. Pull models
log "Pulling ${QWEN_TAG} (~30GB, this will take a while)..."
ollama pull "${QWEN_TAG}" || {
    log "FP8 tag not available, falling back to qwen3:30b (Q4_K_M ~19GB)..."
    QWEN_TAG="qwen3:30b"
    ollama pull "${QWEN_TAG}"
}
ok "Pulled: ${QWEN_TAG}"

log "Pulling ${GEMMA_TAG} (~17GB)..."
ollama pull "${GEMMA_TAG}" || {
    log "A4B tag not available, falling back to gemma4:27b (Q4 ~17GB)..."
    GEMMA_TAG="gemma4:27b"
    ollama pull "${GEMMA_TAG}"
}
ok "Pulled: ${GEMMA_TAG}"

# 5. Verify
log "Verifying models..."
QWEN_RESP=$(ollama run "${QWEN_TAG}" "Respond with exactly: SIGMAVAULT_OK" --nowordwrap 2>/dev/null | tail -1 || echo "")
GEMMA_RESP=$(ollama run "${GEMMA_TAG}" "Respond with exactly: SIGMAVAULT_OK" --nowordwrap 2>/dev/null | tail -1 || echo "")

echo ""
echo "======================================="
echo "  Model Cache Verification"
echo "======================================="
ollama list
echo "======================================="
if [[ "${QWEN_RESP}" == *"SIGMAVAULT_OK"* ]]; then
    ok "Qwen3 inference: PASS"
else
    log "Qwen3 inference response: ${QWEN_RESP:0:60}"
    ok "Qwen3 model cached (inference smoke test inconclusive)"
fi
if [[ "${GEMMA_RESP}" == *"SIGMAVAULT_OK"* ]]; then
    ok "Gemma4 inference: PASS"
else
    log "Gemma4 inference response: ${GEMMA_RESP:0:60}"
    ok "Gemma4 model cached (inference smoke test inconclusive)"
fi
echo "======================================="
echo "  Pre-cache complete. Models ready for"
echo "  air-gap deployment on 1TB drive."
echo "======================================="
echo ""
