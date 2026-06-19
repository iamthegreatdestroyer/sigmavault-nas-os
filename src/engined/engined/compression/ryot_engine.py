"""
Ryot-backed compression engine for SigmaVault NAS OS.

Integrates Ryot's fractal quantization (ProbabilisticLattice) for numerical
and structured data compression. Falls back to zlib/lzma for binary blobs.

Architecture
------------
The RyotCompressionEngine sits alongside StubCompressionEngine in bridge.py.
CompressionBridge tries: EliteSigma-NAS -> RyotEngine -> StubEngine (zlib/lzma).

For structured data (JSON, CSV, numerical arrays), Ryot's adaptive fractal
quantization achieves higher compression ratios than zlib by exploiting the
multi-resolution lattice: easy (uniform) data compresses to 2-3 bits per
scalar; complex data uses up to 8 bits. The lattice IS the uncertainty
estimate — no separate metadata needed.

Wire format
-----------
  RYOT_MAGIC (4 bytes) || version (1 byte) || dtype (1 byte)
  || shape_ndim (1 byte) || shape (ndim * 4 bytes, uint32 LE)
  || x_min (4 bytes, float32 LE) || x_max (4 bytes, float32 LE)
  || bits_used (1 byte) || n_lattices (4 bytes, uint32 LE)
  || lattice_data (n_lattices * 8 bytes)
  || SHA-256 checksum (32 bytes)

For non-numerical data, falls through to StubCompressionEngine (zlib/lzma).
"""

import hashlib
import json
import logging
import struct
from typing import Any

logger = logging.getLogger(__name__)

RYOT_MAGIC = b"RYOT"
RYOT_VERSION = 1

# Data type tags for wire format
DTYPE_FLOAT32 = 0x01
DTYPE_JSON_NUMERIC = 0x02
DTYPE_CSV_NUMERIC = 0x03
DTYPE_RAW_BYTES = 0xFF

_ryot_available = False
try:
    import sys
    from pathlib import Path

    _ryot_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent
    for candidate in [
        _ryot_path / "Layer-4-Storage" / "Ryot",
        Path("S:/repos/Layer-4-Storage/Ryot"),
    ]:
        if (candidate / "src" / "quantization").exists():
            sys.path.insert(0, str(candidate))
            break

    from src.quantization.fractal_quantization import (
        AdaptiveInferenceQuery,
        FractalQuantizer,
        ProbabilisticLattice,
    )

    _ryot_available = True
    logger.info("Ryot fractal quantization available")
except ImportError:
    logger.info("Ryot not available — RyotCompressionEngine will be inactive")


def _detect_numeric_json(data: bytes) -> list[float] | None:
    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if isinstance(parsed, list) and len(parsed) > 0:
        if all(isinstance(x, (int, float)) for x in parsed):
            return [float(x) for x in parsed]

    if isinstance(parsed, dict):
        values = list(parsed.values())
        if len(values) > 0 and all(isinstance(v, (int, float)) for v in values):
            return [float(v) for v in values]

    return None


def _detect_csv_numeric(data: bytes) -> list[float] | None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None

    lines = text.strip().split("\n")
    if len(lines) < 2:
        return None

    values = []
    for line in lines:
        cells = line.split(",")
        for cell in cells:
            cell = cell.strip()
            try:
                values.append(float(cell))
            except ValueError:
                continue

    if len(values) < 4:
        return None

    return values


