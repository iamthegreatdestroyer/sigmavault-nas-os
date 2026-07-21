#!/bin/bash
# SigmaVault NAS OS - One-Command Deployer
# Usage: sudo /opt/sigmavault/deploy.sh
# Target: Fresh Debian 13 (trixie) amd64 install

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}"
DATA_DIR="/var/lib/sigmavault"
LOG_DIR="/var/log/sigmavault"
CONFIG_DIR="/etc/sigmavault"
SERVICE_USER="sigmavault"
API_PORT=12080
ENGINED_PORT=5000
GO_VERSION="1.25.11"   # matches src/api/go.mod's toolchain (no GOTOOLCHAIN re-fetch)
# SECURITY: pinned SHA256 of the Go tarball per arch (from https://go.dev/dl/). Update these
# together with GO_VERSION. Verified before extraction so a tampered/MITM'd download is refused.
GO_SHA256_amd64="34f14304e856893f4ba30c2cacfe93906e9de7915c5f6aaaf3a81cdccd7ba30b"
GO_SHA256_arm64="c30bf9e156a54ea4e31fbbbf31a712b32734b58cc9a22426fa5ee632d0885124"

log()  { printf "  [$(date +%H:%M:%S)] %s\n" "$*"; }
ok()   { printf "  OK: %s\n" "$*"; }
die()  { printf "  ERROR: %s\n" "$*" >&2; exit 1; }

echo ""
echo "======================================="
echo "  SigmaVault NAS OS - Deploy v1.1 (Debian 13.5)"
echo "======================================="
echo ""

[[ $EUID -eq 0 ]] || die "Run as root: sudo $0"

# Verify Debian 13 (trixie) — Debian 12 EOL June 10 2026
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    if [[ "${VERSION_CODENAME:-}" != "trixie" ]]; then
        die "Requires Debian 13 trixie. Detected: ${PRETTY_NAME:-unknown}"
    fi
else
    die "Cannot detect OS: /etc/os-release missing"
fi

# 1. System packages
log "Installing system packages..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    curl wget ca-certificates openssl \
    python3 python3-pip \
    build-essential
ok "System packages ready"

# 2. Go
GOBIN=/usr/local/go/bin/go
if [[ -x "$GOBIN" ]]; then
    log "Go already installed: $("$GOBIN" version | awk '{print $3}')"
else
    log "Installing Go ${GO_VERSION}..."
    ARCH=$(dpkg --print-architecture)
    [[ "$ARCH" == "arm64" ]] || ARCH="amd64"
    wget -q "https://go.dev/dl/go${GO_VERSION}.linux-${ARCH}.tar.gz" -O /tmp/go.tar.gz
    # SECURITY: verify against the pinned SHA256 before extracting (indirect var: GO_SHA256_<arch>).
    EXPECTED_SHA_VAR="GO_SHA256_${ARCH}"
    echo "${!EXPECTED_SHA_VAR}  /tmp/go.tar.gz" | sha256sum -c - \
        || die "Go tarball SHA256 mismatch for ${ARCH} — refusing to install (possible tampering)"
    rm -rf /usr/local/go
    tar -C /usr/local -xzf /tmp/go.tar.gz
    rm /tmp/go.tar.gz
    ok "Go ${GO_VERSION} installed"
fi
export PATH="/usr/local/go/bin:$PATH"

# 3. Python packages (SECURITY: version-pinned via requirements.txt, not an unpinned list)
log "Installing Python packages (pinned)..."
pip3 install --break-system-packages --quiet -r "${INSTALL_DIR}/requirements.txt"
ok "Python packages installed (pinned versions)"

# 4. System user
log "Setting up sigmavault user..."
getent group  "$SERVICE_USER" &>/dev/null || groupadd --system "$SERVICE_USER"
getent passwd "$SERVICE_USER" &>/dev/null || useradd --system \
    --gid "$SERVICE_USER" --no-create-home \
    --shell /usr/sbin/nologin "$SERVICE_USER"
ok "User/group ready"

# 5. Directories
log "Creating directories..."
mkdir -p "$DATA_DIR" "$LOG_DIR" "$CONFIG_DIR"
mkdir -p "${INSTALL_DIR}/bin"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "$DATA_DIR" "$LOG_DIR"
ok "Directories ready"

# 6. Build Go binary
log "Building sigmavault-api..."
cd "${INSTALL_DIR}/src/api"
GOTOOLCHAIN=auto CGO_ENABLED=0 go build \
    -ldflags="-s -w" \
    -o "${INSTALL_DIR}/bin/sigmavault-api" \
    .
chmod +x "${INSTALL_DIR}/bin/sigmavault-api"
ok "Binary built: $(du -sh ${INSTALL_DIR}/bin/sigmavault-api | cut -f1)"

# 7. Config
log "Writing config..."
cat > "${CONFIG_DIR}/config.yaml" <<'YAML'
api:
  port: 12080
  host: "127.0.0.1"   # loopback by default; the binary honors SIGMAVAULT_HOST (see the unit)
engined:
  port: 5000
  host: "127.0.0.1"
storage:
  data_dir: "/var/lib/sigmavault"
logging:
  level: "info"
  dir: "/var/log/sigmavault"
YAML
ok "Config written to ${CONFIG_DIR}/config.yaml"

