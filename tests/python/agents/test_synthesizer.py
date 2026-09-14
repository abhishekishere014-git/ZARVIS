"""Tests for FinalSynthesizer combining task results into a single user response."""

import pytest
from jarvis.agents.models import (
    AgentGoal,
    AgentPlan,
    AgentRun,
    AgentState,
    AgentStepResult,
    AgentTask,
    AgentVerification,
    TaskState,
    VerificationState,
)
from jarvis.agents.synthesizer import FinalSynthesizer


@pytest.mark.asyncio
async def test_synthesizer_deterministic_summary() -> None:
    synthesizer = FinalSynthesizer()

    goal = AgentGoal(user_prompt="Build Q3 Financial Briefing")
    plan = AgentPlan(
        goal_id=goal.id,
        tasks=[
            AgentTask(id="t1", title="Research", description="D1", assigned_agent="a1"),
            AgentTask(id="t2", title="Generate", description="D2", assigned_agent="a2"),
        ],
    )
    run = AgentRun(
        goal=goal,
        plan=plan,
        state=AgentState.COMPLETED,
        completed_tasks=["t1", "t2"],
        task_results={
            "t1": AgentStepResult(task_id="t1", agent_id="a1", status=TaskState.COMPLETED, output="Revenue was $10M"),
            "t2": AgentStepResult(task_id="t2", agent_id="a2", status=TaskState.COMPLETED, output="Report created", artifacts=["/workspace/report.docx"]),
        },
        verifications={
            "t1": AgentVerification(task_id="t1", state=VerificationState.PASSED),
            "t2": AgentVerification(task_id="t2", state=VerificationState.PASSED, verified_artifacts=["/workspace/report.docx"]),
        },
    )

    final_resp = await synthesizer.synthesize(run)
    assert final_resp.run_id == run.run_id
    assert final_resp.status == AgentState.COMPLETED
    assert "Build Q3 Financial Briefing" in final_resp.summary
    assert "report.docx" in final_resp.summary
    assert final_resp.task_statistics["completed"] == 2
