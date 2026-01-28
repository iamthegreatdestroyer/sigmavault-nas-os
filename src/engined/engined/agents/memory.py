"""
MNEMONIC Memory System for Elite Agent Collective.

Implements episodic, semantic, and procedural memory stores that allow agents
to learn from past experiences, build knowledge graphs, and optimize procedures.

Memory Types:
- Episodic: Specific event memories (task completions, errors, interactions)
- Semantic: Factual knowledge and relationships (patterns, correlations)
- Procedural: Learned procedures and optimizations (how to do things better)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from weakref import WeakValueDictionary

import logging

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memories in the MNEMONIC system."""
    EPISODIC = "episodic"      # Event memories: what happened
    SEMANTIC = "semantic"       # Knowledge memories: what is true
    PROCEDURAL = "procedural"   # Skill memories: how to do things


class MemoryPriority(int, Enum):
    """Priority levels for memory retention."""
    CRITICAL = 100   # Never forget (errors, security events)
    HIGH = 75        # Rarely forget (important patterns)
    NORMAL = 50      # Standard retention
    LOW = 25         # Quick to forget (routine events)
    EPHEMERAL = 10   # Very short-term


@dataclass
class MemoryEntry:
    """A single memory entry in the MNEMONIC system."""
    id: str
    type: MemoryType
    content: Dict[str, Any]
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    priority: MemoryPriority = MemoryPriority.NORMAL
    tags: Set[str] = field(default_factory=set)
    associations: Set[str] = field(default_factory=set)  # IDs of related memories
    embedding: Optional[List[float]] = None  # For semantic search
    decay_rate: float = 0.1  # How fast memory fades (0-1)
    strength: float = 1.0    # Current memory strength (0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "priority": self.priority.value,
            "tags": list(self.tags),
            "associations": list(self.associations),
            "decay_rate": self.decay_rate,
            "strength": self.strength,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryEntry:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            access_count=data.get("access_count", 0),
            priority=MemoryPriority(data.get("priority", MemoryPriority.NORMAL.value)),
            tags=set(data.get("tags", [])),
            associations=set(data.get("associations", [])),
            decay_rate=data.get("decay_rate", 0.1),
            strength=data.get("strength", 1.0),
        )
    
    def access(self) -> None:
        """Record an access to this memory, strengthening it."""
        self.accessed_at = datetime.now()
        self.access_count += 1
        # Strengthen memory on access (spaced repetition effect)
        self.strength = min(1.0, self.strength + 0.1)
    
    def decay(self, elapsed_hours: float) -> None:
        """Apply time-based decay to memory strength."""
        if self.priority == MemoryPriority.CRITICAL:
            return  # Critical memories never decay
        decay_factor = self.decay_rate * (elapsed_hours / 24.0)
        self.strength = max(0.0, self.strength - decay_factor)


@dataclass
class MemoryIndex:
    """Index for fast memory lookup."""
    by_tag: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    by_type: Dict[MemoryType, Set[str]] = field(default_factory=lambda: defaultdict(set))
    by_agent: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    temporal: List[Tuple[datetime, str]] = field(default_factory=list)  # (timestamp, id)
    
    def add(self, entry: MemoryEntry, agent_id: Optional[str] = None) -> None:
        """Add entry to indices."""
        self.by_type[entry.type].add(entry.id)
        for tag in entry.tags:
            self.by_tag[tag].add(entry.id)
        if agent_id:
            self.by_agent[agent_id].add(entry.id)
        self.temporal.append((entry.created_at, entry.id))
    
    def remove(self, entry: MemoryEntry, agent_id: Optional[str] = None) -> None:
        """Remove entry from indices."""
        self.by_type[entry.type].discard(entry.id)
        for tag in entry.tags:
            self.by_tag[tag].discard(entry.id)
        if agent_id:
            self.by_agent[agent_id].discard(entry.id)
        self.temporal = [(t, i) for t, i in self.temporal if i != entry.id]


