"""Tests for normalized Agent domain models, contracts, and enums."""

import pytest
from pydantic import ValidationError
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentGoal,
    AgentPlan,
    AgentRun,
    AgentState,
    AgentTask,
    AgentVerification,
    TaskState,
    VerificationState,
)


def test_agent_definition_defaults_and_validation() -> None:
    defn = AgentDefinition(
        id="agent.custom",
        name="Custom Agent",
        description="A specialized test agent",
        capabilities={AgentCapability.REASONING},
    )
    assert defn.id == "agent.custom"
    assert defn.enabled is True
    assert defn.risk_level == "low"
    assert AgentCapability.REASONING in defn.capabilities


def test_agent_goal_id_and_timestamp() -> None:
    g1 = AgentGoal(user_prompt="Analyze project status")
    g2 = AgentGoal(user_prompt="Generate documentation")
    assert g1.id != g2.id
    assert g1.user_prompt == "Analyze project status"
    assert g1.timestamp is not None


def test_agent_task_defaults_and_dependencies() -> None:
    task = AgentTask(
        id="t1",
        title="Extract Data",
        description="Extract metrics from logs",
        assigned_agent="agent.research",
        dependencies=["t0"],
    )
    assert task.state == TaskState.PENDING
    assert task.retry_count == 0
    assert task.dependencies == ["t0"]
    assert task.timeout_seconds == 60.0


def test_agent_plan_creation() -> None:
    plan = AgentPlan(
        goal_id="g_1",
        tasks=[
            AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1"),
            AgentTask(id="t2", title="T2", description="D2", assigned_agent="a2", dependencies=["t1"]),
        ],
        rationale="Sequential execution",
    )
    assert len(plan.tasks) == 2
    assert plan.goal_id == "g_1"
    assert plan.plan_id.startswith("plan_")


def test_agent_verification_model() -> None:
    ver = AgentVerification(
        task_id="t1",
        state=VerificationState.PASSED,
        score=1.0,
        verified_artifacts=["/workspace/report.docx"],
    )
    assert ver.state == VerificationState.PASSED
    assert ver.score == 1.0
    assert len(ver.verified_artifacts) == 1


def test_agent_run_state_tracking() -> None:
    goal = AgentGoal(user_prompt="Run complete build")
    run = AgentRun(goal=goal)
    assert run.state == AgentState.IDLE
    assert run.run_id.startswith("run_")
    assert run.completed_tasks == []
    assert run.failed_tasks == []
