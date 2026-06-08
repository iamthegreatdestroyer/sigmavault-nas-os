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
GO_VERSION="1.25.0"

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
    curl wget ca-certificates \
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
    rm -rf /usr/local/go
    tar -C /usr/local -xzf /tmp/go.tar.gz
    rm /tmp/go.tar.gz
    ok "Go ${GO_VERSION} installed"
fi
export PATH="/usr/local/go/bin:$PATH"

# 3. Python packages
log "Installing Python packages..."
pip3 install --break-system-packages --quiet \
    aiohttp structlog prometheus-client \
    pydantic pydantic-settings \
    fastapi starlette httpx psutil \
    zstandard lz4 brotli \
    grpcio grpcio-tools protobuf \
    anyio "numpy>=2.0.0"
ok "Python packages installed"

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
  host: "0.0.0.0"
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