class MemoryStore:
    """
    Core memory storage with indexing, decay, and consolidation.
    
    Features:
    - Time-based decay (forgetting curve)
    - Access-based strengthening (spaced repetition)
    - Associative linking between memories
    - Tag-based and temporal indexing
    - Automatic consolidation (short-term to long-term)
    """
    
    def __init__(
        self,
        max_entries: int = 10000,
        consolidation_interval: float = 300.0,  # 5 minutes
        decay_interval: float = 3600.0,  # 1 hour
        strength_threshold: float = 0.2,  # Below this, memory is forgotten
    ) -> None:
        self._memories: Dict[str, MemoryEntry] = {}
        self._index = MemoryIndex()
        self._max_entries = max_entries
        self._consolidation_interval = consolidation_interval
        self._decay_interval = decay_interval
        self._strength_threshold = strength_threshold
        self._lock = asyncio.Lock()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Metrics
        self._total_stored = 0
        self._total_forgotten = 0
        self._total_retrieved = 0
        self._consolidation_runs = 0
    
    async def start(self) -> None:
        """Start background maintenance tasks."""
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._decay_loop()),
            asyncio.create_task(self._consolidation_loop()),
        ]
        logger.info("MemoryStore started with background maintenance")
    
    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks = []
        logger.info("MemoryStore stopped")
    
    async def store(
        self,
        memory_type: MemoryType,
        content: Dict[str, Any],
        tags: Optional[Set[str]] = None,
        priority: MemoryPriority = MemoryPriority.NORMAL,
        agent_id: Optional[str] = None,
        associations: Optional[Set[str]] = None,
    ) -> str:
        """
        Store a new memory entry.
        
        Returns the memory ID.
        """
        # Generate content-based ID for deduplication
        content_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()[:16]
        memory_id = f"{memory_type.value[:3]}_{content_hash}_{int(time.time() * 1000) % 100000}"
        
        now = datetime.now()
        entry = MemoryEntry(
            id=memory_id,
            type=memory_type,
            content=content,
            created_at=now,
            accessed_at=now,
            priority=priority,
            tags=tags or set(),
            associations=associations or set(),
        )
        
        async with self._lock:
            # Check capacity
            if len(self._memories) >= self._max_entries:
                await self._evict_weakest()
            
            self._memories[memory_id] = entry
            self._index.add(entry, agent_id)
            self._total_stored += 1
        
        logger.debug(f"Stored {memory_type.value} memory: {memory_id}")
        return memory_id
    
    async def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID, strengthening it on access."""
        async with self._lock:
            entry = self._memories.get(memory_id)
            if entry:
                entry.access()
                self._total_retrieved += 1
            return entry
    
    async def search(
        self,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[Set[str]] = None,
        agent_id: Optional[str] = None,
        min_strength: float = 0.0,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[MemoryEntry]:
        """
        Search memories by various criteria.
        
        Returns memories sorted by strength (strongest first).
        """
        async with self._lock:
            # Start with all memories or filter by type
            if memory_type:
                candidate_ids = self._index.by_type.get(memory_type, set())
            else:
                candidate_ids = set(self._memories.keys())
            
            # Filter by tags (intersection)
            if tags:
                for tag in tags:
                    tag_ids = self._index.by_tag.get(tag, set())
                    candidate_ids = candidate_ids.intersection(tag_ids)
            
            # Filter by agent
            if agent_id:
                agent_ids = self._index.by_agent.get(agent_id, set())
                candidate_ids = candidate_ids.intersection(agent_ids)
            
            # Get entries and filter by strength/time
            results = []
            for mid in candidate_ids:
                entry = self._memories.get(mid)
                if not entry:
                    continue
                if entry.strength < min_strength:
                    continue
                if since and entry.created_at < since:
                    continue
                entry.access()  # Strengthen on search hit
                results.append(entry)
            
            # Sort by strength (descending)
            results.sort(key=lambda e: e.strength, reverse=True)
            self._total_retrieved += len(results[:limit])
            return results[:limit]
    
    async def associate(self, memory_id1: str, memory_id2: str) -> bool:
        """Create bidirectional association between memories."""
        async with self._lock:
            m1 = self._memories.get(memory_id1)
            m2 = self._memories.get(memory_id2)
            if m1 and m2:
                m1.associations.add(memory_id2)
                m2.associations.add(memory_id1)
                return True
            return False
    
    async def get_associated(self, memory_id: str, depth: int = 1) -> List[MemoryEntry]:
        """Get memories associated with a given memory (up to depth levels)."""
        async with self._lock:
            entry = self._memories.get(memory_id)
            if not entry:
                return []
            
            visited: Set[str] = {memory_id}
            current_level = entry.associations.copy()
            results: List[MemoryEntry] = []
            
            for _ in range(depth):
                next_level: Set[str] = set()
                for mid in current_level:
                    if mid in visited:
                        continue
                    visited.add(mid)
                    mem = self._memories.get(mid)
                    if mem:
                        mem.access()
                        results.append(mem)
                        next_level.update(mem.associations)
                current_level = next_level
            
            return results
    
    async def forget(self, memory_id: str) -> bool:
        """Explicitly forget a memory."""
        async with self._lock:
            entry = self._memories.pop(memory_id, None)
            if entry:
                self._index.remove(entry)
                self._total_forgotten += 1
                logger.debug(f"Forgot memory: {memory_id}")
                return True
            return False
    
    async def _evict_weakest(self) -> None:
        """Evict weakest memories when at capacity."""
        # Find memories below threshold or lowest strength non-critical
        weak_memories = [
            (mid, m) for mid, m in self._memories.items()
            if m.priority != MemoryPriority.CRITICAL and m.strength < self._strength_threshold
        ]
        
        if not weak_memories:
            # No weak memories, evict lowest strength non-critical
            candidates = [
                (mid, m) for mid, m in self._memories.items()
                if m.priority != MemoryPriority.CRITICAL
            ]
            if candidates:
                candidates.sort(key=lambda x: x[1].strength)
                weak_memories = candidates[:max(1, len(candidates) // 10)]
        
        for mid, entry in weak_memories:
            del self._memories[mid]
            self._index.remove(entry)
            self._total_forgotten += 1
    
    async def _decay_loop(self) -> None:
        """Background loop to apply decay to all memories."""
        last_decay = datetime.now()
        while self._running:
            await asyncio.sleep(self._decay_interval)
            now = datetime.now()
            elapsed = (now - last_decay).total_seconds() / 3600.0
            last_decay = now
            
            async with self._lock:
                to_forget = []
                for mid, entry in self._memories.items():
                    entry.decay(elapsed)
                    if entry.strength < self._strength_threshold:
                        if entry.priority != MemoryPriority.CRITICAL:
                            to_forget.append(mid)
                
                for mid in to_forget:
                    entry = self._memories.pop(mid, None)
                    if entry:
                        self._index.remove(entry)
                        self._total_forgotten += 1
            
            if to_forget:
                logger.debug(f"Decay cycle forgot {len(to_forget)} weak memories")
    
    async def _consolidation_loop(self) -> None:
        """Background loop to consolidate related memories."""
        while self._running:
            await asyncio.sleep(self._consolidation_interval)
            self._consolidation_runs += 1
            
            async with self._lock:
                # Find patterns: memories with same tags that aren't associated
                tag_groups: Dict[frozenset, List[str]] = defaultdict(list)
                for mid, entry in self._memories.items():
                    if entry.tags:
                        key = frozenset(entry.tags)
                        tag_groups[key].append(mid)
                
                # Auto-associate memories with identical tags
                associations_made = 0
                for tag_set, memory_ids in tag_groups.items():
                    if len(memory_ids) > 1 and len(tag_set) >= 2:
                        for i, mid1 in enumerate(memory_ids):
                            for mid2 in memory_ids[i+1:]:
                                m1 = self._memories.get(mid1)
                                m2 = self._memories.get(mid2)
                                if m1 and m2 and mid2 not in m1.associations:
                                    m1.associations.add(mid2)
                                    m2.associations.add(mid1)
                                    associations_made += 1
                
                if associations_made:
                    logger.debug(f"Consolidation created {associations_made} associations")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get memory store metrics."""
        return {
            "total_memories": len(self._memories),
            "total_stored": self._total_stored,
            "total_forgotten": self._total_forgotten,
            "total_retrieved": self._total_retrieved,
            "consolidation_runs": self._consolidation_runs,
            "max_entries": self._max_entries,
            "by_type": {
                t.value: len(ids) for t, ids in self._index.by_type.items()
            },
        }


