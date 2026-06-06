#!/bin/bash
set -e

SYSDIR=/etc/systemd/system
SRCDIR=/opt/sigmavault/live-build/config/includes.chroot/etc/systemd/system

for svc in sigmavault-engined sigmavault-api sigmavault-webui; do
    cp "$SRCDIR/$svc.service" "$SYSDIR/"
done

systemctl daemon-reload

systemctl start sigmavault-engined
echo "sigmavault-engined started (port 5000)"

systemctl start sigmavault-api
echo "sigmavault-api started (port 12080)"

systemctl start sigmavault-webui
echo "sigmavault-webui started (port 3000)"

echo ""
echo "=== Status ==="
systemctl status sigmavault-engined --no-pager -l
echo ""
systemctl status sigmavault-api --no-pager -l
