"""Tests for the master AgentOrchestrator state machine and workflow execution."""

from pathlib import Path
import pytest
from jarvis.agents.factory import build_agent_system
from jarvis.agents.models import AgentState
from jarvis.tools.factory import build_tool_system


@pytest.mark.asyncio
async def test_orchestrator_runs_goal_to_completion(tmp_path: Path) -> None:
    tool_system = build_tool_system(workspace_dir=tmp_path)
    agent_system = build_agent_system(tool_system=tool_system, checkpoint_dir=tmp_path / "checkpoints")

    final_resp = await agent_system.orchestrator.run("Generate an executive word document briefing on Q3")

    assert final_resp.status == AgentState.COMPLETED
    assert final_resp.task_statistics["completed"] >= 2
    assert final_resp.task_statistics["failed"] == 0
    assert len(final_resp.verified_artifacts) >= 1
    assert Path(final_resp.verified_artifacts[0]).exists()
    assert "executive word document briefing" in final_resp.summary.lower()


@pytest.mark.asyncio
async def test_orchestrator_cancellation(tmp_path: Path) -> None:
    tool_system = build_tool_system(workspace_dir=tmp_path)
    agent_system = build_agent_system(tool_system=tool_system, checkpoint_dir=tmp_path / "checkpoints")

    orch = agent_system.orchestrator
    # Mark a fake run cancelled
    orch.cancel_run("run_cancel_test")
    assert "run_cancel_test" in orch._cancelled_runs
