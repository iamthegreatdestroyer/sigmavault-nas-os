"""
Copyright 2025 Stephen Bilodeau. All Rights Reserved.
SigmaVault NAS OS - Compression Bridge

Bridge module connecting SigmaVault engined to EliteSigma-NAS compression engine.
Provides a clean interface for AI-powered compression operations.
"""

import sys
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Add EliteSigma-NAS to path
ELITESIGMA_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "submodules" / "EliteSigma-NAS" / "src"
if ELITESIGMA_PATH.exists():
    sys.path.insert(0, str(ELITESIGMA_PATH))
    logger.info(f"EliteSigma-NAS path added: {ELITESIGMA_PATH}")
else:
    logger.warning(f"EliteSigma-NAS not found at: {ELITESIGMA_PATH}")


class CompressionLevel(Enum):
    """Compression level presets."""
    FAST = "fast"         # Quick compression, lower ratio
    BALANCED = "balanced" # Balance speed and ratio
    MAXIMUM = "maximum"   # Best ratio, slower
    ADAPTIVE = "adaptive" # AI-selected based on content


@dataclass
class CompressionConfig:
    """Configuration for compression operations."""
    level: CompressionLevel = CompressionLevel.BALANCED
    chunk_size: int = 1024 * 1024  # 1MB chunks
    use_semantic: bool = True       # Use ΣLANG semantic compression
    use_transformer: bool = False   # Use transformer embeddings (slower)
    lossless: bool = True           # Ensure lossless compression
    max_codebook_size: int = 10000  # Max glyph count
    parallel_chunks: int = 4        # Parallel processing threads


@dataclass
class CompressionProgress:
    """Progress update for compression operations."""
    job_id: str
    bytes_processed: int
    bytes_total: int
    elapsed_seconds: float
    eta_seconds: float
    current_ratio: float
    phase: str  # "analyzing", "compressing", "finalizing"
    chunks_complete: int
    chunks_total: int


