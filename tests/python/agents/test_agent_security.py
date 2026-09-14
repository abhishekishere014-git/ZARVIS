"""Security, adversarial attack, and isolation test suite for the agent runtime."""

from pathlib import Path
import pytest
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.executor import AgentTaskExecutor
from jarvis.agents.models import (
    AgentDefinition,
    AgentPlan,
    AgentStepResult,
    AgentTask,
    TaskState,
    VerificationState,
)
from jarvis.agents.plan_validator import PlanValidationError, PlanValidator
from jarvis.agents.registry import AgentRegistry
from jarvis.agents.verifier import AgentVerifier
from jarvis.tools.factory import build_tool_system


def test_security_blocks_circular_dependency_attack() -> None:
    validator = PlanValidator()
    # Cycle attack
    t1 = AgentTask(id="a", title="A", description="D", assigned_agent="x", dependencies=["b"])
    t2 = AgentTask(id="b", title="B", description="D", assigned_agent="x", dependencies=["a"])
    plan = AgentPlan(goal_id="g_attack", tasks=[t1, t2])

    with pytest.raises(PlanValidationError):
        validator.validate_and_sort(plan)


def test_security_blocks_disabled_agent_invocation() -> None:
    reg = AgentRegistry()

    class EvilAgent(BaseAgent):
        def __init__(self) -> None:
            super().__init__(AgentDefinition(id="agent.disabled", name="Disabled", description="Disabled", enabled=False))

        async def execute(self, context: AgentContext) -> AgentStepResult:
            return AgentStepResult(task_id=context.task.id, agent_id=self.id, status=TaskState.COMPLETED)

    reg.register(EvilAgent())
    validator = PlanValidator(agent_registry=reg)

    t1 = AgentTask(id="t1", title="Run Disabled", description="D", assigned_agent="agent.disabled")
    plan = AgentPlan(goal_id="g1", tasks=[t1])

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_and_sort(plan)
    assert "assigned to disabled agent" in str(exc.value)


@pytest.mark.asyncio
async def test_security_blocks_unauthorized_tool_request(tmp_path: Path) -> None:
    tool_system = build_tool_system(workspace_dir=tmp_path)
    reg = AgentRegistry()

    # Agent only authorized for docx
    class RestrictedAgent(BaseAgent):
        def __init__(self) -> None:
            super().__init__(
                AgentDefinition(
                    id="agent.restricted",
                    name="Restricted",
                    description="Restricted",
                    allowed_tools={"office.create_docx"},
                )
            )

        async def execute(self, context: AgentContext) -> AgentStepResult:
            return AgentStepResult(task_id=context.task.id, agent_id=self.id, status=TaskState.COMPLETED)

    agent = RestrictedAgent()
    reg.register(agent)
    task_exec = AgentTaskExecutor(agent_registry=reg, tool_executor=tool_system.executor)

    # Attempt to execute pptx (unauthorized)
    obs = await task_exec.execute_tool_for_agent(
        agent=agent,
        tool_id="office.create_pptx",
        arguments={"filename": "hack.pptx", "title": "Hack", "slides": []},
        task_id="t_unauth",
    )
    assert obs.status == "denied"
    assert "not authorized to invoke tool" in (obs.error or "")


def test_security_verifier_rejects_hallucinated_file_success(tmp_path: Path) -> None:
    verifier = AgentVerifier()
    task = AgentTask(id="t_fake", title="Fake", description="D", assigned_agent="a1")
    # Agent claims file exists at /imaginary/path/doc.docx
    fake_result = AgentStepResult(
        task_id="t_fake",
        agent_id="a1",
        status=TaskState.COMPLETED,
        output="Created document successfully!",
        artifacts=[str(tmp_path / "nonexistent_fabricated.docx")],
    )

    ver = verifier.verify_step(task, fake_result)
    assert ver.state != VerificationState.PASSED
    assert any("missing_file" in m for m in ver.missing_evidence)
