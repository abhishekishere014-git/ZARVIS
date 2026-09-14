"""Tests for AgentTaskExecutor dispatching tasks and tools."""

from pathlib import Path
import pytest
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.executor import AgentTaskExecutor
from jarvis.agents.models import (
    AgentDefinition,
    AgentStepResult,
    AgentTask,
    TaskState,
)
from jarvis.agents.registry import AgentRegistry
from jarvis.tools.factory import build_tool_system


class MockWorkerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            AgentDefinition(
                id="agent.worker",
                name="Worker",
                description="Worker",
                allowed_tools={"office.create_docx"},
            )
        )

    async def execute(self, context: AgentContext) -> AgentStepResult:
        if not context.tool_executor:
            return AgentStepResult(task_id=context.task.id, agent_id=self.id, status=TaskState.FAILED, error="No tool executor")

        from jarvis.tools.models import ToolRequest
        from jarvis.agents.observation import ObservationNormalizer

        tool_req = ToolRequest(
            tool_id="office.create_docx",
            arguments={
                "filename": "worker_doc.docx",
                "title": "Worker Report",
                "sections": [{"heading": "Notes", "paragraph": "Content"}],
            },
            caller=self.id,
        )
        tool_res = await context.tool_executor.execute(tool_req)
        obs = ObservationNormalizer.from_tool_result(task_id=context.task.id, result=tool_res)

        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED if obs.status == "success" else TaskState.FAILED,
            output=obs.output,
            artifacts=obs.artifacts,
            observations=[obs],
        )


@pytest.mark.asyncio
async def test_agent_task_executor_runs_task_and_tool(tmp_path: Path) -> None:
    tool_system = build_tool_system(workspace_dir=tmp_path)
    agent_reg = AgentRegistry()
    worker = MockWorkerAgent()
    agent_reg.register(worker)

    task_exec = AgentTaskExecutor(agent_registry=agent_reg, tool_executor=tool_system.executor)

    task = AgentTask(
        id="task_work_1",
        title="Generate Worker Doc",
        description="Run worker",
        assigned_agent="agent.worker",
    )

    res = await task_exec.execute_task(
        run_id="run_test_exec",
        task=task,
        prior_observations=[],
    )

    assert res.status == TaskState.COMPLETED
    assert len(res.artifacts) == 1
    assert Path(res.artifacts[0]).exists()

