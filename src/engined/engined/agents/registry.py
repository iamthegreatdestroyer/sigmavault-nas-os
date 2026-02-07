"""
Agent Registry - Central management for Elite Agent Collective.

Provides registration, discovery, and coordination for all 40 agents.
"""

from typing import Dict, List, Optional
import asyncio
import logging
from .base import BaseAgent, AgentCapability, AgentState, AgentTask, TaskResult

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all agents in the Elite Agent Collective.
    
    Responsibilities:
    - Agent registration and lifecycle management
    - Agent discovery by ID, tier, or capability
    - Batch operations (initialize all, shutdown all)
    - Agent status aggregation
    """

    def __init__(self):
        """Initialize empty registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._capabilities: Dict[str, AgentCapability] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def register_agent(self, agent: BaseAgent) -> bool:
        """
        Register agent in the registry.
        
        Args:
            agent: Agent instance to register
            
        Returns:
            True if registration successful, False if already registered
        """
        async with self._lock:
            if agent.agent_id in self._agents:
                logger.warning(f"Agent {agent.agent_id} already registered")
                return False

            self._agents[agent.agent_id] = agent
            self._capabilities[agent.agent_id] = agent.capability
            logger.info(
                f"Registered agent: {agent.agent_id} "
                f"(Tier {agent.capability.tier}, {len(agent.capability.domains)} domains)"
            )
            return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister agent from registry.
        
        Args:
            agent_id: Agent to unregister
            
        Returns:
            True if unregistered, False if not found
        """
        async with self._lock:
            if agent_id not in self._agents:
                logger.warning(f"Agent {agent_id} not found in registry")
                return False

            # Shutdown agent if still running
            agent = self._agents[agent_id]
            if agent.state not in (AgentState.SHUTDOWN, AgentState.STUB):
                await agent.shutdown()

            del self._agents[agent_id]
            del self._capabilities[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True

    async def initialize_all(self) -> Dict[str, bool]:
        """
        Initialize all registered agents.
        
        Returns:
            Dict mapping agent_id to initialization success status
        """
        if self._initialized:
            logger.warning("Registry already initialized")
            return {aid: True for aid in self._agents.keys()}

        results = {}
        tasks = []
        
        for agent_id, agent in self._agents.items():
            tasks.append(self._initialize_agent(agent_id, agent))
        
        # Initialize all agents concurrently
        initialization_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for agent_id, result in zip(self._agents.keys(), initialization_results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_id} initialization failed: {result}")
                results[agent_id] = False
            else:
                results[agent_id] = result
        
        self._initialized = True
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Initialized {success_count}/{len(results)} agents successfully")
        
        return results

    async def _initialize_agent(self, agent_id: str, agent: BaseAgent) -> bool:
        """Helper method to initialize single agent."""
        try:
            success = await agent.initialize()
            if success:
                logger.info(f"Agent {agent_id} initialized successfully")
            else:
                logger.warning(f"Agent {agent_id} initialization returned False")
            return success
        except Exception as e:
            logger.error(f"Agent {agent_id} initialization failed: {e}", exc_info=True)
            return False

    async def shutdown_all(self):
        """
        Shutdown all agents gracefully.
        
        Waits for all agents to complete current tasks before shutting down.
        """
        logger.info("Shutting down all agents...")
        
        tasks = []
        for agent_id, agent in self._agents.items():
            if agent.state not in (AgentState.SHUTDOWN, AgentState.STUB):
                tasks.append(agent.shutdown())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self._initialized = False
        logger.info("All agents shut down")

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_id)

    def list_agents(
        self,
        tier: Optional[int] = None,
        state: Optional[AgentState] = None,
        domain: Optional[str] = None
    ) -> List[Dict]:
        """
        List agents with optional filters.
        
        Args:
            tier: Filter by tier (1-4)
            state: Filter by agent state
            domain: Filter by domain expertise
            
        Returns:
            List of agent status dictionaries
        """
        agents = []
        
        for agent in self._agents.values():
            # Apply filters
            if tier is not None and agent.capability.tier != tier:
                continue
            if state is not None and agent.state != state:
                continue
            if domain is not None and domain not in agent.capability.domains:
                continue
            
            agents.append(agent.get_status())
        
        return agents

    def get_agents_by_tier(self, tier: int) -> List[BaseAgent]:
        """
        Get all agents in a specific tier.
        
        Args:
            tier: Tier number (1=Foundational, 2=Specialist, 3=Innovator, 4=Meta)
            
        Returns:
            List of agents in that tier
        """
        return [
            agent for agent in self._agents.values()
            if agent.capability.tier == tier
        ]

    def get_agents_by_domain(self, domain: str) -> List[BaseAgent]:
        """
        Get all agents with expertise in a domain.
        
        Args:
            domain: Domain name (e.g., "security", "ml", "database")
            
        Returns:
            List of agents with that domain expertise
        """
        return [
            agent for agent in self._agents.values()
            if domain in agent.capability.domains
        ]

    def find_agents_by_skill(self, skill: str) -> List[BaseAgent]:
        """
        Find agents with a specific skill.
        
        Args:
            skill: Skill name
            
        Returns:
            List of agents with that skill
        """
        return [
            agent for agent in self._agents.values()
            if skill in agent.capability.skills
        ]

    async def dispatch_task(
        self,
        agent_id: str,
        task: AgentTask
    ) -> bool:
        """
        Dispatch task to specific agent.
        
        Args:
            agent_id: Target agent ID
            task: Task to dispatch
            
        Returns:
            True if task submitted successfully
        """
        agent = self.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return False
        
        return await agent.submit_task(task)

    def get_registry_status(self) -> Dict:
        """
        Get overall registry status.
        
        Returns:
            Dictionary with registry metrics and statistics
        """
        total_agents = len(self._agents)
        
        # Count by state
        state_counts = {}
        for agent in self._agents.values():
            state = agent.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Count by tier
        tier_counts = {}
        for agent in self._agents.values():
            tier = agent.capability.tier
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Aggregate metrics
        total_tasks = sum(agent.task_count for agent in self._agents.values())
        total_success = sum(agent.success_count for agent in self._agents.values())
        total_errors = sum(agent.error_count for agent in self._agents.values())
        
        return {
            "total_agents": total_agents,
            "initialized": self._initialized,
            "agents_by_state": state_counts,
            "agents_by_tier": tier_counts,
            "aggregate_metrics": {
                "total_tasks": total_tasks,
                "successful_tasks": total_success,
                "failed_tasks": total_errors,
                "overall_success_rate": (
                    total_success / total_tasks if total_tasks > 0 else 0.0
                ),
            }
        }

    def __len__(self) -> int:
        """Return number of registered agents."""
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        """Check if agent is registered."""
        return agent_id in self._agents

    def __repr__(self) -> str:
        """String representation of registry."""
        return f"AgentRegistry(agents={len(self._agents)}, initialized={self._initialized})"