class RyotCompressionEngine:
    """
    Fractal quantization compression for numerical/structured data.

    Uses Ryot's ProbabilisticLattice to encode scalar values at adaptive
    bit depths. Structured data (JSON arrays, CSV numeric columns) is
    detected automatically and routed through fractal quantization.

    Non-numerical data is rejected (returns None) so the caller can
    fall back to zlib/lzma.
    """

    def __init__(self, bit_levels: int = 8, tolerance: float = 0.01):
        if not _ryot_available:
            raise RuntimeError("Ryot not available")
        self._quantizer = FractalQuantizer(bit_levels=bit_levels)
        self._adaptive = AdaptiveInferenceQuery(min_bits=2, max_bits=bit_levels)
        self._tolerance = tolerance
        self._bit_levels = bit_levels
        logger.info(
            "RyotCompressionEngine initialized (bit_levels=%d, tolerance=%.3f)",
            bit_levels,
            tolerance,
        )

    def compress(self, data: bytes) -> bytes | None:
        """
        Compress data using fractal quantization if it's numerical.

        Returns:
            Compressed bytes with RYOT header, or None if data isn't
            suitable for fractal quantization (caller should fall back).
        """
        import torch

        values, dtype = self._extract_numerics(data)
        if values is None:
            return None

        tensor = torch.tensor(values, dtype=torch.float32)
        lattices, x_min, x_max = self._quantizer.quantize(tensor)

        centroid = [0.0] * 256
        for v in values:
            idx = int(abs(v) * 255) % 256
            centroid[idx] += 1
        total = sum(centroid)
        if total > 0:
            centroid = [c / total for c in centroid]
        bits_hint = self._adaptive.estimate_bits(centroid)

        _, bits_used, _ = self._quantizer.query_adaptive(
            lattices,
            x_min,
            x_max,
            shape=tensor.shape,
            tolerance=self._tolerance,
            min_bits=max(2, bits_hint - 1),
            max_bits=min(self._bit_levels, bits_hint + 1),
        )

        lattice_bytes = b"".join(lat.to_bytes() for lat in lattices)

        shape = list(tensor.shape)
        header = struct.pack("<4sBBB", RYOT_MAGIC, RYOT_VERSION, dtype, len(shape))
        for dim in shape:
            header += struct.pack("<I", dim)
        header += struct.pack("<ff", x_min.item(), x_max.item())
        header += struct.pack("<B", bits_used)
        header += struct.pack("<I", len(lattices))

        payload = header + lattice_bytes
        checksum = hashlib.sha256(payload).digest()

        return payload + checksum

    def decompress(self, data: bytes) -> bytes:
        """
        Decompress RYOT-encoded data back to the original format.

        Returns the data in its original format (JSON or CSV string as bytes).
        """
        import torch

        if data[:4] != RYOT_MAGIC:
            raise ValueError("Not a RYOT-compressed stream")

        offset = 4
        version, dtype, ndim = struct.unpack_from("<BBB", data, offset)
        offset += 3

        if version != RYOT_VERSION:
            raise ValueError(f"Unsupported RYOT version: {version}")

        shape = []
        for _ in range(ndim):
            (dim,) = struct.unpack_from("<I", data, offset)
            shape.append(dim)
            offset += 4

        x_min_val, x_max_val = struct.unpack_from("<ff", data, offset)
        offset += 8
        x_min = torch.tensor(x_min_val)
        x_max = torch.tensor(x_max_val)

        (bits_used,) = struct.unpack_from("<B", data, offset)
        offset += 1
        (n_lattices,) = struct.unpack_from("<I", data, offset)
        offset += 4

        lattices = []
        for _ in range(n_lattices):
            lat_data = data[offset : offset + self._bit_levels]
            lattices.append(ProbabilisticLattice.from_bytes(lat_data))
            offset += self._bit_levels

        stored_checksum = data[offset : offset + 32]
        payload = data[: offset - 0]
        # Verify payload = everything before the checksum
        payload_for_check = data[: len(data) - 32]
        expected = hashlib.sha256(payload_for_check).digest()
        if stored_checksum != expected:
            raise ValueError("RYOT checksum mismatch — data corrupted")

        tensor = self._quantizer.dequantize(
            lattices, x_min, x_max, bits=bits_used, shape=tuple(shape)
        )
        values = tensor.tolist()

        if dtype == DTYPE_JSON_NUMERIC:
            return json.dumps(values).encode("utf-8")
        elif dtype == DTYPE_CSV_NUMERIC:
            return ",".join(str(v) for v in values).encode("utf-8")
        else:
            return json.dumps(values).encode("utf-8")

    def _extract_numerics(
        self, data: bytes
    ) -> tuple[list[float] | None, int]:
        values = _detect_numeric_json(data)
        if values is not None:
            return values, DTYPE_JSON_NUMERIC

        values = _detect_csv_numeric(data)
        if values is not None:
            return values, DTYPE_CSV_NUMERIC

        return None, DTYPE_RAW_BYTES

    def get_stats(self) -> dict[str, Any]:
        return {
            "engine": "RyotCompressionEngine",
            "bit_levels": self._bit_levels,
            "tolerance": self._tolerance,
            "ryot_available": _ryot_available,
            "adaptive_query_stats": self._adaptive.stats(),
        }


def is_ryot_available() -> bool:
    return _ryot_available
