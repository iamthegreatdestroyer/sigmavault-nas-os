"""
Real cryptographic backend for the encryption API.

Delegates AES-256-GCM / Kyber-1024 / hybrid-Kyber-AES to the sigmavault
library (Kyber-1024 KEM, AES-256-GCM, Dilithium-3 signing), and implements
standalone ChaCha20-Poly1305 directly since sigmavault only offers
ChaCha20 paired with a Kyber exchange (its PQ_ONLY mode), never alone.

Previously `AgentSwarm.generate_encryption_key` / `.submit_encryption_task`
did not exist at all -- every call into this API crashed with
AttributeError regardless of algorithm. This module is the real
implementation those calls now delegate to.
"""

from __future__ import annotations

import hashlib
import os
import struct
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

import zstandard
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from sigmavault.crypto.hybrid_encryption import (
    EncryptionAlgorithm as VaultAlgorithm,
)
from sigmavault.crypto.hybrid_encryption import (
    HybridEncryptedData,
    HybridEncryption,
)
from sigmavault.crypto.hybrid_key_derivation import HybridKeyDerivation, HybridKeySet


class CryptoAlgorithm(str, Enum):
    """Mirrors engined.api.encryption.EncryptionAlgorithm -- kept as a
    separate enum so this module has no import dependency on the API layer."""

    AES_256_GCM = "aes-256-gcm"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    KYBER_1024 = "kyber-1024"
    HYBRID_KYBER_AES = "hybrid-kyber-aes"


# sigmavault's HybridEncryption already solves "a KEM alone can't encrypt a
# file" correctly: PQ_ONLY pairs Kyber-1024 with a ChaCha20-Poly1305 DEM, so
# kyber-1024 maps onto it directly rather than needing special handling.
_VAULT_ALGORITHM_MAP = {
    CryptoAlgorithm.AES_256_GCM: VaultAlgorithm.CLASSICAL_ONLY,
    CryptoAlgorithm.KYBER_1024: VaultAlgorithm.PQ_ONLY,
    CryptoAlgorithm.HYBRID_KYBER_AES: VaultAlgorithm.HYBRID,
}

# On-disk envelope. sigmavault's own HybridEncryptedData.to_bytes()/
# from_bytes() only round-trips the flat `ciphertext` field --
# from_bytes() returns an object with header/classical_ct/pq_ct/signatures
# all empty, so decrypt() on a from_bytes()-reconstructed object silently
# returns b'' with no error rather than raising. This envelope owns real
# serialization instead of depending on that.
#
# MAGIC(4) VERSION(1) ALG_TAG(1) FLAGS(1) then:
#   - chacha20-poly1305 (standalone): NONCE(12) + CIPHERTEXT(rest)
#   - everything else: 4x [LEN(4 BE) + bytes] for
#     header / classical_ct / pq_ct / signatures
_MAGIC = b"SVNE"
_VERSION = 1
_FLAG_COMPRESSED = 0x01

_ALG_TAG = {
    CryptoAlgorithm.AES_256_GCM: 0,
    CryptoAlgorithm.CHACHA20_POLY1305: 1,
    CryptoAlgorithm.KYBER_1024: 2,
    CryptoAlgorithm.HYBRID_KYBER_AES: 3,
}
_TAG_ALG = {v: k for k, v in _ALG_TAG.items()}


def _pack_envelope(algorithm: CryptoAlgorithm, compressed: bool, body: bytes) -> bytes:
    flags = _FLAG_COMPRESSED if compressed else 0
    out = bytearray()
    out += _MAGIC
    out.append(_VERSION)
    out.append(_ALG_TAG[algorithm])
    out.append(flags)
    out += body
    return bytes(out)


