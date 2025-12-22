"""
Encryption API Endpoints

Provides REST API for quantum-resistant encryption operations.
Supports traditional (AES-256-GCM, ChaCha20-Poly1305) and post-quantum
(Kyber, Dilithium) cryptographic algorithms.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from engined.agents.swarm import AgentSwarm

router = APIRouter()


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms."""

    AES_256_GCM = "aes-256-gcm"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    KYBER_1024 = "kyber-1024"  # Post-quantum KEM
    HYBRID_KYBER_AES = "hybrid-kyber-aes"  # Recommended for future-proofing


class KeyType(str, Enum):
    """Key types for encryption operations."""

    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    HYBRID = "hybrid"


class OperationType(str, Enum):
    """Type of cryptographic operation."""

    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"


class JobStatus(str, Enum):
    """Encryption job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EncryptionRequest(BaseModel):
    """Request model for encryption operations."""

    source_path: str = Field(description="Source file or directory path")
    destination_path: str | None = Field(
        default=None,
        description="Destination path",
    )
    operation: OperationType = Field(
        default=OperationType.ENCRYPT,
        description="Encrypt or decrypt",
    )
    algorithm: EncryptionAlgorithm = Field(
        default=EncryptionAlgorithm.HYBRID_KYBER_AES,
        description="Encryption algorithm",
    )
    key_id: str | None = Field(
        default=None,
        description="Key identifier (generates new if not provided)",
    )
    compress_first: bool = Field(
        default=True,
        description="Compress before encrypting (encrypt only)",
    )
    shred_original: bool = Field(
        default=False,
        description="Securely delete original after encryption",
    )


class EncryptionResult(BaseModel):
    """Result model for encryption operations."""

    job_id: str
    status: JobStatus
    operation: OperationType
    source_path: str
    destination_path: str | None
    algorithm: str
    key_id: str | None
    file_size: int | None
    time_elapsed_ms: int | None
    created_at: str
    completed_at: str | None
    error: str | None


class KeyInfo(BaseModel):
    """Key information model."""

    key_id: str
    algorithm: str
    key_type: KeyType
    created_at: str
    expires_at: str | None
    is_quantum_safe: bool
    fingerprint: str


class KeyGenerationRequest(BaseModel):
    """Request for generating new encryption keys."""

    algorithm: EncryptionAlgorithm = Field(
        default=EncryptionAlgorithm.HYBRID_KYBER_AES,
    )
    key_type: KeyType = Field(default=KeyType.HYBRID)
    label: str | None = Field(default=None, description="Human-readable key label")
    expires_days: int | None = Field(
        default=365,
        ge=1,
        le=3650,
        description="Key expiration in days",
    )


# In-memory storage (would be secure vault in production)
_encryption_jobs: dict[str, EncryptionResult] = {}
_keys: dict[str, KeyInfo] = {}


@router.post("/jobs", response_model=EncryptionResult, status_code=status.HTTP_202_ACCEPTED)
async def start_encryption(
    request: Request,
    encryption_request: EncryptionRequest,
    background_tasks: BackgroundTasks,
) -> EncryptionResult:
    """
    Start a new encryption/decryption job.
    
    For maximum security, use hybrid-kyber-aes which combines classical
    AES-256-GCM with post-quantum Kyber-1024 for key encapsulation.
    """
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    if not swarm or not swarm.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent swarm not ready",
        )
    
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    result = EncryptionResult(
        job_id=job_id,
        status=JobStatus.PENDING,
        operation=encryption_request.operation,
        source_path=encryption_request.source_path,
        destination_path=encryption_request.destination_path,
        algorithm=encryption_request.algorithm.value,
        key_id=encryption_request.key_id,
        file_size=None,
        time_elapsed_ms=None,
        created_at=now.isoformat(),
        completed_at=None,
        error=None,
    )
    
    _encryption_jobs[job_id] = result
    
    background_tasks.add_task(
        process_encryption_job,
        job_id,
        encryption_request,
        swarm,
    )
    
    return result


async def process_encryption_job(
    job_id: str,
    request: EncryptionRequest,
    swarm: AgentSwarm,
) -> None:
    """Background task to process encryption job."""
    import time
    
    job = _encryption_jobs.get(job_id)
    if not job:
        return
    
    start_time = time.monotonic()
    
    try:
        job.status = JobStatus.PROCESSING
        
        # Submit to agent swarm
        agent_result = await swarm.submit_encryption_task(
            source_path=request.source_path,
            operation=request.operation.value,
            algorithm=request.algorithm.value,
            key_id=request.key_id,
            compress_first=request.compress_first,
        )
        
        job.status = JobStatus.COMPLETED
        job.destination_path = agent_result.get("destination_path")
        job.key_id = agent_result.get("key_id")
        job.file_size = agent_result.get("file_size", 0)
        job.time_elapsed_ms = int((time.monotonic() - start_time) * 1000)
        job.completed_at = datetime.now(timezone.utc).isoformat()
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.now(timezone.utc).isoformat()


@router.get("/jobs", response_model=list[EncryptionResult])
async def list_encryption_jobs(
    status_filter: JobStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[EncryptionResult]:
    """List encryption jobs with optional filtering."""
    jobs = list(_encryption_jobs.values())
    
    if status_filter:
        jobs = [j for j in jobs if j.status == status_filter]
    
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    
    return jobs[offset : offset + limit]


@router.get("/jobs/{job_id}", response_model=EncryptionResult)
async def get_encryption_job(job_id: str) -> EncryptionResult:
    """Get details of a specific encryption job."""
    job = _encryption_jobs.get(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    return job


@router.post("/keys", response_model=KeyInfo, status_code=status.HTTP_201_CREATED)
async def generate_key(
    request: Request,
    key_request: KeyGenerationRequest,
) -> KeyInfo:
    """
    Generate a new encryption key.
    
    For quantum-resistant security, use Kyber-1024 or hybrid-kyber-aes.
    The key is stored in the secure vault and only the key_id is returned.
    """
    swarm: AgentSwarm | None = getattr(request.app.state, "swarm", None)
    
    if not swarm or not swarm.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent swarm not ready",
        )
    
    key_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Generate key via crypto agent
    key_result = await swarm.generate_encryption_key(
        algorithm=key_request.algorithm.value,
        key_type=key_request.key_type.value,
    )
    
    from datetime import timedelta
    
    expires_at = None
    if key_request.expires_days:
        expires_at = (now + timedelta(days=key_request.expires_days)).isoformat()
    
    is_quantum_safe = key_request.algorithm in (
        EncryptionAlgorithm.KYBER_1024,
        EncryptionAlgorithm.HYBRID_KYBER_AES,
    )
    
    key_info = KeyInfo(
        key_id=key_id,
        algorithm=key_request.algorithm.value,
        key_type=key_request.key_type,
        created_at=now.isoformat(),
        expires_at=expires_at,
        is_quantum_safe=is_quantum_safe,
        fingerprint=key_result.get("fingerprint", "unknown"),
    )
    
    _keys[key_id] = key_info
    
    return key_info


@router.get("/keys", response_model=list[KeyInfo])
async def list_keys(
    algorithm_filter: EncryptionAlgorithm | None = None,
    quantum_safe_only: bool = False,
) -> list[KeyInfo]:
    """List all encryption keys."""
    keys = list(_keys.values())
    
    if algorithm_filter:
        keys = [k for k in keys if k.algorithm == algorithm_filter.value]
    
    if quantum_safe_only:
        keys = [k for k in keys if k.is_quantum_safe]
    
    return keys


@router.get("/keys/{key_id}", response_model=KeyInfo)
async def get_key(key_id: str) -> KeyInfo:
    """Get key information (not the key material itself)."""
    key = _keys.get(key_id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key {key_id} not found",
        )
    
    return key


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(key_id: str) -> None:
    """
    Revoke and securely delete an encryption key.
    
    WARNING: Data encrypted with this key will become unrecoverable.
    """
    if key_id not in _keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key {key_id} not found",
        )
    
    del _keys[key_id]


@router.get("/algorithms")
async def list_algorithms() -> dict:
    """List available encryption algorithms with their properties."""
    return {
        "algorithms": [
            {
                "id": "aes-256-gcm",
                "name": "AES-256-GCM",
                "type": "symmetric",
                "quantum_safe": False,
                "performance": "fast",
                "recommended_for": "general use, high performance needs",
            },
            {
                "id": "chacha20-poly1305",
                "name": "ChaCha20-Poly1305",
                "type": "symmetric",
                "quantum_safe": False,
                "performance": "fast",
                "recommended_for": "mobile devices, software implementations",
            },
            {
                "id": "kyber-1024",
                "name": "Kyber-1024",
                "type": "kem",
                "quantum_safe": True,
                "performance": "medium",
                "recommended_for": "post-quantum key exchange",
            },
            {
                "id": "hybrid-kyber-aes",
                "name": "Hybrid Kyber-AES",
                "type": "hybrid",
                "quantum_safe": True,
                "performance": "medium",
                "recommended_for": "maximum security, long-term data protection",
            },
        ],
        "default": "hybrid-kyber-aes",
        "recommended": "hybrid-kyber-aes",
    }
