"""Tests for resource bounds and limit enforcement in the agent runtime."""

import pytest
from jarvis.agents.models import AgentPlan, AgentTask
from jarvis.agents.plan_validator import PlanValidationError, PlanValidator
from jarvis.agents.recovery import RecoveryEngine


def test_validator_enforces_max_steps() -> None:
    validator = PlanValidator(max_steps=3)
    tasks = [AgentTask(id=f"t{i}", title=f"T{i}", description="D", assigned_agent="a") for i in range(5)]
    plan = AgentPlan(goal_id="g_limit", tasks=tasks)

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_and_sort(plan)
    assert "exceeds maximum permitted" in str(exc.value)


def test_recovery_engine_enforces_max_attempts() -> None:
    engine = RecoveryEngine(max_step_retries=1, max_replans=1, max_recovery_attempts=2)
    task = AgentTask(id="t_rec", title="Task", description="Desc", assigned_agent="a")

    from jarvis.agents.models import AgentGoal, AgentRecoveryAttempt, AgentRun, RecoveryState
    run = AgentRun(goal=AgentGoal(user_prompt="Goal"))
    # Pre-populate 2 recovery attempts to hit limit
    run.recovery_attempts.append(AgentRecoveryAttempt(task_id="t1", failure_reason="f1", recovery_action="a1", state=RecoveryState.RETRYING, attempt_number=1))
    run.recovery_attempts.append(AgentRecoveryAttempt(task_id="t1", failure_reason="f2", recovery_action="a2", state=RecoveryState.RETRYING, attempt_number=2))

    state, action = engine.evaluate_failure(task, "f3", run)
    assert state == RecoveryState.ABORTED
    assert "Global recovery budget exhausted" in action
