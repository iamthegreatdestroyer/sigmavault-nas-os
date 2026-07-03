"""
Integration test for AgentSwarm's crypto methods.

test_crypto_bridge.py proves CryptoBridge itself is correct in isolation.
This proves the actual call path the API endpoints use --
AgentSwarm.generate_encryption_key() / .submit_encryption_task() -- wires
through to it correctly, since those two methods did not exist at all
before this fix (every call was an AttributeError, regardless of
algorithm).
"""

import pytest

from engined.agents.swarm import AgentSwarm


@pytest.fixture
async def swarm():
    s = AgentSwarm()
    await s.initialize()
    yield s
    await s.stop()


class TestSwarmCryptoIntegration:
    async def test_generate_key_through_swarm(self, swarm):
        result = await swarm.generate_encryption_key(
            key_id="itest-key", algorithm="hybrid-kyber-aes", key_type="hybrid"
        )
        assert result["key_id"] == "itest-key"
        assert result["fingerprint"]

    async def test_encrypt_decrypt_round_trip_through_swarm(self, swarm, tmp_path):
        plaintext = b"end to end through the real AgentSwarm call path"
        source = tmp_path / "plain.txt"
        source.write_bytes(plaintext)

        await swarm.generate_encryption_key(
            key_id="itest-key-2", algorithm="hybrid-kyber-aes", key_type="hybrid"
        )

        enc = await swarm.submit_encryption_task(
            source_path=str(source),
            operation="encrypt",
            algorithm="hybrid-kyber-aes",
            key_id="itest-key-2",
            compress_first=True,
            destination_path=str(tmp_path / "plain.txt.svenc"),
        )
        assert enc["key_id"] == "itest-key-2"

        dec = await swarm.submit_encryption_task(
            source_path=enc["destination_path"],
            operation="decrypt",
            algorithm="hybrid-kyber-aes",
            key_id="itest-key-2",
            compress_first=True,
            destination_path=str(tmp_path / "decrypted.txt"),
        )

        assert (tmp_path / "decrypted.txt").read_bytes() == plaintext
        assert dec["file_size"] == len(plaintext)