def _unpack_envelope(blob: bytes) -> tuple[CryptoAlgorithm, bool, bytes]:
    if len(blob) < 7 or blob[:4] != _MAGIC:
        raise ValueError("Not a recognized SigmaVault encryption envelope")
    version = blob[4]
    if version != _VERSION:
        raise ValueError(f"Unsupported envelope version {version}")
    algorithm = _TAG_ALG.get(blob[5])
    if algorithm is None:
        raise ValueError(f"Unknown algorithm tag {blob[5]} in envelope")
    compressed = bool(blob[6] & _FLAG_COMPRESSED)
    return algorithm, compressed, blob[7:]


def _pack_hybrid_body(data: HybridEncryptedData) -> bytes:
    out = bytearray()
    for part in (data.header, data.classical_ct, data.pq_ct, data.signatures):
        out += struct.pack(">I", len(part))
        out += part
    return bytes(out)


def _unpack_hybrid_body(body: bytes) -> HybridEncryptedData:
    offset = 0
    fields = []
    for _ in range(4):
        (length,) = struct.unpack_from(">I", body, offset)
        offset += 4
        fields.append(bytes(body[offset : offset + length]))
        offset += length
    header, classical_ct, pq_ct, signatures = fields
    return HybridEncryptedData(
        header=header,
        classical_ct=classical_ct,
        pq_ct=pq_ct,
        signatures=signatures,
    )


def _secure_delete(path: str) -> None:
    """Best-effort overwrite-then-unlink.

    Not a guarantee on SSDs or copy-on-write filesystems: wear-leveling
    and CoW snapshots can retain the original blocks regardless of what
    gets overwritten at the filesystem-visible path. Documented
    limitation, not a silent one -- callers should not treat this as
    forensic-grade erasure.
    """
    try:
        size = os.path.getsize(path)
        with open(path, "r+b") as f:
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
    finally:
        os.remove(path)


@dataclass
class KeyMaterial:
    """In-process handle for generated key material.

    Persistent, encrypted-at-rest key storage is a deliberate follow-up,
    not implemented here: keys currently live only in engined's process
    memory and do not survive a restart. Tracked as a known gap, not a
    silent one -- see CLAUDE.md.
    """

    algorithm: CryptoAlgorithm
    keyset: HybridKeySet | None = None  # for the 3 sigmavault-backed modes
    # Built once, here, at key-generation time -- and reused for every
    # later encrypt/decrypt against this key_id. HybridEncryption.__init__
    # generates a fresh, random Dilithium signing keypair on every
    # construction (real Dilithium keygen has no way to be derived from
    # the password-based keyset), so a *new* HybridEncryption(keyset, ...)
    # built later for a decrypt call would sign-verify against a
    # different, unrelated public key than the one that actually signed
    # the ciphertext -- decrypt would reject every file as "tampered"
    # even though nothing was. Persisting the same instance is what makes
    # encrypt-now-decrypt-later actually work.
    encryptor: HybridEncryption | None = None
    chacha_key: bytes | None = None  # for standalone chacha20-poly1305
    fingerprint: str = ""


