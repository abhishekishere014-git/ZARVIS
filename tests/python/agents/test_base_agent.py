"""Tests for BaseAgent contract and AgentContext behavior."""

import pytest
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentDefinition,
    AgentStepResult,
    AgentTask,
    TaskState,
)


class SimpleAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            AgentDefinition(
                id="agent.simple",
                name="Simple Agent",
                description="Performs simple execution",
            )
        )

    async def execute(self, context: AgentContext) -> AgentStepResult:
        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output=f"Executed: {context.task.title}",
        )


@pytest.mark.asyncio
async def test_base_agent_execution_contract() -> None:
    agent = SimpleAgent()
    task = AgentTask(id="task_10", title="Test Task", description="Desc", assigned_agent=agent.id)
    ctx = AgentContext(
        run_id="run_test",
        task=task,
        agent_definition=agent.definition,
    )

    result = await agent.execute(ctx)
    assert result.task_id == "task_10"
    assert result.agent_id == "agent.simple"
    assert result.status == TaskState.COMPLETED
    assert "Executed: Test Task" in str(result.output)
