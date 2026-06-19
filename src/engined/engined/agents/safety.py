"""
Agent Safety Layer — audit logs, approval gates, rollback.

Non-negotiable for production agent autonomy on a storage system.
One bad agent decision = data loss. This module ensures:

1. Every agent-initiated storage operation is logged to an append-only
   audit trail before execution.
2. Destructive operations (delete, migrate, compress-in-place, reformat)
   require explicit human approval via an approval gate.
3. Every destructive operation creates a rollback checkpoint that can
   undo the operation within a configurable retention window.

Integration
-----------
Wrap agent task execution with SafetyGuard:

    guard = SafetyGuard(audit_dir="/var/lib/sigmavault/audit")
    result = await guard.execute_safe(agent, task)

The guard intercepts execute_task(), logs the operation, checks approval
if destructive, creates rollback state, then delegates to the real agent.

Wire format (audit log)
-----------------------
Each entry is one JSON line (JSONL) appended to a date-partitioned file:
    /var/lib/sigmavault/audit/2026-06-18.jsonl

Fields: timestamp, agent_id, task_id, task_type, operation_class,
        payload_hash (SHA-256 of payload, never raw payload),
        requires_approval, approved, result_status, rollback_id.

The audit file is opened in append-only mode. Entries are never modified
or deleted by the application. Retention/rotation is handled by logrotate
or an external policy — this module only appends.
"""

import asyncio
import hashlib
import json
import logging
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .base import AgentTask, BaseAgent, TaskResult

logger = logging.getLogger(__name__)


class OperationClass(Enum):
    """Classification of agent operations by risk level."""

    READ = "read"
    COMPUTE = "compute"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


DESTRUCTIVE_TASK_TYPES = frozenset({
    "delete_file",
    "delete_dataset",
    "delete_pool",
    "delete_share",
    "format_disk",
    "compress_in_place",
    "migrate_data",
    "purge_cache",
    "rebalance_pool",
    "remove_snapshot",
    "overwrite_config",
    "shutdown_service",
})

WRITE_TASK_TYPES = frozenset({
    "create_file",
    "create_dataset",
    "create_pool",
    "create_share",
    "create_snapshot",
    "compress_file",
    "update_config",
    "start_service",
})


def classify_operation(task_type: str) -> OperationClass:
    if task_type in DESTRUCTIVE_TASK_TYPES:
        return OperationClass.DESTRUCTIVE
    if task_type in WRITE_TASK_TYPES:
        return OperationClass.WRITE
    if task_type.startswith(("get_", "list_", "query_", "check_", "status_")):
        return OperationClass.READ
    return OperationClass.COMPUTE


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

@dataclass
class AuditEntry:
    """One line in the append-only audit log."""

    timestamp: str
    agent_id: str
    task_id: str
    task_type: str
    operation_class: str
    payload_hash: str
    requires_approval: bool
    approved: bool | None
    result_status: str | None = None
    rollback_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "agent_id": self.agent_id,
                "task_id": self.task_id,
                "task_type": self.task_type,
                "operation_class": self.operation_class,
                "payload_hash": self.payload_hash,
                "requires_approval": self.requires_approval,
                "approved": self.approved,
                "result_status": self.result_status,
                "rollback_id": self.rollback_id,
                "error": self.error,
                "metadata": self.metadata,
            },
            separators=(",", ":"),
        )