class AgentMemory:
    """
    Agent-specific memory interface to the shared MemoryStore.
    
    Provides agent-scoped operations and learning from experiences.
    """
    
    def __init__(self, agent_id: str, store: MemoryStore) -> None:
        self.agent_id = agent_id
        self._store = store
    
    async def remember_task(
        self,
        task_id: str,
        task_type: str,
        result: str,
        duration_ms: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store episodic memory of a task execution."""
        priority = MemoryPriority.HIGH if not success else MemoryPriority.NORMAL
        content = {
            "task_id": task_id,
            "task_type": task_type,
            "result": result,
            "duration_ms": duration_ms,
            "success": success,
            "metadata": metadata or {},
        }
        tags = {"task", task_type}
        if not success:
            tags.add("failure")
        
        return await self._store.store(
            memory_type=MemoryType.EPISODIC,
            content=content,
            tags=tags,
            priority=priority,
            agent_id=self.agent_id,
        )
    
    async def remember_pattern(
        self,
        pattern_name: str,
        pattern_data: Dict[str, Any],
        confidence: float = 0.5,
    ) -> str:
        """Store semantic memory of a discovered pattern."""
        priority = MemoryPriority.HIGH if confidence > 0.8 else MemoryPriority.NORMAL
        content = {
            "pattern_name": pattern_name,
            "pattern_data": pattern_data,
            "confidence": confidence,
        }
        return await self._store.store(
            memory_type=MemoryType.SEMANTIC,
            content=content,
            tags={"pattern", pattern_name},
            priority=priority,
            agent_id=self.agent_id,
        )
    
    async def remember_procedure(
        self,
        procedure_name: str,
        steps: List[str],
        success_rate: float,
        avg_duration_ms: float,
    ) -> str:
        """Store procedural memory of how to do something."""
        priority = MemoryPriority.HIGH if success_rate > 0.9 else MemoryPriority.NORMAL
        content = {
            "procedure_name": procedure_name,
            "steps": steps,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration_ms,
        }
        return await self._store.store(
            memory_type=MemoryType.PROCEDURAL,
            content=content,
            tags={"procedure", procedure_name},
            priority=priority,
            agent_id=self.agent_id,
        )
    
    async def recall_similar_tasks(
        self,
        task_type: str,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Recall past task executions of similar type."""
        return await self._store.search(
            memory_type=MemoryType.EPISODIC,
            tags={"task", task_type},
            agent_id=self.agent_id,
            limit=limit,
        )
    
    async def recall_failures(self, limit: int = 10) -> List[MemoryEntry]:
        """Recall past failures to avoid repeating them."""
        return await self._store.search(
            memory_type=MemoryType.EPISODIC,
            tags={"failure"},
            agent_id=self.agent_id,
            min_strength=0.5,  # Only strong failure memories
            limit=limit,
        )
    
    async def recall_procedure(self, procedure_name: str) -> Optional[MemoryEntry]:
        """Recall a learned procedure."""
        results = await self._store.search(
            memory_type=MemoryType.PROCEDURAL,
            tags={"procedure", procedure_name},
            agent_id=self.agent_id,
            limit=1,
        )
        return results[0] if results else None
    
    async def get_agent_metrics(self) -> Dict[str, Any]:
        """Get memory metrics for this agent."""
        async with self._store._lock:
            agent_memories = self._store._index.by_agent.get(self.agent_id, set())
            by_type: Dict[str, int] = defaultdict(int)
            total_strength = 0.0
            for mid in agent_memories:
                mem = self._store._memories.get(mid)
                if mem:
                    by_type[mem.type.value] += 1
                    total_strength += mem.strength
            
            return {
                "agent_id": self.agent_id,
                "total_memories": len(agent_memories),
                "by_type": dict(by_type),
                "avg_strength": total_strength / len(agent_memories) if agent_memories else 0.0,
            }


# Global memory store instance
_memory_store: Optional[MemoryStore] = None
_agent_memories: Dict[str, AgentMemory] = {}


async def init_memory_system(
    max_entries: int = 10000,
    consolidation_interval: float = 300.0,
    decay_interval: float = 3600.0,
) -> MemoryStore:
    """Initialize the global memory system."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(
            max_entries=max_entries,
            consolidation_interval=consolidation_interval,
            decay_interval=decay_interval,
        )
        await _memory_store.start()
        logger.info("MNEMONIC memory system initialized")
    return _memory_store


async def shutdown_memory_system() -> None:
    """Shutdown the global memory system."""
    global _memory_store, _agent_memories
    if _memory_store:
        await _memory_store.stop()
        _memory_store = None
        _agent_memories.clear()
        logger.info("MNEMONIC memory system shutdown")


def get_memory_store() -> Optional[MemoryStore]:
    """Get the global memory store."""
    return _memory_store


def get_agent_memory(agent_id: str) -> Optional[AgentMemory]:
    """Get or create an AgentMemory instance for an agent."""
    global _agent_memories
    if _memory_store is None:
        return None
    
    if agent_id not in _agent_memories:
        _agent_memories[agent_id] = AgentMemory(agent_id, _memory_store)
    
    return _agent_memories[agent_id]
