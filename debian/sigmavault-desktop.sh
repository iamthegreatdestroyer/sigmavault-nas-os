#!/bin/sh
# Launcher script for SigmaVault Desktop UI

# Set Python path
export PYTHONPATH="/usr/lib/python3/dist-packages:${PYTHONPATH}"

# Set data directory for CSS and resources
export SIGMAVAULT_DATA_DIR="/usr/share/sigmavault-desktop"

# Run the application
exec python3 -m sigmavault_desktop "$@"
