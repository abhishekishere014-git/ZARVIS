"""Full end-to-end autonomous multi-agent workflow test."""

from pathlib import Path
import pptx
import pytest
from jarvis.agents.factory import build_agent_system
from jarvis.agents.models import AgentState
from jarvis.tools.factory import build_tool_system


@pytest.mark.asyncio
async def test_full_autonomous_presentation_generation_workflow(tmp_path: Path) -> None:
    tool_system = build_tool_system(workspace_dir=tmp_path)
    agent_system = build_agent_system(tool_system=tool_system, checkpoint_dir=tmp_path / "checkpoints")

    user_goal = "Create a project presentation for executive stakeholders on AI Assistant Architecture"

    final_resp = await agent_system.orchestrator.run(user_goal)

    # 1. State check
    assert final_resp.status == AgentState.COMPLETED
    assert final_resp.task_statistics["completed"] >= 3
    assert final_resp.task_statistics["failed"] == 0

    # 2. Artifact verification
    assert len(final_resp.verified_artifacts) >= 1
    pptx_file = Path(final_resp.verified_artifacts[0])
    assert pptx_file.exists()
    assert pptx_file.suffix.lower() == ".pptx"

    # 3. Structural inspection of verified artifact
    prs = pptx.Presentation(str(pptx_file))
    assert len(prs.slides) >= 2

    # 4. Synthesized narrative check
    assert "executive stakeholders" in final_resp.summary.lower() or "objective successfully accomplished" in final_resp.summary.lower()
    assert pptx_file.name in final_resp.summary
