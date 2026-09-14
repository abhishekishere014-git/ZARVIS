"""Built-in specialized agents for the JARVIS platform."""

from jarvis.agents.builtins.coding import CodingAgent
from jarvis.agents.builtins.planner import PlannerAgent
from jarvis.agents.builtins.reasoning import ReasoningAgent
from jarvis.agents.builtins.recovery_agent import RecoveryAgent
from jarvis.agents.builtins.research import ResearchAgent
from jarvis.agents.builtins.review import ReviewAgent
from jarvis.agents.builtins.security import SecurityAgent
from jarvis.agents.builtins.synthesis_agent import SynthesisAgent
from jarvis.agents.builtins.testing import TestingAgent
from jarvis.agents.builtins.verifier_agent import VerifierAgent
from jarvis.agents.registry import AgentRegistry


def register_builtin_agents(registry: AgentRegistry) -> None:
    """Registers all 10 specialized built-in agents into the given AgentRegistry."""
    registry.register(PlannerAgent())
    registry.register(ResearchAgent())
    registry.register(ReasoningAgent())
    registry.register(CodingAgent())
    registry.register(SecurityAgent())
    registry.register(TestingAgent())
    registry.register(ReviewAgent())
    registry.register(VerifierAgent())
    registry.register(RecoveryAgent())
    registry.register(SynthesisAgent())


__all__ = [
    "PlannerAgent",
    "ResearchAgent",
    "ReasoningAgent",
    "CodingAgent",
    "SecurityAgent",
    "TestingAgent",
    "ReviewAgent",
    "VerifierAgent",
    "RecoveryAgent",
    "SynthesisAgent",
    "register_builtin_agents",
]
