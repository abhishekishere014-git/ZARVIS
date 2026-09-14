"""Tests for bounded RecoveryEngine retries and replanning limits."""

from jarvis.agents.models import (
    AgentGoal,
    AgentRecoveryAttempt,
    AgentRun,
    AgentTask,
    RecoveryState,
)
from jarvis.agents.recovery import RecoveryEngine


def test_recovery_engine_retries_step() -> None:
    engine = RecoveryEngine(max_step_retries=2, max_replans=1)
    task = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1")
    run = AgentRun(goal=AgentGoal(user_prompt="Goal"))

    # First failure -> Retry
    state1, action1 = engine.evaluate_failure(task, "Network timeout", run)
    assert state1 == RecoveryState.RETRYING
    assert task.retry_count == 1
    assert len(run.recovery_attempts) == 1

    # Second failure -> Retry
    state2, action2 = engine.evaluate_failure(task, "Network timeout 2", run)
    assert state2 == RecoveryState.RETRYING
    assert task.retry_count == 2

    # Third failure -> Exhausted step retries -> Trigger Replan
    state3, action3 = engine.evaluate_failure(task, "Network timeout 3", run)
    assert state3 == RecoveryState.REPLANNING


def test_recovery_engine_aborts_after_replan_exhaustion() -> None:
    engine = RecoveryEngine(max_step_retries=1, max_replans=1)
    task = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1", retry_count=1)
    run = AgentRun(goal=AgentGoal(user_prompt="Goal"))
    # Simulate an existing replan
    run.recovery_attempts.append(
        AgentRecoveryAttempt(
            task_id="t1",
            failure_reason="Err",
            recovery_action="Replan",
            state=RecoveryState.REPLANNING,
            attempt_number=1,
        )
    )

    # With 1 replan already executed, subsequent failure must ABORT
    state, action = engine.evaluate_failure(task, "Final error", run)
    assert state == RecoveryState.ABORTED
    assert "Terminal failure" in action