# 7b. API security env — production auth (SECURITY, closes the :12080 dev-auth-bypass).
# The API defaults to SIGMAVAULT_ENV=development, which makes middleware/auth.go inject a
# fake admin user and skip ALL auth. Production mode enforces real JWT + non-default CORS
# (main.go Validate() log.Fatal()s otherwise). This reproduces, in-repo, the 2026-07-16
# on-box hardening drop-in so a fresh deploy is secure by default instead of dev-open.
# Secret lives ONLY in this root-owned 0600 file (never in the repo, never in the 0644
# unit); systemd reads it as root before dropping to User=sigmavault. Generated ONCE and
# left alone on redeploy so existing tokens aren't invalidated.
API_ENV_FILE="${CONFIG_DIR}/api.env"
log "Provisioning API security env (production auth)..."
if [[ -f "$API_ENV_FILE" ]]; then
    ok "API env already provisioned: ${API_ENV_FILE} (left unchanged)"
else
    JWT_SECRET="$(openssl rand -hex 32)"   # 64 hex chars, well over the 32-char minimum
    # First-boot admin credential (SECURITY): replaces the former hardcoded admin/admin login.
    # Generate a random password, store only its bcrypt hash, and show the password ONCE.
    ADMIN_PASSWORD="$(openssl rand -base64 18)"
    ADMIN_PASSWORD_HASH="$("${INSTALL_DIR}/bin/sigmavault-api" hashpw "$ADMIN_PASSWORD")"
    ( umask 077
      cat > "$API_ENV_FILE" <<ENVEOF
# SigmaVault API — production auth. Root-owned 0600. NOT in the repo.
# Generated by deploy.sh $(date -u +%FT%TZ). Do not commit; do not log the secret.
SIGMAVAULT_ENV=production
SIGMAVAULT_JWT_SECRET=${JWT_SECRET}
SIGMAVAULT_CORS_ORIGINS=http://127.0.0.1:12080
SIGMAVAULT_HOST=127.0.0.1
SIGMAVAULT_ADMIN_USER=admin
SIGMAVAULT_ADMIN_PASSWORD_HASH=${ADMIN_PASSWORD_HASH}
ENVEOF
    )
    chown root:root "$API_ENV_FILE"
    chmod 600 "$API_ENV_FILE"
    ok "API env provisioned: ${API_ENV_FILE} (production, fresh 256-bit JWT secret + admin cred)"
    echo ""
    echo "  ============================================================"
    echo "  ADMIN LOGIN (shown ONCE — save it now, it is not stored):"
    echo "      username: admin"
    echo "      password: ${ADMIN_PASSWORD}"
    echo "  Only the bcrypt hash is kept, in ${API_ENV_FILE} (root 0600)."
    echo "  ============================================================"
    echo ""
fi

# 8. Systemd services
log "Installing systemd services..."

cat > /etc/systemd/system/sigmavault-engined.service <<SVCEOF
[Unit]
Description=SigmaVault NAS OS Python Engine (RPC + Agents)
After=network.target

[Service]
Type=simple
User=sigmavault
Group=sigmavault
Environment=PYTHONPATH=/opt/sigmavault/src/engined
Environment=SIGMAVAULT_CONFIG=/etc/sigmavault/config.yaml
Environment=SIGMAVAULT_PORT=5000
ExecStart=/usr/bin/python3 -m engined.main
WorkingDirectory=/opt/sigmavault/src/engined
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/sigmavault /var/log/sigmavault
MemoryMax=4G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/systemd/system/sigmavault-api.service <<SVCEOF
[Unit]
Description=SigmaVault NAS OS API Server
After=network.target sigmavault-engined.service
Requires=sigmavault-engined.service

[Service]
Type=simple
User=sigmavault
Group=sigmavault
Environment=SIGMAVAULT_CONFIG=/etc/sigmavault/config.yaml
Environment=SIGMAVAULT_PORT=12080
Environment=SIGMAVAULT_RPC_URL=http://127.0.0.1:5000/api/v1
# Bind loopback-only (SECURITY): was 0.0.0.0:12080 (all interfaces). Set to 10.88.0.1 to
# expose on wg0, or 0.0.0.0 only behind a firewall. Consumers (brain-snapshot, sigma-vault-ui,
# Prometheus) are all on-host, so loopback is sufficient.
Environment=SIGMAVAULT_HOST=127.0.0.1
# Production auth floor (SECURITY): forces real JWT + CORS validation, no dev bypass.
Environment=SIGMAVAULT_ENV=production
# JWT secret + CORS from the root-owned 0600 env file (step 7b) — secret never in this unit.
EnvironmentFile=${CONFIG_DIR}/api.env
ExecStart=/opt/sigmavault/bin/sigmavault-api
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/sigmavault /var/log/sigmavault
MemoryMax=1G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
ok "Systemd services installed"

# 9. Enable and start
log "Enabling and starting services..."
systemctl enable sigmavault-engined sigmavault-api
systemctl restart sigmavault-engined
sleep 3
systemctl restart sigmavault-api
sleep 3
ok "Services started"

# 10. Health check
log "Running health check..."
HEALTH=""
for i in $(seq 1 12); do
    HEALTH=$(curl -sf "http://localhost:${API_PORT}/api/v1/health" 2>/dev/null || true)
    if [[ -n "$HEALTH" ]]; then break; fi
    log "  Waiting... (${i}/12)"
    sleep 5
done

if [[ -z "${HEALTH}" ]]; then
    echo ""
    echo "WARNING: Health check timed out. Recent logs:"
    journalctl -u sigmavault-api -n 30 --no-pager
    exit 1
fi

ok "Health check passed: ${HEALTH:0:120}"

echo ""
echo "======================================="
echo "  Deployment complete!"
echo "======================================="
echo "  API:    http://localhost:${API_PORT}"
echo "  Health: http://localhost:${API_PORT}/api/v1/health"
echo "  Logs:   journalctl -u sigmavault-api -f"
echo "======================================="
echo ""
