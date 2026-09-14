"""Central in-memory registry for specialized agents."""

import logging
from typing import Dict, List, Optional
from jarvis.agents.base import BaseAgent
from jarvis.agents.models import AgentCapability, AgentDefinition

logger = logging.getLogger("jarvis.agents.registry")


class AgentRegistry:
    """Central registry maintaining active specialized agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Registers a specialized agent instance. Rejects duplicate IDs."""
        agent_id = agent.definition.id
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("Agent ID must be a non-empty string.")

        if agent_id in self._agents:
            raise ValueError(f"Agent with ID '{agent_id}' is already registered.")

        self._agents[agent_id] = agent
        logger.debug("Registered agent: '%s' (%s)", agent_id, agent.definition.name)

    def unregister(self, agent_id: str) -> bool:
        """Removes an agent from the registry. Returns True if removed."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.debug("Unregistered agent: '%s'", agent_id)
            return True
        return False

    def get(self, agent_id: str) -> BaseAgent:
        """Retrieves a registered agent instance by ID."""
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' is not registered.")
        return self._agents[agent_id]

    def has(self, agent_id: str) -> bool:
        """Checks if an agent ID is registered."""
        return agent_id in self._agents

    def enable(self, agent_id: str) -> None:
        """Enables a registered agent."""
        agent = self.get(agent_id)
        agent.definition.enabled = True

    def disable(self, agent_id: str) -> None:
        """Disables a registered agent."""
        agent = self.get(agent_id)
        agent.definition.enabled = False

    def list(self, enabled_only: bool = True) -> List[AgentDefinition]:
        """Lists definitions of all registered agents."""
        definitions = [agent.definition for agent in self._agents.values()]
        if enabled_only:
            definitions = [d for d in definitions if d.enabled]
        return definitions

    def discover(
        self,
        capability: Optional[AgentCapability] = None,
        enabled_only: bool = True,
    ) -> List[AgentDefinition]:
        """Discovers agents matching capability constraints."""
        defs = self.list(enabled_only=enabled_only)
        if capability:
            defs = [d for d in defs if capability in d.capabilities]
        return defs

    def find_by_capability(
        self,
        capability: AgentCapability,
        enabled_only: bool = True,
    ) -> List[BaseAgent]:
        """Returns agent instances providing a specific capability."""
        agents = list(self._agents.values())
        if enabled_only:
            agents = [a for a in agents if a.definition.enabled]
        return [a for a in agents if capability in a.definition.capabilities]
