"""
Unit tests for the real crypto backend (engined.crypto.bridge).

Before this module existed, AgentSwarm.generate_encryption_key and
.submit_encryption_task did not exist at all -- every encryption API call
crashed with AttributeError regardless of algorithm. These tests prove
each of the four advertised algorithms now does real, correct,
round-tripping file encryption, and that decrypting with the wrong
algorithm or a tampered file is rejected rather than silently mishandled.
"""

import os
from pathlib import Path

import pytest

from engined.crypto.bridge import CryptoAlgorithm, CryptoBridge

ALL_ALGORITHMS = [
    CryptoAlgorithm.AES_256_GCM,
    CryptoAlgorithm.CHACHA20_POLY1305,
    CryptoAlgorithm.KYBER_1024,
    CryptoAlgorithm.HYBRID_KYBER_AES,
]


class TestKeyGeneration:
    def test_generate_key_returns_real_fingerprint(self):
        bridge = CryptoBridge()
        result = bridge.generate_key("key-1", CryptoAlgorithm.HYBRID_KYBER_AES.value)
        assert result["key_id"] == "key-1"
        assert len(result["fingerprint"]) == 64  # sha256 hex digest

    def test_two_generated_keys_have_different_fingerprints(self):
        bridge = CryptoBridge()
        a = bridge.generate_key("key-a", CryptoAlgorithm.AES_256_GCM.value)
        b = bridge.generate_key("key-b", CryptoAlgorithm.AES_256_GCM.value)
        assert a["fingerprint"] != b["fingerprint"]

    @pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
    def test_generate_key_works_for_every_advertised_algorithm(self, algorithm):
        bridge = CryptoBridge()
        result = bridge.generate_key("key-1", algorithm.value)
        assert result["key_id"] == "key-1"
        assert result["fingerprint"]


class TestFileEncryptDecryptRoundTrip:
    @pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
    def test_round_trip_recovers_original_bytes(self, tmp_path, algorithm):
        plaintext = b"the ecosystem is only as strong as its weakest link"
        source = tmp_path / "plain.txt"
        source.write_bytes(plaintext)
        encrypted_path = str(tmp_path / "plain.txt.svenc")
        decrypted_path = str(tmp_path / "plain.decrypted.txt")

        bridge = CryptoBridge()
        enc_result = bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=algorithm.value,
            key_id=None,
            compress_first=False,
            destination_path=encrypted_path,
        )
        assert enc_result["key_id"]
        assert os.path.exists(encrypted_path)
        # Ciphertext must not just be the plaintext copied through.
        assert Path(encrypted_path).read_bytes() != plaintext

        dec_result = bridge.run_task(
            source_path=encrypted_path,
            operation="decrypt",
            algorithm=algorithm.value,
            key_id=enc_result["key_id"],
            compress_first=False,
            destination_path=decrypted_path,
        )
        assert Path(decrypted_path).read_bytes() == plaintext
        assert dec_result["file_size"] == len(plaintext)

    @pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
    def test_compress_first_round_trips_correctly(self, tmp_path, algorithm):
        plaintext = b"AAAA" * 5000  # compressible
        source = tmp_path / "plain.txt"
        source.write_bytes(plaintext)
        encrypted_path = str(tmp_path / "plain.txt.svenc")
        decrypted_path = str(tmp_path / "plain.decrypted.txt")

        bridge = CryptoBridge()
        enc_result = bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=algorithm.value,
            key_id=None,
            compress_first=True,
            destination_path=encrypted_path,
        )
        assert Path(encrypted_path).stat().st_size < len(plaintext)

        bridge.run_task(
            source_path=encrypted_path,
            operation="decrypt",
            algorithm=algorithm.value,
            key_id=enc_result["key_id"],
            compress_first=True,
            destination_path=decrypted_path,
        )
        assert Path(decrypted_path).read_bytes() == plaintext

    def test_encrypt_without_key_id_autogenerates_and_returns_it(self, tmp_path):
        source = tmp_path / "plain.txt"
        source.write_bytes(b"auto key test")
        bridge = CryptoBridge()

        result = bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=CryptoAlgorithm.HYBRID_KYBER_AES.value,
            key_id=None,
            compress_first=False,
            destination_path=str(tmp_path / "out.svenc"),
        )
        assert result["key_id"] in bridge._keys

    def test_encrypt_without_destination_path_defaults_to_svenc_suffix(self, tmp_path):
        source = tmp_path / "plain.txt"
        source.write_bytes(b"default destination test")
        bridge = CryptoBridge()

        result = bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=CryptoAlgorithm.AES_256_GCM.value,
            key_id=None,
            compress_first=False,
        )
        assert result["destination_path"] == str(source) + ".svenc"
        assert os.path.exists(result["destination_path"])


