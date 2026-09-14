"""Tests for evidence-based AgentVerifier inspecting outputs, tools, and artifacts."""

from pathlib import Path
from jarvis.agents.models import (
    AgentObservation,
    AgentPlan,
    AgentStepResult,
    AgentTask,
    TaskState,
    VerificationState,
)
from jarvis.agents.verifier import AgentVerifier
from jarvis.tools.sandbox import FileSystemSandbox


def test_verifier_passes_on_valid_evidence(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    verifier = AgentVerifier(sandbox=sandbox)

    # Create dummy artifact file in sandbox
    doc_file = tmp_path / "report.docx"
    doc_file.write_text("dummy doc content")

    task = AgentTask(id="t1", title="Gen Doc", description="Create doc", assigned_agent="a1")
    step_res = AgentStepResult(
        task_id="t1",
        agent_id="a1",
        status=TaskState.COMPLETED,
        output="Document created",
        artifacts=[str(doc_file)],
        observations=[
            AgentObservation(task_id="t1", tool_id="office.create_docx", status="success", artifacts=[str(doc_file)])
        ],
    )

    ver = verifier.verify_step(task, step_res)
    assert ver.state == VerificationState.PASSED
    assert ver.score == 1.0
    assert len(ver.verified_artifacts) == 1


def test_verifier_fails_on_missing_artifact(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    verifier = AgentVerifier(sandbox=sandbox)

    ghost_file = tmp_path / "does_not_exist.docx"
    task = AgentTask(id="t2", title="Gen Doc", description="Create doc", assigned_agent="a1")
    step_res = AgentStepResult(
        task_id="t2",
        agent_id="a1",
        status=TaskState.COMPLETED,
        output="Claims success",
        artifacts=[str(ghost_file)],
    )

    ver = verifier.verify_step(task, step_res)
    assert ver.state in (VerificationState.FAILED, VerificationState.PARTIAL)
    assert any("missing_file" in m for m in ver.missing_evidence)


def test_verifier_fails_on_failed_tool() -> None:
    verifier = AgentVerifier()
    task = AgentTask(id="t3", title="Run Tool", description="Run tool", assigned_agent="a1")
    step_res = AgentStepResult(
        task_id="t3",
        agent_id="a1",
        status=TaskState.COMPLETED,
        output="Ran tool",
        observations=[
            AgentObservation(task_id="t3", tool_id="office.create_docx", status="failed", error="Disk full")
        ],
    )

    ver = verifier.verify_step(task, step_res)
    assert ver.state == VerificationState.FAILED
    assert "reported failure" in ver.notes


def test_verifier_plan_verification() -> None:
    verifier = AgentVerifier()
    t1 = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1")
    t2 = AgentTask(id="t2", title="T2", description="D2", assigned_agent="a2")
    plan = AgentPlan(goal_id="g1", tasks=[t1, t2])

    from jarvis.agents.models import AgentVerification
    verifications = {
        "t1": AgentVerification(task_id="t1", state=VerificationState.PASSED),
        "t2": AgentVerification(task_id="t2", state=VerificationState.PASSED),
    }
    assert verifier.verify_plan(plan, verifications) is True

    verifications["t2"] = AgentVerification(task_id="t2", state=VerificationState.FAILED)
    assert verifier.verify_plan(plan, verifications) is False
