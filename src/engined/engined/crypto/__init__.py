"""Real cryptographic backend (Kyber-1024, AES-256-GCM, ChaCha20-Poly1305,
Dilithium-3 signing) for the encryption API, replacing the previous facade
that called AgentSwarm methods which did not exist."""

from engined.crypto.bridge import CryptoAlgorithm, CryptoBridge

__all__ = ["CryptoAlgorithm", "CryptoBridge"]