class CryptoBridge:
    """Real crypto backend: Kyber-1024 KEM + AES-256-GCM + Dilithium-3
    signing via sigmavault, plus a standalone ChaCha20-Poly1305 path."""

    def __init__(self) -> None:
        self._keys: dict[str, KeyMaterial] = {}

    def generate_key(self, key_id: str, algorithm: str) -> dict[str, Any]:
        alg = CryptoAlgorithm(algorithm)

        if alg == CryptoAlgorithm.CHACHA20_POLY1305:
            raw_key = os.urandom(32)
            fingerprint = hashlib.sha256(raw_key).hexdigest()
            material = KeyMaterial(
                algorithm=alg, chacha_key=raw_key, fingerprint=fingerprint
            )
        else:
            derivation = HybridKeyDerivation()
            keyset = derivation.derive_hybrid_keys(
                password=os.urandom(32), salt=os.urandom(16)
            )
            encryptor = HybridEncryption(keyset, algorithm=_VAULT_ALGORITHM_MAP[alg])
            fingerprint = hashlib.sha256(keyset.hybrid_key).hexdigest()
            material = KeyMaterial(
                algorithm=alg, keyset=keyset, encryptor=encryptor, fingerprint=fingerprint
            )

        self._keys[key_id] = material
        return {"key_id": key_id, "fingerprint": material.fingerprint}

    def run_task(
        self,
        *,
        source_path: str,
        operation: str,
        algorithm: str,
        key_id: str | None,
        compress_first: bool,
        destination_path: str | None = None,
        shred_original: bool = False,
    ) -> dict[str, Any]:
        alg = CryptoAlgorithm(algorithm)

        if operation == "encrypt":
            if key_id is None:
                key_id = str(uuid.uuid4())
                self.generate_key(key_id, algorithm)
            if destination_path is None:
                destination_path = source_path + ".svenc"
            return self._encrypt_file(
                source_path, destination_path, alg, key_id, compress_first, shred_original
            )

        if operation == "decrypt":
            if key_id is None:
                raise ValueError("key_id is required to decrypt")
            if destination_path is None:
                raise ValueError("destination_path is required to decrypt")
            return self._decrypt_file(
                source_path, destination_path, alg, key_id, shred_original
            )

        raise ValueError(f"Unknown operation {operation!r}")

    def _require_key(self, key_id: str, algorithm: CryptoAlgorithm) -> KeyMaterial:
        material = self._keys.get(key_id)
        if material is None:
            raise KeyError(f"Key {key_id} not found")
        if material.algorithm != algorithm:
            raise ValueError(
                f"Key {key_id} was generated for {material.algorithm.value}, "
                f"not {algorithm.value}"
            )
        return material

    def _encrypt_file(
        self,
        source_path: str,
        destination_path: str,
        alg: CryptoAlgorithm,
        key_id: str,
        compress_first: bool,
        shred_original: bool,
    ) -> dict[str, Any]:
        material = self._require_key(key_id, alg)

        with open(source_path, "rb") as f:
            payload = f.read()

        if compress_first:
            payload = zstandard.ZstdCompressor().compress(payload)

        if alg == CryptoAlgorithm.CHACHA20_POLY1305:
            nonce = os.urandom(12)
            ciphertext = ChaCha20Poly1305(material.chacha_key).encrypt(
                nonce, payload, None
            )
            body = nonce + ciphertext
        else:
            encrypted = material.encryptor.encrypt(payload)
            body = _pack_hybrid_body(encrypted)

        blob = _pack_envelope(alg, compress_first, body)

        with open(destination_path, "wb") as f:
            f.write(blob)

        if shred_original:
            _secure_delete(source_path)

        return {
            "destination_path": destination_path,
            "key_id": key_id,
            "file_size": len(blob),
        }

    def _decrypt_file(
        self,
        source_path: str,
        destination_path: str,
        alg: CryptoAlgorithm,
        key_id: str,
        shred_original: bool,
    ) -> dict[str, Any]:
        material = self._require_key(key_id, alg)

        with open(source_path, "rb") as f:
            blob = f.read()

        envelope_alg, compressed, body = _unpack_envelope(blob)
        if envelope_alg != alg:
            raise ValueError(
                f"File was encrypted with {envelope_alg.value}, "
                f"not {alg.value} -- pass the matching algorithm to decrypt"
            )

        if alg == CryptoAlgorithm.CHACHA20_POLY1305:
            nonce, ciphertext = body[:12], body[12:]
            payload = ChaCha20Poly1305(material.chacha_key).decrypt(
                nonce, ciphertext, None
            )
        else:
            encrypted = _unpack_hybrid_body(body)
            payload = material.encryptor.decrypt(encrypted)

        plaintext = (
            zstandard.ZstdDecompressor().decompress(payload) if compressed else payload
        )

        with open(destination_path, "wb") as f:
            f.write(plaintext)

        if shred_original:
            _secure_delete(source_path)

        return {
            "destination_path": destination_path,
            "key_id": key_id,
            "file_size": len(plaintext),
        }
