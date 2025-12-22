"""
SigmaVault NAS OS - AI/ML RPC Engine

This package provides the Python-based RPC engine for SigmaVault NAS OS,
featuring a 40-agent AI swarm for compression, encryption, and storage optimization.

Architecture:
    - FastAPI for REST API interface
    - gRPC for high-performance inter-service communication
    - 40 specialized AI agents for various operations
    - Quantum-resistant encryption via liboqs
    - MNEMONIC memory system for agent learning

Author: SigmaVault Team
License: AGPL-3.0-or-later
"""

__version__ = "0.1.0"
__author__ = "SigmaVault Team"
__all__ = ["__version__", "__author__"]