class TestErrorHandling:
    def test_decrypt_without_key_id_raises(self, tmp_path):
        bridge = CryptoBridge()
        with pytest.raises(ValueError, match="key_id is required"):
            bridge.run_task(
                source_path=str(tmp_path / "nope.svenc"),
                operation="decrypt",
                algorithm=CryptoAlgorithm.AES_256_GCM.value,
                key_id=None,
                compress_first=False,
                destination_path=str(tmp_path / "out.txt"),
            )

    def test_decrypt_without_destination_path_raises(self, tmp_path):
        bridge = CryptoBridge()
        with pytest.raises(ValueError, match="destination_path is required"):
            bridge.run_task(
                source_path=str(tmp_path / "nope.svenc"),
                operation="decrypt",
                algorithm=CryptoAlgorithm.AES_256_GCM.value,
                key_id="whatever",
                compress_first=False,
            )

    def test_decrypt_with_unknown_key_id_raises_keyerror(self, tmp_path):
        source = tmp_path / "plain.txt"
        source.write_bytes(b"data")
        bridge = CryptoBridge()
        enc = bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=CryptoAlgorithm.AES_256_GCM.value,
            key_id=None,
            compress_first=False,
            destination_path=str(tmp_path / "out.svenc"),
        )
        with pytest.raises(KeyError):
            bridge.run_task(
                source_path=enc["destination_path"],
                operation="decrypt",
                algorithm=CryptoAlgorithm.AES_256_GCM.value,
                key_id="nonexistent-key-id",
                compress_first=False,
                destination_path=str(tmp_path / "out.txt"),
            )

    def test_decrypt_with_wrong_algorithm_is_rejected(self, tmp_path):
        """A file encrypted with one algorithm must not silently decrypt
        (or worse, silently produce garbage) under a different one."""
        source = tmp_path / "plain.txt"
        source.write_bytes(b"data")
        bridge = CryptoBridge()
        enc = bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=CryptoAlgorithm.HYBRID_KYBER_AES.value,
            key_id=None,
            compress_first=False,
            destination_path=str(tmp_path / "out.svenc"),
        )
        # A key generated for a different algorithm can't be used here either.
        bridge.generate_key("aes-key", CryptoAlgorithm.AES_256_GCM.value)
        with pytest.raises(ValueError):
            bridge.run_task(
                source_path=enc["destination_path"],
                operation="decrypt",
                algorithm=CryptoAlgorithm.AES_256_GCM.value,
                key_id="aes-key",
                compress_first=False,
                destination_path=str(tmp_path / "out.txt"),
            )

    def test_tampered_ciphertext_is_rejected_not_silently_decrypted(self, tmp_path):
        source = tmp_path / "plain.txt"
        source.write_bytes(b"do not trust me if tampered")
        bridge = CryptoBridge()
        enc = bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=CryptoAlgorithm.HYBRID_KYBER_AES.value,
            key_id=None,
            compress_first=False,
            destination_path=str(tmp_path / "out.svenc"),
        )

        raw = bytearray(Path(enc["destination_path"]).read_bytes())
        raw[-1] ^= 0xFF  # flip a bit in the trailing signature block
        Path(enc["destination_path"]).write_bytes(bytes(raw))

        with pytest.raises(RuntimeError):
            bridge.run_task(
                source_path=enc["destination_path"],
                operation="decrypt",
                algorithm=CryptoAlgorithm.HYBRID_KYBER_AES.value,
                key_id=enc["key_id"],
                compress_first=False,
                destination_path=str(tmp_path / "out.txt"),
            )

    def test_unrecognized_envelope_is_rejected(self, tmp_path):
        garbage_path = tmp_path / "garbage.svenc"
        garbage_path.write_bytes(b"not a real envelope at all")
        bridge = CryptoBridge()
        bridge.generate_key("key-1", CryptoAlgorithm.AES_256_GCM.value)

        with pytest.raises(ValueError, match="Not a recognized"):
            bridge.run_task(
                source_path=str(garbage_path),
                operation="decrypt",
                algorithm=CryptoAlgorithm.AES_256_GCM.value,
                key_id="key-1",
                compress_first=False,
                destination_path=str(tmp_path / "out.txt"),
            )


class TestShredOriginal:
    def test_shred_original_removes_source_file(self, tmp_path):
        source = tmp_path / "plain.txt"
        source.write_bytes(b"secret to be shredded")
        bridge = CryptoBridge()

        bridge.run_task(
            source_path=str(source),
            operation="encrypt",
            algorithm=CryptoAlgorithm.AES_256_GCM.value,
            key_id=None,
            compress_first=False,
            destination_path=str(tmp_path / "out.svenc"),
            shred_original=True,
        )
        assert not source.exists()
