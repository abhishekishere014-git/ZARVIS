"""Tests for ObservationNormalizer structuring tool results and internal computations."""

from jarvis.agents.observation import ObservationNormalizer
from jarvis.tools.models import ToolExecutionStatus, ToolResult


def test_observation_from_tool_result() -> None:
    tool_res = ToolResult(
        execution_id="exec_abc",
        tool_id="office.create_docx",
        status=ToolExecutionStatus.SUCCESS,
        output={"size_bytes": 14000, "paragraphs_count": 8},
        artifacts=["/path/to/doc.docx"],
        duration_ms=52.4,
    )

    obs = ObservationNormalizer.from_tool_result(task_id="task_1", result=tool_res)

    assert obs.task_id == "task_1"
    assert obs.tool_id == "office.create_docx"
    assert obs.status == "success"
    assert obs.artifacts == ["/path/to/doc.docx"]
    assert obs.evidence["size_bytes"] == 14000
    assert obs.evidence["paragraphs_count"] == 8


def test_observation_from_agent_computation() -> None:
    obs = ObservationNormalizer.from_agent_computation(
        task_id="task_2",
        output="Synthesized notes",
        status="success",
        duration_ms=12.1,
        evidence={"confidence": 0.95},
    )

    assert obs.task_id == "task_2"
    assert obs.tool_id is None
    assert obs.output == "Synthesized notes"
    assert obs.evidence["confidence"] == 0.95
