"""SigmaVault Native UI - GNOME desktop application for compression management."""

__version__ = "0.1.0"
__author__ = "SigmaVault Dev Team"

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
