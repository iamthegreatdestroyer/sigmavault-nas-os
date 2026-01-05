"""
SigmaVault RPC Package

Contains gRPC service definitions and implementations.
"""

from .server import create_grpc_server

__all__ = ['create_grpc_server']