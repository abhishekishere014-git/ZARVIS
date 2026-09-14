"""Base agent interface and execution context contracts."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from jarvis.agents.models import (
    AgentDefinition,
    AgentObservation,
    AgentStepResult,
    AgentTask,
)
from jarvis.ai.router import AIRouter
from jarvis.tools.executor import ToolExecutor


class AgentContext(BaseModel):
    """Contextual environment injected into a specialized agent for task execution."""

    model_config = {"arbitrary_types_allowed": True}

    run_id: str
    task: AgentTask
    agent_definition: AgentDefinition
    router: Optional[AIRouter] = None
    tool_executor: Optional[ToolExecutor] = None
    prior_observations: List[AgentObservation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class establishing the contract for specialized agents."""

    def __init__(self, definition: AgentDefinition) -> None:
        self.definition = definition

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentStepResult:
        """Executes the assigned task within the provided context and returns a structured step result."""
        pass
