"""Tests for AgentRegistry registration, duplicate rejection, and discovery."""

import pytest
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentStepResult,
    TaskState,
)
from jarvis.agents.registry import AgentRegistry


class DummyAgent(BaseAgent):
    def __init__(self, agent_id: str, capability: AgentCapability = AgentCapability.RESEARCH) -> None:
        super().__init__(
            AgentDefinition(
                id=agent_id,
                name=f"Dummy {agent_id}",
                description="Test dummy agent",
                capabilities={capability},
            )
        )

    async def execute(self, context: AgentContext) -> AgentStepResult:
        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output="dummy_success",
        )


def test_agent_registry_registration_and_retrieval() -> None:
    reg = AgentRegistry()
    agent = DummyAgent("agent.test_1")
    reg.register(agent)

    assert reg.has("agent.test_1") is True
    retrieved = reg.get("agent.test_1")
    assert retrieved.id == "agent.test_1"
    assert retrieved.definition.name == "Dummy agent.test_1"

    # Reject duplicate ID
    with pytest.raises(ValueError) as exc:
        reg.register(DummyAgent("agent.test_1"))
    assert "already registered" in str(exc.value)


def test_agent_registry_unregister() -> None:
    reg = AgentRegistry()
    reg.register(DummyAgent("agent.temp"))
    assert reg.unregister("agent.temp") is True
    assert reg.has("agent.temp") is False

    with pytest.raises(KeyError):
        reg.get("agent.temp")


def test_agent_registry_enable_disable() -> None:
    reg = AgentRegistry()
    reg.register(DummyAgent("agent.toggle"))

    assert len(reg.list(enabled_only=True)) == 1
    reg.disable("agent.toggle")
    assert len(reg.list(enabled_only=True)) == 0
    assert len(reg.list(enabled_only=False)) == 1

    reg.enable("agent.toggle")
    assert len(reg.list(enabled_only=True)) == 1


def test_agent_registry_discover_and_find_by_capability() -> None:
    reg = AgentRegistry()
    reg.register(DummyAgent("agent.r1", capability=AgentCapability.RESEARCH))
    reg.register(DummyAgent("agent.c1", capability=AgentCapability.CODING))

    researchers = reg.discover(capability=AgentCapability.RESEARCH)
    assert len(researchers) == 1
    assert researchers[0].id == "agent.r1"

    coding_agents = reg.find_by_capability(AgentCapability.CODING)
    assert len(coding_agents) == 1
    assert coding_agents[0].id == "agent.c1"