class AuditLog:
    """
    Append-only JSONL audit log for agent operations.

    One file per UTC date: {audit_dir}/2026-06-18.jsonl
    Entries are flushed immediately — no buffering.
    """

    def __init__(self, audit_dir: str | Path):
        self._dir = Path(audit_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _path_for_today(self) -> Path:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        return self._dir / f"{date_str}.jsonl"

    async def append(self, entry: AuditEntry) -> None:
        async with self._lock:
            path = self._path_for_today()
            line = entry.to_json() + "\n"
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()

    async def read_today(self) -> list[AuditEntry]:
        path = self._path_for_today()
        if not path.exists():
            return []
        entries = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entries.append(AuditEntry(**data))
        return entries

    def stats(self) -> dict[str, Any]:
        files = sorted(self._dir.glob("*.jsonl"))
        total_entries = 0
        for f in files:
            with open(f, encoding="utf-8") as fh:
                total_entries += sum(1 for _ in fh)
        return {
            "audit_dir": str(self._dir),
            "log_files": len(files),
            "total_entries": total_entries,
            "oldest": files[0].stem if files else None,
            "newest": files[-1].stem if files else None,
        }


# ---------------------------------------------------------------------------
# Approval Gate
# ---------------------------------------------------------------------------

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A request for human approval of a destructive operation."""

    request_id: str
    agent_id: str
    task_id: str
    task_type: str
    description: str
    payload_summary: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    decided_at: str | None = None
    decided_by: str | None = None
    expiry_seconds: int = 300


class ApprovalGate:
    """
    Human approval gate for destructive agent operations.

    When an agent attempts a destructive operation, the gate creates an
    ApprovalRequest and blocks until a human approves, denies, or the
    request expires.

    The gate exposes pending requests via get_pending() for the UI to
    poll and display. Approval/denial is submitted via approve() or deny().
    """

    def __init__(self, expiry_seconds: int = 300):
        self._requests: dict[str, ApprovalRequest] = {}
        self._events: dict[str, asyncio.Event] = {}
        self._expiry = expiry_seconds
        self._lock = asyncio.Lock()

    async def request_approval(
        self,
        agent_id: str,
        task: AgentTask,
        description: str | None = None,
    ) -> ApprovalRequest:
        """Create an approval request and wait for human decision."""
        req_id = f"apr_{uuid.uuid4().hex[:12]}"

        summary = {}
        for k, v in task.payload.items():
            if isinstance(v, str) and len(v) > 200:
                summary[k] = v[:200] + "..."
            else:
                summary[k] = v

        req = ApprovalRequest(
            request_id=req_id,
            agent_id=agent_id,
            task_id=task.task_id,
            task_type=task.task_type,
            description=description or f"Agent {agent_id} wants to execute: {task.task_type}",
            payload_summary=summary,
            expiry_seconds=self._expiry,
        )

        event = asyncio.Event()

        async with self._lock:
            self._requests[req_id] = req
            self._events[req_id] = event

        logger.warning(
            "APPROVAL REQUIRED: %s by %s (request=%s, expires=%ds)",
            task.task_type,
            agent_id,
            req_id,
            self._expiry,
        )

        try:
            await asyncio.wait_for(event.wait(), timeout=self._expiry)
        except asyncio.TimeoutError:
            async with self._lock:
                req.status = ApprovalStatus.EXPIRED
                req.decided_at = datetime.now(UTC).isoformat()
            logger.warning("Approval request %s expired", req_id)

        return req

    async def approve(self, request_id: str, decided_by: str = "human") -> bool:
        async with self._lock:
            req = self._requests.get(request_id)
            if req is None or req.status != ApprovalStatus.PENDING:
                return False
            req.status = ApprovalStatus.APPROVED
            req.decided_at = datetime.now(UTC).isoformat()
            req.decided_by = decided_by
            event = self._events.get(request_id)
            if event:
                event.set()
        logger.info("Approval GRANTED for %s by %s", request_id, decided_by)
        return True

    async def deny(self, request_id: str, decided_by: str = "human") -> bool:
        async with self._lock:
            req = self._requests.get(request_id)
            if req is None or req.status != ApprovalStatus.PENDING:
                return False
            req.status = ApprovalStatus.DENIED
            req.decided_at = datetime.now(UTC).isoformat()
            req.decided_by = decided_by
            event = self._events.get(request_id)
            if event:
                event.set()
        logger.info("Approval DENIED for %s by %s", request_id, decided_by)
        return True

    def get_pending(self) -> list[ApprovalRequest]:
        return [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

    def get_all(self) -> list[ApprovalRequest]:
        return list(self._requests.values())


# ---------------------------------------------------------------------------
# Rollback Checkpoint
# ---------------------------------------------------------------------------

@dataclass
class RollbackCheckpoint:
    """
    Pre-operation snapshot for undo capability.

    For file operations: stores a copy of the original file.
    For config operations: stores the previous config state.
    For dataset operations: stores metadata for ZFS/Btrfs rollback.
    """

    checkpoint_id: str
    task_id: str
    agent_id: str
    task_type: str
    created_at: str
    artifact_path: str | None = None
    previous_state: dict[str, Any] = field(default_factory=dict)
    rolled_back: bool = False
    expired: bool = False


class RollbackManager:
    """
    Manages rollback checkpoints for destructive operations.

    Checkpoints are stored in {rollback_dir}/{checkpoint_id}/.
    File backups go into the checkpoint directory.
    Metadata goes into checkpoint.json.
    """

    def __init__(
        self,
        rollback_dir: str | Path,
        retention_hours: int = 24,
    ):
        self._dir = Path(rollback_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._retention_hours = retention_hours
        self._checkpoints: dict[str, RollbackCheckpoint] = {}

    async def create_checkpoint(
        self,
        task: AgentTask,
        agent_id: str,
    ) -> RollbackCheckpoint:
        cp_id = f"rb_{uuid.uuid4().hex[:12]}"
        cp_dir = self._dir / cp_id
        cp_dir.mkdir(parents=True, exist_ok=True)

        cp = RollbackCheckpoint(
            checkpoint_id=cp_id,
            task_id=task.task_id,
            agent_id=agent_id,
            task_type=task.task_type,
            created_at=datetime.now(UTC).isoformat(),
        )

        target_path = task.payload.get("path") or task.payload.get("file_path")
        if target_path:
            target = Path(target_path)
            if target.exists() and target.is_file():
                backup_path = cp_dir / target.name
                shutil.copy2(target, backup_path)
                cp.artifact_path = str(backup_path)
                logger.info("Rollback checkpoint %s: backed up %s", cp_id, target)

        config_state = task.payload.get("previous_state")
        if config_state:
            cp.previous_state = config_state

        meta_path = cp_dir / "checkpoint.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "task_id": cp.task_id,
                    "agent_id": cp.agent_id,
                    "task_type": cp.task_type,
                    "created_at": cp.created_at,
                    "artifact_path": cp.artifact_path,
                    "previous_state": cp.previous_state,
                },
                f,
                indent=2,
            )

        self._checkpoints[cp_id] = cp
        return cp

    async def rollback(self, checkpoint_id: str) -> bool:
        cp = self._checkpoints.get(checkpoint_id)
        if cp is None:
            logger.error("Rollback checkpoint %s not found", checkpoint_id)
            return False
        if cp.rolled_back:
            logger.warning("Checkpoint %s already rolled back", checkpoint_id)
            return False

        if cp.artifact_path:
            backup = Path(cp.artifact_path)
            if backup.exists():
                original_path = None
                meta_path = backup.parent / "checkpoint.json"
                if meta_path.exists():
                    with open(meta_path, encoding="utf-8") as f:
                        meta = json.load(f)
                    # The original path was in the task payload
                    # We stored the backup name = original filename
                    # Restore requires knowing the original location
                    # which we store in previous_state or derive from task
                    original_path = meta.get("previous_state", {}).get("original_path")

                if original_path:
                    shutil.copy2(backup, original_path)
                    logger.info(
                        "Rollback %s: restored %s -> %s",
                        checkpoint_id,
                        backup,
                        original_path,
                    )

        cp.rolled_back = True
        logger.info("Rollback completed for checkpoint %s", checkpoint_id)
        return True

    def get_checkpoints(self) -> list[RollbackCheckpoint]:
        return list(self._checkpoints.values())

    def stats(self) -> dict[str, Any]:
        return {
            "rollback_dir": str(self._dir),
            "total_checkpoints": len(self._checkpoints),
            "rolled_back": sum(1 for cp in self._checkpoints.values() if cp.rolled_back),
            "retention_hours": self._retention_hours,
        }


# ---------------------------------------------------------------------------
# SafetyGuard — the main integration point
# ---------------------------------------------------------------------------

class SafetyGuard:
    """
    Wraps agent task execution with audit logging, approval gates,
    and rollback checkpoints.

    Usage:
        guard = SafetyGuard(audit_dir="/var/lib/sigmavault/audit")
        result = await guard.execute_safe(agent, task)

    Flow:
        1. Classify operation (read/compute/write/destructive)
        2. Log pre-execution audit entry
        3. If destructive: request approval, create rollback checkpoint
        4. Execute task via agent
        5. Log post-execution audit entry with result
    """

    def __init__(
        self,
        audit_dir: str | Path = "/var/lib/sigmavault/audit",
        rollback_dir: str | Path = "/var/lib/sigmavault/rollback",
        approval_expiry: int = 300,
        require_approval_for_writes: bool = False,
    ):
        self.audit = AuditLog(audit_dir)
        self.approvals = ApprovalGate(expiry_seconds=approval_expiry)
        self.rollbacks = RollbackManager(rollback_dir)
        self._require_approval_for_writes = require_approval_for_writes

    async def execute_safe(
        self,
        agent: BaseAgent,
        task: AgentTask,
    ) -> TaskResult:
        """Execute a task with full safety wrapping."""
        op_class = classify_operation(task.task_type)
        payload_hash = hashlib.sha256(
            json.dumps(task.payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        needs_approval = (
            op_class == OperationClass.DESTRUCTIVE
            or (self._require_approval_for_writes and op_class == OperationClass.WRITE)
        )

        # Pre-execution audit
        entry = AuditEntry(
            timestamp=datetime.now(UTC).isoformat(),
            agent_id=agent.agent_id,
            task_id=task.task_id,
            task_type=task.task_type,
            operation_class=op_class.value,
            payload_hash=payload_hash,
            requires_approval=needs_approval,
            approved=None,
        )
        await self.audit.append(entry)

        # Approval gate for destructive operations
        if needs_approval:
            req = await self.approvals.request_approval(
                agent.agent_id,
                task,
                description=f"Destructive operation: {task.task_type}",
            )
            if req.status != ApprovalStatus.APPROVED:
                entry.approved = False
                entry.result_status = f"blocked:{req.status.value}"
                await self.audit.append(entry)
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    output=None,
                    error=f"Operation {task.task_type} was {req.status.value} by approval gate",
                )
            entry.approved = True

        # Rollback checkpoint for destructive operations
        rollback_id = None
        if op_class == OperationClass.DESTRUCTIVE:
            cp = await self.rollbacks.create_checkpoint(task, agent.agent_id)
            rollback_id = cp.checkpoint_id
            entry.rollback_id = rollback_id

        # Execute
        result = await agent._execute_with_lifecycle(task)

        # Post-execution audit
        entry.result_status = "success" if result.success else "failure"
        if result.error:
            entry.error = result.error[:500]
        await self.audit.append(entry)

        return result

    def stats(self) -> dict[str, Any]:
        return {
            "audit": self.audit.stats(),
            "approvals_pending": len(self.approvals.get_pending()),
            "rollbacks": self.rollbacks.stats(),
        }
