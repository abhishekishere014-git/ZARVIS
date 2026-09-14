"""Tests for PlanValidator verifying acyclicity, dependencies, and wave sorting."""

import pytest
from jarvis.agents.models import AgentPlan, AgentTask
from jarvis.agents.plan_validator import PlanValidationError, PlanValidator


def test_plan_validator_linear_waves() -> None:
    validator = PlanValidator(max_steps=10)

    t1 = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1")
    t2 = AgentTask(id="t2", title="T2", description="D2", assigned_agent="a2", dependencies=["t1"])
    t3 = AgentTask(id="t3", title="T3", description="D3", assigned_agent="a3", dependencies=["t2"])

    plan = AgentPlan(goal_id="g1", tasks=[t1, t2, t3])
    waves = validator.validate_and_sort(plan)

    assert len(waves) == 3
    assert [t.id for t in waves[0]] == ["t1"]
    assert [t.id for t in waves[1]] == ["t2"]
    assert [t.id for t in waves[2]] == ["t3"]


def test_plan_validator_parallel_waves() -> None:
    validator = PlanValidator(max_steps=10)

    # t1 and t2 have no dependencies, t3 depends on both
    t1 = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1")
    t2 = AgentTask(id="t2", title="T2", description="D2", assigned_agent="a2")
    t3 = AgentTask(id="t3", title="T3", description="D3", assigned_agent="a3", dependencies=["t1", "t2"])

    plan = AgentPlan(goal_id="g1", tasks=[t1, t2, t3])
    waves = validator.validate_and_sort(plan)

    assert len(waves) == 2
    # Wave 0 runs t1 and t2 concurrently
    wave_0_ids = {t.id for t in waves[0]}
    assert wave_0_ids == {"t1", "t2"}
    # Wave 1 runs t3
    assert [t.id for t in waves[1]] == ["t3"]


def test_plan_validator_rejects_cycles() -> None:
    validator = PlanValidator()

    # Cycle: t1 -> t2 -> t3 -> t1
    t1 = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1", dependencies=["t3"])
    t2 = AgentTask(id="t2", title="T2", description="D2", assigned_agent="a2", dependencies=["t1"])
    t3 = AgentTask(id="t3", title="T3", description="D3", assigned_agent="a3", dependencies=["t2"])

    plan = AgentPlan(goal_id="g1", tasks=[t1, t2, t3])
    with pytest.raises(PlanValidationError) as exc:
        validator.validate_and_sort(plan)
    assert "Circular dependency detected" in str(exc.value)


def test_plan_validator_rejects_missing_dependency() -> None:
    validator = PlanValidator()
    t1 = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1", dependencies=["ghost_task"])
    plan = AgentPlan(goal_id="g1", tasks=[t1])

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_and_sort(plan)
    assert "nonexistent dependency" in str(exc.value)


def test_plan_validator_rejects_self_dependency() -> None:
    validator = PlanValidator()
    t1 = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1", dependencies=["t1"])
    plan = AgentPlan(goal_id="g1", tasks=[t1])

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_and_sort(plan)
    assert "cannot depend on itself" in str(exc.value)


def test_plan_validator_rejects_duplicate_task_ids() -> None:
    validator = PlanValidator()
    t1 = AgentTask(id="dup", title="T1", description="D1", assigned_agent="a1")
    t2 = AgentTask(id="dup", title="T2", description="D2", assigned_agent="a2")
    plan = AgentPlan(goal_id="g1", tasks=[t1, t2])

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_and_sort(plan)
    assert "Duplicate task ID" in str(exc.value)


def test_plan_validator_enforces_step_limit() -> None:
    validator = PlanValidator(max_steps=2)
    t1 = AgentTask(id="t1", title="T1", description="D1", assigned_agent="a1")
    t2 = AgentTask(id="t2", title="T2", description="D2", assigned_agent="a2")
    t3 = AgentTask(id="t3", title="T3", description="D3", assigned_agent="a3")
    plan = AgentPlan(goal_id="g1", tasks=[t1, t2, t3])

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_and_sort(plan)
    assert "exceeds maximum permitted" in str(exc.value)
