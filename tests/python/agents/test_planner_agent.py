"""Tests for PlannerAgent goal decomposition for office and general workflows."""

import pytest
from jarvis.agents.base import AgentContext
from jarvis.agents.builtins.planner import PlannerAgent
from jarvis.agents.models import AgentTask, TaskState


@pytest.mark.asyncio
async def test_planner_agent_decomposes_presentation_goal() -> None:
    planner = PlannerAgent()
    task = AgentTask(
        id="plan_1",
        title="Plan",
        description="Plan generation",
        assigned_agent=planner.id,
        input_data={"goal_prompt": "Create a project presentation on machine learning"},
    )
    ctx = AgentContext(run_id="run_1", task=task, agent_definition=planner.definition)

    res = await planner.execute(ctx)
    assert res.status == TaskState.COMPLETED
    plan_dict = res.output["plan"]
    assert len(plan_dict["tasks"]) >= 3

    task_ids = [t["id"] for t in plan_dict["tasks"]]
    assert "task_generate_pptx" in task_ids


@pytest.mark.asyncio
async def test_planner_agent_decomposes_spreadsheet_goal() -> None:
    planner = PlannerAgent()
    task = AgentTask(
        id="plan_2",
        title="Plan",
        description="Plan spreadsheet",
        assigned_agent=planner.id,
        input_data={"goal_prompt": "Generate an excel spreadsheet for quarterly revenue"},
    )
    ctx = AgentContext(run_id="run_2", task=task, agent_definition=planner.definition)

    res = await planner.execute(ctx)
    assert res.status == TaskState.COMPLETED
    plan_dict = res.output["plan"]
    task_ids = [t["id"] for t in plan_dict["tasks"]]
    assert "task_generate_xlsx" in task_ids


@pytest.mark.asyncio
async def test_planner_agent_decomposes_word_goal() -> None:
    planner = PlannerAgent()
    task = AgentTask(
        id="plan_3",
        title="Plan",
        description="Plan doc",
        assigned_agent=planner.id,
        input_data={"goal_prompt": "Create a word document briefing for leadership"},
    )
    ctx = AgentContext(run_id="run_3", task=task, agent_definition=planner.definition)

    res = await planner.execute(ctx)
    assert res.status == TaskState.COMPLETED
    plan_dict = res.output["plan"]
    task_ids = [t["id"] for t in plan_dict["tasks"]]
    assert "task_generate_docx" in task_ids
