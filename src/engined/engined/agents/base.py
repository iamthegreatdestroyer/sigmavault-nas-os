"""
Base classes for Elite Agent Collective.

This module provides the foundational infrastructure for the 40-agent swarm,
including state management, capability descriptors, and task execution framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    
    STUB = "stub"           # Not initialized
    IDLE = "idle"           # Ready for tasks
    BUSY = "busy"           # Executing task
    ERROR = "error"         # Failed state
    SHUTDOWN = "shutdown"   # Gracefully stopped


class TaskPriority(Enum):
    """Task priority levels."""
    
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


@dataclass
class AgentCapability:
    """
    Agent capability descriptor.
    
    Defines what an agent can do, its tier classification,
    and domain expertise.
    """
    
    name: str
    tier: int  # 1=Foundational, 2=Specialist, 3=Innovator, 4=Meta
    domains: List[str]
    skills: List[str]
    description: str
    max_concurrent_tasks: int = 1


@dataclass
class AgentTask:
    """
    Task submitted to an agent.
    
    Contains all information needed for task execution including
    payload, priority, and timeout constraints.
    """
    
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    timeout: int = 300  # seconds
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """
    Result of task execution.
    
    Contains output, metrics, and any errors encountered.
    """
    
    task_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all Elite Agent Collective members.
    
    Provides common infrastructure for:
    - State management
    - Task execution lifecycle
    - Metrics tracking
    - Error handling
    
    Each specialized agent (APEX, CIPHER, etc.) inherits from this class
    and implements the execute_task method.
    """

    def __init__(self, agent_id: str, capability: AgentCapability):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique agent identifier (e.g., "APEX-01")
            capability: Agent capability descriptor
        """
        self.agent_id = agent_id
        self.capability = capability
        self.state = AgentState.STUB
        self.current_task: Optional[AgentTask] = None
        
        # Metrics
        self.task_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        
        # State management
        self._state_lock = asyncio.Lock()
        self._task_queue: asyncio.Queue[AgentTask] = asyncio.Queue()
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> bool:
        """
        Initialize agent - transition from STUB to IDLE.
        
        Override this method to add custom initialization logic.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            async with self._state_lock:
                if self.state != AgentState.STUB:
                    logger.warning(f"{self.agent_id}: Already initialized (state={self.state})")
                    return False
                
                # Perform initialization
                await self._custom_initialize()
                
                # Transition to IDLE
                self.state = AgentState.IDLE
                logger.info(f"{self.agent_id}: Initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"{self.agent_id}: Initialization failed - {e}")
            self.state = AgentState.ERROR
            return False

    async def _custom_initialize(self):
        """
        Custom initialization logic.
        
        Override this in derived classes for agent-specific initialization.
        """
        pass

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> TaskResult:
        """
        Execute assigned task.
        
        This method MUST be implemented by each specialized agent.
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult with output and execution metrics
            
        Raises:
            NotImplementedError: If not overridden in derived class
        """
        raise NotImplementedError(f"{self.agent_id}: execute_task must be implemented")

    async def submit_task(self, task: AgentTask) -> bool:
        """
        Submit task to agent's queue.
        
        Args:
            task: Task to submit
            
        Returns:
            True if task queued successfully
        """
        if self.state not in (AgentState.IDLE, AgentState.BUSY):
            logger.warning(f"{self.agent_id}: Cannot accept task in state {self.state}")
            return False
        
        await self._task_queue.put(task)
        logger.debug(f"{self.agent_id}: Task {task.task_id} queued")
        return True

    async def _execute_with_lifecycle(self, task: AgentTask) -> TaskResult:
        """
        Execute task with full lifecycle management.
        
        Handles state transitions, timing, error handling, and metrics.
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Transition to BUSY
            async with self._state_lock:
                self.state = AgentState.BUSY
                self.current_task = task
                self.task_count += 1
            
            logger.info(f"{self.agent_id}: Executing task {task.task_id}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute_task(task),
                timeout=task.timeout
            )
            
            # Update metrics
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.execution_time = execution_time
            self.total_execution_time += execution_time
            
            if result.success:
                self.success_count += 1
                logger.info(f"{self.agent_id}: Task {task.task_id} completed successfully")
            else:
                self.error_count += 1
                logger.warning(f"{self.agent_id}: Task {task.task_id} failed - {result.error}")
            
            return result
            
        except asyncio.TimeoutError:
            self.error_count += 1
            logger.error(f"{self.agent_id}: Task {task.task_id} timed out after {task.timeout}s")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                error=f"Task timed out after {task.timeout} seconds"
            )
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"{self.agent_id}: Task {task.task_id} failed with exception - {e}", exc_info=True)
            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                error=str(e)
            )
            
        finally:
            # Transition back to IDLE
            async with self._state_lock:
                self.state = AgentState.IDLE
                self.current_task = None

    async def run(self):
        """
        Main agent loop - processes tasks from queue.
        
        This is typically run as a background task via asyncio.create_task().
        """
        logger.info(f"{self.agent_id}: Agent loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for task with timeout to check shutdown periodically
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                
                # Execute task
                result = await self._execute_with_lifecycle(task)
                
                # Mark task done
                self._task_queue.task_done()
                
            except asyncio.TimeoutError:
                # No task available, continue loop
                continue
            except Exception as e:
                logger.error(f"{self.agent_id}: Error in agent loop - {e}", exc_info=True)
                await asyncio.sleep(1.0)
        
        logger.info(f"{self.agent_id}: Agent loop stopped")

    async def shutdown(self):
        """
        Graceful shutdown.
        
        Waits for current task to complete, then stops the agent loop.
        """
        logger.info(f"{self.agent_id}: Shutdown initiated")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for current task to complete
        if self.current_task:
            logger.info(f"{self.agent_id}: Waiting for current task to complete")
            while self.state == AgentState.BUSY:
                await asyncio.sleep(0.1)
        
        # Wait for queue to empty
        await self._task_queue.join()
        
        # Transition to SHUTDOWN
        async with self._state_lock:
            self.state = AgentState.SHUTDOWN
        
        logger.info(f"{self.agent_id}: Shutdown complete")

    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status.
        
        Returns:
            Dictionary with agent state, metrics, and current task info
        """
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "tier": self.capability.tier,
            "domains": self.capability.domains,
            "skills": self.capability.skills,
            "current_task": self.current_task.task_id if self.current_task else None,
            "queue_size": self._task_queue.qsize(),
            "metrics": {
                "task_count": self.task_count,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "success_rate": (
                    self.success_count / self.task_count if self.task_count > 0 else 0.0
                ),
                "avg_execution_time": (
                    self.total_execution_time / self.task_count if self.task_count > 0 else 0.0
                ),
            }
        }

    def __repr__(self) -> str:
        """String representation of agent."""
        return f"{self.__class__.__name__}(id={self.agent_id}, state={self.state.value})"