@dataclass
class CompressionResult:
    """Result of a compression operation."""
    job_id: str
    success: bool
    original_size: int
    compressed_size: int
    compression_ratio: float
    elapsed_seconds: float
    data_type: str
    method: str
    checksum: str
    is_lossless: bool
    output_path: Optional[str] = None
    compressed_data: Optional[bytes] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompressionBridge:
    """
    Bridge to EliteSigma-NAS compression engine.
    
    Provides:
    - Async compression/decompression operations
    - Progress callbacks for real-time updates
    - Automatic data type detection
    - ΣLANG semantic compression
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        """Initialize compression bridge."""
        self.config = config or CompressionConfig()
        self._engine = None
        self._codebook = None
        self._initialized = False
        self._progress_callbacks: list[Callable[[CompressionProgress], Awaitable[None]]] = []

    async def initialize(self) -> bool:
        """
        Initialize the compression engine.
        
        Returns:
            True if initialization successful, False otherwise.
        """
        if self._initialized:
            return True

        try:
            # Import EliteSigma-NAS components
            from nas_core.compression_engine import (
                CompressionEngine,
                SigmaCodebook,
                DataTypeDetector,
            )
            
            # Initialize codebook
            self._codebook = SigmaCodebook(max_glyphs=self.config.max_codebook_size)
            
            # Initialize engine
            self._engine = CompressionEngine(codebook=self._codebook)
            
            self._initialized = True
            logger.info("CompressionBridge initialized successfully")
            return True
            
        except ImportError as e:
            logger.warning(f"EliteSigma-NAS not available: {e}")
            # Fall back to stub implementation
            self._engine = StubCompressionEngine()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize compression engine: {e}")
            return False

    def add_progress_callback(
        self,
        callback: Callable[[CompressionProgress], Awaitable[None]]
    ) -> None:
        """Register a callback for progress updates."""
        self._progress_callbacks.append(callback)

    def remove_progress_callback(
        self,
        callback: Callable[[CompressionProgress], Awaitable[None]]
    ) -> None:
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    async def _emit_progress(self, progress: CompressionProgress) -> None:
        """Emit progress to all registered callbacks."""
        for callback in self._progress_callbacks:
            try:
                await callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    async def compress_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> CompressionResult:
        """
        Compress a file using AI-powered compression.
        
        Args:
            input_path: Path to input file.
            output_path: Path for compressed output (optional).
            job_id: Job identifier for tracking.
            
        Returns:
            CompressionResult with compression statistics.
        """
        if not self._initialized:
            await self.initialize()

        job_id = job_id or f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        try:
            # Read input file
            input_file = Path(input_path)
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            original_data = input_file.read_bytes()
            original_size = len(original_data)

            # Emit initial progress
            await self._emit_progress(CompressionProgress(
                job_id=job_id,
                bytes_processed=0,
                bytes_total=original_size,
                elapsed_seconds=0,
                eta_seconds=0,
                current_ratio=1.0,
                phase="analyzing",
                chunks_complete=0,
                chunks_total=max(1, original_size // self.config.chunk_size),
            ))

            # Compress data
            result = await self.compress_data(original_data, job_id)

            # Write output if path provided
            if output_path and result.success and result.compressed_data:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_bytes(result.compressed_data)
                result.output_path = str(output_file)

            return result

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Compression failed for {input_path}: {e}")
            return CompressionResult(
                job_id=job_id,
                success=False,
                original_size=0,
                compressed_size=0,
                compression_ratio=0.0,
                elapsed_seconds=elapsed,
                data_type="unknown",
                method="none",
                checksum="",
                is_lossless=True,
                error=str(e),
            )

    async def compress_data(
        self,
        data: bytes,
        job_id: Optional[str] = None,
    ) -> CompressionResult:
        """
        Compress raw bytes using AI-powered compression.
        
        Args:
            data: Raw bytes to compress.
            job_id: Job identifier for tracking.
            
        Returns:
            CompressionResult with compressed data and statistics.
        """
        if not self._initialized:
            await self.initialize()

        job_id = job_id or f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        original_size = len(data)

        try:
            # Detect data type
            from nas_core.compression_engine import DataTypeDetector
            data_type = DataTypeDetector.detect(data)
        except ImportError:
            data_type = "unknown"

        try:
            # Process in chunks with progress updates
            chunk_size = self.config.chunk_size
            chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
            total_chunks = len(chunks)
            
            compressed_chunks = []
            bytes_processed = 0
            current_ratio = 1.0  # Initialize for empty data edge case

            for i, chunk in enumerate(chunks):
                chunk_start = datetime.now()
                
                # Compress chunk
                compressed_chunk = await self._compress_chunk(chunk)
                compressed_chunks.append(compressed_chunk)
                
                bytes_processed += len(chunk)
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Calculate ETA
                if bytes_processed > 0:
                    rate = bytes_processed / elapsed
                    remaining = original_size - bytes_processed
                    eta = remaining / rate if rate > 0 else 0
                else:
                    eta = 0

                # Calculate current ratio
                compressed_so_far = sum(len(c) for c in compressed_chunks)
                current_ratio = bytes_processed / compressed_so_far if compressed_so_far > 0 else 1.0

                # Emit progress
                await self._emit_progress(CompressionProgress(
                    job_id=job_id,
                    bytes_processed=bytes_processed,
                    bytes_total=original_size,
                    elapsed_seconds=elapsed,
                    eta_seconds=eta,
                    current_ratio=current_ratio,
                    phase="compressing",
                    chunks_complete=i + 1,
                    chunks_total=total_chunks,
                ))

            # Finalize
            await self._emit_progress(CompressionProgress(
                job_id=job_id,
                bytes_processed=original_size,
                bytes_total=original_size,
                elapsed_seconds=(datetime.now() - start_time).total_seconds(),
                eta_seconds=0,
                current_ratio=current_ratio,
                phase="finalizing",
                chunks_complete=total_chunks,
                chunks_total=total_chunks,
            ))

            # Combine compressed chunks
            compressed_data = b"".join(compressed_chunks)
            compressed_size = len(compressed_data)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0

            # Calculate checksum
            import hashlib
            checksum = hashlib.sha256(data).hexdigest()

            elapsed = (datetime.now() - start_time).total_seconds()

            return CompressionResult(
                job_id=job_id,
                success=True,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                elapsed_seconds=elapsed,
                data_type=str(data_type) if hasattr(data_type, '__str__') else "unknown",
                method="semantic" if self.config.use_semantic else "standard",
                checksum=checksum,
                is_lossless=self.config.lossless,
                compressed_data=compressed_data,
                metadata={
                    "chunks": total_chunks,
                    "chunk_size": chunk_size,
                    "level": self.config.level.value,
                },
            )

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Compression failed: {e}")
            return CompressionResult(
                job_id=job_id,
                success=False,
                original_size=original_size,
                compressed_size=0,
                compression_ratio=0.0,
                elapsed_seconds=elapsed,
                data_type=str(data_type) if hasattr(data_type, '__str__') else "unknown",
                method="none",
                checksum="",
                is_lossless=True,
                error=str(e),
            )

    async def _compress_chunk(self, chunk: bytes) -> bytes:
        """Compress a single chunk."""
        if self._engine is None:
            return chunk

        # Run compression in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._engine.compress,
            chunk,
        )

    async def decompress_file(
        self,
        input_path: str,
        output_path: str,
        job_id: Optional[str] = None,
    ) -> CompressionResult:
        """
        Decompress a file.
        
        Args:
            input_path: Path to compressed file.
            output_path: Path for decompressed output.
            job_id: Job identifier for tracking.
            
        Returns:
            CompressionResult with decompression statistics.
        """
        if not self._initialized:
            await self.initialize()

        job_id = job_id or f"decomp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        try:
            input_file = Path(input_path)
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            compressed_data = input_file.read_bytes()
            result = await self.decompress_data(compressed_data, job_id)

            if result.success and result.compressed_data:
                # Note: For decompress, compressed_data contains the decompressed output
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_bytes(result.compressed_data)
                result.output_path = str(output_file)

            return result

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Decompression failed for {input_path}: {e}")
            return CompressionResult(
                job_id=job_id,
                success=False,
                original_size=0,
                compressed_size=0,
                compression_ratio=0.0,
                elapsed_seconds=elapsed,
                data_type="unknown",
                method="none",
                checksum="",
                is_lossless=True,
                error=str(e),
            )

    async def decompress_data(
        self,
        data: bytes,
        job_id: Optional[str] = None,
    ) -> CompressionResult:
        """
        Decompress raw bytes.
        
        Args:
            data: Compressed bytes to decompress.
            job_id: Job identifier for tracking.
            
        Returns:
            CompressionResult with decompressed data.
        """
        if not self._initialized:
            await self.initialize()

        job_id = job_id or f"decomp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        compressed_size = len(data)

        try:
            # Decompress
            if self._engine is None:
                decompressed_data = data
            else:
                loop = asyncio.get_event_loop()
                decompressed_data = await loop.run_in_executor(
                    None,
                    self._engine.decompress,
                    data,
                )

            original_size = len(decompressed_data)
            elapsed = (datetime.now() - start_time).total_seconds()

            import hashlib
            checksum = hashlib.sha256(decompressed_data).hexdigest()

            return CompressionResult(
                job_id=job_id,
                success=True,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=original_size / compressed_size if compressed_size > 0 else 1.0,
                elapsed_seconds=elapsed,
                data_type="decompressed",
                method="semantic",
                checksum=checksum,
                is_lossless=True,
                compressed_data=decompressed_data,  # Contains decompressed output
            )

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Decompression failed: {e}")
            return CompressionResult(
                job_id=job_id,
                success=False,
                original_size=0,
                compressed_size=compressed_size,
                compression_ratio=0.0,
                elapsed_seconds=elapsed,
                data_type="unknown",
                method="none",
                checksum="",
                is_lossless=True,
                error=str(e),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get compression engine statistics."""
        stats = {
            "initialized": self._initialized,
            "engine_type": type(self._engine).__name__ if self._engine else "none",
            "config": {
                "level": self.config.level.value,
                "chunk_size": self.config.chunk_size,
                "use_semantic": self.config.use_semantic,
                "lossless": self.config.lossless,
            },
        }

        if self._codebook:
            stats["codebook"] = {
                "glyphs": len(self._codebook.glyphs) if hasattr(self._codebook, 'glyphs') else 0,
                "max_glyphs": self._codebook.max_glyphs if hasattr(self._codebook, 'max_glyphs') else 0,
            }

        return stats


class StubCompressionEngine:
    """
    Stub compression engine for when EliteSigma-NAS is not available.
    Provides basic zlib compression as fallback.
    """

    def __init__(self):
        """Initialize stub engine."""
        import zlib
        self._zlib = zlib
        logger.info("Using StubCompressionEngine (zlib fallback)")

    def compress(self, data: bytes) -> bytes:
        """Compress data using zlib."""
        return self._zlib.compress(data, level=6)

    def decompress(self, data: bytes) -> bytes:
        """Decompress data using zlib."""
        return self._zlib.decompress(data)
